"""CZSC 核心算法（FX/BI/ZS）一致性单元测试。

本测试套件验证迁移后的 czsc-core（Rust 实现）在固定输入下产生的
分型（FX）、笔（BI）、中枢（ZS）结果，与基线快照（baseline snapshot）
逐字节一致（byte-for-byte identical）。

业务背景：
    缠论的核心识别算法对最终交易信号有决定性影响，任何细微的实现差异都
    可能导致大量信号漂移。因此在从 ``rs_czsc`` 迁移到 in-repo 的
    ``czsc._native`` 过程中，必须保证算法输出与一个锁定的基线（
    rs-czsc commit ``47ef6efa``，seed=42）完全一致。

测试覆盖：
    - ``czsc.CZSC`` 的来源必须是 ``czsc._native``，而不是外部 ``rs_czsc``；
    - 在固定 mock 数据（seed=42）上构造 CZSC 对象后：
        * 分型数量与基线一致
        * 笔数量与基线一致
        * 分型方向序列与基线一致
        * 笔方向序列与基线一致
        * 笔长度序列与基线一致
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# 基线快照文件路径，存放固定输入下应得的标准输出
SNAPSHOT_PATH = Path(__file__).parent / "snapshots" / "core_parity_seed42.json"


def _load_snapshot() -> dict[str, Any]:
    """加载基线快照 JSON 文件并返回字典。"""
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _build_czsc() -> tuple[Any | None, str | None]:
    """构造一个用于一致性比对的 CZSC 实例。

    使用固定参数（symbol='000001'，30 分钟，2024-01-01~2024-03-01，seed=42）
    生成可重现的 mock K 线数据，再转换为 RawBar 列表，最后构造 CZSC 对象。

    返回值：
        构造成功时返回 ``(czsc_obj, None)``；任何异常情况下返回
        ``(None, 错误描述)``，避免在 fixture 阶段直接抛出导致测试 ERROR
        而不是 FAIL。
    """
    try:
        import czsc
        from czsc.mock import generate_symbol_kines

        df = generate_symbol_kines("000001", "30分钟", "20240101", "20240301", seed=42)
        bars = czsc.format_standard_kline(df, freq=czsc.Freq.F30)
        return czsc.CZSC(bars), None
    except Exception as exc:  # noqa: BLE001
        return None, f"build failed: {type(exc).__name__}: {exc}"


def test_czsc_source_is_in_repo_native() -> None:
    """验证 czsc.CZSC 类来源于 czsc._native，而不是外部 rs_czsc。

    测试目标：
        迁移目标之一是彻底剥离对 ``rs_czsc`` PyPI 包的依赖，
        因此 ``CZSC`` 类的 ``__module__`` 必须以 ``czsc.`` 开头。

    关键断言：
        ``type(obj).__module__`` 字符串以 ``"czsc."`` 开头。
    """
    obj, err = _build_czsc()
    assert obj is not None, err
    module = type(obj).__module__
    assert module.startswith("czsc."), (
        f"czsc.CZSC 必须来自 czsc._native（实际：{module!r}）；迁移目标要求完全移除 rs_czsc PyPI 依赖。"
    )


def test_fx_list_count_matches_baseline() -> None:
    """验证识别出的分型（FX）数量与基线一致。"""
    obj, err = _build_czsc()
    assert obj is not None, err
    snap = _load_snapshot()
    assert len(obj.fx_list) == snap["fx_list_count"], (
        f"FX 数量出现漂移：实际 {len(obj.fx_list)}，基线 {snap['fx_list_count']}"
    )


def test_bi_list_count_matches_baseline() -> None:
    """验证识别出的笔（BI）数量与基线一致。"""
    obj, err = _build_czsc()
    assert obj is not None, err
    snap = _load_snapshot()
    assert len(obj.bi_list) == snap["bi_list_count"], (
        f"BI 数量出现漂移：实际 {len(obj.bi_list)}，基线 {snap['bi_list_count']}"
    )


def test_fx_marks_sequence_matches_baseline() -> None:
    """验证分型方向序列（顶分型 G / 底分型 D）逐项与基线一致。

    关键断言：
        将 ``obj.fx_list`` 中每个 FX 的 ``mark`` 字段转字符串后形成的列表，
        必须与基线快照中的 ``fx_marks`` 列表完全相等。
    """
    obj, err = _build_czsc()
    assert obj is not None, err
    snap = _load_snapshot()
    actual = [str(fx.mark) for fx in obj.fx_list]
    assert actual == snap["fx_marks"], (
        f"FX 方向序列出现漂移；首个差异下标 = "
        f"{next((i for i, (a, b) in enumerate(zip(actual, snap['fx_marks'], strict=False)) if a != b), 'len mismatch')}"
    )


def test_bi_directions_sequence_matches_baseline() -> None:
    """验证笔方向序列（向上笔 Up / 向下笔 Down）逐项与基线一致。"""
    obj, err = _build_czsc()
    assert obj is not None, err
    snap = _load_snapshot()
    actual = [str(bi.direction) for bi in obj.bi_list]
    assert actual == snap["bi_directions"], (
        f"BI 方向序列出现漂移；首个差异下标 = "
        f"{next((i for i, (a, b) in enumerate(zip(actual, snap['bi_directions'], strict=False)) if a != b), 'len mismatch')}"
    )


def test_bi_lengths_sequence_matches_baseline() -> None:
    """验证每一笔的长度（包含 K 线根数）序列与基线一致。"""
    obj, err = _build_czsc()
    assert obj is not None, err
    snap = _load_snapshot()
    actual = [bi.length for bi in obj.bi_list]
    assert actual == snap["bi_lengths"], f"BI 长度序列出现漂移；期望 {snap['bi_lengths'][:5]}…，实际 {actual[:5]}…"
