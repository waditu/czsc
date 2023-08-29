import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.objects import Mark
from czsc.utils import create_single_signal, get_sub_elements


def cxt_bi_stop_V230815(c: CZSC, **kwargs) -> OrderedDict:
    """定位笔的止损距离大小

    参数模板："{freq}_距离{th}BP_止损V230815"

    **信号逻辑：**

    以向上笔为例：如果当前K线的收盘价高于该笔的最高价的1 - 0.5%，则认为在止损阈值内，否则认为在止损阈值外。

    **信号列表：**

    - Signal('15分钟_距离50BP_止损V230815_向下_阈值外_任意_0')
    - Signal('15分钟_距离50BP_止损V230815_向上_阈值内_任意_0')
    - Signal('15分钟_距离50BP_止损V230815_向下_阈值内_任意_0')
    - Signal('15分钟_距离50BP_止损V230815_向上_阈值外_任意_0')

    :param c: CZSC对象
    :param kwargs: 

        - th: 止损距离阈值，单位为BP, 默认为50BP, 即0.5%

    :return: 信号识别结果
    """
    th = int(kwargs.get('th', 50))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_距离{th}BP_止损V230815".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bi_list) < 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    bi, last_bar = c.bi_list[-1], c.bars_ubi[-1]
    if bi.direction == Direction.Up:
        v1 = '向下'
        v2 = "阈值内" if last_bar.close > bi.high * (1 - th / 10000) else "阈值外"
    if bi.direction == Direction.Down:
        v1 = '向上'
        v2 = "阈值内" if last_bar.close < bi.low * (1 + th / 10000) else "阈值外"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_bi_stop_V230815, 'freq': '15分钟'}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
