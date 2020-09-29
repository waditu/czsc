# coding: utf-8
from typing import List


def cal_nbar_percentile(k: dict, kn: List[dict], n: int) -> float:
    """计算 N 周期区间百分位

    假设选股策略确认选股时间为 T，股价为 P，T+N 区间内的K线最高价为 MAX_P，最低价为 MIN_P，则
    N周期区间百分位 = (MAX_P - P) / (MAX_P - MIN_P) * 100;
    N周期区间百分位值域为(0, 100)，值越大，说明离区间最大值越远，对于做多交易而言有更高的安全性。

    :param k: dict
        信号出现时的 K 线，如：
        {'symbol': '000001.SH',
         'dt': '2007-04-05 15:00:00',
         'open': 3286.16,
         'close': 3319.14,
         'high': 3326.92,
         'low': 3259.63,
         'vol': 114528051.0}

    :param kn: List[dict]
        信号出现后的 N 根 K 线，如：
        [{'symbol': '000001.SH',
          'dt': '2007-04-06 15:00:00',
          'open': 3287.68,
          'close': 3323.59,
          'high': 3334.22,
          'low': 3273.86,
          'vol': 119644881.0},
         {'symbol': '000001.SH',
          'dt': '2007-04-09 15:00:00',
          'open': 3333.42,
          'close': 3398.95,
          'high': 3399.51,
          'low': 3333.26,
          'vol': 137314104.0}]

    :param n: int
        周期数 N

    :return: float
    """
    assert len(kn) == n, "计算 {} 周期区间百分位时传入的 kn 数量为 {}".format(n, len(kn))
    c = k['close']
    min_p = min([x['low'] for x in kn])
    max_p = max([x['high'] for x in kn])

    if max_p == min_p:
        return 0
    else:
        percentile = round((max_p-c) / (max_p-min_p) * 100, 2)
        return percentile

def cal_nbar_income(k: dict, kn: List[dict], n: int) -> float:
    """计算 N 周期区间收益

    假设选股策略确认选股时间为 T，股价为 P，第T+N 根K线收盘价为 C，则
    N周期绝对收益 = (C - P) / P * 100;
    N周期绝对收益值域为(-100, +inf)，值越大，说明绝对收益越大，对于做多交易而言有更高的收益率。

    :param k: dict
        信号出现时的 K 线，如：
        {'symbol': '000001.SH',
         'dt': '2007-04-05 15:00:00',
         'open': 3286.16,
         'close': 3319.14,
         'high': 3326.92,
         'low': 3259.63,
         'vol': 114528051.0}

    :param kn: List[dict]
        信号出现后的 N 根 K 线，如：
        [{'symbol': '000001.SH',
          'dt': '2007-04-06 15:00:00',
          'open': 3287.68,
          'close': 3323.59,
          'high': 3334.22,
          'low': 3273.86,
          'vol': 119644881.0},
         {'symbol': '000001.SH',
          'dt': '2007-04-09 15:00:00',
          'open': 3333.42,
          'close': 3398.95,
          'high': 3399.51,
          'low': 3333.26,
          'vol': 137314104.0}]

    :param n: int
        周期数 N

    :return: float
    """
    assert len(kn) == n, "计算 {} 周期区间收益时传入的 kn 数量为 {}".format(n, len(kn))
    c = k['close']
    last_c = kn[-1]['close']

    income = round((last_c - c) / c * 100, 2)
    return income











