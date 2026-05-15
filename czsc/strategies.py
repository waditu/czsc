"""
策略门面（Facade）模块

定位:
    在 Rust 后端的 Trader / 信号 / 仓位之上，提供一层 Python 友好的策略
    抽象（CzscStrategyBase），屏蔽底层 PyO3 类型与运行时格式细节。
    用户只需要继承基类、实现 ``positions`` 即可获得完整的回测、回放、
    序列化与反序列化能力。

关键设计:
    1. 策略元数据（unique_signals / signals_config / freqs / base_freq）
       全部由 ``positions`` 自动派生，避免子类手工填写引起不一致
    2. 用户层与运行时配置之间的格式互转集中在 czsc._runtime_adapters，本模块只负责
       调度，不直接关心字段映射
    3. backtest / replay 委托给 czsc.research 中的 run_research / run_replay，
       本模块只组合参数与处理 IO（路径、刷新、是否落盘等）
"""

from __future__ import annotations

import hashlib
import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from czsc._native import Position

# 直接调用 Rust 端的派生器（用下划线后缀别名，避免与同名公开 API 混淆）
from czsc._native import (
    derive_signals_config as _derive_signals_config_impl,
)
from czsc._native import (
    derive_signals_freqs as _derive_signals_freqs_impl,
)
from czsc._runtime_adapters import (
    bars_to_dataframe,
    position_dump_to_runtime,
    signal_config_to_runtime,
    sort_freqs,
)
from czsc.research import run_replay, run_research


