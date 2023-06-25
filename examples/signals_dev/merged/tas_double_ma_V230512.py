import talib as ta
import numpy as np
from czsc import CZSC
from czsc.utils import create_single_signal, get_sub_elements
from czsc.signals.tas import update_ma_cache


def tas_double_ma_V230511(c: CZSC, **kwargs):
    """双均线金叉死叉后的反向信号

    参数模板："{freq}_D{di}#{ma_type}#{t1}#{t2}_BS辅助V230511"

    **信号逻辑：**

    1. t1周期均线上穿t2周期均线，且当前K线为大实体阴线，看多信号；
    2. t1周期均线下穿t2周期均线，且当前K线为大实体阳线，看空信号；

    **信号列表：**

    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看空_任意_任意_0')
    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看多_第一个_任意_0')
    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看多_任意_任意_0')
    - Signal('日线_D2#SMA#5#20_BS辅助V230511_看空_第一个_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - t1: 均线1周期
        - t2: 均线2周期
        - ma_type: 均线类型，支持：MA, EMA, WMA, DEMA, TEMA, TRIMA, KAMA, MAMA, T3
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    t1 = int(kwargs.get('t1', 5))
    t2 = int(kwargs.get('t2', 20))
    assert t1 < t2, "t1 必须小于 t2，否则无法判断金叉死叉"
    ma_type = kwargs.get('ma_type', 'SMA').upper()
    cache_key1 = update_ma_cache(c, ma_type=ma_type, timeperiod=t1)
    cache_key2 = update_ma_cache(c, ma_type=ma_type, timeperiod=t2)

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}#{ma_type}#{t1}#{t2}_BS辅助V230511".split('_')
    v1, v2 = '其他', '任意'
    if len(c.bars_raw) < t2 + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=t2+1)
    mean_solid = np.mean([x.solid for x in bars])
    bar = c.bars_raw[-di]
    solid_th = max(bar.upper, bar.lower, mean_solid)

    if bar.solid < solid_th:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if bar.cache[cache_key1] > bar.cache[cache_key2] and bar.close < bar.open:
        v1 = '看多'

        right_bars = []
        for x in bars[::-1]:
            if x.cache[cache_key1] > x.cache[cache_key2]:
                right_bars.append({'bar': x, '大实体阴线': x.solid > solid_th and x.close < x.open})
            else:
                break

        if len(right_bars) < t2 / 2 and sum([x['大实体阴线'] for x in right_bars]) == 1:
            v2 = '第一个'

    if bar.cache[cache_key1] < bar.cache[cache_key2] and bar.close > bar.open:
        v1 = '看空'

        right_bars = []
        for x in bars[::-1]:
            if x.cache[cache_key1] < x.cache[cache_key2]:
                right_bars.append({'bar': x, '大实体阳线': x.solid > solid_th and x.close > x.open})
            else:
                break

        if len(right_bars) < t2 / 2 and sum([x['大实体阳线'] for x in right_bars]) == 1:
            v2 = '第一个'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_double_ma_V230511, 'freq': '日线', 'di': 2}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')


if __name__ == '__main__':
    check()
