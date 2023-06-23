# -*- coding: utf-8 -*-
# @Time    : 2023/6/18 16:11
# @Author  : 琅盎
# @FileName: BIAS_V1.py
# @Software: PyCharm
from collections import OrderedDict
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def bias_up_dw_line_V230618(c: CZSC, **kwargs) -> OrderedDict:
    """BIAS乖离率指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}P{p}TH1{th1}TH2{th2}TH3{th3}_BIAS乖离率V230618"

    **信号逻辑：**

    乖离率 BIAS 用来衡量收盘价与移动平均线之间的差距。
    当 BIAS6 大于 3 且 BIAS12 大于 5 且 BIAS24 大于 8，
    三个乖离率均进入股价强势上涨区间，产生买入信号；
    当 BIAS6 小于-3 且 BIAS12 小于-5 且BIAS24 小于-8 时，
    三种乖离率均进入股价强势下跌区间，产生卖出信号

    **信号列表：**

    - Signal('日线_D1N6M12P24TH11TH23TH35_BIAS乖离率V230618_看空_任意_任意_0')
    - Signal('日线_D1N6M12P24TH11TH23TH35_BIAS乖离率V230618_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param m: 获取K线的根数，默认为20
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 6))
    m = int(kwargs.get("m", 12))
    p = int(kwargs.get("p", 24))
    th1 = int(kwargs.get("th1", 1))
    th2 = int(kwargs.get("th2", 3))
    th3 = int(kwargs.get("th3", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}P{p}TH1{th1}TH2{th2}TH3{th3}_BIAS乖离率V230618".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + max(n, m, p):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars1 = get_sub_elements(c.bars_raw, di=di, n=n)
    bars2 = get_sub_elements(c.bars_raw, di=di, n=m)
    bars3 = get_sub_elements(c.bars_raw, di=di, n=p)

    bias_ma1 = np.mean([bars1[i].close for i in range(len(bars1))])
    bias_ma2 = np.mean([bars2[i].close for i in range(len(bars2))])
    bias_ma3 = np.mean([bars3[i].close for i in range(len(bars3))])

    bias1 = (bars1[-1].close - bias_ma1) / bias_ma1 * 100
    bias2 = (bars2[-1].close - bias_ma2) / bias_ma2 * 100
    bias3 = (bars3[-1].close - bias_ma3) / bias_ma3 * 100

    if bias1 > th1 and bias2 > th2 and bias3 > th3:
        v1 = "看多"
    if bias1 < -th1 and bias2 < -th2 and bias3 < -th3:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': bias_up_dw_line_V230618, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config)

if __name__ == '__main__':
    main()