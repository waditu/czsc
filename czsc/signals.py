# coding: utf-8

import warnings
from collections import OrderedDict
from typing import List
from .objects import Direction, BI
from .enum import FdThree, FdFive, FdSeven, FdNine

def signals_long_short():
    """信号值的多空经验分析"""
    ls = {
        "第N笔方向": {
            Direction.Down.value: "多头信号",
            Direction.Up.value: "空头信号",
        },
        "第N笔的三笔形态": {
            FdThree.L1.value: "多头信号",
            FdThree.L2.value: "多头信号",
            FdThree.L3.value: "多头信号",
            FdThree.L4.value: "多头信号",
            FdThree.L5.value: "多头信号",
            FdThree.L6.value: "多头信号",

            FdThree.S1.value: "空头信号",
            FdThree.S2.value: "空头信号",
            FdThree.S3.value: "空头信号",
            FdThree.S4.value: "空头信号",
            FdThree.S5.value: "空头信号",
            FdThree.S6.value: "空头信号",
        },
        "第N-1笔的三笔形态": {
            FdThree.L1.value: "空头信号",
            FdThree.L2.value: "空头信号",
            FdThree.L3.value: "空头信号",
            FdThree.L4.value: "空头信号",
            FdThree.L5.value: "空头信号",
            FdThree.L6.value: "空头信号",

            FdThree.S1.value: "多头信号",
            FdThree.S2.value: "多头信号",
            FdThree.S3.value: "多头信号",
            FdThree.S4.value: "多头信号",
            FdThree.S5.value: "多头信号",
            FdThree.S6.value: "多头信号",
        },
        "第N-2笔的三笔形态": {
            FdThree.L1.value: "多头信号",
            FdThree.L2.value: "多头信号",
            FdThree.L3.value: "多头信号",
            FdThree.L4.value: "多头信号",
            FdThree.L5.value: "多头信号",
            FdThree.L6.value: "多头信号",

            FdThree.S1.value: "空头信号",
            FdThree.S2.value: "空头信号",
            FdThree.S3.value: "空头信号",
            FdThree.S4.value: "空头信号",
            FdThree.S5.value: "空头信号",
            FdThree.S6.value: "空头信号",
        },
        "第N-3笔的三笔形态": {
            FdThree.L1.value: "空头信号",
            FdThree.L2.value: "空头信号",
            FdThree.L3.value: "空头信号",
            FdThree.L4.value: "空头信号",
            FdThree.L5.value: "空头信号",
            FdThree.L6.value: "空头信号",

            FdThree.S1.value: "多头信号",
            FdThree.S2.value: "多头信号",
            FdThree.S3.value: "多头信号",
            FdThree.S4.value: "多头信号",
            FdThree.S5.value: "多头信号",
            FdThree.S6.value: "多头信号",
        },
        "第N笔的五笔形态": {
            FdFive.L1A1.value: "多头信号",
            FdFive.L1B1.value: "多头信号",
            FdFive.L2A1.value: "多头信号",
            FdFive.L2B1.value: "多头信号",
            FdFive.L3A1.value: "多头信号",
            FdFive.L4A1.value: "多头信号",
            FdFive.L4A2.value: "多头信号",
            FdFive.L4B1.value: "多头信号",
            FdFive.L4B2.value: "多头信号",
            FdFive.L4C1.value: "多头信号",
            FdFive.L4C2.value: "多头信号",
            FdFive.L4D1.value: "多头信号",
            FdFive.L4D2.value: "多头信号",
            FdFive.L5A1.value: "多头信号",
            FdFive.L5B1.value: "多头信号",

            FdFive.S1A1.value: "空头信号",
            FdFive.S1B1.value: "空头信号",
            FdFive.S2A1.value: "空头信号",
            FdFive.S2B1.value: "空头信号",
            FdFive.S3A1.value: "空头信号",
            FdFive.S4A1.value: "空头信号",
            FdFive.S4A2.value: "空头信号",
            FdFive.S4B1.value: "空头信号",
            FdFive.S4B2.value: "空头信号",
            FdFive.S4C1.value: "空头信号",
            FdFive.S4C2.value: "空头信号",
            FdFive.S4D1.value: "空头信号",
            FdFive.S4D2.value: "空头信号",
            FdFive.S5A1.value: "空头信号",
            FdFive.S5B1.value: "空头信号",
        },
        "第N-1笔的五笔形态": {
            FdFive.L1A1.value: "空头信号",
            FdFive.L1B1.value: "空头信号",
            FdFive.L2A1.value: "空头信号",
            FdFive.L2B1.value: "空头信号",
            FdFive.L3A1.value: "空头信号",
            FdFive.L4A1.value: "空头信号",
            FdFive.L4A2.value: "空头信号",
            FdFive.L4B1.value: "空头信号",
            FdFive.L4B2.value: "空头信号",
            FdFive.L4C1.value: "空头信号",
            FdFive.L4C2.value: "空头信号",
            FdFive.L4D1.value: "空头信号",
            FdFive.L4D2.value: "空头信号",
            FdFive.L5A1.value: "空头信号",
            FdFive.L5B1.value: "空头信号",

            FdFive.S1A1.value: "多头信号",
            FdFive.S1B1.value: "多头信号",
            FdFive.S2A1.value: "多头信号",
            FdFive.S2B1.value: "多头信号",
            FdFive.S3A1.value: "多头信号",
            FdFive.S4A1.value: "多头信号",
            FdFive.S4A2.value: "多头信号",
            FdFive.S4B1.value: "多头信号",
            FdFive.S4B2.value: "多头信号",
            FdFive.S4C1.value: "多头信号",
            FdFive.S4C2.value: "多头信号",
            FdFive.S4D1.value: "多头信号",
            FdFive.S4D2.value: "多头信号",
            FdFive.S5A1.value: "多头信号",
            FdFive.S5B1.value: "多头信号",
        },
        "第N-2笔的五笔形态": {
            FdFive.L1A1.value: "多头信号",
            FdFive.L1B1.value: "多头信号",
            FdFive.L2A1.value: "多头信号",
            FdFive.L2B1.value: "多头信号",
            FdFive.L3A1.value: "多头信号",
            FdFive.L4A1.value: "多头信号",
            FdFive.L4A2.value: "多头信号",
            FdFive.L4B1.value: "多头信号",
            FdFive.L4B2.value: "多头信号",
            FdFive.L4C1.value: "多头信号",
            FdFive.L4C2.value: "多头信号",
            FdFive.L4D1.value: "多头信号",
            FdFive.L4D2.value: "多头信号",
            FdFive.L5A1.value: "多头信号",
            FdFive.L5B1.value: "多头信号",

            FdFive.S1A1.value: "空头信号",
            FdFive.S1B1.value: "空头信号",
            FdFive.S2A1.value: "空头信号",
            FdFive.S2B1.value: "空头信号",
            FdFive.S3A1.value: "空头信号",
            FdFive.S4A1.value: "空头信号",
            FdFive.S4A2.value: "空头信号",
            FdFive.S4B1.value: "空头信号",
            FdFive.S4B2.value: "空头信号",
            FdFive.S4C1.value: "空头信号",
            FdFive.S4C2.value: "空头信号",
            FdFive.S4D1.value: "空头信号",
            FdFive.S4D2.value: "空头信号",
            FdFive.S5A1.value: "空头信号",
            FdFive.S5B1.value: "空头信号",
        },
        "第N-3笔的五笔形态": {
            FdFive.L1A1.value: "空头信号",
            FdFive.L1B1.value: "空头信号",
            FdFive.L2A1.value: "空头信号",
            FdFive.L2B1.value: "空头信号",
            FdFive.L3A1.value: "空头信号",
            FdFive.L4A1.value: "空头信号",
            FdFive.L4A2.value: "空头信号",
            FdFive.L4B1.value: "空头信号",
            FdFive.L4B2.value: "空头信号",
            FdFive.L4C1.value: "空头信号",
            FdFive.L4C2.value: "空头信号",
            FdFive.L4D1.value: "空头信号",
            FdFive.L4D2.value: "空头信号",
            FdFive.L5A1.value: "空头信号",
            FdFive.L5B1.value: "空头信号",

            FdFive.S1A1.value: "多头信号",
            FdFive.S1B1.value: "多头信号",
            FdFive.S2A1.value: "多头信号",
            FdFive.S2B1.value: "多头信号",
            FdFive.S3A1.value: "多头信号",
            FdFive.S4A1.value: "多头信号",
            FdFive.S4A2.value: "多头信号",
            FdFive.S4B1.value: "多头信号",
            FdFive.S4B2.value: "多头信号",
            FdFive.S4C1.value: "多头信号",
            FdFive.S4C2.value: "多头信号",
            FdFive.S4D1.value: "多头信号",
            FdFive.S4D2.value: "多头信号",
            FdFive.S5A1.value: "多头信号",
            FdFive.S5B1.value: "多头信号",
        },
        "第N笔的七笔形态": {
            FdSeven.L1A1.value: "多头信号",
            FdSeven.L2A1.value: "多头信号",
            FdSeven.L3A1.value: "多头信号",
            FdSeven.L3B1.value: "多头信号",
            FdSeven.L4A1.value: "多头信号",

            FdSeven.S1A1.value: "空头信号",
            FdSeven.S2A1.value: "空头信号",
            FdSeven.S3A1.value: "空头信号",
            FdSeven.S3B1.value: "空头信号",
            FdSeven.S4A1.value: "空头信号",
        },
        "第N-1笔的七笔形态": {
            FdSeven.L1A1.value: "空头信号",
            FdSeven.L2A1.value: "空头信号",
            FdSeven.L3A1.value: "空头信号",
            FdSeven.L3B1.value: "空头信号",
            FdSeven.L4A1.value: "空头信号",

            FdSeven.S1A1.value: "多头信号",
            FdSeven.S2A1.value: "多头信号",
            FdSeven.S3A1.value: "多头信号",
            FdSeven.S3B1.value: "多头信号",
            FdSeven.S4A1.value: "多头信号",
        },
        "第N-2笔的七笔形态": {
            FdSeven.L1A1.value: "多头信号",
            FdSeven.L2A1.value: "多头信号",
            FdSeven.L3A1.value: "多头信号",
            FdSeven.L3B1.value: "多头信号",
            FdSeven.L4A1.value: "多头信号",

            FdSeven.S1A1.value: "空头信号",
            FdSeven.S2A1.value: "空头信号",
            FdSeven.S3A1.value: "空头信号",
            FdSeven.S3B1.value: "空头信号",
            FdSeven.S4A1.value: "空头信号",
        },
        "第N-3笔的七笔形态": {
            FdSeven.L1A1.value: "空头信号",
            FdSeven.L2A1.value: "空头信号",
            FdSeven.L3A1.value: "空头信号",
            FdSeven.L3B1.value: "空头信号",
            FdSeven.L4A1.value: "空头信号",

            FdSeven.S1A1.value: "多头信号",
            FdSeven.S2A1.value: "多头信号",
            FdSeven.S3A1.value: "多头信号",
            FdSeven.S3B1.value: "多头信号",
            FdSeven.S4A1.value: "多头信号",
        },
        "第N笔的九笔形态": {
            FdNine.L1A1.value: "多头信号",
            FdNine.L2A1.value: "多头信号",
            FdNine.L2B1.value: "多头信号",
            FdNine.L2C1.value: "多头信号",
            FdNine.L3A1.value: "多头信号",
            FdNine.L4A1.value: "多头信号",
            FdNine.L4B1.value: "多头信号",

            FdNine.S1A1.value: "空头信号",
            FdNine.S2A1.value: "空头信号",
            FdNine.S2B1.value: "空头信号",
            FdNine.S2C1.value: "空头信号",
            FdNine.S3A1.value: "空头信号",
            FdNine.S4A1.value: "空头信号",
            FdNine.S4B1.value: "空头信号",
        },
        "第N-1笔的九笔形态": {
            FdNine.L1A1.value: "空头信号",
            FdNine.L2A1.value: "空头信号",
            FdNine.L2B1.value: "空头信号",
            FdNine.L2C1.value: "空头信号",
            FdNine.L3A1.value: "空头信号",
            FdNine.L4A1.value: "空头信号",
            FdNine.L4B1.value: "空头信号",

            FdNine.S1A1.value: "多头信号",
            FdNine.S2A1.value: "多头信号",
            FdNine.S2B1.value: "多头信号",
            FdNine.S2C1.value: "多头信号",
            FdNine.S3A1.value: "多头信号",
            FdNine.S4A1.value: "多头信号",
            FdNine.S4B1.value: "多头信号",
        },
        "第N-2笔的九笔形态": {
            FdNine.L1A1.value: "多头信号",
            FdNine.L2A1.value: "多头信号",
            FdNine.L2B1.value: "多头信号",
            FdNine.L2C1.value: "多头信号",
            FdNine.L3A1.value: "多头信号",
            FdNine.L4A1.value: "多头信号",
            FdNine.L4B1.value: "多头信号",

            FdNine.S1A1.value: "空头信号",
            FdNine.S2A1.value: "空头信号",
            FdNine.S2B1.value: "空头信号",
            FdNine.S2C1.value: "空头信号",
            FdNine.S3A1.value: "空头信号",
            FdNine.S4A1.value: "空头信号",
            FdNine.S4B1.value: "空头信号",
        },
        "第N-3笔的九笔形态": {
            FdNine.L1A1.value: "空头信号",
            FdNine.L2A1.value: "空头信号",
            FdNine.L2B1.value: "空头信号",
            FdNine.L2C1.value: "空头信号",
            FdNine.L3A1.value: "空头信号",
            FdNine.L4A1.value: "空头信号",
            FdNine.L4B1.value: "空头信号",

            FdNine.S1A1.value: "多头信号",
            FdNine.S2A1.value: "多头信号",
            FdNine.S2B1.value: "多头信号",
            FdNine.S2C1.value: "多头信号",
            FdNine.S3A1.value: "多头信号",
            FdNine.S4A1.value: "多头信号",
            FdNine.S4B1.value: "多头信号",
        },
    }

    ls_map = OrderedDict()
    for freq in ['1分钟', '5分钟', '15分钟', '30分钟', '日线']:
        for name, values in ls.items():
            for v, s in values.items():
                k = "{}_{}_{}".format(freq, name, v)
                ls_map[k] = s
    return ls_map

