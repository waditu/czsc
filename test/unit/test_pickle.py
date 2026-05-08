"""PyO3 类的 pickle 往返序列化单元测试。

本测试套件验证 czsc 暴露的所有 PyO3 类（Rust 实现 + Python 绑定）都支持
``pickle.dumps`` / ``pickle.loads`` 往返序列化（roundtrip），从而保证它们
能够安全地穿越多进程边界（multiprocessing boundary）。

业务背景：
    在 Streamlit、Joblib、Dask 等多进程场景下，工作进程之间通常通过 pickle
    协议传递对象。如果某个 PyO3 类没有实现 ``__getstate__`` /
    ``__setstate__``，则在跨进程传递时会失败，导致并行化能力受损。

测试策略：
    采用 "FAIL 而不是 ERROR" 的策略：在 fixture 阶段捕获导入和构造异常，
    并通过 ``pytest.fail`` 转换为断言失败。这样 CI 能直接看到失败原因，
    而不是因为构造阶段抛异常使测试以 ERROR 状态结束、被部分工具忽略。

测试覆盖：
    - ``CZSC``: 缠论分析核心类；
    - ``BarGenerator``: K 线生成器；
    - ``Position``: 持仓对象；
    - ``CzscSignals`` / ``CzscTrader``: 信号与交易容器类。
"""

from __future__ import annotations

import pickle
from typing import Any

import pytest


def _try_build_bars() -> tuple[Any | None, str | None]:
    """通过 czsc.mock + format_standard_kline 构造小批量 RawBar 列表。

    使用固定 seed=42 与短时间区间以保证测试快速、结果稳定。

    返回值：
        - 成功：``(bars, None)``；
        - 失败：``(None, error_msg)``。

    通过返回元组而非抛异常，调用方可以将失败转化为 AssertionError，
    避免 fixture 阶段直接抛异常造成 pytest 报告为 ERROR 的情况。
    """
    try:
        from czsc import Freq, format_standard_kline  # type: ignore[attr-defined]
        from czsc.mock import generate_symbol_kines  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        return None, f"import failed: {type(exc).__name__}: {exc}"

    try:
        df = generate_symbol_kines("000001", "30分钟", "20240101", "20240105", seed=42)
        bars = format_standard_kline(df, freq=Freq.F30)
        return bars, None
    except Exception as exc:  # noqa: BLE001
        return None, f"bar generation failed: {type(exc).__name__}: {exc}"


def _build_obj(name: str, bars: Any) -> tuple[Any | None, str | None]:
    """根据目标类名构造一个待 pickle 的实例（不抛异常版本）。

    支持构造的目标类：
        - ``CZSC``: 直接使用 RawBar 列表构造；
        - ``BarGenerator``: 仅初始化基础频率与目标频率列表；
        - ``Position``: 构造一个空的开平仓策略对象；
        - ``CzscSignals``/``CzscTrader``: 需要先用 BarGenerator 喂入 bars，
          再分别传入信号配置与持仓策略列表。
    """
    try:
        import czsc

        if name == "CZSC":
            return czsc.CZSC(bars), None
        if name == "BarGenerator":
            return czsc.BarGenerator(base_freq="30分钟", freqs=["日线"]), None
        if name == "Position":
            return (
                czsc.Position(symbol="000001", name="t", opens=[], exits=[]),
                None,
            )
        if name in ("CzscSignals", "CzscTrader"):
            # CzscSignals 与 CzscTrader 都要求传入一个已经接收过 K 线、
            # 处于"已就绪"状态的 BarGenerator，以及信号配置列表；
            # 其中 CzscTrader 还额外要求一个持仓策略列表。
            bg = czsc.BarGenerator(base_freq="30分钟", freqs=["日线"])
            for bar in bars:
                bg.update(bar)
            if name == "CzscSignals":
                return czsc.CzscSignals(bg, []), None
            return czsc.CzscTrader(bg, [], []), None
    except Exception as exc:  # noqa: BLE001
        return None, f"construction failed: {type(exc).__name__}: {exc}"
    return None, f"unknown target: {name}"


# 参数化覆盖所有需要支持 pickle 的核心 PyO3 类
@pytest.mark.parametrize(
    "target",
    ["CZSC", "BarGenerator", "Position", "CzscSignals", "CzscTrader"],
)
def test_pickle_roundtrip(target: str) -> None:
    """对每个 PyO3 类执行完整的 pickle dump → load 往返。

    测试场景：
        1. 构造测试用 RawBar 列表与目标对象；
        2. 调用 ``pickle.dumps`` 序列化对象到字节串；
        3. 调用 ``pickle.loads`` 反序列化恢复对象；
        4. 校验类型与内部状态保持一致。

    关键断言：
        - 反序列化后对象类型与原对象完全一致；
        - 若两者都实现了 ``__getstate__``，反序列化后状态字典相等。
    """
    bars, err = _try_build_bars()
    if err is not None:
        pytest.fail(f"[{target}] {err}")  # 转化为 FAIL，避免 ERROR

    obj, build_err = _build_obj(target, bars)
    if obj is None:
        pytest.fail(f"[{target}] {build_err}")

    try:
        blob = pickle.dumps(obj)
        restored = pickle.loads(blob)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"[{target}] pickle 往返序列化抛出异常 {type(exc).__name__}: {exc}")

    assert type(restored) is type(obj), f"[{target}] 往返序列化改变了对象类型：{type(obj)} → {type(restored)}"

    if hasattr(obj, "__getstate__") and hasattr(restored, "__getstate__"):
        assert restored.__getstate__() == obj.__getstate__(), f"[{target}] __getstate__ 在往返序列化后发生变化"
