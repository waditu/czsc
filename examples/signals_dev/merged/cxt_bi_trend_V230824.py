import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')

import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_bi_trend_V230824(c: CZSC, **kwargs) -> OrderedDict:
    """判断N笔形态

    参数模板："{freq}_D{di}N{n}TH{th}_形态V230824"

    **信号逻辑：**

    1. 通过对最近N笔的中心点的均值和-n笔的中心点的位置关系来判断当前N比是上涨形态还是下跌，横盘震荡形态
    2. 给定阈值 th，判断上涨下跌横盘按照 所有笔中心点/第-n笔中心点 与 正负th区间的相对位置来判断。
    3. 当在区间上时为上涨，区间内为横盘，区间下为下跌

    **信号列表：**

    - Signal('日线_D1N4TH5_形态V230824_横盘_任意_任意_0')
    - Signal('日线_D1N4TH5_形态V230824_向上_任意_任意_0')
    - Signal('日线_D1N4TH5_形态V230824_向下_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
        - n ：检查范围
        - th: 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 4))
    th = int(kwargs.get('th', 2))  # 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}TH{th}_形态V230824".split('_')
    v1 = '其他'
    if len(c.bi_list) < di + n + 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bis = get_sub_elements(c.bi_list, di=di, n=n)
    assert len(_bis) == n, f"获取第 {di} 笔到第 {di+n} 笔失败"

    all_means = [(bi.low + bi.high) / 2 for bi in _bis]
    average_of_means = sum(all_means) / n
    ratio = all_means[0] / average_of_means

    if ratio * 100 > 100 + th:
        v1 = "向下"
    elif ratio * 100 < 100 - th:
        v1 = "向上"
    else:
        v1 = "横盘"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[0]
    # for symbol in symbols[:10]:
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': cxt_bi_trend_V230824, 'freq': '日线', 'di': 1, 'n': 6, 'th': 5}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
