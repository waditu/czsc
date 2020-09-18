# coding: utf-8

import pandas as pd
import mplfinance as mpf
import matplotlib as mpl
import matplotlib.pyplot as plt
from pyecharts import options as opts
from pyecharts.charts import Kline, Line, Bar, Scatter, Grid
from pyecharts.commons.utils import JsCode


def plot_ka(ka, file_image, mav=(5, 20, 120, 250), max_k_count=1000, dpi=50):
    """绘制 ka，保存到 file_image"""
    df = ka.to_df(use_macd=True, ma_params=(5, 20,), max_count=max_k_count)
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

    title = '%s@%s（%s - %s）' % (ka.symbol, ka.name, df.index[0].__str__(), df.index[-1].__str__())
    fig, axes = mpf.plot(df, columns=['Open', 'High', 'Low', 'Close', 'Volume'], style=s,
                         title=title, ylabel='K线', ylabel_lower='成交量', **kwargs,
                         alines=dict(alines=bi_xd, colors=['r', 'g'], linewidths=8, alpha=0.35),
                         returnfig=True)

    w = len(df) * 0.15
    fig.set_size_inches(w, 30)
    ax = plt.gca()
    ax.set_xbound(-1, len(df) + 1)
    fig.savefig(fname=file_image, dpi=dpi, bbox_inches='tight')
    plt.close()


def ka_to_echarts(ka, width="1500px", height='800px'):
    """用 pyecharts 绘制分析结果

    :param ka: KlineAnalyze
    :param width: str
    :param height: str
    :return:
    """
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

    dz_inside = opts.DataZoomOpts(False, "inside", xaxis_index=[0, 1, 2], range_start=80, range_end=100)
    dz_slider = opts.DataZoomOpts(True, "slider", xaxis_index=[0, 1, 2], pos_top="96%", pos_bottom="0.5%", range_start=80, range_end=100)

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

    ma_keys = [x for x in ma[0].keys() if "ma" in x]
    for i, k in enumerate(ma_keys):
        y_data = [x[k] for x in ma]
        chart_ma.add_yaxis(series_name=k.upper(), y_axis=y_data, is_smooth=True,
                           is_selected=False, symbol_size=0, label_opts=label_not_show_opts,
                           linestyle_opts=opts.LineStyleOpts(opacity=0.8, width=1.0))

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

