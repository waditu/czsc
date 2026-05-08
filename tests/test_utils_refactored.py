"""``czsc.utils`` 重构后的子包结构与向后兼容性单元测试。

本测试套件验证 ``czsc.utils`` 经过重构、按主题划分到多个子包后，
新旧导入路径都能正确工作，并且各子包暴露的常量、函数与验证器行为符合预期。

业务背景：
    ``czsc.utils`` 重构为以下子包/模块：

    - ``czsc.utils.plotting``：绘图相关，进一步分为 ``common``（颜色/标签等
      共享常量与 ``figure_to_html`` 工具函数）、回测绘图、权重绘图等子模块。
    - ``czsc.utils.data``：数据相关，包括 ``validators``（DataFrame 校验）、
      ``converters``（标准化转换）等。
    - ``czsc.utils.crypto``：对称加密工具，从 ``czsc.utils.crypto.fernet`` 升级
      为子包导出。
    - ``czsc.utils.analysis``：统计与相关性分析工具的统一入口。

    重构同时要求保持完整的向后兼容性，旧的导入路径（如 ``from czsc.utils
    import DiskCache``）必须继续工作。
"""

import pandas as pd
import pytest


def test_plotting_common_module():
    """验证 ``czsc.utils.plotting.common`` 中的常量与 figure_to_html 工具函数。

    测试场景：
        1. 校验四个核心常量值：颜色、Sigma 等级数、月份标签数；
        2. 用空 ``go.Figure`` 调用 ``figure_to_html``：
           - ``to_html=False`` 时返回原 Figure 对象；
           - ``to_html=True`` 时返回包含 plotly 标识的 HTML 字符串。

    关键断言：
        - ``COLOR_DRAWDOWN`` 与 ``COLOR_RETURN`` 为预定义颜色字符串；
        - ``SIGMA_LEVELS`` 长度为 6（覆盖 ±1/±2/±3 sigma）；
        - ``MONTH_LABELS`` 长度为 12（一月到十二月）；
        - ``figure_to_html`` 在两种模式下分别返回 Figure 与 str。
    """
    from czsc.utils.plotting.common import (
        COLOR_DRAWDOWN,
        COLOR_RETURN,
        MONTH_LABELS,
        SIGMA_LEVELS,
        figure_to_html,
    )

    # 测试常量
    assert COLOR_DRAWDOWN == "salmon"
    assert COLOR_RETURN == "#34a853"
    assert len(SIGMA_LEVELS) == 6
    assert len(MONTH_LABELS) == 12

    # 测试 figure_to_html
    import plotly.graph_objects as go

    fig = go.Figure()

    # 测试返回 Figure
    result = figure_to_html(fig, to_html=False)
    assert isinstance(result, go.Figure)

    # 测试返回 HTML
    result = figure_to_html(fig, to_html=True)
    assert isinstance(result, str)
    assert "plotly" in result.lower()


def test_plotting_backtest_imports():
    """验证回测绘图模块的关键 API 可以从 ``czsc.utils.plotting`` 顶层导入。

    关键断言：
        ``plot_cumulative_returns``、``plot_colored_table``、``plot_czsc_chart``
        三个函数均可被导入且为可调用对象。
    """
    from czsc.utils.plotting import (
        plot_colored_table,
        plot_cumulative_returns,
        plot_czsc_chart,
    )

    assert callable(plot_cumulative_returns)
    assert callable(plot_colored_table)
    assert callable(plot_czsc_chart)


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


def test_crypto_module():
    """验证加密子包 ``czsc.utils.crypto`` 的密钥生成与往返加密能力。

    测试场景：
        1. 生成 Fernet 密钥；
        2. 用该密钥对字典做加密；
        3. 用同一密钥解密并以字典形式还原。

    关键断言：
        - 密钥与密文类型为 ``bytes`` 或 ``str``（Fernet 实现允许两种形式）；
        - 解密后字典与原始字典完全一致。
    """
    from czsc.utils.crypto import (
        fernet_decrypt,
        fernet_encrypt,
        generate_fernet_key,
    )

    key = generate_fernet_key()
    assert isinstance(key, (bytes, str))  # 密钥既可能是 bytes 也可能是 str

    text = {"account": "test", "password": "123"}
    encrypted = fernet_encrypt(text, key)
    assert isinstance(encrypted, (bytes, str))

    decrypted = fernet_decrypt(encrypted, key, is_dict=True)
    assert decrypted == text


def test_analysis_stats_imports():
    """验证统计分析模块 ``czsc.utils.analysis`` 的关键函数可被导入。

    关键断言：
        ``daily_performance``、``holds_performance``、``top_drawdowns`` 三个统计
        函数均为可调用对象。
    """
    from czsc.utils.analysis import (
        daily_performance,
        holds_performance,
        top_drawdowns,
    )

    assert callable(daily_performance)
    assert callable(holds_performance)
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
    """验证向后兼容性：重构前的旧导入路径仍然可用。

    测试场景：
        在重构后，仍然支持从 ``czsc.utils`` 顶层直接导入历史接口，包括：
        ``DataClient``、``DiskCache``、``KlineChart``、``daily_performance``、
        ``generate_fernet_key``、``home_path``、``plot_colored_table`` 等。

    关键断言：
        - 各个名称都能成功导入；
        - 类对象 / 路径对象不为 None；
        - 函数对象 ``callable(...)`` 为真。
    """
    # 测试从主utils导入
    from czsc.utils import (
        DataClient,
        DiskCache,
        KlineChart,
        daily_performance,
        generate_fernet_key,
        home_path,
    )

    assert home_path is not None
    assert DiskCache is not None
    assert DataClient is not None
    assert callable(generate_fernet_key)
    assert callable(daily_performance)
    assert KlineChart is not None

    # 测试向后兼容性 - 通过 czsc.utils 的 __init__.py 重新导出
    from czsc.utils import DiskCache, generate_fernet_key, plot_colored_table

    assert callable(plot_colored_table)
    assert DiskCache is not None
    assert callable(generate_fernet_key)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
