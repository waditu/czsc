import pytest
import pandas as pd
from czsc.eda import weights_simple_ensemble


def test_cal_yearly_days():
    if pd.__version__ < "2.1.0":
        pytest.skip("skip this test if pandas version is less than 1.3.0")

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


def test_weights_simple_ensemble_mean():
    df = pd.DataFrame({"strategy1": [0.1, 0.2, 0.3], "strategy2": [0.2, 0.3, 0.4], "strategy3": [0.3, 0.4, 0.5]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="mean")
    expected = pd.Series([0.2, 0.3, 0.4], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


def test_weights_simple_ensemble_vote():
    df = pd.DataFrame({"strategy1": [1, -1, 1], "strategy2": [-1, 1, -1], "strategy3": [1, 1, -1]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="vote")
    expected = pd.Series([1, 1, -1], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


def test_weights_simple_ensemble_sum_clip():
    df = pd.DataFrame({"strategy1": [0.5, -0.5, 0.5], "strategy2": [0.5, 0.5, -0.5], "strategy3": [0.5, 0.5, 0.5]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="sum_clip", clip_min=-1, clip_max=1)
    expected = pd.Series([1, 0.5, 0.5], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


def test_weights_simple_ensemble_only_long():
    df = pd.DataFrame({"strategy1": [0.5, -0.5, 0.5], "strategy2": [0.5, 0.5, -0.5], "strategy3": [0.5, 0.5, 0.5]})
    weight_cols = ["strategy1", "strategy2", "strategy3"]
    result = weights_simple_ensemble(df, weight_cols, method="sum_clip", clip_min=-1, clip_max=1, only_long=True)
    expected = pd.Series([1, 0.5, 0.5], name="weight")
    pd.testing.assert_series_equal(result["weight"], expected)


if __name__ == "__main__":
    pytest.main()
