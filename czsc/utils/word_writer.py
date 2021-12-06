# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/28 21:22
describe: 实现一个用python-docx写word文档的辅助工具

参考资料：
1. https://cloud.tencent.com/developer/article/1512325
2. https://blog.csdn.net/zhouz92/article/details/107066709
"""
import os
import docx
import pandas as pd
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT


class WordWriter:
    """用 Word 文档记录信息"""

    def __init__(self, file_docx=None):
        self.file_docx = file_docx
        if file_docx and os.path.exists(file_docx):
            self.document = docx.Document(file_docx)
        else:
            self.document = docx.Document()
        self.document.core_properties.author = "Reporter"

        # 设置正文样式
        self.document.styles["Normal"].font.name = 'Times New Roman'
        self.document.styles["Normal"].element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')

    def add_title(self, text):
        self.document.core_properties.title = text
        title_ = self.document.add_heading(level=0)
        title_.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
        title_run = title_.add_run(text)
        title_run.font.size = Pt(22)
        title_run.font.bold = True
        title_run.font.name = 'Times New Roman'
        title_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')

    def add_heading(self, text, level=1):
        if level == 1:
            size = 18
        elif level == 2:
            size = 16
        else:
            size = 14
        title_ = self.document.add_heading(level=level)
        title_run = title_.add_run(text)
        title_run.font.size = Pt(size)
        title_run.font.name = 'Times New Roman'
        title_run.element.rPr.rFonts.set(qn('w:eastAsia'), '微软雅黑')
        title_run.font.color.rgb = RGBColor(0, 0, 0)

    def add_paragraph(self, text, style=None, bold=False):
        p = self.document.add_paragraph(style=style)
        p.paragraph_format.left_indent = Cm(0)
        p.paragraph_format.first_line_indent = Cm(0.74)
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(8)

        text = p.add_run(text)
        text.bold = bold
        text.font.name = 'Times New Roman'
        text.element.rPr.rFonts.set(qn('w:eastAsia'), '宋体')
        text.font.size = Pt(12)

    def add_df_table(self, df: pd.DataFrame, style='Table Grid'):
        """添加数据表

        https://www.jianshu.com/p/93e0df92cf16
        :param df: 数据表
        :param style: 表格样式
        :return:
        """
        if df.empty:
            print(f"add_df_table error: 传入的数据表是空的")
            return

        table = self.document.add_table(rows=1, cols=df.shape[1], style=style)
        # 设置整个表格字体属性
        table.style.font.size = Pt(12)
        table.style.font.color.rgb = RGBColor(0, 0, 0)
        table.style.paragraph_format.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER

        records = df.to_dict("records")
        columns = df.columns.to_list()

        hdr_cells = table.rows[0].cells
        for i, c in enumerate(columns):
            hdr_cells[i].text = c

        for row in records:
            row_cells = table.add_row().cells
            for i, c in enumerate(columns):
                row_cells[i].text = str(row[c])

    def add_picture(self, file, width=None, height=None, alignment='center') -> None:
        """写入图片到文档中

        :param file: 图片文件路径
        :param width: 图片宽度，默认单位 cm
        :param height: 图片高度，默认单位 cm
        :param alignment: 图片对齐，默认 center
        :return:
        """
        alignment_map = {
            'center': WD_PARAGRAPH_ALIGNMENT.CENTER,
            'left': WD_PARAGRAPH_ALIGNMENT.LEFT,
            'right': WD_PARAGRAPH_ALIGNMENT.RIGHT,
        }
        if isinstance(width, int):
            width = Cm(width)

        if isinstance(height, int):
            height = Cm(height)

        paragraph = self.document.add_paragraph()
        paragraph.alignment = alignment_map[alignment]
        run = paragraph.add_run("")
        run.add_picture(file, width, height)

    def add_page_break(self):
        """添加分页符"""
        self.document.add_page_break()

    def save(self, file_docx=None):
        """保存结果到文件"""
        if not file_docx:
            file_docx = self.file_docx
        self.document.save(file_docx)
