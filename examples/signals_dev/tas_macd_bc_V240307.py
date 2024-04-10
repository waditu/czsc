import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Direction, ZS
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal, get_sub_elements


def tas_macd_bc_V240307(c: CZSC, **kwargs) -> OrderedDict:
    """MACD柱子辅助背驰判断

    参数模板："{freq}_D{di}N{n}柱子背驰_BS辅助V240307"

    **信号逻辑：**

    以顶背驰为例，最近N根K线的MACD柱子都大于0，且最近一个柱子高点小于前面的柱子高点，认为是顶背驰，做空；反之，做多。

    **信号列表：**

    - Signal('60分钟_D1N20柱子背驰_BS辅助V240307_底背驰_第1次_任意_0')
    - Signal('60分钟_D1N20柱子背驰_BS辅助V240307_底背驰_第2次_任意_0')
    - Signal('60分钟_D1N20柱子背驰_BS辅助V240307_底背驰_第3次_任意_0')
    - Signal('60分钟_D1N20柱子背驰_BS辅助V240307_顶背驰_第1次_任意_0')
    - Signal('60分钟_D1N20柱子背驰_BS辅助V240307_顶背驰_第2次_任意_0')
    - Signal('60分钟_D1N20柱子背驰_BS辅助V240307_顶背驰_第3次_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 20))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}柱子背驰_BS辅助V240307".split('_')
    v1, v2 = '其他', '其他'
    cache_key = update_macd_cache(c)
    if len(c.bars_raw) < 7 + n:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=n)
    macd = [x.cache[cache_key]['macd'] for x in bars]
    n = len(macd)

    # 计算 MACD 柱子的顶和底序列
    gs = [i for i in range(1, n - 1) if macd[i - 1] < macd[i] > macd[i + 1] and macd[i] > 0]
    ds = [i for i in range(1, n - 1) if macd[i - 1] > macd[i] < macd[i + 1] and macd[i] < 0]

    if macd[-1] > 0 and len(gs) >= 2 and macd[gs[-1]] < macd[gs[-2]] and gs[-1] - gs[-2] > 2:
        macd_sub = macd[gs[-2]:]
        # 两个顶之间的柱子没有出现大的负值
        if abs(np.sum([x for x in macd_sub if x < 0])) < np.std(np.abs(macd_sub)):
            v1 = '顶背驰'
            v2 = f"第{n - gs[-1] - 1}次"

    if macd[-1] < 0 and len(ds) >= 2 and macd[ds[-1]] > macd[ds[-2]] and ds[-1] - ds[-2] > 2:
        macd_sub = macd[ds[-2]:]
        # 两个底之间的柱子没有出现大的正值
        if abs(np.sum([x for x in macd_sub if x > 0])) < np.std(np.abs(macd_sub)):
            v1 = '底背驰'
            v2 = f"第{n - ds[-1] - 1}次"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_macd_bc_V240307, 'freq': "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore


if __name__ == '__main__':
    check()