def check_three_fd(fds: List[BI]) -> str:
    """识别三段形态

    :param fds: list
        由远及近的三段形态
    :return: str
    """
    v = FdThree.Other.value

    if len(fds) != 3:
        warnings.warn("len(fdx) != 3，无法识别三段形态")
        return v

    fd1, fd2, fd3 = fds
    if not (fd1.direction == fd3.direction):
        # warnings.warn("1,3的 direction 不一致，无法识别三段形态")
        print("1,3的 direction 不一致，无法识别三段形态")
        return v

    if fd3.direction == Direction.Down:
        if fd3.low > fd1.high:
            v = FdThree.L1.value        # "向下不重合"

        if fd2.low < fd3.low < fd1.high < fd2.high:
            v = FdThree.L2.value        # "向下奔走型中枢"

        if fd1.high > fd3.high and fd1.low < fd3.low:
            v = FdThree.L3.value        # "向下三角收敛中枢"

        if fd1.high < fd3.high and fd1.low > fd3.low:
            v = FdThree.L4.value        # "向下三角扩张中枢"

        if fd3.low < fd1.low and fd3.high < fd1.high:
            if fd3.power < fd1.power:
                v = FdThree.L5.value    # '向下盘背中枢'
            else:
                v = FdThree.L6.value    # '向下无背中枢'
    elif fd3.direction == Direction.Up:
        if fd3.high > fd1.low:
            v = FdThree.S1.value        # "向上不重合"

        if fd2.low < fd1.low < fd3.high < fd2.high:
            v = FdThree.S2.value        # "向上奔走型中枢"

        if fd1.high > fd3.high and fd1.low < fd3.low:
            v = FdThree.S3.value        # "向上三角收敛中枢"

        if fd1.high < fd3.high and fd1.low > fd3.low:
            v = FdThree.S4.value        # "向上三角扩张中枢"

        if fd3.low > fd1.low and fd3.high > fd1.high:
            if fd3.power < fd1.power:
                v = FdThree.S5.value        # '向上盘背中枢'
            else:
                v = FdThree.S6.value        # '向上无背中枢'
    else:
        raise ValueError("direction 的取值错误")

    return v

