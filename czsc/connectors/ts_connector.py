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
from tqdm import tqdm
from loguru import logger

# 首次使用需要打开一个python终端按如下方式设置 token
# czsc.set_url_token(token='your token', url='http://api.tushare.pro')

cache_path = os.getenv("TS_CACHE_PATH", os.path.expanduser("~/.ts_data_cache"))
dc = czsc.DataClient(url="http://api.tushare.pro", cache_path=cache_path)


def format_kline(kline: pd.DataFrame, freq: Freq) -> List[RawBar]:
    """Tushare K线数据转换

    :param kline: Tushare 数据接口返回的K线数据
    :param freq: K线周期
    :return: 转换好的K线数据
    """
    bars = []
    dt_key = "trade_time" if "分钟" in freq.value else "trade_date"
    kline = kline.sort_values(dt_key, ascending=True, ignore_index=True)
    records = kline.to_dict("records")

    for i, record in enumerate(records):
        if freq == Freq.D:
            vol = int(record["vol"] * 100) if record["vol"] > 0 else 0
            amount = int(record.get("amount", 0) * 1000)
        else:
            vol = int(record["vol"]) if record["vol"] > 0 else 0
            amount = int(record.get("amount", 0))

        # 将每一根K线转换成 RawBar 对象
        bar = RawBar(
            symbol=record["ts_code"],
            dt=pd.to_datetime(record[dt_key]),
            id=i,
            freq=freq,
            open=record["open"],
            close=record["close"],
            high=record["high"],
            low=record["low"],
            vol=vol,  # 成交量，单位：股
            amount=amount,  # 成交额，单位：元
        )
        bars.append(bar)
    return bars


def get_sw_members(level="L1"):
    """获取申万行业分类成分股"""
    # https://tushare.pro/document/2?doc_id=181 申万行业分类
    sw = dc.index_classify(level=level, src="SW2021")
    rows = []
    for _index in sw.to_dict(orient="records"):
        # https://tushare.pro/document/2?doc_id=182 申万行业成分股
        dfp = dc.index_member(index_code=_index["index_code"])
        dfp["industry_name"] = _index["industry_name"]
        dfp = dfp[dfp["is_new"] == "Y"]
        rows.append(dfp)
    df = pd.concat(rows, ignore_index=True)
    return df


def get_daily_basic(sdt="20100101", edt="20240101"):
    """获取全市场A股的每日指标数据

    https://s0cqcxuy3p.feishu.cn/wiki/W5UYwk0qwiHWlxk2ngDcjxQKncg
    """
    sdt = pd.to_datetime(sdt)
    edt = pd.to_datetime(edt)

    dates = czsc.get_trading_dates(sdt, edt)
    rows = []
    for date in tqdm(dates, desc="获取全市场A股的每日指标"):
        try:
            date = pd.to_datetime(date).strftime("%Y%m%d")
            df = dc.daily_basic(trade_date=date)
            rows.append(df)
        except Exception as e:
            logger.error(f"{date} {e}")
    dfb = pd.concat(rows, ignore_index=True)
    return dfb


def moneyflow_hsgt(start_date, end_date):
    """获取沪深港通资金流向数据

    https://tushare.pro/document/2?doc_id=47

    :param start_date: str, 开始日期, 格式为 "YYYYMMDD"
    :param end_date: str, 结束日期, 格式为 "YYYYMMDD"
    :return: DataFrame, 包含沪深港通资金流向数据
    """
    sdt = pd.to_datetime(start_date)
    edt = pd.to_datetime(end_date)
    dts = pd.date_range(sdt, edt, freq="YE").to_list() + [sdt, edt]
    dts = sorted(list(set(dts)))

    rows = []
    for dt1, dt2 in zip(dts[:-1], dts[1:]):
        ttl = -1 if dt2 != edt else 0
        df1 = dc.moneyflow_hsgt(
            start_date=dt1.strftime("%Y%m%d"),
            end_date=dt2.strftime("%Y%m%d"),
            fields="trade_date, ggt_ss, ggt_sz, hgt, sgt, north_money, south_money",
            ttl=ttl,
        )
        df1 = df1.fillna(0)
        if not df1.empty:
            rows.append(df1)

    df = pd.concat(rows, axis=0, ignore_index=True)
    df["dt"] = pd.to_datetime(df["trade_date"])
    df.sort_values("dt", inplace=True)
    df.drop_duplicates(subset=["dt"], keep="last", inplace=True)
    df = df.drop(["trade_date"], axis=1).reset_index(drop=True)
    df.fillna(0, inplace=True)
    return df


