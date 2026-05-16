"""
基于 Plotly 的 K 线绘图模块

本模块提供两个核心能力：

1. :class:`KlineChart`：通用 K 线图工具类，封装了 Plotly 的 ``make_subplots``、
   ``Candlestick``、``Bar``、``Scatter`` 等接口，支持快速叠加均线、成交量、MACD、
   自定义指标、标记点等；
2. :func:`plot_czsc_chart`：针对 ``CZSC`` 对象的便捷绘图入口，自动绘制 K 线、
   均线、成交量、MACD，并叠加分型与笔；
3. :func:`plot_nx_graph`：用 Plotly 渲染 ``networkx`` 图（节点 + 带权边）。

作者: zengbin93
邮箱: zeng_bin8888@163.com
创建时间: 2023/2/26 15:03
"""

import os
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from plotly import graph_objects as go

if TYPE_CHECKING:
    from czsc import CZSC


class KlineChart:
    """K 线绘图工具类

    封装 Plotly 的多子图布局，便于在同一张图上叠加 K 线、均线、成交量、MACD 等。

    Plotly 参数详解可参考：https://www.jianshu.com/p/4f4daf47cc85
    """

    def __init__(self, n_rows=3, **kwargs):
        """初始化 K 线绘图工具类

        初始化执行逻辑：

        - 接收一个可选参数 ``n_rows``，默认值为 3，表示图表的子图数量；
        - 接收可变参数 ``**kwargs``，用于传递其他配置（如 ``row_heights``、``title``、``height`` 等）；
        - 若未提供 ``row_heights``，则根据 ``n_rows`` 选择内置的高度比例；
        - 定义两个常用颜色：``color_red``（上涨）和 ``color_green``（下跌）；
        - 调用 ``make_subplots`` 创建 ``n_rows × 1`` 的子图布局，并设置共享 X 轴等属性；
        - 通过 ``update_yaxes`` / ``update_xaxes`` 配置 Y/X 轴的网格、自动 margin、Spike 等；
        - 通过 ``update_layout`` 设置标题、外边距、图例、模板（plotly_dark）、悬停样式等；
        - 把构造好的 ``go.Figure`` 赋给 ``self.fig`` 供后续操作。

        :param n_rows: int，子图数量，仅支持 3 / 4 / 5
        :param kwargs: 其他参数
            - row_heights: list[float]，每个子图的高度比例
            - y_fixed_range: bool，Y 轴是否固定范围
            - title: str，图表标题
            - height: int，图表高度（像素）
        """
        from plotly.subplots import make_subplots

        self.n_rows = n_rows
        row_heights = kwargs.get("row_heights")
        if not row_heights:
            # 内置的高度配置：3/4/5 行各一种默认比例
            heights_map = {3: [0.6, 0.2, 0.2], 4: [0.55, 0.15, 0.15, 0.15], 5: [0.4, 0.15, 0.15, 0.15, 0.15]}
            assert self.n_rows in heights_map, "使用内置高度配置，n_rows 只能是 3, 4, 5"
            row_heights = heights_map[self.n_rows]

        # 上涨用红色、下跌用绿色（A 股配色习惯）
        self.color_red = "rgba(249,41,62,0.7)"
        self.color_green = "rgba(0,170,59,0.7)"
        fig = make_subplots(
            rows=self.n_rows,
            cols=1,
            shared_xaxes=True,
            row_heights=row_heights,
            horizontal_spacing=0,
            vertical_spacing=0,
        )

        # 统一的 Y 轴样式：显示网格、Spike 跨子图等
        fig = fig.update_yaxes(
            showgrid=True,
            zeroline=False,
            automargin=True,
            fixedrange=kwargs.get("y_fixed_range", True),
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            showline=False,
            spikedash="dot",
        )
        # 统一的 X 轴样式：使用 category 类型，避免 plotly 自动跳过非交易时段
        fig = fig.update_xaxes(
            type="category",
            rangeslider_visible=False,
            showgrid=False,
            automargin=True,
            showticklabels=False,
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            showline=False,
            spikedash="dot",
        )

        # 整体布局：暗色主题、悬停联动、紧凑边距
        # 参考：https://plotly.com/python/reference/layout/
        fig.update_layout(
            title={"text": kwargs.get("title", ""), "yanchor": "top", "y": 0.95},
            margin=go.layout.Margin(l=0, r=0, b=0, t=0),  # 上下左右四个方向的外边距
            # 图例配置：水平、靠近顶部、透明背景
            # 参考：https://plotly.com/python/reference/layout/#layout-legend
            legend={
                "orientation": "h",
                "yanchor": "top",
                "y": 1.05,
                "xanchor": "left",
                "x": 0,
                "bgcolor": "rgba(0,0,0,0)",
            },
            template="plotly_dark",
            hovermode="x unified",
            hoverlabel={"bgcolor": "rgba(255,255,255,0.1)", "font": {"size": 20}},  # 半透明背景，方便看清后面的 K 线
            dragmode="pan",
            legend_title_font_color="red",
            height=kwargs.get("height", 600),
        )

        self.fig = fig

    def add_kline(self, kline: pd.DataFrame, name: str = "K线", **kwargs):
        """绘制 K 线

        函数执行逻辑：

        1. 检查 ``kline`` DataFrame 是否包含 ``'text'`` 列；如果没有则补一个空字符串列；
        2. 用 ``go.Candlestick`` 创建蜡烛图，参数包括：
            - x: 日期时间数据
            - open / high / low / close: 开盘价、最高价、最低价、收盘价
            - text: 显示在每根 K 线上的文本标签
            - name: 图例名称
            - showlegend: 是否显示图例
            - increasing_line_color / decreasing_line_color: 上涨 / 下跌时的描边颜色
            - increasing_fillcolor / decreasing_fillcolor: 上涨 / 下跌时的填充颜色
            - **kwargs: 其他自定义参数透传给 Candlestick；
        3. 把蜡烛图加入第 1 个子图（``row=1, col=1``）；
        4. 通过 ``update_traces(xaxis="x1")`` 让所有 trace 共享同一根 X 轴。
        """
        if "text" not in kline.columns:
            kline["text"] = ""

        candle = go.Candlestick(
            x=kline["dt"],
            open=kline["open"],
            high=kline["high"],
            low=kline["low"],
            close=kline["close"],
            text=kline["text"],
            name=name,
            showlegend=True,
            increasing_line_color=self.color_red,
            decreasing_line_color=self.color_green,
            increasing_fillcolor=self.color_red,
            decreasing_fillcolor=self.color_green,
            **kwargs,
        )
        self.fig.add_trace(candle, row=1, col=1)
        self.fig.update_traces(xaxis="x1")

    def add_vol(self, kline: pd.DataFrame, row=2, **kwargs):
        """绘制成交量图

        函数执行逻辑：

        1. 复制输入的 ``kline`` 到本地变量 ``df``；
        2. 用 ``np.where`` 根据收盘价与开盘价的关系给每根柱体上色：
           收盘 > 开盘 用红色（``self.color_red``），否则用绿色（``self.color_green``）；
        3. 调用 :meth:`add_bar_indicator` 完成成交量绘制；参数包括：
            - x: 日期时间
            - y: 成交量
            - color: 上一步生成的颜色数组
            - name: ``"成交量"``
            - row: 子图行号，默认 2
            - show_legend: 默认 False
        """
        df = kline.copy()
        df["vol_color"] = np.where(df["close"] > df["open"], self.color_red, self.color_green)
        self.add_bar_indicator(df["dt"], df["vol"], color=df["vol_color"], name="成交量", row=row, show_legend=False)

    def add_sma(self, kline: pd.DataFrame, row=1, ma_seq=(5, 10, 20), visible=False, **kwargs):
        """绘制均线（SMA）

        函数执行逻辑：

        1. 复制输入 ``kline`` 到本地变量 ``df``；
        2. 读取 ``line_width`` 参数（默认 0.6）；
        3. 遍历 ``ma_seq`` 中的均线周期，对收盘价做 ``rolling(window).mean()``，
           调用 :meth:`add_scatter_indicator` 绘制为折线图：
            - x: 日期时间
            - y: 移动平均序列
            - name: ``f"MA{ma}"``
            - row: 子图行号，默认 1
            - line_width: 线宽
            - visible: 是否默认可见
            - show_legend: 默认 True
        """
        df = kline.copy()
        line_width = kwargs.get("line_width", 0.6)
        for ma in ma_seq:
            self.add_scatter_indicator(
                df["dt"],
                df["close"].rolling(ma).mean(),
                name=f"MA{ma}",
                row=row,
                line_width=line_width,
                visible=visible,
                show_legend=True,
            )

    def add_macd(self, kline: pd.DataFrame, row=3, **kwargs):
        """绘制 MACD

        函数执行逻辑：

        1. 复制输入 ``kline`` 到本地变量 ``df``；
        2. 读取 ``fastperiod`` / ``slowperiod`` / ``signalperiod`` / ``line_width`` 参数，
           默认值分别为 12 / 26 / 9 / 0.6；
        3. 若 ``df`` 已包含 ``DIFF / DEA / MACD`` 列则直接复用，否则调用
           plotting 内部的 ``compute_macd``（柱状图 ×2 约定）计算；
        4. 根据 MACD 是否大于 0 给柱体上色（大于 0 红色，否则绿色）；
        5. 用 :meth:`add_scatter_indicator` 把 ``DIFF`` / ``DEA`` 绘制为折线，
           用 :meth:`add_bar_indicator` 把 ``MACD`` 绘制为柱体。
        """
        df = kline.copy()
        fastperiod = kwargs.get("fastperiod", 12)
        slowperiod = kwargs.get("slowperiod", 26)
        signalperiod = kwargs.get("signalperiod", 9)
        line_width = kwargs.get("line_width", 0.6)

        if "DIFF" in df.columns and "DEA" in df.columns and "MACD" in df.columns:
            diff, dea, macd = df["DIFF"], df["DEA"], df["MACD"]
        else:
            from czsc.utils.plotting._macd import compute_macd

            diff, dea, macd = compute_macd(
                df["close"].to_numpy(), fastperiod=fastperiod, slowperiod=slowperiod, signalperiod=signalperiod
            )

        macd_colors = np.where(macd > 0, self.color_red, self.color_green)
        self.add_scatter_indicator(
            df["dt"], diff, name="DIFF", row=row, line_color="white", show_legend=False, line_width=line_width
        )
        self.add_scatter_indicator(
            df["dt"], dea, name="DEA", row=row, line_color="yellow", show_legend=False, line_width=line_width
        )
        self.add_bar_indicator(df["dt"], macd, name="MACD", row=row, color=macd_colors, show_legend=False)

    def add_indicator(
        self, dt, scatters: list = None, scatter_names: list = None, bar=None, bar_name="", row=4, **kwargs
    ):
        """同时绘制多条曲线 + 一组 bar 型指标

        函数执行逻辑：

        1. 读取 ``line_width`` 参数（默认 0.6）；
        2. 若 ``scatters`` 不为空，则遍历每条散点序列调用 :meth:`add_scatter_indicator`；
            - x: 日期时间
            - y: 散点数据
            - name: 来自 ``scatter_names``
            - row: 子图行号，默认 4
            - show_legend: 默认 False
            - line_width: 线宽
        3. 如 ``bar`` 不为空，则按"大于零红色 / 否则绿色"给每根柱体上色；
        4. 调用 :meth:`add_bar_indicator` 绘制柱状图：
            - x: 日期时间
            - y: bar 数据
            - name: ``bar_name``
            - row: 子图行号，默认 4
            - color: 计算好的颜色数组
            - show_legend: 默认 False
        """
        line_width = kwargs.get("line_width", 0.6)
        for i, scatter in enumerate(scatters):
            self.add_scatter_indicator(
                dt, scatter, name=scatter_names[i], row=row, show_legend=False, line_width=line_width
            )

        if bar:
            bar_colors = np.where(np.array(bar, dtype=np.double) > 0, self.color_red, self.color_green)
            self.add_bar_indicator(dt, bar, name=bar_name, row=row, color=bar_colors, show_legend=False)

    def add_marker_indicator(self, x, y, name: str, row: int, text=None, **kwargs):
        """绘制标记类指标（仅 marker，无连线）

        函数执行逻辑：

        1. 从 ``kwargs`` 读取 ``line_color``、``line_width``、``hover_template``、
           ``show_legend``、``visible``、``color``、``tag`` 等参数，分别对应：
           折线颜色、宽度、悬停模板、图例可见性、整体可见性、标记颜色、标记符号；
        2. 用 ``go.Scatter`` 创建一个 ``mode='markers'`` 的散点对象；
        3. 通过 ``self.fig.add_trace`` 加入指定子图，并统一 X 轴为 ``"x1"``。

        :param x: 指标的 X 轴
        :param y: 指标的 Y 轴
        :param name: str，指标名称
        :param row: int，放入第几个子图
        :param text: 文本说明
        :param kwargs: 其他自定义参数
        """
        line_color = kwargs.get("line_color")
        line_width = kwargs.get("line_width")
        hover_template = kwargs.get("hover_template", "%{y:.3f}-%{text}")
        show_legend = kwargs.get("show_legend", True)
        visible = True if kwargs.get("visible", True) else "legendonly"
        color = kwargs.get("color")
        tag = kwargs.get("tag")
        scatter = go.Scatter(
            x=x,
            y=y,
            name=name,
            text=text,
            line_width=line_width,
            line_color=line_color,
            hovertemplate=hover_template,
            showlegend=show_legend,
            visible=visible,
            opacity=1.0,
            mode="markers",
            marker={"size": 10, "color": color, "symbol": tag},
        )

        self.fig.add_trace(scatter, row=row, col=1)
        self.fig.update_traces(xaxis="x1")

    def add_scatter_indicator(self, x, y, name: str, row: int, text=None, **kwargs):
        """绘制线性 / 离散指标

        参考 Plotly 的 Scatter 文档：
        https://plotly.com/python-api-reference/generated/plotly.graph_objects.Scatter.html

        函数执行逻辑：

        1. 从 ``kwargs`` 中弹出 ``mode``、``hover_template``、``show_legend``、
           ``opacity``、``visible`` 等参数，剩余 kwargs 直接透传给 ``go.Scatter``；
        2. 创建 ``go.Scatter`` 对象，默认 ``mode='text+lines'``；
        3. 把 trace 加入指定子图，并统一 X 轴为 ``"x1"``。

        :param x: 指标的 X 轴
        :param y: 指标的 Y 轴
        :param name: str，指标名称
        :param row: int，放入第几个子图
        :param text: 文本说明
        :param kwargs: 其他自定义参数
        """
        mode = kwargs.pop("mode", "text+lines")
        hover_template = kwargs.pop("hover_template", "%{y:.3f}")
        show_legend = kwargs.pop("show_legend", True)
        opacity = kwargs.pop("opacity", 1.0)
        visible = True if kwargs.pop("visible", True) else "legendonly"

        scatter = go.Scatter(
            x=x,
            y=y,
            name=name,
            text=text,
            mode=mode,
            hovertemplate=hover_template,
            showlegend=show_legend,
            visible=visible,
            opacity=opacity,
            **kwargs,
        )
        self.fig.add_trace(scatter, row=row, col=1)
        self.fig.update_traces(xaxis="x1")

    def add_bar_indicator(self, x, y, name: str, row: int, color=None, **kwargs):
        """绘制条形图指标

        参考 Plotly 的 Bar 文档：
        https://plotly.com/python-api-reference/generated/plotly.graph_objects.Bar.html

        函数执行逻辑：

        1. 从 ``kwargs`` 中弹出 ``hover_template``、``show_legend``、``visible``、``base`` 等参数；
        2. 若 ``color`` 为 None，则使用 ``self.color_red`` 作为默认颜色；
        3. 创建 ``go.Bar`` 对象（marker 描边/填充颜色一致）；
        4. 把 trace 加入指定子图，并统一 X 轴为 ``"x1"``。

        :param x: 指标的 X 轴
        :param y: 指标的 Y 轴
        :param name: str，指标名称
        :param row: int，放入第几个子图
        :param color: str | list[str]，单色或与 y 等长的颜色序列；
            例如 ``'rgba(249,41,62,0.7)'`` 或 ``['rgba(249,41,62,0.7)', 'rgba(0,170,59,0.7)']``
        :param kwargs: 其他自定义参数
        """
        hover_template = kwargs.pop("hover_template", "%{y:.3f}")
        show_legend = kwargs.pop("show_legend", True)
        visible = kwargs.pop("visible", True)
        base = kwargs.pop("base", True)
        if color is None:
            color = self.color_red

        bar = go.Bar(
            x=x,
            y=y,
            marker_line_color=color,
            marker_color=color,
            name=name,
            showlegend=show_legend,
            hovertemplate=hover_template,
            visible=visible,
            base=base,
            **kwargs,
        )
        self.fig.add_trace(bar, row=row, col=1)
        self.fig.update_traces(xaxis="x1")

    def open_in_browser(self, file_name: str = None, **kwargs):
        """把图表写入 HTML 并在系统默认浏览器中打开

        :param file_name: str，输出文件路径；为 None 时写入 ``home_path`` 下的 ``kline_chart.html``
        :param kwargs: 透传给 ``fig.update_layout``
        """
        import webbrowser

        if not file_name:
            from czsc.utils.data.cache import home_path

            file_name = os.path.join(home_path, "kline_chart.html")

        self.fig.update_layout(**kwargs)
        self.fig.write_html(file_name)
        webbrowser.open(file_name)

    def show(self, **kwargs):
        """显示图表

        支持传入任意 plotly layout 参数。
        参考：https://plotly.com/python/reference/layout/
        """
        self.fig.update_layout(**kwargs)
        self.fig.show()


