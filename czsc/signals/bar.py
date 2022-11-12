# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/11 20:18
describe: bar 作为前缀，代表信号属于基础 K 线信号
"""
from datetime import datetime
from collections import OrderedDict
from czsc import CZSC, Signal, CzscAdvancedTrader
from czsc.utils import check_pressure_support, get_sub_elements


def bar_end_V221111(c: CZSC, k1='60分钟') -> OrderedDict:
    """分钟 K 线结束

    :param c: 基础周期的 CZSC 对象
    :param k1: 分钟周期名称
    :return: s
    """
    k2, k3 = "K线", "结束"
    assert "分钟" in k1

    m = int(k1.replace("分钟", ""))
    dt: datetime = c.bars_raw[-1].dt
    v = "是" if dt.minute % m == 0 else "否"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v)
    s[signal.key] = signal.value
    return s


def bar_operate_span_V221111(c: CZSC, k1: str = '开多', span=("1400", "1450")) -> OrderedDict:
    """日内操作时间区间，c 必须是

    :param c: 基础周期的 CZSC 对象
    :param k1: 操作名称
    :param span: 时间范围，格式是 ("%H%M", "%H%M")
    :return: s
    """
    assert len(span) == 2
    k2, k3 = span

    dt: datetime = c.bars_raw[-1].dt
    v = "是" if k2 <= dt.strftime("%H%M") <= k3 else "否"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v)
    s[signal.key] = signal.value
    return s


def bar_zdt_V221110(c: CZSC, di=1) -> OrderedDict:
    """计算倒数第di根K线的涨跌停信息

    对于A股，任何K线，只要收盘价是最高价，那就不能买，只要收盘价是最低价，就不能卖。

    **信号逻辑：** close等于high大于前close，近似认为是涨停；反之，跌停。

    **信号列表：**

    - Signal('15分钟_D2K_ZDT_跌停_任意_任意_0')
    - Signal('15分钟_D2K_ZDT_涨停_任意_任意_0')

    :param c: 基础周期的 CZSC 对象
    :param di: 倒数第 di 根 K 线
    :return: s
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_ZDT".split("_")

    if len(c.bars_raw) < di + 2:
        v1 = "其他"
    else:
        b1, b2 = c.bars_raw[-di],  c.bars_raw[-di-1]

        if b1.close == b1.high > b2.close:
            v1 = "涨停"
        elif b1.close == b1.low < b2.close:
            v1 = "跌停"
        else:
            v1 = "其他"

    s = OrderedDict()
    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[v.key] = v.value
    return s


def bar_zdt_V221111(cat: CzscAdvancedTrader, freq: str, di: int = 1) -> OrderedDict:
    """更精确地倒数第1根K线的涨跌停计算

    **信号逻辑：** close等于high，且相比昨天收盘价涨幅大于9%，就是涨停；反之，跌停。

    **信号列表：**

    - Signal('15分钟_D2K_涨跌停_跌停_任意_任意_0')
    - Signal('15分钟_D2K_涨跌停_涨停_任意_任意_0')

    :param cat: CzscAdvancedTrader
    :param freq: K线周期
    :param di: 计算截止倒数第 di 根 K 线
    :return: s
    """
    zdt_cache = cat.cache.get('zdt_cache', {})
    bars = get_sub_elements(cat.kas[freq].bars_raw, di=di, n=300)
    last_bar = bars[-1]
    today = last_bar.dt.date()

    if not zdt_cache:
        yesterday_last = [x for x in bars if x.dt.date() != today][-1]
        zdt_cache['昨日'] = yesterday_last.dt.date()
        zdt_cache['昨收'] = yesterday_last.close

    else:
        if today != zdt_cache['今日']:
            # 新的一天，全部刷新
            zdt_cache['昨日'] = zdt_cache['今日']
            zdt_cache['昨收'] = zdt_cache['今收']

    zdt_cache['今日'] = last_bar.dt.date()
    zdt_cache['今收'] = last_bar.close
    zdt_cache['update_dt'] = last_bar.dt
    cat.cache['zdt_cache'] = zdt_cache

    k1, k2, k3 = freq, f"D{di}K", "涨跌停"
    if last_bar.close == last_bar.high > zdt_cache['昨收'] * 1.09:
        v1 = "涨停"
    elif last_bar.close == last_bar.low < zdt_cache['昨收'] * 0.91:
        v1 = "跌停"
    else:
        v1 = "其他"

    s = OrderedDict()
    v = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[v.key] = v.value
    return s


