"""
PDF 报告构建器

提供灵活的 PDF 报告生成功能，支持链式调用和按需添加内容元素。
使用 reportlab 库生成专业的量化金融 PDF 报告，支持中文文本、Plotly 图表嵌入和数据表格。
"""

import io
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether,
)

# ---------------------------------------------------------------------------
# 注册中文字体（reportlab 内置 CID 字体，无需外部字体文件）
# ---------------------------------------------------------------------------
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

# ---------------------------------------------------------------------------
# 颜色常量（与 HTML 报告主题一致）
# ---------------------------------------------------------------------------
COLOR_PRIMARY = HexColor("#007bff")
COLOR_SUCCESS = HexColor("#28a745")
COLOR_DANGER = HexColor("#dc3545")
COLOR_WARNING = HexColor("#ffc107")
COLOR_SECONDARY = HexColor("#6c757d")
COLOR_LIGHT = HexColor("#f8f9fa")
COLOR_DARK = HexColor("#212529")
COLOR_BORDER = HexColor("#dee2e6")

COLOR_SUCCESS_BG = HexColor("#d4edda")
COLOR_DANGER_BG = HexColor("#f8d7da")
COLOR_PRIMARY_BG = HexColor("#cce5ff")

# ---------------------------------------------------------------------------
# 页面布局常量
# ---------------------------------------------------------------------------
PAGE_SIZE = landscape(A4)
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE
MARGIN_TOP = 1.5 * cm
MARGIN_BOTTOM = 1.5 * cm
MARGIN_LEFT = 2 * cm
MARGIN_RIGHT = 2 * cm
CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
CM_TO_PX = 96 / 2.54  # 96 DPI / 2.54 cm per inch ≈ 37.795
CARD_SPACING = 4  # 指标卡片间距（pt）

FONT_NAME = "STSong-Light"
FONT_NAME_BOLD = "STSong-Light"  # CID 字体无独立粗体，用同一字体


def _build_styles() -> Dict[str, ParagraphStyle]:
    """构建报告中使用的段落样式集合。"""
    base = getSampleStyleSheet()
    styles: Dict[str, ParagraphStyle] = {}

    styles["title"] = ParagraphStyle(
        "PDFTitle", parent=base["Title"], fontName=FONT_NAME, fontSize=22,
        leading=28, textColor=COLOR_DARK, alignment=TA_LEFT, spaceAfter=4,
    )
    styles["subtitle"] = ParagraphStyle(
        "PDFSubtitle", parent=base["Normal"], fontName=FONT_NAME, fontSize=11,
        leading=16, textColor=COLOR_SECONDARY, alignment=TA_LEFT, spaceAfter=8,
    )
    styles["section_title"] = ParagraphStyle(
        "PDFSectionTitle", parent=base["Heading2"], fontName=FONT_NAME, fontSize=14,
        leading=20, textColor=COLOR_PRIMARY, spaceBefore=12, spaceAfter=6,
    )
    styles["body"] = ParagraphStyle(
        "PDFBody", parent=base["Normal"], fontName=FONT_NAME, fontSize=9,
        leading=14, textColor=COLOR_DARK, spaceAfter=6,
    )
    styles["badge"] = ParagraphStyle(
        "PDFBadge", parent=base["Normal"], fontName=FONT_NAME, fontSize=8,
        leading=12, textColor=COLOR_SECONDARY, alignment=TA_CENTER,
    )
    styles["metric_value"] = ParagraphStyle(
        "PDFMetricValue", parent=base["Normal"], fontName=FONT_NAME, fontSize=16,
        leading=22, alignment=TA_CENTER, spaceAfter=2,
    )
    styles["metric_label"] = ParagraphStyle(
        "PDFMetricLabel", parent=base["Normal"], fontName=FONT_NAME, fontSize=8,
        leading=12, textColor=COLOR_SECONDARY, alignment=TA_CENTER,
    )
    styles["footer"] = ParagraphStyle(
        "PDFFooter", parent=base["Normal"], fontName=FONT_NAME, fontSize=8,
        leading=12, textColor=COLOR_SECONDARY, alignment=TA_CENTER,
    )
    styles["table_header"] = ParagraphStyle(
        "PDFTableHeader", parent=base["Normal"], fontName=FONT_NAME, fontSize=8,
        leading=12, textColor=colors.white, alignment=TA_CENTER,
    )
    styles["table_cell"] = ParagraphStyle(
        "PDFTableCell", parent=base["Normal"], fontName=FONT_NAME, fontSize=8,
        leading=12, textColor=COLOR_DARK, alignment=TA_CENTER,
    )
    return styles


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------

