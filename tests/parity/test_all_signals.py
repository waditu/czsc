"""全量 K 线信号在不同规模数据集下的等价性测试。

本测试是 parity 套件中覆盖面最广的一组：覆盖所有已注册的 222 个 K 线
信号，并在四种不同规模的数据集上分别比对 ``rs_czsc`` 与 ``czsc`` 的
``run_research`` 输出。

每个数据集的执行步骤：
    1. 把注册表里每一个 K 线信号渲染成具体的七段式信号字符串。其中 218
       个信号可以通过 ``derive_signals_config`` 反推出运行时配置；剩下 4
       个（``bar_amount_acc_V230214``、``bar_mean_amount_V221112``、
       ``bar_section_momentum_V221112``、``bar_zdf_V221203``）的模板含有
       value 段占位符，无法反推 —— rs_czsc 与 czsc 都返回 ``[]``，因此
       我们直接根据 Rust 源代码手写它们的运行时配置，覆盖率从 218 提升
       到 222。
    2. 把所有信号配置合并成一个 ``signals_config``，使用同一个 base freq。
    3. 用完全相同的 Arrow 字节 + JSON 策略分别调用
       ``czsc._native.run_research`` 与 ``rs_czsc._rs_czsc.run_research``。
    4. 解码两边的 ``signals_arrow`` 输出，逐列做比特级一致性断言。

数据集规模设计：
    * **small**  约 520 根日线（约 2 年）
    * **medium** 约 5 200 根日线（约 20 年），通过 30min 重采样得到，
      但保持 ``日线`` 作为 base freq
    * **large**  约 21 000 根 30 分钟 K 线（约 4 年日内）
    * **xlarge** 约 52 500 根 30 分钟 K 线（约 10 年日内）

xlarge 用例覆盖了与生产回测同一量级的输入，能在一次测试里同时拿到所有
规模下的耗时比和成功/失败状态。
"""

from __future__ import annotations

import json
import time

import pandas as pd
import pytest

from ._signal_defaults import render

# --------------------------------------------------------------------- #
# K 线 fixture                                                          #
# --------------------------------------------------------------------- #

# 数据集元组：(标签, base_freq, 起始日期, 结束日期)
DATASETS = [
    ("small", "日线", "20230101", "20250101"),
    ("medium", "日线", "20100101", "20250101"),
    ("large", "30分钟", "20210101", "20250101"),
    ("xlarge", "30分钟", "20140101", "20250101"),
]


def _make_bars(freq: str, sdt: str, edt: str) -> pd.DataFrame:
    """生成指定频率与日期范围的 mock K 线，并清洗为 ``bars_to_dataframe`` 输出形态。"""
    from wbt.mock import mock_symbol_kline

    from czsc._compat import bars_to_dataframe

    df = mock_symbol_kline("000001", freq, sdt, edt, seed=42)
    df["dt"] = pd.to_datetime(df["dt"])
    return bars_to_dataframe(df, symbol="000001")


# --------------------------------------------------------------------- #
# 策略合成                                                              #
# --------------------------------------------------------------------- #


def _build_all_signals_strategy(czsc_module, base_freq: str):
    """构造覆盖全部 K 线信号的运行时策略。

    返回 (strategy_dict, n_signals)。复用 ``_signal_defaults.render`` 渲染
    信号字符串，确保 rs_czsc 与 czsc 接收的配置完全一致。
    """
    from czsc._compat import position_dump_to_runtime, signal_config_to_runtime

    sigs = [s for s in czsc_module._native.list_all_signals() if s["category"] == "kline"]
    test_signals = []
    for s in sigs:
        # 强制把 freq 占位符替换为当前数据集的 base_freq
        rendered = render(s["param_template"]).replace("日线", base_freq, 1)
        test_signals.append(rendered)

    runtime = czsc_module.derive_signals_config(test_signals)
    runtime_for_freq = [c for c in runtime if c.get("freq") == base_freq]

    # 4 个 value 段含占位符的信号，derive_signals_config 无法反推出运行时配置。
    # 这里直接根据 Rust 源代码默认值手写：字段名与 Rust 端 ``params.*`` 取值
    # 完全一致，czsc 与 rs_czsc 都能消费。补齐之后覆盖率从 218 升到 222。
    derive_blind_spots = [
        {"name": "bar_amount_acc_V230214", "freq": base_freq, "params": {"di": 1, "n": 5, "t": 5}},
        {"name": "bar_mean_amount_V221112", "freq": base_freq, "params": {"di": 1, "n": 5, "th1": 1, "th2": 10}},
        {"name": "bar_section_momentum_V221112", "freq": base_freq, "params": {"di": 1, "n": 5, "th": 50}},
        {"name": "bar_zdf_V221203", "freq": base_freq, "params": {"di": 1, "mode": "ZF", "span": "5,20"}},
    ]
    runtime_for_freq.extend(derive_blind_spots)

    # 构造一个 dummy Position，用于满足 run_research 对 positions 非空的校验。
    dummy_sig = test_signals[0].replace("日线", base_freq, 1)
    parts = dummy_sig.split("_")
    dummy_pos = czsc_module.Position.load(
        {
            "symbol": "000001",
            "name": "_parity_dummy_",
            "opens": [
                {
                    "name": "o",
                    "operate": "开多",
                    "signals_all": [{"key": "_".join(parts[:-4]), "value": "_".join(parts[-4:])}],
                    "signals_any": [],
                    "signals_not": [],
                }
            ],
            "exits": [
                {
                    "name": "e",
                    "operate": "平多",
                    "signals_all": [{"key": "_".join(parts[:-4]), "value": "_".join(parts[-4:])}],
                    "signals_any": [],
                    "signals_not": [],
                }
            ],
            "interval": 0,
            "timeout": 100,
            "stop_loss": 100,
            "T0": False,
        }
    )

    strategy = {
        "name": "AllSignals",
        "symbol": "000001",
        "base_freq": base_freq,
        "signals_config": [signal_config_to_runtime(c) for c in runtime_for_freq],
        "positions": [position_dump_to_runtime(dummy_pos.dump(with_data=False))],
        "market": "默认",
        "bg_max_count": 5000,
    }
    return strategy, len(runtime_for_freq)


