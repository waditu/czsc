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
