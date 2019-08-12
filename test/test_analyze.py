# coding: utf-8

import sys
sys.path.insert(0, r"C:\ZB\git_repo\zengbin93\chan")

import os
import webbrowser
from pyecharts import options as opts
from pyecharts.charts import Kline, Grid, Line, Bar, Scatter
from pyecharts.globals import ThemeType
from chan.a import get_kline
from chan import cache_path
from chan.analyze import preprocess, find_fx, find_bi, find_xd


def show_preprocessed_kline(kline_raw, show=True):
    x_data = kline_raw.dt.values.tolist()
    oclh = kline_raw[['open', 'close', 'low', 'high']].values.tolist()
    symbol = kline_raw.iloc[0]['symbol']
    start_dt = kline_raw.iloc[0]["dt"]
    end_dt = kline_raw.iloc[-1]["dt"]

    kline = (
        Kline(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name=symbol,
            y_axis=oclh,
            itemstyle_opts=opts.ItemStyleOpts(color="#ec0000", color0="#00da3c"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="缠论分析结果：%s" % symbol,
                subtitle="时间区间：%s 至 %s" % (start_dt, end_dt)
            ),
            xaxis_opts=opts.AxisOpts(type_="category"),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            legend_opts=opts.LegendOpts(
                is_show=True, pos_top=10, pos_left="center"
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=0,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="90%",
                    range_start=0,
                    range_end=100,
                ),
            ],
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                dimension=2,
                series_index=5,
                is_piecewise=True,
                pieces=[
                    {"value": 1, "color": "#ec0000"},
                    {"value": -1, "color": "#00da3c"},
                ],
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
            brush_opts=opts.BrushOpts(
                x_axis_index="all",
                brush_link="all",
                out_of_brush={"colorAlpha": 0.1},
                brush_type="lineX",
            ),
        )
    )

    bar = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="Volume",
            yaxis_data=kline_raw.vol.values.tolist(),
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                grid_index=1,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                is_scale=True,
                split_number=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    # Kline And Line
    # kline = kline.overlap(line)

    # Grid Overlap + Bar
    grid_chart = Grid(opts.InitOpts(width="1400px", height="800px", theme=ThemeType.WHITE))
    grid_chart.add(
        kline,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", height="60%"
        ),
    )
    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", pos_top="70%", height="16%"
        ),
    )

    graph_path = os.path.join(cache_path, "%s_kline_%s.html" % (symbol, 'preprocessed'))
    grid_chart.render(path=graph_path)

    # 调用浏览器打开可视化结果
    if show:
        webbrowser.open(graph_path)


def show_fx_kline(kline_raw, show=True):
    freq = '5min'
    start_dt = kline_raw.iloc[0]["dt"]
    end_dt = kline_raw.iloc[-1]["dt"]

    x_data = kline_raw.dt.values.tolist()
    oclh = kline_raw[['open', 'close', 'low', 'high']].values.tolist()
    symbol = kline_raw.iloc[0]['symbol']

    kline = (
        Kline(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name=symbol,
            y_axis=oclh,
            itemstyle_opts=opts.ItemStyleOpts(color="#ec0000", color0="#00da3c"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="缠论分析结果：%s-%s" % (symbol, freq),
                subtitle="时间区间：%s 至 %s" % (start_dt, end_dt)
            ),
            xaxis_opts=opts.AxisOpts(type_="category"),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            legend_opts=opts.LegendOpts(
                is_show=True, pos_top=10, pos_left="center"
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=0,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="90%",
                    range_start=0,
                    range_end=100,
                ),
            ],
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                dimension=2,
                series_index=5,
                is_piecewise=True,
                pieces=[
                    {"value": 1, "color": "#ec0000"},
                    {"value": -1, "color": "#00da3c"},
                ],
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
            brush_opts=opts.BrushOpts(
                x_axis_index="all",
                brush_link="all",
                out_of_brush={"colorAlpha": 0.1},
                brush_type="lineX",
            ),
        )
    )

    chan = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("分型标记", kline_raw.fx.values.tolist(),
                   label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    bar = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="Volume",
            yaxis_data=kline_raw.vol.values.tolist(),
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                grid_index=1,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                is_scale=True,
                split_number=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    # Kline And Line
    kline = kline.overlap(chan)

    # Grid Overlap + Bar
    grid_chart = Grid(opts.InitOpts(width="1400px", height="800px", theme=ThemeType.WHITE))
    grid_chart.add(
        kline,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", height="60%"
        ),
    )
    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", pos_top="70%", height="16%"
        ),
    )

    graph_path = os.path.join(cache_path, "%s_kline_%s.html" % (symbol, "fx"))
    grid_chart.render(path=graph_path)

    # 调用浏览器打开可视化结果
    if show:
        webbrowser.open(graph_path)


