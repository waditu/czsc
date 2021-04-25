# coding: utf-8

import warnings
from typing import List
from .objects import Direction, BI
from .enum import Signals

def check_three_fd(fds: List[BI]) -> str:
    """识别三段形态
    :param fds: list
        由远及近的三段形态
    :return: str
    """
    v = Signals.Other.value

    if len(fds) != 3:
        return v

    fd1, fd2, fd3 = fds
    if not (fd1.direction == fd3.direction):
        print("1,3的 direction 不一致，无法识别三段形态")
        return v

    if fd3.direction == Direction.Down:
        if fd3.low > fd1.high:
            v = Signals.X3LA0.value

        if fd2.low < fd3.low < fd1.high < fd2.high:
            v = Signals.X3LB0.value

        if fd1.high > fd3.high and fd1.low < fd3.low:
            v = Signals.X3LC0.value

        if fd1.high < fd3.high and fd1.low > fd3.low:
            v = Signals.X3LD0.value

        if fd3.low < fd1.low and fd3.high < fd1.high:
            if fd3.power < fd1.power:
                v = Signals.X3LE0.value
            else:
                v = Signals.X3LF0.value
    elif fd3.direction == Direction.Up:
        if fd3.high > fd1.low:
            v = Signals.X3SA0.value

        if fd2.low < fd1.low < fd3.high < fd2.high:
            v = Signals.X3SB0.value

        if fd1.high > fd3.high and fd1.low < fd3.low:
            v = Signals.X3SC0.value

        if fd1.high < fd3.high and fd1.low > fd3.low:
            v = Signals.X3SD0.value

        if fd3.low > fd1.low and fd3.high > fd1.high:
            if fd3.power < fd1.power:
                v = Signals.X3SE0.value
            else:
                v = Signals.X3SF0.value
    else:
        raise ValueError("direction 的取值错误")

    return v

def check_five_fd(fds: List[BI]) -> str:
    """识别五段形态

    :param fds: 由远及近的五段走势
    :return: str
    """
    v = Signals.Other.value

    if len(fds) != 5:
        return v

    fd1, fd2, fd3, fd4, fd5 = fds
    if not (fd1.direction == fd3.direction == fd5.direction):
        print("1,3,5 的 direction 不一致，无法识别五段形态")
        return v
    direction = fd1.direction
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if direction == Direction.Down:
        if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) and max_high == fd1.high and fd5.power < fd1.power:
            if (min_low == fd3.low and fd5.low < fd1.low) or (min_low == fd5.low):
                v = Signals.LA0.value

        if max(fd1.low, fd3.low) < min(fd1.high, fd3.high) < fd5.low:
            v = Signals.LI0.value

        if fd4.high < fd2.low and fd5.power < fd3.power and max_high == fd1.high:
            v = Signals.LF0.value

        if fd1.high < fd3.high < fd5.high and fd1.low > fd3.low > fd5.low:
            v = Signals.LJ0.value

        if fd1.high > fd3.high > fd5.high and fd1.low < fd3.low < fd5.low:
            v = Signals.LK0.value

        if (min_low == fd1.low and fd5.high > min(fd1.high, fd2.high) > fd5.low > fd1.low) \
                or (min_low == fd3.low and fd5.high > min(fd3.high, fd4.high) > fd5.low > fd3.low):
            v = Signals.LG0.value

    elif direction == Direction.Up:
        if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) and min_low == fd1.low and fd5.power < fd1.power:
            if (max_high == fd3.high and fd5.high > fd1.high) or (max_high == fd5.high):
                v = Signals.SA0.value

        if min(fd1.high, fd3.high) > max(fd1.low, fd3.low) > fd5.high:
            v = Signals.SI0.value

        if min_low == fd1.low and fd5.power < fd1.power and fd4.low > fd2.high:
            v = Signals.SF0.value

        if fd1.high < fd3.high < fd5.high and fd1.low > fd3.low > fd5.low:
            v = Signals.SJ0.value

        if fd1.high > fd3.high > fd5.high and fd1.low < fd3.low < fd5.low:
            v = Signals.SK0.value

        if (max_high == fd1.high and fd5.low < max(fd1.low, fd2.low) < fd5.high < max_high) \
                or (max_high == fd3.high and fd5.low < max(fd3.low, fd4.low) < fd5.high < max_high):
            v = Signals.SG0.value

    else:
        raise ValueError("direction 的取值错误")
    return v