class KlineGenerator:
    """K线生成器，仿实盘"""

    def __init__(self, max_count=5000, freqs=None):
        """

        :param max_count: int
            最大K线数量
        :param freqs: list of str
            级别列表，默认值为 ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        """
        self.max_count = max_count
        if freqs is None:
            self.freqs = ['周线', '日线', '60分钟', '30分钟', '15分钟', '5分钟', '1分钟']
        else:
            self.freqs = freqs
        self.m1 = []
        self.m5 = []
        self.m15 = []
        self.m30 = []
        self.m60 = []
        self.D = []
        self.W = []
        self.end_dt = None
        self.symbol = None

    def __repr__(self):
        return "<KlineGenerator for {}; latest_dt={}>".format(self.symbol, self.end_dt)

    def update(self, k):
        """输入1分钟最新K线，更新其他级别K线

        :param k: dict
            {'symbol': '000001.XSHG',
             'dt': Timestamp('2020-07-16 14:51:00'),  # 必须是K线结束时间
             'open': 3216.8,
             'close': 3216.63,
             'high': 3216.95,
             'low': 3216.2,
             'vol': '270429600'}
        """
        self.end_dt = k['dt']
        self.symbol = k['symbol']

        # 更新1分钟线
        if "1分钟" in self.freqs:
            if not self.m1:
                self.m1.append(k)
            else:
                if k['dt'] > self.m1[-1]['dt']:
                    self.m1.append(k)
                elif k['dt'] == self.m1[-1]['dt']:
                    self.m1[-1] = k
                else:
                    raise ValueError("1分钟新K线的时间必须大于等于最后一根K线的时间")
            self.m1 = self.m1[-self.max_count:]

        # 更新5分钟线
        if "5分钟" in self.freqs:
            if not self.m5:
                self.m5.append(k)
            last_m5 = self.m5[-1]
            if last_m5['dt'].minute % 5 == 0 and k['dt'].minute % 5 != 0:
                self.m5.append(k)
            else:
                new = dict(last_m5)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m5['high']),
                    "low": min(k['low'], last_m5['low']),
                    "vol": k['vol'] + last_m5['vol']
                })
                self.m5[-1] = new
            self.m5 = self.m5[-self.max_count:]

        # 更新15分钟线
        if "15分钟" in self.freqs:
            if not self.m15:
                self.m15.append(k)
            last_m15 = self.m15[-1]
            if last_m15['dt'].minute % 15 == 0 and k['dt'].minute % 15 != 0:
                self.m15.append(k)
            else:
                new = dict(last_m15)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m15['high']),
                    "low": min(k['low'], last_m15['low']),
                    "vol": k['vol'] + last_m15['vol']
                })
                self.m15[-1] = new
            self.m15 = self.m15[-self.max_count:]

        # 更新30分钟线
        if "30分钟" in self.freqs:
            if not self.m30:
                self.m30.append(k)
            last_m30 = self.m30[-1]
            if last_m30['dt'].minute % 30 == 0 and k['dt'].minute % 30 != 0:
                self.m30.append(k)
            else:
                new = dict(last_m30)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m30['high']),
                    "low": min(k['low'], last_m30['low']),
                    "vol": k['vol'] + last_m30['vol']
                })
                self.m30[-1] = new
            self.m30 = self.m30[-self.max_count:]

        # 更新60分钟线
        if "60分钟" in self.freqs:
            if not self.m60:
                self.m60.append(k)
            last_m60 = self.m60[-1]
            if last_m60['dt'].minute % 60 == 0 and k['dt'].minute % 60 != 0:
                self.m60.append(k)
            else:
                new = dict(last_m60)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_m60['high']),
                    "low": min(k['low'], last_m60['low']),
                    "vol": k['vol'] + last_m60['vol']
                })
                self.m60[-1] = new
            self.m60 = self.m60[-self.max_count:]

        # 更新日线
        if "日线" in self.freqs:
            if not self.D:
                self.D.append(k)
            last_d = self.D[-1]
            if k['dt'].date() != last_d['dt'].date():
                self.D.append(k)
            else:
                new = dict(last_d)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_d['high']),
                    "low": min(k['low'], last_d['low']),
                    "vol": k['vol'] + last_d['vol']
                })
                self.D[-1] = new
            self.D = self.D[-self.max_count:]

        # 更新周线
        if "周线" in self.freqs:
            if not self.W:
                self.W.append(k)
            last_w = self.W[-1]
            if k['dt'].weekday() == 0 and k['dt'].weekday() != last_w['dt'].weekday():
                self.W.append(k)
            else:
                new = dict(last_w)
                new.update({
                    'close': k['close'],
                    "dt": k['dt'],
                    "high": max(k['high'], last_w['high']),
                    "low": min(k['low'], last_w['low']),
                    "vol": k['vol'] + last_w['vol']
                })
                self.W[-1] = new
            self.W = self.W[-self.max_count:]

    def get_kline(self, freq, count):
        """获取单个级别的K线

        :param freq: str
            级别名称，可选值 1分钟；5分钟；15分钟；30分钟；60分钟；日线；周线
        :param count: int
            数量
        :return: list of dict
        """
        freqs_map = {"1分钟": self.m1, "5分钟": self.m5, "15分钟": self.m15,
                     "30分钟": self.m30, "60分钟": self.m60, "日线": self.D, "周线": self.W}
        return [dict(x) for x in freqs_map[freq][-count:]]

    def get_klines(self, counts=None):
        """获取多个级别的K线

        :param counts: dict
            默认值 {"1分钟": 1000, "5分钟": 1000, "30分钟": 1000, "日线": 100}
        :return: dict of list of dict
        """
        if counts is None:
            counts = {"1分钟": 1000, "5分钟": 1000, "30分钟": 1000, "日线": 100}
        return {k: self.get_kline(k, v) for k, v in counts.items()}
