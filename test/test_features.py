import pytest
import pandas as pd


def test_is_event_feature():
    from czsc.features.utils import is_event_feature

    # 测试事件类因子
    df1 = pd.DataFrame({'factor': [0, 1, -1, 0, 1, -1]})
    assert is_event_feature(df1, 'factor') is True

    # 测试非事件类因子
    df2 = pd.DataFrame({'factor': [0, 1, 2, 3, 4, 5]})
    assert is_event_feature(df2, 'factor') is False
