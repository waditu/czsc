from enum import Enum
from czsc.objects import *
from typing import List


class CenterFrom(Enum):
    """
    中枢构成的方式
    """
    # 原始数据构造
    ORIGIN = 1
    # 中枢扩张
    CENTER_EXPAND = 2
    # 中枢延伸
    CENTER_STRETCH = 3


class Center:
    """
    中枢信息
    """

    def __init__(self, bars: List[RawBar], direction: Direction, source: CenterFrom,
                 main_center, expand_center,
                 level: int = 0):
        # 原始数据
        self.bar_raw = bars

        # 中枢构建方式
        self.source: CenterFrom = source
        # 中枢方向
        self.direction = direction
        # 级别
        self.level = level
        # 核心中枢
        self.main_center: Center = main_center
        # 扩张 中枢
        self.expand_center: Center = expand_center