def check_seven_fd(fds: List[BI]) -> str:
    """识别七段形态

    :param fds: 由远及近的七段走势
    :return: str
    """
    v = Signals.Other.value
    if len(fds) != 7:
        return v

    fd1, fd2, fd3, fd4, fd5, fd6, fd7 = fds
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if fd7.direction == Direction.Down:
        if fd1.high == max_high and fd7.low == min_low:
            if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) > fd6.high and fd7.power < fd5.power:
                v = Signals.LB0.value

            if fd2.low > min(fd4.high, fd6.high) > max(fd4.low, fd6.low) and fd7.power < (fd1.high - fd3.low):
                v = Signals.LD0.value

            if min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) and fd7.power < fd1.power:
                v = Signals.LA0.value

            if fd2.low > fd4.high and fd4.low > fd6.high and fd7.power < fd5.power:
                v = Signals.LF0.value

        if fd4.low == min_low and min(fd1.high, fd3.high) > max(fd1.low, fd3.low) \
                and min(fd5.high, fd7.high) > max(fd5.low, fd7.low) \
                and max(fd4.high, fd6.high) > min(fd3.high, fd4.high):
            if max(fd1.high, fd3.high) < max(fd5.high, fd7.high):
                v = Signals.LH1.value
            else:
                v = Signals.LH0.value

    elif fd7.direction == Direction.Up:
        if fd1.low == min_low and fd7.high == max_high:
            if fd6.low > min(fd2.high, fd4.high) > max(fd2.low, fd4.low) and fd7.power < fd5.power:
                v = Signals.SB0.value

            if min(fd4.high, fd6.high) > max(fd4.low, fd6.low) > fd2.high and fd7.power < (fd3.high - fd1.low):
                v = Signals.SD0.value

            if min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) and fd7.power < fd1.power:
                v = Signals.SA0.value

            if fd2.high < fd4.low and fd4.high < fd6.low and fd7.power < fd5.power:
                v = Signals.SF0.value

        if fd4.high == max_high and min(fd1.high, fd3.high) > max(fd1.low, fd3.low) \
                and min(fd5.high, fd7.high) > max(fd5.low, fd7.low) \
                and min(fd4.low, fd6.low) < max(fd3.low, fd4.low):
            if min(fd1.low, fd3.low) > min(fd5.low, fd7.low):
                v = Signals.SH1.value
            else:
                v = Signals.SH0.value

    else:
        raise ValueError("direction 的取值错误")
    return v

def check_nine_fd(fds: List[BI]) -> str:
    """识别九段形态

    :param fds: list
        由远及近的九段形态
    :return: str
    """
    v = Signals.Other.value
    if len(fds) != 9:
        return v

    direction = fds[-1].direction
    fd1, fd2, fd3, fd4, fd5, fd6, fd7, fd8, fd9 = fds
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if direction == Direction.Down:
        if min_low == fd9.low and max_high == fd1.high:
            # aAbBc式底背弛
            if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) > fd6.high \
                    and min(fd6.high, fd8.high) > max(fd6.low, fd8.low) \
                    and min(fd2.low, fd4.low) > max(fd6.high, fd8.high) \
                    and fd9.power < fd5.power:
                v = Signals.LC0.value

            if min(fd2.high, fd4.high, fd6.high, fd8.high) > max(fd2.low, fd4.low, fd6.low, fd8.low) \
                    and fd9.power < fd1.power and fd3.low >= fd1.low and fd7.high <= fd9.high:
                v = Signals.LA0.value

            if min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) > fd8.high \
                    and fd9.power < fd7.power:
                v = Signals.LB0.value

            if fd3.low < fd1.low and fd7.high > fd9.high \
                    and min(fd4.high, fd6.high) > max(fd4.low, fd6.low) \
                    and (fd1.high - fd3.low) > (fd7.high - fd9.low):
                v = Signals.LE0.value

    elif direction == Direction.Up:
        if max_high == fd9.high and min_low == fd1.low:
            # aAbBc式顶背驰
            if fd6.low > min(fd2.high, fd4.high) > max(fd2.low, fd4.low) \
                    and min(fd6.high, fd8.high) > max(fd6.low, fd8.low) \
                    and max(fd2.high, fd4.high) < min(fd6.low, fd8.low) \
                    and fd9.power < fd5.power:
                v = Signals.SC0.value

            if min(fd2.high, fd4.high, fd6.high, fd8.high) > max(fd2.low, fd4.low, fd6.low, fd8.low) \
                    and fd9.power < fd1.power and fd3.high <= fd1.high and fd7.low >= fd9.low:
                v = Signals.SA0.value

            if fd8.low > min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) \
                    and fd9.power < fd7.power:
                v = Signals.SB0.value

            if fd3.high > fd1.high and fd7.low < fd9.low \
                    and min(fd4.high, fd6.high) > max(fd4.low, fd6.low) \
                    and (fd3.high - fd1.low) > (fd9.high - fd7.low):
                v = Signals.SE0.value

    else:
        raise ValueError("direction 的取值错误")
    return v

