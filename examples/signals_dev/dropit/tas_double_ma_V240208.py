from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.signals.tas import update_ma_cache
from czsc.utils import create_single_signal, get_sub_elements, fast_slow_cross


def tas_double_ma_V240208(c: CZSC, **kwargs) -> OrderedDict:
    """双均线多空信号，辅助V240208

    参数模板："{freq}_D{di}N{N}M{M}双均线_BS辅助V240208"

    **信号逻辑：**

    1. 找出最近3个均线交叉点，时间上由远到近，分别为 X1，X2，X3
    2. 以多头为例：X3 和 X1 为金叉，且 X2 的价格最高

    **信号列表：**

    - Signal('60分钟_D1N5M21双均线_BS辅助V240208_多头_任意_任意_0')
    - Signal('60分钟_D1N5M21双均线_BS辅助V240208_空头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数设置

        - di: int, default 1, 倒数第几根K线
        - N: int, default 20, 快线周期
        - M: int, default 60, 慢线周期

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    N = int(kwargs.get('N', 20))
    M = int(kwargs.get('M', 60))
    assert N < M, "N < M"

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{N}M{M}双均线_BS辅助V240208".split('_')
    v1 = '其他'
    fast_ma_key = update_ma_cache(c, ma_type='SMA', timeperiod=N)
    slow_ma_key = update_ma_cache(c, ma_type='SMA', timeperiod=M)

    bars = get_sub_elements(c.bars_raw, di=di, n=M * 30)
    fast_ma = [x.cache[fast_ma_key] for x in bars]
    slow_ma = [x.cache[slow_ma_key] for x in bars]
    cross_info = fast_slow_cross(fast_ma, slow_ma)

    if len(cross_info) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    x1, x2, x3 = cross_info[-3:]
    if x3['类型'] == "金叉" and x2['快线'] > max(x1['快线'], x3['快线']):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='多头')

    if x3['类型'] == "死叉" and x2['快线'] < min(x1['快线'], x3['快线']):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1='空头')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_double_ma_V240208, 'freq': "60分钟", 'N': 5, 'M': 21}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore


if __name__ == '__main__':
    check()
