"""优化器底层函数的等价性测试。

本套件验证 ``build_*_optim_positions`` 与 ``run_optimize_batch`` 三个
低层 Rust 入口的等价性：

    * ``build_open_optim_positions`` —— 纯 Rust 的开仓优化变体构造器
      （没有磁盘 IO），只对仓位 dict 做笛卡尔积式扩展。
    * ``build_exit_optim_positions`` —— 同上，但作用于出场事件。
    * ``run_optimize_batch``         —— 完整的优化批处理（含磁盘 IO），
      两套实现都会写出 parquet 输出，最后逐文件解码并比较内容。

通过这三个测试可以保证：
    1. Rust 端的纯函数变体生成器输出一致；
    2. 端到端的批处理流水线（含落盘格式）也一致。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def position_files(tmp_path, sample_position_dict, czsc_module):
    """把一份样例 Position 物化为 JSON 文件，供两个 build 助手使用。

    文件采用运行时格式（signals_all 为字符串列表），并保留占位的 ``symbol``
    字段 —— 这与 rs_czsc 的 ``OpensOptimize._materialize_position_files``
    行为一致（``runtime.setdefault("symbol", "symbol")``）。

    返回值：单元素列表，包含 JSON 文件的绝对路径字符串。
    """
    from czsc._compat import position_dump_to_runtime

    pos = czsc_module.Position.load(sample_position_dict)
    payload = position_dump_to_runtime(pos.dump(with_data=False))
    payload.setdefault("symbol", "symbol")
    payload.pop("md5", None)
    payload.pop("pairs", None)
    payload.pop("holds", None)
    p = tmp_path / "beta.json"
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return [str(p)]


def test_build_open_optim_positions_matches(rs_czsc_module, czsc_module, position_files):
    """``build_open_optim_positions`` 必须在两套实现间产出等价的开仓变体。

    测试场景：用同一份基线仓位文件 + 同一个候选信号，调用 rs_czsc 与 czsc
    的纯函数实现，对比生成的变体 Position 列表。

    关键断言：
        * 变体数量一致
        * 经规范化后的 (name, opens hash, exits hash) 三元组集合一致
          （列表顺序不要求一致）
    """
    candidates = ["日线_D1N5M5TH10_ADTMV230603_看多_任意_任意_0"]

    rs_raw = rs_czsc_module._rs_czsc.build_open_optim_positions(position_files, candidates)
    czsc_raw = czsc_module._native.build_open_optim_positions(position_files, candidates)

    rs_data = json.loads(rs_raw) if isinstance(rs_raw, str) else rs_raw
    czsc_data = json.loads(czsc_raw) if isinstance(czsc_raw, str) else czsc_raw

    assert len(rs_data) == len(czsc_data), f"position count mismatch: rs={len(rs_data)} czsc={len(czsc_data)}"

    # 仓位列表的顺序在两次独立运行间不一定一致；统一用 (name, opens hash,
    # exits hash) 做规范化后再比较集合相等。
    def _canon(positions):
        return sorted(
            (
                p["name"],
                json.dumps(p.get("opens", []), sort_keys=True, ensure_ascii=False),
                json.dumps(p.get("exits", []), sort_keys=True, ensure_ascii=False),
            )
            for p in positions
        )

    assert _canon(rs_data) == _canon(czsc_data), "open-optim variants diverge"


def test_build_exit_optim_positions_matches(rs_czsc_module, czsc_module, position_files):
    """``build_exit_optim_positions`` 必须在两套实现间产出等价的出场变体。

    测试场景：候选事件以 JSON 字符串形式传入；和开仓侧一样，做集合等价
    校验，不要求列表顺序一致。
    """
    candidate_events = [
        {
            "name": "exit_event",
            "operate": "平多",
            "signals_all": ["日线_D1N5M5TH10_ADTMV230603_看空_任意_任意_0"],
            "signals_any": [],
            "signals_not": [],
        }
    ]

    rs_raw = rs_czsc_module._rs_czsc.build_exit_optim_positions(
        position_files, json.dumps(candidate_events, ensure_ascii=False)
    )
    czsc_raw = czsc_module._native.build_exit_optim_positions(
        position_files, json.dumps(candidate_events, ensure_ascii=False)
    )

    rs_data = json.loads(rs_raw) if isinstance(rs_raw, str) else rs_raw
    czsc_data = json.loads(czsc_raw) if isinstance(czsc_raw, str) else czsc_raw

    assert len(rs_data) == len(czsc_data)

    def _canon(positions):
        return sorted(
            (
                p["name"],
                json.dumps(p.get("opens", []), sort_keys=True, ensure_ascii=False),
                json.dumps(p.get("exits", []), sort_keys=True, ensure_ascii=False),
            )
            for p in positions
        )

    assert _canon(rs_data) == _canon(czsc_data)


@pytest.fixture
def bars_dir(tmp_path, mock_kline_df, czsc_module):
    """落地一份 mock K 线 parquet，供两套实现共用。

    rs_czsc 与 czsc 都从同一个目录读取 bars，从而把 IO 层带来的潜在
    差异降到最低。
    """
    from czsc._compat import bars_to_dataframe

    bars_path = tmp_path / "bars"
    bars_path.mkdir()
    df = bars_to_dataframe(mock_kline_df, symbol="000001")
    df.to_parquet(bars_path / "000001.parquet", index=False)
    return bars_path


def test_run_optimize_batch_matches(rs_czsc_module, czsc_module, bars_dir, position_files, tmp_path):
    """``run_optimize_batch`` 端到端等价性测试。

    测试场景：构造一个最小化的开仓优化任务配置，rs_czsc 与 czsc 各跑
    一次，输出落到不同目录，然后递归对比文件清单与 parquet 内容。

    关键断言：
        * 两边的输出文件相对路径集合完全一致（无任何缺失或额外文件）
        * 每个 parquet 的 shape 与公共列内容完全等价
    """
    cfg = {
        "optim_type": "open",
        "task_name": "parity_open",
        "base_freq": "日线",
        "symbols": ["000001"],
        "files_position": position_files,
        "candidate_signals": ["日线_D1N5M5TH10_ADTMV230603_看多_任意_任意_0"],
        "market": "默认",
        "bg_max_count": 5000,
    }

    rs_out = tmp_path / "rs_results"
    czsc_out = tmp_path / "czsc_results"
    rs_out.mkdir()
    czsc_out.mkdir()

    rs_msg = rs_czsc_module._rs_czsc.run_optimize_batch(
        str(bars_dir), json.dumps(cfg, ensure_ascii=False), str(rs_out), 1
    )
    czsc_msg = czsc_module._native.run_optimize_batch(
        str(bars_dir), json.dumps(cfg, ensure_ascii=False), str(czsc_out), 1
    )
    assert isinstance(rs_msg, str)
    assert isinstance(czsc_msg, str)

    # 递归扫描两棵输出树，构造 {相对路径: 字节数} 清单
    def _inventory(root: Path) -> dict[str, int]:
        out = {}
        for p in sorted(root.rglob("*")):
            if p.is_file():
                out[str(p.relative_to(root))] = p.stat().st_size
        return out

    rs_files = _inventory(rs_out)
    czsc_files = _inventory(czsc_out)
    assert set(rs_files) == set(czsc_files), (
        f"output tree differs.\nrs only: {set(rs_files) - set(czsc_files)}\n"
        f"czsc only: {set(czsc_files) - set(rs_files)}"
    )

    # 逐文件比较 parquet 内容
    for rel in sorted(rs_files):
        if not rel.endswith(".parquet"):
            continue
        rs_df = pd.read_parquet(rs_out / rel)
        czsc_df = pd.read_parquet(czsc_out / rel)
        # cache 列含不可哈希对象，比对前先丢掉
        for c in ("cache",):
            rs_df = rs_df.drop(columns=c, errors="ignore")
            czsc_df = czsc_df.drop(columns=c, errors="ignore")
        assert rs_df.shape == czsc_df.shape, f"{rel}: shape mismatch"
        common = sorted(set(rs_df.columns) & set(czsc_df.columns))
        pd.testing.assert_frame_equal(
            rs_df[common].reset_index(drop=True),
            czsc_df[common].reset_index(drop=True),
            check_dtype=False,
            check_like=True,
        )
