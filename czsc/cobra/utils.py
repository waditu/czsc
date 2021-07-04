# coding: utf-8

import numpy as np
import pandas as pd
import traceback
from typing import List, Union

from ..utils.ta import KDJ
from ..objects import RawBar


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


def drop_duplicates_by_window(seq: List[Union[str, int, float]],
                              default_value: [str, int, float] = None,
                              window_size: int = 5) -> List[Union[str, int, float]]:
    """从左到右按窗口进行去重，并使用 default_value 进行填充

    :param seq: 输入序列
    :param default_value: 重复位置的默认填充值
    :param window_size: 窗口大小
    :return: 去重后的序列
    """
    for i in range(len(seq)):
        if i < window_size:
            left = seq[: i]
        else:
            left = seq[i-window_size+1: i]

        if seq[i] in left:
            seq[i] = default_value
    return seq


