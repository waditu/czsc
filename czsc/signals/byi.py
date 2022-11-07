# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/7 19:16
describe: 白仪 https://www.zhihu.com/people/bai-yi-520/posts 知乎上定义的一些信号

byi 是 bai yi 的缩写
"""
from collections import OrderedDict
from typing import List
from czsc import CZSC
from czsc.objects import Signal, BI, Direction
from czsc.utils import get_sub_elements
from czsc.utils.sig import is_symmetry_zs


def byi_symmetry_zs_V2211007(c: CZSC, di=1):
    """对称中枢信号

    信号逻辑：
    从di笔往前数7/5/3笔，如果构成中枢，且所有笔的力度序列标
    准差小于均值的一定比例，则认为是对称中枢

    信号列表：
    - Signal('15分钟_D1B_对称中枢_否_向下_任意_0')
    - Signal('15分钟_D1B_对称中枢_是_向上_7笔_0')
    - Signal('15分钟_D1B_对称中枢_否_向上_任意_0')
    - Signal('15分钟_D1B_对称中枢_是_向下_3笔_0')
    - Signal('15分钟_D1B_对称中枢_是_向上_3笔_0')
    - Signal('15分钟_D1B_对称中枢_是_向下_5笔_0')
    - Signal('15分钟_D1B_对称中枢_是_向上_5笔_0')
    - Signal('15分钟_D1B_对称中枢_是_向下_7笔_0')

    :param c: CZSC对象
    :param di: 倒数第 di 笔
    :return:
    """
    bis: List[BI] = get_sub_elements(c.bi_list, di=di, n=10)
    k1, k2, k3 = f"{c.freq.value}_D{di}B_对称中枢".split("_")
    for i in (7, 5, 3):
        v1 = is_symmetry_zs(bis[-i:])
        if v1:
            v3 = f"{i}笔"
            break
        else:
            v3 = "任意"

    v1 = "是" if v1 else "否"
    v2 = "向上" if bis[-1].direction == Direction.Down else "向下"

    s = OrderedDict()
    x1 = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)
    s[x1.key] = x1.value
    return s



