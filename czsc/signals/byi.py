# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/7 19:16
describe: 白仪 https://www.zhihu.com/people/bai-yi-520/posts 知乎上定义的一些信号

byi 是 bai yi 的缩写
"""
import numpy as np
from typing import List
from czsc import CZSC
from collections import OrderedDict
from czsc.objects import BI, Direction, Mark
from czsc.utils import get_sub_elements, create_single_signal
from czsc.utils.sig import is_symmetry_zs
from czsc.signals.tas import update_macd_cache, update_boll_cache_V230228, update_ma_cache


def byi_symmetry_zs_V221107(c: CZSC, **kwargs):
    """对称中枢信号

    参数模板："{freq}_D{di}B_对称中枢"

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
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
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

    参数模板："{freq}_D0停顿分型_BE辅助V230106"

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

    参数模板："{freq}_D0验证分型_BE辅助V230107"

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


def byi_second_bs_V230324(c: CZSC, **kwargs) -> OrderedDict:
    """白仪二类买卖点辅助V230324

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}回抽零轴_BS2辅助V230324"

    参考资料：https://zhuanlan.zhihu.com/p/550719065
    由于文字描述的比较模糊，笔的算法也有差异，这里的实现和原文有一定出入

    参数模板："{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}回抽零轴_BS2辅助V230324"

    **信号逻辑：**

    1. 二买定义：
        a. 1,3,5笔的dif值都小于0，且1,3,5笔的dif值中最大值小于-2倍标准差，且8笔的dif值大于0，且9笔的dif值小于0.3倍标准差
        b. 第9笔向下

    2. 二卖定义：
        a. 1,3,5笔的dif值都大于0，且1,3,5笔的dif值中最小值大于2倍标准差，且8笔的dif值小于0，且9笔的dif值大于-0.3倍标准差
        b. 第9笔向上

    **信号列表：**

    - Signal('15分钟_D1MACD12#26#9回抽零轴_BS2辅助V230324_看空_任意_任意_0')
    - Signal('15分钟_D1MACD12#26#9回抽零轴_BS2辅助V230324_看多_任意_任意_0')

    :param c: CZSC对象
    :param di: 从倒数第几笔开始检查
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    cache_key = update_macd_cache(c, **kwargs)
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}{cache_key}回抽零轴_BS2辅助V230324".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 10:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2, b3, b4, b5, b6, b7, b8, b9 = get_sub_elements(c.bi_list, di=di, n=9)
    b1_dif = b1.fx_b.raw_bars[1].cache[cache_key]['dif']
    b3_dif = b3.fx_b.raw_bars[1].cache[cache_key]['dif']
    b5_dif = b5.fx_b.raw_bars[1].cache[cache_key]['dif']
    b8_dif = b8.fx_b.raw_bars[1].cache[cache_key]['dif']
    b9_dif = b9.fx_b.raw_bars[1].cache[cache_key]['dif']
    dif_std = np.std([x.cache[cache_key]['dif'] for x in b1.raw_bars])

    if b9.direction == Direction.Down and max(b1_dif, b3_dif, b5_dif) < 0 \
            and min(b1_dif, b3_dif, b5_dif) < -dif_std * 2 < dif_std * 1 < b8_dif \
            and abs(b9_dif) < dif_std * 0.3:
        v1 = "看多"

    if b9.direction == Direction.Up and min(b1_dif, b3_dif, b5_dif) > 0 \
            and max(b1_dif, b3_dif, b5_dif) > dif_std * 2 > -dif_std * 1 > b8_dif \
            and abs(b9_dif) < dif_std * 0.3:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def byi_fx_num_V230628(c: CZSC, **kwargs) -> OrderedDict:
    """白仪前面下跌或上涨一笔次级别笔结构数量满足条件；贡献者：谌意勇

    参数模板："{freq}_D{di}笔分型数大于{num}_BE辅助V230628"

    **信号逻辑：**

    对于采用分型停顿或者分型验证开开仓，前一笔内部次级别笔结构尽量带结构，
    此信号函数为当分型笔数量判断大于 num 为满足条件

    **信号列表：**

    - Signal('15分钟_D1笔分型数大于4_BE辅助V230628_向下_满足_任意_0')
    - Signal('15分钟_D1笔分型数大于4_BE辅助V230628_向上_满足_任意_0')
    
    :param c: CZSC对象
    :param di: 从倒数第几笔开始检查
    :param num: 前笔内部次级别笔数量
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    num = int(kwargs.get('num', 4))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}笔分型数大于{num}_BE辅助V230628".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 1 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    
    bi = c.bi_list[-di]
    v1 = bi.direction.value
    v2 = "满足" if len(bi.fxs) >= num else "其他"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
