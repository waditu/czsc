import pytest
import numpy as np
import pandas as pd


def test_is_event_feature():
    from czsc.features.utils import is_event_feature

    # 测试事件类因子
    df1 = pd.DataFrame({'factor': [0, 1, -1, 0, 1, -1]})
    assert is_event_feature(df1, 'factor') is True

    # 测试非事件类因子
    df2 = pd.DataFrame({'factor': [0, 1, 2, 3, 4, 5]})
    assert is_event_feature(df2, 'factor') is False


def test_rolling_tanh():
    from czsc.features.utils import rolling_tanh

    # Create a dummy dataframe
    df = pd.DataFrame({
        'dt': pd.date_range(start='1/1/2021', periods=500),
        'col1': np.random.rand(500)
    })

    # Apply the rolling_tanh function
    result_df = rolling_tanh(df, 'col1')
    assert 'col1_tanh' in result_df.columns
    assert result_df['col1_tanh'].between(-1, 1).all()

    # Apply the rolling_tanh function
    result_df = rolling_tanh(df, 'col1', new_col='col1_tanh2')
    assert 'col1_tanh2' in result_df.columns
    assert result_df['col1_tanh2'].between(-1, 1).all()

    result_df = rolling_tanh(df, 'col1', new_col='col1_tanh3', window=100, min_periods=50)
    assert 'col1_tanh3' in result_df.columns
    assert result_df['col1_tanh3'].between(-1, 1).all()


def test_normalize_corr():
    from czsc.features.utils import normalize_corr

    np.random.seed(123)
    # Create a fake DataFrame
    df = pd.DataFrame({
        'dt': pd.date_range(start='1/1/2021', periods=3000),
        'symbol': ['AAPL'] * 3000,
        'price': np.random.rand(3000),
        'factor': np.random.rand(3000),
    })

    df['n1b'] = df['price'].shift(-1) / df['price'] - 1
    raw_corr = df['n1b'].corr(df['factor'])

    # Call the function with the fake DataFrame
    result = normalize_corr(df, fcol='factor', copy=True, mode='rolling', window=600)
    corr1 = result['n1b'].corr(result['factor'])
    assert result.shape == df.shape and np.sign(corr1) == -np.sign(raw_corr)

    # Call the function with the fake DataFrame
    result = normalize_corr(df, fcol='factor', copy=True, mode='rolling', window=300)
    corr1 = result['n1b'].corr(result['factor'])
    assert result.shape == df.shape and np.sign(corr1) == np.sign(raw_corr)

    result = normalize_corr(df, fcol='factor', copy=True, mode='rolling', window=2000)
    corr1 = result['n1b'].corr(result['factor'])
    assert result.shape == df.shape and np.sign(corr1) == -np.sign(raw_corr)

    result = normalize_corr(df, fcol='factor', copy=True, mode='simple')
    corr2 = result['n1b'].corr(result['factor'])
    assert result.shape == df.shape and corr2 == -raw_corr
