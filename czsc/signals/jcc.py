# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:17
describe: jcc 是 Japanese Candlestick Charting 的缩写
"""
from typing import List, Any
from collections import OrderedDict
from czsc import CZSC
from czsc.objects import Signal, RawBar
from czsc.utils import get_sub_elements


def jcc_san_xing_xian_V221023(c: CZSC, di=1, th=2) -> OrderedDict:
    """伞形线

    **有效信号列表：**

    * Signal('15分钟_D5TH200_伞形线_满足_上吊_任意_0')
    * Signal('15分钟_D5TH200_伞形线_满足_锤子_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 可调阈值，下影线超过实体的倍数，保留两位小数
    :return: 伞形线识别结果
    """
    th = int(th * 100)
    k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}_伞形线".split('_')

    # 判断对应K线是否满足：1) 下影线超过实体 th 倍；2）上影线小于实体 0.2 倍
    bar: RawBar = c.bars_raw[-di]
    # x1 - 上影线大小；x2 - 实体大小；x3 - 下影线大小
    x1, x2, x3 = bar.high - max(bar.open, bar.close), abs(bar.close - bar.open), min(bar.open, bar.close) - bar.low
    v1 = "满足" if x3 > x2 * th / 100 and x1 < 0.2 * x2 else "其他"

    # 判断K线趋势【这是一个可以优化的方向】
    v2 = "其他"
    if len(c.bars_raw) > 20 + di:
        left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=20)
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])
        gap = left_max - left_min

        if bar.low <= left_min + 0.25 * gap:
            v2 = "锤子"
        elif bar.high >= left_max - 0.25 * gap:
            v2 = "上吊"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_ten_mo_V221028(c: CZSC, di=1) -> OrderedDict:
    """吞没形态

    **吞没形态，有三条判别标准：**

    1. 在吞没形态之前，市场必须处在明确的上升趋势（看跌吞没形态）或下降趋势（看涨吞没形态）中，哪怕这个趋势只是短期的。
    2. 吞没形态由两条蜡烛线组成。其中第二根蜡烛线的实体必须覆盖第一根蜡烛线的实体（但是不一定需要吞没前者的上下影线）。
    3. 吞没形态的第二个实体应与第一个实体的颜色相反。

    **有效信号列表：**

    * Signal('15分钟_D1_吞没形态_满足_看跌吞没_任意_0')
    * Signal('15分钟_D1_吞没形态_满足_看涨吞没_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 吞没形态识别结果
    """

    k1, k2, k3 = f"{c.freq.value}_D{di}_吞没形态".split('_')
    bar1 = c.bars_raw[-di]
    bar2 = c.bars_raw[-di - 1]
    v1 = '满足' if bar1.high > bar2.high and bar1.low < bar2.low else "其他"

    v2 = "其他"
    if len(c.bars_raw) > 20 + di:
        left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=20)
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])
        gap = left_max - left_min

        if bar1.low <= left_min + 0.25 * gap and bar1.close > bar1.open \
                and bar1.close > bar2.high and bar1.open < bar2.low:
            v2 = "看涨吞没"

        elif bar1.high >= left_max - 0.25 * gap and bar1.close < bar1.open \
                and bar1.close < bar2.low and bar1.open > bar2.high:
            v2 = "看跌吞没"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_bai_san_bing_V221030(c: CZSC, di=1, th=0.5) -> OrderedDict:
    """白三兵

    **有效信号列表：**

    * Signal('15分钟_D3TH50_白三兵_满足_挺进_任意_0')
    * Signal('15分钟_D3TH50_白三兵_满足_受阻_任意_0')
    * Signal('15分钟_D3TH50_白三兵_满足_停顿_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di根K线 取倒数三根k线
    :param th: 可调阈值，上影线超过实体的倍数，保留两位小数
    :return: 白三兵识别结果
    """
    th = int(th * 100)
    k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}_白三兵".split('_')

    # 取三根K线 判断是否满足基础形态
    bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=3)
    bar1, bar2, bar3 = bars

    # 白色三兵由接连出现的三根白色蜡烛线组成的，收盘价依次上升;
    # 开盘价位于前一天的收盘价和开盘价之间;
    # 分为三种形态: 挺进形态,受阻形态,停顿形态
    v1 = "其他"
    if bar3.close > bar2.close > bar3.open > bar1.close > bar2.open > bar1.open:
        v1 = "满足"

    # 判断最后一根k线的上影线 是否小于实体0.5倍 x1 bar3上影线与bar3实体的比值,
    # 判断最后一根k线的收盘价,涨幅是否大于倒数第二根k线实体的0.2倍, x2 bar2到bar3的涨幅与bar2实体的比值,
    v2 = "其他"
    if v1 == "满足":
        x1 = (bar3.high - bar3.close) / (bar3.close - bar3.open) * 100
        x2 = (bar3.close - bar2.close) / (bar3.close - bar3.open) * 100
        if x1 > th:
            v2 = "受阻"
        elif x1 <= th and x2 <= 0.2*100:
            v2 = "停顿"
        elif x1 <= th and x2 > 0.2*100:
            v2 = "挺进"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s

