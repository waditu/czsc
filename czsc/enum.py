# coding: utf-8

from enum import Enum


class Operate(Enum):
    # 持有状态
    HL = "持多"  # Hold Long
    HS = "持空"  # Hold Short
    HO = "持币"  # Hold Other

    # 多头操作
    LO = "开多"          # Long Open
    LE = "平多"          # Long Exit
    LA1 = "第一次加多仓"  # Long Add 1
    LA2 = "第二次加多仓"  # Long Add 2
    LR1 = "第一次减多仓"  # Long Reduce 1
    LR2 = "第二次减多仓"  # Long Reduce 2

    # 空头操作
    SO = "开空"          # Short Open
    SE = "平空"          # Short Exit
    SA1 = "第一次加空仓"  # Short Add 1
    SA2 = "第二次加空仓"  # Short Add 2
    SR1 = "第一次减空仓"  # Short Reduce 1
    SR2 = "第二次减空仓"  # Short Reduce 2


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