class CzscStrategyBase(ABC):
    """
    czsc 风格策略定义的 Python 抽象基类

    使用方式:
        子类只需实现 :attr:`positions` 属性，返回 ``Position`` 列表；
        其它元数据（unique_signals / signals_config / freqs / base_freq）
        会由本类基于 ``positions`` 自动派生，子类无需关心。

    必填初始化参数（通过 kwargs 传入）:
        - symbol: 策略对应的标的代码

    常用可选参数:
        - name:                策略名（默认取类名），影响产物目录命名
        - market:              市场标识，默认 "默认"
        - bg_max_count:        BarGenerator 缓冲根数上限，默认 5000
        - sdt / include_sdt_bar: 起始时间相关
    """

    def __init__(self, **kwargs):
        """保存策略级参数，子类可通过 ``self.kwargs.get(key)`` 读取或扩展。"""
        self.kwargs = kwargs

    @property
    def symbol(self):
        """策略绑定的标的代码（必传，缺失会触发 KeyError 显式报错）"""
        return self.kwargs["symbol"]

    @property
    def unique_signals(self):
        """
        汇总所有 Position 中出现过的信号 key，去重并保持首次出现顺序

        为什么不用 ``set``？
            - set 不保证顺序，会让最终生成的 signals_config 顺序在不同
              Python 版本/运行环境中飘移
            - 显式维护一个 ``ordered`` 列表 + ``seen`` 集合既能去重又能
              保留稳定顺序，便于 diff 与产物比对
        """
        seen = set()
        ordered = []
        for pos in self.positions:
            for signal in pos.unique_signals:
                if signal not in seen:
                    seen.add(signal)
                    ordered.append(signal)
        return ordered

    @property
    def signals_config(self):
        """基于 ``unique_signals`` 派生的信号配置列表（运行时三段式格式）。"""
        return list(_derive_signals_config_impl(self.unique_signals))

    @property
    def freqs(self):
        """
        策略涉及的所有周期集合（去重并按缠论惯用顺序排序）

        实现细节:
            先把 signals_config 转回运行时格式，再交给 Rust 派生器返回所有
            涉及的周期；最后用 :func:`sort_freqs` 做去重与排序。
        """
        runtime = [signal_config_to_runtime(cfg) for cfg in self.signals_config]
        return sort_freqs(_derive_signals_freqs_impl(runtime))

    @property
    def sorted_freqs(self):
        """与 :attr:`freqs` 等价的别名（保留接口兼容）"""
        return sort_freqs(self.freqs)

    @property
    def base_freq(self):
        """策略基础周期：取 freqs 中最小（最高频）的那一档"""
        return self.sorted_freqs[0]

    @property
    @abstractmethod
    def positions(self):
        """
        策略持仓列表（必须由子类实现）

        返回值要求:
            list[czsc._native.Position]，每个元素描述一组开/平仓事件与参数。
        """
        raise NotImplementedError

    def backtest(self, bars, **kwargs):
        """
        执行策略回测，返回内存中的 :class:`ResearchResult`

        参数:
            bars:   K 线数据；可以是 DataFrame、RawBar 列表或 Arrow 字节
            kwargs: 可选覆盖项：
                    - sdt:           起始时间覆盖
                    - emit_signals:  是否产出信号产物
                    - include_sdt_bar: 是否包含 sdt 当根 K 线
        """
        return run_research(
            self._normalize_bars_input(bars),
            self._build_runtime_strategy(kwargs),
            sdt=kwargs.get("sdt"),
            opts=self._build_run_opts(kwargs),
        )

    def replay(self, bars, res_path, **kwargs):
        """
        执行策略回放，结果写入指定目录

        参数:
            bars:     K 线数据
            res_path: 落盘根目录
            kwargs:
                refresh:   True 表示先清空 res_path 再写入；默认 False
                exist_ok:  目录已存在但 refresh=False 时是否仍然执行；
                           默认 False，此时会跳过执行并返回 None
                其余可覆盖项同 :meth:`backtest`

        返回:
            :class:`ReplayResult`；当目录已存在且未要求覆盖时返回 ``None``
        """
        path = Path(res_path)
        # 显式要求刷新：先清空目录，避免新旧产物混合
        if kwargs.get("refresh", False):
            shutil.rmtree(path, ignore_errors=True)

        # 既不允许覆盖也未要求刷新 -> 跳过执行（避免重复回放浪费算力）
        exist_ok = kwargs.get("exist_ok", False)
        if path.exists() and not exist_ok and not kwargs.get("refresh", False):
            return None

        return run_replay(
            self._normalize_bars_input(bars),
            self._build_runtime_strategy(kwargs),
            res_path=path,
            sdt=kwargs.get("sdt"),
            opts=self._build_run_opts(kwargs),
        )

    def save_positions(self, path):
        """
        将策略持仓序列化为 JSON 文件落盘（兼容 ``Position.dump`` 格式）

        每个 Position 写为一个独立 JSON 文件（``<position_name>.json``），
        文件中包含一个 ``md5`` 字段，用于后续加载时校验文件未被篡改。

        参数:
            path: 输出目录；不存在会自动创建
        """
        out_dir = Path(path)
        out_dir.mkdir(parents=True, exist_ok=True)
        for pos in self.positions:
            payload = position_dump_to_runtime(pos.dump(with_data=False))
            # symbol 与策略实例耦合，落盘时移除以便 Position 可被复用到不同标的
            payload.pop("symbol", None)
            # md5 校验码：基于序列化字符串生成，加载时可校验配置完整性
            payload["md5"] = hashlib.md5(str(payload).encode("utf-8")).hexdigest()
            (out_dir / f"{payload['name']}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load_positions(self, files, check=True):
        """
        从多个 JSON 文件加载 Position 列表，并自动绑定当前策略的 symbol

        参数:
            files: JSON 文件路径列表
            check: 是否校验文件中的 md5 字段；默认开启。出现不一致即抛 AssertionError，
                   防止持仓配置被外部静默修改。

        返回:
            list[Position]
        """
        positions = []
        for file in files:
            payload = json.loads(Path(file).read_text(encoding="utf-8"))
            md5 = payload.pop("md5", None)
            # md5 校验：确保 dump/load 之间文件内容一致；md5 不存在时跳过校验（兼容旧文件）
            if check and md5 is not None:
                assert md5 == hashlib.md5(str(payload).encode("utf-8")).hexdigest()
            # 把当前策略的 symbol 注入到 Position 配置中（save_positions 时被剥离）
            payload["symbol"] = self.symbol
            positions.append(Position.load(payload))
        return positions

    def _build_runtime_strategy(self, overrides: dict[str, Any]) -> dict[str, Any]:
        """
        把 self + overrides 拼装为 Rust 端可以直接消费的运行时 strategy dict

        参数:
            overrides: 调用 backtest/replay 时传入的临时覆盖参数

        返回:
            一份完整的策略字典，positions 与 signals_config 已转为运行时格式
        """
        # sdt 解析顺序：调用时显式传 > 实例 kwargs > None（不带 sdt 字段）
        sdt = overrides.get("sdt", self.kwargs.get("sdt"))
        strategy = {
            "name": self.kwargs.get("name", self.__class__.__name__),
            "symbol": self.symbol,
            "base_freq": self.base_freq,
            "signals_config": [signal_config_to_runtime(cfg) for cfg in self.signals_config],
            "positions": [position_dump_to_runtime(pos.dump(with_data=False)) for pos in self.positions],
            "market": self.kwargs.get("market", "默认"),
            "bg_max_count": int(self.kwargs.get("bg_max_count", 5000)),
            # 仅当 sdt 存在时才注入字段，避免显式写 None 触发 Rust 端 schema 错误
            **({"sdt": sdt} if sdt else {}),
        }
        # include_sdt_bar 行为说明：
        #   - 默认走 CzscStrategyBase 语义：bars_right 从 ``dt > sdt`` 开始（不包含起始那根）
        #   - 调用方显式传 True 时，切到 generate_czsc_signals 风格 ``dt >= sdt``（包含起始那根）
        #   - 显式传 False 同样会写入字段，让 Rust 端按指定语义运行
        include_sdt_bar = overrides.get(
            "include_sdt_bar",
            self.kwargs.get("include_sdt_bar"),
        )
        if include_sdt_bar is not None:
            strategy["include_sdt_bar"] = bool(include_sdt_bar)
        return strategy

    @staticmethod
    def _build_run_opts(kwargs: dict[str, Any]) -> dict[str, Any] | None:
        """
        从用户 kwargs 中提取 Rust 端 opts 字段

        当前仅暴露 ``emit_signals`` 一个开关，控制是否把信号产物写入结果。
        未传入时返回 None，让 Rust 端使用默认行为，避免发送空 dict 引起歧义。
        """
        if "emit_signals" not in kwargs:
            return None
        return {"emit_signals": bool(kwargs["emit_signals"])}

    def _normalize_bars_input(self, bars):
        """
        把多种 K 线输入统一为 Rust 可接受的形式

        - bytes / bytearray: 视为已就绪的 Arrow 字节，直接透传
        - 其他（DataFrame / list[RawBar]）: 走 ``bars_to_dataframe`` 强制规范，
          关键是把所有数值列转为 Float64（Rust IPC 读取器对类型严格匹配）
        """
        if isinstance(bars, (bytes, bytearray)):
            return bytes(bars)
        # 即便已经是 DataFrame，也要走一次 bars_to_dataframe，
        # 以确保数值列被强制转为 Float64（Rust IPC 读取器对此严格要求）。
        return bars_to_dataframe(bars, symbol=self.symbol)


class CzscJsonStrategy(CzscStrategyBase):
    """
    直接从 JSON 文件加载持仓定义的策略包装器

    使用场景:
        策略配置由外部工具（GUI / 管理后台 / 优化结果）落盘为 JSON 后，
        Python 侧只需指定文件路径即可装载并执行回测/回放。

    初始化关键参数（通过 kwargs 传入）:
        - files_position: JSON 文件路径列表
        - check_position: 是否做 md5 校验；默认 True
        - 其余同 :class:`CzscStrategyBase`
    """

    @property
    def positions(self):
        """从 ``files_position`` 加载并返回 Position 列表，受 ``check_position`` 控制是否校验"""
        return self.load_positions(self.kwargs["files_position"], self.kwargs.get("check_position", True))
