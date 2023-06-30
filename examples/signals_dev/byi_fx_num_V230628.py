import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
sys.path.insert(0, '../../..')
import math
import numpy as np
import pandas as pd
from collections import OrderedDict
from czsc import CZSC
from loguru import logger
from czsc.signals.tas import update_atr_cache
from czsc.utils import create_single_signal, get_sub_elements


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def byi_fx_num_V230628(c: CZSC, **kwargs) -> OrderedDict:
    """白仪前面下跌或上涨一笔次级别笔结构数量满足条件；贡献者：谌意勇

    参数模板："{freq}_D{di}笔分型数大于{num}_BE辅助V230628"

    **信号逻辑：**

    对于采用分型停顿或者分型验证开开仓，前一笔内部次级别笔结构尽量带结构，
    此信号函数为当分型笔数量判断大于 num 为满足条件

    **信号列表：**

    - Signal('15分钟_D1笔分型数大于4_BE辅助V230628_向下_满足_任意_0')
    - Signal('15分钟_D1笔分型数大于4_BE辅助V230628_向上_满足_任意_0')
    
    :param c: CZSC对象
    :param di: 从倒数第几笔开始检查
    :param num: 前笔内部次级别笔数量
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    num = int(kwargs.get('num', 4))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}笔分型数大于{num}_BE辅助V230628".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 1 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    bi = c.bi_list[-di]
    v1 = bi.direction.value
    v2 = "满足" if len(bi.fxs) >= num else "其他"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols('中证500成分股')
    symbol = symbols[10]
    bars = research.get_raw_bars(symbol, '15分钟', '20181101', '20210101', fq='前复权')
    signals_config = [{'name': byi_fx_num_V230628, 'freq': '15分钟', 'di': 1}]
    check_signals_acc(bars, signals_config=signals_config, height='780px')  # type: ignore


if __name__ == '__main__':
    check()
