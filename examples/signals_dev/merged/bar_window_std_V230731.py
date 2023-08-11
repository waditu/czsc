from collections import OrderedDict
import pandas as pd
import numpy as np
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def bar_window_std_V230731(c: CZSC, **kwargs) -> OrderedDict:
    """指定窗口内波动率的特征

    参数模板："{freq}_D{di}W{window}M{m}N{n}_窗口波动V230731"

    **信号逻辑：**

    滚动计算最近m根K线的波动率，分成n层，最大值为n，最小值为1；
    最近window根K线的最大值为max_layer，最小值为min_layer。
    以这两个值作为窗口内的波动率特征。

    **信号列表：**

    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N7_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N6_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N8_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N9_低波N6_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N9_低波N9_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N9_低波N8_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N8_低波N8_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N8_低波N7_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N7_低波N7_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N7_低波N5_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N6_低波N5_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N5_低波N4_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N5_低波N3_任意_0')
    - Signal('60分钟_D2W3M100N10_窗口波动V230731_高波N4_低波N3_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
    
        - :param di: 信号计算截止倒数第i根K线
        - :param w: 观察的窗口大小。
        - :param m: 计算分位数所需取K线的数量。
        - :param n: 分层的数量。

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    w = int(kwargs.get("w", 5))
    m = int(kwargs.get("m", 100))
    n = int(kwargs.get("n", 10))

    # 更新STD20波动率缓存
    cache_key = "STD20"
    for i, bar in enumerate(c.bars_raw):
        if cache_key in bar.cache:
            continue
        bar.cache[cache_key] = 0 if i < 5 else np.std([x.close for x in c.bars_raw[max(i-20, 0):i]])

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}W{w}M{m}N{n}_窗口波动V230731".split('_')
    v1 = "其他"

    if len(c.bars_raw) < di + m + w:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    stds = [x.cache[cache_key] for x in get_sub_elements(c.bars_raw, di=di, n=m)]
    layer = pd.qcut(stds, n, labels=False, duplicates='drop')
    max_layer = max(layer[-w:]) + 1
    min_layer = min(layer[-w:]) + 1

    v1, v2 = f"高波N{max_layer}", f"低波N{min_layer}"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20191101', '20210101', fq='前复权')

    signals_config = [
        {'name': bar_window_std_V230731, 'freq': '60分钟', 'di': 2, 'm': 200, 'window': 10},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
