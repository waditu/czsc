"""
HtmlReportBuilder 使用示例

展示如何使用新的 HtmlReportBuilder 类创建灵活的HTML报告
"""

import czsc
from czsc.utils.html_report_builder import HtmlReportBuilder
from czsc.utils.backtest_report import generate_backtest_report
import pandas as pd


def example_basic_usage():
    """基础使用示例"""
    print("示例1：HtmlReportBuilder 基础使用")
    
    # 创建构建器
    builder = HtmlReportBuilder(title="我的第一个HTML报告")
    
    # 添加头部信息
    params = {
        "作者": "量化交易员",
        "日期": "2024-01-15",
        "版本": "v1.0"
    }
    builder.add_header(params, subtitle="展示 HtmlReportBuilder 的基础功能")
    
    # 添加绩效指标
    metrics = [
        {"label": "总收益率", "value": "25.6%", "is_positive": True},
        {"label": "年化收益", "value": "18.3%", "is_positive": True},
        {"label": "最大回撤", "value": "-12.4%", "is_positive": False},
        {"label": "夏普比率", "value": "1.92", "is_positive": True},
        {"label": "胜率", "value": "58.7%", "is_positive": True}
    ]
    builder.add_metrics(metrics)
    
    # 添加页脚
    builder.add_footer()
    
    # 保存报告
    output_path = "example_basic_report.html"
    builder.save(output_path)
    print(f"✓ 基础报告已生成: {output_path}")


def example_chain_calls():
    """链式调用示例"""
    print("\n示例2：链式调用")
    
    # 使用链式调用快速构建报告
    builder = (HtmlReportBuilder(title="链式调用示例")
              .add_header({"项目": "量化策略", "状态": "运行中"})
              .add_metrics([
                  {"label": "今日收益", "value": "+1.2%", "is_positive": True},
                  {"label": "持仓数量", "value": "5", "is_positive": True}
              ])
              .add_section("交易策略", """
              <div class="alert alert-success">
                  <h4>策略概述</h4>
                  <p>基于缠论技术分析的多因子量化策略，结合趋势跟踪和均值回归逻辑。</p>
              </div>
              """)
              .add_footer())
    
    builder.save("example_chain_calls.html")
    print("✓ 链式调用报告已生成: example_chain_calls.html")


def example_custom_content():
    """自定义内容示例"""
    print("\n示例3：自定义内容和样式")
    
    builder = HtmlReportBuilder(title="自定义报告")
    
    # 添加自定义CSS样式
    custom_css = """
    .strategy-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .highlight-text {
        color: #667eea;
        font-weight: bold;
        font-size: 1.2em;
    }
    """
    builder.add_custom_css(custom_css)
    
    # 添加头部
    builder.add_header({"报告类型": "自定义分析"})
    
    # 添加自定义HTML内容
    strategy_html = """
    <div class="strategy-card">
        <h3>🚀 高级量化策略</h3>
        <p>使用 <span class="highlight-text">机器学习</span> 和 <span class="highlight-text">深度学习</span> 技术</p>
        <ul>
            <li>多因子模型</li>
            <li>风险管理优化</li>
            <li>动态仓位调整</li>
        </ul>
    </div>
    """
    builder.add_section("策略详情", strategy_html, icon="bi-rocket")
    
    # 添加数据表格
    data = pd.DataFrame({
        "日期": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"],
        "开盘价": [100.5, 101.2, 99.8, 102.1, 103.5],
        "收盘价": [101.2, 99.8, 102.1, 103.5, 104.2],
        "成交量": [1000000, 1200000, 900000, 1500000, 1100000],
        "涨跌幅": ["+0.7%", "-1.4%", "+2.3%", "+1.4%", "+0.7%"]
    })
    builder.add_table(data, title="最近5个交易日数据", max_rows=10)
    
    # 添加自定义JavaScript
    custom_js = """
    console.log("报告加载完成");
    // 可以添加交互功能
    """
    builder.add_custom_script(custom_js)
    
    builder.add_footer()
    builder.save("example_custom_content.html")
    print("✓ 自定义内容报告已生成: example_custom_content.html")


def example_chart_tabs():
    """图表标签页示例"""
    print("\n示例4：多图表标签页")
    
    builder = HtmlReportBuilder(title="图表分析报告")
    
    # 模拟多个图表的HTML内容
    # 在实际使用中，这些可以是真实的Plotly图表HTML
    charts = {
        "K线图": '<div style="padding: 20px; text-align: center; background: #f0f0f0; height: 400px;">K线图模拟内容</div>',
        "成交量图": '<div style="padding: 20px; text-align: center; background: #e0f0e0; height: 400px;">成交量图模拟内容</div>',
        "指标图": '<div style="padding: 20px; text-align: center; background: #e0e0f0; height: 400px;">技术指标图模拟内容</div>',
        "资金曲线": '<div style="padding: 20px; text-align: center; background: #f0e0e0; height: 400px;">资金曲线模拟内容</div>'
    }
    
    # 添加头部
    builder.add_header({"分析周期": "2024年全年", "数据频率": "日线"})
    
    # 添加多个图表标签页
    icons = ["bi-graph-up", "bi-bar-chart", "bi-activity", "bi-pie-chart"]
    for i, (chart_name, chart_html) in enumerate(charts.items()):
        is_active = (i == 0)  # 第一个图表设为激活状态
        builder.add_chart_tab(chart_name, chart_html, icons[i], active=is_active)
    
    # 生成图表区域
    builder.add_charts_section()
    
    builder.add_footer()
    builder.save("example_chart_tabs.html")
    print("✓ 图表标签页报告已生成: example_chart_tabs.html")


