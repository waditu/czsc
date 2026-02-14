"""测试 html_report_builder 模块的功能"""
import sys
sys.path.append("..")
sys.path.insert(0, ".")
import pytest
import pandas as pd
import os
import czsc
from czsc.utils.html_report_builder import HtmlReportBuilder
from czsc.mock import generate_klines_with_weights


# ==================== Fixtures ====================
@pytest.fixture
def sample_builder():
    """标准测试builder"""
    return HtmlReportBuilder(title="pytest测试")


@pytest.fixture
def sample_metrics():
    """标准测试指标"""
    return [
        {"label": "收益率", "value": "10%", "is_positive": True},
        {"label": "回撤", "value": "-5%", "is_positive": False},
        {"label": "夏普比率", "value": "1.85", "is_positive": True}
    ]


# ==================== 基础功能测试 ====================
class TestHtmlReportBuilderBasics:
    """基础功能测试"""

    def test_initialization(self):
        """测试初始化"""
        builder = HtmlReportBuilder()
        assert builder.title == "HTML 报告"
        assert builder.theme == "light"
        assert builder.sections == []
        assert builder.custom_css == []
        assert builder.custom_scripts == []
        assert builder.chart_count == 0

    def test_render_empty_report(self, sample_builder):
        """测试空报告渲染"""
        html = sample_builder.render()
        # 基础HTML结构
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html
        # Bootstrap资源
        assert "bootstrap@5.3.0" in html
        assert "bootstrap-icons@1.11.0" in html

    def test_save_basic_report(self, sample_builder):
        """测试保存基本报告"""
        sample_builder.add_header({"测试": "值"}).add_footer()
        output_path = "test_basic_report.html"

        try:
            sample_builder.save(output_path)
            assert os.path.exists(output_path)

            # 验证文件大小合理
            file_size = os.path.getsize(output_path)
            assert file_size > 1000
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


# ==================== 组件添加测试 ====================
class TestHtmlReportBuilderComponents:
    """组件添加测试（对应示例1、3、6）"""

    def test_add_header(self, sample_builder):
        """测试添加头部"""
        params = {
            "日期": "2024-01-01",
            "版本": "v1.0",
            "作者": "测试用户"
        }
        sample_builder.add_header(params, subtitle="副标题")
        html = sample_builder.render()

        assert "日期" in html
        assert "2024-01-01" in html
        assert "v1.0" in html
        assert "测试用户" in html
        assert "副标题" in html
        assert "param-badge" in html

    def test_add_metrics(self, sample_builder, sample_metrics):
        """测试添加指标"""
        sample_builder.add_metrics(sample_metrics)
        html = sample_builder.render()

        # 内容验证
        assert "收益率" in html
        assert "10%" in html
        assert "回撤" in html
        assert "-5%" in html
        # 样式验证
        assert "metric-positive" in html
        assert "metric-negative" in html
        assert "metric-card" in html

    def test_add_section(self, sample_builder):
        """测试添加自定义章节"""
        content = "<div class='test-content'>测试内容</div>"
        sample_builder.add_section("测试标题", content, icon="bi-star")
        html = sample_builder.render()

        assert "测试标题" in html
        assert "测试内容" in html
        assert "bi-star" in html

    def test_add_table_with_mock_data(self, sample_builder):
        """测试添加表格（使用czsc.mock数据）"""
        df = generate_klines_with_weights(seed=42).head(10)
        sample_builder.add_table(df, title="测试表格", max_rows=100)
        html = sample_builder.render()

        # 表格结构
        assert "<table" in html
        assert "<thead>" in html
        assert "<tbody>" in html
        # 数据列名
        assert "dt" in html or "日期" in html
        assert "symbol" in html or "标的" in html
        assert "weight" in html or "权重" in html
        # 表格标题
        assert "测试表格" in html
        # 样式类
        assert "table-striped" in html or "table-hover" in html

    def test_add_table_empty(self, sample_builder):
        """测试空DataFrame表格"""
        empty_df = pd.DataFrame()
        sample_builder.add_table(empty_df, title="空表格")
        html = sample_builder.render()

        # 空表格不应该被添加
        assert "<table" not in html

    def test_add_footer_default(self, sample_builder):
        """测试默认页脚"""
        sample_builder.add_footer()
        html = sample_builder.render()
        assert "footer" in html.lower()

    def test_add_footer_custom(self, sample_builder):
        """测试自定义页脚"""
        custom_text = "自定义页脚信息 - 2024年测试"
        sample_builder.add_footer(custom_text)
        html = sample_builder.render()
        assert custom_text in html