def pro_bar_minutes(ts_code, sdt, edt, freq="60min", asset="E", adj=None):
    """获取分钟线

    https://tushare.pro/document/2?doc_id=109

    :param ts_code: 标的代码
    :param sdt: 开始时间，精确到分钟
    :param edt: 结束时间，精确到分钟
    :param freq: 分钟周期，可选值 1min, 5min, 15min, 30min, 60min
    :param asset: 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权 CB可转债（v1.2.39），默认E
    :param adj: 复权类型，None不复权，qfq:前复权，hfq:后复权
    :param raw_bar: 是否返回 RawBar 对象列表
    :return:
    """
    import tushare as ts
    from datetime import timedelta
    pro = dc

    dt_fmt = "%Y%m%d"

    sdt = pd.to_datetime(sdt).strftime(dt_fmt)
    edt = pd.to_datetime(edt).strftime(dt_fmt)

    klines = []
    end_dt = pd.to_datetime(edt)
    dt1 = pd.to_datetime(sdt)
    delta = timedelta(days=20 * int(freq.replace("min", "")))
    dt2 = dt1 + delta
    while dt1 < end_dt:
        df = ts.pro_bar(
            ts_code=ts_code,
            asset=asset,
            freq=freq,
            start_date=dt1.strftime(dt_fmt),
            end_date=dt2.strftime(dt_fmt),
        )
        klines.append(df)
        dt1 = dt2
        dt2 = dt1 + delta
        print(f"pro_bar_minutes: {ts_code} - {asset} - {freq} - {dt1} - {dt2} - {len(df)}")

    df_klines = pd.concat(klines, ignore_index=True)
    kline = df_klines.drop_duplicates("trade_time").sort_values("trade_time", ascending=True, ignore_index=True)
    kline["trade_time"] = pd.to_datetime(kline["trade_time"], format=dt_fmt)
    kline["dt"] = kline["trade_time"]
    float_cols = ["open", "close", "high", "low", "vol", "amount"]
    kline[float_cols] = kline[float_cols].astype("float32")
    kline["avg_price"] = kline["amount"] / kline["vol"]

    # 删除9:30的K线
    kline["keep"] = kline["trade_time"].apply(lambda x: 0 if x.hour == 9 and x.minute == 30 else 1)
    kline = kline[kline["keep"] == 1]
    
    # 删除没有成交量的K线
    kline = kline[kline["vol"] > 0]
    kline.drop(["keep"], axis=1, inplace=True)

    start_date = pd.to_datetime(sdt)
    end_date = pd.to_datetime(edt)
    kline = kline[(kline["trade_time"] >= start_date) & (kline["trade_time"] <= end_date)]
    kline = kline.reset_index(drop=True)
    kline["trade_date"] = kline.trade_time.apply(lambda x: x.strftime(dt_fmt))

    if asset == "E":
        # https://tushare.pro/document/2?doc_id=28
        factor = pro.adj_factor(ts_code=ts_code, start_date=sdt, end_date=edt)
    elif asset == "FD":
        # https://tushare.pro/document/2?doc_id=199
        factor = pro.fund_adj(ts_code=ts_code, start_date=sdt, end_date=edt)
    else:
        factor = pd.DataFrame()

    if len(factor) > 0:
        # 处理复权因子缺失的情况：前值填充
        df1 = pd.DataFrame({"trade_date": kline["trade_date"].unique().tolist()})
        factor = df1.merge(factor, on=["trade_date"], how="left").ffill().bfill()
        factor = factor.sort_values("trade_date", ignore_index=True)

    print(f"pro_bar_minutes: {ts_code} - {asset} - 复权因子长度 = {len(factor)}")

    # 复权行情说明：https://tushare.pro/document/2?doc_id=146
    if len(factor) > 0 and adj and adj == "qfq":
        # 前复权	= 当日收盘价 × 当日复权因子 / 最新复权因子
        latest_factor = factor.iloc[-1]["adj_factor"]
        adj_map = {row["trade_date"]: row["adj_factor"] for _, row in factor.iterrows()}
        for col in ["open", "close", "high", "low"]:
            kline[col] = kline.apply(lambda x: x[col] * adj_map[x["trade_date"]] / latest_factor, axis=1)

    if len(factor) > 0 and adj and adj == "hfq":
        # 后复权	= 当日收盘价 × 当日复权因子
        adj_map = {row["trade_date"]: row["adj_factor"] for _, row in factor.iterrows()}
        for col in ["open", "close", "high", "low"]:
            kline[col] = kline.apply(lambda x: x[col] * adj_map[x["trade_date"]], axis=1)   

    if sdt:
        kline = kline[kline["trade_time"] >= pd.to_datetime(sdt)]
    if edt:
        kline = kline[kline["trade_time"] <= pd.to_datetime(edt)]

    kline = kline.reset_index(drop=True)
    return kline


def get_symbols(step="all"):
    """获取标的代码"""
    stocks = dc.stock_basic(exchange="", list_status="L", fields="ts_code,symbol,name,area,industry,list_date")
    stocks_ = stocks[stocks["list_date"] < "2010-01-01"].ts_code.to_list()
    stocks_map = {
        "index": [
            "000905.SH",
            "000016.SH",
            "000300.SH",
            "000001.SH",
            "000852.SH",
            "399001.SZ",
            "399006.SZ",
            "399376.SZ",
            "399377.SZ",
            "399317.SZ",
            "399303.SZ",
        ],
        "stock": stocks.ts_code.to_list(),
        "check": ["000001.SZ"],
        "train": stocks_[:200],
        "valid": stocks_[200:600],
        "etfs": [
            "512880.SH",
            "518880.SH",
            "515880.SH",
            "513050.SH",
            "512690.SH",
            "512660.SH",
            "512400.SH",
            "512010.SH",
            "512000.SH",
            "510900.SH",
            "510300.SH",
            "510500.SH",
            "510050.SH",
            "159992.SZ",
            "159985.SZ",
            "159981.SZ",
            "159949.SZ",
            "159915.SZ",
        ],
    }

    asset_map = {"index": "I", "stock": "E", "check": "E", "train": "E", "valid": "E", "etfs": "FD"}

    if step.lower() == "all":
        symbols = []
        for k, v in stocks_map.items():
            symbols += [f"{ts_code}#{asset_map[k]}" for ts_code in v]
    else:
        asset = asset_map[step]
        symbols = [f"{ts_code}#{asset}" for ts_code in stocks_map[step]]

    return symbols


def get_raw_bars(symbol, freq, sdt, edt, fq="后复权", raw_bar=True):
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
