# coding:utf-8
"""
交易模拟器，用于研究单标的的买卖点变化过程

"""
import sys
sys.path.insert(0, "C:\git_repo\zengbin93\chan")
import chan
print(chan.__version__)

import os
import time
import traceback
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
from chan import SolidAnalyze, KlineAnalyze, macd
from pyecharts import options as opts
from pyecharts.commons.utils import JsCode
from pyecharts.charts import Kline, Line, Bar, Grid, Scatter


# 首次使用，需要在这里设置你的 tushare token，用于获取数据；在同一台机器上，tushare token 只需要设置一次
# 没有 token，到 https://tushare.pro/register?reg=7 注册获取
# ts.set_token("your tushare token")

freq_map = {"1min": "1分钟", '5min': "5分钟", "30min": "30分钟", "D": "日线"}


def is_trade_day(date):
    """判断date日期是不是交易日

    :param date: str or datetime.date, 如 20180315
    :return: Bool
    """
    FILE_CALENDAR = "calendar.csv"
    if os.path.exists(FILE_CALENDAR) and \
            time.time() - os.path.getmtime(FILE_CALENDAR) < 3600 * 24:
        trade_calendar = pd.read_csv(FILE_CALENDAR, encoding='utf-8', dtype={"cal_date": str})
    else:
        pro = ts.pro_api()
        trade_calendar = pro.trade_cal()  # tushare提供的交易日历
        trade_calendar.to_csv(FILE_CALENDAR, index=False, encoding='utf-8')

    trade_day = trade_calendar[trade_calendar["is_open"] == 1]
    trade_day_list = [str(x).replace("-", "") for x in list(trade_day['cal_date'])]
    if isinstance(date, datetime):
        date = str(date.date()).replace("-", "")
    if date.replace("-", "") in trade_day_list:
        return True
    else:
        return False


def _get_start_date(end_date, freq):
    end_date = datetime.strptime(end_date, '%Y%m%d')
    if freq == '1min':
        start_date = end_date - timedelta(days=70)
    elif freq == '5min':
        start_date = end_date - timedelta(days=150)
    elif freq == '30min':
        start_date = end_date - timedelta(days=1000)
    elif freq == 'D':
        start_date = end_date - timedelta(weeks=1000)
    elif freq == 'W':
        start_date = end_date - timedelta(weeks=1000)
    else:
        raise ValueError("'freq' value error, current value is %s, "
                         "optional valid values are ['1min', '5min', '30min', "
                         "'D', 'W']" % freq)
    return start_date


def get_kline(ts_code, end_date, start_date=None, freq='30min', asset='E'):
    """获取指定级别的前复权K线

    :param ts_code: str
        股票代码，如 600122.SH
    :param freq: str
        K线级别，可选值 [1min, 5min, 15min, 30min, 60min, D, M, Y]
    :param end_date: str
        日期，如 20190610
    :param start_date:
    :param asset: str
        交易资产类型，可选值 E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
    :return: pd.DataFrame
        columns = ["symbol", "dt", "open", "close", "high", "low", "vol"]
    """
    if not start_date:
        start_date = _get_start_date(end_date, freq)
        start_date = start_date.date().__str__().replace("-", "")

    if freq.endswith('min'):
        end_date = datetime.strptime(end_date, '%Y%m%d')
        end_date = end_date + timedelta(days=1)
        end_date = end_date.date().__str__().replace("-", "")

    df = ts.pro_bar(ts_code=ts_code, freq=freq, start_date=start_date, end_date=end_date,
                    adj='qfq', asset=asset)

    # 统一 k 线数据格式为 6 列，分别是 ["symbol", "dt", "open", "close", "high", "low", "vr"]
    if "min" in freq:
        df.rename(columns={'ts_code': "symbol", "trade_time": "dt"}, inplace=True)
    else:
        df.rename(columns={'ts_code': "symbol", "trade_date": "dt"}, inplace=True)

    df.drop_duplicates(subset='dt', keep='first', inplace=True)
    df.sort_values('dt', inplace=True)
    df['dt'] = df.dt.apply(str)
    if freq.endswith("min"):
        # 清理 9:30 的空数据
        df['not_start'] = df.dt.apply(lambda x: not x.endswith("09:30:00"))
        df = df[df['not_start']]
    df.reset_index(drop=True, inplace=True)
    if freq == 'D':
        df['dt'] = df['dt'].apply(lambda x: datetime.strptime(x, "%Y%m%d").strftime("%Y-%m-%d %H:%M:%S"))

    k = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]

    for col in ['open', 'close', 'high', 'low']:
        k[col] = k[col].apply(round, args=(2,))
    return k


