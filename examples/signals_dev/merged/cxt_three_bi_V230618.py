import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.utils import create_single_signal, get_sub_elements


def cxt_three_bi_V230618(c: CZSC, **kwargs) -> OrderedDict:
    """三笔形态分类

    参数模板："{freq}_D{di}三笔_形态V230618"

    **信号逻辑：**

    三笔的形态分类

    **信号列表：**

    - Signal('日线_D1三笔_形态V230618_向下盘背_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上奔走型_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上扩张_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下奔走型_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上收敛_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下无背_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上不重合_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下收敛_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下扩张_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下不重合_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上盘背_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上无背_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
    
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}三笔_形态V230618".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=3)
    assert len(bis) == 3 and bis[0].direction == bis[2].direction
    bi1, bi2, bi3 = bis

    # 识别向下形态
    if bi3.direction == Direction.Down:
        if bi3.low > bi1.high:
            v1 = '向下不重合'
        elif bi2.low < bi3.low < bi1.high < bi2.high:
            v1 = '向下奔走型'
        elif bi1.high > bi3.high and bi1.low < bi3.low:
            v1 = '向下收敛'
        elif bi1.high < bi3.high and bi1.low > bi3.low:
            v1 = '向下扩张'
        elif bi3.low < bi1.low and bi3.high < bi1.high:
            v1 = '向下盘背' if bi3.power < bi1.power else '向下无背'

    # 识别向上形态
    elif bi3.direction == Direction.Up:
        if bi3.high < bi1.low:
            v1 = '向上不重合'
        elif bi2.low < bi1.low < bi3.high < bi2.high:
            v1 = '向上奔走型'
        elif bi1.high > bi3.high and bi1.low < bi3.low:
            v1 = '向上收敛'
        elif bi1.high < bi3.high and bi1.low > bi3.low:
            v1 = '向上扩张'
        elif bi3.low > bi1.low and bi3.high > bi1.high:
            v1 = '向上盘背' if bi3.power < bi1.power else '向上无背'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_three_bi_V230618, 'freq': '日线', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
