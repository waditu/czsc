"""``run_research`` 全链路等价性测试。

这是 parity 套件中最强的一组等价性保证：要求 ``run_research`` 在两套
实现间产出比特级一致的输出。

输入侧两个模块都拿到：
    * 完全相同的 Arrow 编码 K 线 bars
    * 完全相同的 JSON 策略（含 positions + signals_config）

输出侧需要产出完全一致的 signals / pairs / holds DataFrame。这里的
"完全一致"是在 pandas 层做比较 —— 因为 Arrow IPC 的底层字节可能在
framing（footer、字典编码等）细节上有差别，但只要逻辑内容相等就视为
等价。
"""

from __future__ import annotations

import json

import pandas as pd
import pytest


def _strategy_payload(czsc_module, position_dict):
    """构造两套实现都能消费的运行时格式 strategy dict。

    使用 czsc 的 ``_compat`` 工具函数把 Position dict 转成标准的运行时
    格式。rs_czsc 与 czsc 的 Rust 端都通过 serde_json 反序列化同一份
    JSON，因此只要 payload 校验通过即可。
    """
    from czsc._compat import position_dump_to_runtime, signal_config_to_runtime

    pos = czsc_module.Position.load(position_dict)
    runtime_position = position_dump_to_runtime(pos.dump(with_data=False))
    signals_cfg = czsc_module.derive_signals_config(pos.unique_signals)
    return {
        "name": "ParityStrategy",
        "symbol": position_dict["symbol"],
        "base_freq": "日线",
        "signals_config": [signal_config_to_runtime(c) for c in signals_cfg],
        "positions": [runtime_position],
        "market": "默认",
        "bg_max_count": 5000,
    }


def _bars_arrow_bytes(czsc_module, mock_kline_df):
    """生成两套实现共用的、dtype 干净的 Arrow 字节流。"""
    from czsc._compat import bars_to_dataframe
    from czsc._utils._df_convert import pandas_to_arrow_bytes

    df = bars_to_dataframe(mock_kline_df, symbol="000001")
    return pandas_to_arrow_bytes(df)


def _decode_arrow(arrow_bytes: bytes) -> pd.DataFrame:
    """把 Arrow 字节流解码回 pandas DataFrame。"""
    from czsc._utils._df_convert import arrow_bytes_to_pd_df

    return arrow_bytes_to_pd_df(arrow_bytes)


def _normalise_for_compare(df: pd.DataFrame) -> pd.DataFrame:
    """比较前做归一化：去掉不可哈希列、按时间排序。"""
    drop = [c for c in ("cache",) if c in df.columns]
    out = df.drop(columns=drop, errors="ignore").copy()
    if "dt" in out.columns:
        out = out.sort_values("dt").reset_index(drop=True)
    return out


@pytest.fixture
def parity_inputs(rs_czsc_module, czsc_module, mock_kline_df, sample_position_dict):
    """构造 parity 测试需要的 (arrow_bytes, strategy_json) 入参。

    返回元组：
        * arrow_bytes:   两边都能解析的 K 线 Arrow 字节流
        * strategy_json: 两边都能消费的运行时策略 JSON 字符串
    """
    arrow_bytes = _bars_arrow_bytes(czsc_module, mock_kline_df)
    strategy = _strategy_payload(czsc_module, sample_position_dict)
    return arrow_bytes, json.dumps(strategy, ensure_ascii=False)


def test_run_research_signals_match(rs_czsc_module, czsc_module, parity_inputs):
    """``run_research`` 的 signals_arrow 输出必须在两套实现间完全等价。

    关键断言：
        * shape 一致
        * 列集合完全相同（无新增/缺失）
        * 公共列的内容（按 dt 排序后）逐 cell 相等
    """
    arrow_bytes, strategy_json = parity_inputs

    rs_payload = rs_czsc_module._rs_czsc.run_research(arrow_bytes, strategy_json, None, None)
    czsc_payload = czsc_module._native.run_research(arrow_bytes, strategy_json, None, None)

    rs_df = _normalise_for_compare(_decode_arrow(bytes(rs_payload["signals_arrow"])))
    czsc_df = _normalise_for_compare(_decode_arrow(bytes(czsc_payload["signals_arrow"])))

    assert rs_df.shape == czsc_df.shape, f"shape mismatch: rs={rs_df.shape} czsc={czsc_df.shape}"
    assert set(rs_df.columns) == set(czsc_df.columns), (
        f"signals columns differ.\n"
        f"rs only: {set(rs_df.columns) - set(czsc_df.columns)}\n"
        f"czsc only: {set(czsc_df.columns) - set(rs_df.columns)}"
    )
    common_cols = sorted(rs_df.columns)
    pd.testing.assert_frame_equal(rs_df[common_cols], czsc_df[common_cols], check_dtype=False)


