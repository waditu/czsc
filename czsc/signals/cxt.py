# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/11/7 19:29
describe:  cxt 代表 CZSC 形态信号
"""
import numpy as np
import pandas as pd
from typing import List
from czsc import CZSC
from czsc.traders.base import CzscSignals
from czsc.objects import FX, BI, Direction, ZS, Mark
from czsc.utils import get_sub_elements, create_single_signal
from czsc.utils.sig import get_zs_seq
from czsc.signals.tas import update_ma_cache, update_macd_cache
from collections import OrderedDict
from deprecated import deprecated
from sklearn.linear_model import LinearRegression


def cxt_bi_base_V230228(c: CZSC, **kwargs) -> OrderedDict:
    """BI基础信号

    参数模板："{freq}_D0BL{bi_init_length}_V230228"

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
    bi_init_length = int(kwargs.get('bi_init_length', 9))  # 笔的初始延伸长度，即笔的延伸长度小于该值时，笔的状态为转折，否则为中继
    k1, k2, k3 = f"{c.freq.value}_D0BL{bi_init_length}_V230228".split('_')
    v1 = '其他'
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    assert last_bi.direction in [Direction.Up, Direction.Down]
    v1 = '向上' if last_bi.direction == Direction.Down else '向下'
    v2 = "中继" if len(c.bars_ubi) >= bi_init_length else "转折"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_fx_power_V221107(c: CZSC, **kwargs) -> OrderedDict:
    """倒数第di个分型的强弱

    参数模板："{freq}_D{di}F_分型强弱"

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
    di = int(kwargs.get('di', 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}F_分型强弱".split("_")
    last_fx: FX = c.fx_list[-di]
    v1 = f"{last_fx.power_str}{last_fx.mark.value[0]}"
    v2 = "有中枢" if last_fx.has_zs else "无中枢"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_first_buy_V221126(c: CZSC, **kwargs) -> OrderedDict:
    """一买信号

    参数模板："{freq}_D{di}B_BUY1"

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
    :param kwargs:
        - di: 倒数第di个笔
    :return: 信号字典
    """
    di = int(kwargs.get('di', 1))

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
            continue

        _res = __check_first_buy(_bis)
        if _res['match']:
            v1, v2, v3 = _res['v1'], _res['v2'], _res['v3']
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def cxt_first_sell_V221126(c: CZSC, **kwargs) -> OrderedDict:
    """一卖信号

    参数模板："{freq}_D{di}B_SELL1"

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
    di = int(kwargs.get('di', 1))

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
            continue

        _res = __check_first_sell(_bis)
        if _res['match']:
            v1, v2, v3 = _res['v1'], _res['v2'], _res['v3']
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)


def cxt_zhong_shu_gong_zhen_V221221(cat: CzscSignals, freq1='日线', freq2='60分钟', **kwargs) -> OrderedDict:
    """大小级别中枢共振，类二买共振；贡献者：琅盎

    参数模板："{freq1}_{freq2}_中枢共振V221221"

    **信号逻辑：**

    1. 不区分上涨或下跌中枢
    2. 次级别中枢 DD 大于本级别中枢中轴
    3. 次级别向下笔出底分型开多；反之看空

    **信号列表：**

    - Signal('日线_60分钟_中枢共振V221221_看空_任意_任意_0')
    - Signal('日线_60分钟_中枢共振V221221_看多_任意_任意_0')

    :param cat:
    :param freq1: 大级别周期
    :param freq2: 小级别周期
    :return: 信号识别结果
    """
    k1, k2, k3 = f"{freq1}_{freq2}_中枢共振V221221".split('_')

    if not cat.kas or freq1 not in cat.kas or freq2 not in cat.kas:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1="其他")

    max_freq: CZSC = cat.kas[freq1]
    min_freq: CZSC = cat.kas[freq2]
    symbol = cat.symbol

    def __is_zs(_bis):
        _zs = ZS(bis=_bis)
        if _zs.zd < _zs.zg:
            return True
        else:
            return False

    v1 = "其他"
    if len(max_freq.bi_list) >= 5 and __is_zs(max_freq.bi_list[-3:]) and len(min_freq.bi_list) >= 5 and __is_zs(
            min_freq.bi_list[-3:]):

        big_zs = ZS(bis=max_freq.bi_list[-3:])
        small_zs = ZS(bis=min_freq.bi_list[-3:])

        if small_zs.dd > big_zs.zz and min_freq.bi_list[-1].direction == Direction.Down:
            v1 = "看多"

        if small_zs.gg < big_zs.zz and min_freq.bi_list[-1].direction == Direction.Up:
            v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_end_V230222(c: CZSC, **kwargs) -> OrderedDict:
    """当前是最后笔的第几次新低底分型或新高顶分型，用于笔结束辅助

    参数模板："{freq}_D1MO{max_overlap}_BE辅助V230222"

    **信号逻辑：**

    1. 取最后笔及未成笔的分型，
    2. 当前如果是顶分型，则看当前顶分型是否新高，是第几个新高
    2. 当前如果是底分型，则看当前底分型是否新低，是第几个新低

    **信号列表：**

    - Signal('日线_D1MO3_BE辅助V230222_新低_第2次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新高_第2次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新低_第3次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新低_第4次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新高_第3次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新高_第4次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新高_第5次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新低_第1次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新高_第1次_任意_0')
    - Signal('日线_D1MO3_BE辅助V230222_新低_第5次_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    max_overlap = int(kwargs.get('max_overlap', 3))
    k1, k2, k3 = f"{c.freq.value}_D1MO{max_overlap}_BE辅助V230222".split('_')
    v1 = '其他'
    v2 = '其他'

    if not c.ubi_fxs or len(c.bars_ubi) >= 7:
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

    参数模板："{freq}_D1_BE辅助V230224"

    **信号逻辑：**

    1. 向下笔结束：fx_b 内最低的那根K线下影大于上影的两倍，同时fx_b内的平均成交量小于当前笔的平均成交量的0.618
    2. 向上笔结束：fx_b 内最高的那根K线上影大于下影的两倍，同时fx_b内的平均成交量大于当前笔的平均成交量的2倍

    **信号列表：**

    - Signal('15分钟_D1_BE辅助V230224_看多_任意_任意_0')
    - Signal('15分钟_D1_BE辅助V230224_看空_任意_任意_0')

    :param c: CZSC 对象
    :return: 信号字典
    """
    k1, k2, k3 = f"{c.freq.value}_D1_BE辅助V230224".split('_')
    v1 = '其他'
    if len(c.bi_list) <= 3 or len(c.bars_ubi) >= 7:
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

    if 2 * bar2.upper < bar2.lower and fx_vol_mean < bi_vol_mean * 0.618:
        v1 = '看多'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_third_buy_V230228(c: CZSC, **kwargs) -> OrderedDict:
    """笔三买辅助

    参数模板："{freq}_D{di}_三买辅助V230228"

    **信号逻辑：**

    1. 定义大于前一个向上笔的高点的笔为向上突破笔，最近所有向上突破笔有价格重叠
    2. 当下笔的最低点在任一向上突破笔的高点上，且当下笔的最低点离笔序列最低点的距离不超过向上突破笔列表均值的1.618倍

    **信号列表：**

    - Signal('15分钟_D1_三买辅助V230228_三买_14笔_任意_0')
    - Signal('15分钟_D1_三买辅助V230228_三买_10笔_任意_0')
    - Signal('15分钟_D1_三买辅助V230228_三买_6笔_任意_0')
    - Signal('15分钟_D1_三买辅助V230228_三买_8笔_任意_0')
    - Signal('15分钟_D1_三买辅助V230228_三买_12笔_任意_0')

    :param c: CZSC对象
    :param kwargs:
        - di: 倒数第几笔
    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}_三买辅助V230228".split('_')
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
        _bis = get_sub_elements(c.bi_list, di=di, n=n + 1)
        if len(_bis) != n + 1:
            continue

        _res = check_third_buy(_bis)
        if _res['match']:
            v1 = _res['v1']
            v2 = _res['v2']
            break

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_double_zs_V230311(c: CZSC, **kwargs):
    """两个中枢组合辅助判断BS1，贡献者：韩知辰

    参数模板："{freq}_D{di}双中枢_BS1辅助V230311"

    **信号逻辑：**

    1. 最后一笔向下，最近两个中枢依次向下，最后一个中枢的倒数第一笔的K线长度大于倒数第二笔的K线长度，看多；
    2. 最后一笔向上，最近两个中枢依次向上，最后一个中枢的倒数第一笔的K线长度大于倒数第二笔的K线长度，看空；

    **信号列表：**

    - Signal('15分钟_D1双中枢_BS1辅助V230311_看多_任意_任意_0')
    - Signal('15分钟_D1双中枢_BS1辅助V230311_看空_任意_任意_0')

    :param c: CZSC对象
    :param di: 倒数第 di 笔
    :return: s
    """
    di = int(kwargs.get('di', 1))
    k1, k2, k3 = f"{c.freq.value}_D{di}双中枢_BS1辅助V230311".split("_")
    v1 = "其他"

    bis: List[BI] = get_sub_elements(c.bi_list, di=di, n=20)
    zss = get_zs_seq(bis)

    if len(zss) >= 2 and len(zss[-2].bis) >= 2 and len(zss[-1].bis) >= 2:
        zs1, zs2 = zss[-2], zss[-1]

        ts1 = len(zs2.bis[-1].bars)
        ts2 = len(zs2.bis[-2].bars)

        if bis[-1].direction == Direction.Down and ts1 >= ts2 * 2 and zs1.gg > zs2.gg:
            v1 = "看多"

        if bis[-1].direction == Direction.Up and ts1 >= ts2 * 2 and zs1.dd < zs2.dd:
            v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_second_bs_V230320(c: CZSC, **kwargs) -> OrderedDict:
    """均线辅助识别第二类买卖点

    参数模板："{freq}_D{di}#{ma_type}#{timeperiod}_BS2辅助V230320"

    **信号逻辑：**

    1. 二买：1）123笔序列向下，其中 1,3 笔的低点都在均线下方；2）5的fx_a的均线值小于fx_b均线值
    2. 二卖：1）123笔序列向上，其中 1,3 笔的高点都在均线上方；2）5的fx_a的均线值大于fx_b均线值

    **信号列表：**

    - Signal('15分钟_D1#SMA#21_BS2辅助V230320_二买_任意_任意_0')
    - Signal('15分钟_D1#SMA#21_BS2辅助V230320_二卖_任意_任意_0')

    :param c: CZSC对象
    :param di: 从最后一个笔的第几个开始识别
    :param kwargs: ma_type: 均线类型，timeperiod: 均线周期
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    timeperiod = int(kwargs.get("timeperiod", 21))
    ma_type = kwargs.get("ma_type", "SMA").upper()
    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D{di}#{ma_type}#{timeperiod}_BS2辅助V230320".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2, b3, b4, b5 = get_sub_elements(c.bi_list, di=di, n=5)

    b1_ma_b = b1.fx_b.raw_bars[-2].cache[cache_key]
    b3_ma_b = b3.fx_b.raw_bars[-2].cache[cache_key]

    b5_ma_a = b5.fx_a.raw_bars[-2].cache[cache_key]
    b5_ma_b = b5.fx_b.raw_bars[-2].cache[cache_key]

    lc1 = b1.low < b1_ma_b and b3.low < b3_ma_b
    if b5.direction == Direction.Down and lc1 and b5_ma_a < b5_ma_b:
        v1 = "二买"

    sc1 = b1.high > b1_ma_b and b3.high > b3_ma_b
    if b5.direction == Direction.Up and sc1 and b5_ma_a > b5_ma_b:
        v1 = "二卖"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


