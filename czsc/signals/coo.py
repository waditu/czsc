# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/10 23:14
describe: coo 是 cooperation 的缩写，作为前缀代表信号开源协作成员贡献的信号
"""
import numpy as np
from deprecated import deprecated
from collections import OrderedDict
from czsc import CZSC, Signal
from czsc.utils import create_single_signal, get_sub_elements


# 在这里可以定义自己的信号函数
# ----------------------------------------------------------------------------------------------------------------------

def __cal_td_seq(close: np.ndarray):
    """TDSEQ计算辅助函数

    正值表示上涨，负值表示下跌

    :param close: np.array
        收盘价序列
    :return: np.array
    """
    if len(close) < 5:
        return np.zeros(len(close), dtype=np.int32)

    res = np.zeros(len(close), dtype=np.int32)
    for i in range(4, len(close)):
        if close[i] > close[i - 4]:
            res[i] = res[i - 1] + 1
        elif close[i] < close[i - 4]:
            res[i] = res[i - 1] - 1

    return res


@deprecated(version='1.0.0', reason="请使用 coo_td_V221111")
def coo_td_V221110(c: CZSC, **kwargs) -> OrderedDict:
    """获取倒数第i根K线的TD信号

    参数模板："{freq}_D{di}K_TD"

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
    di = int(kwargs.get("di", 1))
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

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)



def coo_td_V221111(c: CZSC, **kwargs) -> OrderedDict:
    """获取倒数第i根K线的TD信号

    参数模板："{freq}_D{di}TD_BS辅助V221111"

    **信号逻辑：**

    神奇九转指标

    **信号列表：**

    - Signal('15分钟_D1TD_BS辅助V221111_延续_TD底_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_看多_非顶_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_延续_非顶_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_延续_非底_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_延续_TD顶_任意_0')
    - Signal('15分钟_D1TD_BS辅助V221111_看空_非底_任意_0')

    :param c: CZSC对象
    :param di: 倒数第di根K线
    :return: s
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}TD_BS辅助V221111".split("_")
    if len(c.bars_raw) < 50 + di:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")
    
    bars = get_sub_elements(c.bars_raw, di=di, n=50)
    close = np.array([x.close for x in bars])
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

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
