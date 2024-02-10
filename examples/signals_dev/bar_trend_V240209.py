import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC
from loguru import logger
from czsc.signals.tas import update_ma_cache, update_macd_cache
from czsc.utils import create_single_signal, get_sub_elements, fast_slow_cross


def bar_trend_V240209(c: CZSC, **kwargs) -> OrderedDict:
    """趋势跟踪信号

    参数模板："{freq}_D{di}N{N}趋势跟踪_BS辅助V240209"

    **信号逻辑：**

    以多头为例：
    1. 低点出现在高点之后，且低点右侧的高点到当前K线之间的K线数量在5-30之间；
    2. 低点右侧的K线的DIF值小于前N根K线的DIF值的标准差的一半；
    3. 低点右侧的K线的最低价大于低点的最低价；
    4. 低点右侧的K线的MACD值小于前N根K线的MACD值的标准差的一半。

    **信号列表：**

    - Signal('60分钟_D1N60趋势跟踪_BS辅助V240209_多头_任意_任意_0')
    - Signal('60分钟_D1N60趋势跟踪_BS辅助V240209_空头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数设置

        - di: int, default 1, 倒数第几根K线
        - N: int, default 20, 窗口大小

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    N = int(kwargs.get('N', 60))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{N}趋势跟踪_BS辅助V240209".split('_')
    v1 = '其他'
    cache_key = update_macd_cache(c)
    bars = get_sub_elements(c.bars_raw, di=di, n=N)
    max_bar = max(bars, key=lambda x: x.high)
    min_bar = min(bars, key=lambda x: x.low)
    dif_std = np.std([x.cache[cache_key]['dif'] for x in bars])
    macd_std = np.std([x.cache[cache_key]['macd'] for x in bars])

    if min_bar.dt < max_bar.dt:
        right_bars = [x for x in c.bars_raw if x.dt >= max_bar.dt]
        right_min_bar = min(right_bars, key=lambda x: x.low)
        c1 = 30 > right_min_bar.id - max_bar.id > 5
        c2 = abs(right_bars[-1].cache[cache_key]['dif']) < dif_std        # type: ignore
        c3 = right_min_bar.low > min_bar.low
        c4 = abs(right_bars[-1].cache[cache_key]['macd']) < macd_std     # type: ignore

        if c1 and c2 and c3 and c4:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="多头")

    if min_bar.dt > max_bar.dt:
        right_bars = [x for x in c.bars_raw if x.dt >= min_bar.dt]
        right_max_bar = max(right_bars, key=lambda x: x.high)
        c1 = 30 > right_max_bar.id - min_bar.id > 5
        c2 = abs(right_bars[-1].cache[cache_key]['dif']) < dif_std        # type: ignore
        c3 = right_max_bar.high < max_bar.high
        c4 = abs(right_bars[-1].cache[cache_key]['macd']) < macd_std      # type: ignore

        if c1 and c2 and c3 and c4:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1="空头")

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': bar_trend_V240209, 'freq': "60分钟", 'N': 60}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=1)  # type: ignore


if __name__ == '__main__':
    check()
