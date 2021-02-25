# coding: utf-8

import warnings
from typing import List
from .objects import Direction, BI
from .enum import Signals

def check_five_fd(fds: List[BI], x9_high: float, x9_low: float) -> str:
    """识别五段形态

    :param fds: 由远及近的五段走势
    :param x9_high: 由远及近的九段走势的最高点
    :param x9_low: 由远及近的九段走势的最低点
    :return: str
    """
    v = Signals.Other.value

    if len(fds) != 5:
        warnings.warn("len(fdx) != 5，无法识别五段形态")
        return v

    fd1, fd2, fd3, fd4, fd5 = fds
    if not (fd1.direction == fd3.direction == fd5.direction):
        print("1,3,5 的 direction 不一致，无法识别五段形态")
        return v
    direction = fd1.direction
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if direction == Direction.Down:
        assert x9_low <= min_low
        if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) and max_high == fd1.high and fd5.power < fd1.power:
            if (x9_low == fd3.low and fd5.low < fd1.low) or (x9_low == fd5.low):
                v = Signals.X5LA1.value
                if fd5.rsq > 0.8:
                    v = Signals.X5LA2.value
            elif (min_low == fd3.low and fd5.low < fd1.low) or (min_low == fd5.low):
                v = Signals.X5LA0.value
                if fd5.rsq > 0.8:
                    v = Signals.X5LA2.value

        if max(fd1.low, fd3.low) < min(fd1.high, fd3.high) < fd5.low:
            if min_low == x9_low:
                v = Signals.X5LB1.value
            else:
                v = Signals.X5LB0.value

        if fd4.high < fd2.low and fd5.power < fd3.power and max_high == fd1.high:
            if fd5.low == x9_low:
                v = Signals.X5LC1.value
            elif fd5.low == min_low:
                v = Signals.X5LC0.value

        if fd1.high < fd3.high < fd5.high and fd1.low > fd3.low > fd5.low:
            v = Signals.X5LD0.value

        if fd1.high > fd3.high > fd5.high and fd1.low < fd3.low < fd5.low:
            v = Signals.X5LE0.value

        if (x9_low == fd1.low and fd5.high > min(fd1.high, fd2.high) > fd5.low > fd1.low) \
                or (x9_low == fd3.low and fd5.high > min(fd3.high, fd4.high) > fd5.low > fd3.low):
            v = Signals.X5LF0.value

    elif direction == Direction.Up:
        assert x9_high >= max_high
        if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) and min_low == fd1.low and fd5.power < fd1.power:
            if (x9_high == fd3.high and fd5.high > fd1.high) or (x9_high == fd5.high):
                v = Signals.X5SA1.value
                if fd5.rsq > 0.8:
                    v = Signals.X5SA2.value
            elif (max_high == fd3.high and fd5.high > fd1.high) or (max_high == fd5.high):
                v = Signals.X5SA0.value
                if fd5.rsq > 0.8:
                    v = Signals.X5SA2.value

        if min(fd1.high, fd3.high) > max(fd1.low, fd3.low) > fd5.high:
            if max_high == x9_high:
                v = Signals.X5SB1.value
            else:
                v = Signals.X5SB0.value

        if min_low == fd1.low and fd5.power < fd1.power and fd4.low > fd2.high:
            if fd5.high == x9_high:
                v = Signals.X5SC1.value
            elif fd5.high == max_high:
                v = Signals.X5SC0.value

        if fd1.high < fd3.high < fd5.high and fd1.low > fd3.low > fd5.low:
            v = Signals.X5SD0.value

        if fd1.high > fd3.high > fd5.high and fd1.low < fd3.low < fd5.low:
            v = Signals.X5SE0.value

        if (x9_high == fd1.high and fd5.low < max(fd1.low, fd2.low) < fd5.high < fd1.high) \
                or (x9_high == fd3.high and fd5.low < max(fd3.low, fd4.low) < fd5.high < fd3.high):
            v = Signals.X5SF0.value

    else:
        raise ValueError("direction 的取值错误")
    return v

