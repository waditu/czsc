# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/21 12:18
describe: 信号计算的工具函数
"""
import numpy as np
import pandas as pd
import traceback
from datetime import datetime
from typing import List, Union

from ..utils.ta import KDJ
from ..objects import RawBar, BI, Direction


def return_to_label(r, th=50):
    """收益转标签

    :param r: 收益值
    :param th: 阈值
    :return:
    """
    if r > 0:
        if r > th:
            return "超强"
        else:
            return "强势"
    else:
        if abs(r) > th:
            return "超弱"
        else:
            return "弱势"


def get_sub_span(bis: List[BI], start_dt: [datetime, str], end_dt: [datetime, str], direction: Direction) -> List[BI]:
    """获取子区间（这是进行多级别联立分析的关键步骤）

    :param bis: 笔的列表
    :param start_dt: 子区间开始时间
    :param end_dt: 子区间结束时间
    :param direction: 方向
    :return: 子区间
    """
    start_dt = pd.to_datetime(start_dt)
    end_dt = pd.to_datetime(end_dt)
    sub = []
    for bi in bis:
        if bi.fx_b.dt > start_dt > bi.fx_a.dt:
            sub.append(bi)
        elif start_dt <= bi.fx_a.dt < bi.fx_b.dt <= end_dt:
            sub.append(bi)
        elif bi.fx_a.dt < end_dt < bi.fx_b.dt:
            sub.append(bi)
        else:
            continue

    if len(sub) > 0 and sub[0].direction != direction:
        sub = sub[1:]
    if len(sub) > 0 and sub[-1].direction != direction:
        sub = sub[:-1]
    return sub


def get_sub_bis(bi: BI, sub_bis: List[BI]) -> List[BI]:
    """获取大级别笔对象对应的小级别笔走势

    :param bi: 大级别笔对象
    :param sub_bis: 小级别笔列表
    :return:
    """
    sub_ = get_sub_span(sub_bis, start_dt=bi.fx_a.dt, end_dt=bi.fx_b.dt, direction=bi.direction)
    if not sub_:
        return []
    return sub_


def down_cross_count(x1: Union[List, np.array], x2: Union[List, np.array]) -> int:
    """输入两个序列，计算 x1 下穿 x2 的次数

    :param x1: list
    :param x2: list
    :return: int

    example:
    ========
    >>> x1 = [1, 1, 3, 4, 5, 12, 9, 8]
    >>> x2 = [2, 2, 1, 5, 8, 9, 10, 10]
    >>> print("x1 下穿 x2 的次数：{}".format(down_cross_count(x1, x2)))
    >>> print("x1 上穿 x2 的次数：{}".format(down_cross_count(x2, x1)))
    """
    x = np.array(x1) < np.array(x2)
    num = 0
    for i in range(len(x) - 1):
        b1, b2 = x[i], x[i + 1]
        if b2 and b1 != b2:
            num += 1
    return num


def kdj_gold_cross(kline: Union[List[RawBar], pd.DataFrame], just: bool = True) -> bool:
    """输入K线，判断KDJ是否金叉

    :param kline: pd.DataFrame
    :param just: bool
        是否是刚刚形成
    :return: bool
    """
    try:
        if isinstance(kline, list):
            close = [x.close for x in kline]
            high = [x.high for x in kline]
            low = [x.low for x in kline]
        else:
            close = kline.close.values
            high = kline.high.values
            low = kline.low.values

        k, d, j = KDJ(close=close, high=high, low=low)

        if d[-1] > 30:
            return False

        if not just and j[-1] > k[-1] > d[-1]:
            return True
        elif just and j[-1] > k[-1] > d[-1] and not (j[-2] > k[-2] > d[-2]):
            return True
        else:
            return False
    except:
        traceback.print_exc()
        return False


def kdj_dead_cross(kline: Union[List[RawBar], pd.DataFrame], just: bool = True) -> bool:
    """输入K线，判断KDJ是否死叉

    :param kline: pd.DataFrame
    :param just: bool
        是否是刚刚形成
    :return: bool
    """
    try:
        if isinstance(kline, list):
            close = [x.close for x in kline]
            high = [x.high for x in kline]
            low = [x.low for x in kline]
        else:
            close = kline.close.values
            high = kline.high.values
            low = kline.low.values

        k, d, j = KDJ(close=close, high=high, low=low)

        if d[-1] < 70:
            return False

        if not just and j[-1] < k[-1] < d[-1]:
            return True
        elif just and j[-1] < k[-1] < d[-1] and not (j[-2] < k[-2] < d[-2]):
            return True
        else:
            return False
    except:
        traceback.print_exc()
        return False
