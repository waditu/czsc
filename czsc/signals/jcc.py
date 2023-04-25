# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:17
describe: jcc 是 Japanese Candlestick Charting 的缩写，日本蜡烛图技术
"""
import numpy as np
from typing import List, Any
from collections import OrderedDict
from czsc import CZSC
from czsc.objects import Signal, RawBar, Direction
from czsc.utils import get_sub_elements


def jcc_san_xing_xian_V221023(c: CZSC, **kwargs) -> OrderedDict:
    """伞形线

    参数模板："{freq}_D{di}TH{th}_伞形线"

    **有效信号列表：**

    * Signal('15分钟_D5TH200_伞形线_满足_上吊_任意_0')
    * Signal('15分钟_D5TH200_伞形线_满足_锤子_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 可调阈值，下影线超过实体的倍数，保留两位小数
    :return: 伞形线识别结果
    """
    di = int(kwargs.get("di", 1))
    th = float(kwargs.get("th", 2))
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


def jcc_ten_mo_V221028(c: CZSC, **kwargs) -> OrderedDict:
    """吞没形态；贡献者：琅盎

    参数模板："{freq}_D{di}_吞没形态"

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
    di = int(kwargs.get("di", 1))

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

        if bar1.low <= left_min + 0.25 * gap and bar1.close > bar1.open and bar1.close > bar2.high and bar1.open < bar2.low:
            v2 = "看涨吞没"

        elif bar1.high >= left_max - 0.25 * gap and bar1.close < bar1.open and bar1.close < bar2.low and bar1.open > bar2.high:
            v2 = "看跌吞没"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_wu_yun_gai_ding_V221101(c: CZSC, **kwargs) -> OrderedDict:
    """乌云盖顶，贡献者：魏永超

    参数模板："{freq}_D{di}Z{z}TH{th}_乌云盖顶"

    **信号逻辑：**

    1. 当前的走势属于上升趋势，或者水平调整区间的顶部。
    2. 前一天是坚挺的白色实体，也就是大阳线。
    3. 当天跳空高开，开盘价高于前一天的最高价。
    4. 当天收盘在最低价附近，且明显向下扎入前一天的K线实体内。一般要求当天收盘价低于前一天阳线实体的50%。

    **信号列表：**

    * Signal('日线_D5Z500TH50_乌云盖顶_满足_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param z: 可调阈值，前一天上涨K线实体的最低涨幅（收盘价-开盘价）/开盘价*10000，500表示至少涨5%
    :param th: 可调阈值，当天收盘价跌入前一天实体高度的百分比
    :return: 乌云盖顶识别结果
    """
    di = int(kwargs.get("di", 1))
    z = int(kwargs.get("z", 500))
    th = int(kwargs.get("th", 50))

    k1, k2, k3 = f"{c.freq.value}_D{di}Z{z}TH{th}_乌云盖顶".split('_')
    v1 = "其他"

    if len(c.bars_raw) > di + 10:

        # 判断前一天K线是否满足：实体涨幅 大于 z
        pre_bar: RawBar = c.bars_raw[-di - 1]
        z0 = ((pre_bar.close - pre_bar.open) / pre_bar.open) * 10000
        flag_z = z0 > z
        # 判断当天K线是否满足：1) 跳空高开；2）收盘低于前一天实体th位置
        bar: RawBar = c.bars_raw[-di]
        flag_ho = bar.open > pre_bar.high
        flag_th = bar.close < (pre_bar.close + pre_bar.open) * (th / 100)

        # 上升趋势的高点，或者平台整理的高点
        if len(c.bars_raw) > di + 10:
            left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di + 2, n=10)
            left_max_close = max([x.close for x in left_bars])

            flag_up = pre_bar.close >= left_max_close

            v1 = "满足" if flag_z and flag_ho and flag_th and flag_up else "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def jcc_ci_tou_V221101(c: CZSC, **kwargs) -> OrderedDict:
    """刺透形态

    参数模板："{freq}_D{di}Z{z}TH{th}_刺透形态"

    **信号列表：**

    - Signal('15分钟_D1Z100TH50_刺透形态_满足_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param z: 可调阈值，前一天下跌K线实体的最低跌幅（收盘价-开盘价）/开盘价*10000，500表示至少跌5%
    :param th: 可调阈值，当天收盘价涨超前一天实体高度的百分比
    :return: 刺绣形态识别结果
    """
    di = int(kwargs.get("di", 1))
    z = int(kwargs.get("z", 100))
    th = int(kwargs.get("th", 50))

    k1, k2, k3 = f"{c.freq.value}_D{di}Z{z}TH{th}_刺透形态".split('_')

    if len(c.bars_raw) < di + 15:
        v1 = "其他"
    else:
        bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=2)
        c1 = bar2.close < bar2.open and 1 - bar2.close / bar2.open > z / 10000
        c2 = bar1.open < bar2.low and bar1.close > bar2.close + (bar2.open - bar2.close) * (th / 100)

        v1 = "满足" if c1 and c2 else "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def jcc_san_fa_V20221118(c: CZSC, **kwargs) -> OrderedDict:
    """上升&下降三法

    参数模板："{freq}_D{di}K_三法A"

    **上升三法形态由以下几个方面组成：**

    1. 首先出现的是一根长长的阳线。
    2.在这根长长的阳线之后，紧跟着一群依次下降的或者横向延伸的小实体蜡烛线。这群小实体蜡烛线的理想数目是3根，但是2根或者3根以上
    也是可以接受的，条件是：只要这群小实体蜡烛线基本上都局限在前面长长的白色蜡烛线的高点到低点的价格范围之内。小蜡烛线既可以是
    白色的，也可以是黑色的，不过，黑色蜡烛线最理想。
    3. 最后一天应当是一根坚挺的白色实体蜡烛线，并且它的收盘价高于前一天的收盘价，同时其开盘价应当高于前一天的收盘价。

    **下降三法形态由以下几个方面组成：**

    1.下降三法形态与上升三法形态完全是对等的，只不过方向相反。这类形态的形成过程如下：
    2.市场应当处在下降趋势中，首先出场的是一根长长的黑色蜡烛线。在这根黑色蜡烛线之后，跟随着大约3根依次上升的小蜡烛线，并且这群
    蜡烛线的实体都局限在第一根蜡烛线的范围之内（包括其上、下影线）。
    3.最后一天，开盘价应低于前一天的收盘价，并且收盘价应低于第一根黑色蜡烛线的收盘价。本形态与看跌旗形或看跌三角旗形形态相似。
    本形态的理想情形是，在第一根长实体之后，小实体的颜色与长实体相反。

    **信号列表：**

    - Signal('60分钟_D1K_三法A_上升三法_8K_任意_0')
    - Signal('60分钟_D1K_三法A_上升三法_6K_任意_0')
    - Signal('60分钟_D1K_三法A_上升三法_5K_任意_0')
    - Signal('60分钟_D1K_三法A_下降三法_5K_任意_0')
    - Signal('60分钟_D1K_三法A_下降三法_6K_任意_0')
    - Signal('60分钟_D1K_三法A_上升三法_7K_任意_0')
    - Signal('60分钟_D1K_三法A_下降三法_7K_任意_0')
    - Signal('60分钟_D1K_三法A_下降三法_8K_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 上升及下降三法形态识别结果
    """
    di = int(kwargs.get("di", 1))

    def __check_san_fa(bars: List[RawBar]):
        if len(bars) < 5:
            return "其他"

        # 条件1：最近一根和最后一根K线同向
        if bars[-1].close > bars[-1].open and bars[0].close > bars[0].open and bars[-1].close > bars[0].high:
            c1 = "上升"
        elif bars[-1].close < bars[-1].open and bars[0].close < bars[0].open and bars[-1].close < bars[0].low:
            c1 = "下降"
        else:
            c1 = "其他"

        # 条件2：中间K线的高低点要求
        hhc = max([x.close for x in bars[1:-1]])
        llc = min([x.close for x in bars[1:-1]])
        hhv = max([x.high for x in bars[1:-1]])
        llv = min([x.low for x in bars[1:-1]])
        if c1 == "上升" and bars[-1].close > hhv > bars[0].high and llv > bars[0].open and bars[0].close > hhc:
            c2 = "上升三法"
        elif c1 == "下降" and bars[0].low > llv > bars[-1].close and hhv < bars[0].open and bars[0].close < llc:
            c2 = "下降三法"
        else:
            c2 = "其他"

        return c2

    k1, k2, k3 = f"{c.freq.value}_D{di}K_三法A".split('_')

    for n in (5, 6, 7, 8):
        _bars = get_sub_elements(c.bars_raw, di=di, n=n)
        v1 = __check_san_fa(_bars)
        if v1 != "其他":
            v2 = f"{n}K"
            break
        else:
            v2 = "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_san_fa_V20221115(c: CZSC, **kwargs) -> OrderedDict:
    """上升&下降三法；贡献者：琅盎

    参数模板："{freq}_D{di}K_三法"

    **上升三法形态由以下几个方面组成：**

    1. 首先出现的是一根长长的阳线。
    2.在这根长长的阳线之后，紧跟着一群依次下降的或者横向延伸的小实体蜡烛线。这群小实体蜡烛线的理想数目是3根，但是2根或者3根以上
    也是可以接受的，条件是：只要这群小实体蜡烛线基本上都局限在前面长长的白色蜡烛线的高点到低点的价格范围之内。小蜡烛线既可以是
    白色的，也可以是黑色的，不过，黑色蜡烛线最理想。
    3. 最后一天应当是一根坚挺的白色实体蜡烛线，并且它的收盘价高于前一天的收盘价，同时其开盘价应当高于前一天的收盘价。

    **下降三法形态由以下几个方面组成：**

    1.下降三法形态与上升三法形态完全是对等的，只不过方向相反。这类形态的形成过程如下：
    2.市场应当处在下降趋势中，首先出场的是一根长长的黑色蜡烛线。在这根黑色蜡烛线之后，跟随着大约3根依次上升的小蜡烛线，并且这群
    蜡烛线的实体都局限在第一根蜡烛线的范围之内（包括其上、下影线）。
    3.最后一天，开盘价应低于前一天的收盘价，并且收盘价应低于第一根黑色蜡烛线的收盘价。本形态与看跌旗形或看跌三角旗形形态相似。
    本形态的理想情形是，在第一根长实体之后，小实体的颜色与长实体相反。

    **信号列表：**

    * Signal('60分钟_D1K_三法_满足_上升三法_任意_0')
    * Signal('60分钟_D1K_三法_满足_下降三法_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param zdf: 倒1和倒数第5根K线涨跌幅，单位 BP
    :return: 上升及下降三法形态识别结果
    """
    di = int(kwargs.get("di", 1))
    zdf = int(kwargs.get("zdf", 500))

    k1, k2, k3 = f"{c.freq.value}_D{di}K_三法".split('_')
    bar6, bar5, bar4, bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=6)

    bar1_zdf = abs((bar2.close - bar1.close) / bar2.close) * 10000
    bar5_zdf = abs((bar6.close - bar5.close) / bar6.close) * 10000
    max_high = max(bar2.high, bar3.high, bar4.high)
    min_low = min(bar2.low, bar3.low, bar4.low)

    v1 = '满足' if bar1_zdf >= zdf and bar5_zdf > zdf and bar5.high > max_high else "其他"

    if bar5.close > bar5.open and bar1.close > bar1.open and bar1.close > bar5.high and bar1.close > max_high and bar1.open > bar2.close:
        v2 = "上升三法"
    elif bar5.close < bar5.open and bar1.close < bar1.open and bar1.close < bar5.low and bar1.close < min_low and bar1.open < bar2.close:
        v2 = "下降三法"
    else:
        v2 = "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_xing_xian_V221118(c: CZSC, **kwargs) -> OrderedDict:
    """星形态

    参数模板："{freq}_D{di}TH{th}_星形线"

    **星形态，判断标准：**

    1.启明星：

        蜡烛线1。一根长长的黑色实体，形象地表明空头占据主宰地位
        蜡烛线2。一根小小的实体，并且它与前一根实体之间不相接触（这两条蜡烛线组成了基本的星线形态）。小实体意味着卖方丧失了驱动市场走低的能力
        蜡烛线3。一根白色实体，它明显地向上推进到了第一个时段的黑色实体之内，标志着启明星形态的完成。这表明多头已经夺回了主导权

        在理想的启明星形态中，第二根蜡烛线（即星线）的实体，与第三根蜡烛线的实体之间有价格跳空。根据我的经验，即使没有这个价格跳空，
        似乎也不会削减启明星形态的技术效力。其决定性因素是，第二根蜡烛线应为纺锤线，同时第三根蜡烛线应显著深入到第一根黑色蜡烛线内部

    2.黄昏星：

        a. 如果第一根与第二根蜡烛线，第二根与第三根蜡烛线的实体之间不存在重叠。
        b. 如果第三根蜡烛线的收市价向下深深扎入第一根蜡烛线的实体内部。
        c. 如果第一根蜡烛线的交易量较小，而第三根蜡烛线的交易量较大。这表明之前趋势的驱动力正在减弱，新趋势方向的驱动力正在加强

    3.十字黄昏星

        在常规的黄昏星形态中，第二根蜡烛线具有较小的实体，如果不是较小的实体，而是一个十字线，则称为十字黄昏星形态
    4.十字启明星

        在启明星形态中，如果其星线（即三根蜡烛线中的第二根蜡烛线）是一个十字线，则成为十字启明星形态

    **信号列表：**

    - Signal('60分钟_D1TH2_星形线_黄昏星_任意_任意_0')
    - Signal('60分钟_D1TH2_星形线_启明星_任意_任意_0')
    - Signal('60分钟_D1TH2_星形线_启明星_中间十字_任意_0')
    - Signal('60分钟_D1TH2_星形线_黄昏星_中间十字_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 左侧实体是当前实体的多少倍
    :return: 星形线识别结果
    """
    di = int(kwargs.get("di", 2))
    th = int(kwargs.get("th", 2))
    assert di >= 1

    k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}_星形线".split('_')

    bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=3)
    x3 = abs(bar3.close - bar3.open)
    x2 = abs(bar2.close - bar2.open)
    x1 = abs(bar1.close - bar1.open)

    v1 = "其他"
    if bar3.high > bar2.high < bar1.high and bar3.low > bar2.low < bar1.low:
        """
        方向向下，启明星
            - 蜡烛线3。一根长长的黑色实体，形象地表明空头占据主宰地位。
            - 蜡烛线2。一根小小的实体，并且它与前一根实体之间不相接触（这两条蜡烛线组成了基本的星线形态）。小实体意味着卖方丧失了驱动市场走低的能力。
            - 蜡烛线1。一根白色实体，它明显地向上推进到了第一个时段的黑色实体之内，标志着启明星形态的完成。这表明多头已经夺回了主导权
        """
        if bar3.close < bar3.open and x2 * th < x3 < x2 + x1 and bar1.close > bar1.open > max(bar2.close, bar2.open):
            v1 = "启明星"

    elif bar3.high < bar2.high > bar1.high and bar3.low < bar2.low > bar1.low:
        """
        方向向上，黄昏星。
            1. 如果第一根与第二根蜡烛线，第二根与第三根蜡烛线的实体之间不存在重叠。
            2. 如果第三根蜡烛线的收市价向下深深扎入第一根蜡烛线的实体内部。
            3. 如果第一根蜡烛线的交易量较小，而第三根蜡烛线的交易量较大。这表明之前趋势的驱动力正在减弱，新趋势方向的驱动力正在加强
        """
        if bar3.close > bar3.open and x2 * th < x3 < x2 + x1 and bar1.close < bar1.open < min(bar2.close, bar2.open):
            v1 = "黄昏星"

    v2 = "中间十字" if bar2.close == bar2.open else "任意"
    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_fen_shou_xian_V20221113(c: CZSC, **kwargs) -> OrderedDict:
    """分手线：分手形态是一个中继形态；贡献者：琅盎

    参数模板："{freq}_D{di}K_分手线"

    **分手线形态，有三条判断标准 **

    1.分手线是由二根开盘价相等、运动方向相反的K线组成，因此也称分离线。
    2.上升分手线出现在上升途中，由一阴一阳两根开盘价相等的K线组成，属于上涨持续形态；如果下跌趋势发展了较长时间之后出现上涨分手线，后市可能上涨应极积关注。
    3.下跌分手线出现在下跌途中，由一阳一阴两根开盘价相等的K线组成，属于下跌持续形态；如果上涨趋势发展了较长时间之后出现下跌分手线，后市可能下跌应及时出场。

    **有效信号列表： **

    - Signal('60分钟_D1K_分手线_满足_上升分手_任意_0')
    - Signal('60分钟_D1K_分手线_满足_下跌分手_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di根K线，加上这个参数就可以不用借助缓存就可以回溯
    :param zdf: 可调阈值，涨跌幅，单位 BP
    :return: 分离形态识别结果
    """
    di = int(kwargs.get('di', 1))
    zdf = int(kwargs.get('zdf', 300))

    k1, k2, k3 = f"{c.freq.value}_D{di}K_分手线".split('_')
    bar1 = c.bars_raw[-di]
    bar2 = c.bars_raw[-di - 1]

    # 条件
    v1 = '满足' if bar1.open == bar2.open and bar1.close < bar2.low or bar1.close > bar2.high else "其他"

    # 判断K线趋势【这是一个可以优化的方向】
    v2 = "其他"
    if len(c.bars_raw) > 20 + di:
        left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=20)
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])
        gap = left_max - left_min

        if bar1.low <= left_min + 0.25 * gap and bar1.open == bar2.open and bar1.close < bar2.low \
                and bar2.close > bar2.open and (bar2.close - bar1.close) / bar2.close * 10000 > zdf:

            v2 = "下跌分手"

        elif bar1.high >= left_max - 0.25 * gap and bar1.open == bar2.open and bar1.close > bar2.high \
                and bar2.close < bar2.open and (bar1.close - bar2.close) / bar2.close * 10000 > zdf:
            v2 = "上升分手"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_zhu_huo_xian_V221027(c: CZSC, **kwargs) -> OrderedDict:
    """烛火线，贡献者：琅盎

    参数模板："{freq}_D{di}T{th}F{zf}_烛火线"

    **信号列表： **

    - Signal('60分钟_D1T200F500_烛火线_满足_风中烛_任意_0')
    - Signal('60分钟_D1T200F500_烛火线_满足_箭在弦_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 可调阈值，下影线超过实体的倍数，保留两位小数
    :param zf: 可调阈值，震荡幅度大小，单位 BP
    :return: 烛火线识别结果
    """
    di = int(kwargs.get('di', 1))
    th = float(kwargs.get('th', 2))
    zf = int(kwargs.get('zf', 500))

    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}F{zf}_烛火线".split('_')
    bar: RawBar = c.bars_raw[-di]
    x1, x2, x3 = bar.high - max(bar.open, bar.close), abs(bar.close - bar.open), min(bar.open, bar.close) - bar.low
    zf_min = (bar.high - bar.low) / bar.low * 10000 >= zf

    # 下影线大于实体的2倍，上影线小于实体的0.2倍，上影线小于下影线0.5倍，振幅大于等于5%
    v1 = "满足" if x1 > x2 * th / 100 and x3 < 0.2 * x2 and x3 < 0.5 * x1 and zf_min else "其他"
    v2 = "其他"
    if len(c.bars_raw) > 20 + di:
        left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=20)
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])
        gap = left_max - left_min

        if bar.low <= left_min + 0.25 * gap:
            v2 = "箭在弦"
        elif bar.high >= left_max - 0.25 * gap:
            v2 = "风中烛"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_yun_xian_V221118(c: CZSC, **kwargs) -> OrderedDict:
    """孕线形态

    参数模板："{freq}_D{di}_孕线"

    ** 信号逻辑：**
    二日K线模式，分多头孕线与空头孕线，两者相反，以多头孕线为例，
    在下跌趋势中，第一日K线长阴，第二日开盘和收盘价都在第一日价格
    振幅之内，为阳线，预示趋势反转，股价上升

    **有效信号列表：**

    - Signal('60分钟_D1_孕线_看空_任意_任意_0')
    - Signal('60分钟_D1_孕线_看多_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 孕线识别结果
    """
    di = int(kwargs.get('di', 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}_孕线".split('_')
    bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=2)

    v1 = "其他"
    if bar2.solid > max(bar2.upper, bar2.lower) and bar1.solid < max(bar1.upper, bar1.lower):
        if bar2.close > bar1.close > bar2.open and bar2.close > bar1.open > bar2.open:
            v1 = "看空"

        if bar2.close < bar1.close < bar2.open and bar2.close < bar1.open < bar2.open:
            v1 = "看多"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def jcc_ping_tou_V221113(c: CZSC, **kwargs) -> OrderedDict:
    """平头形态，贡献者：平凡

    参数模板："{freq}_D{di}TH{th}_平头形态"

    **平头形态，判断标准：**

    1. 平头形态是由几乎具有相同水平的最高点的两根蜡烛线组成的， 或者是由几乎具有相同的最低点的两根蜡烛线组成的。
    2. 在理想情 况下，平头形态应当由前一根长实体蜡烛线与后一根小实体蜡烛线组合而成

    **有效信号列表：**

    * Signal('15分钟_D2TH20_平头形态_满足_平头顶部_任意_0')
    * Signal('15分钟_D2TH20_平头形态_满足_平头底部_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di根K线
    :param th: 百分比，右侧K线的高/低点与当前K线的高/低点之间的差距比例，单位 BP
    :return: 平头形态识别结果
    """
    di = int(kwargs.get('di', 2))
    th = int(kwargs.get('th', 100))

    k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}_平头形态".split('_')
    bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=2)
    if abs(bar2.low - bar1.low) * 10000 / max(bar2.low, bar1.low) < th:
        v1 = "底部"
    elif abs(bar2.high - bar1.high) * 10000 / max(bar2.high, bar1.high) < th:
        v1 = '顶部'
    else:
        v1 = "其他"

    v2 = '实体标准' if bar2.solid > max(bar1.solid, bar1.upper) else "任意"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_zhuo_yao_dai_xian_v221113(c: CZSC, **kwargs) -> OrderedDict:
    """捉腰带线，贡献者：平凡

    参数模板："{freq}_D{di}L{left}_捉腰带线"

    **捉腰带线判别标准：**

    捉腰带形态是由单独一根蜡烛线构成的。看涨捉腰带形态是一 根坚挺的白色蜡烛线，其开市价位于时段的最低点
    （或者，这根蜡烛线只有极短的下影线），然后市场一路上扬，收市价位于或接近本时段的最高

    **有效信号列表：**

    - Signal('60分钟_D1L20_捉腰带线_看跌_光头阴线_任意_0')
    - Signal('60分钟_D1L20_捉腰带线_看多_光脚阳线_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param left: 从di向左数left根K线
    :return: 捉腰带线识别结果
    """
    di = int(kwargs.get('di', 1))
    left = int(kwargs.get('left', 20))

    k1, k2, k3 = f"{c.freq.value}_D{di}L{left}_捉腰带线".split('_')
    v1, v2 = "其他", "其他"

    bar: RawBar = c.bars_raw[-di]
    # x1 - 上影线大小；x2 - 实体大小；x3 - 下影线大小
    x1, x2, x3 = bar.high - max(bar.open, bar.close), abs(bar.close - bar.open), min(bar.open, bar.close) - bar.low

    if len(c.bars_raw) > left + di:
        left_bars: List[RawBar] = c.bars_raw[-left - di:-di]
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])

        if bar.low < left_min:
            if bar.close > bar.open and x3 == 0:
                v1 = "看多"
                v2 = "光脚阳线"
        elif bar.high > left_max:
            if bar.close < bar.open and x1 == 0:
                v1 = "看跌"
                v2 = "光头阴线"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_two_crow_V221108(c: CZSC, **kwargs):
    """两只乌鸦

    参数模板："{freq}_D{di}K_两只乌鸦"

    **信号逻辑：**

    1. 市场本来处于上升趋势中；
    2. 第一根K线为长阳；
    3. 第二根K线跳空高开低走，收于前收盘价上方；
    4. 第三根K线同样高开低走，包含第二根K线，收于第一根K线收盘价上方。

    **信号列表：**

    - Signal('60分钟_D1K_两只乌鸦_看空_任意_任意_0')

    :param c: CZSC对象
    :param di: 连续倒di根K线
    :return:
    """
    di = int(kwargs.get('di', 1))
    s = OrderedDict()
    k1, k2, k3 = f"{c.freq.value}_D{di}K_两只乌鸦".split('_')
    bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=3)

    c1 = bar3.close > bar3.open and bar3.solid > max(bar3.upper, bar3.lower)
    c2 = bar2.open > bar2.close > bar3.high
    c3 = bar1.close < bar1.open and bar1.close < bar2.close
    v1 = '看空' if c1 and c2 and c3 else '其他'

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def jcc_three_crow_V221108(c: CZSC, **kwargs):
    """三只乌鸦，贡献者：马鸣

    参数模板："{freq}_D{di}_三只乌鸦"

    **信号逻辑：**

    1、连续出现了三根依次下降的黑色蜡烛线，每根黑色蜡烛线的开市价处于前一个实体的范围之内，则构成了所谓的常规三只乌鸦形态；
    2、三只乌鸦形态中的第二根和第三根蜡烛线都开市于之前的实体之下构成更加疲软的三只乌鸦形态；
    3、允许有上影线，但是不能出现包含关系；
    4、允许有下影线，但是最低价接近收盘价；
    5、该信号出现在阶段性顶部。

    **信号列表：**

    - Signal('30分钟_D1_三只乌鸦_满足_常规_任意_0')
    - Signal('30分钟_D1_三只乌鸦_满足_加强_任意_0')
    - Signal('30分钟_D1_三只乌鸦_满足_半加强_任意_0')

    :param c: CZSC对象
    :param di: 连续倒di根K线
    :return:
    """
    di = int(kwargs.get('di', 1))
    s = OrderedDict()
    k1, k2, k3 = f"{c.freq.value}_D{di}_三只乌鸦".split('_')
    signal = Signal(k1=k1, k2=k2, k3=k3, v1='其他', v2='其他')
    s[signal.key] = signal.value

    # 逻辑判断：
    # 1) 三根K线均收盘价 < 开盘价；
    # 2) 三根K线收盘价越来越低；
    # 3) 三根K线最高价越来越低；
    # 4) 三根K线下影线小于实体一半（可调节）；
    # 5) 三根K线上影线小于实体

    bar1 = c.bars_raw[-di]
    bar2 = c.bars_raw[-di - 1]
    bar3 = c.bars_raw[-di - 2]

    if len(c.bars_raw) > 20 + 3:
        left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di=3, n=20)
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])
        gap = left_max - left_min

        if bar3.high >= left_max - 0.25 * gap:
            pass
        else:
            return s

    if bar1.close < bar1.open and bar2.close < bar2.open and bar3.open > bar3.close > bar2.close > bar1.close \
            and bar3.high > bar2.high > bar1.high:

        if (bar1.close - bar1.low) < 0.5 * (bar1.open - bar1.close) \
                and (bar2.close - bar2.low) < 0.5 * (bar2.open - bar2.close) \
                and (bar3.close - bar3.low) < 0.5 * (bar3.open - bar3.close) \
                and (bar1.high - bar1.open) < (bar1.open - bar1.close) \
                and (bar2.high - bar2.open) < (bar2.open - bar2.close) \
                and (bar3.high - bar3.open) < (bar3.open - bar3.close):

            if bar2.close <= bar1.open <= bar2.open and bar3.close <= bar2.open <= bar3.open:
                v1 = '满足'
                v2 = '常规'
            elif bar1.open < bar2.close and bar2.open < bar3.close:
                v1 = '满足'
                v2 = '加强'
            elif (bar2.close <= bar1.open <= bar2.open and bar3.open < bar3.close) or \
                    (bar3.close <= bar2.open <= bar3.open and bar1.open < bar2.close):
                v1 = '满足'
                v2 = '半加强'
            else:
                v1 = '其他'
                v2 = '其他'
        else:
            v1 = '其他'
            v2 = '其他'
    else:
        v1 = "其他"
        v2 = '其他'

    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value

    return s


