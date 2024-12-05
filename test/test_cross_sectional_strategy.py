# tests/test_cross_sectional_strategy.py
import pytest
import pandas as pd
from czsc.eda import cross_sectional_strategy


@pytest.fixture
def sample_data():
    data = {
        "dt": [
            "2023-01-01",
            "2023-01-02",
            "2023-01-03",
            "2023-01-04",
            "2023-01-05",
            "2023-01-06",
            "2023-01-07",
            "2023-01-08",
            "2023-01-09",
            "2023-01-10",
        ]
        * 5,
        "symbol": ["A"] * 10 + ["B"] * 10 + ["C"] * 10 + ["D"] * 10 + ["E"] * 10,
        "factor": list(range(1, 51)),
    }
    return pd.DataFrame(data)


def test_cross_sectional_strategy_positive(sample_data):
    result = cross_sectional_strategy(sample_data, factor="factor", long=0.5, short=0.5, factor_direction="positive")
    assert "weight" in result.columns
    assert result["weight"].sum() == 0  # Long and short positions should balance out


def test_cross_sectional_strategy_negative(sample_data):
    result = cross_sectional_strategy(sample_data, factor="factor", long=0.5, short=0.5, factor_direction="negative")
    assert "weight" in result.columns
    assert result["weight"].sum() == 0  # Long and short positions should balance out
    print(result)


def test_cross_sectional_strategy_negative_norm(sample_data):
    result = cross_sectional_strategy(
        sample_data, factor="factor", long=0.5, short=0.5, factor_direction="negative", norm=False
    )
    assert "weight" in result.columns
    assert result["weight"].sum() == 0  # Long and short positions should balance out
    print(result)


def test_cross_sectional_strategy_no_positions(sample_data):
    result = cross_sectional_strategy(sample_data, factor="factor", long=0, short=0)
    assert "weight" in result.columns
    assert result["weight"].sum() == 0  # No positions should be taken


def test_cross_sectional_strategy_invalid_factor(sample_data):
    with pytest.raises(AssertionError):
        cross_sectional_strategy(sample_data, factor="invalid_factor", long=0.5, short=0.5)


def test_cross_sectional_strategy_invalid_factor_direction(sample_data):
    with pytest.raises(AssertionError):
        cross_sectional_strategy(sample_data, factor="factor", long=0.5, short=0.5, factor_direction="invalid")


if __name__ == "__main__":
    pytest.main()
