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
from deprecated import deprecated
from datetime import datetime
from typing import List, Union
from collections import Counter

from ..utils.ta import KDJ
from ..objects import RawBar, BI, Direction, ZS


@deprecated
def check_pressure_support(bars: List[RawBar], q_seq: List[float] = None):
    """检查 bars 中的支撑、压力信息

    1. 通过 round 函数对 K 线价格序列进行近似，统计价格出现次数，取出现次数超过5次的价位
    2. 在出现次数最多的价格序列上计算分位数序列作为关键价格序列

    :param bars: K线序列，按时间升序
    :param q_seq: 分位数序列
    :return:
    """

    assert len(bars) >= 500, "分析至少需要500根K线"
    min_low = min(x.low for x in bars)
    price_seq = [y for x in bars for y in (x.open, x.close, x.high, x.low)]
    price_seq = [round(x, 0) if min_low > 100 else round(x, 1) for x in price_seq]

    lines = sorted([x for x, v in Counter(price_seq).most_common() if v >= 5])
    q_seq = q_seq if q_seq else [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
    key_price = [np.quantile(lines, i, method='nearest') for i in q_seq]
    kp_low = [x for x in key_price if x <= bars[-1].close]
    kp_high = [x for x in key_price if x >= bars[-1].close]

    info = {
        "关键位": key_price,
        "支撑位": kp_low,
        "压力位": kp_high,
        "第一支撑": kp_low[-1] if len(kp_low) >= 1 else -1,
        "第二支撑": kp_low[-2] if len(kp_low) >= 2 else -1,
        "第一压力": kp_high[0] if len(kp_high) >= 1 else -1,
        "第二压力": kp_high[1] if len(kp_high) >= 2 else -1,
    }
    return info


@deprecated
def check_gap_info(bars: List[RawBar]):
    """检查 bars 中的缺口信息

    :param bars: K线序列，按时间升序
    :return:
    """
    gap_info = []
    if len(bars) < 2:
        return gap_info

    for i in range(1, len(bars)):
        bar1, bar2 = bars[i-1], bars[i]
        right = bars[i:]

        gap = None
        if bar1.high < bar2.low:
            delta = round(bar2.low / bar1.high - 1, 4)
            cover = "已补" if min(x.low for x in right) < bar1.high else "未补"
            gap = {"kind": "向上缺口", 'cover': cover, 'sdt': bar1.dt, 'edt': bar2.dt,
                   'high': bar2.low, 'low': bar1.high, 'delta': delta}

        if bar1.low > bar2.high:
            delta = round(bar1.low / bar2.high - 1, 4)
            cover = "已补" if max(x.high for x in right) > bar1.low else "未补"
            gap = {"kind": "向下缺口", 'cover': cover, 'sdt': bar1.dt, 'edt': bar2.dt,
                   'high': bar1.low, 'low': bar2.high, 'delta': delta}

        if gap:
            gap_info.append(gap)

    return gap_info


def check_cross_info(fast: [List, np.array], slow: [List, np.array]):
    """计算 fast 和 slow 的交叉信息

    :param fast: 快线
    :param slow: 慢线
    :return:
    """
    assert len(fast) == len(slow), "快线和慢线的长度不一样"

    if isinstance(fast, list):
        fast = np.array(fast)
    if isinstance(slow, list):
        slow = np.array(slow)

    length = len(fast)
    delta = fast - slow
    cross_info = []
    last_i = -1
    last_v = 0
    temp_fast = []
    temp_slow = []
    for i, v in enumerate(delta):
        last_i += 1
        last_v += abs(v)
        temp_fast.append(fast[i])
        temp_slow.append(slow[i])

        if i >= 2 and delta[i-1] <= 0 < delta[i]:
            kind = "金叉"
        elif i >= 2 and delta[i-1] >= 0 > delta[i]:
            kind = "死叉"
        else:
            continue

        cross_info.append({'位置': i, "类型": kind, "快线": fast[i], "慢线": slow[i],
                           "距离": last_i, '距今': length - i,
                           "面积": round(last_v, 4), '价差': round(v, 4),
                           "快线高点": max(temp_fast), "快线低点": min(temp_fast),
                           "慢线高点": max(temp_slow), "慢线低点": min(temp_slow),
                           })
        last_i = 0
        last_v = 0
        temp_fast = []
        temp_slow = []

    return cross_info


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


def is_bis_down(bis: List[BI]) -> bool:
    """判断 bis 中的连续笔是否是向下的"""
    if not bis or len(bis) < 3 or len(bis) % 2 == 0:
        return False

    assert bis[1].fx_b.dt > bis[0].fx_b.dt, "时间由远到近"

    if bis[-1].direction == Direction.Down \
            and bis[0].high == max([x.high for x in bis]) \
            and bis[-1].low == min([x.low for x in bis]):
        return True
    else:
        return False


def is_bis_up(bis: List[BI]) -> bool:
    """判断 bis 中的连续笔是否是向上的"""
    if not bis or len(bis) < 3 and len(bis) % 2 == 0:
        return False

    assert bis[1].fx_b.dt > bis[0].fx_b.dt, "时间由远到近"

    if bis[-1].direction == Direction.Up \
            and bis[-1].high == max([x.high for x in bis]) \
            and bis[0].low == min([x.low for x in bis]):
        return True
    else:
        return False


def get_zs_seq(bis: List[BI]) -> List[ZS]:
    """获取连续笔中的中枢序列

    :param bis: 连续笔对象列表
    :return: 中枢序列
    """
    zs_list = []
    if not bis:
        return []

    for bi in bis:
        if not zs_list:
            zs_list.append(ZS(symbol=bi.symbol, bis=[bi]))
            continue

        zs = zs_list[-1]
        if not zs.bis:
            zs.bis.append(bi)
            zs_list[-1] = zs
        else:
            if (bi.direction == Direction.Up and bi.high < zs.zd) \
                    or (bi.direction == Direction.Down and bi.low > zs.zg):
                zs_list.append(ZS(symbol=bi.symbol, bis=[bi]))
            else:
                zs.bis.append(bi)
                zs_list[-1] = zs
    return zs_list