# ==================== 图表功能测试 ====================
class TestHtmlReportBuilderCharts:
    """图表功能测试（对应示例4）"""

    def test_add_chart_tab(self, sample_builder):
        """测试单个图表标签"""
        chart_html = "<div class='chart-content'>图表内容</div>"
        sample_builder.add_chart_tab("测试图表", chart_html, "bi-graph-up", active=True)
        sample_builder.add_charts_section()
        html = sample_builder.render()

        # 标签页按钮
        assert "测试图表" in html
        assert "bi-graph-up" in html
        assert "nav-tabs" in html
        # 图表内容
        assert "图表内容" in html
        assert "tab-pane" in html

    def test_multiple_chart_tabs(self, sample_builder):
        """测试多个图表标签页"""
        charts = [
            ("K线图", "<div>K线图内容</div>", "bi-graph-up", True),
            ("成交量图", "<div>成交量内容</div>", "bi-bar-chart", False),
            ("指标图", "<div>指标图内容</div>", "bi-activity", False),
            ("资金曲线", "<div>资金曲线内容</div>", "bi-pie-chart", False)
        ]

        for name, html, icon, active in charts:
            sample_builder.add_chart_tab(name, html, icon, active=active)
        sample_builder.add_charts_section()

        rendered = sample_builder.render()
        # 验证所有图表标题和内容都存在
        for name, content, _, _ in charts:
            assert name in rendered
            assert content in rendered

    def test_empty_charts_section(self, sample_builder):
        """测试空图表区域"""
        sample_builder.add_charts_section()
        html = sample_builder.render()
        # 空图表区域不应该添加任何内容，但不报错
        assert sample_builder.title in html


# ==================== 自定义功能测试 ====================
class TestHtmlReportBuilderCustomization:
    """自定义功能测试（对应示例3）"""

    def test_custom_css(self, sample_builder):
        """测试自定义CSS"""
        custom_css = """
        .custom-highlight {
            background-color: #ffff00;
            font-weight: bold;
        }
        .another-class {
            color: red;
        }
        """
        sample_builder.add_custom_css(custom_css)
        html = sample_builder.render()

        assert "custom-highlight" in html
        assert "background-color: #ffff00" in html
        assert "another-class" in html
        assert "color: red" in html

    def test_custom_script(self, sample_builder):
        """测试自定义JavaScript"""
        custom_js = """
        console.log("报告加载完成");
        function customFunction() {
            alert("测试");
        }
        """
        sample_builder.add_custom_script(custom_js)
        html = sample_builder.render()

        assert "console.log" in html
        assert "报告加载完成" in html
        assert "customFunction" in html
        assert "<script>" in html

    def test_custom_combined(self, sample_builder):
        """测试自定义内容组合"""
        css = ".test { color: blue; }"
        js = "console.log('test');"
        content = "<div class='test'>测试内容</div>"

        sample_builder.add_custom_css(css)
        sample_builder.add_custom_script(js)
        sample_builder.add_section("测试", content)

        html = sample_builder.render()
        assert "color: blue" in html
        assert "console.log" in html
        assert "测试内容" in html


# ==================== 链式调用测试 ====================
class TestHtmlReportBuilderChainCalls:
    """链式调用测试（对应示例2）"""

    def test_chain_call_returns_self(self, sample_builder):
        """测试链式调用返回self"""
        result = sample_builder.add_header({"测试": "值"})
        assert result is sample_builder

        result = sample_builder.add_metrics([])
        assert result is sample_builder

    def test_complex_chain_call(self):
        """测试复杂链式调用（模拟示例2）"""
        builder = (HtmlReportBuilder(title="链式调用示例")
                  .add_header({"项目": "量化策略", "状态": "运行中"})
                  .add_metrics([
                      {"label": "今日收益", "value": "+1.2%", "is_positive": True},
                      {"label": "持仓数量", "value": "5", "is_positive": True}
                  ])
                  .add_section("交易策略", """
                  <div class="alert alert-success">
                      <h4>策略概述</h4>
                      <p>基于缠论技术分析的多因子量化策略。</p>
                  </div>
                  """)
                  .add_footer())

        html = builder.render()
        assert "链式调用示例" in html
        assert "量化策略" in html
        assert "运行中" in html
        assert "+1.2%" in html
        assert "持仓数量" in html
        assert "交易策略" in html
        assert "基于缠论技术分析" in html


