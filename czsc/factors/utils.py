# coding: utf-8

from typing import List, Set

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