def check_five_fd(fds: List[BI]) -> str:
    """识别五段形态

    :param fds: list
        由远及近的五段走势
    :return: str
    """
    v = FdFive.Other.value

    if len(fds) != 5:
        warnings.warn("len(fdx) != 5，无法识别五段形态")
        return v

    fd1, fd2, fd3, fd4, fd5 = fds
    if not (fd1.direction == fd3.direction == fd5.direction):
        warnings.warn("1,3,5 的 direction 不一致，无法识别五段形态")
        return v
    direction = fd1.direction
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if direction == Direction.Down:
        if fd1.high > fd3.high > fd5.high and fd1.low < fd3.low < fd5.low:
            v = FdFive.L1A1.value     # "向下三角收敛中枢"
        if fd1.high < fd3.high < fd5.high and fd1.low > fd3.low > fd5.low:
            v = FdFive.L1B1.value     # "向下三角扩张中枢"

        if max_high == fd1.high and min_low == fd5.low and fd4.high > fd2.low and fd5.power < fd1.power:
            if fd2.high > fd4.high and fd2.low < fd4.low:
                v = FdFive.L2B1.value     # "aAb式底背驰B"
            else:
                v = FdFive.L2A1.value     # "aAb式底背驰A"

        if max_high == fd1.high and min_low == fd3.low and fd5.power < fd1.power \
                and fd4.high > fd2.low and fd5.low > fd3.low:
            v = FdFive.L2C1.value     # "aAb式底背驰C"

        if fd4.high < fd2.low and fd5.power < fd3.power and max_high == fd1.high and min_low == fd5.low:
            v = FdFive.L3A1.value     # "类趋势底背驰"

    elif direction == Direction.Up:
        if fd1.high > fd3.high > fd5.high and fd1.low < fd3.low < fd5.low:
            v = FdFive.S1A1.value     # "向上三角收敛中枢"
        if fd1.high < fd3.high < fd5.high and fd1.low > fd3.low > fd5.low:
            v = FdFive.S1B1.value     # "向上三角扩张中枢"

        if max_high == fd5.high and min_low == fd1.low and fd5.power < fd1.power:
            if fd2.high > fd4.high and fd2.low < fd4.low:
                v = FdFive.S2B1.value     # "aAb式顶背驰B"
            else:
                v = FdFive.S2A1.value     # "aAb式顶背驰A"

        if max_high == fd3.high and min_low == fd1.low and fd5.power < fd1.power \
                and fd5.high < fd3.high and fd4.low < fd2.high:
            v = FdFive.S2C1.value     # "aAb式顶背驰C"

        if max_high == fd5.high and min_low == fd1.low and fd5.power < fd1.power and fd4.low > fd4.low:
            v = FdFive.S3A1.value     # "类趋势顶背驰"
    else:
        raise ValueError("direction 的取值错误，必须是 down / up 之一，实际值为{}".format(fd5.direction))

    direction = fd5.direction
    zg = min([x.high for x in fds[:3]])
    gg = max([x.high for x in fds[:3]])
    zd = max([x.low for x in fds[:3]])
    dd = min([x.low for x in fds[:3]])
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if zd > zg:
        return v

    if direction == Direction.Down:
        if fd4.high == max_high:
            if fd1.high > fd3.high and fd1.low < fd3.low:
                if fd5.low > gg:
                    v = FdFive.L4A1.value     # "三买A1"
                if gg > fd5.low > zg:
                    v = FdFive.L4A2.value     # "三买A2"

            if fd3.high > fd1.high and fd3.low < fd1.low:
                if fd5.low > gg:
                    v = FdFive.L4B1.value     # "三买B1"
                if gg > fd5.low > zg:
                    v = FdFive.L4B2.value     # "三买B2"

            if fd3.high > fd1.high and fd3.low > fd1.low:
                if fd5.low > gg:
                    v = FdFive.L4C1.value     # "三买C1"
                if gg > fd5.low > zg:
                    v = FdFive.L4C2.value     # "三买C2"

            if fd3.power < fd1.power and fd3.high < fd1.high and fd3.low < fd1.low:
                if fd5.low > gg:
                    v = FdFive.L4D1.value     # "三买D1"
                if gg > fd5.low > zg:
                    v = FdFive.L4D2.value     # "三买D2"

    elif direction == Direction.Up:
        if fd4.low == min_low:
            if fd1.high > fd3.high and fd1.low < fd3.low:
                if fd5.high < dd:
                    v = FdFive.S4A1.value     # "三卖A1"
                if zd > fd5.high > dd:
                    v = FdFive.S4A2.value     # "三卖A2"

            if fd3.high > fd1.high and fd3.low < fd1.low:
                if fd5.high < dd:
                    v = FdFive.S4B1.value     # "三卖B1"
                if zd > fd5.high > dd:
                    v = FdFive.S4B2.value     # "三卖B2"

            if fd3.high < fd1.high and fd3.low < fd1.low:
                if fd5.high < dd:
                    v = FdFive.S4C1.value     # "三卖C1"
                if zd > fd5.high > dd:
                    v = FdFive.S4C2.value     # "三卖C2"

            if fd3.high > fd1.high and fd3.low > fd1.low and fd3.power < fd1.power:
                if fd5.high < dd:
                    v = FdFive.S4D1.value     # "三卖D1"
                if zd > fd5.high > dd:
                    v = FdFive.S4D2.value     # "三卖D2"
    else:
        raise ValueError("direction 的取值错误")
    return v

