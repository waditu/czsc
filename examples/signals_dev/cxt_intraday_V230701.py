from loguru import logger
from czsc import CzscSignals
from collections import OrderedDict
from czsc.utils import create_single_signal


def cxt_intraday_V230701(cat: CzscSignals, **kwargs) -> OrderedDict:
    """每日走势分类

    参数模板："{freq1}#{freq2}_D{di}日_走势分类V230701"

    **信号逻辑：**

    参见博客：https://blog.sina.com.cn/s/blog_486e105c010009uy.html

    **信号列表：**

    - Signal('30分钟#日线_D2日_走势分类V230701_强平衡市_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_弱平衡市_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_双中枢下跌_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_转折平衡市_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_双中枢上涨_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 2))
    freq1 = kwargs.get("freq1", "30分钟")
    freq2 = kwargs.get("freq2", "日线")
    assert freq1 == '30分钟', 'freq1必须为30分钟'
    assert freq2 == '日线', 'freq2必须为日线'

    assert 21 > di > 0, "di必须为大于0小于21的整数，暂不支持当日走势分类"
    k1, k2, k3 = f"{freq1}#{freq2}_D{di}日_走势分类V230701".split('_')
    v1 = "其他"
    if '30分钟' not in cat.kas.keys() or '日线' not in cat.kas.keys():
        logger.warning(f"缺少30分钟或日线K线数据，无法计算当日走势分类, {cat.kas.keys()}")
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    c1 = cat.kas[freq1]
    c2 = cat.kas[freq2]
    day = c2.bars_raw[-di].dt.date()
    bars = [x for x in c1.bars_raw if x.dt.date() == day]
    assert len(bars) <= 8, f"仅适用于A股市场，日内有8根30分钟K线的情况, {len(bars)}, {day}, {bars}"
    if len(bars) <= 4:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    zs_list = []
    for b1, b2, b3 in zip(bars[:-2], bars[1:-1], bars[2:]):
        if min(b1.high, b2.high, b3.high) > max(b1.low, b2.low, b3.low):
            zs_list.append([b1, b2, b3])
    
    _dir = "上涨" if bars[-1].close > bars[0].open else "下跌"

    if not zs_list:
        v1 = f"无中枢{_dir}"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    # 双中枢的情况，有一根K线的 high low 与前后两个中枢没有重叠
    if len(zs_list) >= 2:
        zs1, zs2 = zs_list[0], zs_list[-1]
        zs1_high, zs1_low = max([x.high for x in zs1]), min([x.low for x in zs1])
        zs2_high, zs2_low = max([x.high for x in zs2]), min([x.low for x in zs2])
        if _dir == "上涨" and zs1_high < zs2_low:
            v1 = f"双中枢{_dir}"
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
        
        if _dir == "下跌" and zs1_low > zs2_high:
            v1 = f"双中枢{_dir}"
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
        
    # 单中枢的情况，前三根K线出现高点：弱平衡市，前三根K线出现低点：强平衡市，否则：转折平衡市
    high_first = max(bars[0].high, bars[1].high, bars[2].high) == max([x.high for x in bars])
    low_first = min(bars[0].low, bars[1].low, bars[2].low) == min([x.low for x in bars])
    if high_first and not low_first:
        v1 = "弱平衡市"
    elif low_first and not high_first:
        v1 = "强平衡市"
    else:
        v1 = "转折平衡市"
        
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_intraday_V230701, 'di': 1, 'freq1': '30分钟', 'freq2': '日线'}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=0) # type: ignore


if __name__ == '__main__':
    check()