def plot_nx_graph(g, **kwargs) -> go.Figure:
    """使用 Plotly 绘制 ``nx.Graph`` 的图形

    采用 ``spring_layout`` 自动布局节点，边宽与节点大小可通过 kwargs 控制；同时把
    每条边的权重作为文字标签放在边的中点，正负权重用红绿区分。

    :param g: nx.Graph 对象
    :param kwargs: 其他参数
        - title: str，图表标题，默认 ``"Network graph made with Python"``
        - edge_width: float，边宽，默认 1.5
        - node_marker_size: float，节点大小，默认 10
    :return: plotly.graph_objs.Figure
    """
    import networkx as nx

    title = kwargs.get("title", "Network graph made with Python")
    edge_width = kwargs.get("edge_width", 1.5)
    node_marker_size = kwargs.get("node_marker_size", 10)

    # 通过 spring_layout 给每个节点分配二维坐标
    pos = nx.spring_layout(g)

    # 准备绘图数据：边起止点 + 权重
    edge_x = []
    edge_y = []
    edge_weights = []
    for edge in g.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_weights.append(f"{g[edge[0]][edge[1]]['weight']:.2f}")

    node_x = []
    node_y = []
    node_labels = []
    for node in g.nodes():
        node_x.append(pos[node][0])
        node_y.append(pos[node][1])
        node_labels.append(node)

    # 边：用线条 trace 表示
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line={"width": edge_width, "color": "#888"},
        hoverinfo="none",
        mode="lines",
    )

    # 节点：用散点 trace 表示
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers",
        hoverinfo="text",
        text=node_labels,  # 节点标签
        marker={
            "showscale": False,
            "color": "skyblue",
            "size": node_marker_size,
            "line_width": 0,
        },
    )

    # 计算每条边中点位置，作为权重文字的注释
    edge_annotations = []
    for edge in g.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        mid_x = (x0 + x1) / 2
        mid_y = (y0 + y1) / 2
        weight = f"{g[edge[0]][edge[1]]['weight']:.2f}"
        edge_annotations.append(
            {
                "x": mid_x,
                "y": mid_y,
                "text": weight,
                "showarrow": False,
                "font": {"size": 12, "color": "red" if float(weight) > 0 else "green"},
            }
        )

    # 组装最终 figure
    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=f"<br>{title}",
            titlefont_size=16,
            showlegend=False,
            hovermode="closest",
            margin={"b": 20, "l": 5, "r": 5, "t": 40},
            xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
            annotations=edge_annotations,  # 边的权重文字注释
        ),
    )

    return fig


