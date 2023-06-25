from collections import OrderedDict
import numpy as np
import pandas as pd
from loguru import logger
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def emv_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """能量异动，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}_V230605emv"

    **信号逻辑：**

    emv 综合考虑了成交量和价格（中间价）的变化。
    emv>0 则多头处于优势，emv 上升说明买方力量在增大；
    emv<0 则空头处于优势，emv 下降说明卖方力量在增大。
    如果 emv 上穿 0，则产生买入信号；
    如果 emv 下穿 0，则产生卖出信号。

    **信号列表：**

    - Signal('30分钟_D1_EMV多空V230605_看空_任意_任意_0')
    - Signal('30分钟_D1_EMV多空V230605_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为105

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}_EMV多空V230605".split('_')

    if len(c.bars_raw) < di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    _bars = get_sub_elements(c.bars_raw, di=di, n=2)
    mid_pt_move = (_bars[-1].high + _bars[-1].low) / 2 - (_bars[-2].high + _bars[-2].low) / 2
    # box_ratio = _bars[-1].vol / 1000000 / (_bars[-1].high - _bars[-1].low)
    # emv = mid_pt_move / box_ratio

    v1 = '看多' if mid_pt_move > 0 else '看空'
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': emv_up_dw_line_V230605, 'freq': '30分钟', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
