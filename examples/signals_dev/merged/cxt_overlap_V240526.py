import numpy as np
from collections import OrderedDict
from czsc.analyze import CZSC, BI, Direction
from czsc.utils import create_single_signal, get_sub_elements
from loguru import logger as log


def cxt_overlap_V240526(c: CZSC, **kwargs) -> OrderedDict:
    """K线收盘价与最近9笔的顶底分型重合次数

    参数模板："{freq}_顶底重合_支撑压力V240526"

    **信号逻辑：**

    1. 取最近 15 笔；
    2. 如果当前笔是向下笔，且向下笔的底分型区间与前面的15笔中存在 t 个以上的分型区间重合，则认为是并列二买；

    **信号列表：**

    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合1次_底重合0次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合0次_底重合1次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合0次_底重合2次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合1次_底重合1次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合0次_底重合0次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合0次_底重合3次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合2次_底重合0次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合3次_底重合0次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合2次_底重合1次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合1次_底重合2次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合4次_底重合0次_任意_0')
    - Signal('60分钟_顶底重合_支撑压力V240526_顶重合0次_底重合4次_任意_0')

    :param c: CZSC对象
    :param kwargs: 无
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_顶底重合_支撑压力V240526".split("_")
    v1 = "其他"
    if len(c.bi_list) < 11:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=1, n=9)
    last_bar = c.bars_raw[-1]
    # 找出向上笔的顶分型
    fxg = [x.fx_b for x in bis if x.direction == Direction.Up]
    fxd = [x.fx_b for x in bis if x.direction == Direction.Down]

    # 与 fxg 的重合次数
    overlap_count_g = sum([1 for fx in fxg if fx.low <= last_bar.close <= fx.high])
    overlap_count_d = sum([1 for fx in fxd if fx.low <= last_bar.close <= fx.high])
    v1 = f"顶重合{overlap_count_g}次"
    v2 = f"底重合{overlap_count_d}次"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def check():
    from czsc.connectors import research
    from czsc.traders.base import check_signals_acc

    symbols = research.get_symbols("A股主要指数")
    bars = research.get_raw_bars(symbols[0], "15分钟", "20181101", "20210101", fq="前复权")

    signals_config = [{"name": cxt_overlap_V240526, "freq": "60分钟"}]
    check_signals_acc(bars, signals_config=signals_config, height="780px", delta_days=5)  # type: ignore


if __name__ == "__main__":
    check()
