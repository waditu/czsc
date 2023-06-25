from collections import OrderedDict
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def amv_up_dw_line_V230603(c: CZSC, **kwargs) -> OrderedDict:
    """AMV能量异动，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}_AMV能量V230603"

    **信号逻辑：**

    用成交量作为权重对开盘价和收盘价的均值进行加权移动平均。成交量越大的价格对移动平均结果的影响越大，
    AMV 指标减小了成交量小的价格波动的影响。当短期 AMV 线上穿/下穿长期 AMV线时，产生买入/卖出信号。


    **信号列表：**

    - Signal('日线_D1N30M120_AMV能量V230603_看多_任意_任意_0')
    - Signal('日线_D1N30M120_AMV能量V230603_看空_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param m: 获取K线的根数，默认为20
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    m = int(kwargs.get("m", 120))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}_AMV能量V230603".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + 120:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    n_bars = get_sub_elements(c.bars_raw, di=di, n=n)  
    m_bars = get_sub_elements(c.bars_raw, di=di, n=m)

    amov1 = np.sum([(n_bars[i].amount * (n_bars[i].open + n_bars[i].close) / 2) for i in range(len(n_bars))])
    amov2 = np.sum([(m_bars[i].amount * (m_bars[i].open + m_bars[i].close) / 2) for i in range(len(m_bars))])
    vol_sum1 = np.sum([n_bars[i].amount for i in range(len(n_bars))])
    vol_sum2 = np.sum([m_bars[i].amount for i in range(len(m_bars))])
    amv1 = amov1 / vol_sum1
    amv2 = amov2 / vol_sum2

    v1 = "看多" if amv1 > amv2 else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': amv_up_dw_line_V230603, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