def example_backtest_integration():
    """回测报告集成示例"""
    print("\n示例5：回测报告生成（使用现有功能）")
    
    # 生成模拟的权重数据
    print("正在生成模拟回测数据...")
    dfw = czsc.mock.generate_klines_with_weights()
    
    print(f"数据信息：")
    print(f"  记录数: {len(dfw)}")
    print(f"  标的数: {dfw['symbol'].nunique()}")
    print(f"  时间范围: {dfw['dt'].min()} ~ {dfw['dt'].max()}")
    
    # 使用现有的回测报告生成功能（现在内部使用HtmlReportBuilder）
    print("\n正在生成回测报告...")
    output_path = "example_backtest_report.html"
    
    generate_backtest_report(
        df=dfw,
        output_path=output_path,
        title="量化策略回测报告",
        fee_rate=0.000,  # 无手续费
        digits=2,
        weight_type="ts",
        yearly_days=252
    )
    
    print(f"✓ 回测报告已生成: {output_path}")


def example_complete_report():
    """完整报告示例"""
    print("\n示例6：完整综合报告")
    
    builder = HtmlReportBuilder(title="综合分析报告")
    
    # 1. 头部信息
    params = {
        "分析师": "AI量化系统",
        "报告日期": "2024-01-15",
        "数据周期": "2023-01-01 ~ 2023-12-31",
        "策略类型": "多因子量化"
    }
    builder.add_header(params, subtitle="全市场量化策略综合分析报告")
    
    # 2. 核心绩效指标
    metrics = [
        {"label": "总收益", "value": "45.8%", "is_positive": True},
        {"label": "年化收益", "value": "38.2%", "is_positive": True},
        {"label": "最大回撤", "value": "-15.6%", "is_positive": False},
        {"label": "夏普比率", "value": "2.14", "is_positive": True},
        {"label": "胜率", "value": "62.3%", "is_positive": True},
        {"label": "盈亏比", "value": "2.1", "is_positive": True}
    ]
    builder.add_metrics(metrics, title="核心绩效指标")
    
    # 3. 策略说明
    strategy_content = """
    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">策略特点</h5>
                </div>
                <div class="card-body">
                    <ul>
                        <li>多因子选股模型</li>
                        <li>风险平价仓位管理</li>
                        <li>动态止损止盈</li>
                        <li>跨品种套利</li>
                    </ul>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card">
                <div class="card-header bg-success text-white">
                    <h5 class="mb-0">适用市场</h5>
                </div>
                <div class="card-body">
                    <ul>
                        <li>A股市场</li>
                        <li>期货市场</li>
                        <li>加密货币</li>
                        <li>债券市场</li>
                    </ul>
                </div>
            </div>
        </div>
    </div>
    """
    builder.add_section("策略详情", strategy_content, icon="bi-lightbulb")
    
    # 4. 添加模拟图表
    mock_chart1 = '<div style="padding: 20px; background: #f8f9fa; height: 400px; text-align: center; line-height: 400px;">累计收益曲线图</div>'
    mock_chart2 = '<div style="padding: 20px; background: #e9ecef; height: 400px; text-align: center; line-height: 400px;">回撤分析图</div>'
    mock_chart3 = '<div style="padding: 20px; background: #dee2e6; height: 400px; text-align: center; line-height: 400px;">月度收益热力图</div>'
    
    builder.add_chart_tab("收益分析", mock_chart1, "bi-graph-up", active=True)
    builder.add_chart_tab("风险分析", mock_chart2, "bi-shield")
    builder.add_chart_tab("收益分布", mock_chart3, "bi-calendar3")
    builder.add_charts_section()
    
    # 5. 交易数据表
    trading_data = pd.DataFrame({
        "日期": ["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12"],
        "操作": ["买入", "持有", "加仓", "减仓", "卖出"],
        "标的": ["000001.SZ", "000001.SZ", "600000.SH", "000001.SZ", "600000.SH"],
        "价格": [10.25, 10.40, 11.20, 10.80, 11.50],
        "数量": [1000, 1000, 500, 800, 1500],
        "收益": ["+2.5%", "+1.4%", "+7.7%", "+3.6%", "+12.1%"]
    })
    builder.add_table(trading_data, title="最近交易记录")
    
    # 6. 风险提示
    risk_warning = """
    <div class="alert alert-warning">
        <h4>⚠️ 风险提示</h4>
        <p>本报告仅供参考，不构成投资建议。量化策略存在模型风险、数据风险、市场风险等。投资有风险，入市需谨慎。</p>
    </div>
    """
    builder.add_section("风险提示", risk_warning, icon="bi-exclamation-triangle")
    
    # 7. 页脚
    builder.add_footer("本报告由 CZSC 缠中说禅技术分析工具生成 | 数据来源：模拟数据")
    
    # 保存报告
    builder.save("example_complete_report.html")
    print("✓ 完整报告已生成: example_complete_report.html")


def main():
    """运行所有示例"""
    print("=" * 60)
    print("HtmlReportBuilder 使用示例")
    print("=" * 60)
    
    # 运行各个示例
    example_basic_usage()
    example_chain_calls()
    example_custom_content()
    example_chart_tabs()
    example_backtest_integration()
    example_complete_report()
    
    print("\n" + "=" * 60)
    print("✓ 所有示例执行完成！")
    print("=" * 60)
    print("\n生成的文件列表：")
    print("1. example_basic_report.html - 基础使用示例")
    print("2. example_chain_calls.html - 链式调用示例")
    print("3. example_custom_content.html - 自定义内容示例")
    print("4. example_chart_tabs.html - 图表标签页示例")
    print("5. example_backtest_report.html - 回测报告集成示例")
    print("6. example_complete_report.html - 完整综合报告示例")
    print("\n请在浏览器中打开这些HTML文件查看效果")


if __name__ == "__main__":
    main()
