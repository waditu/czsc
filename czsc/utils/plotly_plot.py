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
        # 子图数量
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
        """绘制K线"""
        if 'text' not in kline.columns:
            kline['text'] = ""

        candle = go.Candlestick(x=kline['dt'], open=kline["open"], high=kline["high"], low=kline["low"],
                                close=kline["close"], text=kline["text"], name=name, showlegend=True,
                                increasing_line_color=self.color_red, decreasing_line_color=self.color_green,
                                increasing_fillcolor=self.color_red, decreasing_fillcolor=self.color_green, **kwargs)
        self.fig.add_trace(candle, row=1, col=1)
        self.fig.update_traces(xaxis="x1")

    def add_vol(self, kline: pd.DataFrame, row=2, **kwargs):
        """绘制成交量图"""
        df = kline.copy()
        df['vol_color'] = np.where(df['close'] > df['open'], self.color_red, self.color_green)
        self.add_bar_indicator(df['dt'], df['vol'], color=df['vol_color'], name="成交量", row=row, show_legend=False)

    def add_sma(self, kline: pd.DataFrame, row=1, ma_seq=(5, 10, 20), visible=False, **kwargs):
        """绘制均线图"""
        df = kline.copy()
        line_width = kwargs.get('line_width', 0.6)
        for ma in ma_seq:
            self.add_scatter_indicator(df['dt'], df['close'].rolling(ma).mean(), name=f"MA{ma}",
                                       row=row, line_width=line_width, visible=visible, show_legend=True)

    def add_macd(self, kline: pd.DataFrame, row=3, **kwargs):
        """绘制MACD图"""
        df = kline.copy()
        fastperiod = kwargs.get('fastperiod', 12)
        slowperiod = kwargs.get('slowperiod', 26)
        signalperiod = kwargs.get('signalperiod', 9)
        line_width = kwargs.get('line_width', 0.6)
        diff, dea, macd = MACD(df["close"], fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod)
        macd_colors = np.where(macd > 0, self.color_red, self.color_green)
        self.add_scatter_indicator(df['dt'], diff, name="DIFF", row=row,
                                   line_color='white', show_legend=False, line_width=line_width)
        self.add_scatter_indicator(df['dt'], dea, name="DEA", row=row,
                                   line_color='yellow', show_legend=False, line_width=line_width)
        self.add_bar_indicator(df['dt'], macd, name="MACD", row=row, color=macd_colors, show_legend=False)

    def add_indicator(self, dt, scatters: list = None, scatter_names: list = None, bar=None, bar_name='', row=4, **kwargs):
        """绘制曲线叠加bar型指标"""
        line_width = kwargs.get('line_width', 0.6)
        for i, scatter in enumerate(scatters):
            self.add_scatter_indicator(dt, scatter, name=scatter_names[i], row=row, show_legend=False, line_width=line_width)

        if bar:
            bar_colors = np.where(np.array(bar, dtype=np.double) > 0, self.color_red, self.color_green)
            self.add_bar_indicator(dt, bar, name=bar_name, row=row, color=bar_colors, show_legend=False)

    def add_marker_indicator(self, x, y, name: str, row: int, text=None, **kwargs):
        """绘制标记类指标

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
