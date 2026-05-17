"""``czsc.utils`` 重构后的子包结构与向后兼容性单元测试。

本测试套件验证 ``czsc.utils`` 经过重构、按主题划分到多个子包后，
新旧导入路径都能正确工作，并且各子包暴露的常量、函数与验证器行为符合预期。

业务背景：
    ``czsc.utils`` 重构为以下子包/模块：

    - ``czsc.utils.plotting``：绘图相关，进一步分为 ``common``（颜色/标签等
      共享常量与 ``figure_to_html`` 工具函数）、回测绘图、权重绘图等子模块。
    - ``czsc.utils.data``：数据相关，包括 ``validators``（DataFrame 校验）、
      ``converters``（标准化转换）等。
    - ``czsc.utils.analysis``：统计与相关性分析工具的统一入口。

    重构同时要求保持完整的向后兼容性，旧的导入路径（如 ``from czsc.utils
    import DiskCache``）必须继续工作。
"""

import pandas as pd
import pytest


def test_plotting_weight_module_removed():
    """2026-05-17 PR-A：``czsc.utils.plotting.weight`` 整文件已 git rm。

    上一波保留 ``calculate_turnover_stats`` / ``calculate_weight_stats`` 等 6 个
    权重分析函数，本次清理整体放弃，调用方改用 ``plotly.express`` 或
    ``wbt.generate_backtest_report``，迁移说明见 ``docs/migration/cleanup-non-czsc-core.md``。
    """
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("czsc.utils.plotting.weight")

    from czsc.utils import plotting

    for name in (
        "calculate_turnover_stats",
        "calculate_weight_stats",
        "plot_weight_histogram_kde",
        "plot_weight_cdf",
        "plot_turnover_overview",
        "plot_turnover_cost_analysis",
    ):
        assert not hasattr(plotting, name), f"czsc.utils.plotting.{name} 应已删除"


def test_data_validators():
    """验证数据校验器 ``czsc.utils.data.validators`` 的核心断言行为。

    测试场景：
        - ``validate_dataframe_columns``：列齐全时静默通过，缺列时抛 ValueError；
        - ``validate_datetime_index``：DatetimeIndex 静默通过，普通整数索引抛 ValueError；
        - ``validate_numeric_column``：列存在时静默通过，列不存在时抛 ValueError。

    关键断言：
        - 所有正常情况都不抛异常；
        - 所有异常分支都通过 ``pytest.raises`` 配合 ``match`` 参数校验异常消息中
          的关键中文字符串。
    """
    from czsc.utils.data.validators import (
        validate_dataframe_columns,
        validate_datetime_index,
        validate_numeric_column,
    )

    # 测试 validate_dataframe_columns
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})

    # 正常情况
    validate_dataframe_columns(df, ["a", "b"], "test_df")

    # 缺少列应该抛出异常
    with pytest.raises(ValueError, match="缺少必需的列"):
        validate_dataframe_columns(df, ["a", "b", "c"], "test_df")

    # 测试 validate_datetime_index
    df_with_dt_index = pd.DataFrame({"value": [1, 2, 3]}, index=pd.date_range("2024-01-01", periods=3))
    validate_datetime_index(df_with_dt_index, "test_df")

    # 非DatetimeIndex应该抛出异常
    with pytest.raises(ValueError, match="必须是 DatetimeIndex"):
        validate_datetime_index(df, "test_df")

    # 测试 validate_numeric_column
    validate_numeric_column(df, "a", "test_df")

    # 不存在的列
    with pytest.raises(ValueError, match="中不存在列"):
        validate_numeric_column(df, "nonexistent", "test_df")


def test_data_converters():
    """验证数据转换器 ``czsc.utils.data.converters`` 的标准化能力。

    测试场景：
        - ``to_standard_kline_format``：将带有 ``datetime`` / ``volume`` 列名的
          DataFrame 转换为 czsc 的标准列名（``dt`` / ``vol``）；
        - ``normalize_symbol``：去除前后空格并转换为大写。

    关键断言：
        - 转换后必须包含 ``dt``、``open``、``vol`` 等标准列；
        - ``dt`` 列的元素类型必须是 ``pd.Timestamp``；
        - ``" aapl "`` → ``"AAPL"``、``"  tsla  "`` → ``"TSLA"``。
    """
    from czsc.utils.data.converters import (
        normalize_symbol,
        to_standard_kline_format,
    )

    # 测试 to_standard_kline_format
    df = pd.DataFrame(
        {
            "datetime": pd.date_range("2024-01-01", periods=3),
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [99, 100, 101],
            "close": [103, 104, 105],
            "volume": [1000, 1100, 1200],
        }
    )

    result = to_standard_kline_format(df, dt_col="datetime", volume_col="volume")

    assert "dt" in result.columns
    assert "open" in result.columns
    assert "vol" in result.columns
    assert isinstance(result["dt"].iloc[0], pd.Timestamp)

    # 测试 normalize_symbol
    assert normalize_symbol(" aapl ") == "AAPL"
    assert normalize_symbol("  tsla  ") == "TSLA"


def test_analysis_stats_module_removed():
    """2026-05-17 PR-A：``czsc.utils.analysis.stats`` 整文件已 git rm。

    ``daily_performance`` / ``top_drawdowns`` 改由 ``wbt`` 提供，czsc 顶层
    ``czsc.daily_performance`` / ``czsc.top_drawdowns`` 仍可用（透传 wbt）。
    """
    import importlib

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("czsc.utils.analysis.stats")

    from czsc.utils import analysis

    for name in (
        "daily_performance",
        "top_drawdowns",
        "psi",
        "evaluate_pairs",
        "cal_break_even_point",
    ):
        assert not hasattr(analysis, name), f"czsc.utils.analysis.{name} 应已删除"


def test_analysis_corr_imports():
    """验证相关性分析模块 ``czsc.utils.analysis`` 的关键函数可被导入。

    2026-05-17 PR-A 起：``nmi_matrix`` / ``single_linear`` 已删除，本测试只断言
    ``cross_sectional_ic`` 仍可用。
    """
    from czsc.utils.analysis import cross_sectional_ic

    assert callable(cross_sectional_ic)


def test_backward_compatibility():
    """验证向后兼容性：``czsc.utils`` 顶层仍稳定暴露非绘图类公共接口。

    评审决议（L-5/L-6）已经移除了 ``czsc.utils`` 的 lazy loading 入口，
    绘图相关 symbol 现在统一从 ``czsc.utils.plotting.*`` 显式获取。本测试
    锁定这条契约，避免有人后续又把 lazy loading 加回来：

    - ``czsc.utils.*``：稳定暴露 ``DataClient`` / ``DiskCache`` / ``home_path`` 等
      数据接口（``daily_performance`` 已下沉 wbt，本子包不再 re-export，2026-05-17 PR-A）；
    - ``czsc.utils.plotting.lightweight.plot_czsc{,_trader,_signals}``：缠论 K 线
      可视化的唯一对外接口（二阶段清理 PR-C 起）。
    """
    from czsc import daily_performance
    from czsc.utils import DataClient, DiskCache, home_path

    assert home_path is not None
    assert DiskCache is not None
    assert DataClient is not None
    assert callable(daily_performance)

    # 唯一保留的缠论 K 线可视化入口
    from czsc.utils.plotting.lightweight import plot_czsc, plot_czsc_signals, plot_czsc_trader

    assert callable(plot_czsc)
    assert callable(plot_czsc_trader)
    assert callable(plot_czsc_signals)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