# def jcc_bai_san_bin_V221030(c: CZSC, di=1, th=0.5, **kwargs) -> OrderedDict:
#     """白三兵；贡献者：鲁克林
#
#     **信号逻辑：**
#
#     1. 白三兵由接连出现的三根白色蜡烛线组成的，收盘价依次上升;
#     2. 开盘价位于前一天的收盘价和开盘价之间;
#     3. 分为三种形态: 挺进形态,受阻形态,停顿形态
#
#     **信号列表：**
#
#     * Signal('15分钟_D3TH50_白三兵_满足_挺进_任意_0')
#     * Signal('15分钟_D3TH50_白三兵_满足_受阻_任意_0')
#     * Signal('15分钟_D3TH50_白三兵_满足_停顿_任意_0')
#
#     :param c: CZSC 对象
#     :param di: 倒数第di根K线
#     :param th: 可调阈值，上影线超过实体的倍数，保留两位小数
#     :return: 白三兵识别结果
#     """
#     th = int(th * 100)
#     k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}_白三兵".split('_')
#
#     # 取三根K线 判断是否满足基础形态
#     bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=3)
#     bar1, bar2, bar3 = bars
#
#     v1 = "满足" if bar3.close > bar2.close > bar3.open > bar1.close > bar2.open > bar1.open else "其他"
#     # 判断最后一根k线的上影线 是否小于实体0.5倍 x1 bar3上影线与bar3实体的比值,
#     # 判断最后一根k线的收盘价,涨幅是否大于倒数第二根k线实体的0.2倍, x2 bar2到bar3的涨幅与bar2实体的比值,
#     v2 = "其他"
#     if v1 == "满足":
#         x1 = (bar3.high - bar3.close) / (bar3.close - bar3.open) * 100
#         x2 = (bar3.close - bar2.close) / (bar3.close - bar3.open) * 100
#         if x1 > th:
#             v2 = "受阻"
#         elif x1 <= th and x2 <= 0.2*100:
#             v2 = "停顿"
#         elif x1 <= th and x2 > 0.2*100:
#             v2 = "挺进"
#
#     s = OrderedDict()
#     signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
#     s[signal.key] = signal.value
#     return s


