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
from czsc.utils import get_sub_elements, create_single_signal, is_bis_up, is_bis_down
from collections import OrderedDict


def cxt_bi_base_V230228(c: CZSC, **kwargs) -> OrderedDict:
    """BI基础信号

    **信号逻辑：**

    1. 取最后一个笔，最后一笔向下，则当前笔向上，最后一笔向上，则当前笔向下；
    2. 根据延伸K线数量判断当前笔的状态，中继或转折。

    **信号列表：**

    - Signal('15分钟_D0BL9_V230228_向下_中继_任意_0')
    - Signal('15分钟_D0BL9_V230228_向上_转折_任意_0')
    - Signal('15分钟_D0BL9_V230228_向下_转折_任意_0')
    - Signal('15分钟_D0BL9_V230228_向上_中继_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    bi_init_length = kwargs.get('bi_init_length', 9)  # 笔的初始延伸长度，即笔的延伸长度小于该值时，笔的状态为转折，否则为中继
    k1, k2, k3 = f"{c.freq.value}_D0BL{bi_init_length}_V230228".split('_')
    v1 = '其他'
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    assert last_bi.direction in [Direction.Up, Direction.Down]
    v1 = '向上' if last_bi.direction == Direction.Down else '向下'
    v2 = "中继" if len(c.bars_ubi) >= bi_init_length else "转折"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_fx_power_V221107(c: CZSC, di: int = 1, **kwargs) -> OrderedDict:
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


def cxt_first_buy_V221126(c: CZSC, di=1, **kwargs) -> OrderedDict:
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


def cxt_first_sell_V221126(c: CZSC, di=1, **kwargs) -> OrderedDict:
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


def cxt_bi_break_V221126(c: CZSC, di=1, **kwargs) -> OrderedDict:
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


def cxt_sub_b3_V221212(cat: CzscSignals, freq1='60分钟', freq2='15分钟', th=10, **kwargs) -> OrderedDict:
    """小级别突破大级别中枢形成三买，贡献者：魏永超

    **信号逻辑：**

    1. freq级别中产生笔中枢，最后一笔向上时，中枢由之前3笔构成；最后一笔向下时，中枢由最后3笔构成。
    2. sub_freq级别中出现向上笔超越大级别中枢最高点，且随后不回到大级别中枢区间的th%以内。

    **信号列表：**

    - Signal('60分钟_15分钟_3买回踩10_确认_任意_任意_0')

    :param cat:
    :param freq1: 中枢所在的大级别
    :param freq2: 突破大级别中枢，回踩形成小级别类3买的小级别
    :param th: 小级别回落对大级别中枢区间的回踩程度，0表示回踩不进大级别中枢，10表示回踩不超过中枢区间的10%
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{freq1}_{freq2}_三买回踩{th}".split('_')

    c: CZSC = cat.kas[freq1]
    sub_c: CZSC = cat.kas[freq2]

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


def cxt_zhong_shu_gong_zhen_V221221(cat: CzscSignals, freq1='日线', freq2='60分钟', **kwargs) -> OrderedDict:
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


