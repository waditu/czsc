
from typing import List
from .factors import CzscFactors, factors_all
from ..enum import Factors
from .trader import CzscTrader


def get_trade_factors(name: str,
                      mp: float,
                      allow_zero: bool,
                      long_open_values: List,
                      long_close_values: List,
                      short_open_values: List = None,
                      short_close_values: List = None) -> dict:
    """获取指定 name 下的交易因子

    :param allow_zero: 是否使用基础型
    :param name: 因子系统的名称
    :param mp: 单个标的最大允许持仓，小于0表示仓位百分比，大于0表示手数
    :param long_open_values: 开多因子值
    :param long_close_values: 平多因子值
    :param short_open_values: 开空因子值
    :param short_close_values: 平空因子值
    :return: 因子交易系统

    example:
    ===================
    >>> factors = get_trade_factors(name="日线笔结束", long_open_values=['BDE'], long_close_values=['BUE'])
    """
    if not short_close_values:
        short_close_values = []

    if not short_open_values:
        short_open_values = []

    def __is_match(v, x):
        if allow_zero:
            if v in x.name:
                return 1
            else:
                return 0
        else:
            if v in x.name and "0" not in x.name:
                return 1
            else:
                return 0

    long_open_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                         if sum([__is_match(v, x) for v in long_open_values]) > 0]

    long_close_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                          if sum([__is_match(v, x) for v in long_close_values]) > 0]

    short_open_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                          if sum([__is_match(v, x) for v in short_open_values]) > 0]

    short_close_factors = ["{}@{}".format(name, x.value) for x in Factors.__members__.values()
                           if sum([__is_match(v, x) for v in short_close_values]) > 0]

    factors_ = {
        "name": name,
        "version": factors_all[name].__name__,
        "mp": mp,
        "long_open_factors": long_open_factors,
        "long_close_factors": long_close_factors,
        "short_open_factors": short_open_factors,
        "short_close_factors": short_close_factors,
    }
    return factors_


