import talib as ta
import numpy as np
from czsc import CZSC
from datetime import datetime
from collections import OrderedDict
from czsc.utils.bar_generator import freq_end_time
from czsc.utils import create_single_signal, get_sub_elements


def bar_end_V221211(c: CZSC, freq1='60分钟', **kwargs) -> OrderedDict:
    """判断分钟 K 线是否结束

    参数模板："{freq}_{freq1}结束_BS辅助221211"

    **信号列表：**

    - Signal('60分钟_K线_结束_否_任意_任意_0')
    - Signal('60分钟_K线_结束_是_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param freq1: 分钟周期名称
    :return: s
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_{freq1}结束_BS辅助221211".split('_')
    assert "分钟" in freq1

    dt: datetime = c.bars_raw[-1].dt
    v = "是" if freq_end_time(dt, freq1) == dt else "否"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': bar_end_V221211, 'freq': '15分钟', 'freq1': '60分钟'}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=0)


if __name__ == '__main__':
    check()
