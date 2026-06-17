"""czsc.traders.optimize —— 开仓/平仓参数批量优化的 Python 外观层。

本模块对外保留与历史版本一致的类式调用接口（``OpensOptimize``、
``ExitsOptimize`` 以及与之配套的两个策略类 ``CzscOpenOptimStrategy``、
``CzscExitOptimStrategy``），但实际的优化计算已统一委托给 Rust 端的批量
优化引擎 ``czsc.research.run_optimize_batch``，以便利用其多线程与底层
向量化能力。

Python 侧的主要职责：

1. **配置归一化**：将候选信号、候选事件等多种灵活输入形式归一到 Rust 侧
   接受的稳定结构。
2. **物化数据**：将原始 K 线和持仓配置序列化到磁盘 parquet/JSON 文件，
   作为 Rust 引擎读取的数据源。
3. **任务命名/哈希**：基于候选输入与品种集合生成唯一任务哈希，便于结果
   目录隔离与任务复用。
4. **结果转发**：保留 Rust 引擎的执行结果对象，并在实例上记录 ``message``
   等关键字段供调用方查看。

策略类（``CzscOpenOptimStrategy`` / ``CzscExitOptimStrategy``）则负责将
单个"基准仓位（beta）"按候选信号或候选事件展开为多组变体仓位，配合上层
研究框架完成参数空间扫描。
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from czsc._native import Position

# 运行时适配层：仅引入被多处共享的转换函数；哈希 / Python 字面量渲染等
# 唯一被本模块使用的 helper 已下沉到文件末尾的私有函数段，避免拆解后
# _runtime_adapters 又长成"什么都装"的中转站。
from czsc._runtime_adapters import (
    bars_to_dataframe,
    normalize_candidate_event,
    normalize_candidate_events,
)
from czsc.research import run_optimize_batch
from czsc.strategies import CzscStrategyBase


# ----------------------------------------------------------------------------
# 私有 helper：哈希与 Python 字面量渲染（用于任务哈希 + 生成策略骨架字面量）
# ----------------------------------------------------------------------------
def _md5_upper8(value: str) -> str:
    """计算字符串 MD5 哈希并截取前 8 位大写表示（用于生成短任务 ID）。"""
    return hashlib.md5(value.encode("utf-8")).hexdigest()[:8].upper()


def _py_escape_str(value: str) -> str:
    """转义字符串中的反斜杠和单引号，便于嵌入 Python 源代码字面量。"""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _py_repr_list_str(items: list[str]) -> str:
    """把字符串列表渲染为 Python 字面量片段（``['a', 'b']``），空列表返回 ``"[]"``。"""
    if not items:
        return "[]"
    return "[" + ", ".join(f"'{_py_escape_str(item)}'" for item in items) + "]"


def _py_repr_json(value: Any) -> str:
    """将 JSON 兼容值递归渲染为 Python 字面量字符串。

    与内置 ``repr()`` 的差异：

    - 字符串总是用单引号包裹，便于嵌入双引号 docstring
    - 对反斜杠和单引号执行 :func:`_py_escape_str` 转义，避免破坏代码结构
    - bool 单独处理（必须在 int 之前），避免被 ``isinstance(_, int)`` 错误吞掉

    支持：None / bool / int / float / str / list / dict；其他类型走 ``str()`` 兜底再递归。
    """
    if value is None:
        return "None"
    if isinstance(value, bool):
        # 必须先于 int 检查：bool 是 int 的子类，否则会被当成 0/1 输出
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f"'{_py_escape_str(value)}'"
    if isinstance(value, list):
        return "[" + ", ".join(_py_repr_json(item) for item in value) + "]"
    if isinstance(value, dict):
        return (
            "{" + ", ".join(f"'{_py_escape_str(str(key))}': {_py_repr_json(val)}" for key, val in value.items()) + "}"
        )
    # 兜底：把非典型类型按字符串处理，再走一次递归
    return _py_repr_json(str(value))


def _signal_to_kv(signal: dict[str, Any] | str) -> dict[str, str]:
    """将单个候选信号统一转换为 ``{"key": ..., "value": ...}`` 结构。

    输入可以是已经构造好的字典，也可以是缠论信号约定的字符串形式。
    字符串信号通常按 ``_`` 分割成多段，最后 4 段视为信号取值（value），
    其余段视为信号键（key）。

    Args:
        signal: 待规范化的信号；支持 ``dict`` 或 ``str``。

    Returns:
        包含 ``key`` 与 ``value`` 字段的字典；两个字段都被显式转换为字符串。

    Raises:
        ValueError: 当 ``signal`` 为字符串但分段数不足 5 段时抛出，
            说明该信号字符串不符合 czsc 命名规范。
    """
    if isinstance(signal, dict):
        # 字典输入只需做类型规范化，避免下游 Rust 端遇到非字符串类型时报错。
        return {"key": str(signal["key"]), "value": str(signal["value"])}
    parts = str(signal).split("_")
    if len(parts) < 5:
        # czsc 信号串至少形如 "freq_k1_k2_v1_v2_v3_v4"，不足 5 段时无法切分。
        raise ValueError(f"invalid signal string: {signal}")
    # 约定最后 4 段为取值（value），其余段拼接回完整的 key。
    return {"key": "_".join(parts[:-4]), "value": "_".join(parts[-4:])}


def _read_bars(read_bars: Callable, symbol: str, base_freq: str, bar_sdt: str, bar_edt: str):
    """以兼容方式调用上层提供的 ``read_bars`` 函数获取原始 K 线。

    某些用户自定义的 ``read_bars`` 不接受 ``fq``、``raw_bar`` 等扩展参数，
    本函数对此进行 ``TypeError`` 兜底重试，从而避免使用方修改自己的实现
    就能接入优化框架。

    Args:
        read_bars: 用户提供的 K 线读取函数。
        symbol: 标的代码。
        base_freq: 基础 K 线周期（如 "30分钟"）。
        bar_sdt: 起始日期，字符串格式。
        bar_edt: 结束日期，字符串格式。

    Returns:
        ``read_bars`` 实现返回的 K 线对象（通常是 RawBar 列表）。
    """
    try:
        # 优先以"完整签名"调用，确保拉取的是后复权的 RawBar 序列。
        return read_bars(symbol, base_freq, bar_sdt, bar_edt, fq="后复权", raw_bar=True)
    except TypeError:
        # 用户函数若签名较老/较窄，则退化到最简调用形式。
        return read_bars(symbol, base_freq, bar_sdt, bar_edt)


class CzscOpenOptimStrategy(CzscStrategyBase):
    """开仓参数优化所使用的兼容策略类。

    本策略以一个"基准仓位（beta position）"为种子，根据用户提供的候选开仓
    信号集合，为每条候选信号派生出一份新的仓位变体；最终的 ``positions``
    属性返回基准仓位与所有变体仓位的并集，供研究框架批量回测对比。
    """

    @staticmethod
    def update_beta_opens(beta: Position, open_signals_all):
        """复制基准仓位，并在其首个开仓事件中追加额外的"全部满足"信号。

        Args:
            beta: 作为模板复制的基准 :class:`Position` 实例。
            open_signals_all: 候选开仓信号；可以是单个信号字符串/字典，
                也可以是包含多个信号的列表，统一被视作"全部满足"约束。

        Returns:
            一份新的 :class:`Position` 实例，其名称带有 ``#<8 位哈希>``
            后缀，用于在结果目录中区分不同变体。
        """
        if isinstance(open_signals_all, str):
            # 兼容用户传入单个信号字符串的情形，统一升级为列表处理。
            open_signals_all = [open_signals_all]

        # 把所有候选信号统一转成 {"key": ..., "value": ...} 字典格式。
        normalized = [_signal_to_kv(sig) for sig in open_signals_all]
        # 以 with_data=False 拿到仓位的"配置面"快照，避免拷贝运行时数据。
        pos_dict = beta.dump(with_data=False)
        # 用候选信号集合的 md5 前 8 位作为名称后缀，确保变体名称唯一可追溯。
        sig_hash = hashlib.md5(str(normalized).encode("utf-8")).hexdigest()[:8].upper()
        pos_dict["name"] = f"{beta.name}#{sig_hash}"
        # 在第一个开仓事件的 signals_all（AND 约束）列表中追加候选信号。
        pos_dict["opens"][0]["signals_all"].extend(normalized)
        return Position.load(pos_dict)

    @property
    def positions(self):
        """构造所有待回测的仓位列表（基准 + 各候选信号变体）。

        Returns:
            ``list[Position]``：先包含全部基准仓位，再追加每个基准仓位与
            每条候选信号交叉派生出的变体仓位。
        """
        betas = self.load_positions(self.kwargs["files_position"])
        # 输出列表先复制一份基准仓位，作为对照组保留。
        pos_list = list(betas)
        for beta in betas:
            for sig in list(self.kwargs["candidate_signals"]):
                # 基准仓位 × 候选信号 的二重笛卡尔积，逐个生成变体仓位。
                pos_list.append(self.update_beta_opens(beta, sig))
        return pos_list


class CzscExitOptimStrategy(CzscStrategyBase):
    """平仓参数优化所使用的兼容策略类。

    在基准仓位的基础上，结合用户提供的"候选平仓事件"集合，按"替换"和
    "追加"两种模式各派生出一份新的仓位变体，从而扫描不同平仓规则对收益
    的影响。
    """

    @staticmethod
    def update_beta_exits(beta: Position, event_dict: dict[str, Any], mode="replace"):
        """复制基准仓位并应用一条候选平仓事件，生成一份新的仓位。

        Args:
            beta: 作为模板复制的基准 :class:`Position` 实例。
            event_dict: 候选平仓事件的字典描述，需包含 ``operate`` 字段。
            mode: 应用方式，支持 ``"replace"``（用候选事件替换原有 exits）
                与 ``"append"``（在原有 exits 末尾追加候选事件）。

        Returns:
            一份新的 :class:`Position` 实例；当候选事件的 operate 与基准
            仓位的开仓方向不匹配（例如全开多但事件为"平空"）时，返回
            ``None`` 表示该变体应被跳过。

        Raises:
            ValueError: 当 ``mode`` 既不是 ``"replace"`` 也不是 ``"append"`` 时抛出。
        """
        # 通过兼容层把候选事件归一化成 Rust 侧期望的稳定结构。
        event = normalize_candidate_event(event_dict)
        pos_dict = beta.dump(with_data=False)
        # 收集所有开仓事件的方向，用于判断本仓位是"全多"还是"全空"。
        open_ops = [item["operate"] for item in pos_dict["opens"]]

        # 仅当事件方向与开仓方向一致时才有意义；否则跳过该候选。
        if all(op == "开多" for op in open_ops) and event["operate"] != "平多":
            return None
        if all(op == "开空" for op in open_ops) and event["operate"] != "平空":
            return None
        if mode not in {"replace", "append"}:
            raise ValueError("mode must be replace or append")

        # 用事件内容的 md5 前 8 位作为变体名称后缀，确保唯一可追溯。
        event_hash = hashlib.md5(str(event).encode("utf-8")).hexdigest()[:8].upper()
        if mode == "replace":
            # "替换"模式：用候选事件完全覆盖原有平仓规则集合。
            pos_dict["exits"] = [event]
            pos_dict["name"] = f"{beta.name}#替换{event_hash}"
        else:
            # "追加"模式：保留原有平仓规则，在末尾叠加候选事件。
            pos_dict["exits"].append(event)
            pos_dict["name"] = f"{beta.name}#追加{event_hash}"
        return Position.load(pos_dict)

    @property
    def positions(self):
        """构造所有待回测的仓位列表（基准 + 替换变体 + 追加变体）。

        Returns:
            ``list[Position]``：先包含全部基准仓位；随后对每个基准仓位
            与每条候选事件，分别尝试 ``append`` 与 ``replace`` 两种应用
            模式，仅保留方向匹配的有效变体。
        """
        betas = self.load_positions(self.kwargs["files_position"])
        # 候选事件统一归一化，确保 mode 判断和后续派生时数据结构稳定。
        events = normalize_candidate_events(self.kwargs["candidate_events"])
        pos_list = list(betas)
        for beta in betas:
            for event in events:
                # 同时尝试追加模式与替换模式，最大化扫描覆盖。
                append_pos = self.update_beta_exits(beta, event, mode="append")
                replace_pos = self.update_beta_exits(beta, event, mode="replace")
                if append_pos is not None:
                    pos_list.append(append_pos)
                if replace_pos is not None:
                    pos_list.append(replace_pos)
        return pos_list


class OpensOptimize:
    """开仓参数批量优化的 Python 外观类。

    与历史版本的 ``czsc.traders.optimize.OpensOptimize`` 在调用方式上完全
    一致；内部不再实现 Python 端的优化主循环，而是把任务配置、K 线数据、
    持仓快照等输入物化到磁盘后委托给 Rust 端的批量优化引擎执行。

    Attributes:
        version: 当前 OpensOptimize 实现的版本标识符。
        read_bars: 用户传入的 K 线读取函数。
        kwargs: 用户提供的全部配置项的浅拷贝。
        symbols: 排序后的标的代码列表。
        files_position: 待优化的基准持仓配置文件列表。
        task_name: 任务名称，用于结果目录命名。
        candidate_signals: 排序后的候选开仓信号列表。
        base_freq: 基础 K 线周期，未提供时通过策略类自动推导。
        results_root: 结果输出根目录。
        task_hash: 由候选信号 + 标的列表生成的 8 位 MD5 任务哈希。
        results_path: 当前任务的结果输出目录（含哈希后缀）。
        poss_path: 当前任务的持仓快照子目录路径。
        message: ``execute`` 完成后填充，记录 Rust 端返回的信息。
    """

    def __init__(self, read_bars: Callable, **kwargs):
        """保存配置并预计算任务哈希、输出目录等元信息。

        Args:
            read_bars: 用户提供的 K 线读取函数，签名详见 :func:`_read_bars`。
            **kwargs: 任务配置；至少需要包含 ``symbols``、``files_position``、
                ``candidate_signals``、``results_path`` 等键；可选项包括
                ``task_name``、``base_freq``、``bar_sdt``、``bar_edt``、
                ``market``、``bg_max_count`` 等。

        Notes:
            未显式提供 ``base_freq`` 时，会临时构造一个 :class:`CzscOpenOptimStrategy`
            实例从其 ``base_freq`` 属性中推导。
        """
        self.version = "OpensOptimizeV230924"
        self.read_bars = read_bars
        # 浅拷贝一份用户配置，避免外部 dict 后续被修改影响内部状态。
        self.kwargs = dict(kwargs)
        self.symbols = sorted(kwargs["symbols"])
        self.files_position = [str(x) for x in kwargs["files_position"]]
        self.task_name = kwargs.get("task_name", "入场优化")
        self.candidate_signals = sorted(kwargs["candidate_signals"])
        # base_freq 优先取用户显式配置；否则借助策略类自动推导，
        # 保证后续读取 K 线和写入 Rust 配置时频率信息一致。
        self.base_freq = (
            kwargs.get("base_freq")
            or CzscOpenOptimStrategy(
                symbol="symbol",
                files_position=self.files_position,
                candidate_signals=self.candidate_signals,
            ).base_freq
        )
        self.results_root = Path(kwargs["results_path"])
        # 用候选信号集合 + 标的列表的字符串拼接做 MD5，截前 8 位作任务哈希；
        # 相同输入会得到相同的输出目录，便于结果复用与覆盖。
        self.task_hash = _md5_upper8(
            f"{_py_repr_list_str(self.candidate_signals)}_{_py_repr_list_str(sorted(self.symbols))}"
        )
        self.results_path = str(self.results_root / f"{self.task_name}_{self.task_hash}")
        self.poss_path = str(Path(self.results_path) / "poss")

    def execute(self, n_jobs=1):
        """物化输入数据并触发 Rust 端的开仓批量优化任务。

        Args:
            n_jobs: 传给 Rust 引擎的并发线程数；默认为 1（顺序执行）。

        Returns:
            Rust 引擎返回的结果对象；同时该对象的 ``message`` 字段会被
            缓存到 ``self.message`` 上，便于调用方事后查阅。
        """
        # 把所有标的的 K 线写入 parquet，作为 Rust 引擎读取的原料。
        bars_dir = self._materialize_bars_dir()
        # 把基准持仓 JSON 转换为 Rust 期望的 runtime 格式后落盘。
        files_position = self._materialize_position_files()
        # 组装传给 Rust 的优化任务配置；optim_type 标记为开仓优化。
        cfg = {
            "optim_type": "open",
            "task_name": self.task_name,
            "base_freq": self.base_freq,
            "symbols": self.symbols,
            "files_position": files_position,
            "candidate_signals": self.candidate_signals,
            "market": self.kwargs.get("market", "默认"),
            "bg_max_count": self.kwargs.get("bg_max_count", 5000),
        }
        if self.kwargs.get("sdt"):
            # 仅当用户显式指定 sdt 时才下发，避免覆盖 Rust 端的默认值。
            cfg["sdt"] = self.kwargs["sdt"]
        result = run_optimize_batch(bars_dir, cfg, self.results_root, n_threads=n_jobs)
        # 暴露 Rust 端返回的执行信息，方便上层日志记录或失败诊断。
        self.message = result.message
        return result

    def _materialize_bars_dir(self):
        """将所有标的的 K 线序列写入 parquet 文件并返回所在目录。

        Returns:
            包含 ``<symbol>.parquet`` 文件的目录路径，供 Rust 引擎扫描读取。
        """
        bars_dir = Path(self.results_path) / "bars"
        bars_dir.mkdir(parents=True, exist_ok=True)
        # 默认时间范围与历史版本保持一致；用户可通过 kwargs 自定义覆盖。
        bar_sdt = self.kwargs.get("bar_sdt", "20150101")
        bar_edt = self.kwargs.get("bar_edt", "20220101")
        for symbol in self.symbols:
            bars = _read_bars(self.read_bars, symbol, self.base_freq, bar_sdt, bar_edt)
            # parquet 不写 index，Rust 端按列名读取，避免歧义。
            bars_to_dataframe(bars, symbol=symbol).to_parquet(bars_dir / f"{symbol}.parquet", index=False)
        return bars_dir

    def _materialize_position_files(self):
        """把每份基准仓位 JSON 转换为 runtime 格式后写入磁盘。

        Returns:
            ``list[str]``：转换后落盘的仓位 JSON 文件绝对路径列表。
        """
        out_dir = Path(self.results_path) / "positions_input"
        out_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for file in self.files_position:
            payload = json.loads(Path(file).read_text(encoding="utf-8"))
            # PR-4：Rust 端 Position load 已经能识别两种 signal 字段写法，
            # 直接使用持久化 dump 作为运行时结构即可。
            runtime = payload
            # 移除回测/校验类字段，避免 Rust 端误用历史结果污染本次优化。
            runtime.pop("md5", None)
            runtime.pop("pairs", None)
            runtime.pop("holds", None)
            # symbol 字段在批量优化场景被忽略，但 Rust 端要求必填，给个占位。
            runtime.setdefault("symbol", "symbol")
            out_path = out_dir / Path(file).name
            # 使用 ensure_ascii=False 保留中文字段，便于人工查看。
            out_path.write_text(json.dumps(runtime, ensure_ascii=False), encoding="utf-8")
            files.append(str(out_path))
        return files


class ExitsOptimize:
    """平仓参数批量优化的 Python 外观类。

    设计与 :class:`OpensOptimize` 对称：候选事件先在 Python 侧通过兼容层
    归一化，再连同 K 线、基准持仓等一起交给 Rust 端的批量优化引擎执行。

    Attributes:
        version: 当前 ExitsOptimize 实现的版本标识符。
        read_bars: 用户传入的 K 线读取函数。
        kwargs: 用户提供的全部配置项的浅拷贝。
        symbols: 标的代码列表（保留原始顺序）。
        files_position: 待优化的基准持仓配置文件列表。
        task_name: 任务名称，用于结果目录命名。
        candidate_events: 归一化后的候选平仓事件列表。
        base_freq: 基础 K 线周期，未提供时通过策略类自动推导。
        results_root: 结果输出根目录。
        task_hash: 由候选事件 + 标的列表生成的 8 位 MD5 任务哈希。
        results_path: 当前任务的结果输出目录（含哈希后缀）。
        poss_path: 当前任务的持仓快照子目录路径。
        message: ``execute`` 完成后填充，记录 Rust 端返回的信息。
    """

    def __init__(self, read_bars: Callable, **kwargs):
        """保存配置并预计算任务哈希、输出目录等元信息。

        Args:
            read_bars: 用户提供的 K 线读取函数，签名详见 :func:`_read_bars`。
            **kwargs: 任务配置；至少需要包含 ``symbols``、``files_position``、
                ``candidate_events``、``results_path`` 等键；可选项与
                :class:`OpensOptimize` 类似。

        Notes:
            未显式提供 ``base_freq`` 时，会临时构造一个 :class:`CzscExitOptimStrategy`
            实例从其 ``base_freq`` 属性中推导。
        """
        self.version = "ExitsOptimizeV230924"
        self.read_bars = read_bars
        self.kwargs = dict(kwargs)
        self.symbols = list(kwargs["symbols"])
        self.files_position = [str(x) for x in kwargs["files_position"]]
        self.task_name = kwargs.get("task_name", "出场优化")
        # 候选事件首先在 Python 侧统一归一化，下游 Rust 端拿到的结构稳定。
        self.candidate_events = normalize_candidate_events(kwargs["candidate_events"])
        # 与 OpensOptimize 对称：未显式指定 base_freq 时通过策略类反推。
        self.base_freq = (
            kwargs.get("base_freq")
            or CzscExitOptimStrategy(
                symbol="symbol",
                files_position=self.files_position,
                candidate_events=self.candidate_events,
            ).base_freq
        )
        self.results_root = Path(kwargs["results_path"])
        # 候选事件用 JSON 化字符串再做 MD5，避免 dict 不同顺序导致哈希漂移。
        self.task_hash = _md5_upper8(f"{_py_repr_json(self.candidate_events)}_{_py_repr_list_str(self.symbols)}")
        self.results_path = str(self.results_root / f"{self.task_name}_{self.task_hash}")
        self.poss_path = str(Path(self.results_path) / "poss")

    def execute(self, n_jobs=1):
        """物化输入数据并触发 Rust 端的平仓批量优化任务。

        Args:
            n_jobs: 传给 Rust 引擎的并发线程数；默认为 1（顺序执行）。

        Returns:
            Rust 引擎返回的结果对象；执行信息同时缓存到 ``self.message``。
        """
        bars_dir = self._materialize_bars_dir()
        files_position = self._materialize_position_files()
        # optim_type 标记为平仓优化；其余字段与 OpensOptimize.execute 类似，
        # 但传入的是 candidate_events 而非 candidate_signals。
        cfg = {
            "optim_type": "exit",
            "task_name": self.task_name,
            "base_freq": self.base_freq,
            "symbols": self.symbols,
            "files_position": files_position,
            "candidate_events": self.candidate_events,
            "market": self.kwargs.get("market", "默认"),
            "bg_max_count": self.kwargs.get("bg_max_count", 5000),
        }
        if self.kwargs.get("sdt"):
            cfg["sdt"] = self.kwargs["sdt"]
        result = run_optimize_batch(bars_dir, cfg, self.results_root, n_threads=n_jobs)
        self.message = result.message
        return result

    def _materialize_bars_dir(self):
        """将所有标的的 K 线序列写入 parquet 文件并返回所在目录。

        Returns:
            包含 ``<symbol>.parquet`` 文件的目录路径，供 Rust 引擎扫描读取。
        """
        bars_dir = Path(self.results_path) / "bars"
        bars_dir.mkdir(parents=True, exist_ok=True)
        bar_sdt = self.kwargs.get("bar_sdt", "20150101")
        bar_edt = self.kwargs.get("bar_edt", "20220101")
        for symbol in self.symbols:
            bars = _read_bars(self.read_bars, symbol, self.base_freq, bar_sdt, bar_edt)
            bars_to_dataframe(bars, symbol=symbol).to_parquet(bars_dir / f"{symbol}.parquet", index=False)
        return bars_dir

    def _materialize_position_files(self):
        """把每份基准仓位 JSON 转换为 runtime 格式后写入磁盘。

        Returns:
            ``list[str]``：转换后落盘的仓位 JSON 文件绝对路径列表。
        """
        out_dir = Path(self.results_path) / "positions_input"
        out_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for file in self.files_position:
            payload = json.loads(Path(file).read_text(encoding="utf-8"))
            # PR-4：Rust 端 Position load 已经能识别两种 signal 字段写法，直接透传。
            runtime = payload
            runtime.pop("md5", None)
            runtime.pop("pairs", None)
            runtime.pop("holds", None)
            runtime.setdefault("symbol", "symbol")
            out_path = out_dir / Path(file).name
            out_path.write_text(json.dumps(runtime, ensure_ascii=False), encoding="utf-8")
            files.append(str(out_path))
        return files