def _fig_to_image_bytes(fig, width: float, height: float) -> bytes:
    """将 Plotly Figure 转换为 PNG 字节流。

    :param fig: plotly.graph_objects.Figure 对象
    :param width: 图片宽度（像素）
    :param height: 图片高度（像素）
    :return: PNG 格式字节流
    """
    return fig.to_image(format="png", width=int(width), height=int(height), scale=2)


def _make_metric_cell(value_text: str, label_text: str, is_positive: Optional[bool],
                      styles: Dict[str, ParagraphStyle], cell_width: float) -> Table:
    """创建单个指标卡片（作为内嵌 Table 返回）。

    :param value_text: 指标值文本
    :param label_text: 指标标签文本
    :param is_positive: 正向/负向/中性 (True/False/None)
    :param styles: 样式字典
    :param cell_width: 单元格宽度
    :return: reportlab Table 对象
    """
    if is_positive is True:
        val_color = COLOR_SUCCESS
        bg_color = COLOR_SUCCESS_BG
    elif is_positive is False:
        val_color = COLOR_DANGER
        bg_color = COLOR_DANGER_BG
    else:
        val_color = COLOR_PRIMARY
        bg_color = COLOR_PRIMARY_BG

    val_style = ParagraphStyle(
        "mv", parent=styles["metric_value"], textColor=val_color,
    )
    val_para = Paragraph(str(value_text), val_style)
    lbl_para = Paragraph(str(label_text), styles["metric_label"])

    card = Table([[val_para], [lbl_para]], colWidths=[cell_width], rowHeights=[28, 18])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg_color),
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    return card


# ---------------------------------------------------------------------------
# PdfReportBuilder 类
# ---------------------------------------------------------------------------

