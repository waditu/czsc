# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/6/24 18:49
describe: Tushare数据源
"""
import os
import czsc
import pandas as pd
from czsc import Freq, RawBar
from typing import List

# 首次使用需要打开一个python终端按如下方式设置 token
# czsc.set_url_token(token='your token', url='http://api.tushare.pro')

cache_path = os.getenv("TS_CACHE_PATH", os.path.expanduser("~/.ts_data_cache"))
dc = czsc.DataClient(url='http://api.tushare.pro', cache_path=cache_path)


def format_kline(kline: pd.DataFrame, freq: Freq) -> List[RawBar]:
    """Tushare K线数据转换

    :param kline: Tushare 数据接口返回的K线数据
    :param freq: K线周期
    :return: 转换好的K线数据
    """
    bars = []
    dt_key = 'trade_time' if '分钟' in freq.value else 'trade_date'
    kline = kline.sort_values(dt_key, ascending=True, ignore_index=True)
    records = kline.to_dict('records')

    for i, record in enumerate(records):
        if freq == Freq.D:
            vol = int(record['vol'] * 100) if record['vol'] > 0 else 0
            amount = int(record.get('amount', 0) * 1000)
        else:
            vol = int(record['vol']) if record['vol'] > 0 else 0
            amount = int(record.get('amount', 0))

        # 将每一根K线转换成 RawBar 对象
        bar = RawBar(symbol=record['ts_code'], dt=pd.to_datetime(record[dt_key]),
                     id=i, freq=freq, open=record['open'], close=record['close'],
                     high=record['high'], low=record['low'],
                     vol=vol,          # 成交量，单位：股
                     amount=amount,    # 成交额，单位：元
                     )
        bars.append(bar)
    return bars


def get_symbols(step="all"):
    """获取标的代码"""
    stocks = dc.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
    stocks_ = stocks[stocks['list_date'] < '2010-01-01'].ts_code.to_list()
    stocks_map = {
        "index": ['000905.SH', '000016.SH', '000300.SH', '000001.SH', '000852.SH',
                  '399001.SZ', '399006.SZ', '399376.SZ', '399377.SZ', '399317.SZ', '399303.SZ'],
        "stock": stocks.ts_code.to_list(),
        "check": ['000001.SZ'],
        "train": stocks_[:200],
        "valid": stocks_[200:600],
        "etfs": ['512880.SH', '518880.SH', '515880.SH', '513050.SH', '512690.SH',
                 '512660.SH', '512400.SH', '512010.SH', '512000.SH', '510900.SH',
                 '510300.SH', '510500.SH', '510050.SH', '159992.SZ', '159985.SZ',
                 '159981.SZ', '159949.SZ', '159915.SZ'],
    }

    asset_map = {
        "index": "I",
        "stock": "E",
        "check": "E",
        "train": "E",
        "valid": "E",
        "etfs": "FD"
    }

    if step.lower() == "all":
        symbols = []
        for k, v in stocks_map.items():
            symbols += [f"{ts_code}#{asset_map[k]}" for ts_code in v]
    else:
        asset = asset_map[step]
        symbols = [f"{ts_code}#{asset}" for ts_code in stocks_map[step]]

    return symbols


def get_raw_bars(symbol, freq, sdt, edt, fq='后复权', raw_bar=True):
    """读取本地数据"""
    from czsc import data
    tdc = data.TsDataCache(data_path=cache_path)
    ts_code, asset = symbol.split("#")
    freq = str(freq)
    adj = "qfq" if fq == "前复权" else "hfq"

    if "分钟" in freq:
        freq = freq.replace("分钟", "min")
        bars = tdc.pro_bar_minutes(ts_code, sdt=sdt, edt=edt, freq=freq, asset=asset, adj=adj, raw_bar=raw_bar)

    else:
        _map = {"日线": "D", "周线": "W", "月线": "M"}
        freq = _map[freq]
        bars = tdc.pro_bar(ts_code, start_date=sdt, end_date=edt, freq=freq, asset=asset, adj=adj, raw_bar=raw_bar)
    return bars
