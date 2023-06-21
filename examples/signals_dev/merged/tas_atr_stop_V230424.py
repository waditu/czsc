import talib as ta
import numpy as np
from czsc import CZSC
from czsc.utils import create_single_signal, get_sub_elements


def update_atr_cache(c: CZSC, **kwargs):
    """更新ATR缓存

    平均真实波幅（ATR）的计算方法：

    1、当前交易日的最高价与最低价间的波幅
    2、前一交易日收盘价与当个交易日最高价间的波幅
    3、前一交易日收盘价与当个交易日最低价间的波幅

    今日振幅、今日最高与昨收差价，今日最低与昨收差价中的最大值，为真实波幅，在有了真实波幅后，就可以利用一段时间的平均值计算ATR了。

    :param c: CZSC对象
    :return:
    """
    timeperiod = int(kwargs.get('timeperiod', 14))
    cache_key = f"ATR{timeperiod}"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        bars = c.bars_raw
    else:
        # 增量更新最近5个K线缓存
        bars = c.bars_raw[-timeperiod - 10:]

    high = np.array([x.high for x in bars])
    low = np.array([x.low for x in bars])
    close = np.array([x.close for x in bars])
    atr = ta.ATR(high, low, close, timeperiod=timeperiod)

    for i in range(len(bars)):
        _c = dict(bars[i].cache) if bars[i].cache else dict()
        if cache_key not in _c.keys():
            _c.update({cache_key: atr[i] if atr[i] else 0})
            bars[i].cache = _c

    return cache_key


def bar_atr_break_V230424(c: CZSC, **kwargs):
    """ATR突破

    参数模板："{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403"

    **信号逻辑：**

    1. 以ATR为基础的通道突破；
    2. close 向上突破 LL + th * ATR, 看多；
    3. close 向下突破 HH - th * ATR，看空

    **信号列表：**

    - Signal('日线_D1ATR5T30突破_BS辅助V230424_看空_任意_任意_0')
    - Signal('日线_D1ATR5T30突破_BS辅助V230424_看多_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - timeperiod: ATR的计算周期
        - th: ATR突破的倍数，根据经验优化
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 30))
    timeperiod = int(kwargs.get('timeperiod', 5))
    cache_key = update_atr_cache(c, timeperiod=timeperiod)
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}ATR{timeperiod}T{th}突破_BS辅助V230424".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di, n=timeperiod)
    HH = max([i.high for i in bars])
    LL = min([i.low for i in bars])
    bar = c.bars_raw[-di]
    atr = c.bars_raw[-di].cache[cache_key]

    th = th / 10
    if HH - th * atr > bar.close > LL + th * atr:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    if bar.close > LL + th * atr:
        v1 = '看多'
    elif bar.close < HH - th * atr:
        v1 = '看空'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': bar_atr_break_V230424, 'freq': '日线', 'di': 1, 'timeperiod': 5, 'th': 30}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')


if __name__ == '__main__':
    check()
