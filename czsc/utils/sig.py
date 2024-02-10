# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/27 23:23
describe: 用于信号计算函数的各种辅助工具函数
"""
import numpy as np
from collections import Counter, OrderedDict
from typing import List, Any, Dict, Union, Tuple
from czsc.enum import Direction
from czsc.objects import BI, RawBar, ZS, Signal


def create_single_signal(**kwargs) -> OrderedDict:
    """创建单个信号"""
    s = OrderedDict()
    k1, k2, k3 = kwargs.get('k1', '任意'), kwargs.get('k2', '任意'), kwargs.get('k3', '任意')
    v1, v2, v3 = kwargs.get('v1', '任意'), kwargs.get('v2', '任意'), kwargs.get('v3', '任意')
    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3, score=kwargs.get('score', 0))
    s[v.key] = v.value
    return s


def is_symmetry_zs(bis: List[BI], th: float = 0.3) -> bool:
    """对称中枢判断：中枢中所有笔的力度序列，标准差小于均值的一定比例

    https://pic2.zhimg.com/80/v2-2f55ef49eda01972462531ebb6de4f19_1440w.jpg

    :param bis: 构成中枢的笔序列
    :param th: 标准差小于均值的比例阈值
    :return:
    """
    if len(bis) % 2 == 0:
        return False

    zs = ZS(bis=bis)
    if zs.zd > zs.zg or max([x.low for x in bis]) > min([x.high for x in bis]):
        return False

    zns = [x.power_price for x in bis]
    if np.std(zns) / np.mean(zns) <= th:
        return True
    else:
        return False


def check_cross_info(fast: [List, np.array], slow: [List, np.array]):
    """计算 fast 和 slow 的交叉信息

    :param fast: 快线
    :param slow: 慢线
    :return:
    """
    assert len(fast) == len(slow), "快线和慢线的长度不一样"

    if isinstance(fast, list):
        fast = np.array(fast)
    if isinstance(slow, list):
        slow = np.array(slow)

    length = len(fast)
    delta = fast - slow
    cross_info = []
    last_i = -1
    last_v = 0
    temp_fast = []
    temp_slow = []
    for i, v in enumerate(delta):
        last_i += 1
        last_v += abs(v)
        temp_fast.append(fast[i])
        temp_slow.append(slow[i])

        if i >= 2 and delta[i - 1] <= 0 < delta[i]:
            kind = "金叉"
        elif i >= 2 and delta[i - 1] >= 0 > delta[i]:
            kind = "死叉"
        else:
            continue

        cross_info.append({'位置': i, "类型": kind, "快线": fast[i], "慢线": slow[i],
                           "距离": last_i, '距今': length - i,
                           "面积": round(last_v, 4), '价差': round(v, 4),
                           "快线高点": max(temp_fast), "快线低点": min(temp_fast),
                           "慢线高点": max(temp_slow), "慢线低点": min(temp_slow),
                           })
        last_i = 0
        last_v = 0
        temp_fast = []
        temp_slow = []

    return cross_info


def check_pressure_support(bars: List[RawBar], q_seq: List[float] = None) -> Dict:
    """检查 bars 中的支撑、压力信息

    1. 通过 round 函数对 K 线价格序列进行近似，统计价格出现次数，取出现次数超过5次的价位
    2. 在出现次数最多的价格序列上计算分位数序列作为关键价格序列

    :param bars: K线序列，按时间升序
    :param q_seq: 分位数序列
    :return:
    """

    assert len(bars) >= 300, "分析至少需要300根K线"
    min_low = min(x.low for x in bars)
    price_seq = [y for x in bars for y in (x.open, x.close, x.high, x.low)]
    price_seq = [round(x, 0) if min_low > 100 else round(x, 1) for x in price_seq]

    lines = sorted([x for x, v in Counter(price_seq).most_common() if v >= 5])
    q_seq = q_seq if q_seq else [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
    key_price = [np.quantile(lines, i, method='nearest') for i in q_seq]
    kp_low = [x for x in key_price if x <= bars[-1].close]
    kp_high = [x for x in key_price if x >= bars[-1].close]

    info = {
        "关键位": key_price,
        "支撑位": kp_low,
        "压力位": kp_high,
        "第一支撑": kp_low[-1] if len(kp_low) >= 1 else -1,
        "第二支撑": kp_low[-2] if len(kp_low) >= 2 else -1,
        "第一压力": kp_high[0] if len(kp_high) >= 1 else -1,
        "第二压力": kp_high[1] if len(kp_high) >= 2 else -1,
    }
    return info


def check_gap_info(bars: List[RawBar]):
    """检查 bars 中的缺口信息

    :param bars: K线序列，按时间升序
    :return:
    """
    gap_info = []
    if len(bars) < 2:
        return gap_info

    for i in range(1, len(bars)):
        bar1, bar2 = bars[i-1], bars[i]
        right = bars[i:]

        gap = None
        if bar1.high < bar2.low:
            delta = round(bar2.low / bar1.high - 1, 4)
            cover = "已补" if min(x.low for x in right) < bar1.high else "未补"
            gap = {"kind": "向上缺口", 'cover': cover, 'sdt': bar1.dt, 'edt': bar2.dt,
                   'high': bar2.low, 'low': bar1.high, 'delta': delta}

        if bar1.low > bar2.high:
            delta = round(bar1.low / bar2.high - 1, 4)
            cover = "已补" if max(x.high for x in right) > bar1.low else "未补"
            gap = {"kind": "向下缺口", 'cover': cover, 'sdt': bar1.dt, 'edt': bar2.dt,
                   'high': bar1.low, 'low': bar2.high, 'delta': delta}

        if gap:
            gap_info.append(gap)

    return gap_info


def fast_slow_cross(fast, slow):
    """计算 fast 和 slow 的交叉信息

    :param fast: 快线
    :param slow: 慢线
    :return:
    """
    assert len(fast) == len(slow), "快线和慢线的长度不一样"

    if isinstance(fast, list):
        fast = np.array(fast)
    if isinstance(slow, list):
        slow = np.array(slow)

    length = len(fast)
    delta = fast - slow
    cross_info = []
    last_i = -1
    last_v = 0
    temp_fast = []
    temp_slow = []
    for i, v in enumerate(delta):
        last_i += 1
        last_v += abs(v)
        temp_fast.append(fast[i])
        temp_slow.append(slow[i])

        if i >= 2 and delta[i - 1] <= 0 < delta[i]:
            kind = "金叉"
        elif i >= 2 and delta[i - 1] >= 0 > delta[i]:
            kind = "死叉"
        else:
            continue

        cross_info.append({'位置': i, "类型": kind, "快线": fast[i], "慢线": slow[i],
                           "距离": last_i, '距今': length - i,
                           "面积": round(last_v, 4), '价差': round(v, 4),
                           "快线高点": max(temp_fast), "快线低点": min(temp_fast),
                           "慢线高点": max(temp_slow), "慢线低点": min(temp_slow),
                           })
        last_i = 0
        last_v = 0
        temp_fast = []
        temp_slow = []

    return cross_info


def same_dir_counts(seq: [List, np.array]):
    """计算 seq 中与最后一个数字同向的数字数量

    :param seq: 数字序列
    :return:

    example
    ----------
    >>>print(same_dir_counts([-1, -1, -2, -3, 0, 1, 2, 3, -1, -2, 1, 1, 2, 3]))
    >>>print(same_dir_counts([-1, -1, -2, -3, 0, 1, 2, 3]))
    """
    s = seq[-1]
    c = 0
    for num in seq[::-1]:
        if (num > 0 and s > 0) or (num < 0 and s < 0):
            c += 1
        else:
            break
    return c


def count_last_same(seq: Union[List, np.array, Tuple]):
    """统计与seq列表最后一个元素相似的连续元素数量

    :param seq: 数字序列
    :return:
    """
    s = seq[-1]
    c = 0
    for _s in seq[::-1]:
        if _s == s:
            c += 1
        else:
            break
    return c


def get_sub_elements(elements: List[Any], di: int = 1, n: int = 10) -> List[Any]:
    """获取截止到倒数第 di 个元素的前 n 个元素

    :param elements: 全部元素列表
    :param di: 指定结束元素为倒数第 di 个
    :param n: 指定需要的元素个数
    :return: 部分元素列表

    >>>x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    >>>y1 = get_sub_elements(x, di=1, n=3)
    >>>y2 = get_sub_elements(x, di=2, n=3)
    """
    assert di >= 1
    if di == 1:
        se = elements[-n:]
    else:
        se = elements[-n - di + 1: -di + 1]
    return se


def is_bis_down(bis: List[BI]):
    """判断 bis 中的连续笔是否是向下的"""
    if not bis or len(bis) < 3 or len(bis) % 2 == 0:
        return False

    assert bis[1].fx_b.dt > bis[0].fx_b.dt, "时间由远到近"

    if bis[-1].direction == Direction.Down \
            and bis[0].high == max([x.high for x in bis]) \
            and bis[-1].low == min([x.low for x in bis]):
        return True
    else:
        return False


def is_bis_up(bis: List[BI]):
    """判断 bis 中的连续笔是否是向上的"""
    if not bis or len(bis) < 3 and len(bis) % 2 == 0:
        return False

    assert bis[1].fx_b.dt > bis[0].fx_b.dt, "时间由远到近"

    if bis[-1].direction == Direction.Up \
            and bis[-1].high == max([x.high for x in bis]) \
            and bis[0].low == min([x.low for x in bis]):
        return True
    else:
        return False


def get_zs_seq(bis: List[BI]) -> List[ZS]:
    """获取连续笔中的中枢序列

    :param bis: 连续笔对象列表
    :return: 中枢序列
    """
    zs_list = []
    if not bis:
        return []

    for bi in bis:
        if not zs_list:
            zs_list.append(ZS(bis=[bi]))
            continue

        zs = zs_list[-1]
        if not zs.bis:
            zs.bis.append(bi)
            zs_list[-1] = zs
        else:
            if (bi.direction == Direction.Up and bi.high < zs.zd) \
                    or (bi.direction == Direction.Down and bi.low > zs.zg):
                zs_list.append(ZS(bis=[bi]))
            else:
                zs.bis.append(bi)
                zs_list[-1] = zs
    return zs_list


def cross_zero_axis(n1: Union[List, np.ndarray], n2: Union[List, np.ndarray]) -> int:
    """判断两个数列的零轴交叉点

    :param n1: 数列1
    :param n2: 数列2
    :return: 交叉点所在的索引位置
    """
    assert len(n1) == len(n2), '输入两个数列长度不等'
    axis_0 = np.zeros(len(n1))

    n1 = np.flip(n1)
    n2 = np.flip(n2)

    x1 = np.where(n1[0] * n1 < axis_0, True, False)
    x2 = np.where(n2[0] * n2 < axis_0, True, False)

    num1 = np.argmax(x1[:-1] != x1[1:]) + 2 if np.any(x1) else 0
    num2 = np.argmax(x2[:-1] != x2[1:]) + 2 if np.any(x2) else 0
    return max(num1, num2)


def cal_cross_num(cross: List, distance: int = 1) -> tuple:
    """使用 distance 过滤掉fast_slow_cross函数返回值cross列表中
    不符合要求的交叉点，返回处理后的金叉和死叉数值

    :param cross: fast_slow_cross函数返回值
    :param distance: 金叉和死叉之间的最小距离
    :return: jc金叉值 ，SC死叉值
    """
    if len(cross) == 0:
        return 0, 0
    elif len(cross) == 1:
        cross_ = cross
    elif len(cross) == 2:
        if cross[-1]['距离'] < distance:
            cross_ = []
        else:
            cross_ = cross
    else:
        if cross[-1]['距离'] < distance:
            last_cross = cross[-1]
            del cross[-2]
            re_cross = [i for i in cross if i['距离'] >= distance]
            re_cross.append(last_cross)
        else:
            re_cross = [i for i in cross if i['距离'] >= distance]
        cross_ = []
        for i in range(0, len(re_cross)):
            if len(cross_) >= 1 and re_cross[i]['类型'] == re_cross[i - 1]['类型']:
                # 不将上一个元素加入cross_
                del cross_[-1]
                cross_.append(re_cross[i])
            else:
                cross_.append(re_cross[i])

    jc = len([x for x in cross_ if x['类型'] == '金叉'])
    sc = len([x for x in cross_ if x['类型'] == '死叉'])

    return jc, sc


def down_cross_count(x1: Union[List, np.array], x2: Union[List, np.array]) -> int:
    """输入两个序列，计算 x1 下穿 x2 的次数

    :param x1: list
    :param x2: list
    :return: int
    """
    x = np.array(x1) < np.array(x2)
    num = 0
    for i in range(len(x) - 1):
        b1, b2 = x[i], x[i + 1]
        if b2 and b1 != b2:
            num += 1
    return num
