from collections import OrderedDict
import numpy as np
import pandas as pd
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def clv_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """CLV多空分类，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}_CLV多空V230605"

    **信号逻辑：**

    CLV 用来衡量收盘价在最低价和最高价之间的位置。
    当CLOSE=HIGH 时，CLV=1; 当 CLOSE=LOW 时，CLV=-1;当 CLOSE位于 HIGH 和 LOW 的中点时，
    CLV=0。CLV>0（<0），说明收盘价离最高（低）价更近。我们用 CLVMA 上穿/下穿 0 来产生买入/卖出信号

    **信号列表：**
    
    - Signal('日线_D1N70_CLV多空V230605_看多_任意_任意_0')
    - Signal('日线_D1N70_CLV多空V230605_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为60
        - :param m: 收盘价倍数，默认为2
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 70))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}_CLV多空V230605".split('_')

    if len(c.bars_raw) < di + 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)  

    close = np.array([bar.close for bar in _bars])
    low = np.array([bar.low for bar in _bars])
    high = np.array([bar.high for bar in _bars])
    clv_ma = np.mean((2 * close - low - high) / (high - low))

    v1 = "看多" if clv_ma > 0 else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': clv_up_dw_line_V230605, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
