# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/31 16:03
describe: 
"""
import pandas as pd
from typing import List
from czsc.objects import Freq, RawBar
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
        "stock": stocks.ts_code.to_list(),
        "check": ['000001.SZ'],
        "train": stocks[:200],
        "valid": stocks[200:600],
        "etfs": ['512880.SH', '518880.SH', '515880.SH', '513050.SH', '512690.SH',
                 '512660.SH', '512400.SH', '512010.SH', '512000.SH', '510900.SH',
                 '510300.SH', '510500.SH', '510050.SH', '159992.SZ', '159985.SZ',
                 '159981.SZ', '159949.SZ', '159915.SZ'],
    }
    return stocks_map[step]


def test_local_kline():
    # 获取所有板块
    slt = xtdata.get_sector_list()
    stocks = xtdata.get_stock_list_in_sector('沪深A股')

    df = get_local_kline(symbol='000001.SZ', period='1m', count=1000, dividend_type='front',
                         data_dir=r"D:\迅投极速策略交易系统交易终端 华鑫证券QMT实盘\datadir",
                         start_time='20200427', end_time='20221231', update=True)
    assert not df.empty
    # df = get_local_kline(symbol='000001.SZ', period='5m', count=1000, dividend_type='front',
    #                      data_dir=r"D:\迅投极速策略交易系统交易终端 华鑫证券QMT实盘\datadir",
    #                      start_time='20200427', end_time='20221231', update=False)
    # df = get_local_kline(symbol='000001.SZ', period='1d', count=1000, dividend_type='front',
    #                      data_dir=r"D:\迅投极速策略交易系统交易终端 华鑫证券QMT实盘\datadir",
    #                      start_time='20200427', end_time='20221231', update=False)
