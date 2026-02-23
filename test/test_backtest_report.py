"""测试 backtest_report 模块的功能"""
import sys
sys.path.append("..")
sys.path.insert(0, ".")
import czsc
from czsc.utils.backtest_report import generate_backtest_report



def test_generate_html_report():
    """测试生成 HTML 报告"""
    dfw = czsc.mock.generate_klines_with_weights()
    
    assert len(dfw) > 0, "测试数据不应为空"
    assert dfw['symbol'].nunique() > 0, "应有多个标的"
    
    output_path = "test_backtest_report.html"
    
    result_path = generate_backtest_report(
        df=dfw,
        output_path=output_path,
        title="测试权重回测报告",
        fee_rate=0.00,
        digits=2,
        weight_type="ts",
        yearly_days=252
    )
    assert result_path is not None, "生成报告路径不应为None"


if __name__ == "__main__":
    success = test_generate_html_report()
    if success:
        print("\n测试成功！")
    else:
        print("\n测试失败！")
        exit(1)