def plot_czsc_chart(czsc_obj: "CZSC", **kwargs) -> KlineChart:
    """使用 plotly 绘制 ``CZSC`` 对象

    自动绘制 K 线、均线（默认 5/10/21/34/55/89/144 多周期）、成交量、MACD，
    并叠加分型与笔。

    :param czsc_obj: CZSC 对象
    :param kwargs: 其他参数
        - height: int，图表高度，默认 600
        - ma_system: tuple，均线周期序列；首条默认可见，其余默认隐藏
    :return: KlineChart 对象（其内部 ``fig`` 即 plotly Figure）
    """
    height = kwargs.get("height", 600)
    ma_system = kwargs.get("ma_system", (5, 10, 21, 34, 55, 89, 144))

    bi_list = czsc_obj.bi_list
    df = pd.DataFrame([x.__dict__ for x in czsc_obj.bars_raw])
    df = df[["dt", "symbol", "open", "high", "low", "close", "vol", "amount"]]
    chart = KlineChart(n_rows=3, title=f"{czsc_obj.symbol}-{czsc_obj.freq.value}", height=height)
    chart.add_kline(df, name="")
    chart.add_sma(df, ma_seq=[ma_system[0]], row=1, visible=True, line_width=1.2)
    chart.add_sma(df, ma_seq=ma_system[1:], row=1, visible=False, line_width=1.2)
    chart.add_vol(df, row=2)
    chart.add_macd(df, row=3)

    if len(bi_list) > 0:
        # 笔的端点：首端取 fx_a，尾端额外补一个 fx_b
        bi1 = [{"dt": x.fx_a.dt, "bi": x.fx_a.fx, "text": x.fx_a.mark.value.replace("分型", "")} for x in bi_list]
        bi2 = [{"dt": bi_list[-1].fx_b.dt, "bi": bi_list[-1].fx_b.fx, "text": bi_list[-1].fx_b.mark.value[0]}]
        bi = pd.DataFrame(bi1 + bi2)
        fx = pd.DataFrame([{"dt": x.dt, "fx": x.fx} for x in czsc_obj.fx_list])

        # 分型用虚线表示，笔用实线
        chart.add_scatter_indicator(fx["dt"], fx["fx"], name="分型", row=1, line_width=1.8, line_dash="dash")
        chart.add_scatter_indicator(bi["dt"], bi["bi"], name="笔", text=bi["text"], row=1, line_width=1.8)
    return chart