@deprecated(version='1.0.0', reason="即将删除，请使用 cxt_third_bs_V230319")
def cxt_third_bs_V230318(c: CZSC, **kwargs) -> OrderedDict:
    """均线辅助识别第三类买卖点

    参数模板："{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230318"

    **信号逻辑：**

    1. 三买：1）123构成中枢，4离开，5回落不回中枢；2）均线新高
    2. 三卖：1）123构成中枢，4离开，5回升不回中枢；2）均线新低

    **信号列表：**

    - Signal('15分钟_D1#SMA#34_BS3辅助V230318_三卖_任意_任意_0')
    - Signal('15分钟_D1#SMA#34_BS3辅助V230318_三买_任意_任意_0')

    :param c: CZSC对象
    :param di: 从最后一个笔的第几个开始识别
    :param kwargs: ma_type: 均线类型，timeperiod: 均线周期
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    timeperiod = int(kwargs.get("timeperiod", 34))
    ma_type = kwargs.get("ma_type", 'SMA').upper()
    k1, k2, k3 = f"{c.freq.value}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230318".split('_')
    v1 = "其他"

    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    if len(c.bi_list) < di + 6:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2, b3, b4, b5 = get_sub_elements(c.bi_list, di=di, n=5)
    zs_zd, zs_zg = max(b1.low, b3.low), min(b1.high, b3.high)
    if zs_zd > zs_zg:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    ma_1 = b1.fx_b.raw_bars[-1].cache[cache_key]
    ma_3 = b3.fx_b.raw_bars[-1].cache[cache_key]
    ma_5 = b5.fx_b.raw_bars[-1].cache[cache_key]

    # 三买：1）123构成中枢，4离开，5回落不回中枢；2）均线新高
    if b5.direction == Direction.Down and b5.low > zs_zg and ma_5 > ma_3 > ma_1:
        v1 = "三买"

    # 三卖：1）123构成中枢，4离开，5回升不回中枢；2）均线新低
    if b5.direction == Direction.Up and b5.high < zs_zd and ma_5 < ma_3 < ma_1:
        v1 = "三卖"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_third_bs_V230319(c: CZSC, **kwargs) -> OrderedDict:
    """均线辅助识别第三类买卖点，增加均线形态

    参数模板："{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230319"

    **信号逻辑：**

    1. 三买：1）123构成中枢，4离开，5回落不回中枢；2）均线新高或均线底分
    2. 三卖：1）123构成中枢，4离开，5回升不回中枢；2）均线新低或均线顶分

    **信号列表：**

    - Signal('15分钟_D1#SMA#34_BS3辅助V230319_三卖_均线新低_任意_0')
    - Signal('15分钟_D1#SMA#34_BS3辅助V230319_三买_均线底分_任意_0')
    - Signal('15分钟_D1#SMA#34_BS3辅助V230319_三买_均线新高_任意_0')
    - Signal('15分钟_D1#SMA#34_BS3辅助V230319_三买_均线新低_任意_0')

    **信号说明：**

    类似 cxt_third_bs_V230318 信号，但增加了均线形态。

    :param c: CZSC对象
    :param di: 从最后一个笔的第几个开始识别
    :param kwargs: ma_type: 均线类型，timeperiod: 均线周期
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    timeperiod = int(kwargs.get("timeperiod", 34))
    ma_type = kwargs.get("ma_type", 'SMA').upper()
    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230319".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    b1, b2, b3, b4, b5 = get_sub_elements(c.bi_list, di=di, n=5)
    zs_zd, zs_zg = max(b1.low, b3.low), min(b1.high, b3.high)
    if zs_zd > zs_zg:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    ma_1 = b1.fx_b.raw_bars[-1].cache[cache_key]
    ma_3 = b3.fx_b.raw_bars[-1].cache[cache_key]
    ma_5 = b5.fx_b.raw_bars[-1].cache[cache_key]

    # 三买：1）123构成中枢，4离开，5回落不回中枢；2）均线新高
    if b5.direction == Direction.Down and b5.low > zs_zg:
        v1 = "三买"

    # 三卖：1）123构成中枢，4离开，5回升不回中枢；2）均线新低
    if b5.direction == Direction.Up and b5.high < zs_zd:
        v1 = "三卖"

    if v1 == '其他':
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    if ma_5 > ma_3 > ma_1:
        v2 = "均线新高"
    elif ma_5 < ma_3 < ma_1:
        v2 = "均线新低"
    elif ma_5 > ma_3 < ma_1:
        v2 = "均线底分"
    elif ma_5 < ma_3 > ma_1:
        v2 = "均线顶分"
    else:
        v2 = "均线否定"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_bi_end_V230104(c: CZSC, **kwargs) -> OrderedDict:
    """单均线辅助判断笔结束

    参数模板："{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230104"

    **信号逻辑：**

    1. 向下笔底分型，连续三根阳线跨越SMA5超过一定阈值，且最后一根阳线收盘价在SMA5上方，向下笔结束；
    2. 向上笔顶分型，连续三根阴线跨越SMA5超过一定阈值，且最后一根阴线收盘价在SMA5下方，向上笔结束。

    **信号列表：**

    - Signal('15分钟_D0SMA#5T50_BE辅助V230104_看多_任意_任意_0')
    - Signal('15分钟_D0SMA#5T50_BE辅助V230104_看空_任意_任意_0')

    **Notes：**

    1. BE 是 Bi End 的缩写

    :param c: CZSC对象
    :param kwargs: ma_type: 均线类型，timeperiod: 均线周期，th: 距离SMA5均线的阈值，单位：BP
    :return: 信号识别结果
    """
    th = int(kwargs.pop("th", 50))
    timeperiod = int(kwargs.get("timeperiod", 5))
    ma_type = kwargs.get("ma_type", 'SMA').upper()
    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230104".split('_')
    v1 = "其他"
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    bars = get_sub_elements(c.bars_raw, di=1, n=3)
    bar1, bar2, bar3 = bars

    lc1 = last_bi.direction == Direction.Down and min([x.low for x in bars]) == last_bi.low
    lc2 = all(x.close > x.open for x in bars)
    lc3 = bar3.cache[cache_key] * (1 + th / 10000) < bar3.close
    if len(c.bars_ubi) < 7 and lc1 and lc2 and lc3:
        v1 = "看多"

    sc1 = last_bi.direction == Direction.Up and max([x.high for x in bars]) == last_bi.high
    sc2 = all(x.close < x.open for x in bars)
    sc3 = bar3.cache[cache_key] * (1 - th / 10000) > bar3.close
    if len(c.bars_ubi) < 7 and sc1 and sc2 and sc3:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_end_V230105(c: CZSC, **kwargs) -> OrderedDict:
    """K线形态+均线辅助判断笔结束

    参数模板："{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230105"

    **信号逻辑：**

    1. 向下笔底分型右侧两根K线，第一根阴线，第二根K线阳线，且收盘价超过均线一定阈值，向下笔结束。
    2. 反之，向上笔结束。

    **信号列表：**

    - Signal('15分钟_D0SMA#5T50_BE辅助V230105_看多_任意_任意_0')
    - Signal('15分钟_D0SMA#5T50_BE辅助V230105_看空_任意_任意_0')

    **Notes：**

    1. BE 是 Bi End 的缩写

    :param c: CZSC对象
    :param kwargs: ma_type: 均线类型，timeperiod: 均线周期，th: 距离SMA5均线的阈值，单位：BP
    :return: 信号识别结果
    """
    th = int(kwargs.get("th", 50))
    timeperiod = int(kwargs.get("timeperiod", 5))
    ma_type = kwargs.get("ma_type", 'SMA').upper()
    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230105".split('_')
    v1 = "其他"
    if len(c.bi_list) < 3 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    bar1, bar2 = last_bi.fx_b.raw_bars[-2:]

    lc1 = last_bi.direction == Direction.Down and bar1.low == last_bi.low
    lc2 = bar1.close < bar1.open and bar2.close > bar2.cache[cache_key] * (1 + th / 10000) > bar2.open
    if len(c.bars_ubi) < 7 and lc1 and lc2:
        v1 = "看多"

    sc1 = last_bi.direction == Direction.Up and bar1.high == last_bi.high
    sc2 = bar1.close > bar1.open and bar2.close < bar2.cache[cache_key] * (1 - th / 10000) < bar2.open
    if len(c.bars_ubi) < 7 and sc1 and sc2:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_end_V230312(c: CZSC, **kwargs):
    """MACD辅助判断笔结束信号

    参数模板："{freq}_D0MACD{fastperiod}#{slowperiod}#{signalperiod}_BE辅助V230312"

    **信号逻辑：**

    1. 看多，当下笔向下，笔的最后一个分型MACD向上
    2. 反之，看空，当下笔向上，笔的最后一个分型MACD向下

    **信号列表：**

    - Signal('15分钟_D0MACD12#26#9_BE辅助V230312_看多_任意_任意_0')
    - Signal('15分钟_D0MACD12#26#9_BE辅助V230312_看空_任意_任意_0')

    **Notes：**

    1. BE 是 Bi End 的缩写

    :param c: CZSC对象
    :return: 信号识别结果
    """
    fastperiod = int(kwargs.get("fastperiod", 12))
    slowperiod = int(kwargs.get("slowperiod", 26))
    signalperiod = int(kwargs.get("signalperiod", 9))
    k1, k2, k3 = f"{c.freq.value}_D0MACD{fastperiod}#{slowperiod}#{signalperiod}_BE辅助V230312".split('_')
    v1 = "其他"

    cache_key = update_macd_cache(c, **kwargs)
    if len(c.bi_list) < 3 or len(c.bars_ubi) >= 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi: BI = c.bi_list[-1]
    last_fx: FX = last_bi.fx_b
    macd1 = last_fx.raw_bars[-1].cache[cache_key]['macd']
    macd2 = last_fx.raw_bars[0].cache[cache_key]['macd']

    if last_bi.direction == Direction.Down and macd1 > macd2:
        v1 = "看多"

    if last_bi.direction == Direction.Up and macd1 < macd2:
        v1 = "看空"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_end_V230320(c: CZSC, **kwargs) -> OrderedDict:
    """100以内质数时序窗口辅助笔结束判断

    参数模板："{freq}_D0质数窗口MO{max_overlap}_BE辅助V230320"

    **信号逻辑：**

    1. 未完成笔延伸长度等于某个质数，且最后3根K线创新高，或者新低，笔结束

    **信号列表：**

    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_17K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_23K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_29K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_11K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_13K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_19K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_37K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_41K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_13K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_11K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_17K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_19K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_23K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_37K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_31K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_29K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_31K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_41K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_43K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_47K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看多_43K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_53K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_59K_任意_0')
    - Signal('15分钟_D0质数窗口MO3_BE辅助V230320_看空_61K_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    max_overlap = int(kwargs.get("max_overlap", 3))
    k1, k2, k3 = f"{c.freq.value}_D0质数窗口MO{max_overlap}_BE辅助V230320".split("_")
    v1 = "其他"
    if len(c.bi_list) < 3:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
    primes = [11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

    last_bi = c.bi_list[-1]
    bars = c.bars_ubi[1:]
    raw_bars = [y for x in bars for y in x.raw_bars]
    ubi_len = len(raw_bars)
    ubi_min = min([x.low for x in raw_bars])
    ubi_max = max([x.high for x in raw_bars])
    mop_bars = raw_bars[-max_overlap:]

    if last_bi.direction == Direction.Up and ubi_len in primes and min([x.low for x in mop_bars]) == ubi_min:
        v1 = "看多"
        v2 = f"{ubi_len}K"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    if last_bi.direction == Direction.Down and ubi_len in primes and max([x.high for x in mop_bars]) == ubi_max:
        v1 = "看空"
        v2 = f"{ubi_len}K"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_end_V230322(c: CZSC, **kwargs) -> OrderedDict:
    """分型配合均线辅助判断笔的结束

    参数模板："{freq}_D0分型配合{ma_type}#{timeperiod}_BE辅助V230322"

    **信号逻辑：**

    1. 对于顶分型，如果最右边的k线的MA最小，这是向下笔正常延伸的情况
    2. 对于底分型，如果最右边的k线的MA最大，这是向上笔正常延伸的情况

    **信号列表：**

    - Signal('15分钟_D0分型配合SMA#5_BE辅助V230322_看多_同向分型_任意_0')
    - Signal('15分钟_D0分型配合SMA#5_BE辅助V230322_看空_反向分型_任意_0')
    - Signal('15分钟_D0分型配合SMA#5_BE辅助V230322_看多_反向分型_任意_0')
    - Signal('15分钟_D0分型配合SMA#5_BE辅助V230322_看空_同向分型_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    ma_type = kwargs.get("ma_type", "SMA")
    timeperiod = int(kwargs.get("timeperiod", 5))
    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D0分型配合{ma_type}#{timeperiod}_BE辅助V230322".split("_")
    v1, v2 = "其他", "任意"
    ubi_fxs = c.ubi_fxs
    last_bar = c.bars_raw[-1]

    if len(c.bi_list) < 3 or len(c.bars_ubi) > 7 or len(ubi_fxs) == 0 or last_bar.dt != ubi_fxs[-1].raw_bars[-1].dt:
        # 1. 未形成笔
        # 2. 笔结束后的k线数大于7
        # 3. 未形成分型
        # 4. 最后一个分型结束时间不是最后一个k线的结束时间
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    last_fx = ubi_fxs[-1]
    max_ma = max([x.cache[cache_key] for x in last_fx.raw_bars])
    min_ma = min([x.cache[cache_key] for x in last_fx.raw_bars])
    right_ma = last_fx.raw_bars[-1].cache[cache_key]

    if last_bi.direction == Direction.Up:
        if last_fx.mark == Mark.G and right_ma == min_ma:
            v1 = "看空"
            v2 = "同向分型"

        if last_fx.mark == Mark.D and right_ma != max_ma:
            v1 = "看空"
            v2 = "反向分型"

    if last_bi.direction == Direction.Down:
        if last_fx.mark == Mark.D and right_ma == max_ma:
            v1 = "看多"
            v2 = "同向分型"

        if last_fx.mark == Mark.G and right_ma != min_ma:
            v1 = "看多"
            v2 = "反向分型"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_bi_end_V230324(c: CZSC, **kwargs) -> OrderedDict:
    """笔结束分型的均线突破判断笔的结束

    参数模板："{freq}_D0{ma_type}#{timeperiod}均线突破_BE辅助V230324"

    **信号逻辑：**

    1. 向上笔最后一个顶分型左边两个k线的MA最小值被收盘价突破，向上笔结束
    2. 向下笔最后一个底分型左边两个k线的MA最大值被收盘价突破，向下笔结束

    **信号列表：**

    - Signal('15分钟_D0SMA#5均线突破_BE辅助V230324_看空_任意_任意_0')
    - Signal('15分钟_D0SMA#5均线突破_BE辅助V230324_看多_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    ma_type = kwargs.get("ma_type", "SMA")
    timeperiod = int(kwargs.get("timeperiod", 5))
    cache_key = update_ma_cache(c, ma_type=ma_type, timeperiod=timeperiod)
    k1, k2, k3 = f"{c.freq.value}_D0{ma_type}#{timeperiod}均线突破_BE辅助V230324".split("_")
    v1 = "其他"
    ubi_fxs = c.ubi_fxs

    if len(c.bi_list) < 3 or len(c.bars_ubi) > 7 or len(ubi_fxs) == 0:
        # 1. 未形成笔
        # 2. 笔结束后的k线数大于7
        # 3. 未形成分型
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    last_fx = last_bi.fx_b
    max_ma = max([x.cache[cache_key] for x in last_fx.raw_bars[:-1]])
    min_ma = min([x.cache[cache_key] for x in last_fx.raw_bars[:-1]])
    last_close = c.bars_raw[-2].close

    if last_bi.direction == Direction.Up and last_close < min_ma:
        v1 = "看空"

    if last_bi.direction == Direction.Down and last_close > max_ma:
        v1 = "看多"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_status_V230101(c: CZSC, **kwargs) -> OrderedDict:
    """笔的表里关系

    参数模板："{freq}_D1_表里关系V230101"

    表里关系的定义参考：http://blog.sina.com.cn/s/blog_486e105c01007wc1.html

    **信号逻辑：**

    1. 最后一笔向下，且未完成笔的长度大于7根K线，表里关系为向上，否则为向下；
    2. 最后一笔向上，且未完成笔的长度大于7根K线，表里关系为向下，否则为向上；
    3. 向下的笔遇到底分型，表里关系为底分；向上笔的遇到底分型为延伸；
    4. 向上的笔遇到顶分型，表里关系为顶分；向下笔的遇到顶分型为延伸。

    **信号列表：**

    - Signal('15分钟_D1_表里关系V230101_向下_延伸_任意_0')
    - Signal('15分钟_D1_表里关系V230101_向下_底分_任意_0')
    - Signal('15分钟_D1_表里关系V230101_向上_顶分_任意_0')
    - Signal('15分钟_D1_表里关系V230101_向上_延伸_任意_0')

    :param c: CZSC 对象
    :return: 信号字典
    """
    k1, k2, k3, v1 = c.freq.value, "D1", "表里关系V230101", "其他"
    fxs = c.ubi_fxs
    if len(c.bi_list) < 3 or len(fxs) < 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    if last_bi.direction == Direction.Down:
        v1 = "向上" if len(c.bars_ubi) > 7 else "向下"
    else:
        assert last_bi.direction == Direction.Up
        v1 = "向下" if len(c.bars_ubi) > 7 else "向上"

    if fxs[-1].mark == Mark.D:
        v2 = "底分" if v1 == "向下" else "延伸"
    else:
        assert fxs[-1].mark == Mark.G
        v2 = "顶分" if v1 == "向上" else "延伸"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_bi_status_V230102(c: CZSC, **kwargs) -> OrderedDict:
    """笔的表里关系

    参数模板："{freq}_D1_表里关系V230102"

    表里关系的定义参考：http://blog.sina.com.cn/s/blog_486e105c01007wc1.html

    **信号逻辑：**

    1. 最后一笔向下，且未完成笔的长度大于7根K线，表里关系为向上，否则为向下；
    2. 最后一笔向上，且未完成笔的长度大于7根K线，表里关系为向下，否则为向上；
    3. 向下的笔遇到底分型，表里关系为底分；向上笔的遇到底分型为延伸；
    4. 向上的笔遇到顶分型，表里关系为顶分；向下笔的遇到顶分型为延伸。

    **信号列表：**

    - Signal('15分钟_D1_表里关系V230102_向下_底分_任意_0')
    - Signal('15分钟_D1_表里关系V230102_向下_延伸_任意_0')
    - Signal('15分钟_D1_表里关系V230102_向上_顶分_任意_0')
    - Signal('15分钟_D1_表里关系V230102_向上_延伸_任意_0')

    **注意：** 与 cxt_bi_status_V230101 的区别在于，该信号只在分型成立的最后一根K线触发，而不是每根K线都会触发。

    :param c: CZSC 对象
    :return: 信号字典
    """
    k1, k2, k3, v1 = c.freq.value, "D1", "表里关系V230102", "其他"
    fxs = c.ubi_fxs
    if len(c.bi_list) < 3 or len(fxs) < 1 or c.bars_raw[-1].dt != fxs[-1].raw_bars[-1].dt:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    last_bi = c.bi_list[-1]
    if last_bi.direction == Direction.Down:
        v1 = "向上" if len(c.bars_ubi) > 7 else "向下"
    else:
        assert last_bi.direction == Direction.Up
        v1 = "向下" if len(c.bars_ubi) > 7 else "向上"

    if fxs[-1].mark == Mark.D:
        v2 = "底分" if v1 == "向下" else "延伸"
    else:
        assert fxs[-1].mark == Mark.G
        v2 = "顶分" if v1 == "向上" else "延伸"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_bi_zdf_V230601(c: CZSC, **kwargs) -> OrderedDict:
    """BI涨跌幅的分层判断

    参数模板："{freq}_D{di}N{n}_分层V230601"

     **信号逻辑：**

    取最近50个缠论笔，计算涨跌幅，分N层判断。

     **信号列表：**

    - Signal('60分钟_D1N5_分层V230601_向下_第5层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向上_第5层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向下_第3层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向上_第2层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向上_第4层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向下_第2层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向上_第1层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向下_第1层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向上_第3层_任意_0')
    - Signal('60分钟_D1N5_分层V230601_向下_第4层_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典
        - di: 倒数第几根K线
        - n: 取截止dik的前n根K线
    :return: 返回信号结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 5))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}_分层V230601".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bi_list) < 10 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=50)
    v1 = bis[-1].direction.value
    powers = [x.power for x in bis]
    v2 = pd.qcut(powers, n, labels=False, duplicates='drop')[-1]
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=f"第{v2 + 1}层")


