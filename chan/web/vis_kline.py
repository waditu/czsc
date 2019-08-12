# coding: utf-8
"""


https://pyecharts.org/#/zh-cn/rectangular_charts?id=klinecandlestick%ef%bc%9ak%e7%ba%bf%e5%9b%be

"""

import os
import webbrowser
from pyecharts import options as opts
from pyecharts.charts import Kline, Grid, Line, Bar, Scatter
from pyecharts.globals import ThemeType, CurrentConfig

from chan.a import get_kline
from chan.utils import cache_path
from chan.analyze import preprocess, find_fx, find_bi, find_xd


CurrentConfig.PAGE_TITLE = "chan - 缠论分析"


def kline_viewer(ts_code, freq, end_date, asset='E', show=True):
    """

    :param show:
    :param ts_code:
    :param freq:
    :param end_date:
    :param asset:
    :return:

    example:

    >>> from chan.web.vis_kline import kline_viewer
    >>> kline_viewer(ts_code='002739.SZ', freq='1min', end_date="20190809", asset='E')
    """
    kline_raw = get_kline(ts_code, freq=freq, end_date=end_date, asset=asset, indicators=('ma', 'macd'))

    for col in ['open', 'close', 'high', 'low']:
        kline_raw[col] = kline_raw[col].apply(round, args=(2,))

    kline_chan = find_xd(find_bi(find_fx(preprocess(kline_raw))))
    kline_chan = kline_chan[['dt', 'fx', 'fx_mark', 'bi', 'bi_mark', 'xd', 'xd_mark']]
    kline_raw = kline_raw.merge(kline_chan, how='left', on='dt')

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
                is_show=True, pos_top=5, pos_left="center"
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
                    pos_top="60%",
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

    line = (
        Line(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="MA5",
            y_axis=kline_raw.ma5.values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA10",
            y_axis=kline_raw.ma10.values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA20",
            y_axis=kline_raw.ma20.values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA60",
            y_axis=kline_raw.ma60.values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA120",
            y_axis=kline_raw.ma120.values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="MA250",
            y_axis=kline_raw.ma250.values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
    )

    chan_fx = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("分型标记", kline_raw.fx.values.tolist())
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    chan_bi = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("笔标记", kline_raw.bi.values.tolist())
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    chan_xd = (
        Scatter(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis("线段标记", kline_raw.xd.values.tolist())
        .set_global_opts(
            visualmap_opts=opts.VisualMapOpts(type_="size", max_=150, min_=20),
        )
    )

    # Kline And Line
    kline = kline.overlap(line)
    kline = kline.overlap(chan_fx)
    kline = kline.overlap(chan_bi)
    kline = kline.overlap(chan_xd)
    # ==========================================================
    macd_line = (
        Line(init_opts=opts.InitOpts(theme=ThemeType.WHITE))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="DEA",
            y_axis=kline_raw['dea'].values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .add_yaxis(
            series_name="DIFF",
            y_axis=kline_raw['diff'].values.tolist(),
            is_smooth=True,
            is_symbol_show=False,
            is_hover_animation=False,
            linestyle_opts=opts.LineStyleOpts(width=2, opacity=0.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
        .set_global_opts(xaxis_opts=opts.AxisOpts(type_="category"))
    )

    macd_bar = (
        Bar(init_opts=opts.InitOpts(theme=ThemeType.LIGHT))
        .add_xaxis(xaxis_data=x_data)
        .add_yaxis(
            series_name="Volume",
            yaxis_data=kline_raw.macd.values.tolist(),
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

    macd = macd_line.overlap(macd_bar)

    # ==========================================================

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

    # Grid Overlap + Bar
    grid_chart = Grid(opts.InitOpts(width="1500px", height="800px", theme=ThemeType.WHITE))
    grid_chart.add(
        kline,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", height="50%"
        ),
    )
    grid_chart.add(
        macd,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", pos_top="60%", height="16%"
        ),
    )
    grid_chart.add(
        bar,
        grid_opts=opts.GridOpts(
            pos_left="8%", pos_right="8%", pos_top="70%", height="16%"
        ),
    )

    graph_path = os.path.join(cache_path, "%s_kline_%s.html" % (symbol, freq))
    grid_chart.render(path=graph_path)

    # 调用浏览器打开可视化结果
    if show:
        webbrowser.open(graph_path)
