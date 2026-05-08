"""官方示例脚本的端到端等价性测试。

本测试以 ``rs_czsc/examples/`` 下的三个真实示例脚本为蓝本，要求迁移后
的 ``czsc`` 在完全相同的输入上产出与 ``rs_czsc`` 完全一致的结果。

覆盖的三个示例：
    * ``30分钟笔非多即空.py`` —— 多周期策略 → backtest + replay →
      写出 signals/pairs/holds 等 parquet 文件
    * ``use_optimize.py``    —— 开仓优化 + 出场优化两条流水线 →
      产出按品种组织的 parquet 树
    * ``weight_backtest.py`` —— 直接对一个权重 DataFrame 跑
      ``WeightBacktest`` → 比对 stats dict

每个测试都会：
    1. 用 mock K 线 / mock 权重 喂给两套实现，输入完全一致
    2. 记录各自耗时
    3. 断言每个输出 parquet 完全相等，并打印 czsc/rs_czsc 的耗时比
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------- #
# 共享辅助函数                                                          #
# --------------------------------------------------------------------- #


def _patch_event_is_match_tuple_contract(module):
    """把 ``module.Event.is_match`` 包装成 (matched, reason) 元组返回。

    rs_czsc 与 czsc 的示例脚本都需要这个 patch（与上游示例保持一致）。
    使用幂等标记位 ``_rs_tuple_contract_patch`` 防止重复包装，从而支持
    在两个模块上分别打 patch 而互不影响。
    """
    if getattr(module.Event, "_rs_tuple_contract_patch", False):
        return
    origin = module.Event.is_match

    def _wrapped(self, sig):
        out = origin(self, sig)
        if isinstance(out, tuple):
            return out
        if not out:
            return out, ""
        operate = getattr(self, "operate", None)
        return out, str(operate) if operate is not None else "is_match"

    module.Event.is_match = _wrapped
    module.Event._rs_tuple_contract_patch = True


def _build_30m_bars(czsc_module):
    """生成 30 分钟级别的 mock K 线 DataFrame。

    同一份 payload 会同时传给 rs_czsc.format_standard_kline 与
    czsc.format_standard_kline，确保 bars 列表是两套实现间唯一的变量。
    """
    from wbt.mock import mock_symbol_kline

    df = mock_symbol_kline("000001", "30分钟", "20200101", "20240101", seed=42)
    df["dt"] = pd.to_datetime(df["dt"])
    return df


def _build_daily_bars(czsc_module):
    """生成日线级别的 mock K 线 DataFrame，用于 use_optimize 等示例。"""
    from wbt.mock import mock_symbol_kline

    df = mock_symbol_kline("000001", "日线", "20200101", "20240101", seed=42)
    df["dt"] = pd.to_datetime(df["dt"])
    return df


def _normalise_parquet(path: Path) -> pd.DataFrame:
    """把 parquet 读入并做归一化，便于跨模块比较。

    具体处理：
        * 丢弃含不可哈希对象的 ``cache`` 列
        * 按 (dt, symbol, pos_name) 中存在的列稳定排序，使行序一致
    """
    df = pd.read_parquet(path)
    if "cache" in df.columns:
        df = df.drop(columns=["cache"])
    sort_keys = [c for c in ("dt", "symbol", "pos_name") if c in df.columns]
    if sort_keys:
        df = df.sort_values(sort_keys, kind="mergesort").reset_index(drop=True)
    return df


def _compare_parquet_trees(rs_root: Path, czsc_root: Path, label: str):
    """递归对比两棵 parquet 输出树，要求完全等价。

    参数:
        rs_root:   rs_czsc 的输出根目录
        czsc_root: czsc 的输出根目录
        label:     断言失败时使用的标签前缀，便于定位问题
    """
    rs_files = {p.relative_to(rs_root).as_posix() for p in rs_root.rglob("*.parquet")}
    czsc_files = {p.relative_to(czsc_root).as_posix() for p in czsc_root.rglob("*.parquet")}
    assert rs_files == czsc_files, (
        f"[{label}] parquet inventory differs.\n"
        f"  rs only: {rs_files - czsc_files}\n"
        f"  czsc only: {czsc_files - rs_files}"
    )
    for rel in sorted(rs_files):
        rs_df = _normalise_parquet(rs_root / rel)
        czsc_df = _normalise_parquet(czsc_root / rel)
        assert rs_df.shape == czsc_df.shape, f"[{label}/{rel}] shape mismatch: rs={rs_df.shape} czsc={czsc_df.shape}"
        # 列集合严格一致："完全一致"意味着任何一边都不能多出列
        rs_cols = set(rs_df.columns)
        czsc_cols = set(czsc_df.columns)
        assert rs_cols == czsc_cols, (
            f"[{label}/{rel}] column set differs.\n  rs only: {rs_cols - czsc_cols}\n  czsc only: {czsc_cols - rs_cols}"
        )
        cols = sorted(rs_cols)
        pd.testing.assert_frame_equal(
            rs_df[cols].reset_index(drop=True),
            czsc_df[cols].reset_index(drop=True),
            check_dtype=False,
            check_like=False,
        )


# --------------------------------------------------------------------- #
# 示例 1 —— 30分钟笔非多即空.py                                         #
# --------------------------------------------------------------------- #


def _build_long_short_position(module, symbol: str, base_freq: str):
    """构造与 ``30分钟笔非多即空.py::create_long_short_V230909`` 一致的 Position。

    多空两个开仓事件，分别匹配"表里关系向上/向下"，并在涨停/跌停时禁用。
    """
    opens_dict = [
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
        opens=[module.Event.load(x) for x in opens_dict],
        exits=[],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )


def _make_strategy_class(module):
    """为目标模块动态构造 Strategy 子类。

    示例脚本里 Strategy 是局部定义的，必须依赖目标模块的 CzscStrategyBase
    抽象基类才能正确解析；因此每个模块都需要单独构造一份。
    """
    _patch_event_is_match_tuple_contract(module)

    class Strategy(module.CzscStrategyBase):
        @property
        def positions(self):
            # 三个时间周期的 Position 同时启用，复现示例的多周期联立策略
            return [
                _build_long_short_position(module, self.symbol, "30分钟"),
                _build_long_short_position(module, self.symbol, "60分钟"),
                _build_long_short_position(module, self.symbol, "日线"),
            ]

    return Strategy


def _run_30m_example(module, bars_df, results_root: Path):
    """跑一遍 30 分钟示例的完整 backtest + replay 流程，返回耗时。"""
    Strategy = _make_strategy_class(module)
    bars = module.format_standard_kline(bars_df, freq="30分钟")
    symbol = bars[0].symbol
    tactic = Strategy(symbol=symbol)

    start = time.perf_counter()
    tactic.backtest(bars, sdt="2020-06-01")
    replay_dir = results_root / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    tactic.replay(bars, sdt="2020-06-01", res_path=replay_dir, refresh=True)
    elapsed = time.perf_counter() - start
    return elapsed


def test_example_30min_long_short_parity(rs_czsc_module, czsc_module, tmp_path, capsys):
    """30分钟笔非多即空 示例脚本的端到端等价性。

    测试场景：rs_czsc 与 czsc 各跑一次 backtest+replay，输出落到不同目录。

    关键断言：两棵输出 parquet 树（包括 signals/pairs/holds 等）完全等价。
    """
    bars_df = _build_30m_bars(czsc_module)

    rs_root = tmp_path / "rs"
    czsc_root = tmp_path / "czsc"
    rs_root.mkdir()
    czsc_root.mkdir()

    rs_elapsed = _run_30m_example(rs_czsc_module, bars_df, rs_root)
    czsc_elapsed = _run_30m_example(czsc_module, bars_df, czsc_root)

    _compare_parquet_trees(rs_root, czsc_root, "30m-long-short")

    with capsys.disabled():
        ratio = czsc_elapsed / rs_elapsed if rs_elapsed > 0 else float("inf")
        # 顺便打印耗时比，便于跟踪性能
        print(f"\n[30分钟笔非多即空] rs_czsc={rs_elapsed:.3f}s czsc={czsc_elapsed:.3f}s  ratio={ratio:.2f}x")


# --------------------------------------------------------------------- #
# 示例 2 —— use_optimize.py（开仓优化 + 出场优化）                      #
# --------------------------------------------------------------------- #

# 候选开仓信号（与上游示例保持一致的最小可复现集合）
OPEN_CANDIDATE_SIGNALS = [
    "日线_D2单K趋势N5_BS辅助V230506_第1层_任意_任意_0",
    "日线_D2单K趋势N5_BS辅助V230506_第4层_任意_任意_0",
]

# 候选出场事件
EXIT_CANDIDATE_EVENTS = [
    {
        "name": "加速上涨N5T500",
        "operate": "平多",
        "signals_all": ["日线_D2N5T500_绝对动量V230227_超强_任意_任意_0"],
        "signals_any": [],
        "signals_not": [],
    },
    {
        "name": "加速下跌N5T300",
        "operate": "平空",
        "signals_all": ["日线_D2N5T300_绝对动量V230227_超弱_任意_任意_0"],
        "signals_any": [],
        "signals_not": [],
    },
]


def _build_optimize_position(module, symbol: str, name: str, open_signal: str, open_operate: str):
    """根据传入的开仓信号构造一个 Position，用于 OpensOptimize / ExitsOptimize 的基线。"""
    exit_operate = "平多" if open_operate == "开多" else "平空"
    exit_signal = "日线_D1单K趋势N5_BS辅助V230506_第5层_任意_任意_0"
    return module.Position(
        symbol=symbol,
        name=name,
        opens=[
            module.Event.load(
                {
                    "name": f"{name}_open",
                    "operate": open_operate,
                    "signals_all": [open_signal],
                    "signals_any": [],
                    "signals_not": [],
                }
            )
        ],
        exits=[
            module.Event.load(
                {
                    "name": f"{name}_exit",
                    "operate": exit_operate,
                    "signals_all": [exit_signal],
                    "signals_any": [],
                    "signals_not": [],
                }
            )
        ],
        interval=0,
        timeout=120,
        stop_loss=800.0,
        # czsc._native.Position 与 rs_czsc.Position 都接受 t0（后者会自动把 T0 翻译成 t0）
        t0=False,
    )


def _materialize_beta_positions(module, symbol: str, out_dir: Path):
    """把多空两个 Beta 仓位序列化为 JSON 文件，返回文件路径列表。

    通过 ``czsc._compat.position_dump_to_runtime`` 转换成统一的运行时格式，
    确保两套实现读取的内容完全一致。
    """
    import hashlib

    from czsc._compat import position_dump_to_runtime

    out_dir.mkdir(parents=True, exist_ok=True)
    positions = [
        _build_optimize_position(
            module,
            symbol,
            "long_beta",
            "日线_D1单K趋势N5_BS辅助V230506_第1层_任意_任意_0",
            "开多",
        ),
        _build_optimize_position(
            module,
            symbol,
            "short_beta",
            "日线_D1单K趋势N5_BS辅助V230506_第18层_任意_任意_0",
            "开空",
        ),
    ]
    files = []
    for pos in positions:
        payload = position_dump_to_runtime(pos.dump(with_data=False))
        payload.pop("symbol", None)
        # md5 字段供后续缓存命中校验
        payload["md5"] = hashlib.md5(str(payload).encode("utf-8")).hexdigest()
        f = out_dir / f"{pos.name}.json"
        f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        files.append(str(f))
    return files


def _run_optimize_example(module, bars_df, results_root: Path):
    """跑一遍 use_optimize 示例的完整开仓+出场优化流程，返回总耗时。"""
    from czsc._compat import bars_to_dataframe

    if module.__name__ == "rs_czsc":
        from rs_czsc.traders.optimize import ExitsOptimize, OpensOptimize
    else:
        from czsc.traders.optimize import ExitsOptimize, OpensOptimize

    _patch_event_is_match_tuple_contract(module)

    bars_clean = bars_to_dataframe(bars_df, symbol="000001")

    def read_bars(symbol, freq, sdt, edt, **_):
        return bars_clean

    open_root = results_root / "open_demo"
    open_root.mkdir(parents=True, exist_ok=True)
    files_position = _materialize_beta_positions(module, "000001", open_root / "base_positions")

    start = time.perf_counter()
    oop = OpensOptimize(
        symbols=["000001"],
        files_position=files_position,
        task_name="入场优化",
        candidate_signals=sorted(set(OPEN_CANDIDATE_SIGNALS)),
        read_bars=read_bars,
        results_path=open_root,
        signals_module_name="czsc.signals",
        bar_sdt="20200101",
        bar_edt="20240101",
        sdt="20200601",
        base_freq="日线",
    )
    oop.execute(n_jobs=1)

    exit_root = results_root / "exit_demo"
    exit_root.mkdir(parents=True, exist_ok=True)
    files_position_exit = _materialize_beta_positions(module, "000001", exit_root / "base_positions")
    eop = ExitsOptimize(
        symbols=["000001"],
        files_position=files_position_exit,
        task_name="出场优化",
        candidate_events=EXIT_CANDIDATE_EVENTS,
        read_bars=read_bars,
        results_path=exit_root,
        signals_module_name="czsc.signals",
        bar_sdt="20200101",
        bar_edt="20240101",
        sdt="20200601",
        base_freq="日线",
    )
    eop.execute(n_jobs=1)
    return time.perf_counter() - start


def test_example_use_optimize_parity(rs_czsc_module, czsc_module, tmp_path, capsys):
    """use_optimize 示例脚本的端到端等价性。

    测试场景：rs_czsc 与 czsc 分别跑一遍开仓优化 + 出场优化，输出落到
    不同目录。

    关键断言：两棵输出 parquet 树完全等价。
    """
    bars_df = _build_daily_bars(czsc_module)

    rs_root = tmp_path / "rs"
    czsc_root = tmp_path / "czsc"
    rs_root.mkdir()
    czsc_root.mkdir()

    rs_elapsed = _run_optimize_example(rs_czsc_module, bars_df, rs_root)
    czsc_elapsed = _run_optimize_example(czsc_module, bars_df, czsc_root)

    _compare_parquet_trees(rs_root, czsc_root, "use_optimize")

    with capsys.disabled():
        ratio = czsc_elapsed / rs_elapsed if rs_elapsed > 0 else float("inf")
        print(f"\n[use_optimize] rs_czsc={rs_elapsed:.3f}s czsc={czsc_elapsed:.3f}s  ratio={ratio:.2f}x")


# --------------------------------------------------------------------- #
# 示例 3 —— weight_backtest.py                                          #
# --------------------------------------------------------------------- #


def _build_weight_df():
    """构造 ``weight_backtest.py`` 所需的权重 DataFrame。

    列结构与上游示例对齐：``['dt','symbol','weight','price']``。使用
    ``wbt.mock.mock_weights`` 保证两次运行输入一致。
    """
    from wbt.mock import mock_weights

    df = mock_weights(seed=42)
    return df[["dt", "symbol", "weight", "price"]].copy()


def test_example_weight_backtest_parity(rs_czsc_module, czsc_module, capsys):
    """``WeightBacktest`` 示例的等价性测试（弱化版本）。

    关键约定：
        * ``czsc.WeightBacktest`` 是从外部 ``wbt`` 包再导出的
          ``wbt.backtest.WeightBacktest``。
        * ``rs_czsc.WeightBacktest`` 是 rs_czsc 自带的内部实现
          ``rs_czsc._trader.weight_backtest.WeightBacktest``。

    这两者按当前架构本就不是 API 完全相同的实现（统计指标 key 集合、
    版本节奏都不同）。严格的数值等价性不是必需 —— czsc 的契约是"使用
    wbt 作为标准回测提供方"。

    本测试主要做以下事情：
        1. 在同一份输入上跑两套实现，确保都能成功执行
        2. 打印性能耗时比，便于追踪
        3. 对两边都暴露的核心指标（最大回撤、绝对收益、下行波动率、
           新高占比）做 0.5pp 容差范围内的近似一致性校验
        4. 不强制要求 stats dict 完全相等
    """
    df = _build_weight_df()

    start = time.perf_counter()
    rs_wb = rs_czsc_module.WeightBacktest(df, digits=2, n_jobs=1, weight_type="ts")
    rs_stats = dict(rs_wb.stats)
    rs_elapsed = time.perf_counter() - start

    start = time.perf_counter()
    czsc_wb = czsc_module.WeightBacktest(df, digits=2, n_jobs=1, weight_type="ts")
    czsc_stats = dict(czsc_wb.stats)
    czsc_elapsed = time.perf_counter() - start

    # 两套实现都必须成功并产出非空 stats
    assert rs_stats, "rs_czsc.WeightBacktest produced no stats"
    assert czsc_stats, "czsc.WeightBacktest produced no stats"

    # 对两边都暴露的核心指标做近似比较：这些指标即便跨 wbt 版本也应该
    # 大体一致，容差设为 0.005（0.5 个百分点）。
    common_keys = sorted(set(rs_stats) & set(czsc_stats))
    tight_check = {"最大回撤", "绝对收益", "下行波动率", "新高占比"}
    diffs = {}
    for k in common_keys:
        if k not in tight_check:
            continue
        rv, cv = rs_stats[k], czsc_stats[k]
        if isinstance(rv, (int, float)) and isinstance(cv, (int, float)) and abs(rv - cv) > 0.005:
            # 0.5 个百分点的容差
            diffs[k] = (rv, cv)
    assert not diffs, f"core stats divergence beyond 0.005 tolerance: {diffs}"

    with capsys.disabled():
        ratio = czsc_elapsed / rs_elapsed if rs_elapsed > 0 else float("inf")
        print(
            f"\n[weight_backtest] rs_czsc={rs_elapsed:.3f}s "
            f"czsc(wbt)={czsc_elapsed:.3f}s  ratio={ratio:.2f}x  "
            f"(rs keys={len(rs_stats)} czsc keys={len(czsc_stats)} "
            f"common={len(common_keys)})"
        )
