# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/21 19:56
describe: 择时交易策略样例
"""
from loguru import logger
from collections import OrderedDict
from czsc import signals
from czsc.traders import CzscAdvancedTrader
from czsc.objects import Freq, Operate, Signal, Factor, Event, RawBar, PositionLong, PositionShort

logger.disable('czsc.signals.cxt')

# QMT 数据相关函数
# ----------------------------------------------------------------------------------------------------------------------
import pandas as pd
from typing import List
from xtquant import xtdata


def format_stock_kline(kline: pd.DataFrame, freq: Freq) -> List[RawBar]:
    """QMT A股市场K线数据转换

    :param kline: QMT 数据接口返回的K线数据
                         time   open   high    low  close  volume      amount  \
        0 2022-12-01 10:15:00  13.22  13.22  13.16  13.18   20053  26432861.0
        1 2022-12-01 10:20:00  13.18  13.19  13.15  13.15   32667  43002512.0
        2 2022-12-01 10:25:00  13.16  13.18  13.13  13.16   32466  42708049.0
        3 2022-12-01 10:30:00  13.16  13.19  13.13  13.18   15606  20540461.0
        4 2022-12-01 10:35:00  13.20  13.25  13.19  13.22   29959  39626170.0
              symbol
        0  000001.SZ
        1  000001.SZ
        2  000001.SZ
        3  000001.SZ
        4  000001.SZ
    :param freq: K线周期
    :return: 转换好的K线数据
    """
    bars = []
    dt_key = 'time'
    kline = kline.sort_values(dt_key, ascending=True, ignore_index=True)
    records = kline.to_dict('records')

    for i, record in enumerate(records):
        # 将每一根K线转换成 RawBar 对象
        bar = RawBar(symbol=record['symbol'], dt=pd.to_datetime(record[dt_key]), id=i, freq=freq,
                     open=record['open'], close=record['close'], high=record['high'], low=record['low'],
                     vol=record['volume'] * 100 if record['volume'] else 0,  # 成交量，单位：股
                     amount=record['amount'] if record['amount'] > 0 else 0,  # 成交额，单位：元
                     )
        bars.append(bar)
    return bars


def get_local_kline(symbol, period, start_time, end_time, count=-1, dividend_type='none', data_dir=None, update=True):
    """获取 QMT 本地K线数据

    :param symbol: 股票代码 例如：'300001.SZ'
    :param period: 周期 分笔"tick" 分钟线"1m"/"5m" 日线"1d"
    :param start_time: 开始时间，格式YYYYMMDD/YYYYMMDDhhmmss/YYYYMMDDhhmmss.milli，
        例如："20200427" "20200427093000" "20200427093000.000"
    :param end_time: 结束时间 格式同上
    :param count: 数量 -1全部，n: 从结束时间向前数n个
    :param dividend_type: 除权类型"none" "front" "back" "front_ratio" "back_ratio"
    :param data_dir: 下载QMT本地数据路径，如 D:/迅投极速策略交易系统交易终端/datadir
    :param update: 更新QMT本地数据路径中的数据
    :return: df Dataframe格式的数据，样例如下
                         time   open   high    low  close  volume      amount  \
        0 2022-12-01 10:15:00  13.22  13.22  13.16  13.18   20053  26432861.0
        1 2022-12-01 10:20:00  13.18  13.19  13.15  13.15   32667  43002512.0
        2 2022-12-01 10:25:00  13.16  13.18  13.13  13.16   32466  42708049.0
        3 2022-12-01 10:30:00  13.16  13.19  13.13  13.18   15606  20540461.0
        4 2022-12-01 10:35:00  13.20  13.25  13.19  13.22   29959  39626170.0
              symbol
        0  000001.SZ
        1  000001.SZ
        2  000001.SZ
        3  000001.SZ
        4  000001.SZ
    """
    field_list = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
    if update:
        xtdata.download_history_data(symbol, period, start_time='20100101', end_time='21000101')
    local_data = xtdata.get_local_data(field_list, [symbol], period, count=count, dividend_type=dividend_type,
                                       start_time=start_time, end_time=end_time, data_dir=data_dir)

    df = pd.DataFrame({key: value.values[0] for key, value in local_data.items()})
    df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.to_timedelta('8H')
    df.reset_index(inplace=True, drop=True)
    df['symbol'] = symbol
    return df


def get_symbols(step):
    """获取择时策略投研不同阶段对应的标的列表

    :param step: 投研阶段
    :return: 标的列表
    """
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    stocks_map = {
        "index": ['000905.SH', '000016.SH', '000300.SH', '000001.SH', '000852.SH',
                  '399001.SZ', '399006.SZ', '399376.SZ', '399377.SZ', '399317.SZ', '399303.SZ'],
        "stock": stocks,
        "check": ['000001.SZ'],
        "train": stocks[:200],
        "valid": stocks[200:600],
        "etfs": ['512880.SH', '518880.SH', '515880.SH', '513050.SH', '512690.SH',
                 '512660.SH', '512400.SH', '512010.SH', '512000.SH', '510900.SH',
                 '510300.SH', '510500.SH', '510050.SH', '159992.SZ', '159985.SZ',
                 '159981.SZ', '159949.SZ', '159915.SZ'],
    }
    return stocks_map[step]


# 定义择时交易策略，策略函数名称必须是 trader_strategy
# ----------------------------------------------------------------------------------------------------------------------
def trader_strategy(symbol):
    """5日线"""

    def get_signals(cat: CzscAdvancedTrader) -> OrderedDict:
        s = OrderedDict({"symbol": cat.symbol, "dt": cat.end_dt, "close": cat.latest_price})
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='全天', span=('0935', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='临收盘', span=('1410', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='下午', span=('1300', '1450')))
        s.update(signals.bar_operate_span_V221111(cat.kas['15分钟'], k1='上午', span=('0935', '1130')))
        s.update(signals.bar_zdt_V221111(cat, '15分钟', di=1))
        s.update(signals.bar_mean_amount_V221112(cat.kas['日线'], di=2, n=20, th1=2, th2=1000))

        signals.update_ma_cache(cat.kas["日线"], ma_type='SMA', timeperiod=5)
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=1, key='SMA5'))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=2, key='SMA5'))
        s.update(signals.tas_ma_base_V221101(cat.kas["日线"], di=5, key='SMA5'))
        c = cat.kas['30分钟']
        s.update(signals.cxt_first_buy_V221126(c, di=1))
        return s

    # 定义多头持仓对象和交易事件
    long_pos = PositionLong(symbol, hold_long_a=1, hold_long_b=1, hold_long_c=1,
                            T0=False, long_min_interval=3600 * 4)
    long_events = [
        Event(name="开多", operate=Operate.LO,
              signals_not=[Signal('15分钟_D1K_涨跌停_涨停_任意_任意_0')],
              signals_all=[Signal("日线_D2K20B均额_2至1000千万_是_任意_任意_0")],
              factors=[
                  Factor(name="站上SMA5", signals_all=[
                      Signal("全天_0935_1450_是_任意_任意_0"),
                      Signal("日线_D1K_SMA5_多头_任意_任意_0"),
                      Signal("日线_D5K_SMA5_空头_向下_任意_0"),
                      Signal('30分钟_D1B_BUY1_一买_任意_任意_0'),
                  ]),
              ]),

        Event(name="平多", operate=Operate.LE,
              signals_not=[Signal('15分钟_D1K_涨跌停_跌停_任意_任意_0')],
              factors=[
                  Factor(name="跌破SMA5", signals_all=[
                      Signal("下午_1300_1450_是_任意_任意_0"),
                      Signal("日线_D1K_SMA5_空头_任意_任意_0"),
                      Signal("日线_D2K_SMA5_多头_任意_任意_0"),
                  ]),
              ]),
    ]

    tactic = {
        "base_freq": '5分钟',
        "freqs": ['15分钟', '30分钟', '日线'],
        "get_signals": get_signals,

        "long_pos": long_pos,
        "long_events": long_events,
    }

    return tactic


# 定义命令行接口的特定参数
# ----------------------------------------------------------------------------------------------------------------------
# 【必须】执行结果路径
results_path = r"D:\ts_data\SMA5"


# 【必须】策略回测参数设置
dummy_params = {
    "symbols": get_symbols('train'),  # 回测使用的标的列表
    "sdt": "20150101",  # K线数据开始时间
    "mdt": "20200101",  # 策略回测开始时间
    "edt": "20220101",  # 策略回测结束时间
}


# 【可选】策略回放参数设置
replay_params = {
    "symbol": get_symbols('check')[0],  # 回放交易品种
    "sdt": "20150101",  # K线数据开始时间
    "mdt": "20200101",  # 策略回放开始时间
    "edt": "20220101",  # 策略回放结束时间
}

# 【可选】是否使用 debug 模式输出更多信息
debug = True


# 【必须】定义K线数据读取函数，这里是为了方便接入任意数据源的K线行情
# ----------------------------------------------------------------------------------------------------------------------

def read_bars(symbol, sdt, edt):
    """自定义K线数据读取函数，便于接入任意来源的行情数据进行回测一类的分析

    :param symbol: 标的名称
    :param sdt: 行情开始时间
    :param edt: 行情介绍时间
    :return: list of RawBar
    """
    sdt = pd.to_datetime(sdt).strftime("%Y%m%d")
    edt = pd.to_datetime(edt).strftime("%Y%m%d")
    df = get_local_kline(symbol, period='5m', start_time=sdt, end_time=edt, dividend_type='back',
                         data_dir=r"D:\迅投极速策略交易系统交易终端 华鑫证券QMT实盘\datadir", update=True)
    bars = format_stock_kline(df, Freq.F5)
    return bars


