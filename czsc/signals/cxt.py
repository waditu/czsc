# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/7 19:29
describe:  cxt 代表 CZSC 形态信号
"""
import numpy as np
from loguru import logger
from typing import List
from czsc import CZSC
from czsc.traders.base import CzscSignals
from czsc.objects import FX, BI, Direction, ZS, Mark
from czsc.utils import get_sub_elements, create_single_signal
from collections import OrderedDict


def cxt_fx_power_V221107(c: CZSC, di: int = 1) -> OrderedDict:
    """倒数第di个分型的强弱

    **信号列表：**

    - Signal('15分钟_D1F_分型强弱_中顶_有中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_弱底_有中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_强顶_有中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_弱顶_有中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_强底_有中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_中底_有中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_强顶_无中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_中顶_无中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_弱底_无中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_中底_无中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_弱顶_无中枢_任意_0')
    - Signal('15分钟_D1F_分型强弱_强底_无中枢_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di个分型
    :return:
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}F_分型强弱".split("_")
    last_fx: FX = c.fx_list[-di]
    v1 = f"{last_fx.power_str}{last_fx.mark.value[0]}"
    v2 = "有中枢" if last_fx.has_zs else "无中枢"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_first_buy_V221126(c: CZSC, di=1) -> OrderedDict:
    """一买信号

    **信号列表：**

    - Signal('15分钟_D1B_BUY1_一买_5笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_11笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_7笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_21笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_17笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_19笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_9笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_15笔_任意_0')
    - Signal('15分钟_D1B_BUY1_一买_13笔_任意_0')

    :param c: CZSC 对象
    :param di: CZSC 对象
    :return: 信号字典
    """
    def __check_first_buy(bis: List[BI]):
        """检查 bis 是否是一买的结束

        :param bis: 笔序列，按时间升序
        """
        res = {"match": False, "v1": "一买", "v2": f"{len(bis)}笔", 'v3': "任意"}
        if len(bis) % 2 != 1 or bis[-1].direction == Direction.Up or bis[0].direction != bis[-1].direction:
            return res

        if max([x.high for x in bis]) != bis[0].high or min([x.low for x in bis]) != bis[-1].low:
            return res

        # 检查背驰：获取向下突破的笔列表
        key_bis = []
        for i in range(0, len(bis) - 2, 2):
            if i == 0:
                key_bis.append(bis[i])
            else:
                b1, _, b3 = bis[i - 2:i + 1]
                if b3.low < b1.low:
                    key_bis.append(b3)

        # 检查背驰：最后一笔的 power_price，power_volume，length 同时满足背驰条件才算背驰
        bc_price = bis[-1].power_price < max(bis[-3].power_price, np.mean([x.power_price for x in key_bis]))
        bc_volume = bis[-1].power_volume < max(bis[-3].power_volume, np.mean([x.power_volume for x in key_bis]))
        bc_length = bis[-1].length < max(bis[-3].length, np.mean([x.length for x in key_bis]))

        if bc_price and (bc_volume or bc_length):
            res['match'] = True
        return res

    k1, k2, k3 = c.freq.value, f"D{di}B", "BUY1"
    v1, v2, v3 = "其他", '任意', '任意'

    for n in (21, 19, 17, 15, 13, 11, 9, 7, 5):
        _bis = get_sub_elements(c.bi_list, di=di, n=n)
        if len(_bis) != n:
            logger.warning('笔的数量不对')
            continue

        _res = __check_first_buy(_bis)
        if _res['match']:
            v1, v2, v3 = _res['v1'], _res['v2'], _res['v3']
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def cxt_first_sell_V221126(c: CZSC, di=1) -> OrderedDict:
    """一卖信号

    **信号列表：**

    - Signal('15分钟_D1B_SELL1_一卖_17笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_15笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_5笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_7笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_9笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_19笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_21笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_13笔_任意_0')
    - Signal('15分钟_D1B_SELL1_一卖_11笔_任意_0')

    :param c: CZSC 对象
    :param di: CZSC 对象
    :return: 信号字典
    """

    def __check_first_sell(bis: List[BI]):
        """检查 bis 是否是一卖的结束

        :param bis: 笔序列，按时间升序
        """
        res = {"match": False, "v1": "一卖", "v2": f"{len(bis)}笔", 'v3': "任意"}
        if len(bis) % 2 != 1 or bis[-1].direction == Direction.Down:
            return res

        if bis[0].direction != bis[-1].direction:
            return res

        max_high = max([x.high for x in bis])
        min_low = min([x.low for x in bis])

        if max_high != bis[-1].high or min_low != bis[0].low:
            return res

        # 检查背驰：获取向上突破的笔列表
        key_bis = []
        for i in range(0, len(bis) - 2, 2):
            if i == 0:
                key_bis.append(bis[i])
            else:
                b1, _, b3 = bis[i - 2:i + 1]
                if b3.high > b1.high:
                    key_bis.append(b3)

        # 检查背驰：最后一笔的 power_price，power_volume，length 同时满足背驰条件才算背驰
        bc_price = bis[-1].power_price < max(bis[-3].power_price, np.mean([x.power_price for x in key_bis]))
        bc_volume = bis[-1].power_volume < max(bis[-3].power_volume, np.mean([x.power_volume for x in key_bis]))
        bc_length = bis[-1].length < max(bis[-3].length, np.mean([x.length for x in key_bis]))

        if bc_price and (bc_volume or bc_length):
            res['match'] = True
        return res

    k1, k2, k3 = c.freq.value, f"D{di}B", "SELL1"
    v1, v2, v3 = "其他", '任意', '任意'

    for n in (21, 19, 17, 15, 13, 11, 9, 7, 5):
        _bis = get_sub_elements(c.bi_list, di=di, n=n)
        if len(_bis) != n:
            logger.warning('笔的数量不对，跳过')
            continue

        _res = __check_first_sell(_bis)
        if _res['match']:
            v1, v2, v3 = _res['v1'], _res['v2'], _res['v3']
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def cxt_bi_break_V221126(c: CZSC, di=1) -> OrderedDict:
    """向上笔突破回调不破信号

    **信号列表：**

    - Signal('15分钟_D1B_向上_突破_5笔_任意_0')
    - Signal('15分钟_D1B_向上_突破_7笔_任意_0')
    - Signal('15分钟_D1B_向上_突破_9笔_任意_0')

    :param c: CZSC 对象
    :param di: CZSC 对象
    :return: 信号字典
    """

    def __check(bis: List[BI]):
        res = {"match": False, "v1": "突破", "v2": f"{len(bis)}笔", 'v3': "任意"}
        if len(bis) % 2 != 1 or bis[-1].direction == Direction.Up or bis[0].direction != bis[-1].direction:
            return res

        # 获取向上突破的笔列表
        key_bis = []
        for i in range(0, len(bis) - 2, 2):
            if i == 0:
                key_bis.append(bis[i])
            else:
                b1, _, b3 = bis[i - 2:i + 1]
                if b3.high > b1.high:
                    key_bis.append(b3)

        # 检查：
        # 1. 当下笔的最低点在任一向上突破笔的高点上
        # 2. 当下笔的最低点离笔序列最低点的距离不超过向上突破笔列表均值的1.618倍
        tb_break = bis[-1].low > min([x.high for x in key_bis])
        tb_price = bis[-1].low < min([x.low for x in bis]) + 1.618 * np.mean([x.power_price for x in key_bis])
        if tb_break and tb_price:
            res['match'] = True
        return res

    k1, k2, k3 = c.freq.value, f"D{di}B", "向上"
    v1, v2, v3 = "其他", '任意', '任意'

    for n in (9, 7, 5):
        _bis = get_sub_elements(c.bi_list, di=di, n=n)
        if len(_bis) != n:
            logger.warning('笔的数量不对，跳过')
            continue

        _res = __check(_bis)
        if _res['match']:
            v1, v2, v3 = _res['v1'], _res['v2'], _res['v3']
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def cxt_sub_b3_V221212(cat: CzscSignals, freq='60分钟', sub_freq='15分钟', th=10) -> OrderedDict:
    """小级别突破大级别中枢形成三买，贡献者：魏永超

    **信号逻辑：**

    1. freq级别中产生笔中枢，最后一笔向上时，中枢由之前3笔构成；最后一笔向下时，中枢由最后3笔构成。
    2. sub_freq级别中出现向上笔超越大级别中枢最高点，且随后不回到大级别中枢区间的th%以内。

    **信号列表：**

    - Signal('60分钟_15分钟_3买回踩10_确认_任意_任意_0')

    :param cat:
    :param freq: 中枢所在的大级别
    :param sub_freq: 突破大级别中枢，回踩形成小级别类3买的小级别
    :param th: 小级别回落对大级别中枢区间的回踩程度，0表示回踩不进大级别中枢，10表示回踩不超过中枢区间的10%
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{freq}_{sub_freq}_三买回踩{th}".split('_')

    c: CZSC = cat.kas[freq]
    sub_c: CZSC = cat.kas[sub_freq]

    v1 = "其他"
    if len(c.bi_list) > 13 and len(sub_c.bi_list) > 10:
        last_bi = c.bi_list[-1]
        if last_bi.direction == Direction.Down:
            zs = ZS(symbol=cat.symbol, bis=c.bi_list[-3:])
        else:
            zs = ZS(symbol=cat.symbol, bis=c.bi_list[-4:-1])

        min7 = min([x.low for x in c.bi_list[-7:]])
        # 中枢成立，且中枢最低点不是最后7笔的最低点，且最后7笔最低点同时也是最后13笔最低点（保证低点起来第一个中枢）
        if zs.zd < zs.zg and zs.dd > min7 == min([x.low for x in c.bi_list[-13:]]):
            last_sub_bi = sub_c.bi_list[-1]

            if last_sub_bi.direction == Direction.Down and last_sub_bi.high > zs.gg \
                    and last_sub_bi.low > zs.zg - (th / 100) * (zs.zg - zs.zd):
                v1 = "确认"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_zhong_shu_gong_zhen_V221221(cat: CzscSignals, freq1='日线', freq2='60分钟') -> OrderedDict:
    """大小级别中枢共振，类二买共振；贡献者：琅盎

    **信号逻辑：**

    1. 不区分上涨或下跌中枢
    2. 次级别中枢 DD 大于本级别中枢中轴
    3. 次级别向下笔出底分型开多；反之看空

    **信号列表：**

    - Signal('日线_60分钟_中枢共振_看多_任意_任意_0')
    - Signal('日线_60分钟_中枢共振_看空_任意_任意_0')

    :param cat:
    :param freq1:大级别周期
    :param freq2: 小级别周期
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{freq1}_{freq2}_中枢共振".split('_')

    max_freq: CZSC = cat.kas[freq1]
    min_freq: CZSC = cat.kas[freq2]
    symbol = cat.symbol

    def __is_zs(_bis):
        _zs = ZS(symbol=symbol, bis=_bis)
        if _zs.zd < _zs.zg:
            return True
        else:
            return False

    v1 = "其他"
    if len(max_freq.bi_list) >= 5 and __is_zs(max_freq.bi_list[-3:]) \
            and len(min_freq.bi_list) >= 5 and __is_zs(min_freq.bi_list[-3:]):

        big_zs = ZS(symbol=symbol, bis=max_freq.bi_list[-3:])
        small_zs = ZS(symbol=symbol, bis=min_freq.bi_list[-3:])

        if small_zs.dd > big_zs.zz and min_freq.bi_list[-1].direction == Direction.Down:
            v1 = "看多"

        if small_zs.gg < big_zs.zz and min_freq.bi_list[-1].direction == Direction.Up:
            v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_end_V230222(c: CZSC, **kwargs) -> OrderedDict:
    """当前是最后笔的第几次新低底分型或新高顶分型，用于笔结束辅助

    **信号逻辑：**

    1. 取最后笔及未成笔的分型，
    2. 当前如果是顶分型，则看当前顶分型是否新高，是第几个新高
    2. 当前如果是底分型，则看当前底分型是否新低，是第几个新低

    **信号列表：**

    - Signal('15分钟_D1MO3_结束辅助_新低_第1次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第2次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第1次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第2次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第3次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第4次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第3次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第4次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第5次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第5次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第6次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第6次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新高_第7次_任意_0')
    - Signal('15分钟_D1MO3_结束辅助_新低_第7次_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    max_overlap = int(kwargs.get('max_overlap', 3))
    k1, k2, k3 = f"{c.freq.value}_D1MO{max_overlap}_结束辅助".split('_')
    v1 = '其他'
    v2 = '其他'

    if not c.ubi_fxs:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    # 为了只取最后一笔以来的分型，没有用底层fx_list
    fxs = []
    if c.bi_list:
        fxs.extend(c.bi_list[-1].fxs[1:])
    ubi_fxs = c.ubi_fxs
    for x in ubi_fxs:
        if not fxs or x.dt > fxs[-1].dt:
            fxs.append(x)

    # 出分型那刻出信号，或者分型和最后一根bar相差 max_overlap 根K线时间内
    if (fxs[-1].elements[-1].dt == c.bars_ubi[-1].dt) or (c.bars_raw[-1].id - fxs[-1].raw_bars[-1].id <= max_overlap):
        if fxs[-1].mark == Mark.G:
            up = [x for x in fxs if x.mark == Mark.G]
            high_max = float('-inf')
            cnt = 0
            for fx in up:
                if fx.high > high_max:
                    cnt += 1
                    high_max = fx.high
            if fxs[-1].high == high_max:
                v1 = '新高'
                v2 = cnt

        else:
            down = [x for x in fxs if x.mark == Mark.D]
            low_min = float('inf')
            cnt = 0
            for fx in down:
                if fx.low < low_min:
                    cnt += 1
                    low_min = fx.low
            if fxs[-1].low == low_min:
                v1 = '新低'
                v2 = cnt

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=f"第{v2}次")


def cxt_bi_end_V230224(c: CZSC, **kwargs):
    """量价配合的笔结束辅助

    **信号逻辑：**

    1. 向下笔结束：fx_b 内最低的那根K线下影大于上影的两倍，同时fx_b内的平均成交量小于当前笔的平均成交量的0.618
    2. 向上笔结束：fx_b 内最高的那根K线上影大于下影的两倍，同时fx_b内的平均成交量大于当前笔的平均成交量的2倍

    **信号列表：**

    - Signal('15分钟_D1MO3_笔结束V230224_看多_任意_任意_0')
    - Signal('15分钟_D1MO3_笔结束V230224_看空_任意_任意_0')

    :param c: CZSC 对象
    :return: 信号字典
    """
    max_overlap = int(kwargs.get('max_overlap', 3))
    k1, k2, k3 = f"{c.freq.value}_D1MO{max_overlap}_笔结束V230224".split('_')
    v1 = '其他'
    if len(c.bi_list) <= 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    bi_bars = last_bi.raw_bars
    bi_vol_mean = np.mean([x.vol for x in bi_bars])
    fx_bars = last_bi.fx_b.raw_bars
    fx_vol_mean = np.mean([x.vol for x in fx_bars])

    bar1 = fx_bars[np.argmin([x.low for x in fx_bars])]
    bar2 = fx_bars[np.argmax([x.high for x in fx_bars])]

    if bar1.upper > bar1.lower * 2 and fx_vol_mean > bi_vol_mean * 2:
        v1 = '看空'
    elif 2 * bar2.upper < bar2.lower and fx_vol_mean < bi_vol_mean * 0.618:
        v1 = '看多'
    else:
        v1 = '其他'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)



