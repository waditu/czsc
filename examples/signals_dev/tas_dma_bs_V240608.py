from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.signals.tas import update_ma_cache
from czsc.utils import create_single_signal


def tas_dma_bs_V240608(c: CZSC, **kwargs) -> OrderedDict:
    """双均线多头排列下的回调买点

    参数模板："{freq}_N{n}双均线{t1}#{t2}顺势_BS辅助V240608"

    **信号逻辑：**

    参考链接：https://mp.weixin.qq.com/s/hR6wl3UrWvmLm1j5EABVyA

    买点的定位以均线为主，要求如下。
    1，做多的情况下5日均线和10日均线必须多头排列，做空的情况下5日均线和10日均线必须空头排列。
    2，以做多为例，做空反过来就是：日线价格回调到到5日均线或者10日均线。

    **信号列表：**

    - Signal('60分钟_N5双均线5#13顺势_BS辅助V240608_买点_任意_任意_0')
    - Signal('60分钟_N5双均线5#13顺势_BS辅助V240608_卖点_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无

        - n: int, 默认5，取最近均线附近n个价格
        - t1: int, 默认5，均线1的周期
        - t2: int, 默认10，均线2的周期
    :return: 信号识别结果
    """
    n = int(kwargs.get('n', 5))
    t1 = int(kwargs.get('t1', 5))
    t2 = int(kwargs.get('t2', 10))

    assert t1 < t2, "均线1的周期必须小于均线2的周期"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_N{n}双均线{t1}#{t2}顺势_BS辅助V240608".split('_')
    v1 = '其他'
    ma1 = update_ma_cache(c, timeperiod=t1)
    ma2 = update_ma_cache(c, timeperiod=t2)
    if len(c.bars_raw) < 110:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = c.bars_raw[-100:]
    unique_prices = [x.close for x in bars] + [x.high for x in bars] + [x.low for x in bars] + [x.open for x in bars]
    unique_prices = sorted(list(set(unique_prices)))

    bar1, bar2 = bars[-2], bars[-1]
    ma1_value, ma2_value = bar2.cache[ma1], bar2.cache[ma2]
    lower_prices = [x for x in unique_prices if x < ma2_value]
    upper_prices = [x for x in unique_prices if x > ma2_value]

    if upper_prices and ma1_value > ma2_value and bar2.cache[ma2] > bar1.cache[ma2]:
        # ma2_round_high 是 ma2_value 上方的第 n 个价格
        ma2_round_high = upper_prices[n] if len(upper_prices) > n else upper_prices[-1]
        # 买点：1）上一根K线的最低价小于 ma2_round_high；2）当前K线的最高价大于 ma2_round_high，且收盘价小于 ma2_round_high
        if bar1.low < ma2_round_high < bar2.high and bar2.close < ma2_round_high:
            v1 = '买点'

    elif lower_prices and ma1_value < ma2_value and bar2.cache[ma2] < bar1.cache[ma2]:
        # ma2_round_low 是 ma2_value 下方的第 n 个价格
        ma2_round_low = lower_prices[-n] if len(lower_prices) > n else lower_prices[0]
        # 卖点：1）上一根K线的最高价大于 ma2_round_low；2）当前K线的收盘价大于 ma2_round_low，且收盘价大于 ma2_round_low
        if bar1.high > ma2_round_low > bar2.low and bar2.close > ma2_round_low:
            v1 = '卖点'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_dma_bs_V240608, 'freq': "60分钟", 'n': 5, 't1': 5, 't2': 13}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore


if __name__ == '__main__':
    check()
