"""测试 PDF 报告生成模块的功能"""
import sys

sys.path.append("..")
sys.path.insert(0, ".")
import os
import pytest
import pandas as pd
import czsc
from czsc.utils.pdf_report_builder import PdfReportBuilder
from czsc.utils.backtest_report import generate_pdf_backtest_report
from czsc.mock import generate_klines_with_weights


# ==================== PdfReportBuilder 基础功能测试 ====================


class TestPdfReportBuilderBasics:
    """PdfReportBuilder 基础功能测试"""

    def test_initialization(self):
        """测试初始化"""
        builder = PdfReportBuilder()
        assert builder.title == "PDF 报告"
        assert builder.author == "CZSC"

    def test_initialization_custom(self):
        """测试自定义初始化"""
        builder = PdfReportBuilder(title="自定义报告", author="测试作者")
        assert builder.title == "自定义报告"
        assert builder.author == "测试作者"

    def test_render_empty_report(self):
        """测试空报告渲染"""
        builder = PdfReportBuilder(title="空报告")
        pdf_bytes = builder.render()
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"
        assert len(pdf_bytes) > 100

    def test_save_basic_report(self):
        """测试保存基本报告"""
        builder = PdfReportBuilder(title="基本报告")
        builder.add_header({"测试": "值"}).add_footer()

        output_path = "test_basic_pdf_report.pdf"
        try:
            result = builder.save(output_path)
            assert os.path.exists(result)
            assert os.path.getsize(result) > 500
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


# ==================== PdfReportBuilder 组件测试 ====================


class TestPdfReportBuilderComponents:
    """PdfReportBuilder 组件添加测试"""

    def test_add_header(self):
        """测试添加头部"""
        builder = PdfReportBuilder(title="头部测试报告")
        result = builder.add_header(
            {"日期范围": "2024-01-01 ~ 2024-12-31", "标的数": "17"},
            subtitle="测试副标题",
        )
        assert result is builder  # 链式调用

        pdf_bytes = builder.render()
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 500

    def test_add_metrics(self):
        """测试添加指标"""
        builder = PdfReportBuilder(title="指标测试")
        metrics = [
            {"label": "年化收益率", "value": "15.30%", "is_positive": True},
            {"label": "最大回撤", "value": "-8.50%", "is_positive": False},
            {"label": "夏普比率", "value": "1.85", "is_positive": True},
        ]
        result = builder.add_metrics(metrics)
        assert result is builder

        pdf_bytes = builder.render()
        assert len(pdf_bytes) > 500

    def test_add_section(self):
        """测试添加文本章节"""
        builder = PdfReportBuilder(title="章节测试")
        result = builder.add_section("风险提示", "本报告仅供参考，不构成投资建议。")
        assert result is builder

        pdf_bytes = builder.render()
        assert len(pdf_bytes) > 500

    def test_add_table(self):
        """测试添加表格"""
        builder = PdfReportBuilder(title="表格测试")
        df = pd.DataFrame({"策略": ["A", "B"], "年化": ["15%", "12%"], "夏普": [1.85, 1.52]})
        result = builder.add_table(df, title="策略对比")
        assert result is builder

        pdf_bytes = builder.render()
        assert len(pdf_bytes) > 500

    def test_add_table_empty(self):
        """测试空表格"""
        builder = PdfReportBuilder(title="空表格测试")
        result = builder.add_table(pd.DataFrame(), title="空表格")
        assert result is builder

    def test_add_table_with_max_rows(self):
        """测试限制行数"""
        builder = PdfReportBuilder(title="限行测试")
        df = pd.DataFrame({"col": range(100)})
        builder.add_table(df, title="大表格", max_rows=5)
        pdf_bytes = builder.render()
        assert len(pdf_bytes) > 500

    def test_add_footer_default(self):
        """测试默认页脚"""
        builder = PdfReportBuilder(title="页脚测试")
        result = builder.add_footer()
        assert result is builder
        assert builder._footer_text is not None

    def test_add_footer_custom(self):
        """测试自定义页脚"""
        builder = PdfReportBuilder(title="自定义页脚")
        builder.add_footer("自定义页脚文本 - 2024")
        assert builder._footer_text == "自定义页脚文本 - 2024"


# ==================== 链式调用测试 ====================


class TestPdfReportBuilderChainCalls:
    """链式调用测试"""

    def test_complex_chain_call(self):
        """测试复杂链式调用"""
        output_path = "test_chain_pdf.pdf"
        try:
            builder = (
                PdfReportBuilder(title="链式调用报告")
                .add_header({"项目": "量化策略", "状态": "运行中"}, subtitle="策略分析")
                .add_metrics([
                    {"label": "收益率", "value": "+10%", "is_positive": True},
                    {"label": "回撤", "value": "-5%", "is_positive": False},
                ])
                .add_section("说明", "基于缠论技术分析的多因子量化策略。")
                .add_table(pd.DataFrame({"A": [1, 2], "B": [3, 4]}), title="数据")
                .add_footer()
            )

            result = builder.save(output_path)
            assert os.path.exists(result)
            assert os.path.getsize(result) > 1000
        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


# ==================== PDF 回测报告生成测试 ====================


class TestGeneratePdfBacktestReport:
    """PDF 回测报告生成测试"""

    def test_generate_pdf_report(self):
        """测试生成 PDF 回测报告"""
        dfw = generate_klines_with_weights(seed=42)

        assert len(dfw) > 0, "测试数据不应为空"
        assert dfw["symbol"].nunique() > 0, "应有多个标的"

        output_path = "test_pdf_backtest_report.pdf"

        try:
            result_path = generate_pdf_backtest_report(
                df=dfw,
                output_path=output_path,
                title="测试PDF回测报告",
                fee_rate=0.00,
                digits=2,
                weight_type="ts",
                yearly_days=252,
            )

            assert result_path is not None, "生成报告路径不应为None"
            assert os.path.exists(result_path), "PDF文件应存在"

            file_size = os.path.getsize(result_path)
            assert file_size > 10000, f"PDF文件应有足够大小，当前: {file_size} bytes"

            # 验证 PDF 格式
            with open(result_path, "rb") as f:
                header = f.read(5)
                assert header == b"%PDF-", "文件应为有效的PDF格式"

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_default_output_path(self):
        """测试默认输出路径"""
        dfw = generate_klines_with_weights(seed=42)
        default_path = os.path.join(os.getcwd(), "backtest_report.pdf")

        try:
            result_path = generate_pdf_backtest_report(
                df=dfw, title="默认路径测试", fee_rate=0.00, digits=2, yearly_days=252
            )
            assert result_path == default_path
            assert os.path.exists(result_path)
        finally:
            if os.path.exists(default_path):
                os.remove(default_path)

    def test_input_validation(self):
        """测试输入数据验证"""
        # 缺少必需列
        with pytest.raises(ValueError, match="数据缺少必需列"):
            generate_pdf_backtest_report(pd.DataFrame({"a": [1]}))

        # 空数据
        with pytest.raises(ValueError, match="输入数据不能为空"):
            generate_pdf_backtest_report(
                pd.DataFrame(columns=["dt", "symbol", "weight", "price"])
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
