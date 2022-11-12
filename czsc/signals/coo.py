# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/10 23:14
describe: coo 是 cooperation 的缩写，作为前缀代表信号开源协作成员贡献的信号
"""
import numpy as np
from collections import OrderedDict
from czsc import CZSC, Signal


# 在这里可以定义自己的信号函数
# ----------------------------------------------------------------------------------------------------------------------

def __cal_td_seq(close: np.array):
    """TDSEQ计算辅助函数

    正值表示上涨，负值表示下跌

    :param close: np.array
        收盘价序列
    :return: np.array
    """
    up = np.zeros(len(close))
    dn = np.zeros(len(close))
    u = 0
    d = 0
    if len(close) < 5:
        return up

    for i in range(4, len(close)):
        if close[i] > close[i-4]:
            u += 1
            d = 0
        elif close[i] < close[i-4]:
            u = 0
            d -= 1
        else:
            u = 0
            d = 0
        up[i] = u
        dn[i] = d

    res = up+dn
    return np.array(res, dtype=np.int32)


def coo_td_V221110(c: CZSC, di: int = 1) -> OrderedDict:
    """获取倒数第i根K线的TD信号

    **信号列表：**

    - Signal('60分钟_D2K_TD_延续_非底_任意_0')
    - Signal('60分钟_D2K_TD_延续_非顶_任意_0')
    - Signal('60分钟_D2K_TD_延续_TD顶_任意_0')
    - Signal('60分钟_D2K_TD_看空_非底_任意_0')
    - Signal('60分钟_D2K_TD_延续_TD底_任意_0')
    - Signal('60分钟_D2K_TD_看多_非顶_任意_0')

    :param c: CZSC对象
    :param di: 倒数第di根K线
    :return: s
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_TD".split("_")

    if di == 1:
        close = np.array([x.close for x in c.bars_raw[-50:]])
    else:
        close = np.array([x.close for x in c.bars_raw[-50 - di + 1:-di + 1]])

    td = __cal_td_seq(close)
    if td[-1] > 0:
        v1 = '看多' if len(td) > 1 and td[-2] < -8 else '延续'
        v2 = 'TD顶' if td[-1] > 8 else '非顶'
    elif td[-1] < 0:
        v1 = '看空' if len(td) > 1 and td[-2] > 8 else '延续'
        v2 = 'TD底' if td[-1] < -8 else '非底'
    else:
        v1 = '其他'
        v2 = '其他'

    s = OrderedDict()
    sig = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[sig.key] = sig.value
    return s



