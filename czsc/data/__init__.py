# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/24 16:17
describe: 数据工具
"""

from .ts_cache import TsDataCache
from . import ts
from .base import *


def get_symbols(dc: TsDataCache, step):
    """获取择时策略投研不同阶段对应的标的列表

    :param dc: 数据缓存
    :param step: 投研阶段
    :return:
    """
    stocks = dc.stock_basic()
    stocks_ = stocks[stocks['list_date'] < '2010-01-01'].ts_code.to_list()
    stocks_map = {
        "index": ['000905.SH', '000016.SH', '000300.SH', '000001.SH', '000852.SH',
                  '399001.SZ', '399006.SZ', '399376.SZ', '399377.SZ', '399317.SZ', '399303.SZ'],
        "stock": stocks.ts_code.to_list(),
        "check": ['000001.SZ'],
        "train": stocks_[:200],
        "valid": stocks_[200:600],
        "etfs": ['512880.SH', '518880.SH', '515880.SH', '513050.SH', '512690.SH',
                 '512660.SH', '512400.SH', '512010.SH', '512000.SH', '510900.SH',
                 '510300.SH', '510500.SH', '510050.SH', '159992.SZ', '159985.SZ',
                 '159981.SZ', '159949.SZ', '159915.SZ'],
    }

    asset_map = {
        "index": "I",
        "stock": "E",
        "check": "E",
        "train": "E",
        "valid": "E",
        "etfs": "FD"
    }
    asset = asset_map[step]
    symbols = [f"{ts_code}#{asset}" for ts_code in stocks_map[step]]
    return symbols



