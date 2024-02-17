# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/26 15:03
describe: 使用 Plotly 构建绘图模块
"""
import os
import webbrowser
import numpy as np
import pandas as pd
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from czsc.utils.cache import home_path
from czsc.utils.ta import MACD


class KlineChart:
    """K线绘图工具类

    plotly 参数详解: https://www.jianshu.com/p/4f4daf47cc85

    """

    def __init__(self, n_rows=3, **kwargs):
        """K线绘图工具类

        初始化执行逻辑：

        - 接收一个可选参数 n_rows，默认值为 3。这个参数表示图表中的子图数量。
        - 接收一个可变参数列表 **kwargs，可以传递其他配置参数。
        - 如果没有提供 row_heights 参数，则根据 n_rows 设置默认的行高度。
        - 定义了一些颜色变量：color_red 和 color_green。
        - 使用 make_subplots 函数创建一个具有 n_rows 行和 1 列的子图布局，并设置一些共享属性和间距。
        - 使用 fig.update_yaxes 和 fig.update_xaxes 更新 Y 轴和 X 轴的属性，如显示网格、自动调整范围等。
        - 使用 fig.update_layout 更新整个图形的布局，包括标题、边距、图例位置和样式、背景模板等。
        - 将 fig 对象保存在 self.fig 属性中。

        :param n_rows: 子图数量
        :param kwargs:
        """
        self.n_rows = n_rows
        row_heights = kwargs.get("row_heights", None)
        if not row_heights:
            heights_map = {3: [0.6, 0.2, 0.2], 4: [0.55, 0.15, 0.15, 0.15], 5: [0.4, 0.15, 0.15, 0.15, 0.15]}
            assert self.n_rows in heights_map.keys(), "使用内置高度配置，n_rows 只能是 3, 4, 5"
            row_heights = heights_map[self.n_rows]

        self.color_red = 'rgba(249,41,62,0.7)'
        self.color_green = 'rgba(0,170,59,0.7)'
        fig = make_subplots(rows=self.n_rows, cols=1, shared_xaxes=True, row_heights=row_heights,
                            horizontal_spacing=0, vertical_spacing=0)

        fig = fig.update_yaxes(showgrid=True, zeroline=False, automargin=True,
                               fixedrange=kwargs.get('y_fixed_range', True),
                               showspikes=True, spikemode='across', spikesnap='cursor', showline=False, spikedash='dot')
        fig = fig.update_xaxes(type='category', rangeslider_visible=False, showgrid=False, automargin=True,
                               showticklabels=False, showspikes=True, spikemode='across', spikesnap='cursor',
                               showline=False, spikedash='dot')

        # https://plotly.com/python/reference/layout/
        fig.update_layout(
            title=dict(text=kwargs.get('title', ''), yanchor='top'),
            margin=go.layout.Margin(
                l=0,  # left margin
                r=0,  # right margin
                b=0,  # bottom margin
                t=0   # top margin
            ),
            # https://plotly.com/python/reference/layout/#layout-legend
            legend=dict(orientation='h', yanchor="top", y=1.05, xanchor="left", x=0, bgcolor='rgba(0,0,0,0)'),
            template="plotly_dark",
            hovermode="x unified",
            hoverlabel=dict(bgcolor='rgba(255,255,255,0.1)', font=dict(size=20)),  # 透明，更容易看清后面k线
            dragmode='pan',
            legend_title_font_color="red",
            height=kwargs.get('height', 300),
        )

        self.fig = fig

    def add_kline(self, kline: pd.DataFrame, name: str = "K线", **kwargs):
        """绘制K线

        函数执行逻辑：

        1. 检查 kline 数据框是否包含 'text' 列。如果没有，则添加一个空字符串列。
        2. 使用 go.Candlestick 创建一个K线图，并传入以下参数：
            - x: 日期时间数据
            - open, high, low, close: 开盘价、最高价、最低价和收盘价
            - text: 显示在每个 K 线上的文本标签
            - name: 图例名称
            - showlegend: 是否显示图例
            - increasing_line_color 和 decreasing_line_color: 上涨时的颜色和下跌时的颜色
            - increasing_fillcolor 和 decreasing_fillcolor: 上涨时填充颜色和下跌时填充颜色
            - **kwargs: 可以传递其他自定义参数给 Candlestick 函数。

        3. 将创建的烛台图对象添加到 self.fig 中的第一个子图（row=1, col=1）。
        4. 使用 fig.update_traces 更新所有 traces 的 xaxis 属性为 "x1"。
        """
        if 'text' not in kline.columns:
            kline['text'] = ""

        candle = go.Candlestick(x=kline['dt'], open=kline["open"], high=kline["high"], low=kline["low"],
                                close=kline["close"], text=kline["text"], name=name, showlegend=True,
                                increasing_line_color=self.color_red, decreasing_line_color=self.color_green,
                                increasing_fillcolor=self.color_red, decreasing_fillcolor=self.color_green, **kwargs)
        self.fig.add_trace(candle, row=1, col=1)
        self.fig.update_traces(xaxis="x1")

    def add_vol(self, kline: pd.DataFrame, row=2, **kwargs):
        """绘制成交量图

        函数执行逻辑：

        1. 首先，复制输入的 kline 数据框到 df。
        2. 使用 np.where 函数根据收盘价（df['close']）和开盘价（df['open']）之间的关系为 df 创建一个新列 'vol_color'。
           如果收盘价大于开盘价，则使用红色（self.color_red），否则使用绿色（self.color_green）。
        3. 调用 add_bar_indicator 方法绘制成交量图。传递以下参数：
            - x: 日期时间数据
            - y: 成交量数据
            - color: 根据 'vol_color' 列的颜色
            - name: 图例名称
            - row: 指定要添加指标的子图行数，默认值为 2
            - show_legend: 是否显示图例，默认值为 False
        """
        df = kline.copy()
        df['vol_color'] = np.where(df['close'] > df['open'], self.color_red, self.color_green)
        self.add_bar_indicator(df['dt'], df['vol'], color=df['vol_color'], name="成交量", row=row, show_legend=False)

    def add_sma(self, kline: pd.DataFrame, row=1, ma_seq=(5, 10, 20), visible=False, **kwargs):
        """绘制均线图

        函数执行逻辑：

        1. 复制输入的 kline 数据框到 df。
        2. 获取自定义参数 line_width，默认值为 0.6。
        3. 遍历 ma_seq 中的所有均线周期：
            - 对每个周期使用 pandas rolling 方法计算收盘价的移动平均线。
            - 调用 add_scatter_indicator 方法将移动平均线数据绘制为折线图。传递以下参数：
                - x: 日期时间数据
                - y: 移动平均线数据
                - name: 图例名称，格式为 "MA{ma}"，其中 {ma} 是当前的均线周期。
                - row: 指定要添加指标的子图行数，默认值为 1
                - line_width: 线宽，默认值为 0.6
                - visible: 是否可见，默认值为 False
                - show_legend: 是否显示图例，默认值为 True
        """
        df = kline.copy()
        line_width = kwargs.get('line_width', 0.6)
        for ma in ma_seq:
            self.add_scatter_indicator(df['dt'], df['close'].rolling(ma).mean(), name=f"MA{ma}",
                                       row=row, line_width=line_width, visible=visible, show_legend=True)

    def add_macd(self, kline: pd.DataFrame, row=3, **kwargs):
        """绘制MACD图

        函数执行逻辑：

        1. 首先，复制输入的 kline 数据框到 df。
        2. 获取自定义参数 fastperiod、slowperiod 和 signalperiod。这些参数分别对应于计算 MACD 时使用的快周期、慢周期和信号周期，默认值分别为 12、26 和 9。
        3. 使用 talib 库的 MACD 函数计算 MACD 值（diff, dea, macd）。
        4. 创建一个名为 macd_colors 的 numpy 数组，根据 macd 值大于零的情况设置颜色：大于零使用红色（self.color_red），否则使用绿色（self.color_green）。
        5. 调用 add_scatter_indicator 方法将 diff 和 dea 绘制为折线图。传递以下参数：
            - x: 日期时间数据
            - y: diff 或 dea 数据
            - name: 图例名称，分别为 "DIFF" 和 "DEA"
            - row: 指定要添加指标的子图行数，默认值为 3
            - line_color: 线的颜色，分别为 'white' 和 'yellow'
            - show_legend: 是否显示图例，默认值为 False
            - line_width: 线宽，默认值为 0.6
        6. 调用 add_bar_indicator 方法将 macd 绘制为柱状图。传递以下参数：
            - x: 日期时间数据
            - y: macd 数据
            - name: 图例名称，为 "MACD"
            - row: 指定要添加指标的子图行数，默认值为 3
            - color: 根据 macd_colors 设置颜色
            - show_legend: 是否显示图例，默认值为 False
        """
        df = kline.copy()
        fastperiod = kwargs.get('fastperiod', 12)
        slowperiod = kwargs.get('slowperiod', 26)
        signalperiod = kwargs.get('signalperiod', 9)
        line_width = kwargs.get('line_width', 0.6)

        if 'DIFF' in df.columns and 'DEA' in df.columns and 'MACD' in df.columns:
            diff, dea, macd = df['DIFF'], df['DEA'], df['MACD']
        else:
            diff, dea, macd = MACD(df["close"], fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)

        macd_colors = np.where(macd > 0, self.color_red, self.color_green)
        self.add_scatter_indicator(df['dt'], diff, name="DIFF", row=row,
                                   line_color='white', show_legend=False, line_width=line_width)
        self.add_scatter_indicator(df['dt'], dea, name="DEA", row=row,
                                   line_color='yellow', show_legend=False, line_width=line_width)
        self.add_bar_indicator(df['dt'], macd, name="MACD", row=row, color=macd_colors, show_legend=False)

    def add_indicator(self, dt, scatters: list = None, scatter_names: list = None, bar=None, bar_name='', row=4, **kwargs):
        """绘制曲线叠加bar型指标

        1. 获取自定义参数 line_width，默认值为 0.6。
        2. 如果 scatters（列表）不为空，则遍历 scatters 中的所有散点数据：
            - 对于每个散点数据，调用 add_scatter_indicator 方法将其绘制为折线图。传递以下参数：
                - x: 日期时间数据
                - y: 散点数据
                - name: 图例名称，来自 scatter_names 列表
                - row: 指定要添加指标的子图行数，默认值为 4
                - show_legend: 是否显示图例，默认值为 False
                - line_width: 线宽，默认值为 0.6
        3. 如果 bar 不为空，则使用 np.where 函数根据 bar 值大于零的情况设置颜色：大于零使用红色（self.color_red），否则使用绿色（self.color_green）。
        4. 调用 add_bar_indicator 方法将 bar 绘制为柱状图。传递以下参数：
            - x: 日期时间数据
            - y: bar 数据
            - name: 图例名称，为传入的 bar_name 参数
            - row: 指定要添加指标的子图行数，默认值为 4
            - color: 根据上一步计算的颜色设置
            - show_legend: 是否显示图例，默认值为 False
        """
        line_width = kwargs.get('line_width', 0.6)
        for i, scatter in enumerate(scatters):
            self.add_scatter_indicator(dt, scatter, name=scatter_names[i], row=row, show_legend=False, line_width=line_width)

        if bar:
            bar_colors = np.where(np.array(bar, dtype=np.double) > 0, self.color_red, self.color_green)
            self.add_bar_indicator(dt, bar, name=bar_name, row=row, color=bar_colors, show_legend=False)

    def add_marker_indicator(self, x, y, name: str, row: int, text=None, **kwargs):
        """绘制标记类指标

        函数执行逻辑：

        1. 获取自定义参数 line_color、line_width、hover_template、show_legend 和 visible。
            这些参数分别对应于折线颜色、宽度、鼠标悬停时显示的模板、是否显示图例和是否可见。
        2. 使用给定的 x、y 数据创建一个 go.Scatter 对象（散点图），并传入以下参数：
            - x: 指标的x轴数据
            - y: 指标的y轴数据
            - name: 指标名称
            - text: 文本说明
            - line_width: 线宽
            - line_color: 线颜色
            - hovertemplate: 鼠标悬停时显示的模板
            - showlegend: 是否显示图例
            - visible: 是否可见
            - opacity: 透明度
            - mode: 绘制模式，为 'markers' 表示只绘制标记
            - marker: 标记的样式，包括大小、颜色和符号
        3. 调用 self.fig.add_trace 方法将创建的 go.Scatter 对象添加到指定子图中，并更新所有 traces 的 X 轴属性为 "x1"。

        :param x: 指标的x轴
        :param y: 指标的y轴
        :param name: 指标名称
        :param row: 放入第几个子图
        :param text: 文本说明
        :param kwargs:
        :return:
        """
        line_color = kwargs.get('line_color', None)
        line_width = kwargs.get('line_width', None)
        hover_template = kwargs.get('hover_template', '%{y:.3f}-%{text}')
        show_legend = kwargs.get('show_legend', True)
        visible = True if kwargs.get('visible', True) else 'legendonly'
        color = kwargs.get('color', None)
        tag = kwargs.get('tag', None)
        scatter = go.Scatter(x=x, y=y, name=name, text=text, line_width=line_width, line_color=line_color,
                             hovertemplate=hover_template, showlegend=show_legend, visible=visible, opacity=1.0,
                             mode='markers', marker=dict(size=10, color=color, symbol=tag))

        self.fig.add_trace(scatter, row=row, col=1)
        self.fig.update_traces(xaxis="x1")

    def add_scatter_indicator(self, x, y, name: str, row: int, text=None, **kwargs):
        """绘制线性/离散指标

        绘图API文档：https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatter.html

        函数执行逻辑：

        1. 获取自定义参数 mode、hover_template、show_legend、opacity 和 visible。这些参数分别对应于绘图模式、鼠标悬停时显示的模板、是否显示图例、透明度和是否可见。
        2. 使用给定的 x、y 数据创建一个 go.Scatter 对象（散点图），并传入以下参数：
            - x: 指标的x轴数据
            - y: 指标的y轴数据
            - name: 指标名称
            - text: 文本说明
            - mode: 绘制模式，默认为 'text+lines'，表示同时绘制文本和线条
            - hovertemplate: 鼠标悬停时显示的模板
            - showlegend: 是否显示图例
            - visible: 是否可见
            - opacity: 透明度
        3. 调用 self.fig.add_trace 方法将创建的 go.Scatter 对象添加到指定子图中，并更新所有 traces 的 X 轴属性为 "x1"。

        :param x: 指标的x轴
        :param y: 指标的y轴
        :param name: 指标名称
        :param row: 放入第几个子图
        :param text: 文本说明
        :param kwargs:
        :return:
        """
        mode = kwargs.pop('mode', 'text+lines')
        hover_template = kwargs.pop('hover_template', '%{y:.3f}')
        show_legend = kwargs.pop('show_legend', True)
        opacity = kwargs.pop('opacity', 1.0)
        visible = True if kwargs.pop('visible', True) else 'legendonly'

        scatter = go.Scatter(x=x, y=y, name=name, text=text, mode=mode, hovertemplate=hover_template,
                             showlegend=show_legend, visible=visible, opacity=opacity, **kwargs)
        self.fig.add_trace(scatter, row=row, col=1)
        self.fig.update_traces(xaxis="x1")

    def add_bar_indicator(self, x, y, name: str, row: int, color=None, **kwargs):
        """绘制条形图指标

        绘图API文档：https://plotly.com/python-api-reference/generated/plotly.graph_objects.Bar.html

        函数执行逻辑：

        1. 获取自定义参数 hover_template、show_legend、visible 和 base。这些参数分别对应于鼠标悬停时显示的模板、是否显示图例、是否可见和基线（默认为 True）。
        2. 如果 color 参数为空，则使用 self.color_red 作为颜色。
        3. 使用给定的 x、y 数据创建一个 go.Bar 对象（条形图），并传入以下参数：
            - x: 指标的x轴数据
            - y: 指标的y轴数据
            - marker_line_color: 条形边框的颜色
            - marker_color: 条形填充的颜色
            - name: 指标名称
            - showlegend: 是否显示图例
            - hovertemplate: 鼠标悬停时显示的模板
            - visible: 是否可见
            - base: 基线，默认为 True
        4. 调用 self.fig.add_trace 方法将创建的 go.Bar 对象添加到指定子图中，并更新所有 traces 的 X 轴属性为 "x1"。

        :param x: 指标的x轴
        :param y: 指标的y轴
        :param name: 指标名称
        :param row: 放入第几个子图
        :param color: 指标的颜色，可以是单个颜色，也可以是一个列表，列表长度和y的长度一致，指示每个y的颜色
            比如：color = 'rgba(249,41,62,0.7)' 或者 color = ['rgba(249,41,62,0.7)', 'rgba(0,170,59,0.7)']
        :param kwargs:
        :return:
        """
        hover_template = kwargs.pop('hover_template', '%{y:.3f}')
        show_legend = kwargs.pop('show_legend', True)
        visible = kwargs.pop('visible', True)
        base = kwargs.pop('base', True)
        if color is None:
            color = self.color_red

        bar = go.Bar(x=x, y=y, marker_line_color=color, marker_color=color, name=name,
                     showlegend=show_legend, hovertemplate=hover_template, visible=visible, base=base, **kwargs)
        self.fig.add_trace(bar, row=row, col=1)
        self.fig.update_traces(xaxis="x1")

    def open_in_browser(self, file_name: str = None, **kwargs):
        """在浏览器中打开"""
        if not file_name:
            file_name = os.path.join(home_path, "kline_chart.html")
        self.fig.update_layout(**kwargs)
        self.fig.write_html(file_name)
        webbrowser.open(file_name)
