# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/25 17:43
describe: 成交量相关信号
"""
from loguru import logger
try:
    import talib as ta
except:
    logger.warning(f"ta-lib 没有正确安装，相关信号函数无法正常执行。"
                   f"请参考安装教程 https://blog.csdn.net/qaz2134560/article/details/98484091")
import numpy as np
from typing import List
from collections import OrderedDict
from czsc.analyze import CZSC, RawBar
from czsc.utils.sig import get_sub_elements, create_single_signal


def update_vol_ma_cache(c: CZSC, ma_type: str, timeperiod: int, **kwargs):
    """更新均线缓存

    :param c: CZSC对象
    :param ma_type: 均线类型
    :param timeperiod: 计算周期
    :return:
    """
    ma_type_map = {
        'SMA': ta.MA_Type.SMA,
        'EMA': ta.MA_Type.EMA,
        'WMA': ta.MA_Type.WMA,
        'KAMA': ta.MA_Type.KAMA,
        'TEMA': ta.MA_Type.TEMA,
        'DEMA': ta.MA_Type.DEMA,
        'MAMA': ta.MA_Type.MAMA,
        'TRIMA': ta.MA_Type.TRIMA,
    }

    ma_type = ma_type.upper()
    assert ma_type in ma_type_map.keys(), f"{ma_type} 不是支持的均线类型，可选值：{list(ma_type_map.keys())}"
    cache_key = f"VOL#{ma_type}#{timeperiod}"

    if c.bars_raw[-1].cache and c.bars_raw[-1].cache.get(cache_key, None):
        # 如果最后一根K线已经有对应的缓存，不执行更新
        return cache_key

    last_cache = dict(c.bars_raw[-2].cache) if c.bars_raw[-2].cache else dict()
    if cache_key not in last_cache.keys() or len(c.bars_raw) < timeperiod + 15:
        # 初始化缓存
        data = np.array([x.vol for x in c.bars_raw], dtype=np.float64)
        ma = ta.MA(data, timeperiod=timeperiod, matype=ma_type_map[ma_type.upper()])
        assert len(ma) == len(data)
        for i in range(len(data)):
            _c = dict(c.bars_raw[i].cache) if c.bars_raw[i].cache else dict()
            _c.update({cache_key: ma[i] if ma[i] else data[i]})
            c.bars_raw[i].cache = _c

    else:
        # 增量更新最近3个K线缓存
        data = np.array([x.vol for x in c.bars_raw[-timeperiod - 10:]], dtype=np.float64)
        ma = ta.MA(data, timeperiod=timeperiod, matype=ma_type_map[ma_type.upper()])
        for i in range(1, 4):
            _c = dict(c.bars_raw[-i].cache) if c.bars_raw[-i].cache else dict()
            _c.update({cache_key: ma[-i]})
            c.bars_raw[-i].cache = _c
    return cache_key


def vol_single_ma_V230214(c: CZSC, **kwargs) -> OrderedDict:
    """成交量单均线信号

    参数模板："{freq}_D{di}VOL#{ma_type}#{timeperiod}_分类V230214"

    **信号逻辑：**

    1. vol > ma，多头；反之，空头
    2. ma[-1] > ma[-2]，向上；反之，向下

    **信号列表：**

    - Signal('15分钟_D1VOL#SMA#5_分类V230214_空头_向上_任意_0')
    - Signal('15分钟_D1VOL#SMA#5_分类V230214_空头_向下_任意_0')
    - Signal('15分钟_D1VOL#SMA#5_分类V230214_多头_向上_任意_0')
    - Signal('15分钟_D1VOL#SMA#5_分类V230214_多头_向下_任意_0')

    :param c: CZSC对象
    :param kwargs:
        - ma_type: 均线类型，必须是 `ma_type_map` 中的 key
        - timeperiod: 均线计算周期
        - di: 信号计算截止倒数第i根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    ma_type = kwargs.get("ma_type", "SMA").upper()          # ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    timeperiod = int(kwargs.get("timeperiod", 5))           # timeperiod: 均线计算周期
    cache_key = update_vol_ma_cache(c, ma_type, timeperiod)

    k1, k2, k3 = f"{c.freq.value}_D{di}{cache_key}_分类V230214".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    v1 = "多头" if bars[-1].vol >= bars[-1].cache[cache_key] else "空头"
    v2 = "向上" if bars[-1].cache[cache_key] >= bars[-2].cache[cache_key] else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def vol_double_ma_V230214(c: CZSC, **kwargs) -> OrderedDict:
    """成交量双均线信号

    参数模板："{freq}_D{di}VOL双均线{ma_type}#{t1}#{t2}_BS辅助V230214"

    **信号逻辑：**

    1. 短均线在长均线上方，看多；反之，看空

    **信号列表：**

    - Signal('15分钟_D1VOL双均线SMA#5#20_BS辅助V230214_看空_任意_任意_0')
    - Signal('15分钟_D1VOL双均线SMA#5#20_BS辅助V230214_看多_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
        t1: 短线均线，
        t2: 长线均线,
        ma_type: 均线类型,
        di: 信号计算截止倒数第i根K线
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    t1 = int(kwargs.get("t1", 5))
    t2 = int(kwargs.get("t2", 20))
    assert t2 > t1, "t2必须是长线均线，t1为短线均线"
    ma_type = kwargs.get("ma_type", "SMA").upper()  # ma_type: 均线类型，必须是 `ma_type_map` 中的 key
    cache_key1 = update_vol_ma_cache(c, ma_type, t1)
    cache_key2 = update_vol_ma_cache(c, ma_type, t2)

    k1, k2, k3 = f"{c.freq.value}_D{di}VOL双均线{ma_type}#{t1}#{t2}_BS辅助V230214".split('_')
    bars = get_sub_elements(c.bars_raw, di=di, n=3)
    v1 = "看多" if bars[-1].cache[cache_key1] >= bars[-1].cache[cache_key2] else "看空"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def vol_ti_suo_V221216(c: CZSC, **kwargs) -> OrderedDict:
    """梯量/缩量柱：顺势与逆势工具，贡献者：琅盎

    参数模板："{freq}_D{di}K_量柱V221216"

    **信号判断标准 **

    1.只要比昨缩量的就能形成“缩量柱”，只要比昨日增高的就能形成“梯量柱”。严格地讲，
    连续三天缩量就是“缩量柱”，连续三天增量“阶梯状”就是梯量柱，它是当日量能连续同前二天的量相比。
    2.缩量柱的形态是量柱明显走低，梯量柱的形态是成交量明显逐步走高，它们都有两种情况：量价同步和量价背离。
    3.“价升量缩” 的 “缩量柱”，体现了供不应求的局面，主力有主动买入的倾向；
    4.“量增价涨” 的 “梯量柱”，体现了努力上攻的态势，主力有被动买入的倾向。

    **有效信号列表： **

    - Signal('15分钟_D1K_量柱V221216_梯量_价平_任意_0')
    - Signal('15分钟_D1K_量柱V221216_梯量_价跌_任意_0')
    - Signal('15分钟_D1K_量柱V221216_缩量_价平_任意_0')
    - Signal('15分钟_D1K_量柱V221216_缩量_价跌_任意_0')
    - Signal('15分钟_D1K_量柱V221216_梯量_价升_任意_0')
    - Signal('15分钟_D1K_量柱V221216_缩量_价升_任意_0')

    :param c: CZSC 对象
    :param kwargs:
        di: 倒数第di根K线，加上这个参数就可以不用借助缓存就可以回溯
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}K_量柱V221216".split('_')
    v1 = "其他"
    if len(c.bars_raw) < di + 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bar1, bar2, bar3 = c.bars_raw[-di], c.bars_raw[-di-1], c.bars_raw[-di-2]
    close_max = max(bar2.close, bar3.close)
    close_min = min(bar2.close, bar3.close)

    if bar1.vol > bar2.vol > bar3.vol:
        v1 = "梯量"
    elif bar1.vol < bar2.vol < bar3.vol:
        v1 = "缩量"

    if v1 == '其他':
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if bar1.close < close_min and bar1.close < bar1.open:
        v2 = "价跌"
    elif bar1.close > close_max and bar1.close > bar1.open:
        v2 = "价升"
    else:
        v2 = "价平"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def vol_gao_di_V221218(c: CZSC, **kwargs) -> OrderedDict:
    """高量柱&低量柱&高量黄金柱，贡献者：琅盎

    参数模板："{freq}_D{di}K_量柱V221218"

    **高/低量柱判断标准 **

    1.高量柱是在一个阶段内量柱的对比（3天以上），在这一阶段出现的的最高量就是高量柱。
    2.高量柱是在对应的这一价位成交火爆的标志，出现高量柱后的走势多数向上少数向下。
    3.高量柱出现后，不跌或横盘应看涨。
    4.高量柱 + 缩量柱 ＝ 黄金柱 是最具价值的高量柱组合
    5.低量柱判断标准正好和高量柱相反
    6.低量柱出现后，不跌或横盘应看跌。
    7.操作中还需要根据所处位置作判断

    **有效信号列表： **

    - Signal('15分钟_D1K_量柱V221218_低量柱_7K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_低量柱_10K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量柱_10K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量黄金柱_10K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量柱_6K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_低量柱_9K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量黄金柱_7K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量柱_7K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_低量柱_8K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量柱_8K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_低量柱_6K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量柱_9K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量黄金柱_8K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量黄金柱_9K_任意_0')
    - Signal('15分钟_D1K_量柱V221218_高量黄金柱_6K_任意_0')

    :param c: CZSC 对象
    :param kwargs:
        di: 倒数第di根K线，加上这个参数就可以不用借助缓存就可以回溯
    :return: 高量柱识别结果
    """
    freq = c.freq.value
    di = int(kwargs.get("di", 1))
    k1, k2, k3 = f"{freq}_D{di}K_量柱V221218".split('_')
    v1, v2 = "其他", "任意"

    def _check_gao_liang_zhu(bars: List[RawBar]):
        if len(bars) <= 5:
            return "其他"

        max_vol = max([x.vol for x in bars])
        min_vol = min([x.vol for x in bars])
        _v1 = "其他"

        if bars[-1].vol == max_vol:
            _v1 = "高量柱"
        elif bars[-2].vol == max_vol and bars[-1].vol < bars[-2].vol * 0.5:
            _v1 = "高量黄金柱"
        elif bars[-1].vol == min_vol:
            _v1 = "低量柱"
        return _v1

    for n in (10, 9, 8, 7, 6):
        _bars = get_sub_elements(c.bars_raw, di=di, n=n)
        if len(_bars) != n:
            continue

        v1 = _check_gao_liang_zhu(_bars)
        if v1 != "其他":
            v2 = f"{n}K"
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
