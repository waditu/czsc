"""
信号计算辅助工具集

本模块为各类信号函数提供通用的辅助工具，主要包括：

1. :func:`create_single_signal`：构造一个 Signal 对象（``key``-``value`` 的标准化表示），
   并以 ``OrderedDict`` 形式返回；
2. :func:`is_symmetry_zs`：判断"对称中枢"——中枢内所有笔力度的标准差与均值之比是否
   小于阈值；
3. :func:`check_cross_info` / :func:`fast_slow_cross`：计算两个数列（如快慢均线）的
   金叉 / 死叉以及附属统计信息；
4. :func:`check_gap_info`：扫描 K 线序列中的向上 / 向下缺口及其是否被回补；
5. :func:`same_dir_counts` / :func:`count_last_same`：计算尾部连续同方向 / 同值元素数量；
6. :func:`get_sub_elements`：从列表中按"倒数第 di 个元素往前取 n 个"的方式截取；
7. :func:`is_bis_down` / :func:`is_bis_up`：判断连续笔序列是否方向一致；
8. :func:`get_zs_seq`：从连续笔序列推导中枢序列；
9. :func:`cross_zero_axis` / :func:`cal_cross_num` / :func:`down_cross_count`：零轴交叉
   与下穿次数等辅助统计。

作者: zengbin93
邮箱: zeng_bin8888@163.com
创建时间: 2022/10/27 23:23
"""

from collections import OrderedDict
from typing import Any

import numpy as np

from czsc import BI, ZS, Direction, RawBar


def create_single_signal(**kwargs) -> OrderedDict:
    """构造单个标准信号对象

    通过 ``czsc.Signal`` 把 ``k1/k2/k3/v1/v2/v3/score`` 标准字段拼装成
    ``key="k1_k2_k3"`` / ``value="v1_v2_v3_score"`` 的字符串形式，并以
    ``OrderedDict`` 返回，便于和其他信号合并。

    :param kwargs: 其他关键字参数
        - k1/k2/k3: 信号键三段，缺省值均为 ``"任意"``
        - v1/v2/v3: 信号值三段，缺省值均为 ``"任意"``
        - score: int，信号置信度评分，默认 0
    :return: OrderedDict，``{Signal.key: Signal.value}``
    """
    from czsc import Signal

    s = OrderedDict()
    k1, k2, k3 = kwargs.get("k1", "任意"), kwargs.get("k2", "任意"), kwargs.get("k3", "任意")
    v1, v2, v3 = kwargs.get("v1", "任意"), kwargs.get("v2", "任意"), kwargs.get("v3", "任意")
    score = kwargs.get("score", 0)
    v = Signal(key=f"{k1}_{k2}_{k3}", value=f"{v1}_{v2}_{v3}_{score}")
    # 旧式构造方式留作参考：
    # v = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3, score=kwargs.get("score", 0))
    s[v.key] = v.value
    return s


def is_symmetry_zs(bis: list[BI], th: float = 0.3) -> bool:
    """对称中枢判断：中枢中所有笔的力度序列，标准差小于均值的一定比例

    示意图：https://pic2.zhimg.com/80/v2-2f55ef49eda01972462531ebb6de4f19_1440w.jpg

    :param bis: 构成中枢的笔序列；笔的数量必须为奇数
    :param th: float，标准差小于均值的比例阈值；越小越严格
    :return: bool，是否构成对称中枢
    """
    # 中枢笔数必须为奇数
    if len(bis) % 2 == 0:
        return False

    zs = ZS(bis=bis)
    # 校验是否构成有效中枢：上沿不能低于下沿，且各笔区间存在公共范围
    if zs.zd > zs.zg or max([x.low for x in bis]) > min([x.high for x in bis]):
        return False

    # 力度对称性：用 power_price 的 CV（标准差/均值）衡量
    zns = [x.power_price for x in bis]
    return np.std(zns) / np.mean(zns) <= th


