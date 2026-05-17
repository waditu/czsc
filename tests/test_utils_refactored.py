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


def test_plotting_weight_imports():
    """验证权重绘图相关统计函数可以从 ``czsc.utils.plotting`` 导入。

    关键断言：
        ``calculate_turnover_stats`` 与 ``calculate_weight_stats`` 都是可调用对象。
    """
    from czsc.utils.plotting import (
        calculate_turnover_stats,
        calculate_weight_stats,
    )

    assert callable(calculate_turnover_stats)
    assert callable(calculate_weight_stats)


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


def test_analysis_stats_imports():
    """验证统计分析模块 ``czsc.utils.analysis`` 的关键函数可被导入。

    关键断言：
        ``daily_performance``、``top_drawdowns`` 两个统计函数均为可调用对象。
        （``holds_performance`` / ``rolling_daily_performance`` 已在
        二阶段清理 PR-B 删除。）
    """
    from czsc.utils.analysis import (
        daily_performance,
        top_drawdowns,
    )

    assert callable(daily_performance)
    assert callable(top_drawdowns)


def test_analysis_corr_imports():
    """验证相关性分析模块 ``czsc.utils.analysis`` 的关键函数可被导入。

    关键断言：
        ``nmi_matrix``、``single_linear``、``cross_sectional_ic`` 三个相关性分析
        函数均为可调用对象。
    """
    from czsc.utils.analysis import (
        cross_sectional_ic,
        nmi_matrix,
        single_linear,
    )

    assert callable(nmi_matrix)
    assert callable(single_linear)
    assert callable(cross_sectional_ic)


def test_backward_compatibility():
    """验证向后兼容性：``czsc.utils`` 顶层仍稳定暴露非绘图类公共接口。

    评审决议（L-5/L-6）已经移除了 ``czsc.utils`` 的 lazy loading 入口，
    绘图相关 symbol 现在统一从 ``czsc.utils.plotting.*`` 显式获取。本测试
    锁定这条契约，避免有人后续又把 lazy loading 加回来：

    - ``czsc.utils.*``：稳定暴露 ``DataClient`` / ``DiskCache`` / ``home_path`` /
      ``daily_performance`` 等数据/统计接口
    - ``czsc.utils.plotting.kline.plot_nx_graph`` / ``czsc.utils.plotting.weight.*``：
      保留的绘图符号显式从 plotting 子模块拿
    - ``czsc.utils.plotting.lightweight.plot_czsc{,_trader,_signals}``：
      缠论 K 线可视化的唯一对外接口（二阶段清理 PR-C 起）
    """
    from czsc.utils import (
        DataClient,
        DiskCache,
        daily_performance,
        home_path,
    )

    assert home_path is not None
    assert DiskCache is not None
    assert DataClient is not None
    assert callable(daily_performance)

    # 保留的绘图符号显式从 plotting 子模块获取
    from czsc.utils.plotting.kline import plot_nx_graph
    from czsc.utils.plotting.lightweight import plot_czsc, plot_czsc_signals, plot_czsc_trader

    assert callable(plot_nx_graph)
    assert callable(plot_czsc)
    assert callable(plot_czsc_trader)
    assert callable(plot_czsc_signals)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
