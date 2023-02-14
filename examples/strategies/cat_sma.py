# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/21 19:56
describe: 择时交易策略样例
"""
from loguru import logger
from czsc.data import TsDataCache, get_symbols
from czsc import signals
from collections import OrderedDict
from czsc.objects import Event, Position
from czsc.strategies import CzscStrategyBase


logger.disable('czsc.signals.cxt')


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
class CzscStrategySMA5(CzscStrategyBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @classmethod
    def get_signals(cls, cat) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='全天', span=('0935', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='临收盘', span=('1410', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='下午', span=('1300', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='上午', span=('0935', '1130')))
        s.update(signals.bar_zdt_V221111(cat, '15分钟', di=1))
        # s.update(signals.bar_end_V221111(cat.kas['5分钟'], '15分钟'))
        s.update(signals.bar_mean_amount_V221112(cat.kas['日线'], di=2, n=20, th1=2, th2=1000))

        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=1, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=2, ma_type='SMA', timeperiod=5))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=5, ma_type='SMA', timeperiod=5))

        s.update(signals.cxt_first_buy_V221126(cat.kas['30分钟'], di=1))
        return s

    @property
    def positions(self):
        return [
            self.create_pos_a(),
        ]

    @property
    def freqs(self):
        return ['日线', '30分钟', '15分钟']

    def create_pos_a(self):
        opens = [
            {'name': '开多',
             'operate': '开多',
             'signals_all': ['日线_D2K20B均额_2至1000千万_是_任意_任意_0'],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_涨跌停_涨停_任意_任意_0'],
             'factors': [
                 {'name': '站上SMA5',
                  'signals_all': ['全天_0935_1450_是_任意_任意_0',
                                  '日线_D1K_SMA5_多头_任意_任意_0',
                                  '日线_D5K_SMA5_空头_向下_任意_0',
                                  '30分钟_D1B_BUY1_一买_任意_任意_0'],
                  'signals_any': [],
                  'signals_not': []}
             ]},
            {'name': '开空',
             'operate': '开空',
             'signals_all': ['日线_D2K20B均额_2至1000千万_是_任意_任意_0'],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_涨跌停_跌停_任意_任意_0'],
             'factors': [
                 {'name': '站上SMA5',
                  'signals_all': ['全天_0935_1450_是_任意_任意_0',
                                  '日线_D1K_SMA5_空头_任意_任意_0',
                                  '日线_D5K_SMA5_多头_向下_任意_0',
                                  '30分钟_D1B_BUY1_一卖_任意_任意_0'],
                  'signals_any': [],
                  'signals_not': []}
             ]},
        ]

        exits = [
            {'name': '平多',
             'operate': '平多',
             'signals_all': [],
             'signals_any': [],
             'signals_not': ['15分钟_D1K_涨跌停_跌停_任意_任意_0'],
             'factors': [
                 {'name': '跌破SMA5',
                  'signals_all': ['下午_1300_1450_是_任意_任意_0',
                                  '日线_D1K_SMA5_空头_任意_任意_0',
                                  '日线_D2K_SMA5_多头_任意_任意_0'],
                  'signals_any': [],
                  'signals_not': []}
             ]}
        ]
        pos = Position(name="A", symbol=self.symbol,
                       opens=[Event.load(x) for x in opens],
                       exits=[Event.load(x) for x in exits],
                       interval=3600*4, timeout=100, stop_loss=1000, T0=False)
        return pos


# 定义命令行接口的特定参数
# ----------------------------------------------------------------------------------------------------------------------

# 【必须】执行结果路径
results_path = r"D:\ts_data\TS_SMA5"

# 初始化 Tushare 数据缓存
dc = TsDataCache(r"D:\ts_data")

# 【必须】策略回测参数设置
dummy_params = {
    "symbols": get_symbols(dc, 'train'),  # 回测使用的标的列表
    "sdt": "20150101",  # K线数据开始时间
    "mdt": "20200101",  # 策略回测开始时间
    "edt": "20220101",  # 策略回测结束时间
}


# 【可选】策略回放参数设置
replay_params = {
    "symbol": "000002.SZ#E",  # 回放交易品种
    "sdt": "20150101",  # K线数据开始时间
    "mdt": "20200101",  # 策略回放开始时间
    "edt": "20220101",  # 策略回放结束时间
}


# 【必须】定义K线数据读取函数，这里是为了方便接入任意数据源的K线行情
# ----------------------------------------------------------------------------------------------------------------------

def read_bars(symbol, sdt, edt):
    """自定义K线数据读取函数，便于接入任意来源的行情数据进行回测一类的分析

    :param symbol: 标的名称
    :param sdt: 行情开始时间
    :param edt: 行情介绍时间
    :return: list of RawBar
    """
    adj = 'hfq'
    freq = '15min'
    ts_code, asset = symbol.split("#")

    if "min" in freq:
        bars = dc.pro_bar_minutes(ts_code, sdt, edt, freq=freq, asset=asset, adj=adj, raw_bar=True)
    else:
        bars = dc.pro_bar(ts_code, sdt, edt, freq=freq, asset=asset, adj=adj, raw_bar=True)
    return bars


