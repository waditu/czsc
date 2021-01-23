# coding: utf-8
from dataclasses import dataclass
from datetime import datetime
from typing import List
from .enum import Mark, Direction

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
class RawBar:
    """原始K线元素"""
    symbol: str
    dt: datetime = None
    # freq: str = None
    open: [float, int] = None
    close: [float, int] = None
    high: [float, int] = None
    low: [float, int] = None
    vol: [float, int] = None

@dataclass
class NewBar:
    """去除包含关系的K线元素"""
    symbol: str
    dt: datetime = None
    # freq: str = None
    open: [float, int] = None
    close: [float, int] = None
    high: [float, int] = None
    low: [float, int] = None
    vol: [float, int] = None
    elements: List[RawBar] = None   # 存入具有包含关系的原始K线

@dataclass
class FX:
    symbol: str
    dt: datetime = None
    mark: Mark = None
    high: float = None
    low: float = None
    fx: float = None
    power: str = None
    elements: List[NewBar] = None

@dataclass
class BI:
    symbol: str
    fx_a: FX = None    # 笔开始的分型
    fx_b: FX = None    # 笔结束的分型
    direction: Direction = None
    high: float = None
    low: float = None
    power: float = None
    bars: List[NewBar] = None