def show_bi_kline(kline_raw, show=True):
    freq = '5min'
    start_dt = kline_raw.iloc[0]["dt"]
    end_dt = kline_raw.iloc[-1]["dt"]

    x_data = kline_raw.dt.values.tolist()
    oclh = kline_raw[['open', 'close', 'low', 'high']].values.tolist()
    symbol = kline_raw.iloc[0]['symbol']

    kline = (
        Kline(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name=symbol,
            y_axis=oclh,
            itemstyle_opts=opts.ItemStyleOpts(color="#ec0000", color0="#00da3c"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="缠论分析结果：%s-%s" % (symbol, freq),
                subtitle="时间区间：%s 至 %s" % (start_dt, end_dt)
            ),
            xaxis_opts=opts.AxisOpts(type_="category"),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            legend_opts=opts.LegendOpts(
                is_show=True, pos_top=10, pos_left="center"
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=0,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="90%",
                    range_start=0,
                    range_end=100,
                ),
            ],
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                dimension=2,
                series_index=5,
                is_piecewise=True,
                pieces=[
                    {"value": 1, "color": "#ec0000"},
                    {"value": -1, "color": "#00da3c"},
                ],
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
            brush_opts=opts.BrushOpts(
                x_axis_index="all",
                brush_link="all",
                out_of_brush={"colorAlpha": 0.1},
                brush_type="lineX",
            ),
        )
    )

    chan = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("笔标记", kline_raw.bi.values.tolist(),
                   label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    bar = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="Volume",
            yaxis_data=kline_raw.vol.values.tolist(),
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                grid_index=1,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                is_scale=True,
                split_number=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    # Kline And Line
    kline = kline.overlap(chan)

    # Grid Overlap + Bar
    grid_chart = Grid(opts.InitOpts(width="1400px", height="800px", theme=ThemeType.WHITE))
    grid_chart.add(
        kline,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", height="60%"
        ),
    )
    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", pos_top="70%", height="16%"
        ),
    )

    graph_path = os.path.join(cache_path, "%s_kline_%s.html" % (symbol, "fx"))
    grid_chart.render(path=graph_path)

    # 调用浏览器打开可视化结果
    if show:
        webbrowser.open(graph_path)


def show_xd_kline(kline_raw, show=True):
    freq = '5min'
    start_dt = kline_raw.iloc[0]["dt"]
    end_dt = kline_raw.iloc[-1]["dt"]

    x_data = kline_raw.dt.values.tolist()
    oclh = kline_raw[['open', 'close', 'low', 'high']].values.tolist()
    symbol = kline_raw.iloc[0]['symbol']

    kline = (
        Kline(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name=symbol,
            y_axis=oclh,
            itemstyle_opts=opts.ItemStyleOpts(color="#ec0000", color0="#00da3c"),
        )
        .set_global_opts(
            title_opts=opts.TitleOpts(
                title="缠论分析结果：%s-%s" % (symbol, freq),
                subtitle="时间区间：%s 至 %s" % (start_dt, end_dt)
            ),
            xaxis_opts=opts.AxisOpts(type_="category"),
            yaxis_opts=opts.AxisOpts(
                is_scale=True,
                splitarea_opts=opts.SplitAreaOpts(
                    is_show=True, areastyle_opts=opts.AreaStyleOpts(opacity=1)
                ),
            ),
            legend_opts=opts.LegendOpts(
                is_show=True, pos_top=10, pos_left="center"
            ),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False,
                    type_="inside",
                    xaxis_index=[0, 1],
                    range_start=0,
                    range_end=100,
                ),
                opts.DataZoomOpts(
                    is_show=True,
                    xaxis_index=[0, 1],
                    type_="slider",
                    pos_top="90%",
                    range_start=0,
                    range_end=100,
                ),
            ],
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                axis_pointer_type="cross",
                background_color="rgba(245, 245, 245, 0.8)",
                border_width=1,
                border_color="#ccc",
                textstyle_opts=opts.TextStyleOpts(color="#000"),
            ),
            visualmap_opts=opts.VisualMapOpts(
                is_show=False,
                dimension=2,
                series_index=5,
                is_piecewise=True,
                pieces=[
                    {"value": 1, "color": "#ec0000"},
                    {"value": -1, "color": "#00da3c"},
                ],
            ),
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
            brush_opts=opts.BrushOpts(
                x_axis_index="all",
                brush_link="all",
                out_of_brush={"colorAlpha": 0.1},
                brush_type="lineX",
            ),
        )
    )

    chan_fx = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("分型标记", kline_raw.fx.values.tolist(),
                   label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    chan_bi = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("笔标记", kline_raw.bi.values.tolist(),
                   label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    chan_xd = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("线段标记", kline_raw.xd.values.tolist(),
                   label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    bar = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="Volume",
            yaxis_data=kline_raw.vol.values.tolist(),
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                grid_index=1,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                is_scale=True,
                split_number=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
                axisline_opts=opts.AxisLineOpts(is_show=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    # Kline And Line
    kline = kline.overlap(chan_fx)
    kline = kline.overlap(chan_bi)
    kline = kline.overlap(chan_xd)

    # Grid Overlap + Bar
    grid_chart = Grid(opts.InitOpts(width="1400px", height="800px", theme=ThemeType.WHITE))
    grid_chart.add(
        kline,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", height="60%"
        ),
    )
    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", pos_top="70%", height="16%"
        ),
    )

    graph_path = os.path.join(cache_path, "%s_kline_%s.html" % (symbol, "fx"))
    grid_chart.render(path=graph_path)

    # 调用浏览器打开可视化结果
    if show:
        webbrowser.open(graph_path)


if __name__ == '__main__':
    kline = get_kline('000001.SH', freq='5min', end_date='20190810', asset="I", indicators=("ma", 'macd'))
    kline = preprocess(kline)
    # show_preprocessed_kline(kline)
    kline = find_fx(kline)
    # show_fx_kline(kline)
    kline = find_bi(kline)
    # show_bi_kline(kline, show=True)
    kline = find_xd(kline)
    show_xd_kline(kline, show=True)