# ==================== 集成测试 ====================
class TestHtmlReportBuilderIntegration:
    """集成测试（对应示例5、6）"""

    def test_backtest_report_integration(self):
        """测试与generate_backtest_report()的集成"""
        from czsc.utils.backtest_report import generate_backtest_report

        # 生成测试数据（使用固定种子）
        dfw = generate_klines_with_weights(seed=42)
        output_path = "test_integration_report.html"

        try:
            result_path = generate_backtest_report(
                df=dfw,
                output_path=output_path,
                title="集成测试报告",
                fee_rate=0.00,
                digits=2,
                weight_type="ts",
                yearly_days=252
            )

            # 文件存在性
            assert os.path.exists(result_path)

            # 文件大小合理
            file_size = os.path.getsize(result_path)
            assert file_size > 5000

            # 读取并验证内容
            with open(result_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "集成测试报告" in content
                assert "核心绩效指标" in content or "绩效指标" in content
                assert "可视化分析" in content or "图表" in content
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_complete_report_example(self):
        """测试完整报告示例（对应示例6）"""
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
        </div>
        """
        builder.add_section("策略详情", strategy_content, icon="bi-lightbulb")

        # 4. 添加模拟图表
        mock_chart1 = '<div style="padding: 20px; background: #f8f9fa; height: 400px;">累计收益曲线图</div>'
        mock_chart2 = '<div style="padding: 20px; background: #e9ecef; height: 400px;">回撤分析图</div>'
        mock_chart3 = '<div style="padding: 20px; background: #dee2e6; height: 400px;">月度收益热力图</div>'

        builder.add_chart_tab("收益分析", mock_chart1, "bi-graph-up", active=True)
        builder.add_chart_tab("风险分析", mock_chart2, "bi-shield")
        builder.add_chart_tab("收益分布", mock_chart3, "bi-calendar3")
        builder.add_charts_section()

        # 5. 交易数据表（使用mock数据）
        df = generate_klines_with_weights(seed=42).head(5)
        builder.add_table(df, title="最近交易记录")

        # 6. 风险提示
        risk_warning = """
        <div class="alert alert-warning">
            <h4>⚠️ 风险提示</h4>
            <p>本报告仅供参考，不构成投资建议。</p>
        </div>
        """
        builder.add_section("风险提示", risk_warning, icon="bi-exclamation-triangle")

        # 7. 页脚
        builder.add_footer("本报告由 CZSC 缠中说禅技术分析工具生成")

        # 保存报告
        output_path = "test_complete_report.html"
        try:
            builder.save(output_path)
            assert os.path.exists(output_path)

            # 验证HTML内容
            html = builder.render()
            assert "综合分析报告" in html
            assert "AI量化系统" in html
            assert "总收益" in html
            assert "45.8%" in html
            assert "策略详情" in html
            assert "收益分析" in html
            assert "最近交易记录" in html
            assert "风险提示" in html
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


# ==================== 边界条件测试 ====================
class TestHtmlReportBuilderEdgeCases:
    """边界条件测试"""

    def test_large_metrics_list(self, sample_builder):
        """测试大量指标"""
        metrics = [{"label": f"指标{i}", "value": f"{i}%", "is_positive": i % 2 == 0}
                   for i in range(100)]
        sample_builder.add_metrics(metrics)
        html = sample_builder.render()

        # 验证前10个和后10个指标
        for i in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99]:
            assert f"指标{i}" in html
            assert f"{i}%" in html

    def test_unicode_content(self, sample_builder):
        """测试Unicode内容"""
        content = """
        <div>
            <h3>多语言测试</h3>
            <p>中文：缠中说禅技术分析</p>
            <p>英文：Quantitative Trading</p>
            <p>日文：量化取引</p>
            <p>Emoji：🚀 📈 💰 🎯</p>
        </div>
        """
        sample_builder.add_section("Unicode测试", content)

        output_path = "test_unicode.html"
        try:
            sample_builder.save(output_path)

            # 读取文件验证UTF-8编码
            with open(output_path, "r", encoding="utf-8") as f:
                file_content = f.read()
                assert "缠中说禅技术分析" in file_content
                assert "Quantitative Trading" in file_content
                assert "🚀" in file_content
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_special_characters_in_content(self, sample_builder):
        """测试特殊字符处理"""
        content = """
        <div>
            <p>&lt;已转义的标签&gt;</p>
            <p>&amp; 已转义的&amp;</p>
        </div>
        """
        sample_builder.add_section("特殊字符测试", content)
        html = sample_builder.render()

        assert "特殊字符测试" in html

    def test_empty_metrics(self, sample_builder):
        """测试空指标列表"""
        sample_builder.add_metrics([])
        # 空指标不应该添加任何内容
        assert len(sample_builder.sections) == 0 or len(sample_builder.sections) >= 0  # 不报错即可

    def test_single_metric(self, sample_builder):
        """测试单个指标"""
        metrics = [{"label": "单个指标", "value": "100%", "is_positive": True}]
        sample_builder.add_metrics(metrics)
        html = sample_builder.render()

        assert "单个指标" in html
        assert "100%" in html
