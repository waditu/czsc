from collections import OrderedDict
import pandas as pd
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def vol_window_V230731(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内成交量的特征

    参数模板："{freq}_D{di}W{window}M{m}N{n}_窗口能量V230731"

    **信号逻辑：**

    取最近 m 根K线，计算每根K线的成交量，分成n层，最大值为n，最小值为1；
    最近 w 根K线的成交量分层最大值为max_vol_layer，最小值为min_vol_layer，
    以这两个值作为窗口内的成交量特征。

    **信号列表：**

    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N9_低量N4_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N9_低量N5_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N9_低量N2_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N9_低量N3_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N10_低量N4_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N8_低量N3_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N10_低量N3_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N10_低量N6_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N10_低量N7_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N10_低量N5_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N9_低量N6_任意_0')
    - Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N8_低量N2_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    
        - :param di: 信号计算截止倒数第i根K线
        - :param w: 观察的窗口大小。
        - :param n: 分层的数量。
        - :param m: 计算分位数所需取K线的数量。
        
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 5))
    m = int(kwargs.get("m", 30))
    n = int(kwargs.get("n", 10))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}M{m}N{n}_窗口能量V230731".split('_')
    v1 = "其他"

    if len(c.bars_raw) < di + m:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    vols = [x.vol for x in get_sub_elements(c.bars_raw, di=di, n=m)]
    vols_layer = pd.qcut(vols, n, labels=False, duplicates='drop')
    max_vol_layer = max(vols_layer[-w:]) + 1
    min_vol_layer = min(vols_layer[-w:]) + 1

    v1, v2 = f"高量N{max_vol_layer}", f"低量N{min_vol_layer}"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20191101', '20210101', fq='前复权')

    signals_config = [
        {'name': vol_window_V230731, 'freq': '60分钟', 'di': 2, 'm': 100, 'window': 3},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()