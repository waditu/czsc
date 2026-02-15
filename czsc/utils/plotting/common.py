"""
公共绘图函数和常量

此模块包含所有绘图模块共用的常量、类型定义和辅助函数
"""

from typing import Union, Literal, Optional
import pandas as pd
import plotly.graph_objects as go

# ==================== 模块级常量 ====================

# 颜色常量
COLOR_DRAWDOWN = "salmon"
COLOR_RETURN = "#34a853"
COLOR_ANNO_GRAY = "rgba(128,128,128,0.5)"
COLOR_ANNO_RED = "red"
COLOR_BORDER = "darkgrey"
COLOR_HEADER_BG = "grey"

# 分位数常量
QUANTILES_DRAWDOWN = [0.05, 0.1, 0.2]
QUANTILES_DRAWDOWN_ANALYSIS = [0.1, 0.3, 0.5]

# Sigma 级别
SIGMA_LEVELS = [-3, -2, -1, 1, 2, 3]

# 月份标签
MONTH_LABELS = [
    '1月', '2月', '3月', '4月', '5月', '6月',
    '7月', '8月', '9月', '10月', '11月', '12月'
]

# 模板类型
TemplateType = Literal['plotly', 'plotly_dark', 'ggplot2', 'seaborn', 'simple_white']


# ==================== 辅助函数 ====================

def figure_to_html(
    fig: go.Figure,
    to_html: bool = False,
    include_plotlyjs: bool = True
) -> Union[go.Figure, str]:
    """统一处理 Figure 转 HTML 的逻辑

    :param fig: Plotly Figure 对象
    :param to_html: 是否转换为 HTML
    :param include_plotlyjs: 转换 HTML 时是否包含 plotly.js 库
    :return: Figure 对象或 HTML 字符串
    """
    if to_html:
        return fig.to_html(include_plotlyjs=include_plotlyjs, full_html=False)
    return fig


def add_year_boundary_lines(
    fig: go.Figure,
    dates: pd.DatetimeIndex,
    row: Optional[int] = None,
    col: Optional[int] = None,
    line_color: str = "red",
    opacity: float = 0.3,
    line_dash: str = "dash"
) -> None:
    """在图表中添加年度分隔线

    :param fig: Plotly Figure 对象
    :param dates: 日期索引
    :param row: 子图行号（可选）
    :param col: 子图列号（可选）
    :param line_color: 线条颜色
    :param opacity: 透明度
    :param line_dash: 线条样式
    """
    years = dates.year.unique()
    for year in years:
        first_date = dates[dates.year == year].min()
        fig.add_vline(
            x=first_date,
            line_dash=line_dash,
            line_color=line_color,
            opacity=opacity,
            row=row,
            col=col
        )