def cxt_bi_end_V230618(c: CZSC, **kwargs) -> OrderedDict:
    """笔结束辅助判断

    参数模板："{freq}_D{di}MO{max_overlap}_BE辅助V230618"

    **信号逻辑：**

    以向下笔为例，判断笔内是否有小级别中枢，如果有则看多：

    1. 笔内任意两根k线的重叠使该价格位的计数加1，计算从笔.high到笔.low之间各价格位的重叠次数
    2. 通过各价格位的重叠可以得到横轴价格，纵轴重叠次数的图，通过计算途中波峰的个数来得到近似的小中枢个数
        例子：横轴从小到大对应的重叠次数为 1112233211112133334445553321，则可以通过计算从n变为1的次数来得到波峰个数
        这里2-1，2-1，2-1，得到波峰数为3

    **信号列表：**

    - Signal('日线_D1MO1_BE辅助V230618_看多_1小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_3小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_2小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_1小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看多_2小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_5小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看空_4小中枢_任意_0')
    - Signal('日线_D1MO1_BE辅助V230618_看多_3小中枢_任意_0')

    **信号说明：**

    类似 cxt_third_bs_V230318 信号，但增加了笔内有无小级别中枢的判断。用k线重叠来近似小级别中枢的判断

    :param c: CZSC对象
    :param kwargs:

        - di: int, 默认1，表示取倒数第几笔
        - max_overlap: int, 默认3，表示笔内最多允许有几个信号重叠

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    max_overlap = int(kwargs.get("max_overlap", 3))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}MO{max_overlap}_BE辅助V230618".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6 or len(c.bars_ubi) > 3 + max_overlap - 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    def __cal_zs_number(raw_bars):
        """计算笔内的小中枢数量

        **信号逻辑：**

        1. 笔内任意两根k线的重叠使该价格位的计数加1，计算从笔.high到笔.low之间各价格位的重叠次数
        2. 通过各价格位的重叠可以得到横轴价格，纵轴重叠次数的图，通过计算途中波峰的个数来得到近似的小中枢个数
        例子：横轴从小到大对应的重叠次数为 1112233211112133334445553321，则可以通过计算从n变为1的次数来得到波峰个数
        这里2-1，2-1，2-1，得到波峰数为3

        :param raw_bars: 构成笔的bar
        :return: 小中枢数量
        """
        # 用笔内价格极值取得笔内价格范围
        max_price = max(bar.high for bar in raw_bars[:-1])
        min_price = min(bar.low for bar in raw_bars[:-1])
        price_range = max_price - min_price

        # 计算当前k线所覆盖的笔内价格范围，并用百分比表示
        for bar in raw_bars[:-1]:
            bar_high_pct = int((100 * (bar.high - min_price) / price_range))
            bar_low_pct = int((100 * (bar.low - min_price) / price_range))
            bar.dt_high_pct = bar_high_pct
            bar.dt_low_pct = bar_low_pct

        # 用这个list保存每个价格的重叠次数，把每个价格映射到100以内的区间内
        df_chengjiaoqu = [[i, 0] for i in range(101)]

        # 对每个k线进行映射，把该k线的价格范围映射到df_chengjiaoqu
        for bar in raw_bars[:-1]:
            range_max = bar.dt_high_pct
            range_min = bar.dt_low_pct

            if range_max == range_min:
                df_chengjiaoqu[range_max][1] += 1
            else:
                for i in range(range_min, range_max + 1):
                    df_chengjiaoqu[i][1] += 1

        # 计算波峰个数，相当于有多少个小中枢
        # 每个波峰结束后价格重叠区域必然会回到1
        peak_count = 0
        for i in range(1, len(df_chengjiaoqu) - 1):
            if df_chengjiaoqu[i][1] == 1 and df_chengjiaoqu[i][1] < df_chengjiaoqu[i - 1][1]:
                peak_count += 1
        return peak_count

    bi = c.bi_list[-di]
    zs_count = __cal_zs_number(bi.raw_bars)
    v1 = '看多' if bi.direction == Direction.Down else '看空'
    # 为了增加稳定性，要确保笔内有小中枢，并且要确保笔内有至少2个分型存在，保证从上往下的分型12的长度比分型34的长度大，来确认背驰
    if len(bi.fxs) >= 4 and zs_count >= 1 and (bi.fxs[-4].fx - bi.fxs[-3].fx) - (bi.fxs[-2].fx - bi.fxs[-1].fx) > 0:
        v2 = f"{zs_count}小中枢"
    else:
        v2 = "其他"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_three_bi_V230618(c: CZSC, **kwargs) -> OrderedDict:
    """三笔形态分类

    参数模板："{freq}_D{di}三笔_形态V230618"

    **信号逻辑：**

    三笔的形态分类

    **信号列表：**

    - Signal('日线_D1三笔_形态V230618_向下盘背_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上奔走型_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上扩张_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下奔走型_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上收敛_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下无背_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上不重合_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下收敛_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下扩张_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向下不重合_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上盘背_任意_任意_0')
    - Signal('日线_D1三笔_形态V230618_向上无背_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}三笔_形态V230618".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=3)
    assert len(bis) == 3 and bis[0].direction == bis[2].direction
    bi1, bi2, bi3 = bis

    # 识别向下形态
    if bi3.direction == Direction.Down:
        if bi3.low > bi1.high:
            v1 = '向下不重合'
        elif bi2.low < bi3.low < bi1.high < bi2.high:
            v1 = '向下奔走型'
        elif bi1.high > bi3.high and bi1.low < bi3.low:
            v1 = '向下收敛'
        elif bi1.high < bi3.high and bi1.low > bi3.low:
            v1 = '向下扩张'
        elif bi3.low < bi1.low and bi3.high < bi1.high:
            v1 = '向下盘背' if bi3.power < bi1.power else '向下无背'

    # 识别向上形态
    elif bi3.direction == Direction.Up:
        if bi3.high < bi1.low:
            v1 = '向上不重合'
        elif bi2.low < bi1.low < bi3.high < bi2.high:
            v1 = '向上奔走型'
        elif bi1.high > bi3.high and bi1.low < bi3.low:
            v1 = '向上收敛'
        elif bi1.high < bi3.high and bi1.low > bi3.low:
            v1 = '向上扩张'
        elif bi3.low > bi1.low and bi3.high > bi1.high:
            v1 = '向上盘背' if bi3.power < bi1.power else '向上无背'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_five_bi_V230619(c: CZSC, **kwargs) -> OrderedDict:
    """五笔形态分类

    参数模板："{freq}_D{di}五笔_形态V230619"

    **信号逻辑：**

    五笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1五笔_形态V230619_上颈线突破_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类三卖_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类趋势底背驰_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类趋势顶背驰_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_下颈线突破_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_类三买_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_aAb式顶背驰_任意_任意_0')
    - Signal('60分钟_D1五笔_形态V230619_aAb式底背驰_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}五笔_形态V230619".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 6 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=5)
    assert len(bis) == 5 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5 = bis

    direction = bi1.direction
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    assert direction in [Direction.Down, Direction.Up], "direction 的取值错误"

    if direction == Direction.Down:
        # aAb式底背驰
        if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and max_high == bi1.high and bi5.power < bi1.power:
            if (min_low == bi3.low and bi5.low < bi1.low) or (min_low == bi5.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式底背驰')

        # 类趋势底背驰
        if max_high == bi1.high and min_low == bi5.low and bi4.high < bi2.low and bi5.power < max(bi3.power, bi1.power):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势底背驰')

        # 上颈线突破
        if (min_low == bi1.low and bi5.high > min(bi1.high, bi2.high) > bi5.low > bi1.low) \
                or (min_low == bi3.low and bi5.high > bi3.high > bi5.low > bi3.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='上颈线突破')

        # 五笔三买，要求bi5.high是最高点
        if max_high == bi5.high > bi5.low > max(bi1.high, bi3.high) \
                > min(bi1.high, bi3.high) > max(bi1.low, bi3.low) > min_low:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买')

    if direction == Direction.Up:
        # aAb式顶背驰
        if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and min_low == bi1.low and bi5.power < bi1.power:
            if (max_high == bi3.high and bi5.high > bi1.high) or (max_high == bi5.high):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式顶背驰')

        # 类趋势顶背驰
        if min_low == bi1.low and max_high == bi5.high and bi5.power < max(bi1.power, bi3.power) and bi4.low > bi2.high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势顶背驰')

        # 下颈线突破
        if (max_high == bi1.high and bi5.low < max(bi1.low, bi2.low) < bi5.high < max_high) \
                or (max_high == bi3.high and bi5.low < bi3.low < bi5.high < max_high):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='下颈线突破')

        # 五笔三卖，要求bi5.low是最低点
        if min_low == bi5.low < bi5.high < min(bi1.low, bi3.low) \
                < max(bi1.low, bi3.low) < min(bi1.high, bi3.high) < max_high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三卖')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_seven_bi_V230620(c: CZSC, **kwargs) -> OrderedDict:
    """七笔形态分类

    参数模板："{freq}_D{di}七笔_形态V230620"

    **信号逻辑：**

    七笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1七笔_形态V230620_类三卖_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_向上中枢完成_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAbcd式顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_类三买_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_向下中枢完成_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAb式底背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_abcAd式顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_abcAd式底背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAb式顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_类趋势顶背驰_任意_任意_0')
    - Signal('60分钟_D1七笔_形态V230620_aAbcd式底背驰_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}七笔_形态V230620".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 10 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=7)
    assert len(bis) == 7 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5, bi6, bi7 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    direction = bi7.direction

    if direction == Direction.Down:
        if bi1.high == max_high and bi7.low == min_low:
            # aAbcd式底背驰
            if min(bi2.high, bi4.high) > max(bi2.low, bi4.low) > bi6.high and bi7.power < bi5.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式底背驰')

            # abcAd式底背驰
            if bi2.low > min(bi4.high, bi6.high) > max(bi4.low, bi6.low) and bi7.power < (bi1.high - bi3.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='abcAd式底背驰')

            # aAb式底背驰
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) and bi7.power < bi1.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式底背驰')

            # 类趋势底背驰
            if bi2.low > bi4.high and bi4.low > bi6.high and bi7.power < max(bi5.power, bi3.power, bi1.power):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势底背驰')

        # 向上中枢完成
        if bi4.low == min_low and min(bi1.high, bi3.high) > max(bi1.low, bi3.low) \
                and min(bi5.high, bi7.high) > max(bi5.low, bi7.low) \
                and max(bi4.high, bi6.high) > min(bi3.high, bi4.high):
            if max(bi1.low, bi3.low) < max(bi5.high, bi7.high):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='向上中枢完成')

        # 七笔三买：1~3构成中枢，最低点在1~3，最高点在5~7，5~7的最低点大于1~3的最高点
        if min(bi1.low, bi3.low) == min_low and max(bi5.high, bi7.high) == max_high \
                and min(bi5.low, bi7.low) > max(bi1.high, bi3.high) \
                and min(bi1.high, bi3.high) > max(bi1.low, bi3.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买')

    if direction == Direction.Up:
        # 顶背驰
        if bi1.low == min_low and bi7.high == max_high:
            # aAbcd式顶背驰
            if bi6.low > min(bi2.high, bi4.high) > max(bi2.low, bi4.low) and bi7.power < bi5.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式顶背驰')

            # abcAd式顶背驰
            if min(bi4.high, bi6.high) > max(bi4.low, bi6.low) > bi2.high and bi7.power < (bi3.high - bi1.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='abcAd式顶背驰')

            # aAb式顶背驰
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) and bi7.power < bi1.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式顶背驰')

            # 类趋势顶背驰
            if bi2.high < bi4.low and bi4.high < bi6.low and bi7.power < max(bi5.power, bi3.power, bi1.power):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势顶背驰')

        # 向下中枢完成
        if bi4.high == max_high and min(bi1.high, bi3.high) > max(bi1.low, bi3.low) \
                and min(bi5.high, bi7.high) > max(bi5.low, bi7.low) \
                and min(bi4.low, bi6.low) < max(bi3.low, bi4.low):
            if min(bi1.high, bi3.high) > min(bi5.low, bi7.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='向下中枢完成')

        # 七笔三卖：1~3构成中枢，最高点在1~3，最低点在5~7，5~7的最高点小于1~3的最低点
        if min(bi5.low, bi7.low) == min_low and max(bi1.high, bi3.high) == max_high \
                and max(bi7.high, bi5.high) < min(bi1.low, bi3.low) \
                and min(bi1.high, bi3.high) > max(bi1.low, bi3.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三卖')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_nine_bi_V230621(c: CZSC, **kwargs) -> OrderedDict:
    """九笔形态分类

    参数模板："{freq}_D{di}九笔_形态V230621"

    **信号逻辑：**

    九笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1九笔_形态V230621_类三买A_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAb式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_类三卖A_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbcd式类一买_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_ABC式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbBc式类一买_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbcd式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_ZD三卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_aAbBc式类一卖_任意_任意_0')
    - Signal('60分钟_D1九笔_形态V230621_ABC式类一买_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}九笔_形态V230621".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 13 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=9)
    assert len(bis) == 9 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    direction = bi9.direction

    if direction == Direction.Down:
        if min_low == bi9.low and max_high == bi1.high:
            # aAb式类一买
            if min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low) \
                    and bi9.power < bi1.power and bi3.low >= bi1.low and bi7.high <= bi9.high:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式类一买')

            # aAbcd式类一买
            if min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) > bi8.high \
                    and bi9.power < bi7.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式类一买')

            # ABC式类一买
            if bi3.low < bi1.low and bi7.high > bi9.high \
                    and min(bi4.high, bi6.high) > max(bi4.low, bi6.low) \
                    and (bi1.high - bi3.low) > (bi7.high - bi9.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ABC式类一买')

            # 类趋势一买
            if bi8.high < bi6.low < bi6.high < bi4.low < bi4.high < bi2.low \
                    and bi9.power < max([bi1.power, bi3.power, bi5.power, bi7.power]):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势一买')

        # aAbBc式类一买（2~4构成中枢A，6~8构成中枢B，9背驰）
        if max_high == max(bi1.high, bi3.high) and min_low == bi9.low \
                and min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                and min(bi2.low, bi4.low) > max(bi6.high, bi8.high) \
                and min(bi6.high, bi8.high) > max(bi6.low, bi8.low) \
                and bi9.power < bi5.power:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbBc式类一买')

        # 类三买（1357构成中枢，最低点在3或5）
        if max_high == bi9.high > bi9.low \
                > max([x.high for x in [bi1, bi3, bi5, bi7]]) \
                > min([x.high for x in [bi1, bi3, bi5, bi7]]) \
                > max([x.low for x in [bi1, bi3, bi5, bi7]]) \
                > min([x.low for x in [bi3, bi5]]) == min_low:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买A')

        # 类三买（357构成中枢，8的力度小于2，9回调不跌破GG构成三买）
        if bi8.power < bi2.power and max_high == bi9.high > bi9.low \
                > max([x.high for x in [bi3, bi5, bi7]]) \
                > min([x.high for x in [bi3, bi5, bi7]]) \
                > max([x.low for x in [bi3, bi5, bi7]]) > bi1.low == min_low:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买B')

        if min_low == bi5.low and max_high == bi1.high and bi4.high < bi2.low:  # 前五笔构成向下类趋势
            zd = max([x.low for x in [bi5, bi7]])
            zg = min([x.high for x in [bi5, bi7]])
            gg = max([x.high for x in [bi5, bi7]])
            if zg > zd and bi8.high > gg:  # 567构成中枢，且8的高点大于gg
                if bi9.low > zg:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ZG三买')

                # 类二买
                if bi9.high > gg > zg > bi9.low > zd:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二买')

    if direction == Direction.Up:
        if max_high == bi9.high and min_low == bi1.low:
            # aAbBc式类一卖
            if bi6.low > min(bi2.high, bi4.high) > max(bi2.low, bi4.low) \
                    and min(bi6.high, bi8.high) > max(bi6.low, bi8.low) \
                    and max(bi2.high, bi4.high) < min(bi6.low, bi8.low) \
                    and bi9.power < bi5.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbBc式类一卖')

            # aAb式类一卖
            if min(bi2.high, bi4.high, bi6.high, bi8.high) > max(bi2.low, bi4.low, bi6.low, bi8.low) \
                    and bi9.power < bi1.power and bi3.high <= bi1.high and bi7.low >= bi9.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAb式类一卖')

            # aAbcd式类一卖
            if bi8.low > min(bi2.high, bi4.high, bi6.high) > max(bi2.low, bi4.low, bi6.low) \
                    and bi9.power < bi7.power:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='aAbcd式类一卖')

            # ABC式类一卖
            if bi3.high > bi1.high and bi7.low < bi9.low \
                    and min(bi4.high, bi6.high) > max(bi4.low, bi6.low) \
                    and (bi3.high - bi1.low) > (bi9.high - bi7.low):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ABC式类一卖')

            # 类趋势一卖
            if bi8.low > bi6.high > bi6.low > bi4.high > bi4.low > bi2.high \
                    and bi9.power < max([bi1.power, bi3.power, bi5.power, bi7.power]):
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类趋势一卖')

        # 九笔三卖
        if max_high == bi1.high and min_low == bi9.low \
                and bi9.high < max([x.low for x in [bi3, bi5, bi7]]) < min([x.high for x in [bi3, bi5, bi7]]):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三卖A')

        if min_low == bi1.low and max_high == bi5.high and bi2.high < bi4.low:  # 前五笔构成向上类趋势
            zd = max([x.low for x in [bi5, bi7]])
            zg = min([x.high for x in [bi5, bi7]])
            dd = min([x.low for x in [bi5, bi7]])
            if zg > zd and bi8.low < dd:  # 567构成中枢，且8的低点小于dd
                if bi9.high < zd:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='ZD三卖')

                # 类二卖
                if dd < zd <= bi9.high < zg:
                    return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二卖')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_eleven_bi_V230622(c: CZSC, **kwargs) -> OrderedDict:
    """十一笔形态分类

    参数模板："{freq}_D{di}十一笔_形态V230622"

    **信号逻辑：**

    十一笔的形态分类

    **信号列表：**

    - Signal('60分钟_D1十一笔_形态V230622_类三买_任意_任意_0')
    - Signal('60分钟_D1十一笔_形态V230622_A3B3C5式类一卖_任意_任意_0')
    - Signal('60分钟_D1十一笔_形态V230622_类二买_任意_任意_0')
    - Signal('60分钟_D1十一笔_形态V230622_A5B3C3式类一卖_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}十一笔_形态V230622".split('_')
    v1 = "其他"
    if len(c.bi_list) < di + 16 or len(c.bars_ubi) > 7:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bis = get_sub_elements(c.bi_list, di=di, n=11)
    assert len(bis) == 11 and bis[0].direction == bis[2].direction == bis[4].direction, "笔的方向错误"
    bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11 = bis
    max_high = max([x.high for x in bis])
    min_low = min([x.low for x in bis])
    direction = bi11.direction

    if direction == Direction.Down:
        if min_low == bi11.low and max_high == bi1.high:
            # ABC式类一买，A5B3C3
            if bi5.low == min([x.low for x in [bi1, bi3, bi5]]) \
                    and bi9.low > bi11.low and bi9.high > bi11.high \
                    and bi8.high > bi6.low and bi1.high - bi5.low > bi9.high - bi11.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A5B3C3式类一买')

            # ABC式类一买，A3B3C5
            if bi1.high > bi3.high and bi1.low > bi3.low \
                    and bi7.high == max([x.high for x in [bi7, bi9, bi11]]) \
                    and bi6.high > bi4.low and bi1.high - bi3.low > bi7.high - bi11.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B3C5式类一买')

            # ABC式类一买，A3B5C3
            if bi1.low > bi3.low and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi9.high > bi11.high and bi1.high - bi3.low > bi9.high - bi11.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B5C3式类一买')

            # a1Ab式类一买，a1（1~7构成的类趋势）
            if bi2.low > bi4.high > bi4.low > bi6.high > bi5.low > bi7.low and bi10.high > bi8.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='a1Ab式类一买')

        # 类二买（1~7构成盘整背驰，246构成下跌中枢，9/11构成上涨中枢，且上涨中枢GG大于下跌中枢ZG）
        if bi7.power < bi1.power and min_low == bi7.low < max([x.low for x in [bi2, bi4, bi6]]) \
                < min([x.high for x in [bi2, bi4, bi6]]) < max([x.high for x in [bi9, bi11]]) < bi1.high == max_high \
                and bi11.low > min([x.low for x in [bi2, bi4, bi6]]) \
                and min([x.high for x in [bi9, bi11]]) > max([x.low for x in [bi9, bi11]]):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二买')

        # 类二买（1~7为区间极值，9~11构成上涨中枢，上涨中枢GG大于4~6的最大值，上涨中枢DD大于4~6的最小值）
        if max_high == bi1.high and min_low == bi7.low \
                and min(bi9.high, bi11.high) > max(bi9.low, bi11.low) \
                and max(bi11.high, bi9.high) > max(bi4.high, bi6.high) \
                and min(bi9.low, bi11.low) > min(bi4.low, bi6.low):
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二买')

        # 类三买（1~9构成大级别中枢，10离开，11回调不跌破GG）
        gg = max([x.high for x in [bi1, bi2, bi3]])
        zg = min([x.high for x in [bi1, bi2, bi3]])
        zd = max([x.low for x in [bi1, bi2, bi3]])
        dd = min([x.low for x in [bi1, bi2, bi3]])
        if max_high == bi11.high and bi11.low > zg > zd \
                and gg > bi5.low and gg > bi7.low and gg > bi9.low \
                and dd < bi5.high and dd < bi7.high and dd < bi9.high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类三买')

    if direction == Direction.Up:
        if max_high == bi11.high and min_low == bi1.low:
            # ABC式类一卖，A5B3C3
            if bi5.high == max([bi1.high, bi3.high, bi5.high]) and bi9.low < bi11.low and bi9.high < bi11.high \
                    and bi8.low < bi6.high and bi11.high - bi9.low < bi5.high - bi1.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A5B3C3式类一卖')

            # ABC式类一卖，A3B3C5
            if bi7.low == min([bi11.low, bi9.low, bi7.low]) and bi1.high < bi3.high and bi1.low < bi3.low \
                    and bi6.low < bi4.high and bi11.high - bi7.low < bi3.high - bi1.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B3C5式类一卖')

            # ABC式类一卖，A3B5C3
            if bi1.high < bi3.high and min(bi4.high, bi6.high, bi8.high) > max(bi4.low, bi6.low, bi8.low) \
                    and bi9.low < bi11.low and bi3.high - bi1.low > bi11.high - bi9.low:
                return create_single_signal(k1=k1, k2=k2, k3=k3, v1='A3B5C3式类一卖')

        # 类二卖：1~9构成类趋势，11不创新高
        if max_high == bi9.high > bi8.low > bi6.high > bi6.low > bi4.high > bi4.low > bi2.high > bi1.low == min_low \
                and bi11.high < bi9.high:
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1='类二卖')

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_range_oscillation_V230620(c: CZSC, **kwargs) -> OrderedDict:
    """判断区间震荡

    参数模板："{freq}_D{di}TH{th}_区间震荡V230620"

    **信号逻辑：**

    1. 在区间震荡中，无论振幅大小，各笔的中心应改在相近的价格区间内平移，当各笔的中心的振幅大于一定数值时就认为这个窗口内没有固定区间的中枢震荡
    2. 给定阈值 th，当各笔的中心的振幅大于 th 时，认为这个窗口内没有固定区间的中枢震荡

    **信号列表：**

    - Signal('日线_D1TH5_区间震荡V230620_2笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_3笔震荡_向上_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_4笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_5笔震荡_向上_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_6笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_5笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_2笔震荡_向上_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_3笔震荡_向下_任意_0')
    - Signal('日线_D1TH5_区间震荡V230620_4笔震荡_向上_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
        - th: 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    th = int(kwargs.get('th', 2))  # 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}TH{th}_区间震荡V230620".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bi_list) < di + 11:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    def __calculate_max_amplitude_percentage(prices):
        """计算给定价位列表的最大振幅的百分比"""
        if not prices:
            return 100
        max_price, min_price = max(prices), min(prices)
        return ((max_price - min_price) / min_price) * 100 if min_price != 0 else 100

    _bis = get_sub_elements(c.bi_list, di=di, n=12)

    if len(_bis) != 12:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    price_list = []
    count = 1
    for bi in _bis[::-1]:
        price_list.append((bi.high + bi.low) / 2)
        if len(price_list) > 1:
            if __calculate_max_amplitude_percentage(price_list) < th:
                count += 1
            else:
                break

    if count != 1:
        v1 = f"{count}笔震荡"
        v2 = "向上" if _bis[-1].direction == Direction.Up else "向下"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_intraday_V230701(cat: CzscSignals, **kwargs) -> OrderedDict:
    """每日走势分类

    参数模板："{freq1}#{freq2}_D{di}日_走势分类V230701"

    **信号逻辑：**

    参见博客：https://blog.sina.com.cn/s/blog_486e105c010009uy.html

    **信号列表：**

    - Signal('30分钟#日线_D2日_走势分类V230701_强平衡市_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_弱平衡市_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_双中枢下跌_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_转折平衡市_任意_任意_0')
    - Signal('30分钟#日线_D2日_走势分类V230701_双中枢上涨_任意_任意_0')

    :param c: CZSC对象
    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 2))
    freq1 = kwargs.get("freq1", "30分钟")
    freq2 = kwargs.get("freq2", "日线")
    assert freq1 == '30分钟', 'freq1必须为30分钟'
    assert freq2 == '日线', 'freq2必须为日线'

    assert 21 > di > 0, "di必须为大于0小于21的整数，暂不支持当日走势分类"
    k1, k2, k3 = f"{freq1}#{freq2}_D{di}日_走势分类V230701".split('_')
    v1 = "其他"
    if not cat.kas or freq1 not in cat.kas.keys() or freq2 not in cat.kas.keys():
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    c1, c2 = cat.kas[freq1], cat.kas[freq2]
    day = c2.bars_raw[-di].dt.date()
    bars = [x for x in c1.bars_raw if x.dt.date() == day]
    assert len(bars) <= 8, f"仅适用于A股市场，日内有8根30分钟K线的情况, {len(bars)}, {day}, {bars}"
    if len(bars) <= 4:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    zs_list = []
    for b1, b2, b3 in zip(bars[:-2], bars[1:-1], bars[2:]):
        if min(b1.high, b2.high, b3.high) >= max(b1.low, b2.low, b3.low):
            zs_list.append([b1, b2, b3])

    _dir = "上涨" if bars[-1].close > bars[0].open else "下跌"

    if not zs_list:
        v1 = f"无中枢{_dir}"
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 双中枢的情况，有一根K线的 high low 与前后两个中枢没有重叠
    if len(zs_list) >= 2:
        zs1, zs2 = zs_list[0], zs_list[-1]
        zs1_high, zs1_low = max([x.high for x in zs1]), min([x.low for x in zs1])
        zs2_high, zs2_low = max([x.high for x in zs2]), min([x.low for x in zs2])
        if _dir == "上涨" and zs1_high < zs2_low: # type: ignore
            v1 = f"双中枢{_dir}"
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

        if _dir == "下跌" and zs1_low > zs2_high: # type: ignore
            v1 = f"双中枢{_dir}"
            return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    # 单中枢的情况，前三根K线出现高点：弱平衡市，前三根K线出现低点：强平衡市，否则：转折平衡市
    high_first = max(bars[0].high, bars[1].high, bars[2].high) == max([x.high for x in bars])
    low_first = min(bars[0].low, bars[1].low, bars[2].low) == min([x.low for x in bars])
    if high_first and not low_first:
        v1 = "弱平衡市"
    elif low_first and not high_first:
        v1 = "强平衡市"
    else:
        v1 = "转折平衡市"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_ubi_end_V230816(c: CZSC, **kwargs) -> OrderedDict:
    """当前是未完成笔的第几次新低或新高，用于笔结束辅助

    参数模板："{freq}_UBI_BE辅助V230816"

    **信号逻辑：**

    以向上未完成笔为例：取所有顶分型，计算创新高的底分型数量N，如果当前K线创新高，则新高次数为N+1

    **信号列表：**

    - Signal('日线_UBI_BE辅助V230816_新低_第4次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第5次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第6次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第2次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第3次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第4次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第5次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第6次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新高_第7次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第2次_任意_0')
    - Signal('日线_UBI_BE辅助V230816_新低_第3次_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_UBI_BE辅助V230816".split('_')
    v1, v2 = '其他','其他'
    ubi = c.ubi
    if not ubi or len(ubi['fxs']) <= 2 or len(c.bars_ubi) <= 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    fxs = ubi['fxs']
    if ubi['direction'] == Direction.Up:
        fxs = [x for x in fxs if x.mark == Mark.G]
        cnt = 1
        cur_hfx = fxs[0]
        for fx in fxs[1:]:
            if fx.high > cur_hfx.high:
                cnt += 1
                cur_hfx = fx

        if ubi['raw_bars'][-1].high > cur_hfx.high:
            v1 = '新高'
            v2 = f"第{cnt + 1}次"

    if ubi['direction'] == Direction.Down:
        fxs = [x for x in fxs if x.mark == Mark.D]
        cnt = 1
        cur_lfx = fxs[0]
        for fx in fxs[1:]:
            if fx.low < cur_lfx.low:
                cnt += 1
                cur_lfx = fx

        if ubi['raw_bars'][-1].low < cur_lfx.low:
            v1 = '新低'
            v2 = f"第{cnt + 1}次"

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_bi_end_V230815(c: CZSC, **kwargs) -> OrderedDict:
    """一两根K线快速突破反向笔

    参数模板："{freq}_快速突破_BE辅助V230815"

    **信号逻辑：**

    以向上笔为例：右侧分型完成后第一根K线的最低价低于该笔的最低价，认为向上笔结束，反向向下笔开始。

    **信号列表：**

    - Signal('15分钟_快速突破_BE辅助V230815_向下_任意_任意_0')
    - Signal('15分钟_快速突破_BE辅助V230815_向上_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:
    :return: 信号识别结果
    """
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_快速突破_BE辅助V230815".split('_')
    v1 = '其他'
    if len(c.bi_list) < 5 or len(c.bars_ubi) >= 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bi, last_bar = c.bi_list[-1], c.bars_ubi[-1]
    if bi.direction == Direction.Up and last_bar.low < bi.low:
        v1 = '向下'
    if bi.direction == Direction.Down and last_bar.high > bi.high:
        v1 = '向上'
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_stop_V230815(c: CZSC, **kwargs) -> OrderedDict:
    """定位笔的止损距离大小

    参数模板："{freq}_距离{th}BP_止损V230815"

    **信号逻辑：**

    以向上笔为例：如果当前K线的收盘价高于该笔的最高价的1 - 0.5%，则认为在止损阈值内，否则认为在止损阈值外。

    **信号列表：**

    - Signal('15分钟_距离50BP_止损V230815_向下_阈值外_任意_0')
    - Signal('15分钟_距离50BP_止损V230815_向上_阈值内_任意_0')
    - Signal('15分钟_距离50BP_止损V230815_向下_阈值内_任意_0')
    - Signal('15分钟_距离50BP_止损V230815_向上_阈值外_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - th: 止损距离阈值，单位为BP, 默认为50BP, 即0.5%

    :return: 信号识别结果
    """
    th = int(kwargs.get('th', 50))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_距离{th}BP_止损V230815".split('_')
    v1, v2 = '其他', '其他'
    if len(c.bi_list) < 5:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    bi, last_bar = c.bi_list[-1], c.bars_ubi[-1]
    if bi.direction == Direction.Up:
        v1 = '向下'
        v2 = "阈值内" if last_bar.close > bi.high * (1 - th / 10000) else "阈值外"
    if bi.direction == Direction.Down:
        v1 = '向上'
        v2 = "阈值内" if last_bar.close < bi.low * (1 + th / 10000) else "阈值外"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)


def cxt_bi_trend_V230824(c: CZSC, **kwargs) -> OrderedDict:
    """判断N笔形态，贡献者：chenglei

    参数模板："{freq}_D{di}N{n}TH{th}_形态V230824"

    **信号逻辑：**

    1. 通过对最近N笔的中心点的均值和-n笔的中心点的位置关系来判断当前N比是上涨形态还是下跌，横盘震荡形态
    2. 给定阈值 th，判断上涨下跌横盘按照 所有笔中心点/第-n笔中心点 与 正负th区间的相对位置来判断。
    3. 当在区间上时为上涨，区间内为横盘，区间下为下跌

    **信号列表：**

    - Signal('日线_D1N4TH5_形态V230824_横盘_任意_任意_0')
    - Signal('日线_D1N4TH5_形态V230824_向上_任意_任意_0')
    - Signal('日线_D1N4TH5_形态V230824_向下_任意_任意_0')

    :param c: CZSC对象
    :param kwargs:

        - di: 倒数第几笔
        - n ：检查范围
        - th: 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡

    :return: 信号识别结果
    """
    di = int(kwargs.get('di', 1))
    n = int(kwargs.get('n', 4))
    th = int(kwargs.get('th', 2))  # 振幅阈值，2 表示 2%，即 2% 以内的振幅都认为是震荡
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}TH{th}_形态V230824".split('_')
    v1 = '其他'
    if len(c.bi_list) < di + n + 2:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    _bis = get_sub_elements(c.bi_list, di=di, n=n)
    assert len(_bis) == n, f"获取第 {di} 笔到第 {di+n} 笔失败"

    all_means = [(bi.low + bi.high) / 2 for bi in _bis]
    average_of_means = sum(all_means) / n
    ratio = all_means[0] / average_of_means

    if ratio * 100 > 100 + th:
        v1 = "向下"
    elif ratio * 100 < 100 - th:
        v1 = "向上"
    else:
        v1 = "横盘"
    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


def cxt_bi_trend_V230913(c: CZSC, **kwargs) -> OrderedDict:
    """辅助判断股票通道信号，贡献者：马鸣

    参数模板："{freq}_D{di}N{n}笔趋势_高低点辅助判断V230913"

    **信号逻辑：**

    1. 倒数di笔之间的高低点形成趋势线，根据股价的当前位置，推断趋势强弱

    **信号列表：**

    - Signal('日线_D3N1笔趋势_高低点辅助判断V230913_下降趋势_超强_任意_0')
    - Signal('日线_D3N1笔趋势_高低点辅助判断V230913_观望_末笔延伸_任意_0')
    - Signal('日线_D3N1笔趋势_高低点辅助判断V230913_上升趋势_强_任意_0')
    - Signal('日线_D3N1笔趋势_高低点辅助判断V230913_观望_趋势线交叉_任意_0')
    - Signal('日线_D3N1笔趋势_高低点辅助判断V230913_下降趋势_强_任意_0')
    - Signal('日线_D3N1笔趋势_高低点辅助判断V230913_上升趋势_超强_任意_0')

    :param c: CZSC对象
    :param kwargs: 参数字典

        -:param di: 倒数di笔
        -:param n: 倒数第n根K线

    :return: 信号识别结果
    """
    di = int(kwargs.get("di", 4))
    n = int(kwargs.get("n", 1))
    freq = c.freq.value
    k1, k2, k3 = f"{freq}_D{di}N{n}笔趋势_高低点辅助判断V230913".split('_')
    v1 = "其他"
    if len(c.bi_list) <= di + 2 or len(c.bars_ubi) <= n + 1:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    up_trend_price = np.array([x.high for x in c.bi_list if x.direction == Direction.Up][-di:])
    up_trend_time = np.array([x.edt.timestamp() for x in c.bi_list if x.direction == Direction.Up][-di:]).reshape(-1, 1)

    down_trend_price = np.array([x.low for x in c.bi_list if x.direction == Direction.Down][-di:])
    down_trend_time = np.array([x.edt.timestamp() for x in c.bi_list if x.direction == Direction.Down][-di:]).reshape(-1, 1)

    model_up = LinearRegression()
    model_down = LinearRegression()
    model_up.fit(up_trend_time, up_trend_price)
    model_down.fit(down_trend_time, down_trend_price)

    new_bar_data = np.array([c.bars_ubi[-n].dt.timestamp()]).reshape(-1, 1)
    pre_up_price = model_up.predict(new_bar_data)
    pre_down_price = model_down.predict(new_bar_data)
    pre_mid_price = (pre_up_price + pre_down_price) / 2

    if pre_up_price <= pre_down_price:
        v1 = "观望"
        v2 = '趋势线交叉'
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    if len(c.bars_ubi) >= 5:
        v1 = "观望"
        v2 = '末笔延伸'
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    if c.bars_raw[-n].close >= pre_up_price:
        v1 = '上升趋势'
        v2 = '超强'
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    elif pre_mid_price < c.bars_raw[-n].close < pre_up_price:
        v1 = '上升趋势'
        v2 = '强'
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    elif pre_down_price < c.bars_raw[-n].close < pre_mid_price:
        v1 = '下降趋势'
        v2 = '强'
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    elif c.bars_raw[-n].close <= pre_down_price:
        v1 = '下降趋势'
        v2 = '超强'
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)
