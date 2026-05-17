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
    4. save_positions / load_positions 整段下沉 Rust（PR-G）：新契约采用
       sha256(canonical JSON) 作为 ``checksum`` 字段，可在 Rust / Python 端
       byte-for-byte 一致地复现。旧的 ``md5`` 字段（CPython 字典 repr() 计算）
       在加载时**静默忽略**，用户可调用 ``save_positions`` 写回升级。
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

# 直接调用 Rust 端的派生器（用下划线后缀别名，避免与同名公开 API 混淆）
# 2026-05-17 PR-F / PR-G：unique_signals / save_position / load_position 全部
# 下沉 Rust（czsc_trader::strategy），与 Rust crate 上同名 API 共享实现，
# 开发宪法第一条完整收口。
from czsc._native import (
    derive_signals_config as _derive_signals_config_impl,
)
from czsc._native import (
    derive_signals_freqs as _derive_signals_freqs_impl,
)
from czsc._native import (
    strategy_load_position as _strategy_load_position_impl,
)
from czsc._native import (
    strategy_save_position as _strategy_save_position_impl,
)
from czsc._native import (
    strategy_unique_signals as _strategy_unique_signals_impl,
)
from czsc._runtime_adapters import (
    bars_to_dataframe,
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
        """汇总所有 Position 中出现过的信号 key，去重并保持首次出现顺序。

        实现下沉到 Rust（``czsc._native.strategy_unique_signals`` /
        ``czsc_trader::strategy::unique_signals_across``），保证 ``cargo
        add czsc`` 的 Rust 用户与 ``pip install czsc`` 的 Python 用户拿到
        完全一致的语义（参见 CLAUDE.md「🏛️ 开发宪法 · 第一条」）。
        Python 侧只做一次列表透传，不再维护任何去重 / 排序逻辑。
        """
        return list(_strategy_unique_signals_impl(self.positions))

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
        # signals_config 已经是 derive_signals_config 返回的扁平 dict；
        # Rust 端 derive_signals_freqs 直接接受这种形态，无需再做适配（PR-2）。
        return sort_freqs(_derive_signals_freqs_impl(self.signals_config))

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
        """将策略持仓序列化为 JSON 文件落盘，附带 sha256 ``checksum`` 字段。

        每个 Position 写为一个独立 JSON 文件（``<position_name>.json``）。
        IO + 校验逻辑由 Rust 端 ``czsc._native.strategy_save_position`` 完成
        （见 ``czsc_trader::strategy::save_position_to_file``，开发宪法第一条收口）。

        参数:
            path: 输出目录；不存在会自动创建
        """
        out_dir = Path(path)
        out_dir.mkdir(parents=True, exist_ok=True)
        for pos in self.positions:
            target = out_dir / f"{pos.name}.json"
            _strategy_save_position_impl(pos, target)

    def load_positions(self, files, check=True):
        """从多个 JSON 文件加载 Position 列表，自动绑定当前策略的 symbol。

        IO + 校验逻辑由 Rust 端 ``czsc._native.strategy_load_position`` 完成
        （见 ``czsc_trader::strategy::load_position_from_file``）。

        参数:
            files: JSON 文件路径列表
            check: 是否校验文件中的 ``checksum`` 字段；默认开启。
                   - 新格式（PR-G+）``checksum`` 缺失或不匹配时抛 ``ValueError``；
                   - 旧格式 ``md5`` 字段（CPython repr，无法跨语言复现）静默跳过；
                   - 既无 ``checksum`` 也无 ``md5`` 的手写 JSON 也跳过校验。

        返回:
            list[Position]
        """
        return [_strategy_load_position_impl(file, self.symbol, check) for file in files]

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
            # PR-2 / PR-4：signals_config 与 Position dump 的归一化已由 Rust 处理，直接透传
            "signals_config": list(self.signals_config),
            "positions": [pos.dump(with_data=False) for pos in self.positions],
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