# def jcc_three_soldiers_V221030(c: CZSC, di=1, th=1, ri=0.2, **kwargs) -> OrderedDict:
#     """白三兵，贡献者：鲁克林
#
#     **信号逻辑：**
#
#     1. 三根K线均收盘价 > 开盘价；且开盘价越来越高； 且收盘价越来越高；
#     2. 三根K线的开盘价都在前一根K线的实体范围之间
#     3. 倒1K上影线与倒1K实体的比值th_cal小于th
#     4. 倒1K涨幅与倒2K涨幅的比值ri_cal大于ri
#
#     **信号列表：**
#
#     - Signal('60分钟_D1T100R20_白三兵_满足_挺进_任意_0')
#     - Signal('60分钟_D1T100R20_白三兵_满足_受阻_任意_0')
#     - Signal('60分钟_D1T100R20_白三兵_满足_停顿_任意_0')
#
#     :param c: CZSC 对象
#     :param di: 倒数第di跟K线 取倒数三根k线
#     :param th: 可调阈值，倒1K上影线与倒1K实体的比值，保留两位小数
#     :param ri: 可调阈值，倒1K涨幅与倒2K涨幅的比值，保留两位小数
#     :return: 白三兵识别结果
#     """
#     # th = 倒1K上涨阻力； ri = 倒1K相对涨幅；
#     th = int(th * 100)
#     ri = int(ri * 100)
#
#     k1, k2, k3 = f"{c.freq.value}_D{di}T{th}R{ri}_白三兵".split('_')
#
#     # 先后顺序 bar3 <-- bar2 <-- bar1
#     bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=3)
#
#     if bar3.open < bar3.close and bar2.open < bar2.close \
#             and bar1.close > bar1.open > bar2.open > bar3.open \
#             and bar1.close > bar2.close > bar3.close:
#         v1 = "满足"
#         th_cal = (bar1.high - bar1.close) / (bar1.close - bar1.open) * 100
#         ri_cal = (bar1.close - bar2.close) / (bar2.close - bar3.close) * 100
#
#         if ri_cal > ri:
#             if th_cal < th:
#                 v2 = "挺进"
#             else:
#                 v2 = "受阻"
#         else:
#             v2 = "停顿"
#     else:
#         v1 = "其他"
#         v2 = "其他"
#
#     s = OrderedDict()
#     signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
#     s[signal.key] = signal.value
#     return s


