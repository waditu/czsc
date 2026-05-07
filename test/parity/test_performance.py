"""性能对比测试：迁移后的 czsc vs 基线 rs_czsc。

每个测试在两套实现上跑相同的工作负载，对每个输入规模采样若干次，取
中位数耗时并打印 czsc/rs_czsc 的耗时比。``test_examples.py`` 已经覆盖
了输出等价性，本套件只关心性能回归。

耗时通过 ``capsys.disabled()`` 输出，确保在默认 pytest 输出里直接可见。
断言阈值故意设得比较宽松（``czsc <= 1.5x rs_czsc``）以避免抖动导致
CI 间歇性失败 —— 这部分主要是预警机制，而不是硬性卡口。
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

import pandas as pd


# 性能回归预算：czsc 不应慢于 rs_czsc 1.5 倍
PERF_RATIO_BUDGET = 1.5


def _format_standard_kline(module, df, freq):
    """对模块的 format_standard_kline 做一层轻封装，方便统一调用。"""
    return module.format_standard_kline(df, freq=freq)


def _build_long_short_position(module, symbol, base_freq):
    """构造 30分钟笔非多即空 / strategies 用到的多空两个开仓 Position。"""
    opens = [
        {
            "operate": "开多",
            "signals_all": [f"{base_freq}_D1_表里关系V230101_向上_任意_任意_0"],
            "signals_any": [],
            "signals_not": [f"{base_freq}_D1_涨跌停V230331_涨停_任意_任意_0"],
        },
        {
            "operate": "开空",
            "signals_all": [f"{base_freq}_D1_表里关系V230101_向下_任意_任意_0"],
            "signals_any": [],
            "signals_not": [f"{base_freq}_D1_涨跌停V230331_跌停_任意_任意_0"],
        },
    ]
    return module.Position(
        name=f"{base_freq}笔非多即空",
        symbol=symbol,
        opens=[module.Event.load(x) for x in opens],
        exits=[],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )


def _czsc_analyze_perf(module, bars):
    """测量 ``CZSC(bars)`` 构造路径的中位耗时（分析器热路径）。

    每次都强制访问 fx_list / bi_list 以确保惰性计算被触发。
    """
    samples = []
    for _ in range(3):
        start = time.perf_counter()
        c = module.CZSC(bars)
        # 触发分型 / 笔的物化计算
        _ = len(c.fx_list)
        _ = len(c.bi_list)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


def _backtest_perf(module, bars_df, freq, sdt, tmp_path):
    """测量 ``30分钟笔非多即空`` 类策略的 backtest 中位耗时。"""
    bars = _format_standard_kline(module, bars_df, freq)
    symbol = bars[0].symbol

    class Strat(module.CzscStrategyBase):
        @property
        def positions(self):
            return [_build_long_short_position(module, self.symbol, freq)]

    samples = []
    for run_idx in range(3):
        out_dir = tmp_path / f"run_{module.__name__}_{run_idx}"
        out_dir.mkdir(parents=True, exist_ok=True)
        tactic = Strat(symbol=symbol)
        start = time.perf_counter()
        tactic.backtest(bars, sdt=sdt)
        samples.append(time.perf_counter() - start)
    return statistics.median(samples)


# --------------------------------------------------------------------- #
# 测试 1 —— CZSC 分析器构造性能                                          #
# --------------------------------------------------------------------- #

def test_perf_czsc_analyzer(rs_czsc_module, czsc_module, mock_kline_df, capsys):
    """约 522 根日线下，``CZSC(bars)`` 分析器的耗时对比。

    测试目标：保证迁移后的 CZSC 构造路径不会显著慢于基线。

    关键断言：``czsc / rs_czsc`` 中位耗时比不超过 PERF_RATIO_BUDGET。
    """
    rs_bars = _format_standard_kline(rs_czsc_module, mock_kline_df, "日线")
    czsc_bars = _format_standard_kline(czsc_module, mock_kline_df, "日线")

    rs_t = _czsc_analyze_perf(rs_czsc_module, rs_bars)
    czsc_t = _czsc_analyze_perf(czsc_module, czsc_bars)

    ratio = czsc_t / rs_t if rs_t > 0 else float("inf")
    with capsys.disabled():
        print(
            f"\n[CZSC(522 daily bars)] rs_czsc={rs_t * 1000:.2f}ms "
            f"czsc={czsc_t * 1000:.2f}ms ratio={ratio:.2f}x"
        )
    # 这是宽松预算 —— 性能差异主要起到信息提示作用，而不是阻塞性的卡口
    assert ratio <= PERF_RATIO_BUDGET, (
        f"czsc analyzer is {ratio:.2f}x slower than rs_czsc baseline "
        f"({PERF_RATIO_BUDGET}x budget exceeded)"
    )


# --------------------------------------------------------------------- #
# 测试 2 —— 多种 K 线规模下的 backtest 性能                              #
# --------------------------------------------------------------------- #

def test_perf_backtest_scaling(rs_czsc_module, czsc_module, tmp_path, capsys):
    """30 分钟策略 backtest 在不同 K 线规模下的耗时对比。

    测试目标：确认 czsc 与 rs_czsc 在不同规模下的扩展特性接近，没有
    出现任何规模上的显著退化。

    测试场景：在三种规模下分别测量 backtest 耗时：
        * 约 5 个月  —— 起步规模
        * 约 18 个月 —— 中等规模
        * 约 4 年    —— 较大规模

    关键断言：每种规模下 czsc/rs_czsc 的耗时比都不能超过预算。
    """
    from wbt.mock import mock_symbol_kline

    # (起始日期, 结束日期) 三档：5 个月 / 18 个月 / 4 年
    sizes = [
        ("20210101", "20210601"),
        ("20200101", "20210601"),
        ("20180101", "20220101"),
    ]

    rows = []
    for sdt_data, edt_data in sizes:
        df = mock_symbol_kline("000001", "30分钟", sdt_data, edt_data, seed=42)
        df["dt"] = pd.to_datetime(df["dt"])
        # backtest 起始时间在数据起点之后 60 天，避免 warmup 期影响
        backtest_sdt = pd.to_datetime(sdt_data) + pd.Timedelta(days=60)
        backtest_sdt_str = backtest_sdt.strftime("%Y-%m-%d")

        rs_t = _backtest_perf(
            rs_czsc_module, df, "30分钟", backtest_sdt_str, tmp_path / "rs"
        )
        czsc_t = _backtest_perf(
            czsc_module, df, "30分钟", backtest_sdt_str, tmp_path / "czsc"
        )
        ratio = czsc_t / rs_t if rs_t > 0 else float("inf")
        rows.append((len(df), rs_t * 1000, czsc_t * 1000, ratio))

    with capsys.disabled():
        # 打印一张对照表
        print(f"\n[backtest scaling — 30min strategy]")
        print(f"  {'#bars':>6} | {'rs_czsc':>10} | {'czsc':>10} | {'ratio':>6}")
        print(f"  {'-' * 6} | {'-' * 10} | {'-' * 10} | {'-' * 6}")
        for n_bars, rs_ms, czsc_ms, r in rows:
            print(f"  {n_bars:>6} | {rs_ms:>8.2f}ms | {czsc_ms:>8.2f}ms | {r:>5.2f}x")

    # 只要任何一个规模超出预算就视为失败
    over_budget = [(n, r) for n, _, _, r in rows if r > PERF_RATIO_BUDGET]
    assert not over_budget, (
        f"backtest perf budget {PERF_RATIO_BUDGET}x exceeded at: {over_budget}"
    )


# --------------------------------------------------------------------- #
# 测试 3 —— derive_signals_config + run_research 端到端性能              #
# --------------------------------------------------------------------- #

def test_perf_run_research_endtoend(
    rs_czsc_module, czsc_module, mock_kline_df, sample_position_dict, capsys
):
    """``run_research(arrow_bytes, json)`` 的端到端性能对比。

    这是迁移后最关键的入口：把 Arrow 字节 + JSON 策略喂给 Rust 端，
    返回信号/pairs/holds 的 Arrow payload。

    关键断言：``czsc / rs_czsc`` 的中位耗时比不超过 PERF_RATIO_BUDGET。
    """
    from czsc._compat import (
        bars_to_dataframe,
        position_dump_to_runtime,
        signal_config_to_runtime,
    )
    from czsc._utils._df_convert import pandas_to_arrow_bytes

    df = bars_to_dataframe(mock_kline_df, symbol="000001")
    arrow_bytes = pandas_to_arrow_bytes(df)

    # 运行时策略只构造一次，两套实现共享同一份 JSON
    pos = czsc_module.Position.load(sample_position_dict)
    cfg = czsc_module.derive_signals_config(pos.unique_signals)
    strategy_json = json.dumps(
        {
            "name": "PerfStrategy",
            "symbol": "000001",
            "base_freq": "日线",
            "signals_module": "czsc.signals",
            "signals_config": [signal_config_to_runtime(c) for c in cfg],
            "positions": [position_dump_to_runtime(pos.dump(with_data=False))],
            "market": "默认",
            "bg_max_count": 5000,
        },
        ensure_ascii=False,
    )

    def _time(module, n=5):
        samples = []
        for _ in range(n):
            start = time.perf_counter()
            module._native.run_research(arrow_bytes, strategy_json, None, None)
            samples.append(time.perf_counter() - start)
        return statistics.median(samples)

    if hasattr(rs_czsc_module, "_rs_czsc"):
        # rs_czsc 的入口在 ``rs_czsc._rs_czsc`` 子模块上
        rs_native = rs_czsc_module._rs_czsc
    else:
        rs_native = rs_czsc_module._native

    samples_rs = []
    samples_czsc = []
    for _ in range(5):
        start = time.perf_counter()
        rs_native.run_research(arrow_bytes, strategy_json, None, None)
        samples_rs.append(time.perf_counter() - start)

        start = time.perf_counter()
        czsc_module._native.run_research(arrow_bytes, strategy_json, None, None)
        samples_czsc.append(time.perf_counter() - start)

    rs_t = statistics.median(samples_rs)
    czsc_t = statistics.median(samples_czsc)
    ratio = czsc_t / rs_t if rs_t > 0 else float("inf")
    with capsys.disabled():
        print(
            f"\n[run_research(522 bars, 1 position)] "
            f"rs_czsc={rs_t * 1000:.2f}ms czsc={czsc_t * 1000:.2f}ms "
            f"ratio={ratio:.2f}x"
        )

    assert ratio <= PERF_RATIO_BUDGET, (
        f"czsc.run_research is {ratio:.2f}x slower than rs_czsc baseline"
    )
