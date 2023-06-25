import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_range_oscillation_V230620(c: CZSC, **kwargs) -> OrderedDict:
    """判断区间震荡

    参数模板："{freq}_D{di}TH{th}_区间震荡V230620"

    **信号逻辑：**

    1. 在区间震荡中，无论振幅大小，各笔的中心应改在相近的价格区间内平移，当各笔的中心的振幅大于一定数值时就认为这个窗口内没有固定区间的中枢震荡
    2. 给定阈值 th，当各笔的中心的振幅大于 th 时，认为这个窗口内没有固定区间的中枢震荡

    **信号列表：**

    - Signal('日线_D1TH5_区间震荡V230620_2笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_3笔震荡_向上_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_4笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_5笔震荡_向上_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_6笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_5笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_2笔震荡_向上_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_3笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_4笔震荡_向上_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
        - th: 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 2))  # 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}TH{th}_区间震荡V230620".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bi_list) < di + 11:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    def __calculate_max_amplitude_percentage(prices):
        """计算给定价位列表的最大振幅的百分比"""
        if not prices:
            return 100
        max_price, min_price = max(prices), min(prices)
        return ((max_price - min_price) / min_price) * 100 if min_price != 0 else 100

    _bis = get_sub_elements(c.bi_list, di=di, n=12)

    if len(_bis) != 12:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    price_list = []
    count = 1
    for bi in _bis[::-1]:
        price_list.append((bi.high + bi.low) / 2)
        if len(price_list) > 1:
            if __calculate_max_amplitude_percentage(price_list) < th:
                count += 1
            else:
                break

    if count != 1:
        v1 = f"{count}笔震荡"
        v2 = "向上" if _bis[-1].direction == Direction.Up else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[0]
    # for symbol in symbols[:10]:
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': cxt_range_oscillation_V230620, 'freq': '日线', 'di': 1, 'th': 5}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
