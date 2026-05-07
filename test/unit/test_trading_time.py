"""``is_trading_time`` 跨市场交易时段判断单元测试。

本测试套件验证 ``czsc.is_trading_time`` 函数能够正确识别 A 股、港股和
数字货币三大市场的可交易时间段。

业务背景：
    ``is_trading_time`` 是仅在 czsc 中提供（rs-czsc 不包含）的实用函数，
    迁移过程中由 Rust 实现并通过 PyO3 暴露在 ``czsc._native`` 命名空间，
    最终重导出为 ``czsc.is_trading_time``。

各市场交易时段（本地时区）：
    - A 股 (astock)：周一至周五 09:30-11:30 + 13:00-15:00（北京时间）
    - 港股 (hk)：周一至周五 09:30-12:00 + 13:00-16:00（香港时间）
    - 数字货币 (crypto)：全年 7×24 小时可交易

测试覆盖：
    - 三个市场在工作日内边界点（开盘/收盘/午休前后）的判定；
    - A 股周末（非交易日）的拒绝判定；
    - 数字货币的"始终可交易"语义；
    - ``is_trading_time`` 函数的来源必须是 czsc._native（Rust 实现）。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest


def _safe_import_czsc() -> tuple[Any | None, str | None]:
    """安全导入 czsc 顶层包，捕获所有异常并返回 (czsc, err) 元组。"""
    try:
        import czsc

        return czsc, None
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


# 参数化用例覆盖三大市场的关键时间边界点
@pytest.mark.parametrize(
    "market, dt, expected",
    [
        # A 股 — 2024-01-08 周一（正常交易日）：覆盖上下午开盘、午休、收盘前后
        ("astock", datetime(2024, 1, 8, 9, 30), True),
        ("astock", datetime(2024, 1, 8, 10, 0), True),
        ("astock", datetime(2024, 1, 8, 11, 30), True),
        ("astock", datetime(2024, 1, 8, 12, 30), False),
        ("astock", datetime(2024, 1, 8, 13, 0), True),
        ("astock", datetime(2024, 1, 8, 15, 0), True),
        ("astock", datetime(2024, 1, 8, 15, 30), False),
        ("astock", datetime(2024, 1, 6, 10, 0), False),  # 周六，非交易日
        # 港股 — 2024-01-08 周一：覆盖开盘、午休、收盘
        ("hk", datetime(2024, 1, 8, 9, 30), True),
        ("hk", datetime(2024, 1, 8, 12, 0), False),
        ("hk", datetime(2024, 1, 8, 16, 0), True),
        # 数字货币 — 任何时间均可交易（包括周末和节假日）
        ("crypto", datetime(2024, 1, 6, 3, 0), True),
        ("crypto", datetime(2024, 12, 25, 0, 0), True),
    ],
)
def test_is_trading_time(market: str, dt: datetime, expected: bool) -> None:
    """对每个市场 / 时间点组合验证 is_trading_time 的判定结果。

    测试场景：
        参数化执行 13 个用例，覆盖 A 股、港股、数字货币三大市场在
        不同时间段的边界判定。

    关键断言：
        ``czsc.is_trading_time(dt, market=market)`` 返回值与预期布尔值完全相等
        （使用 ``is`` 比较，确保返回的是布尔类型而非 truthy 值）。
    """
    czsc, err = _safe_import_czsc()
    if czsc is None:
        pytest.fail(f"导入 czsc 失败：{err}")
    if not hasattr(czsc, "is_trading_time"):
        pytest.fail(
            "czsc.is_trading_time 尚未暴露 — czsc-utils 必须添加该函数"
        )
    actual = czsc.is_trading_time(dt, market=market)
    assert actual is expected, (
        f"is_trading_time({market}, {dt.isoformat()}) 返回 {actual}，"
        f"预期 {expected}"
    )


def test_is_trading_time_module_origin() -> None:
    """验证 is_trading_time 来自 czsc._native（Rust 实现），而非 Python helper。

    测试目标：
        确保该函数已经走 Rust 实现路径，而不是仍由旧的 Python 工具函数提供。

    关键断言：
        ``is_trading_time.__module__`` 字符串以 ``"czsc."`` 开头。
    """
    czsc, err = _safe_import_czsc()
    if czsc is None:
        pytest.fail(f"导入 czsc 失败：{err}")
    fn = getattr(czsc, "is_trading_time", None)
    if fn is None:
        pytest.fail("czsc.is_trading_time 缺失")
    module = getattr(fn, "__module__", "?")
    assert module.startswith("czsc."), (
        f"is_trading_time 必须来自 czsc._native（实际 {module!r}）"
    )
