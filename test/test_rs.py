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


def test_czsc():
    from rs_czsc import CZSC, format_standard_kline, Freq
    from czsc.mock import generate_klines
    
    df = generate_klines(seed=42)
    symbol = df['symbol'].iloc[0]
    df = df[df['symbol'] == symbol].copy()
    bars = format_standard_kline(df, freq=Freq.D)

    c = CZSC(bars)
    bi = c.bi_list[-1]
    sdt = pd.Timestamp.fromtimestamp(bi.sdt)
    