import numpy as np


def test_daily_performance():
    from czsc import daily_performance

    x = daily_performance([0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01])
    assert x["夏普"] is not None
    assert x["年化"] is not None
    assert x["最大回撤"] >= 0  # 最大回撤为正值，表示回撤幅度
    assert isinstance(x["夏普"], (int, float))


def test_weight_backtest():
    """测试权重回测功能"""
    from rs_czsc import WeightBacktest

    from czsc import mock

    dfw = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    dfw["weight"] = np.where(dfw["close"] > dfw["open"], 1.0, -1.0)
    dfw["price"] = dfw["close"]
    wb = WeightBacktest(dfw[["dt", "weight", "symbol", "price"]])

    assert "夏普" in wb.stats
    assert isinstance(wb.stats["夏普"], (int, float))
    assert wb.stats["夏普"] != 0


def test_czsc():
    from rs_czsc import CZSC, Freq, format_standard_kline

    from czsc.mock import generate_klines

    df = generate_klines(seed=42)
    symbol = df["symbol"].iloc[0]
    df = df[df["symbol"] == symbol].copy()
    bars = format_standard_kline(df, freq=Freq.D)

    c = CZSC(bars)
    assert len(c.bars_raw) > 0
    assert c.bars_raw[-1].close > 0
    if len(c.bi_list) > 0:
        bi = c.bi_list[-1]
        assert bi is not None
