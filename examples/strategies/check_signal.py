# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:27
describe: 专用于信号检查的策略
"""
import talib as ta
import numpy as np
import pandas as pd
from collections import OrderedDict
from typing import List
from loguru import logger
from czsc import CZSC, signals, RawBar, Direction
from czsc.data import TsDataCache, get_symbols
from czsc.utils import get_sub_elements, single_linear
from czsc.objects import Freq, Operate, Signal, Factor, Event, BI
from czsc.traders import CzscAdvancedTrader


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------


def cxt_first_buy_V221126(c: CZSC, di=1) -> OrderedDict:
    """单级别一买信号

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

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2, v3=v3)
    s[signal.key] = signal.value
    return s


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """择时策略"""

    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        # signals.update_macd_cache(cat.kas['60分钟'])
        # logger.info('\n\n')
        s.update(cxt_first_buy_V221126(cat.kas['15分钟'], di=1))
        return s

    tactic = {
        "base_freq": '15分钟',
        "freqs": ['60分钟', '日线'],
        "get_signals": get_signals,
    }
    return tactic


# 定义命令行接口【信号检查】的特定参数
# ----------------------------------------------------------------------------------------------------------------------

# 初始化 Tushare 数据缓存
dc = TsDataCache(r"D:\ts_data")

# 信号检查参数设置【可选】
# check_params = {
#     "symbol": "000001.SZ#E",    # 交易品种，格式为 {ts_code}#{asset}
#     "sdt": "20180101",          # 开始时间
#     "edt": "20220101",          # 结束时间
# }


check_params = {
    "symbol": "300001.SZ#E",  # 交易品种，格式为 {ts_code}#{asset}
    "sdt": "20150101",  # 开始时间
    "edt": "20220101",  # 结束时间
}
