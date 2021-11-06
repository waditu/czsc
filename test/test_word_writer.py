# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/6 11:04
"""
import os

import pandas as pd
import inspect
from czsc.utils import WordWriter
import matplotlib.pyplot as plt
import seaborn as sns


def test_word_writer():
    reporter = WordWriter()

    reporter.add_title('Reporter测试记录文档')
    reporter.add_paragraph('这个方法可以用来生成完整的回测报告。以文字、图表为主，统一格式')

    reporter.add_heading('一、研究背景介绍', level=1)
    reporter.add_paragraph('python-docx 是用于创建和更新Microsoft Word（.docx）文件的Python库。')

    reporter.add_heading('1) 无序项目', level=2)
    reporter.add_paragraph('无序项目1', style='List Bullet')
    reporter.add_paragraph('无序项目2', style='List Bullet')
    reporter.add_paragraph('无序项目3', style='List Bullet')

    reporter.add_heading('2) 有序项目', level=2)
    reporter.add_paragraph('有序项目1', style='List Number')
    reporter.add_paragraph('有序项目2', style='List Number')
    reporter.add_paragraph('有序项目3', style='List Number')
    reporter.add_page_break()

    reporter.add_heading('二、主要研究结果', level=1)
    reporter.add_paragraph('Python中可以用docx来生成word文档，docx中可以自定义文字的大小和字体等。')
    reporter.add_paragraph("段落是Word中的一个块级对象，在其所在容器的左右边界内显示文本，当文本超过"
                           "右边界时自动换行。段落的边界通常是页边界，也可以是分栏排版时的栏边界，或者"
                           "表格单元格中的边界。段落格式用于控制段落在其容器（例如页、栏、单元格）中的"
                           "布局，例如对齐方式、左缩进、右缩进、首行缩进、行距、段前距离、段后距离、换"
                           "页方式、Tab键字符格式等。")

    reporter.add_paragraph("""
    newfile = docx.Document()
    newfile.styles['Normal'].font.name = 'Times New Roman'
    newfile.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), u'宋体')
    """, style='Normal')

    reporter.add_heading('1) 无序项目', level=2)
    reporter.add_paragraph('无序项目1', style='List Bullet')
    reporter.add_paragraph('无序项目2', style='List Bullet')
    reporter.add_paragraph('无序项目3', style='List Bullet')

    reporter.add_heading('2) 有序项目', level=2)
    reporter.add_paragraph('有序项目1', style='List Number')
    reporter.add_paragraph('有序项目2', style='List Number')
    reporter.add_paragraph('有序项目3', style='List Number')

    # 测试表格写入
    df = pd.DataFrame([{'x': 1, 'y': 2, 'z': 3}, {'x': 1, 'y': 2, 'z': 3}, {'x': 1, 'y': 2, 'z': 3}])
    reporter.add_df_table(df)

    reporter.save("reporter_test.docx")

    # 测试续写文档
    file_docx = "reporter_test.docx"
    reporter = WordWriter(file_docx)
    reporter.add_page_break()
    reporter.add_heading('三、讨论', level=1)
    reporter.add_paragraph('Python中可以用docx来生成word文档，docx中可以自定义文字的大小和字体等。')
    reporter.add_paragraph("""段落是Word中的一个块级对象，在其所在容器的左右边界内显示文本，当文本超过
    右边界时自动换行。段落的边界通常是页边界，也可以是分栏排版时的栏边界，或者表格单元格中的边界。段落格式
    用于控制段落在其容器（例如页、栏、单元格）中的布局，例如对齐方式、左缩进、右缩进、首行缩进、行距、段前
    距离、段后距离、换页方式、Tab键字符格式等。
        """.strip().replace("\n", ""))

    reporter.add_page_break()
    reporter.add_heading('四、源码', level=1)
    reporter.add_paragraph(inspect.getsource(WordWriter))

    reporter.save(file_docx)

    # 写入图片
    plt.close()
    df = pd.DataFrame({'x': list(range(100)), 'y': list(range(100))})
    ax1 = plt.subplot(211)
    sns.lineplot(data=df, x='x', y='y', ax=ax1)
    ax2 = plt.subplot(212)
    sns.lineplot(data=df, x='x', y='y', ax=ax2)
    file_png = "x.png"
    plt.savefig(file_png)
    reporter.add_picture(file_png)
    reporter.add_picture(file_png, width=8, height=6)
    reporter.save(file_docx)
    os.remove(file_png)

    # 查看全部样式
    all_styles = list(reporter.document.styles.__iter__())
    os.remove(file_docx)