class PdfReportBuilder:
    """PDF 报告构建器

    支持链式调用，按需添加各种元素，生成专业的量化金融 PDF 报告。

    示例用法::

        builder = PdfReportBuilder(title="策略回测报告", author="CZSC")
        builder.add_header({"日期": "2024-01-01", "版本": "v1.0"}, subtitle="沪深300增强策略") \\
               .add_metrics([{"label": "年化收益", "value": "15.3%", "is_positive": True}]) \\
               .add_chart(fig, title="累计收益曲线") \\
               .add_table(df, title="持仓明细") \\
               .add_section("风险提示", "本报告仅供参考。") \\
               .add_footer() \\
               .save("report.pdf")
    """

    def __init__(self, title: str = "PDF 报告", author: str = "CZSC"):
        """初始化 PDF 报告构建器

        :param title: 报告标题
        :param author: 报告作者
        """
        self.title = title
        self.author = author
        self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._styles = _build_styles()
        self._elements: List[Any] = []  # Platypus flowable 列表
        self._footer_text: Optional[str] = None
        self._temp_files: List[str] = []  # 临时文件路径，save/render 后清理

    # ----- 链式方法 --------------------------------------------------------

    def add_header(self, params: Dict[str, str], subtitle: str = None) -> "PdfReportBuilder":
        """添加报告头部区域

        :param params: 参数字典，如 {"日期": "2024-01-01", "版本": "v1.0"}
        :param subtitle: 副标题
        :return: self，支持链式调用
        """
        # 标题
        self._elements.append(Paragraph(self.title, self._styles["title"]))

        # 副标题
        if subtitle:
            self._elements.append(Paragraph(subtitle, self._styles["subtitle"]))

        # 参数徽章行 —— 均匀分布到整个内容宽度
        if params:
            badge_cells = []
            for key, value in params.items():
                badge_cells.append(Paragraph(f"{key}: {value}", self._styles["badge"]))

            n_badges = len(badge_cells)
            badge_width = CONTENT_WIDTH / max(n_badges, 1)
            badge_table = Table([badge_cells], colWidths=[badge_width] * n_badges)
            badge_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("ROUNDEDCORNERS", [3, 3, 3, 3]),
            ]))
            self._elements.append(Spacer(1, 6))
            self._elements.append(badge_table)

        # 分隔线
        self._elements.append(Spacer(1, 8))
        self._elements.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=10))
        return self

    def add_metrics(self, metrics: List[Dict[str, Any]], title: str = "核心绩效指标") -> "PdfReportBuilder":
        """添加绩效指标卡片

        :param metrics: 指标列表，每个元素为 {"label": str, "value": str, "is_positive": bool/None}
        :param title: 区域标题
        :return: self，支持链式调用
        """
        self._elements.append(Paragraph(title, self._styles["section_title"]))

        cols_per_row = 5
        card_width = (CONTENT_WIDTH - (cols_per_row - 1) * CARD_SPACING) / cols_per_row

        rows: List[list] = []
        current_row: list = []
        for m in metrics:
            card = _make_metric_cell(
                value_text=str(m.get("value", "")),
                label_text=str(m.get("label", "")),
                is_positive=m.get("is_positive"),
                styles=self._styles,
                cell_width=card_width,
            )
            current_row.append(card)
            if len(current_row) == cols_per_row:
                rows.append(current_row)
                current_row = []
        if current_row:
            # 补齐空单元格
            while len(current_row) < cols_per_row:
                current_row.append("")
            rows.append(current_row)

        grid = Table(rows, colWidths=[card_width + CARD_SPACING] * cols_per_row)
        grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        self._elements.append(grid)
        self._elements.append(Spacer(1, 8))
        return self

    def add_chart(self, fig_or_image, title: str = "图表", height: float = 10.0) -> "PdfReportBuilder":
        """添加图表

        支持 Plotly Figure 对象（通过 kaleido 转为 PNG）或图片文件路径。

        :param fig_or_image: Plotly Figure 对象 或 图片文件路径字符串
        :param title: 图表标题
        :param height: 图表高度（单位：cm）
        :return: self，支持链式调用
        """
        self._elements.append(Paragraph(title, self._styles["section_title"]))

        img_height = height * cm
        img_width = CONTENT_WIDTH

        if isinstance(fig_or_image, str):
            # 图片文件路径
            img = Image(fig_or_image, width=img_width, height=img_height)
        else:
            # Plotly Figure → PNG bytes
            px_width = int(img_width / cm * CM_TO_PX)
            px_height = int(img_height / cm * CM_TO_PX)
            png_bytes = _fig_to_image_bytes(fig_or_image, width=px_width, height=px_height)

            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.write(png_bytes)
            tmp.close()
            self._temp_files.append(tmp.name)
            img = Image(tmp.name, width=img_width, height=img_height)

        # 包裹图表在带边框的 Table 中
        chart_table = Table([[img]], colWidths=[CONTENT_WIDTH])
        chart_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ]))
        self._elements.append(chart_table)
        self._elements.append(Spacer(1, 8))
        return self

    def add_table(self, df: pd.DataFrame, title: str = "数据表",
                  max_rows: int = None) -> "PdfReportBuilder":
        """添加数据表格

        :param df: pandas DataFrame
        :param title: 表格标题
        :param max_rows: 最大显示行数，None 表示全部显示
        :return: self，支持链式调用
        """
        if df.empty:
            return self

        if max_rows and len(df) > max_rows:
            df = df.head(max_rows)

        self._elements.append(Paragraph(title, self._styles["section_title"]))

        # 构建表格数据：表头 + 数据行，每个单元格用 Paragraph 包裹以支持中文和自动换行
        header_row = [Paragraph(str(c), self._styles["table_header"]) for c in df.columns]
        data_rows = []
        for _, row in df.iterrows():
            data_rows.append([Paragraph(str(v), self._styles["table_cell"]) for v in row])

        table_data = [header_row] + data_rows
        n_cols = len(df.columns)
        col_width = CONTENT_WIDTH / n_cols

        tbl = Table(table_data, colWidths=[col_width] * n_cols, repeatRows=1)

        # 表格样式：表头深蓝背景 + 交替行颜色
        style_commands = [
            # 表头
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            # 边框
            ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("LINEBELOW", (0, 0), (-1, 0), 1, COLOR_PRIMARY),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, COLOR_BORDER),
        ]
        # 交替行背景色
        for i in range(1, len(table_data)):
            bg = COLOR_LIGHT if i % 2 == 0 else colors.white
            style_commands.append(("BACKGROUND", (0, i), (-1, i), bg))

        tbl.setStyle(TableStyle(style_commands))
        self._elements.append(tbl)
        self._elements.append(Spacer(1, 8))
        return self

    def add_section(self, title: str, content: str) -> "PdfReportBuilder":
        """添加文本章节

        :param title: 章节标题
        :param content: 章节内容（纯文本或简单 HTML）
        :return: self，支持链式调用
        """
        self._elements.append(Paragraph(title, self._styles["section_title"]))
        self._elements.append(Paragraph(content, self._styles["body"]))
        self._elements.append(Spacer(1, 6))
        return self

    def add_footer(self, text: str = None) -> "PdfReportBuilder":
        """设置页脚文本

        :param text: 页脚文本，None 则使用默认文本
        :return: self，支持链式调用
        """
        if text is None:
            text = f"由 CZSC 缠中说禅技术分析工具生成 | 作者: {self.author} | 生成时间: {self.created_at}"
        self._footer_text = text
        return self

    # ----- 页面模板回调 ----------------------------------------------------

    def _draw_page_header(self, canvas, doc):
        """在每页顶部绘制页眉。"""
        canvas.saveState()
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(COLOR_SECONDARY)
        canvas.drawString(MARGIN_LEFT, PAGE_HEIGHT - MARGIN_TOP + 6, self.title)
        canvas.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - MARGIN_TOP + 6, self.created_at)
        canvas.setStrokeColor(COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_LEFT, PAGE_HEIGHT - MARGIN_TOP + 2, PAGE_WIDTH - MARGIN_RIGHT, PAGE_HEIGHT - MARGIN_TOP + 2)
        canvas.restoreState()

    def _draw_page_footer(self, canvas, doc):
        """在每页底部绘制页脚和页码。"""
        canvas.saveState()
        canvas.setStrokeColor(COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN_LEFT, MARGIN_BOTTOM - 2, PAGE_WIDTH - MARGIN_RIGHT, MARGIN_BOTTOM - 2)

        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(COLOR_SECONDARY)
        footer = self._footer_text or ""
        canvas.drawString(MARGIN_LEFT, MARGIN_BOTTOM - 14, footer)
        canvas.drawRightString(PAGE_WIDTH - MARGIN_RIGHT, MARGIN_BOTTOM - 14, f"第 {doc.page} 页")
        canvas.restoreState()

    def _on_page(self, canvas, doc):
        """每页回调：绘制页眉和页脚。"""
        self._draw_page_header(canvas, doc)
        self._draw_page_footer(canvas, doc)

    # ----- 输出方法 --------------------------------------------------------

    def render(self) -> bytes:
        """渲染 PDF 并返回字节流

        :return: PDF 文件的字节内容
        """
        buf = io.BytesIO()
        try:
            self._build_doc(buf)
            return buf.getvalue()
        finally:
            buf.close()
            self._cleanup_temp_files()

    def save(self, file_path: str) -> str:
        """保存 PDF 报告到文件

        :param file_path: 输出文件路径
        :return: 文件路径
        """
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        try:
            with open(file_path, "wb") as f:
                f.write(self.render())
        finally:
            self._cleanup_temp_files()
        return file_path

    # ----- 内部方法 --------------------------------------------------------

    def _build_doc(self, output):
        """构建 PDF 文档并写入到 output（文件对象或 BytesIO）。

        注意：reportlab 的 ``doc.build()`` 会就地消费 elements 列表，因此这里使用浅拷贝
        以保证 ``render()`` / ``save()`` 可被多次调用。
        """
        doc = SimpleDocTemplate(
            output,
            pagesize=PAGE_SIZE,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            leftMargin=MARGIN_LEFT,
            rightMargin=MARGIN_RIGHT,
            title=self.title,
            author=self.author,
        )
        doc.build(list(self._elements), onFirstPage=self._on_page, onLaterPages=self._on_page)

    def _cleanup_temp_files(self):
        """清理临时图片文件。"""
        for fp in self._temp_files:
            try:
                os.unlink(fp)
            except OSError:
                pass
        self._temp_files.clear()
