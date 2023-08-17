import talib as ta
import numpy as np
from czsc import CZSC, Direction
from collections import OrderedDict
from czsc.objects import Mark
from czsc.utils import create_single_signal, get_sub_elements


def cxt_ubi_end_V230816(c: CZSC, **kwargs) -> OrderedDict:
    """当前是未完成笔的第几次新低或新高，用于笔结束辅助

    参数模板："{freq}_UBI_BE辅助V230816"

    **信号逻辑：**

    以向上未完成笔为例：取所有顶分型，计算创新高的底分型数量N，如果当前K线创新高，则新高次数为N+1

    **信号列表：**

    - Signal('日线_UBI_BE辅助V230816_新低_第4次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第5次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第6次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第2次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第3次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第4次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第5次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第6次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第7次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第2次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第3次_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_UBI_BE辅助V230816".split('_')
    v1, v2 = '其他','其他'
    ubi = c.ubi
    if not ubi or len(ubi['fxs']) <= 2 or len(c.bars_ubi) <= 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    fxs = ubi['fxs']
    if ubi['direction'] == Direction.Up:
        fxs = [x for x in fxs if x.mark == Mark.G]
        cnt = 1
        cur_hfx = fxs[0]
        for fx in fxs[1:]:
            if fx.high > cur_hfx.high:
                cnt += 1
                cur_hfx = fx

        if ubi['raw_bars'][-1].high > cur_hfx.high:
            v1 = '新高'
            v2 = f"第{cnt + 1}次"
    
    if ubi['direction'] == Direction.Down:
        fxs = [x for x in fxs if x.mark == Mark.D]
        cnt = 1
        cur_lfx = fxs[0]
        for fx in fxs[1:]:
            if fx.low < cur_lfx.low:
                cnt += 1
                cur_lfx = fx

        if ubi['raw_bars'][-1].low < cur_lfx.low:
            v1 = '新低'
            v2 = f"第{cnt + 1}次"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('A股主要指数')
    bars = research.get_raw_bars(symbols[0], '15分钟', '20181101', '20210101', fq='前复权')

    signals_config = [{'name': cxt_ubi_end_V230816, 'freq': '日线', 'di': 1, 'max_overlap': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px') # type: ignore


if __name__ == '__main__':
    check()