def bar_vol_grow_V221112(c: CZSC, di: int = 2, n: int = 5) -> OrderedDict:
    """倒数第 i 根 K 线的成交量相比于前 N 根 K 线放量

    **信号逻辑: ** 放量的定义为，倒数第i根K线的量能 / 过去N根的平均量能，在2-4倍之间。

    **信号列表：**

    - Signal('15分钟_D2K5B_放量_否_任意_任意_0')
    - Signal('15分钟_D2K5B_放量_是_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止的倒数第 i 根
    :param n: 向前看 n 根
    :return: s
    """
    k1, k2, k3 = str(c.freq.value), f"D{di}K{n}B", "放量"

    if len(c.bars_raw) < di + n + 10:
        v1 = "其他"
    else:
        bars = get_sub_elements(c.bars_raw, di=di, n=n+1)
        assert len(bars) == n + 1

        mean_vol = sum([x.vol for x in bars[:-1]]) / n
        v1 = "是" if mean_vol * 4 >= bars[-1].vol >= mean_vol * 2 else "否"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def bar_mean_amount_V221112(c: CZSC, di: int = 1, n: int = 10, th1: int = 1, th2: int = 4) -> OrderedDict:
    """截取一段时间内的平均成交金额分类信号

    **信号逻辑: ** 倒数第i根K线向前n根K线的成交金额均值在 th1 和 th2 之间

    **信号列表：**

    - Signal('15分钟_D2K20B均额_1至4千万_否_任意_任意_0')
    - Signal('15分钟_D2K20B均额_1至4千万_是_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算截止的倒数第 i 根
    :param n: 向前看 n 根
    :param th1: 成交金额下限，单位：千万
    :param th2: 成交金额上限，单位：千万
    :return: s
    """
    k1, k2, k3 = str(c.freq.value), f"D{di}K{n}B均额", f"{th1}至{th2}千万"

    if len(c.bars_raw) < di + n + 5:
        v1 = "其他"

    else:
        bars = get_sub_elements(c.bars_raw, di=di, n=n)
        assert len(bars) == n

        m = sum([x.amount for x in bars]) / n
        v1 = "是" if th2 >= m / 10000000 >= th1 else "否"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def bar_cross_ps_V221112(c: CZSC, di=1, num=3):
    """倒数第 di 根 K 线穿越支撑、压力位的数量【慎用，非常耗时】

    **信号逻辑：**

    1. 计算最近600根K线的支撑、压力位列表；
    2. 如果dik是阳性，切上穿 num 个以上的压力位，择时多头；反之，空头。

    **信号列表：**

    - Signal('15分钟_D2K_N3_空头_任意_任意_0')
    - Signal('15分钟_D2K_N3_多头_任意_任意_0')

    :param c: CZSC对象
    :param di: 信号计算在倒数第 di 根
    :param num: 阈值
    :return: s
    """
    k1, k2, k3 = str(c.freq.value), f"D{di}K", f"N{num}"

    if len(c.bars_raw) < 300 + di:
        v1 = '其他'

    else:
        bars = get_sub_elements(c.bars_raw, di=di, n=600)
        pres = check_pressure_support(bars, q_seq=[x / 100 for x in list(range(0, 100, 3))])
        last = bars[-1]

        cnt = 0
        for x in pres['关键位']:
            if last.close > x > last.open:
                assert cnt >= 0
                cnt += 1

            if last.close < x < last.open:
                assert cnt <= 0
                cnt -= 1

        if cnt >= num:
            v1 = "多头"
        elif cnt <= -num:
            v1 = "空头"
        else:
            v1 = "其他"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1)
    s[signal.key] = signal.value
    return s


def bar_section_momentum_V221112(c: CZSC, di: int = 1, n: int = 10, th: int = 100) -> OrderedDict:
    """获取某个区间（固定K线数量）的动量强弱

    **信号列表：**

    - Signal('15分钟_D2K10B_阈值100BP_下跌_强势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_下跌_弱势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_下跌_弱势_高波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_弱势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_弱势_高波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_强势_低波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_上涨_强势_高波动_0')
    - Signal('15分钟_D2K10B_阈值100BP_下跌_强势_高波动_0')

    :param c: CZSC对象
    :param di: 区间结束K线位置，倒数
    :param n: 取近n根K线
    :param th: 动量强弱划分的阈值，单位 BP
    :return: s
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K{n}B_阈值{th}BP".split('_')

    if len(c.bars_raw) < di + n:
        v1 = v2 = v3 = "其他"
    else:
        bars = get_sub_elements(c.bars_raw, di=di, n=n)
        bp = (bars[-1].close / bars[0].open - 1) * 10000
        wave = (max([x.high for x in bars]) / min([x.low for x in bars]) - 1) * 10000
        rate = 0 if abs(bp) == 0 else abs(wave) / abs(bp)

        v1 = "上涨" if bp >= 0 else "下跌"
        v2 = "强势" if abs(bp) >= th else "弱势"
        v3 = "高波动" if rate >= 3 else "低波动"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)
    s[signal.key] = signal.value
    return s
