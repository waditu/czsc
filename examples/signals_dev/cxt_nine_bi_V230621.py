import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_nine_bi_V230621(c: CZSC, **kwargs) -> OrderedDict:
    """九笔形态分类

    参数模板："{freq}_D{di}九笔_形态V230621"

    **信号逻辑：**

    九笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1九笔_形态V230621_类三买A_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAb式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_类三卖A_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbcd式类一买_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_ABC式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbBc式类一买_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbcd式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_ZD三卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbBc式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_ABC式类一买_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
    
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}九笔_形态V230621".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 13 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=9)
    assert len(bis) == 9 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    direction = bi9.direction

    if direction == Direction.Down:
        if min_low == bi9.low and max_high == bi1.high:
            # aAb式类一买
            if min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low) \
                    and bi9.power < bi1.power and bi3.low >= bi1.low and bi7.high <= bi9.high:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式类一买')

            # aAbcd式类一买
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) > bi8.high \
                    and bi9.power < bi7.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式类一买')

            # ABC式类一买
            if bi3.low < bi1.low and bi7.high > bi9.high \
                    and min(bi4.high, bi6.high) > max(bi4.low, bi6.low) \
                    and (bi1.high - bi3.low) > (bi7.high - bi9.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ABC式类一买')

            # 类趋势一买
            if bi8.high < bi6.low < bi6.high < bi4.low < bi4.high < bi2.low \
                    and bi9.power < max([bi1.power, bi3.power, bi5.power, bi7.power]):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势一买')

        # aAbBc式类一买（2~4构成中枢A，6~8构成中枢B，9背驰）
        if max_high == max(bi1.high, bi3.high) and min_low == bi9.low \
                and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                and min(bi2.low, bi4.low) > max(bi6.high, bi8.high) \
                and min(bi6.high, bi8.high) > max(bi6.low, bi8.low) \
                and bi9.power < bi5.power:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbBc式类一买')

        # 类三买（1357构成中枢，最低点在3或5）
        if max_high == bi9.high > bi9.low \
                > max([x.high for x in [bi1, bi3, bi5, bi7]]) \
                > min([x.high for x in [bi1, bi3, bi5, bi7]]) \
                > max([x.low for x in [bi1, bi3, bi5, bi7]]) \
                > min([x.low for x in [bi3, bi5]]) == min_low:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买A')

        # 类三买（357构成中枢，8的力度小于2，9回调不跌破GG构成三买）
        if bi8.power < bi2.power and max_high == bi9.high > bi9.low \
                > max([x.high for x in [bi3, bi5, bi7]]) \
                > min([x.high for x in [bi3, bi5, bi7]]) \
                > max([x.low for x in [bi3, bi5, bi7]]) > bi1.low == min_low:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买B')
        
        if min_low == bi5.low and max_high == bi1.high and bi4.high < bi2.low:  # 前五笔构成向下类趋势
            zd = max([x.low for x in [bi5, bi7]])
            zg = min([x.high for x in [bi5, bi7]])
            gg = max([x.high for x in [bi5, bi7]])
            if zg > zd and bi8.high > gg:  # 567构成中枢，且8的高点大于gg
                if bi9.low > zg:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ZG三买')

                # 类二买
                if bi9.high > gg > zg > bi9.low > zd:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二买')

    if direction == Direction.Up:
        if max_high == bi9.high and min_low == bi1.low:
            # aAbBc式类一卖
            if bi6.low > min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and min(bi6.high, bi8.high) > max(bi6.low, bi8.low) \
                    and max(bi2.high, bi4.high) < min(bi6.low, bi8.low) \
                    and bi9.power < bi5.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbBc式类一卖')

            # aAb式类一卖
            if min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low) \
                    and bi9.power < bi1.power and bi3.high <= bi1.high and bi7.low >= bi9.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式类一卖')

            # aAbcd式类一卖
            if bi8.low > min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) \
                    and bi9.power < bi7.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式类一卖')
            
            # ABC式类一卖
            if bi3.high > bi1.high and bi7.low < bi9.low \
                    and min(bi4.high, bi6.high) > max(bi4.low, bi6.low) \
                    and (bi3.high - bi1.low) > (bi9.high - bi7.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ABC式类一卖')
            
            # 类趋势一卖
            if bi8.low > bi6.high > bi6.low > bi4.high > bi4.low > bi2.high \
                    and bi9.power < max([bi1.power, bi3.power, bi5.power, bi7.power]):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势一卖')
            
        # 九笔三卖
        if max_high == bi1.high and min_low == bi9.low \
                and bi9.high < max([x.low for x in [bi3, bi5, bi7]]) < min([x.high for x in [bi3, bi5, bi7]]):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三卖A')

        if min_low == bi1.low and max_high == bi5.high and bi2.high < bi4.low:  # 前五笔构成向上类趋势
            zd = max([x.low for x in [bi5, bi7]])
            zg = min([x.high for x in [bi5, bi7]])
            dd = min([x.low for x in [bi5, bi7]])
            if zg > zd and bi8.low < dd:  # 567构成中枢，且8的低点小于dd
                if bi9.high < zd:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ZD三卖')

                # 类二卖
                if dd < zd <= bi9.high < zg:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二卖')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_nine_bi_V230621, 'freq': '60分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
