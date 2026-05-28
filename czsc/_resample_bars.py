"""
公开 API ``resample_bars`` 的 Python 包装实现。

边界胶水：
    DataFrame ↔ ``list[RawBar]`` 的转换在 Rust/PyO3 类型系统里跨不过去，
    必须在 Python 端做。真正的桶聚合 + 入参校验 (同 symbol / 同 freq /
    严格递增 dt) 全部位于 Rust 端 ``crates/czsc-utils/src/resample.rs``，
    由 ``czsc._native.resample_bars`` 透传过来。

实现取舍：
    - DataFrame 输入：复用同仓库的 ``format_standard_kline``，与
      ``CZSC`` / ``CzscTrader`` 等入口保持一致的列约定与类型容忍度。
    - DataFrame 输出：``raw_bars=False`` 时把 ``list[RawBar]`` 拆回
      标准列布局；空结果保留 8 列空 schema（避免 ``pd.DataFrame([])``
      退化成 0 列产生的下游 KeyError）。
    - ``target_freq`` 的 ``str | Freq`` dual-input：解析在 Rust 端
      （与 ``BarGenerator`` 一致），Python 端不再额外做参数归一化。

已知限制：
    - ``drop_unfinished=True`` 对非分钟 target（D/W/M/S/Y）实际是 no-op，
      因为 Rust 端 ``freq_end_time`` 把日级以上桶 dt 归到 00:00:00。要修
      需重设计 ``freq_end_time`` 的非分钟返回口径，影响面外溢，留待
      单独 PR。

入参约束（fail-loud）：
    - ``dt`` 必须 **tz-naive**（``RawBar`` 构造器在 Rust 端拒绝 tz-aware，
      避免 ``.timestamp()`` 静默把 09:31 Asia/Shanghai 转成 01:31 UTC 引发
      桶边界错位）；DataFrame 入参请先 ``df['dt'].dt.tz_localize(None)``。
    - ``open/close/high/low/vol/amount`` 必须无 ``NaN``；Rust 端 ``last + bar``
      OHLCV 累加会让 NaN 污染整桶，与历史 pandas ``sum(skipna=True)`` 不一致，
      故 batch 模式直接拒绝 NaN 输入。
"""

from __future__ import annotations

import pandas as pd

from czsc._format_standard_kline import format_standard_kline
from czsc._native import Freq, RawBar
from czsc._native import resample_bars as _resample_bars_native

__all__ = ["resample_bars"]

# DataFrame 输出的固定列序，与 ``format_standard_kline`` 的输入约定对齐。
_OUTPUT_COLUMNS: tuple[str, ...] = (
    "symbol",
    "dt",
    "open",
    "close",
    "high",
    "low",
    "vol",
    "amount",
)


def resample_bars(
    df_or_bars: pd.DataFrame | list[RawBar],
    target_freq: Freq | str,
    raw_bars: bool = True,
    *,
    base_freq: Freq | str = Freq.F1,
    drop_unfinished: bool = True,
) -> list[RawBar] | pd.DataFrame:
    """将基础周期 K 线重采样为目标周期。

    参数:
        df_or_bars:  标准列布局的 ``pandas.DataFrame``（参见
                     ``format_standard_kline`` 的列约定），或 ``list[RawBar]``。
                     polars / pyarrow 等"非 pandas DataFrame"未受支持，会按
                     ``list[RawBar]`` 入口尝试解析并在 Rust 边界报错。
        target_freq: 目标周期，``Freq`` 枚举或中文周期字符串（如 ``"30分钟"``）。
        raw_bars:    True 返回 ``list[RawBar]``；False 返回 ``pandas.DataFrame``。
        base_freq:   基础周期。**当 ``df_or_bars`` 是 DataFrame 时必须与数据实际
                     周期一致**——它会被用作每根 RawBar 的 ``freq`` 标签，进而决定
                     Rust 端的市场推断与桶边界。默认 ``Freq.F1`` 仅向后兼容历史
                     调用方（其 DataFrame 一律为 1 分钟）。
                     传 ``list[RawBar]`` 时直接取 ``bars[0].freq``，本参数被忽略。
        drop_unfinished: 若最后一根 base bar 落在未到期边界的桶里，是否丢弃该桶。
                         **对非分钟 target 实际是 no-op（已知限制，见模块 docstring）。**

    返回:
        ``list[RawBar]`` 或 ``pandas.DataFrame``，由 ``raw_bars`` 决定。
        空结果 + ``raw_bars=False`` 返回一个保留 8 列 schema 的空 DataFrame。

    异常:
        ValueError: DataFrame 缺少必需列、base/target 周期解析失败，或
                    bars 列表违反 batch 不变量（混合 symbol / freq、重复或乱序 dt）。
    """
    # 严格分发：只接 pandas.DataFrame 或 list/tuple[RawBar]。
    # polars / numpy / pd.Series 等"也实现了 __iter__"的容器会被显式拒绝，
    # 避免它们落入 list(_) 路径产生 PyO3 端晦涩的类型抽取错误。
    if isinstance(df_or_bars, pd.DataFrame):
        bars = format_standard_kline(df_or_bars, freq=base_freq)
    elif isinstance(df_or_bars, (list, tuple)):
        bars = list(df_or_bars)
    else:
        raise TypeError(
            f"resample_bars: 不支持的输入类型 {type(df_or_bars).__name__}；"
            "请传 pandas.DataFrame 或 list[RawBar]（polars/numpy/Series 请先转换）"
        )

    out = _resample_bars_native(bars, target_freq, drop_unfinished)

    if raw_bars:
        return out

    if not out:
        # 空结果：保留 8 列 schema，避免 pd.DataFrame([]) 退化成 0 列
        # 引发下游 df["dt"] KeyError。
        return pd.DataFrame({col: pd.Series(dtype=object) for col in _OUTPUT_COLUMNS})

    return pd.DataFrame(
        [
            {
                "symbol": b.symbol,
                "dt": b.dt,
                "open": b.open,
                "close": b.close,
                "high": b.high,
                "low": b.low,
                "vol": b.vol,
                "amount": b.amount,
            }
            for b in out
        ],
        columns=list(_OUTPUT_COLUMNS),
    )
