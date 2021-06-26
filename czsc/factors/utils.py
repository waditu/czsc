# coding: utf-8

from typing import List, Set, Dict, OrderedDict

def has_interaction(v1: [List, Set], v2: [List, Set]) -> bool:
    """判断 v1 和 v2 是否存在交集

    :param v1:
    :param v2:
    :return:
    """
    if set(v1).intersection(set(v2)):
        return True
    else:
        return False


def match_factor(s: [Dict, OrderedDict], factor: List[str]) -> bool:
    """判断是否满足组合信号构成的因子

    :param s: 所有级别的信号
    :param factor: 信号组合构成的因子，以‘且’关系进行组合
        输入案例：factor = ['15分钟_倒5形态#LA0~aAb式底背驰', '15分钟_倒1形态#LG0~上颈线突破']
    :return: bool
    """
    for signal in factor:
        key, value = signal.split("#")
        if str(s[key]) != value:
            return False
    return True

def match_factors(s: [Dict, OrderedDict], factors: List[List[str]]) -> bool:
    """判断是否满足多个组合信号构成的因子

    :param s: 所有级别的信号
    :param factors:
        输入案例：factors = [
            ['15分钟_倒5形态#LA0~aAb式底背驰', '15分钟_倒1形态#LG0~上颈线突破'],
        ]
    :return: bool
    """
    for factor in factors:
        if match_factor(s, factor):
            return True
    return False
