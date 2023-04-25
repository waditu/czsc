import talib as ta
import numpy as np
from czsc import CZSC
from czsc.utils import create_single_signal, get_sub_elements


def update_sar_cache(c: CZSC, **kwargs):
    """更新SAR缓存

    SAR是止损转向操作点指标的简称，英文名称为“Stop and ReVere"，缩写为SAR，一般称为抛物线指标。
    该指标是由美国技术分析大师威尔斯·威尔德所创造出来的。

    详细介绍：

    - https://zhuanlan.zhihu.com/p/210169446
    - https://www.investopedia.com/terms/p/parabolicindicator.asp

    :param c: CZSC对象
    :return:
    """
    cache_key = "SAR"
    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < 50:
        # 初始化缓存
        bars = c.bars_raw
    else:
        # 增量更新最近5个K线缓存
        bars = c.bars_raw[-60:]

    high = np.array([x.high for x in bars])
    low = np.array([x.low for x in bars])
    sar = ta.SAR(high, low)

    for i in range(len(bars)):
        _c = dict(bars[i].cache) if bars[i].cache else dict()
        if cache_key not in _c.keys():
            _c.update({cache_key: sar[i] if sar[i] else 0})
            bars[i].cache = _c

    return cache_key


def tas_sar_base_V230425(c: CZSC, **kwargs):
    """SAR基础信号

    参数模板："{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425"

    **信号逻辑：**

    1. 收盘价升破SAR，且前面MO根K中有任意一根K线的收盘价都低于SAR，看多信号
    2. 收盘价跌破SAR，且前面MO根K中有任意一根K线的收盘价都高于SAR，看空信号

    **信号列表：**

    - Signal('日线_D1MO5SAR_BS辅助V230425_看空_任意_任意_0')
    - Signal('日线_D1MO5SAR_BS辅助V230425_看多_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param kwargs: 其他参数
        - di: 倒数第 di 根 K 线
        - max_overlap: 信号最大重叠K线数
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))
    max_overlap = int(kwargs.get('max_overlap', 5))
    cache_key = update_sar_cache(c)
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425".split('_')
    if len(c.bars_raw) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='其他')

    bars = get_sub_elements(c.bars_raw, di=di, n=max_overlap)
    bar = c.bars_raw[-di]
    sar = c.bars_raw[-di].cache[cache_key]
    if bar.close > sar and any([x.close < x.cache[cache_key] for x in bars]):
        v1 = '看多'
    elif bar.close < sar and any([x.close > x.cache[cache_key] for x in bars]):
        v1 = '看空'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': bar_sar_base_V230425, 'freq': '日线', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')


if __name__ == '__main__':
    check()
