# coding: utf-8

from enum import Enum


class Operate(Enum):
    HL = "持多"  # Hold Long
    HS = "持空"  # Hold Short
    HO = "持币"  # Hold Other

    LO = "开多"  # Long Open
    LE = "平多"  # Long Exit

    SO = "开空"  # Short Open
    SE = "平空"  # Short Exit


class Mark(Enum):
    D = "底分型"
    G = "顶分型"


class Direction(Enum):
    Up = "向上"
    Down = "向下"


class Freq(Enum):
    Tick = "Tick"
    F1 = "1分钟"
    F5 = "5分钟"
    F15 = "15分钟"
    F30 = "30分钟"
    F60 = "60分钟"
    D = "日线"
    W = "周线"
    M = "月线"
    S = "季线"
    Y = "年线"