def check_seven_fd(fds: List[BI]) -> str:
    """识别七段形态

    :param fds: list
        由远及近的七段走势
    :return: str
    """
    v = FdSeven.Other.value
    if len(fds) != 7:
        warnings.warn("len(fdx) != 7，无法识别七段形态")
        return v

    fd1, fd2, fd3, fd4, fd5, fd6, fd7 = fds
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if fd7.direction == Direction.Down:
        if fd1.high == max_high and fd7.low == min_low:
            if fd2.low > fd4.high and fd4.low > fd6.high and fd7.power < fd5.power:
                v = FdSeven.L4A1.value    # 七笔类趋势底背驰

            if fd2.low > fd4.high and fd6.high < min(fd2.low, fd4.low) and fd7.power < fd1.power:
                v = FdSeven.L1A1.value  # "aAb式底背驰"

            if fd2.low > fd4.high and fd4.low > fd6.high and fd7.power < fd5.power:
                v = FdSeven.L2A1.value  # "aAbcd式底背驰"

        if min_low == fd3.low and fd1.high > fd3.high and max_high == max(fd1.high, fd4.high) \
                and fd5.high > fd7.high and fd5.low < fd7.low:
            v = FdSeven.L3A1.value  # "BaA式右侧底A"

        if min_low == fd3.low and fd2.low > fd4.low < fd6.low \
                and fd2.high > fd4.high < fd6.high and fd7.low > fd3.low and fd4.high > fd2.low:
            v = FdSeven.L3B1.value  # "BaA式右侧底B"

    elif fd7.direction == Direction.Up:
        if fd1.low == min_low and fd7.high == max_high:
            if fd2.high < fd4.low and fd4.high < fd6.low and fd7.power < fd5.power:
                v = FdSeven.S4A1.value  # "类趋势顶背驰"

            if fd4.low < fd2.high and fd6.low < fd2.high and fd7.power < fd1.power:
                v = FdSeven.S1A1.value  # "aAb式顶背驰"

            if fd4.low < fd2.high and fd6.low > max(fd4.high, fd2.high) and fd7.power < fd5.power:
                v = FdSeven.S2A1.value  # "aAbcd式顶背驰"

        if max_high == fd4.high and min_low == min(fd4.low, fd1.low) and fd6.high < fd2.low \
                and fd5.high > fd7.high and fd5.low < fd7.low and fd1.low < fd3.low:
            v = FdSeven.S3A1.value  # "BaA式右侧顶A"

        if max_high == fd4.high and fd2.high < fd4.high > fd6.high \
                and fd2.low < fd4.low > fd6.low and fd7.high < fd3.high and fd4.low < fd2.high:
            v = FdSeven.S3B1.value  # "BaA式右侧顶B"

    else:
        raise ValueError("direction 的取值错误")
    return v

