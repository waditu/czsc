# coding: utf-8
"""
https://gallery.pyecharts.org/#/Candlestick/professional_kline_chart


"""
from pyecharts import options as opts
from pyecharts.charts import Kline, Line, Bar, Scatter, Grid
from pyecharts.commons.utils import JsCode

from czsc.analyze import KlineAnalyze


def ka_to_echarts(ka: KlineAnalyze, width="1500px", height='800px'):
    # 配置项设置
    # ------------------------------------------------------------------------------------------------------------------
    bg_color = "#1f212d"    # 背景
    up_color = "#F9293E"
    down_color = "#00aa3b"

    init_opts = opts.InitOpts(bg_color=bg_color, width=width, height=height, animation_opts=opts.AnimationOpts(False))
    title_opts = opts.TitleOpts(title="{} - {}".format(ka.symbol, ka.name),
                                subtitle="from {} to {}".format(ka.start_dt, ka.end_dt),
                                pos_top="1%",
                                title_textstyle_opts=opts.TextStyleOpts(color=up_color, font_size=20),
                                subtitle_textstyle_opts=opts.TextStyleOpts(color=down_color, font_size=12))

    label_not_show_opts = opts.LabelOpts(is_show=False)
    legend_not_show_opts = opts.LegendOpts(is_show=False)
    red_item_style = opts.ItemStyleOpts(color=up_color)
    green_item_style = opts.ItemStyleOpts(color=down_color)
    k_style_opts = opts.ItemStyleOpts(color=up_color, color0=down_color, border_color=up_color,
                                      border_color0=down_color, opacity=0.8)

    legend_opts = opts.LegendOpts(is_show=True, pos_top="1%", pos_left="30%", item_width=14, item_height=8,
                                  textstyle_opts=opts.TextStyleOpts(font_size=12, color="#0e99e2"))
    brush_opts = opts.BrushOpts(tool_box=["rect", "polygon", "keep", "clear"],
                                x_axis_index="all", brush_link="all",
                                out_of_brush={"colorAlpha": 0.1}, brush_type="lineX")

    axis_pointer_opts = opts.AxisPointerOpts(is_show=True, link=[{"xAxisIndex": "all"}])

    dz_inside = opts.DataZoomOpts(False, "inside", xaxis_index=[0, 1, 2])
    dz_slider = opts.DataZoomOpts(True, "slider", xaxis_index=[0, 1, 2], pos_top="96%", pos_bottom="0%")

    yaxis_opts = opts.AxisOpts(is_scale=True, axislabel_opts=opts.LabelOpts(color="#c7c7c7", font_size=8, position="inside"))

    grid0_xaxis_opts = opts.AxisOpts(type_="category", grid_index=0, axislabel_opts=label_not_show_opts,
                                     split_number=20, min_="dataMin", max_="dataMax",
                                     is_scale=True, boundary_gap=False, axisline_opts=opts.AxisLineOpts(is_on_zero=False))

    tool_tip_opts = opts.TooltipOpts(
        trigger="axis",
        axis_pointer_type="cross",
        background_color="rgba(245, 245, 245, 0.8)",
        border_width=1,
        border_color="#ccc",
        position=JsCode("""
                    function (pos, params, el, elRect, size) {
    					var obj = {top: 10};
    					obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
    					return obj;
    				}
                    """),
        textstyle_opts=opts.TextStyleOpts(color="#000"),
    )

    # 数据预处理
    # ------------------------------------------------------------------------------------------------------------------
    dts = [x['dt'] for x in ka.kline_raw]
    k_data = [[x['open'], x['close'], x['low'], x['high']] for x in ka.kline_raw]
    ma = ka.ma

    vol = []
    for row in ka.kline_raw:
        item_style = red_item_style if row['close'] > row['open'] else green_item_style
        bar = opts.BarItem(value=row['vol'], itemstyle_opts=item_style, label_opts=label_not_show_opts)
        vol.append(bar)

    macd = []
    for row in ka.macd:
        item_style = red_item_style if row['macd'] > 0 else green_item_style
        bar = opts.BarItem(value=round(row['macd'], 4), itemstyle_opts=item_style, label_opts=label_not_show_opts)
        macd.append(bar)

    diff = [round(x['diff'], 4) for x in ka.macd]
    dea = [round(x['dea'], 4) for x in ka.macd]

    # K 线主图
    # ------------------------------------------------------------------------------------------------------------------
    chart_k = Kline()
    chart_k.add_xaxis(xaxis_data=dts)
    chart_k.add_yaxis(series_name="Kline", y_axis=k_data, itemstyle_opts=k_style_opts)

    chart_k.set_global_opts(
            legend_opts=legend_opts,
            datazoom_opts=[dz_inside, dz_slider],
            yaxis_opts=yaxis_opts,
            tooltip_opts=tool_tip_opts,
            axispointer_opts=axis_pointer_opts,
            brush_opts=brush_opts,
            title_opts=title_opts,
            xaxis_opts=grid0_xaxis_opts
    )

    # 均线图
    # ------------------------------------------------------------------------------------------------------------------
    chart_ma = Line()
    chart_ma.add_xaxis(xaxis_data=dts)

    ma_keys = [x for x in ma[0].keys() if "ma" in x][:3]
    ma_colors = ["#39afe6", "#da6ee8", "#00940b"]
    for i, k in enumerate(ma_keys):
        y_data = [x[k] for x in ma]
        chart_ma.add_yaxis(series_name=k.upper(), y_axis=y_data, is_smooth=True,
                           is_selected=False, symbol_size=0, label_opts=label_not_show_opts,
                           linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0, color=ma_colors[i]))

    chart_ma.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
    chart_k = chart_k.overlap(chart_ma)

    # 缠论结果
    # ------------------------------------------------------------------------------------------------------------------
    fx_dts = [x['dt'] for x in ka.fx_list]
    fx_val = [x['fx'] for x in ka.fx_list]
    chart_fx = Scatter()
    chart_fx.add_xaxis(fx_dts)
    chart_fx.add_yaxis(series_name="FX", y_axis=fx_val, is_selected=False,
                       symbol="circle", symbol_size=6, label_opts=label_not_show_opts,
                       itemstyle_opts=opts.ItemStyleOpts(color="rgba(152, 147, 193, 1.0)",))

    chart_fx.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
    chart_k = chart_k.overlap(chart_fx)

    bi_dts = [x['dt'] for x in ka.bi_list]
    bi_val = [x['bi'] for x in ka.bi_list]
    chart_bi = Scatter()
    chart_bi.add_xaxis(bi_dts)
    chart_bi.add_yaxis(series_name="BI", y_axis=bi_val, is_selected=True,
                       symbol="diamond", symbol_size=10, label_opts=label_not_show_opts,
                       itemstyle_opts=opts.ItemStyleOpts(color="rgba(184, 117, 225, 1.0)",))

    chart_bi.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
    chart_k = chart_k.overlap(chart_bi)

    xd_dts = [x['dt'] for x in ka.xd_list]
    xd_val = [x['xd'] for x in ka.xd_list]
    chart_xd = Scatter()
    chart_xd.add_xaxis(xd_dts)
    chart_xd.add_yaxis(series_name="XD", y_axis=xd_val, is_selected=True, symbol="triangle", symbol_size=10,
                       itemstyle_opts=opts.ItemStyleOpts(color="rgba(37, 141, 54, 1.0)",))

    chart_xd.set_global_opts(xaxis_opts=grid0_xaxis_opts, legend_opts=legend_not_show_opts)
    chart_k = chart_k.overlap(chart_xd)

    # 成交量图
    # ------------------------------------------------------------------------------------------------------------------
    chart_vol = Bar()
    chart_vol.add_xaxis(dts)
    chart_vol.add_yaxis(series_name="Volume", y_axis=vol, bar_width='60%')
    chart_vol.set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=1,
                axislabel_opts=opts.LabelOpts(is_show=True, font_size=8, color="#9b9da9"),
            ),
            yaxis_opts=yaxis_opts, legend_opts=legend_not_show_opts,
        )

    # MACD图
    # ------------------------------------------------------------------------------------------------------------------
    chart_macd = Bar()
    chart_macd.add_xaxis(dts)
    chart_macd.add_yaxis(series_name="MACD", y_axis=macd, bar_width='60%')
    chart_macd.set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=2,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=2,
                split_number=4,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=True, color="#c7c7c7"),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )

    line = Line()
    line.add_xaxis(dts)
    line.add_yaxis(series_name="DIFF", y_axis=diff, label_opts=label_not_show_opts, is_symbol_show=False,
                   linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0, color="#da6ee8"))
    line.add_yaxis(series_name="DEA", y_axis=dea, label_opts=label_not_show_opts, is_symbol_show=False,
                   linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0, color="#39afe6"))

    chart_macd = chart_macd.overlap(line)

    grid0_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="12%", height="58%")
    grid1_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="74%", height="8%")
    grid2_opts = opts.GridOpts(pos_left="0%", pos_right="1%", pos_top="86%", height="10%")

    grid_chart = Grid(init_opts)
    grid_chart.add(chart_k, grid_opts=grid0_opts)
    grid_chart.add(chart_vol, grid_opts=grid1_opts)
    grid_chart.add(chart_macd, grid_opts=grid2_opts)
    return grid_chart
