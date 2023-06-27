import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_seven_bi_V230620(c: CZSC, **kwargs) -> OrderedDict:
    """七笔形态分类

    参数模板："{freq}_D{di}七笔_形态V230620"

    **信号逻辑：**

    七笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1七笔_形态V230620_类三卖_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_向上中枢完成_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAbcd式顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_类三买_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_向下中枢完成_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAb式底背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_abcAd式顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_abcAd式底背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAb式顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_类趋势顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAbcd式底背驰_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
    
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}七笔_形态V230620".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 10 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=7)
    assert len(bis) == 7 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    direction = bi7.direction

    if direction == Direction.Down:
        if bi1.high == max_high and bi7.low == min_low:
            # aAbcd式底背驰
            if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) > bi6.high and bi7.power < bi5.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式底背驰')

            # abcAd式底背驰
            if bi2.low > min(bi4.high, bi6.high) > max(bi4.low, bi6.low) and bi7.power < (bi1.high - bi3.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='abcAd式底背驰')

            # aAb式底背驰
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) and bi7.power < bi1.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式底背驰')

            # 类趋势底背驰
            if bi2.low > bi4.high and bi4.low > bi6.high and bi7.power < max(bi5.power, bi3.power, bi1.power):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势底背驰')

        # 向上中枢完成
        if bi4.low == min_low and min(bi1.high, bi3.high) > max(bi1.low, bi3.low) \
                and min(bi5.high, bi7.high) > max(bi5.low, bi7.low) \
                and max(bi4.high, bi6.high) > min(bi3.high, bi4.high):
            if max(bi1.low, bi3.low) < max(bi5.high, bi7.high):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='向上中枢完成')

        # 七笔三买：1~3构成中枢，最低点在1~3，最高点在5~7，5~7的最低点大于1~3的最高点
        if min(bi1.low, bi3.low) == min_low and max(bi5.high, bi7.high) == max_high \
                and min(bi5.low, bi7.low) > max(bi1.high, bi3.high) \
                and min(bi1.high, bi3.high) > max(bi1.low, bi3.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买')

    if direction == Direction.Up:
        # 顶背驰
        if bi1.low == min_low and bi7.high == max_high:
            # aAbcd式顶背驰
            if bi6.low > min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and bi7.power < bi5.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式顶背驰')

            # abcAd式顶背驰
            if min(bi4.high, bi6.high) > max(bi4.low, bi6.low) > bi2.high and bi7.power < (bi3.high - bi1.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='abcAd式顶背驰')

            # aAb式顶背驰
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) and bi7.power < bi1.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式顶背驰')

            # 类趋势顶背驰
            if bi2.high < bi4.low and bi4.high < bi6.low and bi7.power < max(bi5.power, bi3.power, bi1.power):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势顶背驰')

        # 向下中枢完成
        if bi4.high == max_high and min(bi1.high, bi3.high) > max(bi1.low, bi3.low) \
                and min(bi5.high, bi7.high) > max(bi5.low, bi7.low) \
                and min(bi4.low, bi6.low) < max(bi3.low, bi4.low):
            if min(bi1.high, bi3.high) > min(bi5.low, bi7.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='向下中枢完成')

        # 七笔三卖：1~3构成中枢，最高点在1~3，最低点在5~7，5~7的最高点小于1~3的最低点
        if min(bi5.low, bi7.low) == min_low and max(bi1.high, bi3.high) == max_high \
                and max(bi7.high, bi5.high) < min(bi1.low, bi3.low) \
                and min(bi1.high, bi3.high) > max(bi1.low, bi3.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三卖')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_seven_bi_V230620, 'freq': '60分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
