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
from czsc.utils.sig import get_zs_seq
from czsc.signals.tas import update_ma_cache, update_macd_cache
from collections import OrderedDict


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
    if len(max_freq.bi_list) >= 5 and __is_zs(max_freq.bi_list[-3:]) and len(min_freq.bi_list) >= 5 and __is_zs(
            min_freq.bi_list[-3:]):

        big_zs = ZS(symbol=symbol, bis=max_freq.bi_list[-3:])
        small_zs = ZS(symbol=symbol, bis=min_freq.bi_list[-3:])

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