def check_eleven_fd(fds: List[BI]) -> str:
    """识别十一段形态

    :param fds: list
        由远及近的十一段形态
    :return: str
    """
    v = Signals.Other.value
    if len(fds) != 11:
        return v

    direction = fds[-1].direction
    fd1, fd2, fd3, fd4, fd5, fd6, fd7, fd8, fd9, fd10, fd11 = fds
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if direction == Direction.Down:
        if min_low == fd11.low and max_high == fd1.high:
            # aAbBc式底背弛，fd2-fd6构成A
            if min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) > fd8.high \
                    and min(fd8.high, fd10.high) > max(fd8.low, fd10.low) \
                    and min(fd2.low, fd4.low, fd6.low) > max(fd8.high, fd10.high) \
                    and fd11.power < fd7.power:
                # v = Signals.LC0.value
                v = Signals.LC1.value

            # aAbBc式底背弛，fd6-fd10构成B
            if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) > fd6.high \
                    and min(fd6.high, fd8.high, fd10.high) > max(fd6.low, fd8.low, fd10.low) \
                    and min(fd2.low, fd4.low) > max(fd6.high, fd8.high, fd10.high) \
                    and fd11.power < fd5.power:
                # v = Signals.LC0.value
                v = Signals.LC1.value

            # ABC式底背驰，fd1-fd5构成A
            if fd5.low == min([x.low for x in [fd1, fd3, fd5]]) \
                    and fd9.low > fd11.low and fd9.high > fd11.high \
                    and fd8.high > fd6.low and fd1.high - fd5.low > fd9.high - fd11.low:
                # v = Signals.LE0.value
                v = Signals.LE1.value

            # ABC式底背驰，fd7-fd11构成C
            if fd1.high > fd3.high and fd1.low > fd3.low \
                    and fd7.high == max([x.high for x in [fd7, fd9, fd11]]) \
                    and fd6.high > fd4.low and fd1.high - fd3.low > fd7.high - fd11.low:
                # v = Signals.LE0.value
                v = Signals.LE1.value

    elif direction == Direction.Up:
        if max_high == fd11.high and min_low == fd1.low:
            # aAbBC式顶背驰，fd2-fd6构成A
            if fd8.low > min(fd2.high, fd4.high, fd6.high) >= max(fd2.low, fd4.low, fd6.low) \
                    and min(fd8.high, fd10.high) >= max(fd8.low, fd10.low) \
                    and max(fd2.high, fd4.high, fd6.high) < min(fd8.low, fd10.low) \
                    and fd11.power < fd7.power:
                # v = Signals.SC0.value
                v = Signals.SC1.value

            # aAbBC式顶背驰，fd6-fd10构成B
            if fd6.low > min(fd2.high, fd4.high) >= max(fd2.low, fd4.low) \
                    and min(fd6.high, fd8.high, fd10.high) >= max(fd6.low, fd8.low, fd10.low) \
                    and max(fd2.high, fd4.high) < min(fd6.low, fd8.low, fd10.low) \
                    and fd11.power < fd7.power:
                # v = Signals.SC0.value
                v = Signals.SC1.value

            # ABC式顶背驰，fd1-fd5构成A
            if fd5.high == max([fd1.high, fd3.high, fd5.high]) and fd9.low < fd11.low and fd9.high < fd11.high \
                    and fd8.low < fd6.high and fd11.high - fd9.low < fd5.high - fd1.low:
                # v = Signals.SE0.value
                v = Signals.SE1.value

            # ABC式顶背驰，fd7-fd11构成C
            if fd7.low == min([fd11.low, fd9.low, fd7.low]) and fd1.high < fd3.high and fd1.low < fd3.low \
                    and fd6.low < fd4.high and fd11.high - fd7.low < fd3.high - fd1.low:
                # v = Signals.SE0.value
                v = Signals.SE1.value
    else:
        raise ValueError("direction 的取值错误")
    return v

