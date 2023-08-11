from collections import OrderedDict
import pandas as pd
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def vol_window_V230801(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内成交量的特征

    参数模板："{freq}_D{di}W{w}_窗口能量V230801"

    **信号逻辑：**

    观察一个固定窗口内的成交量特征，本信号以窗口内的最大成交量与最小成交量的先后顺序作为窗口成交量的特征。

    **信号列表：**

    - Signal('60分钟_D1W5_窗口能量V230801_先缩后放_任意_任意_0')
    - Signal('60分钟_D1W5_窗口能量V230801_先放后缩_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    
        - :param di: 信号计算截止倒数第i根K线
        - :param w: 观察的窗口大小。
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 5))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}_窗口能量V230801".split('_')
    if len(c.bars_raw) < di + w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    vols = [x.vol for x in get_sub_elements(c.bars_raw, di=di, n=w)]
    min_i, max_i = vols.index(min(vols)), vols.index(max(vols))
    v1 = "先放后缩" if min_i > max_i else "先缩后放"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20191101', '20210101', fq='前复权')

    signals_config = [
        {'name': vol_window_V230801, 'freq': '60分钟', 'window': 10},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()