def check_szx(bar: RawBar, th: int = 10, **kwargs) -> bool:
    """判断十字线

    :param bar:
    :param th: 可调阈值，(h -l) / (c - o) 的绝对值大于 th, 判定为十字线
    :return:
    """
    if bar.close == bar.open and bar.high != bar.low:
        return True

    if bar.close != bar.open and (bar.high - bar.low) / abs(bar.close - bar.open) > th:
        return True
    else:
        return False


def jcc_szx_V221111(c: CZSC, **kwargs) -> OrderedDict:
    """十字线

    参数模板："{freq}_D{di}TH{th}_十字线"

    **信号逻辑：**

    1， 十字线定义，(h -l) / (c - o) 的绝对值大于 th，或 c == o
    2. 长腿十字线，上下影线都很长；墓碑十字线，上影线很长；蜻蜓十字线，下影线很长；

    **信号列表：**

    - Signal('60分钟_D1TH10_十字线_蜻蜓十字线_北方_任意_0')
    - Signal('60分钟_D1TH10_十字线_十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_蜻蜓十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_墓碑十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_长腿十字线_任意_任意_0')
    - Signal('60分钟_D1TH10_十字线_十字线_北方_任意_0')
    - Signal('60分钟_D1TH10_十字线_墓碑十字线_北方_任意_0')
    - Signal('60分钟_D1TH10_十字线_长腿十字线_北方_任意_0')

    :param c: CZSC 对象
    :param kwargs:
        - di: 倒数第di跟K线
        - th: 可调阈值，(h -l) / (c - o) 的绝对值大于 th, 判定为十字线
    :return: 十字线识别结果
    """
    di = int(kwargs.get("di", 1))
    th = int(kwargs.get("th", 10))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}TH{th}_十字线".split("_")
    if len(c.bars_raw) < di + 10:
        v1 = "其他"
        v2 = "其他"
    else:
        bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=2)
        if check_szx(bar1, th):
            upper = bar1.upper
            solid = bar1.solid
            lower = bar1.lower

            if lower > upper * 2:
                v1 = "蜻蜓十字线"
            elif lower == 0 or lower < solid:
                v1 = "墓碑十字线"
            elif lower > bar2.solid and upper > bar2.solid:
                v1 = "长腿十字线"
            else:
                v1 = "十字线"
        else:
            v1 = "其他"

        v2 = "北方" if bar2.close > bar2.open and bar2.solid > (bar2.upper + bar2.lower) * 3 else "任意"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_san_szx_V221122(c: CZSC, **kwargs) -> OrderedDict:
    """三星形态

    参数模板："{freq}_D{di}T{th}_三星"

    **信号逻辑：**

    1. 最近五根K线中出现三个十字星

    **信号列表：**

    - Signal('15分钟_D1T10_三星_满足_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 可调阈值，(h -l) / (c - o) 的绝对值大于 th, 判定为十字线
    :return: 识别结果
    """
    di = int(kwargs.get("di", 1))
    th = int(kwargs.get("th", 10))
    k1, k2, k3 = f"{c.freq.value}_D{di}T{th}_三星".split("_")
    v1 = "其他"
    if len(c.bars_raw) > 6 + di:
        bars = get_sub_elements(c.bars_raw, di, n=5)
        if sum([check_szx(bar, th) for bar in bars]) >= 3:
            v1 = "满足"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def jcc_fan_ji_xian_V221121(c: CZSC, **kwargs) -> OrderedDict:
    """反击线；贡献者：lynxluu

    参数模板："{freq}_D{di}_反击线"

    **信号逻辑：**

    1. 反击线分两种，看涨反击线和看跌反击线，共同特点是两根K线收盘价接近;
    2. 看涨反击线，下降趋势，先阴线，后大幅低开收阳线;
    3. 看跌反击线，上升趋势，先阳线，后大幅高开收阴线;

    **信号列表：**

    * Signal('15分钟_D1_反击线_满足_看涨反击线_任意_0')
    * Signal('15分钟_D1_反击线_满足_看跌反击线_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di根K线 取倒数三根k线
    :return: 反击线识别结果
    """
    di = int(kwargs.get("di", 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}_反击线".split('_')

    if len(c.bars_raw) < 20 + di:
        v1 = "其他"
        v2 = "任意"
    else:
        # 取前20根K线，计算区间高度gap
        left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=20)
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])
        gap = left_max - left_min

        # 取三根K线 判断是否满足基础形态
        bar1, bar2, bar3 = left_bars[-3:]
        v1 = "其他"

        if bar2.close != bar2.open:
            # 大幅高/低开 高/低开幅度除以bar2实体大于1； x1 >= 1
            # 收盘价接近 bar2和bar3的收盘价差值 除以bar2实体小于0.1； x2 <= 0.1
            # bar2实体除以前20根K线的区间的比值，此值影响比较大；x3 >= 0.02
            bar2h = abs(bar2.close - bar2.open)
            x1 = abs(bar3.open - bar2.close) / bar2h
            x2 = abs(bar3.close - bar2.close) / bar2h
            x3 = bar2h / gap

            if x1 >= 1 and x2 <= 0.1 and x3 >= 0.02:
                v1 = "满足"

        # 看涨：下降趋势； bar2阴线； bar3低开；
        # 看跌：上升趋势； bar2阳线； bar3高开；
        v2 = "任意"
        if v1 == '满足':
            if bar1.low <= left_min + 0.25 * gap and bar1.close > bar2.close and bar2.open > bar2.close > bar3.open:
                v2 = "看涨反击线"

            elif bar1.high >= left_max - 0.25 * gap and bar2.close > bar1.close and bar3.open > bar2.close > bar2.open:
                v2 = "看跌反击线"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


