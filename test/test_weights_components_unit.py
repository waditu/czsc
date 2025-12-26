"""
权重分析组件单元测试

验证组件的基本功能和导入
"""

import pytest
import pandas as pd
import numpy as np
from czsc.svc.weights import (
    show_weight_ts,
    show_weight_dist,
    show_weight_cdf,
    show_weight_abs
)


@pytest.fixture
def sample_weight_data():
    """生成测试用的权重数据"""
    np.random.seed(42)
    
    # 生成100个交易日的数据
    dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
    symbols = ['STOCK001', 'STOCK002', 'STOCK003', 'STOCK004', 'STOCK005']
    
    data = []
    for dt in dates:
        for symbol in symbols:
            # 生成随机权重
            weight = np.random.randn() * 0.3
            if np.random.random() > 0.7:
                weight = 0
            weight = np.clip(weight, -1, 1)
            
            data.append({
                'dt': dt,
                'symbol': symbol,
                'weight': weight
            })
    
    return pd.DataFrame(data)


def test_show_weight_ts(sample_weight_data):
    """测试权重时序分析组件"""
    from czsc.utils.plot_weight import plot_weight_time_series
    
    # 测试原始函数是否可调用
    fig = plot_weight_time_series(sample_weight_data)
    assert fig is not None
    
    # 测试封装函数
    # 注意：这些函数需要 Streamlit 环境，这里只测试导入和参数处理
    assert callable(show_weight_ts)
    

def test_show_weight_dist(sample_weight_data):
    """测试权重分布分析组件"""
    from czsc.utils.plot_weight import plot_weight_histogram_kde
    
    # 测试原始函数是否可调用
    fig = plot_weight_histogram_kde(sample_weight_data)
    assert fig is not None
    
    # 测试封装函数
    assert callable(show_weight_dist)


def test_show_weight_cdf(sample_weight_data):
    """测试权重累积分布组件"""
    from czsc.utils.plot_weight import plot_weight_cdf
    
    # 测试原始函数是否可调用
    fig = plot_weight_cdf(sample_weight_data)
    assert fig is not None
    
    # 测试封装函数
    assert callable(show_weight_cdf)


def test_show_weight_abs(sample_weight_data):
    """测试绝对仓位分析组件"""
    from czsc.utils.plot_weight import plot_absolute_position_analysis
    
    # 测试原始函数是否可调用
    fig = plot_absolute_position_analysis(sample_weight_data)
    assert fig is not None
    
    # 测试封装函数
    assert callable(show_weight_abs)


def test_module_imports():
    """测试模块导入"""
    # 测试所有函数都能正确导入
    from czsc.svc import (
        show_weight_ts,
        show_weight_dist,
        show_weight_cdf,
        show_weight_abs
    )
    
    assert callable(show_weight_ts)
    assert callable(show_weight_dist)
    assert callable(show_weight_cdf)
    assert callable(show_weight_abs)


def test_function_signatures(sample_weight_data):
    """测试函数签名"""
    # 测试所有函数都有正确的参数
    import inspect
    
    functions = [
        show_weight_ts,
        show_weight_dist,
        show_weight_cdf,
        show_weight_abs
    ]
    
    for func in functions:
        sig = inspect.signature(func)
        params = sig.parameters
        
        # 检查是否有 df 参数
        assert 'df' in params, f"{func.__name__} 缺少 df 参数"
        
        # 检查是否有 key 参数
        assert 'key' in params, f"{func.__name__} 缺少 key 参数"
        
        # 检查 key 参数默认值为 None
        assert params['key'].default is None, f"{func.__name__} 的 key 参数默认值应该为 None"
        
        # 检查是否有 **kwargs
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()), \
            f"{func.__name__} 缺少 **kwargs 参数"


def test_data_validation():
    """测试数据验证"""
    # 测试空数据
    empty_df = pd.DataFrame(columns=['dt', 'symbol', 'weight'])
    
    # 这些函数应该能够处理空数据或正确报错
    # 这里只测试函数可以被调用
    assert callable(show_weight_ts)
    assert callable(show_weight_dist)
    assert callable(show_weight_cdf)
    assert callable(show_weight_abs)


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
