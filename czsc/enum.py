# coding: utf-8
from enum import Enum


class Operate(Enum):
    # 持有状态
    HL = "持多"  # Hold Long
    HS = "持空"  # Hold Short
    HO = "持币"  # Hold Other

    # 多头操作
    LO = "开多"  # Long Open
    LE = "平多"  # Long Exit

    # 空头操作
    SO = "开空"  # Short Open
    SE = "平空"  # Short Exit

    def __str__(self):
        return self.value


class Mark(Enum):
    D = "底分型"
    G = "顶分型"

    def __str__(self):
        return self.value


class Direction(Enum):
    Up = "向上"
    Down = "向下"

    def __str__(self):
        return self.value


class Freq(Enum):
    Tick = "Tick"
    F1 = "1分钟"
    F2 = "2分钟"
    F3 = "3分钟"
    F4 = "4分钟"
    F5 = "5分钟"
    F6 = "6分钟"
    F10 = "10分钟"
    F12 = "12分钟"
    F15 = "15分钟"
    F20 = "20分钟"
    F30 = "30分钟"
    F60 = "60分钟"
    F120 = "120分钟"
    D = "日线"
    W = "周线"
    M = "月线"
    S = "季线"
    Y = "年线"

    def __str__(self):
        return self.value
