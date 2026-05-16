"""
Rust/Python 运行时适配层（Runtime Adapters）

把 Python 端用户层的 ``dict`` / ``list`` / ``RawBar`` 等结构，转换为 Rust 后端
（``czsc._native``）期望的运行时格式。

PR-2 / PR-4 之后，原先位于本模块的 ``signal_config_to_runtime`` 与
``position_dump_to_runtime`` 已被 Rust 端的归一化逻辑替代（前者吸收进
``derive_signals_config``，后者通过 ``Signal::Deserialize`` 同时接受
字符串与 ``{key, value}`` 字典形态），不再需要 Python 端转换。

当前仅保留**被 2+ 处生产代码共享**的边界胶水：

- :mod:`czsc.research`         —— ``normalize_candidate_events``
- :mod:`czsc.strategies`       —— ``sort_freqs`` / ``bars_to_dataframe``
- :mod:`czsc.traders.optimize` —— ``bars_to_dataframe`` / ``normalize_candidate_event``
- :func:`czsc.utils.freqs_sorted` —— 间接调用 ``sort_freqs``

设计原则：

- 所有转换函数无副作用，输入不可变（统一通过 ``dict(x)`` / ``list(x)`` 复制）
- 字段缺失走"宽进严出"策略：能用默认值兜底就兜底，无法兜底就显式 raise
- 仅依赖 stdlib 与 pandas，保持适配层最小内聚
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import pandas as pd

# 周期字符串到排序权重的映射表
# 数字越小代表越小级别（越高频），按此权重做稳定排序后，
# 同一策略中"小周期 -> 大周期"的展示顺序与缠论惯例一致。
# 未在本表中的周期会被赋值 10_000，并用字面量做次级排序兜底。
_FREQ_ORDER = {
    "Tick": 0,
    "逐笔": 0,
    "1分钟": 1,
    "2分钟": 2,
    "3分钟": 3,
    "4分钟": 4,
    "5分钟": 5,
    "6分钟": 6,
    "10分钟": 7,
    "12分钟": 8,
    "15分钟": 9,
    "20分钟": 10,
    "30分钟": 11,
    "60分钟": 12,
    "120分钟": 13,
    "240分钟": 14,
    "360分钟": 15,
    "日线": 16,
    "周线": 17,
    "月线": 18,
    "季线": 19,
    "年线": 20,
}


def sort_freqs(freqs: Iterable[str]) -> list[str]:
    """按缠论惯用顺序对周期字符串去重并排序

    :param freqs: 任意可迭代的周期字符串集合（允许包含 None / 空串，会被过滤）
    :return: 从高频到低频依次排列的去重后的周期字符串列表

    备注：
        - 未登记的周期会被排到末尾（权重 10_000），并按字典序作次级排序
        - 排序结果稳定，方便用于 UI 展示与日志输出对齐
    """
    unique = {str(x) for x in freqs if x}
    return sorted(unique, key=lambda x: (_FREQ_ORDER.get(x, 10_000), x))


def bars_to_dataframe(bars: Any, symbol: str | None = None) -> pd.DataFrame:
    """将多种形式的 K 线表示统一转换为 Rust IPC 读取器期望的 DataFrame

    支持的输入：

    - ``pd.DataFrame`` —— 直接拷贝并补齐缺失列
    - ``list[RawBar]`` / ``tuple[RawBar]`` —— 通过 getattr 读取属性逐行构造

    输出契约（必须严格满足，否则 Rust 端反序列化会报错）::

        列顺序：["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]
        类型：
            symbol -> str
            dt     -> datetime64[ns]
            其余 6 列 -> float64
        清洗：
            - 任一关键列为 NaN 的行会被丢弃
            - 同一时间戳重复时保留最后一条（last write wins）
            - 按 dt 升序排列、重置索引

    :param bars: K 线集合（DataFrame 或 RawBar 列表）
    :param symbol: 当 bars 中缺少 symbol 列或部分缺失时用于回填的标的代码
    :return: 规范化后的 DataFrame，可直接传入 Rust IPC 读取通道
    :raises TypeError: bars 类型不在支持列表中
    :raises ValueError: 缺少必需列（dt 或转换后仍然缺失的其他列）
    """
    if isinstance(bars, pd.DataFrame):
        out = bars.copy()
    elif isinstance(bars, (list, tuple)):
        # 遍历对象列表，按字段名取值；缺失字段则使用 None 占位，后续 dropna 兜底
        rows = []
        for bar in bars:
            rows.append(
                {
                    "symbol": getattr(bar, "symbol", symbol),
                    "dt": getattr(bar, "dt", None),
                    "open": getattr(bar, "open", None),
                    "close": getattr(bar, "close", None),
                    "high": getattr(bar, "high", None),
                    "low": getattr(bar, "low", None),
                    "vol": getattr(bar, "vol", None),
                    "amount": getattr(bar, "amount", None),
                }
            )
        out = pd.DataFrame(rows)
    else:
        raise TypeError(f"unsupported bars type: {type(bars)!r}")

    # 兜底补齐 symbol 列：完全缺失就整列填充；部分缺失（NaN）就用 fillna 回填
    if "symbol" not in out.columns:
        out["symbol"] = symbol
    elif symbol:
        out["symbol"] = out["symbol"].fillna(symbol)

    # dt 是核心字段，必须存在；缺失意味着源数据本身有问题，立即报错
    if "dt" not in out.columns:
        raise ValueError("bars is missing dt column")

    # amount（成交额）允许由 vol*close 推算得出，方便上游只提供成交量的场景
    if "amount" not in out.columns:
        out["amount"] = out["vol"] * out["close"]

    # 二次校验：所有必需列必须齐全
    required = ["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]
    missing = [col for col in required if col not in out.columns]
    if missing:
        raise ValueError(f"bars is missing columns: {missing}")

    out = out[required].copy()
    out["dt"] = pd.to_datetime(out["dt"])
    out["symbol"] = out["symbol"].astype(str)
    for col in ["open", "close", "high", "low", "vol", "amount"]:
        # 强制转 float64：Rust IPC 读取器要求六个数值列均为 Float64；
        # 而 wbt 提供的 mock 数据中 vol 默认是 int64，不显式转换会导致类型错误
        out[col] = pd.to_numeric(out[col], errors="coerce").astype("float64")
    # 删除关键字段缺失的脏行，按 dt 升序去重并重置索引
    out = out.dropna(subset=["dt", "open", "close", "high", "low", "vol", "amount"])
    out = out.sort_values("dt").drop_duplicates(subset=["dt"], keep="last").reset_index(drop=True)
    return out


def normalize_candidate_event(event: dict[str, Any]) -> dict[str, Any]:
    """将一个候选 Event 字典归一化为标准结构

    历史上 Event 配置出现过两种风格：

    1. 旧风格：信号关系字段位于 ``factors[0]`` 子节点中
    2. 新风格：信号关系字段直接在 Event 顶层

    本函数统一两种写法，输出固定结构，便于上游统一处理::

        {
            "name": str,            # Event 名称（缺失时退回到 factors[0].name；再缺失为空串）
            "operate": str,         # 操作类型（必须存在，否则触发 KeyError）
            "signals_all": list,    # 必须全部命中
            "signals_any": list,    # 至少一个命中
            "signals_not": list,    # 必须全部不命中
        }

    :param event: 任意风格的候选事件 dict
    :return: 标准化后的浅拷贝 dict
    """
    raw = dict(event)
    # 取出旧风格的 factors[0]，若存在则其内的信号字段作为退路
    factors = list(raw.get("factors") or [])
    factor = dict(factors[0]) if factors else {}

    # "顶层优先、factor 兜底"的取值策略，兼容两种风格
    signals_all = list(raw.get("signals_all") or factor.get("signals_all") or [])
    signals_any = list(raw.get("signals_any") or factor.get("signals_any") or [])
    signals_not = list(raw.get("signals_not") or factor.get("signals_not") or [])
    name = raw.get("name") or factor.get("name") or ""

    return {
        "name": name,
        "operate": raw["operate"],
        "signals_all": signals_all,
        "signals_any": signals_any,
        "signals_not": signals_not,
    }


def normalize_candidate_events(events: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量调用 :func:`normalize_candidate_event`，返回标准化后的事件列表"""
    return [normalize_candidate_event(event) for event in events]


