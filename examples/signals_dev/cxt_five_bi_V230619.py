import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_five_bi_V230619(c: CZSC, **kwargs) -> OrderedDict:
    """五笔形态分类

    参数模板："{freq}_D{di}五笔_形态V230619"

    **信号逻辑：**

    五笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1五笔_形态V230619_上颈线突破_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类三卖_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类趋势底背驰_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类趋势顶背驰_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_下颈线突破_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类三买_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_aAb式顶背驰_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_aAb式底背驰_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
    
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}五笔_形态V230619".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=5)
    assert len(bis) == 5 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5 = bis

    direction = bi1.direction
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    assert direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if direction == Direction.Down:
        # aAb式底背驰
        if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and max_high == bi1.high and bi5.power < bi1.power:
            if (min_low == bi3.low and bi5.low < bi1.low) or (min_low == bi5.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式底背驰')

        # 类趋势底背驰
        if max_high == bi1.high and min_low == bi5.low and bi4.high < bi2.low and bi5.power < max(bi3.power, bi1.power):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势底背驰')

        # 上颈线突破
        if (min_low == bi1.low and bi5.high > min(bi1.high, bi2.high) > bi5.low > bi1.low) \
                or (min_low == bi3.low and bi5.high > bi3.high > bi5.low > bi3.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='上颈线突破')

        # 五笔三买，要求bi5.high是最高点
        if max_high == bi5.high > bi5.low > max(bi1.high, bi3.high) \
                > min(bi1.high, bi3.high) > max(bi1.low, bi3.low) > min_low:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买')

    if direction == Direction.Up:
        # aAb式顶背驰
        if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and min_low == bi1.low and bi5.power < bi1.power:
            if (max_high == bi3.high and bi5.high > bi1.high) or (max_high == bi5.high):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式顶背驰')

        # 类趋势顶背驰
        if min_low == bi1.low and max_high == bi5.high and bi5.power < max(bi1.power, bi3.power) and bi4.low > bi2.high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势顶背驰')

        # 下颈线突破
        if (max_high == bi1.high and bi5.low < max(bi1.low, bi2.low) < bi5.high < max_high) \
                or (max_high == bi3.high and bi5.low < bi3.low < bi5.high < max_high):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='下颈线突破')

        # 五笔三卖，要求bi5.low是最低点
        if min_low == bi5.low < bi5.high < min(bi1.low, bi3.low) \
                < max(bi1.low, bi3.low) < min(bi1.high, bi3.high) < max_high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三卖')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_five_bi_V230619, 'freq': '60分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
