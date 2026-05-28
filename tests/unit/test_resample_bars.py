"""``resample_bars`` 重采样行为单元测试。

业务背景：
    ``czsc.resample_bars`` 是把基础周期 K 线聚合到目标周期的入口。
    本次将历史 Python 实现下沉到 Rust（``crates/czsc-utils/src/resample.rs``），
    Python 端仅保留 DataFrame ↔ list[RawBar] 边界胶水。

测试覆盖：
    - 顶层 ``czsc.resample_bars`` 是 Python wrapper（区别于 ``czsc._native.resample_bars``）；
    - DataFrame 输入 / list[RawBar] 输入两条路径在等价输入下产生相同输出；
    - ``raw_bars=False`` 返回 DataFrame，列序对齐标准 8 列；空结果保留 8 列 schema；
    - 1min→5min OHLCV 聚合数值与历史 Python 公式（first/last/max/min/sum/sum）一致；
    - 1min→日线 把同一交易日所有 1 分钟 bar 聚合成 1 根日线，并显式记录
      drop_unfinished 对非分钟 target 的 no-op 已知限制；
    - drop_unfinished=True 丢掉未到桶边界的尾部 5min 桶（含 OHLC 全字段验证）；
      drop_unfinished=False 保留之；
    - 空输入 → 空输出；
    - **fail-loud**：混合 symbol / 混合 freq / 重复 dt / 乱序 dt 必须显式 Err；
    - 非法入参类型（polars-like / numpy-like / 整数）应抛清晰 TypeError。
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import pytest

import czsc
from czsc import Freq, RawBar, resample_bars
from czsc._native import resample_bars as _resample_bars_native


def _make_ashare_1min_bars(n: int) -> list[RawBar]:
    """构造从 2024-12-12 09:31 起的 n 根连续 A 股 1 分钟 K 线（无午休跨越）。"""
    base = datetime(2024, 12, 12, 9, 31)
    bars = []
    for i in range(n):
        price = 100.0 + i
        bars.append(
            RawBar(
                symbol="000001.XSHG",
                dt=base + timedelta(minutes=i),
                freq=Freq.F1,
                open=price,
                close=price + 0.1,
                high=price + 0.5,
                low=price - 0.5,
                vol=1_000.0 * (i + 1),
                amount=10_000.0 * (i + 1),
                id=i,
            )
        )
    return bars


def _bars_to_df(bars: list[RawBar]) -> pd.DataFrame:
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
            for b in bars
        ]
    )


# ---------------------------------------------------------------------------
# 透传契约
# ---------------------------------------------------------------------------


def test_top_level_is_python_wrapper_not_native():
    """``czsc.resample_bars`` 必须是 Python wrapper（与 ``_native.resample_bars`` 区分），
    不能被 lazy 重定向成 native 实体——否则 DataFrame 入参路径会被旁路。"""
    from czsc import _resample_bars as _wrapper_module

    assert czsc.resample_bars is _wrapper_module.resample_bars
    assert czsc.resample_bars is not _resample_bars_native
    # native 也要确实存在，且与 wrapper 不是同一对象
    assert callable(_resample_bars_native)


# ---------------------------------------------------------------------------
# 正常 OHLCV 聚合
# ---------------------------------------------------------------------------


def test_empty_input_returns_empty_list():
    assert resample_bars([], Freq.F5) == []


def test_one_minute_to_five_minute_ohlcv_aggregation():
    """5 根连续 1 分钟（09:31..09:35） → 1 根 5 分钟（09:35），
    OHLCV 字段必须等于 first/last/max/min/sum/sum。"""
    bars = _make_ashare_1min_bars(5)
    out = resample_bars(bars, Freq.F5)
    assert len(out) == 1
    bar = out[0]
    assert bar.dt == datetime(2024, 12, 12, 9, 35)
    assert bar.freq == Freq.F5
    assert bar.open == bars[0].open
    assert bar.close == bars[-1].close
    assert bar.high == max(b.high for b in bars)
    assert bar.low == min(b.low for b in bars)
    assert bar.vol == sum(b.vol for b in bars)
    assert bar.amount == sum(b.amount for b in bars)


def test_drop_unfinished_drops_partial_tail_bucket():
    """7 根 1 分钟（09:31..09:37）跨两个 5 分钟桶 [09:35, 09:40)。
    drop_unfinished=True 丢掉未到 09:40 边界的尾桶；False 保留之，
    且未完成桶的 open/close/high/low/vol/amount 都要等于子集聚合结果。"""
    bars = _make_ashare_1min_bars(7)

    kept = resample_bars(bars, Freq.F5, drop_unfinished=True)
    assert [b.dt for b in kept] == [datetime(2024, 12, 12, 9, 35)]

    all_ = resample_bars(bars, Freq.F5, drop_unfinished=False)
    assert [b.dt for b in all_] == [
        datetime(2024, 12, 12, 9, 35),
        datetime(2024, 12, 12, 9, 40),
    ]
    # 未完成桶只聚合最后两根 1 分钟（09:36、09:37）—— OHLCV 全字段覆盖
    partial = all_[1]
    assert partial.open == bars[5].open
    assert partial.close == bars[6].close
    assert partial.high == max(bars[5].high, bars[6].high)
    assert partial.low == min(bars[5].low, bars[6].low)
    assert partial.vol == bars[5].vol + bars[6].vol
    assert partial.amount == bars[5].amount + bars[6].amount


def test_one_minute_to_daily_known_limitation_drop_unfinished_is_noop():
    """drop_unfinished 对非分钟 target 是 no-op（freq_end_time 返回日界 00:00:00
    < intraday dt 的比较恒为假），所以 1min→日线 即便未到收盘也会输出 1 根。
    这是已知限制，由 Rust 端 freq_end_time 的非分钟返回口径决定，参见
    ``crates/czsc-utils/src/resample.rs`` 模块级 docstring。"""
    bars = _make_ashare_1min_bars(3)
    out = resample_bars(bars, Freq.D, drop_unfinished=True)
    assert len(out) == 1
    assert out[0].freq == Freq.D
    assert out[0].dt == datetime(2024, 12, 12)
    assert out[0].open == bars[0].open
    assert out[0].close == bars[-1].close


# ---------------------------------------------------------------------------
# 两种入参路径等价
# ---------------------------------------------------------------------------


def test_dataframe_input_equivalent_to_bars_input():
    """DataFrame 与 list[RawBar] 在等价输入下应产生完全一致的聚合结果。"""
    bars = _make_ashare_1min_bars(10)
    df = _bars_to_df(bars)

    from_list = resample_bars(bars, Freq.F5)
    from_df = resample_bars(df, Freq.F5, base_freq=Freq.F1)

    assert len(from_list) == len(from_df)
    for a, b in zip(from_list, from_df, strict=True):
        assert a.dt == b.dt
        assert a.open == b.open
        assert a.close == b.close
        assert a.high == b.high
        assert a.low == b.low
        assert a.vol == b.vol
        assert a.amount == b.amount


def test_raw_bars_false_returns_dataframe_with_standard_columns():
    """raw_bars=False 时返回 DataFrame，列顺序与标准 8 列对齐。"""
    bars = _make_ashare_1min_bars(10)
    df = _bars_to_df(bars)

    out = resample_bars(df, Freq.F5, raw_bars=False, base_freq=Freq.F1)
    assert isinstance(out, pd.DataFrame)
    expected = ("symbol", "dt", "open", "close", "high", "low", "vol", "amount")
    assert tuple(out.columns) == expected, "列序应当与 _OUTPUT_COLUMNS 一致"
    assert len(out) == 2  # 09:35 + 09:40 两个桶


def test_raw_bars_false_empty_input_preserves_schema():
    """空结果 + raw_bars=False 必须返回 8 列 + 与非空一致 dtype 的空 DataFrame。

    若退化成 ``pd.DataFrame([])``：0 列引发下游 ``df['dt']`` KeyError。
    若 dtype 全 ``object``：``df['dt'].dt.year`` 抛 AttributeError，
    且 ``pd.concat([empty, full])`` 把 OHLCV 列降级成 object。
    """
    out = resample_bars([], Freq.F5, raw_bars=False)
    assert isinstance(out, pd.DataFrame)
    assert len(out) == 0
    assert tuple(out.columns) == (
        "symbol",
        "dt",
        "open",
        "close",
        "high",
        "low",
        "vol",
        "amount",
    )
    # dtype 与非空路径对齐：symbol object / dt datetime64[ns] / OHLCV float64
    assert str(out["symbol"].dtype) == "object"
    assert str(out["dt"].dtype) == "datetime64[ns]"
    for col in ("open", "close", "high", "low", "vol", "amount"):
        assert str(out[col].dtype) == "float64", f"{col} dtype 应当是 float64"
    # 空 dt 列也应当能用 .dt accessor，证明 dtype 真的是 datetime64[ns]
    _ = out["dt"].dt  # noqa: B018  — 不抛 AttributeError 即通过


def test_target_freq_accepts_string():
    """``target_freq`` 接受中文周期字符串（在 Rust 端解析），与历史调用兼容。"""
    bars = _make_ashare_1min_bars(5)
    out_enum = resample_bars(bars, Freq.F5)
    out_str = resample_bars(bars, "5分钟")
    assert len(out_enum) == len(out_str) == 1
    assert out_enum[0].dt == out_str[0].dt


@pytest.mark.parametrize(
    ("target_freq", "expected_count"),
    [
        (Freq.F1, 5),  # base == target → 数量不变
        (Freq.F5, 1),  # 5 根 1 分钟恰好一根 5 分钟
    ],
)
def test_count_matches_target_bucket(target_freq, expected_count):
    bars = _make_ashare_1min_bars(5)
    assert len(resample_bars(bars, target_freq)) == expected_count


# ---------------------------------------------------------------------------
# Fail-loud 入参校验
# ---------------------------------------------------------------------------


def test_mixed_symbol_input_raises():
    """混合 symbol 的 list[RawBar] 必须显式 ValueError（不可静默串行聚合）。"""
    bars = _make_ashare_1min_bars(3)
    bars[1] = RawBar(
        symbol="OTHER.XSHG",
        dt=bars[1].dt,
        freq=bars[1].freq,
        open=bars[1].open,
        close=bars[1].close,
        high=bars[1].high,
        low=bars[1].low,
        vol=bars[1].vol,
        amount=bars[1].amount,
        id=bars[1].id,
    )
    with pytest.raises(ValueError, match="symbol"):
        resample_bars(bars, Freq.F5)


def test_mixed_freq_input_raises():
    """混合 freq 的 list[RawBar] 必须显式报错，错误信息点名 freq。"""
    bars = _make_ashare_1min_bars(3)
    bars[1] = RawBar(
        symbol=bars[1].symbol,
        dt=bars[1].dt,
        freq=Freq.F5,  # 故意改成 F5
        open=bars[1].open,
        close=bars[1].close,
        high=bars[1].high,
        low=bars[1].low,
        vol=bars[1].vol,
        amount=bars[1].amount,
        id=bars[1].id,
    )
    with pytest.raises(ValueError, match="freq"):
        resample_bars(bars, Freq.F5)


def test_duplicate_dt_input_raises():
    """重复 dt 必须显式报错——BarGenerator 流式 API 的 silent dedup
    在 batch 模式下不可接受。"""
    bars = _make_ashare_1min_bars(3)
    bars[2] = RawBar(
        symbol=bars[2].symbol,
        dt=bars[1].dt,  # 与 bars[1] 完全相同
        freq=bars[2].freq,
        open=bars[2].open,
        close=bars[2].close,
        high=bars[2].high,
        low=bars[2].low,
        vol=bars[2].vol,
        amount=bars[2].amount,
        id=bars[2].id,
    )
    with pytest.raises(ValueError, match="重复"):
        resample_bars(bars, Freq.F5)


def test_out_of_order_dt_input_raises():
    """乱序 dt 必须显式报错，避免静默错合并。"""
    bars = _make_ashare_1min_bars(3)
    bars[1], bars[2] = bars[2], bars[1]  # 交换次序
    with pytest.raises(ValueError, match="乱序"):
        resample_bars(bars, Freq.F5)


def test_nan_ohlcv_input_raises():
    """OHLCV 任一字段含 NaN 必须显式报错——历史 BarGenerator `last + bar`
    会让 NaN 沿桶传染，与历史 pandas sum(skipna=True) 不一致。"""
    for field in ("open", "close", "high", "low", "vol", "amount"):
        bars = _make_ashare_1min_bars(3)
        kwargs = {
            "symbol": bars[1].symbol,
            "dt": bars[1].dt,
            "freq": bars[1].freq,
            "open": bars[1].open,
            "close": bars[1].close,
            "high": bars[1].high,
            "low": bars[1].low,
            "vol": bars[1].vol,
            "amount": bars[1].amount,
            "id": bars[1].id,
        }
        kwargs[field] = float("nan")
        bars[1] = RawBar(**kwargs)
        with pytest.raises(ValueError, match=field):
            resample_bars(bars, Freq.F5)


def test_tz_aware_dt_raises_at_rawbar_boundary():
    """tz-aware datetime 必须被 RawBar 构造器拒绝，错误信息引导 tz_localize(None)，
    防止 .timestamp() 把 09:31 Asia/Shanghai 静默转成 01:31 UTC 引发桶错位。"""
    from datetime import timezone

    with pytest.raises(ValueError, match="tz-naive"):
        RawBar(
            symbol="000001.XSHG",
            dt=datetime(2024, 12, 12, 9, 31, tzinfo=timezone.utc),
            freq=Freq.F1,
            open=100.0,
            close=100.1,
            high=100.5,
            low=99.5,
            vol=1000.0,
            amount=10000.0,
            id=0,
        )


def test_tz_aware_dataframe_raises():
    """tz-aware DataFrame 经 format_standard_kline → RawBar 构造时同样被拒绝。"""
    bars = _make_ashare_1min_bars(3)
    df = _bars_to_df(bars)
    df["dt"] = df["dt"].dt.tz_localize("Asia/Shanghai")
    with pytest.raises(ValueError, match="tz-naive"):
        resample_bars(df, Freq.F5, base_freq=Freq.F1)


def test_unsupported_input_type_raises_typeerror():
    """非 pandas.DataFrame / list / tuple 的输入应抛清晰 TypeError，
    避免 PyO3 边界抛晦涩的类型抽取错误。"""

    class FakePolarsDF:
        """模拟 polars.DataFrame：实现 __iter__ 返回列名，但不是 pd.DataFrame。"""

        def __iter__(self):
            return iter(["symbol", "dt", "open"])

    with pytest.raises(TypeError, match="不支持的输入类型"):
        resample_bars(FakePolarsDF(), Freq.F5)

    with pytest.raises(TypeError, match="不支持的输入类型"):
        resample_bars(42, Freq.F5)  # type: ignore[arg-type]
