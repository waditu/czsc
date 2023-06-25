from collections import OrderedDict
import numpy as np
import pandas as pd
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal



def asi_up_dw_line_V230603(c: CZSC, **kwargs) -> OrderedDict:
    """ASI多空分类，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}P{p}_ASI多空V230603"

    **信号逻辑：**

    由于 SI 的波动性比较大，所以我们一般对 SI 累计求和得到 ASI 并捕
    捉 ASI 的变化趋势。一般我们不会直接看 ASI 的数值（对 SI 累计求
    和的求和起点不同会导致求出 ASI 的值不同），而是会观察 ASI 的变
    化方向。我们利用 ASI 与其均线的交叉来产生交易信号,上穿/下穿均
    线时买入/卖出

    **信号列表：**

    - Signal('日线_D1N30P120_ASI多空V230603_看多_任意_任意_0')
    - Signal('日线_D1N30P120_ASI多空V230603_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param p: 获取K线的根数，默认为20
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    p = int(kwargs.get("p", 120))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}P{p}_ASI多空V230603".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + p + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=p)  
    close_prices = np.array([bar.close for bar in _bars])
    open_prices = np.array([bar.open for bar in _bars])
    high_prices = np.array([bar.high for bar in _bars])
    low_prices = np.array([bar.low for bar in _bars])

    o = np.concatenate([[close_prices[0]], close_prices[:-1]])
    a = np.abs(high_prices - o)
    b = np.abs(low_prices - o)
    c = np.abs(high_prices - np.concatenate([[low_prices[0]], low_prices[:-1]])) # type: ignore
    d = np.abs(o - np.concatenate([[open_prices[0]], open_prices[:-1]]))

    k = np.maximum(a, b)  
    m = np.maximum(high_prices - low_prices, n)
    r1 = a + 0.5 * b + 0.25 * d
    r2 = b + 0.5 * a + 0.25 * d
    r3 = c + 0.25 * d
    r4 = np.where((a >= b) & (a >= c), r1, r2)
    r = np.where((c >= a) & (c >= b), r3, r4)
    
    if (r * k / m != 0).all():
        si = 50 * (close_prices - c + (c - open_prices) + 0.5 * (close_prices - open_prices)) / (r * k / m)
    else:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    asi = np.cumsum(si) 

    v1 = "看多" if asi[-1] > np.mean(asi[-p:]) else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': asi_up_dw_line_V230603, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
