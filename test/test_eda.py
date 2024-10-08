import pytest
import pandas as pd


def test_cal_yearly_days():
    from czsc.eda import cal_yearly_days

    # Test with a list of dates within a single year
    dts = ["2023-01-01", "2023-01-02", "2023-01-03", "2023-12-31"]
    assert cal_yearly_days(dts) == 252

    # Test with a list of dates spanning more than one year
    dts = ["2022-01-01", "2022-12-31", "2023-01-01", "2023-12-31"]
    assert cal_yearly_days(dts) == 2

    # Test with a list of dates with minute precision
    dts = [
        "2023-01-01 12:00",
        "2023-01-02 13:00",
        "2023-01-01 14:00",
        "2023-02-01 15:00",
        "2023-03-01 16:00",
        "2023-03-01 17:00",
    ]
    assert cal_yearly_days(dts) == 252

    # Test with an empty list
    with pytest.raises(AssertionError):
        cal_yearly_days([])

    # Test with a list of dates with duplicates
    dts = ["2023-01-01", "2023-01-01", "2023-01-02", "2023-01-02"]
    assert cal_yearly_days(dts) == 252
