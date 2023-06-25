from collections import OrderedDict
import numpy as np
import pandas as pd
from loguru import logger
from czsc.connectors import research
from czsc import CZSC, check_signals_acc, get_sub_elements
from czsc.utils import create_single_signal


def demakder_up_dw_line_V230605(c: CZSC, **kwargs) -> OrderedDict:
    """DEM多空，贡献者：琅盎

    参数模板："{freq}_D{di}N{n}H{th}L{tl}_DEM多空V230605"

    **信号逻辑：**

    "Demark Indicator"（也称为 "DeMarker Indicator" 或 "DeM"）是一种基于价格和时间的技术分析指标，
    用于衡量市场的过度买入或卖出。它是由 Tom Demark 开发的，旨在识别市场的顶部和底部。

    当 demaker>0.7 时上升趋势强烈，当 demaker<0.3 时下跌趋势强烈。
    当 demaker 上穿 0.7/下穿 0.3 时产生买入/卖出信号。

    **信号列表：**

    - Signal('日线_D1N105TH7TL7_V230605demakder_看空_任意_任意_0')
    - Signal('日线_D1N105TH7TL7_V230605demakder_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - :param di: 信号计算截止倒数第i根K线
        - :param n: 获取K线的根数，默认为100
        - :param th: 开多预值，默认为7，即demaker上穿0.7
        - :param tl: 开空预值，默认为3，即demaker下穿0.3
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    n = int(kwargs.get("n", 100))
    th = int(kwargs.get("th", 7))
    tl = int(kwargs.get("tl", 3))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}H{th}L{tl}_DEM多空V230605".split('_')

    v1 = "其他"
    if len(c.bars_raw) < di + n + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bars = get_sub_elements(c.bars_raw, di=di, n=n)
    # highs = np.array([bar.high for bar in _bars])
    # lows = np.array([bar.low for bar in _bars])

    # diff_highs = np.diff(highs)
    # diff_lows = np.diff(lows)

    # demax = np.mean(diff_highs[diff_highs > 0])
    # demin = np.mean(diff_lows[diff_lows < 0])

    demax = np.mean([_bars[i].high - _bars[i-1].high for i in range(1, len(_bars)) if _bars[i].high - _bars[i-1].high > 0])
    demin = np.mean([_bars[i-1].low - _bars[i].low for i in range(1, len(_bars)) if _bars[i-1].low - _bars[i].low > 0])
    demaker = demax / (demax + demin)

    # logger.info(f"demaker:{demaker}, demax:{demax}, demin:{demin}")
    if demaker > th / 10:
        v1 = "看多"
    if demaker < tl / 10:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def main():
    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [
        {'name': demakder_up_dw_line_V230605, 'freq': '30分钟', 'di': 1},
    ]
    check_signals_acc(bars, signals_config=signals_config) # type: ignore


if __name__ == '__main__':
    main()
