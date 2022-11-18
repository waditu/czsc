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
def jcc_xing_xian_v221118(c: CZSC, di=2, th=2) -> OrderedDict:
    """星形态

    **星形态，判断标准：**

    1.启明星：

        蜡烛线1。一根长长的黑色实体，形象地表明空头占据主宰地位
        蜡烛线2。一根小小的实体，并且它与前一根实体之间不相接触（这两条蜡烛线组成了基本的星线形态）。小实体意味着卖方丧失了驱动市场走低的能力
        蜡烛线3。一根白色实体，它明显地向上推进到了第一个时段的黑色实体之内，标志着启明星形态的完成。这表明多头已经夺回了主导权

        在理想的启明星形态中，第二根蜡烛线（即星线）的实体，与第三根蜡烛线的实体之间有价格跳空。根据我的经验，即使没有这个价格跳空，
        似乎也不会削减启明星形态的技术效力。其决定性因素是，第二根蜡烛线应为纺锤线，同时第三根蜡烛线应显著深入到第一根黑色蜡烛线内部

    2.黄昏星：

        a. 如果第一根与第二根蜡烛线，第二根与第三根蜡烛线的实体之间不存在重叠。
        b. 如果第三根蜡烛线的收市价向下深深扎入第一根蜡烛线的实体内部。
        c. 如果第一根蜡烛线的交易量较小，而第三根蜡烛线的交易量较大。这表明之前趋势的驱动力正在减弱，新趋势方向的驱动力正在加强

    3.十字黄昏星

        在常规的黄昏星形态中，第二根蜡烛线具有较小的实体，如果不是较小的实体，而是一个十字线，则称为十字黄昏星形态
    4.十字启明星

        在启明星形态中，如果其星线（即三根蜡烛线中的第二根蜡烛线）是一个十字线，则成为十字启明星形态

    **信号列表：**

    - Signal('60分钟_D1TH2_星形线_黄昏星_任意_任意_0')
    - Signal('60分钟_D1TH2_星形线_启明星_任意_任意_0')
    - Signal('60分钟_D1TH2_星形线_启明星_中间十字_任意_0')
    - Signal('60分钟_D1TH2_星形线_黄昏星_中间十字_任意_0')

    :param c: CZSC 对象
    :param di: 倒数第di跟K线
    :param th: 左侧实体是当前实体的多少倍
    :return: 星形线识别结果
    """
    assert di >= 1

    k1, k2, k3 = f"{c.freq.value}_D{di}TH{th}_星形线".split('_')

    bar3, bar2, bar1 = get_sub_elements(c.bars_raw, di=di, n=3)
    x3 = abs(bar3.close - bar3.open)
    x2 = abs(bar2.close - bar2.open)
    x1 = abs(bar1.close - bar1.open)

    v1 = "其他"
    if bar3.high > bar2.high < bar1.high and bar3.low > bar2.low < bar1.low:
        """
        方向向下，启明星
            - 蜡烛线3。一根长长的黑色实体，形象地表明空头占据主宰地位。
            - 蜡烛线2。一根小小的实体，并且它与前一根实体之间不相接触（这两条蜡烛线组成了基本的星线形态）。小实体意味着卖方丧失了驱动市场走低的能力。
            - 蜡烛线1。一根白色实体，它明显地向上推进到了第一个时段的黑色实体之内，标志着启明星形态的完成。这表明多头已经夺回了主导权
        """
        if bar3.close < bar3.open and x2 * th < x3 < x2 + x1 and bar1.close > bar1.open > max(bar2.close, bar2.open):
            v1 = "启明星"

    elif bar3.high < bar2.high > bar1.high and bar3.low < bar2.low > bar1.low:
        """
        方向向上，黄昏星。
            1. 如果第一根与第二根蜡烛线，第二根与第三根蜡烛线的实体之间不存在重叠。
            2. 如果第三根蜡烛线的收市价向下深深扎入第一根蜡烛线的实体内部。
            3. 如果第一根蜡烛线的交易量较小，而第三根蜡烛线的交易量较大。这表明之前趋势的驱动力正在减弱，新趋势方向的驱动力正在加强
        """
        if bar3.close > bar3.open and x2 * th < x3 < x2 + x1 and bar1.close < bar1.open < min(bar2.close, bar2.open):
            v1 = "黄昏星"

    v2 = "中间十字" if bar2.close == bar2.open else "任意"
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
        s.update(jcc_xing_xian_v221118(cat.kas['60分钟'], di=1))
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


