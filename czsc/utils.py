# coding: utf-8

import pandas as pd
import mplfinance as mpf
import matplotlib as mpl
import matplotlib.pyplot as plt


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