def jcc_shan_chun_V221121(c: CZSC, **kwargs) -> OrderedDict:
    """山川形态，表示三山形态和三川形态

    参数模板："{freq}_D{di}B_山川形态"

    **信号逻辑：**

    1. 三山顶部形态一般认为，本形态构成了一种主要顶部反转过程。如果市场先后三次均从某一个高价位上回落下来，或者市场对某一个高价
    位向上进行了三次尝试，但都失败了，那么三山顶部形态就形成了。
    2. 三川底部形态恰巧是三山顶部形态的反面。在市场先后三度向下试探某个底部水平后，就形成了这类形态。市场必须向上突破这个底部形
    态的最高水平，才能证实底部过程已经完成。

    **信号列表：**

    - Signal('15分钟_D1B_山川形态_三山_任意_任意_0')
    - Signal('15分钟_D1B_山川形态_三川_任意_任意_0')

    :param c: CZSC 对象
    :param di: 截止倒数第di笔
    :return: 识别结果
    """
    di = int(kwargs.get("di", 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}B_山川形态".split('_')

    v1 = "其他"
    if len(c.bi_list) < 6 + di:
        pass
    else:
        b5, b4, b3, b2, b1 = get_sub_elements(c.bi_list, di, n=5)
        if b1.direction == Direction.Up and np.var((b5.high, b3.high, b1.high)) < 0.2:
            v1 = "三山"

        if b1.direction == Direction.Down and np.var((b5.low, b3.low, b1.low)) < 0.2:
            v1 = "三川"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def jcc_gap_yin_yang_V221121(c: CZSC, **kwargs) -> OrderedDict:
    """跳空与并列阴阳形态 贡献者：平凡

    参数模板："{freq}_D{di}K_并列阴阳"

    **向上跳空并列阴阳（向下反之）：**

    1. 其中一根白色蜡烛线和一根黑色蜡烛线共同形成了一个向上的窗口。
    2. 这根黑色蜡烛线的开市价位于前一个白色实体之内，收市价位于前一个白色实体之下。
    3. 在这样的情况下，这根黑色蜡烛线的收市价，需要在窗口之上。
    4. 黑白两根K线的实体相差不大

    **有效信号列表：**

    - Signal('15分钟_D1K_并列阴阳_向上跳空_任意_任意_0')
    - Signal('15分钟_D1K_并列阴阳_向下跳空_任意_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 识别结果
    """
    di = int(kwargs.get("di", 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}K_并列阴阳".split('_')

    v1 = "其他"
    if len(c.bars_raw) > di + 5:
        bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=3)

        if min(bar1.low, bar2.low) > bar3.high and bar2.close > bar2.open and bar1.close < bar1.open and np.var(
                (bar1.solid, bar2.solid)) < 0.2:
            v1 = "向上跳空"

        elif max(bar1.high, bar2.high) < bar3.low and bar2.close < bar2.open and bar1.close > bar1.open and np.var(
                (bar1.solid, bar2.solid)) < 0.2:
            v1 = "向下跳空"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def jcc_ta_xing_V221124(c: CZSC, **kwargs) -> OrderedDict:
    """塔形顶底

    参数模板："{freq}_D{di}K_塔形"

    **信号逻辑：**

    1. 首尾两根K线的实体最大
    2. 首k上涨，尾K下跌，且中间高点相近，且低点大于首尾低点的较大者，塔形顶部；反之，底部。

    **信号列表：**

    - Signal('15分钟_D1K_塔形_顶部_6K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_9K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_7K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_5K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_5K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_8K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_6K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_7K_任意_0')
    - Signal('15分钟_D1K_塔形_顶部_8K_任意_0')
    - Signal('15分钟_D1K_塔形_底部_9K_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :return: 识别结果
    """
    di = int(kwargs.get("di", 1))

    def __check_ta_xing(bars: List[RawBar]):
        if len(bars) < 5:
            return "其他"

        rb, lb = bars[0], bars[-1]
        sorted_solid = sorted([x.solid for x in bars])
        if min(rb.solid, lb.solid) >= sorted_solid[-2]:

            g_c1 = rb.close > rb.open and lb.close < lb.open
            g_c2 = np.var([x.high for x in bars[1: -1]]) < 0.5
            g_c3 = all(x.low > max(rb.open, lb.close) for x in bars[1: -1])
            if g_c1 and g_c2 and g_c3:
                return "顶部"

            d_c1 = rb.close < rb.open and lb.close > lb.open
            d_c2 = np.var([x.low for x in bars[1: -1]]) < 0.5
            d_c3 = all(x.high < min(rb.open, lb.close) for x in bars[1: -1])
            if d_c1 and d_c2 and d_c3:
                return "底部"

        return "其他"

    k1, k2, k3 = f"{c.freq.value}_D{di}K_塔形".split("_")

    for n in (5, 6, 7, 8, 9):
        _bars = get_sub_elements(c.bars_raw, di=di, n=n)
        v1 = __check_ta_xing(_bars)
        if v1 != "其他":
            v2 = f"{n}K"
            break
        else:
            v2 = "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s
