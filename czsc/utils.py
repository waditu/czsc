# coding: utf-8

import pandas as pd
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
from pyecharts.charts import Kline, Line, Bar, Grid, Scatter
import mplfinance as mpf
import matplotlib as mpl
import matplotlib.pyplot as plt

from .ta import macd


def plot_kline(ka, bs=None, file_html="kline.html", width="1400px", height="680px"):
    """

    :param ka: KlineAnalyze
    :param bs: pd.DataFrame
        买卖点，包含三个字段 ["操作提示", "交易时间", "交易价格"]
    :param file_html: str
    :param width: str
    :param height: str
    :return: None
    """
    df = pd.DataFrame(ka.kline)
    df = macd(df)
    x = df.dt.to_list()
    title = "%s | %s 至 %s" % (ka.symbol, ka.start_dt, ka.end_dt)
    kline = (
        Kline()
            .add_xaxis(xaxis_data=x)
            .add_yaxis(
            series_name="",
            y_axis=df[['open', 'close', 'low', 'high']].values.tolist(),
            itemstyle_opts=opts.ItemStyleOpts(
                color="#ef232a",
                color0="#14b143",
                border_color="#ef232a",
                border_color0="#14b143",
            ),
        )
            .set_series_opts(
            markarea_opts=opts.MarkAreaOpts(is_silent=True)
        )
            .set_global_opts(
            title_opts=opts.TitleOpts(title=title, pos_left="0"),
            xaxis_opts=opts.AxisOpts(
                type_="category",
                is_scale=True,
                boundary_gap=False,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                split_number=20,
                min_="dataMin",
                max_="dataMax",
            ),
            yaxis_opts=opts.AxisOpts(
                is_scale=True, splitline_opts=opts.SplitLineOpts(is_show=True),
                axislabel_opts=opts.LabelOpts(is_show=True, position="inside")
            ),
            tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="line"),
            datazoom_opts=[
                opts.DataZoomOpts(
                    is_show=False, type_="inside", xaxis_index=[0, 0], range_end=100
                ),
                opts.DataZoomOpts(
                    is_show=True, xaxis_index=[0, 1], pos_top="96%", range_end=100
                ),
                opts.DataZoomOpts(is_show=False, xaxis_index=[0, 2], range_end=100),
            ],
            # 三个图的 axis 连在一块
            axispointer_opts=opts.AxisPointerOpts(
                is_show=True,
                link=[{"xAxisIndex": "all"}],
                label=opts.LabelOpts(background_color="#777"),
            ),
        )
    )

    kline_line = (
        Line()
            .add_xaxis(xaxis_data=x)
            .add_yaxis(
            series_name="笔",
            y_axis=df.bi.tolist(),
            is_smooth=False,
            is_connect_nones=True,
            symbol='diamond',
            symbol_size=8,
            linestyle_opts=opts.LineStyleOpts(opacity=1, type_='dotted', width=2),
            label_opts=opts.LabelOpts(is_show=False),
        )
            .add_yaxis(
            series_name="线段",
            y_axis=df.xd.tolist(),
            is_smooth=False,
            is_connect_nones=True,
            symbol='triangle',
            symbol_size=12,
            linestyle_opts=opts.LineStyleOpts(opacity=1, type_='solid', width=2),
            label_opts=opts.LabelOpts(is_show=True, position='right'),
        )
            .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=1,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                grid_index=1,
                split_number=3,
                axisline_opts=opts.AxisLineOpts(is_on_zero=False),
                axistick_opts=opts.AxisTickOpts(is_show=False),
                splitline_opts=opts.SplitLineOpts(is_show=False),
                axislabel_opts=opts.LabelOpts(is_show=True, position="inside"),
            ),
        )
    )
    # Overlap Kline + Line
    overlap_kline_line = kline.overlap(kline_line)

    if isinstance(bs, pd.DataFrame) and len(bs) > 0:
        c = (
            Scatter()
                .add_xaxis(bs['交易时间'].to_list())
                .add_yaxis(
                "买卖点",
                bs['交易价格'].to_list(),
                label_opts=opts.LabelOpts(
                    is_show=True,
                    position="left",
                    formatter=JsCode(
                        "function(params){return bsName[params.dataIndex][0];}"
                    )
                ),
            ))
        overlap_kline_line = overlap_kline_line.overlap(c)

    # draw volume
    bar_1 = (
        Bar()
            .add_xaxis(xaxis_data=x)
            .add_yaxis(
            series_name="Volumn",
            yaxis_data=df.vol.tolist(),
            xaxis_index=1,
            yaxis_index=1,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                color=JsCode(
                    """
                function(params) {
                    var colorList;
                    if (barData[params.dataIndex][1] > barData[params.dataIndex][0]) {
                        colorList = '#ef232a';
                    } else {
                        colorList = '#14b143';
                    }
                    return colorList;
                }
                """
                )
            ),
        )
            .set_global_opts(
            xaxis_opts=opts.AxisOpts(
                type_="category",
                grid_index=1,
                axislabel_opts=opts.LabelOpts(is_show=False),
            ),
            yaxis_opts=opts.AxisOpts(
                axislabel_opts=opts.LabelOpts(is_show=True, position='inside')
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    # Bar-2 (Overlap Bar + Line)
    bar_2 = (
        Bar()
            .add_xaxis(xaxis_data=x)
            .add_yaxis(
            series_name="MACD",
            yaxis_data=df.macd.tolist(),
            xaxis_index=2,
            yaxis_index=2,
            label_opts=opts.LabelOpts(is_show=False),
            itemstyle_opts=opts.ItemStyleOpts(
                color=JsCode(
                    """
                        function(params) {
                            var colorList;
                            if (params.data >= 0) {
                              colorList = '#ef232a';
                            } else {
                              colorList = '#14b143';
                            }
                            return colorList;
                        }
                        """
                )
            ),
        )
            .set_global_opts(
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
                axislabel_opts=opts.LabelOpts(is_show=True, position="inside"),
            ),
            legend_opts=opts.LegendOpts(is_show=False),
        )
    )

    line_2 = (
        Line()
            .add_xaxis(xaxis_data=x)
            .add_yaxis(
            series_name="DIF",
            y_axis=df['diff'].tolist(),
            xaxis_index=2,
            yaxis_index=2,
            label_opts=opts.LabelOpts(is_show=False),
        )
            .add_yaxis(
            series_name="DEA",
            y_axis=df['dea'].tolist(),
            xaxis_index=2,
            yaxis_index=2,
            label_opts=opts.LabelOpts(is_show=False),
        )
            .set_global_opts(legend_opts=opts.LegendOpts(is_show=False))
    )

    # draw MACD
    overlap_bar_line = bar_2.overlap(line_2)

    # 最后的 Grid
    grid_chart = Grid(init_opts=opts.InitOpts(width=width, height=height, page_title=title))
    grid_chart.add_js_funcs("var barData = {}".format(df[['open', 'close', 'low', 'high']].values.tolist()))
    if isinstance(bs, pd.DataFrame) and len(bs) > 0:
        grid_chart.add_js_funcs("var bsName = {}".format(bs[["操作提示", "交易价格"]].values.tolist()))

    grid_chart.add(
        overlap_kline_line,
        grid_opts=opts.GridOpts(pos_left="3%", pos_right="1%", height="60%"),
    )
    grid_chart.add(
        bar_1,
        grid_opts=opts.GridOpts(pos_left="3%", pos_right="1%", pos_top="71%", height="10%"),
    )
    grid_chart.add(
        overlap_bar_line,
        grid_opts=opts.GridOpts(pos_left="3%", pos_right="1%", pos_top="82%", height="14%"),
    )
    grid_chart.render(path=file_html)


def plot_ka(ka, file_image, mav=(5, 20, 120, 250), max_k_count=1000, dpi=50):
    """绘制 ka，保存到 file_image"""
    df = pd.DataFrame(ka.kline)
    df.rename({"open": "Open", "close": "Close", "high": "High",
               "low": "Low", "vol": "Volume"}, axis=1, inplace=True)
    df.index = pd.to_datetime(df['dt'])
    df = df.tail(max_k_count)
    kwargs = dict(type='candle', mav=mav, volume=True)

    bi_xd = [
        [(x['dt'], x['bi']) for _, x in df.iterrows() if x['bi'] > 0],
        [(x['dt'], x['xd']) for _, x in df.iterrows() if x['xd'] > 0]
    ]

    mc = mpf.make_marketcolors(
        up='red',
        down='green',
        edge='i',
        wick='i',
        volume='in',
        inherit=True)

    s = mpf.make_mpf_style(
        gridaxis='both',
        gridstyle='-.',
        y_on_right=False,
        marketcolors=mc)

    mpl.rcParams['font.sans-serif'] = ['KaiTi']
    mpl.rcParams['font.serif'] = ['KaiTi']
    mpl.rcParams['font.size'] = 48
    mpl.rcParams['axes.unicode_minus'] = False
    mpl.rcParams['lines.linewidth'] = 1.0

    title = '%s缠论分析结果（%s - %s）' % (ka.symbol, df.index[0].__str__(), df.index[-1].__str__())
    fig, axes = mpf.plot(df, columns=['Open', 'High', 'Low', 'Close', 'Volume'], style=s,
                         title=title, ylabel='K线', ylabel_lower='成交量', **kwargs,
                         alines=dict(alines=bi_xd, colors=['r', 'g'], linewidths=8, alpha=0.35),
                         returnfig=True)

    w = len(df) * 0.15
    fig.set_size_inches(w, 30)
    ax = plt.gca()
    ax.set_xbound(-1, len(df)+1)
    fig.savefig(fname=file_image, dpi=dpi, bbox_inches='tight')


