# -*- coding: utf-8 -*-
"""
测试新的绘图模块结构
"""

import pytest
import pandas as pd
import numpy as np


def test_plotting_common_module():
    """测试绘图公共模块的常量和函数"""
    from czsc.utils.plotting.common import (
        COLOR_DRAWDOWN, COLOR_RETURN, SIGMA_LEVELS,
        MONTH_LABELS, figure_to_html, add_year_boundary_lines
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
    assert 'plotly' in result.lower()


def test_plotting_backtest_imports():
    """测试回测绘图模块的导入"""
    from czsc.utils.plotting import (
        plot_cumulative_returns,
        plot_colored_table,
    )
    
    assert callable(plot_cumulative_returns)
    assert callable(plot_colored_table)


def test_plotting_weight_imports():
    """测试权重绘图模块的导入"""
    from czsc.utils.plotting import (
        calculate_turnover_stats,
        calculate_weight_stats,
    )
    
    assert callable(calculate_turnover_stats)
    assert callable(calculate_weight_stats)


def test_data_validators():
    """测试数据验证器"""
    from czsc.utils.data.validators import (
        validate_dataframe_columns,
        validate_datetime_index,
        validate_numeric_column,
    )
    
    # 测试 validate_dataframe_columns
    df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    
    # 正常情况
    validate_dataframe_columns(df, ['a', 'b'], 'test_df')
    
    # 缺少列应该抛出异常
    with pytest.raises(ValueError, match="缺少必需的列"):
        validate_dataframe_columns(df, ['a', 'b', 'c'], 'test_df')
    
    # 测试 validate_datetime_index
    df_with_dt_index = pd.DataFrame(
        {'value': [1, 2, 3]},
        index=pd.date_range('2024-01-01', periods=3)
    )
    validate_datetime_index(df_with_dt_index, 'test_df')
    
    # 非DatetimeIndex应该抛出异常
    with pytest.raises(ValueError, match="必须是 DatetimeIndex"):
        validate_datetime_index(df, 'test_df')
    
    # 测试 validate_numeric_column
    validate_numeric_column(df, 'a', 'test_df')
    
    # 不存在的列
    with pytest.raises(ValueError, match="中不存在列"):
        validate_numeric_column(df, 'nonexistent', 'test_df')


def test_data_converters():
    """测试数据转换器"""
    from czsc.utils.data.converters import (
        to_standard_kline_format,
        pivot_weight_data,
        normalize_symbol,
    )
    
    # 测试 to_standard_kline_format
    df = pd.DataFrame({
        'datetime': pd.date_range('2024-01-01', periods=3),
        'open': [100, 101, 102],
        'high': [105, 106, 107],
        'low': [99, 100, 101],
        'close': [103, 104, 105],
        'volume': [1000, 1100, 1200]
    })
    
    result = to_standard_kline_format(
        df,
        dt_col='datetime',
        volume_col='volume'
    )
    
    assert 'dt' in result.columns
    assert 'open' in result.columns
    assert 'vol' in result.columns
    assert isinstance(result['dt'].iloc[0], pd.Timestamp)
    
    # 测试 normalize_symbol
    assert normalize_symbol(' aapl ') == 'AAPL'
    assert normalize_symbol('  tsla  ') == 'TSLA'


def test_crypto_module():
    """测试加密模块"""
    from czsc.utils.crypto import (
        generate_fernet_key,
        fernet_encrypt,
        fernet_decrypt,
    )
    
    key = generate_fernet_key()
    assert isinstance(key, (bytes, str))  # Key can be bytes or string
    
    text = {"account": "test", "password": "123"}
    encrypted = fernet_encrypt(text, key)
    assert isinstance(encrypted, (bytes, str))
    
    decrypted = fernet_decrypt(encrypted, key, is_dict=True)
    assert decrypted == text


def test_analysis_stats_imports():
    """测试统计分析模块的导入"""
    from czsc.utils.analysis import (
        daily_performance,
        holds_performance,
        top_drawdowns,
    )
    
    assert callable(daily_performance)
    assert callable(holds_performance)
    assert callable(top_drawdowns)


def test_analysis_corr_imports():
    """测试相关性分析模块的导入"""
    from czsc.utils.analysis import (
        nmi_matrix,
        single_linear,
        cross_sectional_ic,
    )
    
    assert callable(nmi_matrix)
    assert callable(single_linear)
    assert callable(cross_sectional_ic)


def test_analysis_events_imports():
    """测试事件分析模块的导入"""
    from czsc.utils.analysis import overlap
    
    assert callable(overlap)


def test_backward_compatibility():
    """测试向后兼容性 - 旧的导入路径仍然可用"""
    # 测试从主utils导入
    from czsc.utils import (
        home_path,
        DiskCache,
        DataClient,
        generate_fernet_key,
        daily_performance,
        overlap,
        KlineChart,
    )
    
    assert home_path is not None
    assert DiskCache is not None
    assert DataClient is not None
    assert callable(generate_fernet_key)
    assert callable(daily_performance)
    assert callable(overlap)
    assert KlineChart is not None
    
    # 测试向后兼容性 - 通过 czsc.utils 的 __init__.py 重新导出
    from czsc.utils import plot_colored_table
    from czsc.utils import DiskCache
    from czsc.utils import generate_fernet_key
    
    assert callable(plot_colored_table)
    assert DiskCache is not None
    assert callable(generate_fernet_key)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