def check_cross_info(fast: list | np.ndarray, slow: list | np.ndarray):
    """计算 fast 和 slow 的交叉信息

    扫描两条等长序列，识别每一次的金叉（fast 上穿 slow）与死叉（fast 下穿 slow），
    并计算自上一次交叉以来的时间距离、累计绝对差、快/慢线的极值等统计信息。

    :param fast: list | np.ndarray，快线
    :param slow: list | np.ndarray，慢线
    :return: list[dict]，每个元素描述一次交叉
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

        # 交叉判定：上一根 <=0 且当前 >0 视为金叉；上一根 >=0 且当前 <0 视为死叉
        if i >= 2 and delta[i - 1] <= 0 < delta[i]:
            kind = "金叉"
        elif i >= 2 and delta[i - 1] >= 0 > delta[i]:
            kind = "死叉"
        else:
            continue

        cross_info.append(
            {
                "位置": i,
                "类型": kind,
                "快线": fast[i],
                "慢线": slow[i],
                "距离": last_i,
                "距今": length - i,
                "面积": round(last_v, 4),
                "价差": round(v, 4),
                "快线高点": max(temp_fast),
                "快线低点": min(temp_fast),
                "慢线高点": max(temp_slow),
                "慢线低点": min(temp_slow),
            }
        )
        # 一次交叉后重置累计变量
        last_i = 0
        last_v = 0
        temp_fast = []
        temp_slow = []

    return cross_info


def check_gap_info(bars: list[RawBar]):
    """检查 bars 中的缺口信息

    依次比较相邻两根 K 线的最高 / 最低价：若 ``bar1.high < bar2.low`` 则视为向上缺口，
    若 ``bar1.low > bar2.high`` 则视为向下缺口；同时通过后续 K 线的极值判断缺口
    是否已被回补。

    :param bars: list[RawBar]，K 线序列，按时间升序
    :return: list[dict]，每个元素描述一个缺口（kind / cover / sdt / edt / high / low / delta）
    """
    gap_info = []
    if len(bars) < 2:
        return gap_info

    for i in range(1, len(bars)):
        bar1, bar2 = bars[i - 1], bars[i]
        right = bars[i:]

        gap = None
        # 向上缺口：bar1 的最高价仍低于 bar2 的最低价
        if bar1.high < bar2.low:
            delta = round(bar2.low / bar1.high - 1, 4)
            cover = "已补" if min(x.low for x in right) < bar1.high else "未补"
            gap = {
                "kind": "向上缺口",
                "cover": cover,
                "sdt": bar1.dt,
                "edt": bar2.dt,
                "high": bar2.low,
                "low": bar1.high,
                "delta": delta,
            }

        # 向下缺口：bar1 的最低价仍高于 bar2 的最高价
        if bar1.low > bar2.high:
            delta = round(bar1.low / bar2.high - 1, 4)
            cover = "已补" if max(x.high for x in right) > bar1.low else "未补"
            gap = {
                "kind": "向下缺口",
                "cover": cover,
                "sdt": bar1.dt,
                "edt": bar2.dt,
                "high": bar1.low,
                "low": bar2.high,
                "delta": delta,
            }

        if gap:
            gap_info.append(gap)

    return gap_info


def fast_slow_cross(fast, slow):
    """计算 fast 和 slow 的交叉信息（与 :func:`check_cross_info` 等价的实现）

    保留此函数主要是为了向后兼容；新代码推荐统一使用 :func:`check_cross_info`。

    :param fast: list | np.ndarray，快线
    :param slow: list | np.ndarray，慢线
    :return: list[dict]，每个元素描述一次交叉
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

        cross_info.append(
            {
                "位置": i,
                "类型": kind,
                "快线": fast[i],
                "慢线": slow[i],
                "距离": last_i,
                "距今": length - i,
                "面积": round(last_v, 4),
                "价差": round(v, 4),
                "快线高点": max(temp_fast),
                "快线低点": min(temp_fast),
                "慢线高点": max(temp_slow),
                "慢线低点": min(temp_slow),
            }
        )
        last_i = 0
        last_v = 0
        temp_fast = []
        temp_slow = []

    return cross_info


def same_dir_counts(seq: list | np.ndarray):
    """计算 seq 中与最后一个数字同向的数字数量

    从尾部向前扫描，遇到符号不一致即停止，返回连续同向的数量（包含最后一个元素本身）。

    :param seq: 数字序列
    :return: int，连续同向的数量

    示例：
        >>> print(same_dir_counts([-1, -1, -2, -3, 0, 1, 2, 3, -1, -2, 1, 1, 2, 3]))
        >>> print(same_dir_counts([-1, -1, -2, -3, 0, 1, 2, 3]))
    """
    s = seq[-1]
    c = 0
    for num in seq[::-1]:
        if (num > 0 and s > 0) or (num < 0 and s < 0):
            c += 1
        else:
            break
    return c


def count_last_same(seq: list | np.ndarray | tuple):
    """统计 seq 列表中尾部与最后一个元素相同的连续元素数量

    :param seq: 数字 / 字符序列
    :return: int，连续相同元素的数量
    """
    s = seq[-1]
    c = 0
    for _s in seq[::-1]:
        if _s == s:
            c += 1
        else:
            break
    return c


def get_sub_elements(elements: list[Any], di: int = 1, n: int = 10) -> list[Any]:
    """获取截止到倒数第 di 个元素的前 n 个元素

    常用于在信号函数中以"截止到当前 K 线 / 当前笔"的方式取数据窗口。

    :param elements: 全部元素列表
    :param di: int，结束位置为倒数第 di 个元素，``di=1`` 表示包含最后一个
    :param n: int，需要的元素个数
    :return: list，部分元素列表

    示例：
        >>> x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        >>> y1 = get_sub_elements(x, di=1, n=3)
        >>> y2 = get_sub_elements(x, di=2, n=3)
    """
    assert di >= 1
    se = elements[-n:] if di == 1 else elements[-n - di + 1 : -di + 1]
    return se


