import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_eleven_bi_V230622(c: CZSC, **kwargs) -> OrderedDict:
    """十一笔形态分类

    参数模板："{freq}_D{di}十一笔_形态V230622"

    **信号逻辑：**

    十一笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1九笔_形态V230621_类三买_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_A3B3C5式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_类二买_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_A5B3C3式类一卖_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
    
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}九笔_形态V230621".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 16 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=11)
    assert len(bis) == 11 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    direction = bi11.direction

    if direction == Direction.Down:
        if min_low == bi11.low and max_high == bi1.high:
            # ABC式类一买，A5B3C3
            if bi5.low == min([x.low for x in [bi1, bi3, bi5]]) \
                    and bi9.low > bi11.low and bi9.high > bi11.high \
                    and bi8.high > bi6.low and bi1.high - bi5.low > bi9.high - bi11.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A5B3C3式类一买')

            # ABC式类一买，A3B3C5
            if bi1.high > bi3.high and bi1.low > bi3.low \
                    and bi7.high == max([x.high for x in [bi7, bi9, bi11]]) \
                    and bi6.high > bi4.low and bi1.high - bi3.low > bi7.high - bi11.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B3C5式类一买')

            # ABC式类一买，A3B5C3
            if bi1.low > bi3.low and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi9.high > bi11.high and bi1.high - bi3.low > bi9.high - bi11.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B5C3式类一买')

            # a1Ab式类一买，a1（1~7构成的类趋势）
            if bi2.low > bi4.high > bi4.low > bi6.high > bi5.low > bi7.low and bi10.high > bi8.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='a1Ab式类一买')

        # 类二买（1~7构成盘整背驰，246构成下跌中枢，9/11构成上涨中枢，且上涨中枢GG大于下跌中枢ZG）
        if bi7.power < bi1.power and min_low == bi7.low < max([x.low for x in [bi2, bi4, bi6]]) \
                < min([x.high for x in [bi2, bi4, bi6]]) < max([x.high for x in [bi9, bi11]]) < bi1.high == max_high \
                and bi11.low > min([x.low for x in [bi2, bi4, bi6]]) \
                and min([x.high for x in [bi9, bi11]]) > max([x.low for x in [bi9, bi11]]):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二买')

        # 类二买（1~7为区间极值，9~11构成上涨中枢，上涨中枢GG大于4~6的最大值，上涨中枢DD大于4~6的最小值）
        if max_high == bi1.high and min_low == bi7.low \
                and min(bi9.high, bi11.high) > max(bi9.low, bi11.low) \
                and max(bi11.high, bi9.high) > max(bi4.high, bi6.high) \
                and min(bi9.low, bi11.low) > min(bi4.low, bi6.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二买')

        # 类三买（1~9构成大级别中枢，10离开，11回调不跌破GG）
        gg = max([x.high for x in [bi1, bi2, bi3]])
        zg = min([x.high for x in [bi1, bi2, bi3]])
        zd = max([x.low for x in [bi1, bi2, bi3]])
        dd = min([x.low for x in [bi1, bi2, bi3]])
        if max_high == bi11.high and bi11.low > zg > zd \
                and gg > bi5.low and gg > bi7.low and gg > bi9.low \
                and dd < bi5.high and dd < bi7.high and dd < bi9.high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买')

    if direction == Direction.Up:
        if max_high == bi11.high and min_low == bi1.low:
            # ABC式类一卖，A5B3C3
            if bi5.high == max([bi1.high, bi3.high, bi5.high]) and bi9.low < bi11.low and bi9.high < bi11.high \
                    and bi8.low < bi6.high and bi11.high - bi9.low < bi5.high - bi1.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A5B3C3式类一卖')

            # ABC式类一卖，A3B3C5
            if bi7.low == min([bi11.low, bi9.low, bi7.low]) and bi1.high < bi3.high and bi1.low < bi3.low \
                    and bi6.low < bi4.high and bi11.high - bi7.low < bi3.high - bi1.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B3C5式类一卖')

            # ABC式类一卖，A3B5C3
            if bi1.high < bi3.high and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi9.low < bi11.low and bi3.high - bi1.low > bi11.high - bi9.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B5C3式类一卖')
            
        # 类二卖：1~9构成类趋势，11不创新高
        if max_high == bi9.high > bi8.low > bi6.high > bi6.low > bi4.high > bi4.low > bi2.high > bi1.low == min_low \
                and bi11.high < bi9.high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二卖')
        
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_eleven_bi_V230622, 'freq': '60分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