def cxt_third_buy_V230228(c: CZSC, di=1, **kwargs) -> OrderedDict:
    """笔三买辅助

    **信号逻辑：**

    1. 定义大于前一个向上笔的高点的笔为向上突破笔，最近所有向上突破笔有价格重叠
    2. 当下笔的最低点在任一向上突破笔的高点上，且当下笔的最低点离笔序列最低点的距离不超过向上突破笔列表均值的1.618倍

    **信号列表：**

    - Signal('15分钟_D1三买辅助_V230228_三买_14笔_任意_0')
    - Signal('15分钟_D1三买辅助_V230228_三买_10笔_任意_0')
    - Signal('15分钟_D1三买辅助_V230228_三买_6笔_任意_0')
    - Signal('15分钟_D1三买辅助_V230228_三买_8笔_任意_0')
    - Signal('15分钟_D1三买辅助_V230228_三买_12笔_任意_0')

    :param c: CZSC对象
    :param di: 倒数第几笔
    :param kwargs:
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}三买辅助_V230228".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bi_list) < di + 11:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    def check_third_buy(bis):
        """检查 bis 是否是三买的结束

        :param bis: 笔序列，按时间升序
        :return:
        """
        res = {"match": False, "v1": "三买", "v2": f"{len(bis)}笔", 'v3': "任意"}
        if bis[-1].direction == Direction.Up or bis[0].direction == bis[-1].direction:
            return res

        # 检查三买：获取向上突破的笔列表
        key_bis = []
        for i in range(0, len(bis) - 2, 2):
            if i == 0:
                key_bis.append(bis[i])
            else:
                b1, _, b3 = bis[i - 2:i + 1]
                if b3.high > b1.high:
                    key_bis.append(b3)
        if len(key_bis) < 2:
            return res

        tb_break = bis[-1].low > min([x.high for x in key_bis]) > max([x.low for x in key_bis])
        tb_price = bis[-1].low < min([x.low for x in bis]) + 1.618 * np.mean([x.power_price for x in key_bis])

        if tb_break and tb_price:
            res['match'] = True
        return res

    for n in (13, 11, 9, 7, 5):
        _bis = get_sub_elements(c.bi_list, di=di, n=n+1)
        if len(_bis) != n + 1:
            continue

        _res = check_third_buy(_bis)
        if _res['match']:
            v1 = _res['v1']
            v2 = _res['v2']
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


class BXT:
    """缠论笔形态识别基础类"""

    def __init__(self, bis: List[BI]):
        self.bis = bis
        self.xt_map = {
            '标准趋势': self.aAbBc,
            '类趋势': self.abcde,
            'aAb式盘整': self.aAb,
            'aAbcd式盘整': self.aAbcd,
            'abcAd式盘整': self.abcAd,
            'ABC式盘整': self.ABC,
            'BS2': self.BS2,
            'BS3': self.BS3,
        }

    @staticmethod
    def is_aAbBc(bis):
        """标准趋势"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}

        if len(bis) >= 11:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11 = bis[-11:]
            max_high = max([x.high for x in bis[-11:]])
            min_low = min([x.low for x in bis[-11:]])

            # 十一笔（2~4构成中枢A，8~10构成中枢B）
            if bi11.direction == Direction.Down and max_high == bi1.high and min_low == bi11.low \
                    and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and is_bis_down([bi5, bi6, bi7]) \
                    and min(bi2.low, bi4.low) > max(bi8.high, bi10.high) \
                    and min(bi8.high, bi10.high) > max(bi8.low, bi10.low):
                res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "A3B3"}
                return res

            if bi11.direction == Direction.Up and max_high == bi11.high and min_low == bi1.low \
                    and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and is_bis_up([bi5, bi6, bi7]) \
                    and max(bi2.high, bi4.high) < min(bi8.low, bi10.low) \
                    and min(bi8.high, bi10.high) > max(bi8.low, bi10.low):
                res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "A3B3"}
                return res

            # 十一笔（2~4构成中枢A，6~10构成中枢B）
            if bi11.direction == Direction.Down and max_high == bi1.high and min_low == bi11.low \
                    and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and min(bi2.low, bi4.low) > max(bi6.high, bi8.high, bi10.high) \
                    and min(bi6.high, bi8.high, bi10.high) > max(bi6.low, bi8.low, bi10.low):
                res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "A3B5"}
                return res

            if bi11.direction == Direction.Up and max_high == bi11.high and min_low == bi1.low \
                    and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and max(bi2.high, bi4.high) < min(bi6.low, bi8.low, bi10.low) \
                    and min(bi6.high, bi8.high, bi10.high) > max(bi6.low, bi8.low, bi10.low):
                res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "A3B5"}
                return res

            # 十一笔（2~6构成中枢A，8~10构成中枢B）
            if bi11.direction == Direction.Down and max_high == bi1.high and min_low == bi11.low \
                    and min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) \
                    and min(bi2.low, bi4.low, bi6.low) > max(bi8.high, bi10.high) \
                    and min(bi8.high, bi10.high) > max(bi8.low, bi10.low):
                res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "A5B3"}
                return res

            if bi11.direction == Direction.Up and max_high == bi11.high and min_low == bi1.low \
                    and min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) \
                    and max(bi2.high, bi4.high, bi6.high) < min(bi8.low, bi10.low) \
                    and min(bi8.high, bi10.high) > max(bi8.low, bi10.low):
                res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "A5B3"}
                return res

        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]
            max_high = max([x.high for x in bis[-9:]])
            min_low = min([x.low for x in bis[-9:]])

            # 九笔（2~4构成中枢A，6~8构成中枢B）
            if bi9.direction == Direction.Down and max_high == bi1.high and min_low == bi9.low \
                    and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and min(bi2.low, bi4.low) > max(bi6.high, bi8.high) \
                    and min(bi6.high, bi8.high) > max(bi6.low, bi8.low):
                res = {'match': True, 'v1': "向下", 'v2': "9笔", 'v3': "A3B3"}
                return res

            if bi9.direction == Direction.Up and max_high == bi9.high and min_low == bi1.low \
                    and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and max(bi2.high, bi4.high) < min(bi6.low, bi8.low) \
                    and min(bi6.high, bi8.high) > max(bi6.low, bi8.low):
                res = {'match': True, 'v1': "向上", 'v2': "9笔", 'v3': "A3B3"}
                return res

        return res

    @property
    def aAbBc(self):
        """标准趋势"""
        return self.is_aAbBc(self.bis)

    @staticmethod
    def is_abcde(bis):
        """类趋势"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}
        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]

            if bi9.direction == Direction.Down and is_bis_down(bis[-9:]) \
                    and bi2.low > bi4.high and bi4.low > bi6.high and bi6.low > bi8.high:
                res = {'match': True, 'v1': "向下", 'v2': "9笔", 'v3': "任意"}
                return res

            if bi9.direction == Direction.Up and is_bis_up(bis[-9:]) \
                    and bi8.low > bi6.high and bi6.low > bi4.high and bi4.low > bi2.high:
                res = {'match': True, 'v1': "向上", 'v2': "9笔", 'v3': "任意"}
                return res

        if len(bis) >= 7:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis[-7:]

            if bi7.direction == Direction.Down and is_bis_down(bis[-7:]) \
                    and bi2.low > bi4.high and bi4.low > bi6.high:
                res = {'match': True, 'v1': "向下", 'v2': "7笔", 'v3': "任意"}
                return res

            if bi7.direction == Direction.Up and is_bis_up(bis[-7:]) \
                    and bi6.low > bi4.high and bi4.low > bi2.high:
                res = {'match': True, 'v1': "向上", 'v2': "7笔", 'v3': "任意"}
                return res

        if len(bis) >= 5:
            bi1, bi2, bi3, bi4, bi5 = bis[-5:]

            if bi5.direction == Direction.Down and is_bis_down(bis[-5:]) \
                    and bi2.low > bi4.high:
                res = {'match': True, 'v1': "向下", 'v2': "5笔", 'v3': "任意"}
                return res

            if bi5.direction == Direction.Up and is_bis_up(bis[-5:]) \
                    and bi4.low > bi2.high:
                res = {'match': True, 'v1': "向上", 'v2': "5笔", 'v3': "任意"}
                return res

        return res

    @property
    def abcde(self):
        """类趋势"""
        return self.is_abcde(self.bis)

    @staticmethod
    def is_aAb(bis):
        """aAb式盘整"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}
        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]
            max_high = max([x.high for x in bis[-9:]])
            min_low = min([x.low for x in bis[-9:]])

            if bi9.direction == Direction.Down and max_high == bi1.high and bi9.low == min_low \
                    and min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low):
                res = {'match': True, 'v1': "向下", 'v2': "9笔", 'v3': "任意"}
                return res

            if bi9.direction == Direction.Up and max_high == bi9.high and bi1.low == min_low \
                    and min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low):
                res = {'match': True, 'v1': "向上", 'v2': "9笔", 'v3': "任意"}
                return res

        if len(bis) >= 7:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis[-7:]
            max_high = max([x.high for x in bis[-7:]])
            min_low = min([x.low for x in bis[-7:]])

            if bi7.direction == Direction.Down and max_high == bi1.high and bi7.low == min_low \
                    and min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low):
                res = {'match': True, 'v1': "向下", 'v2': "7笔", 'v3': "任意"}
                return res

            if bi7.direction == Direction.Up and max_high == bi7.high and bi1.low == min_low \
                    and min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low):
                res = {'match': True, 'v1': "向上", 'v2': "7笔", 'v3': "任意"}
                return res

        if len(bis) >= 5:
            bi1, bi2, bi3, bi4, bi5 = bis[-5:]
            max_high = max([x.high for x in bis[-5:]])
            min_low = min([x.low for x in bis[-5:]])

            if bi5.direction == Direction.Down and max_high == bi1.high and bi5.low == min_low \
                    and bi2.low < bi4.high:
                res = {'match': True, 'v1': "向下", 'v2': "5笔", 'v3': "任意"}
                return res

            if bi5.direction == Direction.Up and max_high == bi5.high and bi1.low == min_low \
                    and bi4.low < bi2.high:
                res = {'match': True, 'v1': "向上", 'v2': "5笔", 'v3': "任意"}
                return res

        return res

    @property
    def aAb(self):
        """aAb式盘整"""
        return self.is_aAb(self.bis)

    @staticmethod
    def is_aAbcd(bis):
        """aAbcd式盘整"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}

        if len(bis) >= 11:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11 = bis[-11:]
            max_high = max([x.high for x in bis[-11:]])
            min_low = min([x.low for x in bis[-11:]])

            gg = max(bi2.high, bi4.high, bi6.high, bi8.high)
            zg = min(bi2.high, bi4.high, bi6.high, bi8.high)
            zd = max(bi2.low, bi4.low, bi6.low, bi8.low)
            dd = min(bi2.low, bi4.low, bi6.low, bi8.low)

            if bi11.direction == Direction.Down and max_high == bi1.high and bi11.low == min_low \
                    and zg >= zd >= dd > bi10.high:
                res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "任意"}
                return res

            if bi11.direction == Direction.Up and max_high == bi11.high and bi1.low == min_low \
                    and bi10.low > gg >= zg >= zd:
                res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "任意"}
                return res

        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]
            max_high = max([x.high for x in bis[-9:]])
            min_low = min([x.low for x in bis[-9:]])

            gg = max(bi2.high, bi4.high, bi6.high)
            zg = min(bi2.high, bi4.high, bi6.high)
            zd = max(bi2.low, bi4.low, bi6.low)
            dd = min(bi2.low, bi4.low, bi6.low)

            if bi9.direction == Direction.Down and max_high == bi1.high and bi9.low == min_low \
                    and zg >= zd >= dd > bi8.high:
                res = {'match': True, 'v1': "向下", 'v2': "9笔", 'v3': "任意"}
                return res

            if bi9.direction == Direction.Up and max_high == bi9.high and bi1.low == min_low \
                    and bi8.low > gg >= zg >= zd:
                res = {'match': True, 'v1': "向上", 'v2': "9笔", 'v3': "任意"}
                return res

        if len(bis) >= 7:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis[-7:]
            max_high = max([x.high for x in bis[-7:]])
            min_low = min([x.low for x in bis[-7:]])

            gg = max(bi2.high, bi4.high)
            zg = min(bi2.high, bi4.high)
            zd = max(bi2.low, bi4.low)
            dd = min(bi2.low, bi4.low)

            if bi7.direction == Direction.Down and max_high == bi1.high and bi7.low == min_low \
                    and zg >= zd >= dd > bi6.high:
                res = {'match': True, 'v1': "向下", 'v2': "7笔", 'v3': "任意"}
                return res

            if bi7.direction == Direction.Up and max_high == bi7.high and bi1.low == min_low \
                    and bi6.low > gg >= zg >= zd:
                res = {'match': True, 'v1': "向上", 'v2': "7笔", 'v3': "任意"}
                return res

        return res

    @property
    def aAbcd(self):
        """aAbcd式盘整"""
        return self.is_aAbcd(self.bis)

    @staticmethod
    def is_abcAd(bis):
        """abcAd式盘整"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}
        if len(bis) >= 11:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11 = bis[-11:]
            max_high = max([x.high for x in bis[-11:]])
            min_low = min([x.low for x in bis[-11:]])

            gg = max(bi4.high, bi6.high, bi8.high, bi10.high)
            zg = min(bi4.high, bi6.high, bi8.high, bi10.high)
            zd = max(bi4.low, bi6.low, bi8.low, bi10.low)
            dd = min(bi4.low, bi6.low, bi8.low, bi10.low)

            if bi11.direction == Direction.Down and max_high == bi1.high and bi11.low == min_low \
                    and bi2.low > gg >= zg >= zd:
                res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "任意"}
                return res

            if bi11.direction == Direction.Up and max_high == bi11.high and bi1.low == min_low \
                    and zg >= zd >= dd > bi2.high:
                res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "任意"}
                return res

        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]
            max_high = max([x.high for x in bis[-9:]])
            min_low = min([x.low for x in bis[-9:]])

            gg = max(bi4.high, bi6.high, bi8.high)
            zg = min(bi4.high, bi6.high, bi8.high)
            zd = max(bi4.low, bi6.low, bi8.low)
            dd = min(bi4.low, bi6.low, bi8.low)

            if bi9.direction == Direction.Down and max_high == bi1.high and bi9.low == min_low \
                    and bi2.low > gg >= zg >= zd:
                res = {'match': True, 'v1': "向下", 'v2': "9笔", 'v3': "任意"}
                return res

            if bi9.direction == Direction.Up and max_high == bi9.high and bi1.low == min_low \
                    and zg >= zd >= dd > bi2.high:
                res = {'match': True, 'v1': "向上", 'v2': "9笔", 'v3': "任意"}
                return res

        if len(bis) >= 7:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis[-7:]
            max_high = max([x.high for x in bis[-7:]])
            min_low = min([x.low for x in bis[-7:]])

            gg = max(bi4.high, bi6.high)
            zg = min(bi4.high, bi6.high)
            zd = max(bi4.low, bi6.low)
            dd = min(bi4.low, bi6.low)

            if bi7.direction == Direction.Down and max_high == bi1.high and bi7.low == min_low \
                    and bi2.low > gg >= zg >= zd:
                res = {'match': True, 'v1': "向下", 'v2': "7笔", 'v3': "任意"}
                return res

            if bi7.direction == Direction.Up and max_high == bi7.high and bi1.low == min_low \
                    and zg >= zd >= dd > bi2.high:
                res = {'match': True, 'v1': "向上", 'v2': "7笔", 'v3': "任意"}
                return res

        return res

    @property
    def abcAd(self):
        """abcAd式盘整"""
        return self.is_abcAd(self.bis)

    @staticmethod
    def is_ABC(bis):
        """ABC式盘整"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}

        if len(bis) >= 11:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11 = bis[-11:]
            max_high = max([x.high for x in bis[-11:]])
            min_low = min([x.low for x in bis[-11:]])

            if bi11.direction == Direction.Down and max_high == bi1.high and bi11.low == min_low:
                # A3B5C3
                if is_bis_down([bi1, bi2, bi3]) and is_bis_down([bi9, bi10, bi11]):
                    res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "A3B5C3"}
                    return res

                # A5B3C3
                if is_bis_down([bi1, bi2, bi3, bi4, bi5]) and is_bis_down([bi9, bi10, bi11]):
                    res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "A5B3C3"}
                    return res

                # A3B3C5
                if is_bis_down([bi1, bi2, bi3]) and is_bis_down([bi7, bi8, bi9, bi10, bi11]):
                    res = {'match': True, 'v1': "向下", 'v2': "11笔", 'v3': "A3B3C5"}
                    return res

            if bi11.direction == Direction.Up and max_high == bi11.high and bi1.low == min_low:
                # A3B5C3
                if is_bis_up([bi1, bi2, bi3]) and is_bis_up([bi9, bi10, bi11]):
                    res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "A3B5C3"}
                    return res

                # A5B3C3
                if is_bis_up([bi1, bi2, bi3, bi4, bi5]) and is_bis_up([bi9, bi10, bi11]):
                    res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "A5B3C3"}
                    return res

                # A3B3C5
                if is_bis_up([bi1, bi2, bi3]) and is_bis_up([bi7, bi8, bi9, bi10, bi11]):
                    res = {'match': True, 'v1': "向上", 'v2': "11笔", 'v3': "A3B3C5"}
                    return res

        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]
            max_high = max([x.high for x in bis[-9:]])
            min_low = min([x.low for x in bis[-9:]])

            if bi9.direction == Direction.Down and max_high == bi1.high and bi9.low == min_low \
                    and is_bis_down([bi1, bi2, bi3]) and is_bis_down([bi7, bi8, bi9]):
                res = {'match': True, 'v1': "向下", 'v2': "9笔", 'v3': "任意"}
                return res

            if bi9.direction == Direction.Up and max_high == bi9.high and bi1.low == min_low \
                    and is_bis_up([bi1, bi2, bi3]) and is_bis_up([bi7, bi8, bi9]):
                res = {'match': True, 'v1': "向上", 'v2': "9笔", 'v3': "任意"}
                return res

        return res

    @property
    def ABC(self):
        """ABC式盘整"""
        return self.is_ABC(self.bis)

    @staticmethod
    def is_BS2(bis):
        """BS2"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}

        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]
            gg = max([bi2.high, bi4.high])
            zg = min([bi2.high, bi4.high])
            zd = max([bi2.low, bi4.low])
            dd = min([bi2.low, bi4.low])

            if bi9.direction == Direction.Down and is_bis_down([bi1, bi2, bi3, bi4, bi5]):
                if gg > bi9.low >= zg:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右4", 'v3': "24上沿"}
                    return res

                if zg > bi9.low >= zd:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右4", 'v3': "24内部"}
                    return res

                if zd > bi9.low >= dd:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右4", 'v3': "24下沿"}
                    return res

            if bi9.direction == Direction.Up and is_bis_up([bi1, bi2, bi3, bi4, bi5]):
                if gg > bi9.high >= zg:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右4", 'v3': "24上沿"}
                    return res

                if zg > bi9.high >= zd:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右4", 'v3': "24内部"}
                    return res

                if zd > bi9.high >= dd:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右4", 'v3': "24下沿"}
                    return res

        if len(bis) >= 7:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis[-7:]
            gg = max([bi2.high, bi4.high])
            zg = min([bi2.high, bi4.high])
            zd = max([bi2.low, bi4.low])
            dd = min([bi2.low, bi4.low])

            if bi7.direction == Direction.Down and is_bis_down([bi1, bi2, bi3, bi4, bi5]):
                if gg > bi7.low >= zg:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右2", 'v3': "24上沿"}
                    return res

                if zg > bi7.low >= zd:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右2", 'v3': "24内部"}
                    return res

                if zd > bi7.low >= dd:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右2", 'v3': "24下沿"}
                    return res

            if bi7.direction == Direction.Up and is_bis_up([bi1, bi2, bi3, bi4, bi5]):
                if gg > bi7.high >= zg:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右2", 'v3': "24上沿"}
                    return res

                if zg > bi7.high >= zd:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右2", 'v3': "24内部"}
                    return res

                if zd > bi7.high >= dd:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右2", 'v3': "24下沿"}
                    return res

        if len(bis) >= 5:
            bi1, bi2, bi3, bi4, bi5 = bis[-5:]
            if bi5.direction == Direction.Down and is_bis_down([bi1, bi2, bi3]):
                if bi2.high > bi5.low > bi2.low:
                    res = {'match': True, 'v1': "向下", 'v2': "左3右2", 'v3': "笔2内部"}
                    return res

                if bi5.high > bi3.high > bi5.low > bi3.low:
                    res = {'match': True, 'v1': "向下", 'v2': "左3右2", 'v3': "笔3内部"}
                    return res

            if bi5.direction == Direction.Up and is_bis_up([bi1, bi2, bi3]):
                if bi2.high > bi5.high > bi2.low:
                    res = {'match': True, 'v1': "向上", 'v2': "左3右2", 'v3': "笔2内部"}
                    return res

                if bi5.high < bi3.high and bi5.low < bi3.low:
                    res = {'match': True, 'v1': "向上", 'v2': "左3右2", 'v3': "笔3内部"}
                    return res

        return res

    @property
    def BS2(self):
        return self.is_BS2(self.bis)

    @staticmethod
    def is_BS3(bis):
        """BS3"""
        # res 定义返回值标准
        res = {'match': False, 'v1': "任意", 'v2': "任意", 'v3': "任意"}

        if len(bis) >= 9:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis[-9:]
            gg = max([bi2.high, bi4.high])
            dd = min([bi2.low, bi4.low])

            if bi9.direction == Direction.Down and is_bis_down([bi1, bi2, bi3, bi4, bi5]):
                if bi7.low < gg < bi9.low:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右4", 'v3': "24上沿"}
                    return res

            if bi9.direction == Direction.Up and is_bis_up([bi1, bi2, bi3, bi4, bi5]):
                if bi9.high < dd < bi7.high:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右4", 'v3': "24下沿"}
                    return res

        if len(bis) >= 7:
            bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis[-7:]
            gg = max([bi2.high, bi4.high])
            dd = min([bi2.low, bi4.low])

            if bi7.direction == Direction.Down and is_bis_down([bi1, bi2, bi3, bi4, bi5]):
                if bi7.low > gg:
                    res = {'match': True, 'v1': "向下", 'v2': "左5右2", 'v3': "24上沿"}
                    return res

            if bi7.direction == Direction.Up and is_bis_up([bi1, bi2, bi3, bi4, bi5]):
                if bi7.high < dd:
                    res = {'match': True, 'v1': "向上", 'v2': "左5右2", 'v3': "24下沿"}
                    return res

        if len(bis) >= 5:
            bi1, bi2, bi3, bi4, bi5 = bis[-5:]
            if bi5.direction == Direction.Down and is_bis_down([bi1, bi2, bi3]):
                if bi5.low > max(bi1.high, bi3.high):
                    res = {'match': True, 'v1': "向下", 'v2': "左3右2", 'v3': "任意"}
                    return res

            if bi5.direction == Direction.Up and is_bis_up([bi1, bi2, bi3]):
                if bi5.high < min(bi1.low, bi3.low):
                    res = {'match': True, 'v1': "向上", 'v2': "左3右2", 'v3': "任意"}
                    return res
        return res

    @property
    def BS3(self):
        return self.is_BS3(self.bis)




