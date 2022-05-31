# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/21 17:48
describe: 笔相关信号的计算
"""
from typing import List, Union
from collections import OrderedDict

from czsc import analyze
from ..objects import Direction, BI, FakeBI, Signal
from ..enum import Freq
from ..utils.ta import RSQ


def check_three_bi(bis: List[Union[BI, FakeBI]], freq: Freq, di: int = 1) -> Signal:
    """识别由远及近的三笔形态

    :param freq: K线周期，也可以称为级别
    :param bis: 由远及近的三笔形态
    :param di: 最近一笔为倒数第i笔
    :return:
    """
    di_name = f"倒{di}笔"
    v = Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='其他', v2='其他', v3='其他')

    if len(bis) != 3:
        return v

    bi1, bi2, bi3 = bis
    if not (bi1.direction == bi3.direction):
        print(f"1,3 的 direction 不一致，无法识别三笔形态，{bi3}")
        return v

    assert bi3.direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if bi3.direction == Direction.Down:
        # 向下不重合
        if bi3.low > bi1.high:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向下不重合')

        # 向下奔走型
        if bi2.low < bi3.low < bi1.high < bi2.high:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向下奔走型')

        # 向下收敛
        if bi1.high > bi3.high and bi1.low < bi3.low:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向下收敛')

        if bi1.high < bi3.high and bi1.low > bi3.low:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向下扩张')

        if bi3.low < bi1.low and bi3.high < bi1.high:
            if bi3.power < bi1.power:
                return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向下盘背')
            else:
                return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向下无背')

    if bi3.direction == Direction.Up:
        if bi3.high < bi1.low:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向上不重合')

        if bi2.low < bi1.low < bi3.high < bi2.high:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向上奔走型')

        if bi1.high > bi3.high and bi1.low < bi3.low:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向上收敛')

        if bi1.high < bi3.high and bi1.low > bi3.low:
            return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向上扩张')

        if bi3.low > bi1.low and bi3.high > bi1.high:
            if bi3.power < bi1.power:
                return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向上盘背')

            else:
                return Signal(k1=freq.value, k2=di_name, k3='三笔形态', v1='向上无背')
    return v


def check_five_bi(bis: List[Union[BI, FakeBI]], freq: Freq, di: int = 1) -> Signal:
    """识别五笔形态

    :param freq: K线周期，也可以称为级别
    :param bis: 由远及近的五笔
    :param di: 最近一笔为倒数第i笔
    :return:
    """
    di_name = f"倒{di}笔"
    v = Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='其他', v2='其他', v3='其他')

    if len(bis) != 5:
        return v

    bi1, bi2, bi3, bi4, bi5 = bis
    if not (bi1.direction == bi3.direction == bi5.direction):
        print(f"1,3,5 的 direction 不一致，无法识别五段形态；{bi1}{bi3}{bi5}")
        return v

    direction = bi1.direction
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    assert direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if direction == Direction.Down:
        # aAb式底背驰
        if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and max_high == bi1.high and bi5.power < bi1.power:
            if (min_low == bi3.low and bi5.low < bi1.low) or (min_low == bi5.low):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='底背驰', v2='五笔aAb式')

        # 类趋势底背驰
        if max_high == bi1.high and min_low == bi5.low and bi4.high < bi2.low and bi5.power < max(bi3.power, bi1.power):
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='底背驰', v2='五笔类趋势')

        # 上颈线突破
        if (min_low == bi1.low and bi5.high > min(bi1.high, bi2.high) > bi5.low > bi1.low) \
                or (min_low == bi3.low and bi5.high > bi3.high > bi5.low > bi3.low):
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='上颈线突破', v2='五笔')

        # 五笔三买，要求bi5.high是最高点
        if max_high == bi5.high > bi5.low > max(bi1.high, bi3.high) \
                > min(bi1.high, bi3.high) > max(bi1.low, bi3.low) > min_low:
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='类三买', v2='五笔')

    if direction == Direction.Up:
        # aAb式类一卖
        if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and min_low == bi1.low and bi5.power < bi1.power:
            if (max_high == bi3.high and bi5.high > bi1.high) or (max_high == bi5.high):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='顶背驰', v2='五笔aAb式')

        # 类趋势类一卖
        if min_low == bi1.low and max_high == bi5.high and bi5.power < max(bi1.power, bi3.power) and bi4.low > bi2.high:
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='顶背驰', v2='五笔类趋势')

        # 下颈线突破
        if (max_high == bi1.high and bi5.low < max(bi1.low, bi2.low) < bi5.high < max_high) \
                or (max_high == bi3.high and bi5.low < bi3.low < bi5.high < max_high):
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='下颈线突破', v2='五笔')

        # 五笔三卖，要求bi5.low是最低点
        if min_low == bi5.low < bi5.high < min(bi1.low, bi3.low) \
                < max(bi1.low, bi3.low) < min(bi1.high, bi3.high) < max_high:
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='类三卖', v2='五笔')

    return v


def check_seven_bi(bis: List[Union[BI, FakeBI]], freq: Freq, di: int = 1) -> Signal:
    """识别七笔形态

    :param freq: K线周期，也可以称为级别
    :param bis: 由远及近的七笔
    :param di: 最近一笔为倒数第i笔
    """
    di_name = f"倒{di}笔"
    v = Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='其他', v2='其他', v3='其他')

    if len(bis) != 7:
        return v

    bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    direction = bi7.direction

    assert direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if direction == Direction.Down:
        if bi1.high == max_high and bi7.low == min_low:
            # aAbcd式底背驰
            if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) > bi6.high and bi7.power < bi5.power:
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='底背驰', v2='七笔aAbcd式')

            # abcAd式底背驰
            if bi2.low > min(bi4.high, bi6.high) > max(bi4.low, bi6.low) and bi7.power < (bi1.high - bi3.low):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='底背驰', v2='七笔abcAd式')

            # aAb式底背驰
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) and bi7.power < bi1.power:
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='底背驰', v2='七笔aAb式')

            # 类趋势底背驰
            if bi2.low > bi4.high and bi4.low > bi6.high and bi7.power < max(bi5.power, bi3.power, bi1.power):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='底背驰', v2='七笔类趋势')

        # 向上中枢完成
        if bi4.low == min_low and min(bi1.high, bi3.high) > max(bi1.low, bi3.low) \
                and min(bi5.high, bi7.high) > max(bi5.low, bi7.low) \
                and max(bi4.high, bi6.high) > min(bi3.high, bi4.high):
            if max(bi1.low, bi3.low) < max(bi5.high, bi7.high):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='向上中枢完成', v2='七笔')

        # 七笔三买：1~3构成中枢，最低点在1~3，最高点在5~7，5~7的最低点大于1~3的最高点
        if min(bi1.low, bi3.low) == min_low and max(bi5.high, bi7.high) == max_high \
                and min(bi5.low, bi7.low) > max(bi1.high, bi3.high) \
                and min(bi1.high, bi3.high) > max(bi1.low, bi3.low):
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='类三买', v2='七笔')

    if direction == Direction.Up:
        # 顶背驰
        if bi1.low == min_low and bi7.high == max_high:
            # aAbcd式顶背驰
            if bi6.low > min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and bi7.power < bi5.power:
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='顶背驰', v2='七笔aAbcd式')

            # abcAd式顶背驰
            if min(bi4.high, bi6.high) > max(bi4.low, bi6.low) > bi2.high and bi7.power < (bi3.high - bi1.low):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='顶背驰', v2='七笔abcAd式')

            # aAb式顶背驰
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) and bi7.power < bi1.power:
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='顶背驰', v2='七笔aAb式')

            # 类趋势顶背驰
            if bi2.high < bi4.low and bi4.high < bi6.low and bi7.power < max(bi5.power, bi3.power, bi1.power):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='顶背驰', v2='七笔类趋势')

        # 向下中枢完成
        if bi4.high == max_high and min(bi1.high, bi3.high) > max(bi1.low, bi3.low) \
                and min(bi5.high, bi7.high) > max(bi5.low, bi7.low) \
                and min(bi4.low, bi6.low) < max(bi3.low, bi4.low):
            if min(bi1.high, bi3.high) > min(bi5.low, bi7.low):
                return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='向下中枢完成', v2='七笔')

        # 七笔三卖：1~3构成中枢，最高点在1~3，最低点在5~7，5~7的最高点小于1~3的最低点
        if min(bi5.low, bi7.low) == min_low and max(bi1.high, bi3.high) == max_high \
                and max(bi7.high, bi5.high) < min(bi1.low, bi3.low) \
                and min(bi1.high, bi3.high) > max(bi1.low, bi3.low):
            return Signal(k1=freq.value, k2=di_name, k3='基础形态', v1='类三卖', v2='七笔')
    return v


def check_nine_bi(bis: List[Union[BI, FakeBI]], freq: Freq, di: int = 1) -> Signal:
    """识别九笔形态

    :param freq: K线周期，也可以称为级别
    :param bis: 由远及近的九笔
    :param di: 最近一笔为倒数第i笔
    """
    di_name = f"倒{di}笔"
    v = Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='其他', v2='其他', v3='其他')
    if len(bis) != 9:
        return v

    direction = bis[-1].direction
    bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    assert direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if direction == Direction.Down:
        if min_low == bi9.low and max_high == bi1.high:
            # aAb式类一买
            if min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low) \
                    and bi9.power < bi1.power and bi3.low >= bi1.low and bi7.high <= bi9.high:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2='九笔aAb式')

            # aAbcd式类一买
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) > bi8.high \
                    and bi9.power < bi7.power:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2='九笔aAbcd式')

            # ABC式类一买
            if bi3.low < bi1.low and bi7.high > bi9.high \
                    and min(bi4.high, bi6.high) > max(bi4.low, bi6.low) \
                    and (bi1.high - bi3.low) > (bi7.high - bi9.low):
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2='九笔ABC式')

            # 类趋势一买
            if bi8.high < bi6.low < bi6.high < bi4.low < bi4.high < bi2.low \
                    and bi9.power < max([bi1.power, bi3.power, bi5.power, bi7.power]):
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2='九笔类趋势')

        # 九笔类一买（2~4构成中枢A，6~8构成中枢B，9背驰）
        if max_high == max(bi1.high, bi3.high) and min_low == bi9.low \
                and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                and min(bi2.low, bi4.low) > max(bi6.high, bi8.high) \
                and min(bi6.high, bi8.high) > max(bi6.low, bi8.low) \
                and bi9.power < bi5.power:
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2='九笔aAbBc式')

        # 类三买（1357构成中枢，最低点在3或5）
        if max_high == bi9.high > bi9.low \
                > max([x.high for x in [bi1, bi3, bi5, bi7]]) \
                > min([x.high for x in [bi1, bi3, bi5, bi7]]) \
                > max([x.low for x in [bi1, bi3, bi5, bi7]]) \
                > min([x.low for x in [bi3, bi5]]) == min_low:
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类三买', v2='九笔GG三买')

        # 类三买（357构成中枢，8的力度小于2，9回调不跌破GG构成三买）
        if bi8.power < bi2.power and max_high == bi9.high > bi9.low \
                > max([x.high for x in [bi3, bi5, bi7]]) \
                > min([x.high for x in [bi3, bi5, bi7]]) \
                > max([x.low for x in [bi3, bi5, bi7]]) > bi1.low == min_low:
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类三买', v2='九笔GG三买')

        if min_low == bi5.low and max_high == bi1.high and bi4.high < bi2.low:  # 前五笔构成向下类趋势
            zd = max([x.low for x in [bi5, bi7]])
            zg = min([x.high for x in [bi5, bi7]])
            gg = max([x.high for x in [bi5, bi7]])
            if zg > zd and bi8.high > gg:  # 567构成中枢，且8的高点大于gg
                if bi9.low > zg:
                    return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类三买', v2='九笔ZG三买')

                # 类二买
                if bi9.high > gg > zg > bi9.low > zd:
                    return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类二买', v2='九笔')

    if direction == Direction.Up:
        if max_high == bi9.high and min_low == bi1.low:
            # aAbBc式类一卖
            if bi6.low > min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and min(bi6.high, bi8.high) > max(bi6.low, bi8.low) \
                    and max(bi2.high, bi4.high) < min(bi6.low, bi8.low) \
                    and bi9.power < bi5.power:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2='九笔aAbBc式')

            # aAb式类一卖
            if min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low) \
                    and bi9.power < bi1.power and bi3.high <= bi1.high and bi7.low >= bi9.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2='九笔aAb式')

            # aAbcd式类一卖
            if bi8.low > min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) \
                    and bi9.power < bi7.power:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2='九笔aAbcd式')

            # ABC式类一卖
            if bi3.high > bi1.high and bi7.low < bi9.low \
                    and min(bi4.high, bi6.high) > max(bi4.low, bi6.low) \
                    and (bi3.high - bi1.low) > (bi9.high - bi7.low):
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2='九笔ABC式')

            # 类趋势一卖
            if bi8.low > bi6.high > bi6.low > bi4.high > bi4.low > bi2.high \
                    and bi9.power < max([bi1.power, bi3.power, bi5.power, bi7.power]):
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2='九笔类趋势')

        # 九笔三卖
        if max_high == bi1.high and min_low == bi9.low \
                and bi9.high < max([x.low for x in [bi3, bi5, bi7]]) < min([x.high for x in [bi3, bi5, bi7]]):
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类三卖', v2='九笔')

        if min_low == bi1.low and max_high == bi5.high and bi2.high < bi4.low:  # 前五笔构成向上类趋势
            zd = max([x.low for x in [bi5, bi7]])
            zg = min([x.high for x in [bi5, bi7]])
            dd = min([x.low for x in [bi5, bi7]])
            if zg > zd and bi8.low < dd:  # 567构成中枢，且8的低点小于dd
                if bi9.high < zd:
                    return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类三卖', v2='九笔ZD三卖')

                # 类二卖
                if dd < zd <= bi9.high < zg:
                    return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类二卖', v2='九笔')
    return v


def check_eleven_bi(bis: List[Union[BI, FakeBI]], freq: Freq, di: int = 1) -> Signal:
    """识别十一笔形态

    :param freq: K线周期，也可以称为级别
    :param bis: 由远及近的十一笔
    :param di: 最近一笔为倒数第i笔
    """
    di_name = f"倒{di}笔"
    v = Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='其他', v2='其他', v3='其他')
    if len(bis) != 11:
        return v

    direction = bis[-1].direction
    bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    assert direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if direction == Direction.Down:
        if min_low == bi11.low and max_high == bi1.high:
            # ABC式类一买，A5B3C3
            if bi5.low == min([x.low for x in [bi1, bi3, bi5]]) \
                    and bi9.low > bi11.low and bi9.high > bi11.high \
                    and bi8.high > bi6.low and bi1.high - bi5.low > bi9.high - bi11.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2="11笔A5B3C3式")

            # ABC式类一买，A3B3C5
            if bi1.high > bi3.high and bi1.low > bi3.low \
                    and bi7.high == max([x.high for x in [bi7, bi9, bi11]]) \
                    and bi6.high > bi4.low and bi1.high - bi3.low > bi7.high - bi11.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2="11笔A3B3C5式")

            # ABC式类一买，A3B5C3
            if bi1.low > bi3.low and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi9.high > bi11.high and bi1.high - bi3.low > bi9.high - bi11.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2="11笔A3B5C3式")

            # a1Ab式类一买，a1（1~7构成的类趋势）
            if bi2.low > bi4.high > bi4.low > bi6.high > bi5.low > bi7.low and bi10.high > bi8.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2="11笔a1Ab式")

        # 类二买（1~7构成盘整背驰，246构成下跌中枢，9/11构成上涨中枢，且上涨中枢GG大于下跌中枢ZG）
        if bi7.power < bi1.power and min_low == bi7.low < max([x.low for x in [bi2, bi4, bi6]]) \
                < min([x.high for x in [bi2, bi4, bi6]]) < max([x.high for x in [bi9, bi11]]) < bi1.high == max_high \
                and bi11.low > min([x.low for x in [bi2, bi4, bi6]]) \
                and min([x.high for x in [bi9, bi11]]) > max([x.low for x in [bi9, bi11]]):
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类二买', v2="11笔")

        # 类二买（1~7为区间极值，9~11构成上涨中枢，上涨中枢GG大于4~6的最大值，上涨中枢DD大于4~6的最小值）
        if max_high == bi1.high and min_low == bi7.low \
                and min(bi9.high, bi11.high) > max(bi9.low, bi11.low) \
                and max(bi11.high, bi9.high) > max(bi4.high, bi6.high) \
                and min(bi9.low, bi11.low) > min(bi4.low, bi6.low):
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类二买', v2="11笔")

        # 类三买（1~9构成大级别中枢，10离开，11回调不跌破GG）
        gg = max([x.high for x in [bi1, bi2, bi3]])
        zg = min([x.high for x in [bi1, bi2, bi3]])
        zd = max([x.low for x in [bi1, bi2, bi3]])
        dd = min([x.low for x in [bi1, bi2, bi3]])
        if max_high == bi11.high and bi11.low > zg > zd \
                and gg > bi5.low and gg > bi7.low and gg > bi9.low \
                and dd < bi5.high and dd < bi7.high and dd < bi9.high:
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类三买', v2="11笔GG三买")

    if direction == Direction.Up:
        if max_high == bi11.high and min_low == bi1.low:
            # ABC式类一卖，A5B3C3
            if bi5.high == max([bi1.high, bi3.high, bi5.high]) and bi9.low < bi11.low and bi9.high < bi11.high \
                    and bi8.low < bi6.high and bi11.high - bi9.low < bi5.high - bi1.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2="11笔A5B3C3式")

            # ABC式类一卖，A3B3C5
            if bi7.low == min([bi11.low, bi9.low, bi7.low]) and bi1.high < bi3.high and bi1.low < bi3.low \
                    and bi6.low < bi4.high and bi11.high - bi7.low < bi3.high - bi1.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2="11笔A3B3C5式")

            # ABC式类一卖，A3B5C3
            if bi1.high < bi3.high and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi9.low < bi11.low and bi3.high - bi1.low > bi11.high - bi9.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2="11笔A3B5C3式")

        # 类二卖：1~9构成类趋势，11不创新高
        if max_high == bi9.high > bi8.low > bi6.high > bi6.low > bi4.high > bi4.low > bi2.high > bi1.low == min_low \
                and bi11.high < bi9.high:
            return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类二卖', v2="11笔")
    return v


def check_thirteen_bi(bis: List[Union[BI, FakeBI]], freq: Freq, di: int = 1) -> Signal:
    """识别十三笔形态

    :param freq: K线周期，也可以称为级别
    :param bis: 由远及近的十三笔
    :param di: 最近一笔为倒数第i笔
    """
    di_name = f"倒{di}笔"
    v = Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='其他', v2='其他', v3='其他')
    if len(bis) != 13:
        return v

    direction = bis[-1].direction
    bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11, bi12, bi13 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])

    assert direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if direction == Direction.Down:
        if min_low == bi13.low and max_high == bi1.high:
            # ABC式类一买，A5B3C5
            if bi5.low < min(bi1.low, bi3.low) and bi9.high > max(bi11.high, bi13.high) \
                    and bi8.high > bi6.low and bi1.high - bi5.low > bi9.high - bi13.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2="13笔A5B3C5式")

            # ABC式类一买，A3B5C5
            if bi3.low < min(bi1.low, bi5.low) and bi9.high > max(bi11.high, bi13.high) \
                    and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi1.high - bi3.low > bi9.high - bi13.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2="13笔A3B5C5式")

            # ABC式类一买，A5B5C3
            if bi5.low < min(bi1.low, bi3.low) and bi11.high > max(bi9.high, bi13.high) \
                    and min(bi6.high, bi8.high, bi10.high) > max(bi6.low, bi8.low, bi10.low) \
                    and bi1.high - bi5.low > bi11.high - bi13.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一买', v2="13笔A5B5C3式")

    if direction == Direction.Up:
        if max_high == bi13.high and min_low == bi1.low:
            # ABC式类一卖，A5B3C5
            if bi5.high > max(bi3.high, bi1.high) and bi9.low < min(bi11.low, bi13.low) \
                    and bi8.low < bi6.high and bi5.high - bi1.low > bi13.high - bi9.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2="13笔A5B3C5式")

            # ABC式类一卖，A3B5C5
            if bi3.high > max(bi5.high, bi1.high) and bi9.low < min(bi11.low, bi13.low) \
                    and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi3.high - bi1.low > bi13.high - bi9.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2="13笔A3B5C5式")

            # ABC式类一卖，A5B5C3
            if bi5.high > max(bi3.high, bi1.high) and bi11.low < min(bi9.low, bi13.low) \
                    and min(bi6.high, bi8.high, bi10.high) > max(bi6.low, bi8.low, bi10.low) \
                    and bi5.high - bi1.low > bi13.high - bi11.low:
                return Signal(k1=freq.value, k2=di_name, k3='类买卖点', v1='类一卖', v2="13笔A5B5C3式")
    return v


# 以上是信号计算的辅助函数，主要是形态识别等。
# ----------------------------------------------------------------------------------------------------------------------
# 以下是信号计算函数（前缀固定为 get_s）

def get_s_three_bi(c: analyze.CZSC, di: int = 1) -> OrderedDict:
    """倒数第i笔的三笔形态信号

    :param c: CZSC 对象
    :param di: 最近一笔为倒数第i笔
    :return: 信号字典
    """
    assert di >= 1
    bis = c.finished_bis
    freq: Freq = c.freq
    s = OrderedDict()
    v = Signal(k1=str(freq.value), k2=f"倒{di}笔", k3="三笔形态", v1="其他", v2='其他', v3='其他')
    s[v.key] = v.value

    if not bis:
        return s

    if di == 1:
        three_bi = bis[-3:]
    else:
        three_bi = bis[-3 - di + 1: -di + 1]

    v = check_three_bi(three_bi, freq, di)
    s[v.key] = v.value
    return s


def get_s_base_xt(c: analyze.CZSC, di: int = 1) -> OrderedDict:
    """倒数第i笔的基础形态信号

    :param c: CZSC 对象
    :param di: 最近一笔为倒数第i笔
    :return: 信号字典
    """
    assert di >= 1

    bis = c.finished_bis
    freq: Freq = c.freq
    s = OrderedDict()
    v = Signal(k1=str(freq.value), k2=f"倒{di}笔", k3="基础形态", v1="其他", v2='其他', v3='其他')
    s[v.key] = v.value

    if not bis:
        return s

    if di == 1:
        five_bi = bis[-5:]
        seven_bi = bis[-7:]
    else:
        five_bi = bis[-5 - di + 1: -di + 1]
        seven_bi = bis[-7 - di + 1: -di + 1]

    for v in [check_five_bi(five_bi, freq, di), check_seven_bi(seven_bi, freq, di)]:
        if "其他" not in v.value:
            s[v.key] = v.value
    return s


def get_s_like_bs(c: analyze.CZSC, di: int = 1) -> OrderedDict:
    """倒数第i笔的类买卖点信号

    :param c: CZSC 对象
    :param di: 最近一笔为倒数第i笔
    :return: 信号字典
    """
    assert di >= 1
    bis = c.finished_bis
    freq: Freq = c.freq
    s = OrderedDict()
    v = Signal(k1=str(freq.value), k2=f"倒{di}笔", k3="类买卖点", v1="其他", v2='其他', v3='其他')
    s[v.key] = v.value

    if not bis:
        return s

    if di == 1:
        nine_bi = bis[-9:]
        eleven_bi = bis[-11:]
        thirteen_bi = bis[-13:]
    else:
        nine_bi = bis[-9 - di + 1: -di + 1]
        eleven_bi = bis[-11 - di + 1: -di + 1]
        thirteen_bi = bis[-13 - di + 1: -di + 1]

    for v in [check_nine_bi(nine_bi, freq, di), check_eleven_bi(eleven_bi, freq, di),
              check_thirteen_bi(thirteen_bi, freq, di)]:
        if "其他" not in v.value:
            s[v.key] = v.value
    return s


def get_s_bi_status(c: analyze.CZSC) -> OrderedDict:
    """倒数第1笔的表里关系信号

    :param c: CZSC 对象
    :return: 信号字典
    """
    freq: Freq = c.freq
    s = OrderedDict()
    v = Signal(k1=str(freq.value), k2="倒1笔", k3="表里关系", v1="其他", v2='其他', v3='其他')
    s[v.key] = v.value

    if c.bi_list:
        # 表里关系的定义参考：http://blog.sina.com.cn/s/blog_486e105c01007wc1.html
        min_ubi = min([x.low for x in c.bars_ubi])
        max_ubi = max([x.high for x in c.bars_ubi])

        last_bi = c.bi_list[-1]
        v = None
        if last_bi.direction == Direction.Down:
            if min_ubi < last_bi.low:
                v = Signal(k1=str(freq.value), k2="倒1笔", k3="表里关系", v1="向下延伸")
            else:
                v = Signal(k1=str(freq.value), k2="倒1笔", k3="表里关系", v1="底分完成")
        if last_bi.direction == Direction.Up:
            if max_ubi > last_bi.high:
                v = Signal(k1=str(freq.value), k2="倒1笔", k3="表里关系", v1="向上延伸")
            else:
                v = Signal(k1=str(freq.value), k2="倒1笔", k3="表里关系", v1="顶分完成")

        if v and "其他" not in v.value:
            s[v.key] = v.value
    return s


def get_s_d0_bi(c: analyze.CZSC) -> OrderedDict:
    """倒数第0笔信号

    :param c: CZSC 对象
    :return: 信号字典
    """
    freq: Freq = c.freq
    s = OrderedDict()

    default_signals = [
        Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="其他", v2='其他', v3='其他'),
        Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="其他", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    bis = c.finished_bis

    if bis:
        # 倒0笔方向
        last_bi = bis[-1]
        if last_bi.direction == Direction.Down:
            v = Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向上")
        elif last_bi.direction == Direction.Up:
            v = Signal(k1=str(freq.value), k2="倒0笔", k3="方向", v1="向下")
        else:
            raise ValueError

        if v and "其他" not in v.value:
            s[v.key] = v.value

        # 倒0笔长度
        bars_ubi = [x for x in c.bars_raw[-20:] if x.dt >= bis[-1].fx_b.elements[0].dt]
        if len(bars_ubi) >= 9:
            v = Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="9根K线以上")
        elif 9 > len(bars_ubi) > 5:
            v = Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="5到9根K线")
        else:
            v = Signal(k1=str(freq.value), k2="倒0笔", k3="长度", v1="5根K线以下")

        if "其他" not in v.value:
            s[v.key] = v.value
    return s


def get_s_di_bi(c: analyze.CZSC, di: int = 1) -> OrderedDict:
    """倒数第i笔的表里关系信号

    :param c: CZSC 对象
    :param di: 最近一笔为倒数第i笔
    :return: 信号字典
    """
    assert di >= 1
    freq: Freq = c.freq
    s = OrderedDict()
    k1 = str(freq.value)
    k2 = f"倒{di}笔"

    default_signals = [
        Signal(k1=k1, k2=k2, k3="方向", v1="其他", v2='其他', v3='其他'),
        Signal(k1=k1, k2=k2, k3="长度", v1="其他", v2='其他', v3='其他'),
        Signal(k1=k1, k2=k2, k3="拟合优度", v1="其他", v2='其他', v3='其他'),
    ]
    for signal in default_signals:
        s[signal.key] = signal.value

    bis = c.finished_bis
    if not bis:
        return s

    last_bi = bis[-di]

    # 方向
    v1 = Signal(k1=k1, k2=k2, k3="方向", v1=last_bi.direction.value)
    s[v1.key] = v1.value

    # 长度
    if len(last_bi.bars) >= 15:
        v = Signal(k1=k1, k2=k2, k3="长度", v1="15根K线以上")
    elif 15 > len(c.bars_ubi) > 9:
        v = Signal(k1=k1, k2=k2, k3="长度", v1="9到15根K线")
    else:
        v = Signal(k1=k1, k2=k2, k3="长度", v1="9根K线以下")

    if "其他" not in v.value:
        s[v.key] = v.value

    # 拟合优度
    rsq = RSQ([x.close for x in last_bi.bars[1:-1]])
    if rsq > 0.8:
        v = Signal(k1=k1, k2=k2, k3="拟合优度", v1="大于0.8")
    elif rsq < 0.2:
        v = Signal(k1=k1, k2=k2, k3="拟合优度", v1="小于0.2")
    else:
        v = Signal(k1=k1, k2=k2, k3="拟合优度", v1="0.2到0.8之间")

    if "其他" not in v.value:
        s[v.key] = v.value
    return s

