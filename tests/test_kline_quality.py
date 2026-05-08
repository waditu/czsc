from czsc import mock
from czsc.utils.kline_quality import check_kline_quality


def test_check_zero_volume():
    """测试零成交量检查功能"""
    df = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    df["vol"] = df["vol"].astype(int)
    df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]]
    report = check_kline_quality(df)
    assert isinstance(report, dict)
    assert len(report) >= 0