def test_run_research_pairs_match(rs_czsc_module, czsc_module, parity_inputs):
    """``run_research`` 的 pairs_arrow（每笔交易明细）输出必须等价。

    关键断言：shape 一致；逐行内容（去掉行索引、允许列顺序不同）等价。
    """
    arrow_bytes, strategy_json = parity_inputs

    rs_payload = rs_czsc_module._rs_czsc.run_research(arrow_bytes, strategy_json, None, None)
    czsc_payload = czsc_module._native.run_research(arrow_bytes, strategy_json, None, None)

    rs_df = _normalise_for_compare(_decode_arrow(bytes(rs_payload["pairs_arrow"])))
    czsc_df = _normalise_for_compare(_decode_arrow(bytes(czsc_payload["pairs_arrow"])))

    assert rs_df.shape == czsc_df.shape
    pd.testing.assert_frame_equal(
        rs_df.reset_index(drop=True),
        czsc_df.reset_index(drop=True),
        check_dtype=False,
        check_like=True,
    )


def test_run_research_holds_match(rs_czsc_module, czsc_module, parity_inputs):
    """``run_research`` 的 holds_arrow（持仓时序）输出必须等价。

    关键断言：shape 一致；逐行内容（去掉行索引、允许列顺序不同）等价。
    """
    arrow_bytes, strategy_json = parity_inputs

    rs_payload = rs_czsc_module._rs_czsc.run_research(arrow_bytes, strategy_json, None, None)
    czsc_payload = czsc_module._native.run_research(arrow_bytes, strategy_json, None, None)

    rs_df = _normalise_for_compare(_decode_arrow(bytes(rs_payload["holds_arrow"])))
    czsc_df = _normalise_for_compare(_decode_arrow(bytes(czsc_payload["holds_arrow"])))

    assert rs_df.shape == czsc_df.shape
    pd.testing.assert_frame_equal(
        rs_df.reset_index(drop=True),
        czsc_df.reset_index(drop=True),
        check_dtype=False,
        check_like=True,
    )


def test_run_research_meta_match(rs_czsc_module, czsc_module, parity_inputs):
    """``run_research`` 的 meta payload 必须在两套实现间等价。

    meta 中包含 symbol / counts / version 等元信息。比较前会先剔除会因
    构建环境不同而合理变化的字段（构建时间戳、git hash、引擎版本号），
    剩余字段必须完全相等。

    关键断言：剔除 ``drop_keys`` 后，rs_meta 与 czsc_meta 完全相等。
    """
    arrow_bytes, strategy_json = parity_inputs

    rs_payload = rs_czsc_module._rs_czsc.run_research(arrow_bytes, strategy_json, None, None)
    czsc_payload = czsc_module._native.run_research(arrow_bytes, strategy_json, None, None)

    # 这些字段在不同构建/运行间合理变化，比较时需要排除：
    #   build_ts / git_hash / engine_version —— 构建环境差异
    #   elapsed_ms —— 同一进程两次调用的毫秒级耗时抖动，与算法/数据无关
    drop_keys = {"build_ts", "git_hash", "engine_version", "elapsed_ms"}
    rs_meta = {k: v for k, v in rs_payload["meta"].items() if k not in drop_keys}
    czsc_meta = {k: v for k, v in czsc_payload["meta"].items() if k not in drop_keys}

    assert rs_meta == czsc_meta, (
        f"meta diverges.\nrs only: {set(rs_meta) - set(czsc_meta)}\n"
        f"czsc only: {set(czsc_meta) - set(rs_meta)}\n"
        f"value diffs: {[(k, rs_meta.get(k), czsc_meta.get(k)) for k in rs_meta if rs_meta.get(k) != czsc_meta.get(k)]}"
    )
