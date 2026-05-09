from czsc import mock
from czsc.utils.kline_quality import check_kline_quality

_EXPECTED_CHECKS = {
    "missing_values",
    "type_mismatches",
    "datetime_order",
    "price_reasonableness",
    "volume_amount",
    "symbol_consistency",
    "duplicate_records",
    "extreme_values",
}


def test_check_kline_quality_structure():
    """验证 check_kline_quality 返回结构：每个品种含全部 8 个检查分类。"""
    df = mock.generate_symbol_kines("000001", "日线", sdt="20230101", edt="20240101", seed=42)
    df["vol"] = df["vol"].astype(int)
    df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]]
    report = check_kline_quality(df)

    assert isinstance(report, dict), "report 必须是 dict"
    assert len(report) > 0, "report 不得为空——至少应包含被检查的品种"
    assert "000001" in report, "report 中必须包含品种 '000001'"

    symbol_report = report["000001"]
    missing = _EXPECTED_CHECKS - set(symbol_report.keys())
    assert not missing, f"品种报告缺少以下检查分类：{missing}"

    for check_name, result in symbol_report.items():
        assert "description" in result, f"{check_name} 缺少 'description' 字段"
        assert "rows" in result, f"{check_name} 缺少 'rows' 字段"
