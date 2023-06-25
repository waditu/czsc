from collections import OrderedDict
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def adtm_up_dw_line_V230603(c: CZSC, **kwargs) -> OrderedDict:
    """ADTM能量异动，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}TH{th}_ADTMV230603"

    **信号逻辑：**

    1. 如果今天的开盘价大于昨天的开盘价，取最高价 - 开盘价、开盘价 - 昨天的开盘价这二者中最大值,
        再将取出的最大值求和；反之取0，形成up_sum
    2. 如果今天的开盘价小于昨天的开盘价，取开盘价 - 最低价、昨天的开盘价 -开盘价这二者中最大值,
        再将取出的最大值求和；么之取0，形成dw_sum
    3. 当 up_sum > dw_sum 或 最大值的差值之商小于TH 看多，反之看空


    **信号列表：**

    - Signal('日线_D1N30M20TH5_ADTMV230603_看空_任意_任意_0')
    - Signal('日线_D1N30M20TH5_ADTMV230603_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为30
        - :param m: 获取K线的根数，默认为20
        - :param th: adtm阈值，默认为5，代表 5 / 10 = 0.5
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 30))
    m = int(kwargs.get("m", 20))
    th = int(kwargs.get("th", 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}TH{th}_ADTMV230603".split('_')

    v1 = "其他"
    if len(c.bars_raw) < di + 30:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    n_bars = get_sub_elements(c.bars_raw, di=di, n=n)  
    m_bars = get_sub_elements(c.bars_raw, di=di, n=m)

    up_sum = np.sum([max(n_bars[i].high - n_bars[i].open, n_bars[i].open - n_bars[i - 1].open)
                     for i in range(1, len(n_bars)) if n_bars[i].open > n_bars[i - 1].open])
    dw_sum = np.sum([max(m_bars[i].open - m_bars[i].low, m_bars[i - 1].open - m_bars[i].open)
                     for i in range(1, len(m_bars)) if m_bars[i].open < m_bars[i - 1].open])

    adtm = (up_sum - dw_sum) / max(up_sum, dw_sum)
    if up_sum > dw_sum or adtm > th / 10:
        v1 = "看多"
    if up_sum < dw_sum or adtm < th / 10:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': adtm_up_dw_line_V230603, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
