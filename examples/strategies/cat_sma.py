# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/21 19:56
describe: 择时交易策略
"""
from collections import OrderedDict
from czsc import signals
from czsc.data import TsDataCache, get_symbols
from czsc.objects import Freq, Operate, Signal, Factor, Event
from czsc.traders import CzscAdvancedTrader
from czsc.objects import PositionLong, PositionShort, RawBar


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------

def trader_strategy(symbol):
    """择时策略"""
    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.pos.get_s_long01(cat, th=100))
        s.update(signals.pos.get_s_long02(cat, th=100))
        s.update(signals.pos.get_s_long05(cat, span='月', th=500))
        for _, c in cat.kas.items():
            if c.freq in [Freq.F15]:
                s.update(signals.bxt.get_s_d0_bi(c))
                s.update(signals.other.get_s_zdt(c, di=1))
                s.update(signals.other.get_s_op_time_span(c, op='开多', time_span=('13:00', '14:50')))
                s.update(signals.other.get_s_op_time_span(c, op='平多', time_span=('09:35', '14:50')))

            if c.freq in [Freq.F60, Freq.D, Freq.W]:
                s.update(signals.ta.get_s_macd(c, di=1))
        return s

    # 定义多头持仓对象和交易事件
    long_pos = PositionLong(symbol, hold_long_a=1, hold_long_b=1, hold_long_c=1,
                            T0=False, long_min_interval=3600*4)
    long_events = [
        Event(name="开多", operate=Operate.LO, factors=[
            Factor(name="低吸", signals_all=[
                Signal("开多时间范围_13:00_14:50_是_任意_任意_0"),
                Signal("15分钟_倒1K_ZDT_非涨跌停_任意_任意_0"),
                Signal("60分钟_倒1K_MACD多空_多头_任意_任意_0"),
                Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),
                Signal("15分钟_倒0笔_长度_5根K线以下_任意_任意_0"),
            ]),
        ]),

        Event(name="平多", operate=Operate.LE, factors=[
            Factor(name="持有资金", signals_all=[
                Signal("平多时间范围_09:35_14:50_是_任意_任意_0"),
                Signal("15分钟_倒1K_ZDT_非涨跌停_任意_任意_0"),
            ], signals_not=[
                Signal("15分钟_倒0笔_方向_向上_任意_任意_0"),
                Signal("60分钟_倒1K_MACD多空_多头_任意_任意_0"),
            ]),
        ]),
    ]

    tactic = {
        "base_freq": '15分钟',
        "freqs": ['60分钟', '日线'],
        "get_signals": get_signals,

        "long_pos": long_pos,
        "long_events": long_events,

        # 空头策略不进行定义，也就是不做空头交易
        "short_pos": None,
        "short_events": None,
    }

    return tactic


# 定义命令行接口的特定参数
# ----------------------------------------------------------------------------------------------------------------------

# 初始化 Tushare 数据缓存
dc = TsDataCache(r"C:\ts_data_czsc")

# 定义回测使用的标的列表
symbols = get_symbols(dc, 'train')[:3]

# 执行结果路径
results_path = r"C:\ts_data_czsc\cat_sma"

# 策略回放参数设置【可选】
replay_params = {
    "symbol": "000001.SZ#E",    # 回放交易品种
    "sdt": "20150101",          # K线数据开始时间
    "mdt": "20180101",          # 策略回放开始时间
    "edt": "20220101",          # 策略回放结束时间
}