def is_bis_down(bis: list[BI]):
    """判断 bis 中的连续笔是否整体向下

    判定条件：
    - 笔数为奇数且至少 3 笔；
    - 序列时间由远到近；
    - 最后一笔方向为 ``Down``；
    - 第一笔的 high 是序列内最高，最后一笔的 low 是序列内最低。

    :param bis: list[BI]
    :return: bool
    """
    if not bis or len(bis) < 3 or len(bis) % 2 == 0:
        return False

    assert bis[1].fx_b.dt > bis[0].fx_b.dt, "时间由远到近"

    return bool(
        bis[-1].direction == Direction.Down
        and bis[0].high == max([x.high for x in bis])
        and bis[-1].low == min([x.low for x in bis])
    )


def is_bis_up(bis: list[BI]):
    """判断 bis 中的连续笔是否整体向上

    判定条件与 :func:`is_bis_down` 对称。

    :param bis: list[BI]
    :return: bool
    """
    if not bis or len(bis) < 3 and len(bis) % 2 == 0:
        return False

    assert bis[1].fx_b.dt > bis[0].fx_b.dt, "时间由远到近"

    return bool(
        bis[-1].direction == Direction.Up
        and bis[-1].high == max([x.high for x in bis])
        and bis[0].low == min([x.low for x in bis])
    )


def get_zs_seq(bis: list[BI]) -> list[ZS]:
    """从连续笔中提取中枢序列

    遍历笔列表，按"上行笔的 high 低于当前中枢下沿"或"下行笔的 low 高于当前中枢
    上沿"作为中枢分界条件，将笔合并到当前中枢或开启新的中枢。

    :param bis: list[BI]，连续笔对象列表
    :return: list[ZS]，中枢序列
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
            # 当前笔脱离中枢区间则开启新的中枢
            if (bi.direction == Direction.Up and bi.high < zs.zd) or (
                bi.direction == Direction.Down and bi.low > zs.zg
            ):
                zs_list.append(ZS(bis=[bi]))
            else:
                zs.bis.append(bi)
                zs_list[-1] = zs
    return zs_list


def cross_zero_axis(n1: list | np.ndarray, n2: list | np.ndarray) -> int:
    """判断两个数列的零轴交叉点

    分别在 ``n1`` 和 ``n2`` 反向序列中找到首次符号反转的位置，再返回二者中较大者，
    用于表征"尚未被零轴干扰"的最长窗口长度。

    :param n1: 数列 1
    :param n2: 数列 2
    :return: int，交叉点所在的索引位置
    """
    assert len(n1) == len(n2), "输入两个数列长度不等"
    axis_0 = np.zeros(len(n1))

    n1 = np.flip(n1)
    n2 = np.flip(n2)

    # 找到第一个与最新值符号相反的位置
    x1 = np.where(n1[0] * n1 < axis_0, True, False)
    x2 = np.where(n2[0] * n2 < axis_0, True, False)

    num1 = np.argmax(x1[:-1] != x1[1:]) + 2 if np.any(x1) else 0
    num2 = np.argmax(x2[:-1] != x2[1:]) + 2 if np.any(x2) else 0
    return int(max(num1, num2))


def cal_cross_num(cross: list, distance: int = 1) -> tuple:
    """根据距离 ``distance`` 过滤交叉点，返回过滤后的金叉/死叉数量

    使用 ``distance`` 把 ``fast_slow_cross`` 返回的交叉序列中过近的伪信号合并，
    再统计净金叉与净死叉的数量。

    :param cross: list，:func:`fast_slow_cross` 的返回值
    :param distance: int，金叉与死叉之间的最小距离
    :return: tuple[int, int]，``(金叉数量 jc, 死叉数量 sc)``
    """
    if len(cross) == 0:
        return 0, 0
    elif len(cross) == 1:
        cross_ = cross
    elif len(cross) == 2:
        cross_ = [] if cross[-1]["距离"] < distance else cross
    else:
        # 距离过近时把最后一次交叉的"前一次同类"丢弃，再按 distance 过滤
        if cross[-1]["距离"] < distance:
            last_cross = cross[-1]
            del cross[-2]
            re_cross = [i for i in cross if i["距离"] >= distance]
            re_cross.append(last_cross)
        else:
            re_cross = [i for i in cross if i["距离"] >= distance]
        cross_ = []
        for i in range(0, len(re_cross)):
            # 同类型连续交叉视作一次（保留最新一次）
            if len(cross_) >= 1 and re_cross[i]["类型"] == re_cross[i - 1]["类型"]:
                del cross_[-1]
                cross_.append(re_cross[i])
            else:
                cross_.append(re_cross[i])

    jc = len([x for x in cross_ if x["类型"] == "金叉"])
    sc = len([x for x in cross_ if x["类型"] == "死叉"])

    return jc, sc


def down_cross_count(x1: list | np.ndarray, x2: list | np.ndarray) -> int:
    """计算 x1 下穿 x2 的次数

    将 ``x1 < x2`` 转为布尔序列，相邻状态由 False 变 True 即视为一次下穿。

    :param x1: list
    :param x2: list
    :return: int，下穿次数
    """
    x = np.array(x1) < np.array(x2)
    num = 0
    for i in range(len(x) - 1):
        b1, b2 = x[i], x[i + 1]
        if b2 and b1 != b2:
            num += 1
    return num
