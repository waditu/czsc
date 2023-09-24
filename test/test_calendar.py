import pandas as pd
from czsc.utils.calendar import is_trading_date, next_trading_date, prev_trading_date


def test_is_trading_date():
    assert is_trading_date('2023-09-08') == True
    assert is_trading_date('2023-09-09') == False
    assert is_trading_date('2023-09-10') == False


def test_next_trading_date():
    assert next_trading_date('2023-09-09') == pd.Timestamp('2023-09-11')
    assert next_trading_date('2023-09-09', n=2) == pd.Timestamp('2023-09-12')
    assert next_trading_date('2023-09-12', n=1) == pd.Timestamp('2023-09-13')


def test_prev_trading_date():
    assert prev_trading_date('2023-09-09') == pd.Timestamp('2023-09-08')
    assert prev_trading_date('2023-09-09', n=2) == pd.Timestamp('2023-09-07')
    assert prev_trading_date('2023-09-07', n=1) == pd.Timestamp('2023-09-06')


def test_get_trading_dates():
    from czsc.utils.calendar import get_trading_dates
    dates = get_trading_dates('2023-09-08', '2023-09-12')
    assert dates == pd.to_datetime(['2023-09-08', '2023-09-11', '2023-09-12']).tolist()
