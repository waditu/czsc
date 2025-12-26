"""测试 backtest_report 模块的功能"""
import sys
sys.path.append("..")
sys.path.insert(0, ".")
import czsc
from czsc.utils.backtest_report import generate_backtest_report



def test_generate_html_report():
    """测试生成 HTML 报告"""
    print("生成测试数据...")
    dfw = czsc.mock.generate_klines_with_weights()
    
    print(f"数据信息：")
    print(f"  记录数: {len(dfw)}")
    print(f"  标的数: {dfw['symbol'].nunique()}")
    print(f"  时间范围: {dfw['dt'].min()} ~ {dfw['dt'].max()}")
    
    print("\n生成 HTML 报告...")
    output_path = "test_backtest_report.html"
    
    try:
        result_path = generate_backtest_report(
            df=dfw,
            output_path=output_path,
            title="测试权重回测报告",
            fee_rate=0.00,  # 无手续费
            digits=2,
            weight_type="ts",
            yearly_days=252
        )
        print(f"HTML 报告已生成: {result_path}")
        print("请在浏览器中打开该文件查看效果")
        
        # 显示一些基本统计信息
        print("\n回测参数：")
        print(f"  手续费: 0 BP")
        print(f"  权重小数位: 2")
        print(f"  年交易日: 252")
        print(f"  权重类型: ts")
        
        return True
    except Exception as e:
        print(f"生成报告时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_generate_html_report()
    if success:
        print("\n测试成功！")
    else:
        print("\n测试失败！")
        exit(1)
