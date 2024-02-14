from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Direction, ZS
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal, get_sub_elements


def tas_macd_bc_ubi_V230804(c: CZSC, **kwargs) -> OrderedDict:
    """未完成笔MACD黄白线辅助背驰判断

    参数模板："{freq}_MACD背驰_BS辅助V230804"

    **信号逻辑：**

    以向上未完成笔为例，当前笔在中枢中轴上方，且MACD黄白线不是最高，认为是背驰，做空；反之，做多。

    **信号列表：**

    - Signal('60分钟_MACD背驰_UBI观察V230804_多头_任意_任意_0')
    - Signal('60分钟_MACD背驰_UBI观察V230804_空头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_MACD背驰_UBI观察V230804".split('_')
    v1 = '其他'
    cache_key = update_macd_cache(c)
    ubi = c.ubi
    if len(c.bi_list) < 7 or not ubi or len(ubi['raw_bars']) < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=1, n=6)
    zs = ZS(bis=bis[-5:])
    if not zs.is_valid:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    dd = min([bi.low for bi in bis])
    gg = max([bi.high for bi in bis])
    b1, b2, b3, b4, b5 = bis[-5:]
    if ubi['direction'] == Direction.Up and ubi['high'] > (gg - (gg - dd) / 4):
        b5_dif = max([x.cache[cache_key]['dif'] for x in ubi['raw_bars'][-5:]])
        od_dif = max([x.cache[cache_key]['dif'] for x in b2.fx_b.raw_bars + b4.fx_b.raw_bars])
        if 0 < b5_dif < od_dif:
            v1 = '空头'
    
    if ubi['direction'] == Direction.Down and ubi['low'] < (dd + (gg - dd) / 4):
        b5_dif = min([x.cache[cache_key]['dif'] for x in ubi['raw_bars'][-5:]])
        od_dif = min([x.cache[cache_key]['dif'] for x in b2.fx_b.raw_bars + b4.fx_b.raw_bars])
        if 0 > b5_dif > od_dif:
            v1 = '多头'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_macd_bc_ubi_V230804, 'freq': "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore


if __name__ == '__main__':
    check()
