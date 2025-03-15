import pandas as pd
import numpy as np


def test_daily_performance():
    from czsc import daily_performance

    x = daily_performance([0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01])
    print(x)


def test_weight_backtest():
    from czsc import WeightBacktest
    from test.test_analyze import read_daily

    dfw = read_daily()
    dfw = pd.DataFrame(dfw)
    dfw["weight"] = np.where(dfw["close"] > dfw["open"], 1.0, -1.0)
    dfw["price"] = dfw["close"]
    wb = WeightBacktest(dfw[["dt", "weight", "symbol", "price"]])

    assert wb.stats["夏普"] == -0.0433