def check_seven_fd(fds: List[BI], x9_high: float, x9_low: float) -> str:
    """识别七段形态

    :param fds: 由远及近的七段走势
    :param x9_high: 由远及近的九段走势的最高点
    :param x9_low: 由远及近的九段走势的最低点
    :return: str
    """
    v = Signals.Other.value
    if len(fds) != 7:
        warnings.warn("len(fdx) != 7，无法识别七段形态")
        return v

    fd1, fd2, fd3, fd4, fd5, fd6, fd7 = fds
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if fd7.direction == Direction.Down:
        assert x9_low <= min_low
        if fd1.high == max_high and fd7.low == min_low:
            if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) > fd6.high and fd7.power < fd5.power:
                if x9_low == min_low:
                    v = Signals.X7LA1.value
                elif fd7.rsq > 0.8:
                    v = Signals.X7LA2.value
                else:
                    v = Signals.X7LA0.value

            if fd2.low > min(fd4.high, fd6.high) > max(fd4.low, fd6.low) and fd7.power < (fd1.high - fd3.low):
                if x9_low == min_low:
                    v = Signals.X7LB1.value
                elif fd7.rsq > 0.8:
                    v = Signals.X7LB2.value
                else:
                    v = Signals.X7LB0.value

            if min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) and fd7.power < fd1.power:
                if x9_low == min_low:
                    v = Signals.X7LC1.value
                elif fd7.rsq > 0.8:
                    v = Signals.X7LC2.value
                else:
                    v = Signals.X7LC0.value

            if fd2.low > fd4.high and fd4.low > fd6.high and fd7.power < fd5.power:
                if x9_low == min_low:
                    v = Signals.X7LD1.value
                else:
                    v = Signals.X7LD0.value

        if fd4.low == x9_low and min(fd1.high, fd3.high) > max(fd1.low, fd3.low) \
                and min(fd5.high, fd7.high) > max(fd5.low, fd7.low) \
                and max(fd4.high, fd6.high) > min(fd3.high, fd4.high):
            v = Signals.X7LE0.value

        if fd1.high == max_high and fd5.low == min_low and fd4.high < fd2.low and fd5.power < fd3.power \
                and fd6.high > fd5.high > fd7.low > fd6.low:
            v = Signals.X7LF0.value

    elif fd7.direction == Direction.Up:
        assert x9_high >= max_high
        if fd1.low == min_low and fd7.high == max_high:
            if fd6.low > min(fd2.high, fd4.high) > max(fd2.low, fd4.low) and fd7.power < fd5.power:
                if x9_high == max_high:
                    v = Signals.X7SA1.value
                elif fd7.rsq > 0.8:
                    v = Signals.X7SA2.value
                else:
                    v = Signals.X7SA0.value

            if min(fd4.high, fd6.high) > max(fd4.low, fd6.low) > fd2.high and fd7.power < (fd3.high - fd1.low):
                if x9_high == max_high:
                    v = Signals.X7SB1.value
                elif fd7.rsq > 0.8:
                    v = Signals.X7SB2.value
                else:
                    v = Signals.X7SB0.value

            if min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) and fd7.power < fd1.power:
                if x9_high == max_high:
                    v = Signals.X7SC1.value
                elif fd7.rsq > 0.8:
                    v = Signals.X7SC2.value
                else:
                    v = Signals.X7SC0.value

            if fd2.high < fd4.low and fd4.high < fd6.low and fd7.power < fd5.power:
                if x9_high == max_high:
                    v = Signals.X7SD1.value
                else:
                    v = Signals.X7SD0.value

        if fd4.high == x9_high and min(fd1.high, fd3.high) > max(fd1.low, fd3.low) \
                and min(fd5.high, fd7.high) > max(fd5.low, fd7.low) \
                and min(fd4.low, fd6.low) < max(fd3.low, fd4.low):
            v = Signals.X7SE0.value

        if fd1.low == min_low and fd5.high == max_high and fd4.low > fd2.high and fd5.power < fd3.power \
                and fd6.low < fd5.low < fd7.high < fd6.high:
            v = Signals.X7SF0.value
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
        warnings.warn("len(fdx) != 9，无法识别九段形态")
        return v

    direction = fds[-1].direction
    fd1, fd2, fd3, fd4, fd5, fd6, fd7, fd8, fd9 = fds
    max_high = max([x.high for x in fds])
    min_low = min([x.low for x in fds])

    if direction == Direction.Down:
        if min_low == fd9.low and max_high == fd1.high:

            if min(fd2.high, fd4.high) > max(fd2.low, fd4.low) > fd6.high \
                    and min(fd6.high, fd8.high) > max(fd6.low, fd8.low) \
                    and min(fd2.low, fd4.low) > max(fd6.high, fd8.high) \
                    and fd9.power < fd5.power:
                v = Signals.X9LA0.value

            if min(fd2.high, fd4.high, fd6.high, fd8.high) > max(fd2.low, fd4.low, fd6.low, fd8.low) \
                    and fd9.power < fd1.power:
                v = Signals.X9LB0.value

            if min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) > fd8.high \
                    and fd9.power < fd7.power:
                v = Signals.X9LC0.value

    elif direction == Direction.Up:
        if max_high == fd9.high and min_low == fd1.low:

            if fd6.low > min(fd2.high, fd4.high) > max(fd2.low, fd4.low) \
                    and min(fd6.high, fd8.high) > max(fd6.low, fd8.low) \
                    and max(fd2.high, fd4.high) < min(fd6.low, fd8.low) \
                    and fd9.power < fd5.power:
                v = Signals.X9SA0.value

            if min(fd2.high, fd4.high, fd6.high, fd8.high) > max(fd2.low, fd4.low, fd6.low, fd8.low) \
                    and fd9.power < fd1.power:
                v = Signals.X9SB0.value

            if fd8.low > min(fd2.high, fd4.high, fd6.high) > max(fd2.low, fd4.low, fd6.low) \
                    and fd9.power < fd7.power:
                v = Signals.X9SC0.value

    else:
        raise ValueError("direction 的取值错误")
    return v
