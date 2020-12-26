# coding: utf-8

from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import List

class Mark(Enum):
    D = "底分型"
    G = "顶分型"

class Direction(Enum):
    Up = "向上"
    Down = "向下"

@dataclass
class Tick:
    symbol: str
    name: str = ""
    volume: float = 0
    open_interest: float = 0
    last_price: float = 0
    last_volume: float = 0
    limit_up: float = 0
    limit_down: float = 0

    open_price: float = 0
    high_price: float = 0
    low_price: float = 0
    pre_close: float = 0

@dataclass
class Bar1:
    """原始K线元素"""
    symbol: str
    dt: datetime
    freq: str
    open: float
    close: float
    high: float
    low: float
    vol: float

@dataclass
class Bar2:
    """去除包含关系的K线元素"""
    symbol: str
    dt: datetime
    freq: str
    open: float
    close: float
    high: float
    low: float
    vol: float
    elements: List[Bar1] = None

@dataclass
class FX:
    symbol: str
    dt: datetime
    mark: Mark
    high: float = None
    low: float = None
    elements: List[Bar2] = None


@dataclass
class BI:
    symbol: str
    fx_a: FX    # 笔开始的分型
    fx_b: FX    # 笔结束的分型
    direction: Direction
    high: float = None
    low: float = None
    elements: List[FX] = None