def get_klines(ts_code, end_date, freqs='1min,5min,30min,D', asset='E'):
    """获取不同级别K线"""
    klines = dict()
    freqs = freqs.split(",")
    for freq in freqs:
        df = get_kline(ts_code, end_date, freq=freq, asset=asset)
        klines[freq_map[freq]] = df
    return klines


def make_klines(k1):
    """从1分钟K线构造多级别K线

    :param k1: pd.DataFrame
        1分钟K线，输入的1分钟K线必须是交易日当天的全部1分钟K线，如果是实时行情，则是截止到交易时间的全部K线
    :return:
    """
    first_dt = k1.iloc[0]['dt']
    kd = pd.DataFrame([{
        'symbol': k1.iloc[0]['symbol'],
        'dt': first_dt.split(" ")[0] + " 00:00:00",
        'open': k1.iloc[0]['open'],
        'close': k1.iloc[-1]['close'],
        'high': max(k1.high),
        'low': min(k1.low),
        'vol': round(sum(k1.vol) / 100, 2)
    }])

    if first_dt.endswith("09:30:00"):
        k1 = k1.iloc[1:]

    cols = ['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']

    def _minute_kline(freq):
        p = {'5min': 5, '15min': 15, '30min': 30, '60min': 60}
        d = p[freq]
        k2 = []
        i = 0
        while i * d < len(k1):
            df = k1.iloc[i * d: (i + 1) * d]
            symbol = df.iloc[0]['symbol']
            dt = df.iloc[-1]['dt']
            open_ = df.iloc[0]['open']
            close_ = df.iloc[-1]['close']
            high_ = max(df.high)
            low_ = min(df.low)
            vol_ = sum(df.vol)

            k = {"symbol": symbol, "dt": dt, "open": open_, "close": close_,
                 "high": high_, "low": low_, "vol": vol_}
            k2.append(k)
            i += 1
        k2 = pd.DataFrame(k2)
        return k2[cols]

    klines = {"1分钟": k1, '5分钟': _minute_kline('5min'), '30分钟': _minute_kline('30min'), "日线": kd[cols]}
    return klines


def kline_simulator(ts_code, trade_dt, asset="E", count=5000):
    """K线模拟器（精确到分钟），每次模拟一天

    >>> ks = kline_simulator(ts_code="300803.SZ", trade_dt='20200310')
    >>> for k in ks.__iter__():
    >>>    print(k['5分钟'].tail(2))

    """
    if "-" in trade_dt:
        dt1 = datetime.strptime(trade_dt, '%Y-%m-%d')
    else:
        dt1 = datetime.strptime(trade_dt, '%Y%m%d')

    last_date = dt1 - timedelta(days=1)
    init_klines = get_klines(ts_code, last_date.strftime("%Y%m%d"), freqs='1min,5min,30min,D', asset=asset)

    k1 = get_kline(ts_code, end_date=dt1.strftime("%Y%m%d"), start_date=dt1.strftime("%Y%m%d"), freq='1min', asset=asset)
    if k1.iloc[0]['dt'].endswith("09:30:00"):
        k1 = k1.iloc[1:]

    for i in range(1, len(k1)+1):
        k1_ = k1.iloc[:i]
        klines = make_klines(k1_)
        # 合并成新K线
        new_klines = dict()
        for freq in init_klines.keys():
            new_klines[freq] = pd.concat([init_klines[freq], klines[freq]]).tail(count)
        yield new_klines


