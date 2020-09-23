# coding: utf-8
from typing import List


def cal_nbar_percentile(k: dict, kn: List[dict], n: int) -> float:
    """计算 N 周期区间百分位


    :param k: dict
        信号出现时的 K 线
    :param kn: List[dict]
        信号出现后的 N 根 K 线
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
        percentile = round((c-min_p) / (max_p-min_p) * 100, 2)
        return percentile

def cal_nbar_income(k: dict, kn: List[dict], n: int) -> float:
    """计算 N 周期区间收益


    :param k: dict
        信号出现时的 K 线
    :param kn: List[dict]
        信号出现后的 N 根 K 线
    :param n: int
        周期数 N
    :return: float
    """
    assert len(kn) == n, "计算 {} 周期区间收益时传入的 kn 数量为 {}".format(n, len(kn))
    c = k['close']
    last_c = kn[-1]['close']

    income = round((last_c - c) / c * 100, 2)
    return income











