from collections import OrderedDict
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def ntmdk_V230824(c: CZSC, **kwargs) -> OrderedDict:
    """NTMDK多空指标，贡献者：琅盎  

    参数模板："freq}_D{di}M{m}_NTMDK多空V230824"

    **信号逻辑：**

    此信号函数的逻辑非常简单，流传于股市中有一句话：日日新高日日持股，
    那么此信号函数利用的是收盘价和M日前的收盘价进行比较，如果差值为正
    即多头成立，反之空头成立。

    **信号列表：**

    - Signal('日线_D1M10_NTMDK多空V230824_看空_任意_任意_0')
    - Signal('日线_D1M10_NTMDK多空V230824_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        - :param di: 信号计算截止倒数第i根K线
        - :param m: m天前的价格

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    m = int(kwargs.get("m", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}M{m}_NTMDK多空V230824".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + m + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    bars = get_sub_elements(c.bars_raw, di=di, n=m)
    v1 = "看多" if bars[-1].close > bars[0].close else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20171101', '20210101', fq='前复权')

    signals_config = [
        {'name': ntmdk_V230824, 'freq': '日线', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config)


if __name__ == '__main__':
    main()