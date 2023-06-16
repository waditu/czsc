from collections import OrderedDict
import numpy as np
import pandas as pd
from loguru import logger
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def cmo_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """CMO能量异动，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}M{m}_CMO能量V230605"

    信号逻辑：**

    CMO指标用过去N天的价格上涨量和价格下跌量得到，CMO>(<)0 表示当前处于上涨（下跌）趋势，CMO 越
    大（小）则当前上涨（下跌）趋势越强。我们用 CMO 上穿 30/下穿-30来产生买入/卖出信号。

    信号列表：

    - Signal('30分钟_D1N70M30_CMO能量V230605_看空_任意_任意_0')
    - Signal('30分钟_D1N70M30_CMO能量V230605_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为60
        - :param m: 信号预警轴，默认为30
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 70))
    m = int(kwargs.get("m", 30))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}M{m}_CMO能量V230605".split('_')

    v1 = "其他"
    if len(c.bars_raw) < di + n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)  
    up_sum = np.sum([_bars[i].close - _bars[i - 1].close for i in range(1, len(_bars))
                     if (_bars[i].close - _bars[i - 1].close) > 0])
    dw_sum = np.sum([_bars[i - 1].close - _bars[i].close for i in range(1, len(_bars))
                     if (_bars[i - 1].close - _bars[i].close) > 0])

    cmo = (up_sum - dw_sum) / (up_sum + dw_sum) * 100
    if cmo > m:
        v1 = "看多"
    if cmo < -m:
        v1 = "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': cmo_up_dw_line_V230605, 'freq': '30分钟', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