def _signal_columns(df: pd.DataFrame) -> list[str]:
    """从 DataFrame 列中剔除 K 线元数据列，仅保留信号输出列。"""
    meta = {"dt", "symbol", "open", "close", "high", "low", "vol", "amount", "id", "freq", "cache"}
    return sorted(c for c in df.columns if c not in meta)


# --------------------------------------------------------------------- #
# 参数化等价性测试                                                      #
# --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "label,base_freq,sdt,edt",
    DATASETS,
    ids=[d[0] for d in DATASETS],
)
def test_all_signals_parity(rs_czsc_module, czsc_module, label, base_freq, sdt, edt, capsys):
    """对每种规模的数据集，``czsc.run_research`` 输出的每一列信号都
    必须与 ``rs_czsc.run_research`` 完全相等。

    测试目标：
        * 验证迁移后的 czsc 在全量 K 线信号上与 rs_czsc 行为一致
        * 在四种数据规模下都能保持比特级一致

    关键断言：
        * 输出 DataFrame 的 shape 完全相同
        * 列集合完全相同（无新增/缺失列）
        * 每一个信号列的每一个 cell 都相等（NaN 也对齐）
    """
    from czsc._utils._df_convert import arrow_bytes_to_pd_df, pandas_to_arrow_bytes

    bars_df = _make_bars(base_freq, sdt, edt)
    arrow = pandas_to_arrow_bytes(bars_df)

    strategy, n_signals = _build_all_signals_strategy(czsc_module, base_freq)
    strategy_json = json.dumps(strategy, ensure_ascii=False)

    # 跑 rs_czsc 基线
    t0 = time.perf_counter()
    rs_payload = rs_czsc_module._rs_czsc.run_research(arrow, strategy_json, None, None)
    rs_elapsed = time.perf_counter() - t0

    # 跑迁移后的 czsc
    t0 = time.perf_counter()
    czsc_payload = czsc_module._native.run_research(arrow, strategy_json, None, None)
    czsc_elapsed = time.perf_counter() - t0

    rs_df = arrow_bytes_to_pd_df(bytes(rs_payload["signals_arrow"]))
    czsc_df = arrow_bytes_to_pd_df(bytes(czsc_payload["signals_arrow"]))

    # shape 必须完全一致
    assert rs_df.shape == czsc_df.shape, f"[{label}] shape mismatch: rs={rs_df.shape} czsc={czsc_df.shape}"

    # 列集合严格相等：任何一边出现额外列都视为失败
    rs_cols = set(rs_df.columns)
    czsc_cols = set(czsc_df.columns)
    assert rs_cols == czsc_cols, (
        f"[{label}] column set differs.\n  rs only: {rs_cols - czsc_cols}\n  czsc only: {czsc_cols - rs_cols}"
    )

    # 逐列、逐 cell 对比信号值，记录所有不一致列
    sig_cols = _signal_columns(rs_df)
    diverging = []
    for col in sig_cols:
        rs_series = rs_df[col].reset_index(drop=True)
        czsc_series = czsc_df[col].reset_index(drop=True)
        if not rs_series.equals(czsc_series):
            # 找到第一个不一致的行号，便于诊断
            mask = rs_series.ne(czsc_series) | (rs_series.isna() ^ czsc_series.isna())
            first_idx = mask.idxmax() if mask.any() else None
            diverging.append(
                (
                    col,
                    first_idx,
                    rs_series.iloc[first_idx] if first_idx is not None else None,
                    czsc_series.iloc[first_idx] if first_idx is not None else None,
                )
            )

    ratio = czsc_elapsed / rs_elapsed if rs_elapsed > 0 else float("inf")
    with capsys.disabled():
        # 打印耗时比和差异统计，便于在 pytest 输出中追踪性能与正确性
        print(
            f"\n[all-signals/{label} bars={len(bars_df)} sigs={n_signals}] "
            f"rs_czsc={rs_elapsed * 1000:.0f}ms "
            f"czsc={czsc_elapsed * 1000:.0f}ms "
            f"ratio={ratio:.2f}x "
            f"signal_cols={len(sig_cols)} "
            f"diverging={len(diverging)}"
        )

    assert not diverging, (
        f"[{label}] {len(diverging)} signal columns diverge.\n  first 5 (col, row, rs, czsc): {diverging[:5]}"
    )
