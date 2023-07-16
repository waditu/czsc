from loguru import logger
from czsc import CZSC
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def bar_eight_V230702(c: CZSC, **kwargs) -> OrderedDict:
    """8K走势分类

    参数模板："{freq}_D{di}#8K_走势分类V230702"

    **信号逻辑：**

    参见博客：https://blog.sina.com.cn/s/blog_486e105c010009uy.html
    这篇博客给出了8K走势分类的逻辑。

    **信号列表：**

    - Signal('30分钟_D1#8K_走势分类V230702_弱平衡市_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_双中枢下跌_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_转折平衡市_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_强平衡市_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_双中枢上涨_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_无中枢上涨_任意_任意_0')
    - Signal('30分钟_D1#8K_走势分类V230702_无中枢下跌_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}#8K_走势分类V230702".split("_")
    v1 = "其他"
    if len(c.bars_raw) < di + 12:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bars = get_sub_elements(c.bars_raw, di=di, n=8)
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

    signals_config = [{'name': bar_eight_V230702, 'di': 1, 'freq': '30分钟'}]
    check_signals_acc(bars, signals_config=signals_config, height='780px', delta_days=0) # type: ignore


if __name__ == '__main__':
    check()