def trade_simulator(ts_code, end_date, file_bs, start_date=None, days=3, asset="E", watch_interval=5):
    """单只标的类实盘模拟，研究买卖点变化过程

    :param file_bs:
    :param ts_code: str
        标的代码，如 300033.SZ
    :param end_date: str
        截止日期，如 20200312
    :param start_date: str
        开始日期
    :param days: int
        从截止日线向前推的天数
    :param asset: str
        tushare 中的资产类型编码
    :param watch_interval: int
        看盘间隔，单位：分钟；默认值为 5分钟看盘一次
    :return: None
    """
    end_date = datetime.strptime(end_date.replace("-", ""), "%Y%m%d")
    if not start_date:
        start_date = end_date - timedelta(days=days)
    else:
        start_date = datetime.strptime(start_date.replace("-", ""), "%Y%m%d")
    results = []

    while start_date <= end_date:
        if (asset in ["E", "I"]) and (not is_trade_day(start_date.strftime('%Y%m%d'))):
            start_date += timedelta(days=1)
            continue

        ks = kline_simulator(ts_code, trade_dt=start_date.strftime('%Y%m%d'), asset=asset)
        for i, klines in enumerate(ks.__iter__(), 1):
            latest_dt = klines['1分钟'].iloc[-1]['dt']
            latest_price = klines['1分钟'].iloc[-1]['close']
            if i % watch_interval != 0:
                continue
            print(latest_dt)
            sa = SolidAnalyze(klines, symbol=ts_code)
            for func in [sa.is_first_buy, sa.is_second_buy, sa.is_third_buy, sa.is_xd_buy,
                         sa.is_first_sell, sa.is_second_sell, sa.is_third_sell, sa.is_xd_sell]:
                for freq in ['1分钟', '5分钟', '30分钟']:
                    try:
                        b, detail = func(freq, tolerance=0.1)
                        if b:
                            detail['交易时间'] = latest_dt
                            detail['交易价格'] = latest_price
                            detail['交易级别'] = freq
                            print(detail)
                            results.append(detail)
                    except:
                        traceback.print_exc()
                        continue

        df = pd.DataFrame(results)
        df.sort_values('交易时间', inplace=True)
        df = df.drop_duplicates(['出现时间', '基准价格', '操作提示', '标的代码'])
        cols = ['标的代码', '操作提示', '交易时间', '交易价格', '交易级别', '出现时间', '基准价格', '其他信息']
        df = df[cols]
        df.to_excel(file_bs, index=False)
        start_date += timedelta(days=1)


def draw(df, file_html="chan_bs.html", width="1400px", height="680px"):
    x = df.dt.to_list()
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
            title_opts=opts.TitleOpts(title="缠论买卖点分析", pos_left="0"),
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
                    is_show=True, xaxis_index=[0, 1], pos_top="97%", range_end=100
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
            linestyle_opts=opts.LineStyleOpts(opacity=1, type_='dotted', width=1.5),
            label_opts=opts.LabelOpts(is_show=False),
        )
            .add_yaxis(
            series_name="线段",
            y_axis=df.xd.tolist(),
            is_smooth=False,
            is_connect_nones=True,
            symbol='triangle',
            symbol_size=12,
            linestyle_opts=opts.LineStyleOpts(opacity=1, type_='solid', width=1.5),
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

    df1 = df[df['基准价格'] > 0]
    c = (
        Scatter()
            .add_xaxis(df1['出现时间'].to_list())
            .add_yaxis(
            "买卖点",
            df1['基准价格'].to_list(),
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
    grid_chart = Grid(init_opts=opts.InitOpts(width=width, height=height, page_title="缠论买卖点分析"))
    grid_chart.add_js_funcs("var barData = {}".format(df[['open', 'close', 'low', 'high']].values.tolist()))
    grid_chart.add_js_funcs("var bsName = {}".format(df1[["操作提示", "基准价格"]].values.tolist()))
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


def check_trade(ts_code, file_bs, freq, end_date="20200314", asset="E", file_html="bs.html"):
    """在图上画出买卖点"""
    bs = pd.read_excel(file_bs)
    bs['f'] = bs['操作提示'].apply(lambda x: 1 if freq_map[freq] in x and "线" not in x else 0)
    bs = bs[bs.f == 1]
    bs['操作提示'] = bs['操作提示'].apply(lambda x: x.replace(freq_map[freq], ""))
    df = get_kline(ts_code, freq=freq, end_date=end_date, asset=asset)
    ka = KlineAnalyze(df)
    df = pd.DataFrame(ka.kline)
    df = macd(df)
    df = df.merge(bs[['操作提示', '出现时间', '基准价格']], left_on='dt', right_on='出现时间', how='left')
    draw(df, file_html)


if __name__ == '__main__':
    ts_code = '000001.SH'
    asset = "I"
    end_date = '20200313'
    freq = '5min'
    file_bs = f"{ts_code}买卖点变化过程.xlsx"
    file_html = f"{ts_code}_{freq}_{end_date}_bs.html"

    # step 1. 仿真交易
    # trade_simulator(ts_code, end_date=end_date, file_bs=file_bs, days=60, asset=asset, watch_interval=5)

    # step 2. 查看仿真交易过程的买卖点提示
    check_trade(ts_code, file_bs, freq=freq, asset=asset, end_date=end_date, file_html=file_html)
