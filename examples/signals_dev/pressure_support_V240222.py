from collections import OrderedDict
from czsc.analyze import CZSC
from czsc.objects import Direction, ZS
from czsc.signals.tas import update_macd_cache
from czsc.utils import create_single_signal, get_sub_elements


def pressure_support_V240222(c: CZSC, **kwargs) -> OrderedDict:
    """支撑压力线辅助V240222

    参数模板："{freq}_D{di}MACD背驰_BS辅助V230804"

    **信号逻辑：**

    给定窗口内，当前价格与前高前低的关系，判断当前价格的压力和支撑。以高点验证压力位为例：

    1. 当前高点与前高的差值在0.2个标准差以内
    2. 当前高点与前高分别在窗口的两端
    3. 中间的最低价与高点的差值在2个标准差以外

    **信号列表：**

    - Signal('60分钟_D1MACD背驰_BS辅助V230804_空头_任意_任意_0')
    - Signal('60分钟_D1MACD背驰_BS辅助V230804_多头_任意_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    w = int(kwargs.get('w', 20))

    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}高低点验证_支撑压力V240222".split('_')
    v1 = '其他'
    if len(c.bars_raw) < 100:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=7)
    zs = ZS(bis=bis[-5:])
    if not zs.is_valid:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    dd = min([bi.low for bi in bis])
    gg = max([bi.high for bi in bis])
    b1, b2, b3, b4, b5 = bis[-5:]
    if b5.direction == Direction.Up and b5.high > (gg - (gg - dd) / 4):
        b5_dif = max([x.cache[cache_key]['dif'] for x in b5.fx_b.raw_bars])
        od_dif = max([x.cache[cache_key]['dif'] for x in b1.fx_b.raw_bars + b3.fx_b.raw_bars])
        if 0 < b5_dif < od_dif:
            v1 = '空头'

    if b5.direction == Direction.Down and b5.low < (dd + (gg - dd) / 4):
        b5_dif = min([x.cache[cache_key]['dif'] for x in b5.fx_b.raw_bars])
        od_dif = min([x.cache[cache_key]['dif'] for x in b1.fx_b.raw_bars + b3.fx_b.raw_bars])
        if 0 > b5_dif > od_dif:
            v1 = '多头'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': tas_macd_bc_V230804, 'freq': "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=5)  # type: ignore


if __name__ == '__main__':
    check()
