# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/7 19:16
describe: 白仪 https://www.zhihu.com/people/bai-yi-520/posts 知乎上定义的一些信号

byi 是 bai yi 的缩写
"""
from typing import List
from czsc import CZSC
from collections import OrderedDict
from czsc.objects import BI, Direction, Mark
from czsc.utils import get_sub_elements, create_single_signal
from czsc.utils.sig import is_symmetry_zs


def byi_symmetry_zs_V221107(c: CZSC, di=1, **kwargs):
    """对称中枢信号

    **信号逻辑：**

    从di笔往前数7/5/3笔，如果构成中枢，且所有笔的力度序列标
    准差小于均值的一定比例，则认为是对称中枢

    **信号列表：**

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
    :return: s
    """
    bis: List[BI] = get_sub_elements(c.bi_list, di=di, n=10)
    k1, k2, k3 = f"{c.freq.value}_D{di}B_对称中枢".split("_")
    v1 = '其他'
    if len(bis) < 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    for i in (7, 5, 3):
        v1 = is_symmetry_zs(bis[-i:])
        if v1:
            v3 = f"{i}笔"
            break
        else:
            v3 = "任意"

    v1 = "是" if v1 else "否"
    v2 = "向上" if bis[-1].direction == Direction.Down else "向下"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def byi_bi_end_V230106(c: CZSC, **kwargs) -> OrderedDict:
    """白仪分型停顿辅助笔结束判断

    **信号逻辑：**

    分型停顿图解：https://pic1.zhimg.com/80/v2-3c5c3f264bffdf14c5ac6ae83bc5d5f0_720w.webp

    1. 白仪底分型停顿，认为是向下笔结束；反之，向上笔结束
    2. 底分型停顿：底分型后一根大阳线收盘在底分型的高点上方；反之，顶分型停顿

    **信号列表：**

    - Signal('15分钟_D0停顿分型_BE辅助V230106_看多_强_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230106_看空_强_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230106_看空_弱_任意_0')
    - Signal('15分钟_D0停顿分型_BE辅助V230106_看多_弱_任意_0')

    **Notes：**

    1. BE 是 Bi End 的缩写

    :param c: CZSC对象
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D0停顿分型_BE辅助V230106".split('_')
    v1 = "其他"

    if len(c.bi_list) < 3 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    bars = get_sub_elements(c.bars_raw, di=1, n=3)
    last_fx = last_bi.fx_b
    bar1, bar2, bar3 = bars

    lc1 = last_bi.direction == Direction.Down and last_fx.mark == Mark.D and bar1.low == last_fx.low
    if lc1 and bar3.close > max([x.high for x in last_fx.raw_bars]):
        v1 = "看多"
        v2 = "强" if bar3.close > bar3.open and bar3.solid > max(bar3.upper, bar3.lower) else "弱"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    sc1 = last_bi.direction == Direction.Up and last_fx.mark == Mark.G and bar1.high == last_fx.high
    if sc1 and bar3.close < min([x.low for x in last_fx.raw_bars]):
        v1 = "看空"
        v2 = "强" if bar3.close < bar3.open and bar3.solid > max(bar3.upper, bar3.lower) else "弱"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def byi_bi_end_V230107(c: CZSC, **kwargs) -> OrderedDict:
    """白仪验证分型辅助判断笔结束

    **信号逻辑：**

    验证分型图解：https://pic1.zhimg.com/80/v2-80ac88269286707db98a5560107da4ec_720w.webp

    1. 白仪验证底分型，认为是向下笔结束；反之，向上笔结束

    **信号列表：**

    - Signal('15分钟_D0验证分型_BE辅助V230107_看空_强_任意_0')
    - Signal('15分钟_D0验证分型_BE辅助V230107_看空_弱_任意_0')
    - Signal('15分钟_D0验证分型_BE辅助V230107_看多_弱_任意_0')
    - Signal('15分钟_D0验证分型_BE辅助V230107_看多_强_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D0验证分型_BE辅助V230107".split('_')

    v1 = "其他"
    if len(c.bi_list) < 3 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    fx1, fx2, fx3 = c.fx_list[-3], c.fx_list[-2], c.fx_list[-1]
    bar1 = c.bars_raw[-1]

    if not (last_bi.fx_b.dt == fx1.dt and fx1.mark == fx3.mark and bar1.dt == fx3.raw_bars[-1].dt):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _high = max([x.close for x in fx1.raw_bars + fx2.raw_bars])
    _low = min([x.close for x in fx1.raw_bars + fx2.raw_bars])

    lc1 = bar1.solid > max(bar1.upper, bar1.lower) and bar1.close > bar1.open and bar1.close > _high
    if last_bi.direction == Direction.Down and fx1.mark == Mark.D and fx3.low > fx1.low:
        v1 = "看多"
        v2 = "强" if lc1 else "弱"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    sc1 = bar1.solid > max(bar1.upper, bar1.lower) and bar1.close < bar1.open and bar1.close < _low
    if last_bi.direction == Direction.Up and fx1.mark == Mark.G and fx3.high < fx1.high:
        v1 = "看空"
        v2 = "强" if sc1 else "弱"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