def check_nine_fd(fds: List[BI]) -> str:
    """识别九段形态

    :param fds: list
        由远及近的九段形态
    :return: str
    """
    v = FdNine.Other.value
    if len(fds) != 9:
        warnings.warn("len(fdx) != 9，无法识别九段形态")
        return v

    direction = fds[-1].direction
    fd1, fd2, fd3, fd4, fd5, fd6, fd7, fd8, fd9 = fds
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if direction == Direction.Up:
        if min_low == fd1.low and max_high == fd9.high:
            if fd2.high < fd4.low and fd4.high < fd6.low and fd6.high < fd8.low and fd9.power < fd7.power:
                v = FdNine.S1A1.value   # 类趋势顶背驰

            if fd2.high < fd4.low and fd4.high < fd6.low and fd6.high > fd8.low:
                v = FdNine.S2A1.value   # 含有一个下上下方向中枢A

            if fd2.high < fd4.low and fd4.high > fd6.low and fd6.high < fd8.low:
                v = FdNine.S2B1.value   # 含有一个下上下方向中枢B

            if fd2.high > fd4.low and fd4.high < fd6.low and fd6.high < fd8.low:
                v = FdNine.S2C1.value   # 含有一个下上下方向中枢C

            if fd2.high > fd4.low and fd4.high < fd6.low \
                    and fd6.high > fd8.low > max(fd2.high, fd4.high)\
                    and fd6.low > max(fd2.high, fd4.high):
                v = FdNine.S3A1.value   # 标准aAbBc向上趋势

            if fd2.high < fd4.low and fd4.high > fd6.low and fd4.high > fd8.low:
                v = FdNine.S4A1.value   # 上中枢七段上涨

            if fd2.high > fd4.low and fd2.high > fd6.low and fd6.high < fd8.low:
                v = FdNine.S4B1.value   # 下中枢七段上涨
    elif direction == Direction.Down:
        if max_high == fd1.high and min_low == fd9.low:
            if fd2.low > fd4.high and fd4.low > fd6.high and fd6.low > fd8.high and fd9.power < fd7.power:
                v = FdNine.L1A1.value   # 类趋势底背驰

            if fd2.low > fd4.high and fd4.low > fd6.high and fd6.low < fd8.high:
                v = FdNine.L2A1.value   # 含有一个上下上方向中枢A
            if fd2.low > fd4.high and fd4.low < fd6.high and fd6.low > fd8.high:
                v = FdNine.L2B1.value   # 含有一个上下上方向中枢B
            if fd2.low < fd4.high and fd4.low > fd6.high and fd6.low > fd8.high:
                v = FdNine.L2C1.value   # 含有一个上下上方向中枢C

            if fd2.low < fd4.high and fd4.low > fd6.high \
                    and fd6.low < fd8.high < min(fd2.low, fd4.low)\
                    and fd6.high < min(fd2.low, fd4.low):
                v = FdNine.L3A1.value   # 标准aAbBc向下趋势

            if fd2.low < fd4.high and fd2.low < fd6.high and fd6.low > fd8.high:
                v = FdNine.L4A1.value   # 上中枢七段下跌
            if fd2.low > fd4.high and fd4.low < fd6.high and fd4.low < fd8.high:
                v = FdNine.L4B1.value   # 下中枢七段下跌
    else:
        raise ValueError("direction 的取值错误")
    return v
