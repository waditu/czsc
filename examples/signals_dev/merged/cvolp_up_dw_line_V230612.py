from collections import OrderedDict
import numpy as np
import pandas as pd

from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def cvolp_up_dw_line_V230612(c: CZSC, **kwargs) -> OrderedDict:
    """CVOLP动量变化率指标，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}UP{up}DW{dw}_CVOLP动量变化率V230612"

    **信号逻辑：**

    成交量移动平均平滑变化率。
    先计算了成交量的N周期指数移动平均线，然后计算了EMAP的M周期前的值，最后计算了CVOLP的值。
    CVOLP 上穿 up 买入，下穿 dw 卖出。

    **信号列表：**

    - Signal('日线_D1N13M21UP5DW5_CVOLP动量变化率V230612_看多_任意_任意_0')
    - Signal('日线_D1N13M21UP5DW5_CVOLP动量变化率V230612_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 取K线数量
        - :param m: 信号预警值
        - :param up: 看多信号预警值
        - :param dw: 看空信号预警值
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 34))
    m = int(kwargs.get("m", 55))
    up = int(kwargs.get("up", 5))
    dw = int(kwargs.get("dw", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}UP{up}DW{dw}_CVOLP动量变化率V230612".split('_')

    # 增加一个约束，如果K线数量不足时直接返回
    v1 = "其他"
    if len(c.bars_raw) < di + n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n + m) 

    volume = np.array([bar.vol for bar in bars])
    n_weights = np.exp(np.linspace(-1., 0., n))
    n_weights /= n_weights.sum()
    emap = np.convolve(volume, n_weights, mode='full')[:len(volume)]
    emap[:n] = emap[n]
    sroc = (emap - np.roll(emap, m))[-1] / np.roll(emap, m)[-1] 

    if sroc > up / 100:
        v1 = "看多"
    if sroc < -dw / 100:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20171101', '20210101', fq='前复权')

    signals_config = [
        {'name': cvolp_up_dw_line_V230612, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config)


if __name__ == '__main__':
    main()