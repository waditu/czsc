"""
Python 端策略研究流程的数据模型定义

本模块集中存放跨子模块共享的轻量数据载体（dataclass / TypedDict），
位于 czsc 顶层是为了避免子包之间循环引用，并便于上层业务直接 ``from czsc.models import ...``。

包含三类对象:
    - StrategyConfig:  策略配置 TypedDict，约束策略 JSON / dict 的字段集合
    - ResearchResult:  研究/回测的统一返回容器，承载 Arrow IPC 字节流并提供 DataFrame 视图
    - ReplayResult:    单标的回放的返回容器，与 ResearchResult 同构（仅类型语义不同）
    - OptimizeResult:  参数优化运行的元信息容器
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict

from czsc._utils._df_convert import arrow_bytes_to_pd_df


class StrategyConfig(TypedDict, total=False):
    """
    策略配置的 TypedDict 契约

    用于类型标注与 IDE 补全，让"用 dict 描述一个策略"的写法获得静态检查保护。
    所有字段都是可选的（``total=False``），具体校验由 Rust 端按字段名读取并报错。

    字段说明:
        name           - 策略名称（用于日志/产物目录命名）
        symbol         - 标的代码
        base_freq      - 基础周期（如 ``"30分钟"``）
        signals_module - 信号实现所在的 Python 模块路径，用于 short-name 解析
        signals_config - 信号配置列表，每项形如 ``{"name": ..., "freq": ..., "params": {...}}``
        positions      - 持仓配置列表，每项是一个 Position 的 JSON dump
        market         - 市场标识（如 "A股"/"期货"），影响交易日、夜盘判断等
        bg_max_count   - BarGenerator 的最大缓冲根数
        sdt            - 起始日期（``YYYYMMDD`` 或 ``YYYY-MM-DD``）
        include_sdt_bar - 是否把 sdt 当日的首根 K 线纳入信号计算
    """

    name: str
    symbol: str
    base_freq: str
    signals_module: str
    signals_config: list[dict[str, Any]]
    positions: list[dict[str, Any]]
    market: str
    bg_max_count: int
    sdt: str
    include_sdt_bar: bool


@dataclass
class ResearchResult:
    """
    通用研究/回测结果容器

    设计要点:
        - 三类核心数据（信号/成对交易/持仓）以 Arrow IPC 字节流形式持有，
          延后到 ``*_df()`` 调用时才反序列化为 DataFrame，避免在跨进程
          /跨语言传输时不必要的对象化开销
        - 同时保留对应的 ``*_path`` 字段，方便上层把结果落盘后只回传路径，
          字节流字段可置空（视调用模式而定）
        - meta 携带策略名、标的、参数、时间窗等元信息，用于结果归档与索引

    字段:
        meta          - 任意 dict 形式的元信息
        signals_arrow - 信号表的 Arrow 字节流
        pairs_arrow   - 成对交易表（成对开平仓配对）的 Arrow 字节流
        holds_arrow   - 持仓时序表的 Arrow 字节流
        signals_path  - 信号表对应的本地路径（可选）
        pairs_path    - 成对交易表对应的本地路径（可选）
        holds_path    - 持仓表对应的本地路径（可选）
    """

    meta: dict[str, Any]
    signals_arrow: bytes
    pairs_arrow: bytes
    holds_arrow: bytes
    signals_path: str | None = None
    pairs_path: str | None = None
    holds_path: str | None = None

    def signals_df(self):
        """将 ``signals_arrow`` 反序列化为 Pandas DataFrame（按需调用，避免无谓开销）"""
        return arrow_bytes_to_pd_df(self.signals_arrow)

    def pairs_df(self):
        """将 ``pairs_arrow`` 反序列化为 Pandas DataFrame"""
        return arrow_bytes_to_pd_df(self.pairs_arrow)

    def holds_df(self):
        """将 ``holds_arrow`` 反序列化为 Pandas DataFrame"""
        return arrow_bytes_to_pd_df(self.holds_arrow)


@dataclass
class ReplayResult(ResearchResult):
    """
    单标的回放的结果容器

    结构与 :class:`ResearchResult` 完全一致，单独定义子类的目的是在调用方
    代码与日志中体现语义差异（"复现某次回放"对应 ReplayResult，"批量研究
    多组参数"对应 ResearchResult）。
    """

    pass


@dataclass
class OptimizeResult:
    """
    参数优化运行的元信息容器

    当前仅持有一个 ``message`` 字段，用于承载 Rust 端返回的简要状态描述
    （成功概要 / 警告 / 错误信息）。后续若需要扩展更结构化的优化指标
    （如最优参数、得分排序等），可在此追加字段，保持向后兼容。
    """

    message: str
