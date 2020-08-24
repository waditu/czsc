# coding: utf-8
"""
对象设计

"""

from datetime import datetime

fx = {
    "dt": datetime.now(),
    "fx_mark": 'd',     # 可选值 d, g
    "fx": 10.0,
    # "right": [],    # fx 对象 right 存储K线
    "start_dt": datetime.now(),
    "end_dt": datetime.now(),
    "fx_high": 11.0,
    "fx_low": 9.0,
}


bi = {
    "dt": datetime.now(),
    "fx_mark": 'd',
    "bi": 9.0,
    # "right": [],    # bi 对象 right 存储 fx 对象，必须以一个能够构成笔的分型开始，且以一个能够构成笔的分型结束
}

xd = {
    "dt": datetime.now(),
    "fx_mark": 'd',
    "xd": 9.0,
    # "right": [],    # xd 对象 right 存储 bi 对象，必须以一个能够构成笔的分型开始，且以一个能够构成笔的分型结束
}


zs = {
    'ZD': 10.0,
    "ZG": 11.0,
    'G': 10.5,
    'GG': 12,
    'D': 10.2,
    'DD': 9.0,
    'start_point': {},
    'end_point': {},
    "points": [],   # 元素为点标记
    "zn": [],       # 元素为与中枢方向相反的走势段
    "third_sell": {},
    "third_buy": {},
}






