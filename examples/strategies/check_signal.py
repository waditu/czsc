# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/31 22:27
describe: 专用于信号检查的策略
"""
from collections import OrderedDict
from typing import List
from loguru import logger
from czsc import CZSC, signals, RawBar
from czsc.data import TsDataCache, get_symbols
from czsc.utils import get_sub_elements
from czsc.objects import Freq, Operate, Signal, Factor, Event
from czsc.traders import CzscAdvancedTrader


# 定义信号函数
# ----------------------------------------------------------------------------------------------------------------------
def jcc_fen_shou_xian_V20221113(c: CZSC, di=1, zdf=300) -> OrderedDict:
    """分手线：分手形态是一个中继形态；贡献者：琅盎

    **分手线形态，有三条判断标准 **

    1.分手线是由二根开盘价相等、运动方向相反的K线组成，因此也称分离线。
    2.上升分手线出现在上升途中，由一阴一阳两根开盘价相等的K线组成，属于上涨持续形态；如果下跌趋势发展了较长时间之后出现上涨分手线，后市可能上涨应极积关注。
    3.下跌分手线出现在下跌途中，由一阳一阴两根开盘价相等的K线组成，属于下跌持续形态；如果上涨趋势发展了较长时间之后出现下跌分手线，后市可能下跌应及时出场。

    **有效信号列表： **

    - Signal('60分钟_D1K_分手线_满足_上升分手_任意_0')
    - Signal('60分钟_D1K_分手线_满足_下跌分手_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di根K线，加上这个参数就可以不用借助缓存就可以回溯
    :param zdf: 可调阈值，涨跌幅，单位 BP
    :return: 分离形态识别结果
    """
    k1, k2, k3 = f"{c.freq.value}_D{di}K_分手线".split('_')
    bar1 = c.bars_raw[-di]
    bar2 = c.bars_raw[-di - 1]

    # 条件
    v1 = '满足' if bar1.open == bar2.open and bar1.close < bar2.low or bar1.close > bar2.high else "其他"

    # 判断K线趋势【这是一个可以优化的方向】
    v2 = "其他"
    if len(c.bars_raw) > 20 + di:
        left_bars: List[RawBar] = get_sub_elements(c.bars_raw, di, n=20)
        left_max = max([x.high for x in left_bars])
        left_min = min([x.low for x in left_bars])
        gap = left_max - left_min

        if bar1.low <= left_min + 0.25 * gap and bar1.open == bar2.open and bar1.close < bar2.low \
                and bar2.close > bar2.open and (bar2.close - bar1.close) / bar2.close * 10000 > zdf:

            v2 = "下跌分手"

        elif bar1.high >= left_max - 0.25 * gap and bar1.open == bar2.open and bar1.close > bar2.high \
                and bar2.close < bar2.open and (bar1.close - bar2.close) / bar2.close * 10000 > zdf:
            v2 = "上升分手"

    s = OrderedDict()
    signal = Signal(k1=k1, k2=k2, k3=k3, v1=v1, v2=v2)
    s[signal.key] = signal.value
    return s


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """择时策略"""
    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(jcc_fen_shou_xian_V20221113(cat.kas['60分钟'], di=1))
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
    "symbol": "300001.SZ#E",    # 交易品种，格式为 {ts_code}#{asset}
    "sdt": "20150101",          # 开始时间
    "edt": "20220101",          # 结束时间
}


