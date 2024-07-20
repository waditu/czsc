# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/11/15 20:45
describe: CZSC开源协作团队内部使用数据接口

接口说明：https://s0cqcxuy3p.feishu.cn/wiki/StQbwOrWdiJPpikET9EcrRVEnrd
"""
import os
import czsc
import requests
import loguru
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from czsc import RawBar, Freq

# 首次使用需要打开一个python终端按如下方式设置 token或者在环境变量中设置 CZSC_TOKEN
# czsc.set_url_token(token='your token', url='http://zbczsc.com:9106')

cache_path = os.getenv("CZSC_CACHE_PATH", os.path.expanduser("~/.quant_data_cache"))
dc = czsc.DataClient(token=os.getenv("CZSC_TOKEN"), url="http://zbczsc.com:9106", cache_path=cache_path)


def get_groups():
    """获取投研共享数据的分组信息

    :return: 分组信息
    """
    return ["A股指数", "ETF", "股票", "期货主力", "南华指数"]


def get_symbols(name, **kwargs):
    """获取指定分组下的所有标的代码

    :param name: 分组名称，可选值：'A股指数', 'ETF', '股票', '期货主力', '南华指数'
    :param kwargs:
    :return:
    """
    if name == "股票":
        df = dc.stock_basic(nobj=1, status=1, ttl=3600 * 6)
        symbols = [f"{row['code']}#STOCK" for _, row in df.iterrows()]
        return symbols

    if name == "ETF":
        df = dc.etf_basic(v=2, fields="code,name", ttl=3600 * 6)
        dfk = dc.pro_bar(trade_date="2024-04-02", asset="e", v=2)
        df = df[df["code"].isin(dfk["code"])].reset_index(drop=True)
        symbols = [f"{row['code']}#ETF" for _, row in df.iterrows()]
        return symbols

    if name == "A股指数":
        # 指数 https://s0cqcxuy3p.feishu.cn/wiki/KuSAweAAhicvsGk9VPTc1ZWKnAd
        df = dc.index_basic(v=2, market="SSE,SZSE", ttl=3600 * 6)
        symbols = [f"{row['code']}#INDEX" for _, row in df.iterrows()]
        return symbols

    if name == "南华指数":
        df = dc.index_basic(v=2, market="NH", ttl=3600 * 6)
        symbols = [row["code"] for _, row in df.iterrows()]
        return symbols

    if name == "期货主力":
        kline = dc.future_klines(trade_date="20240402", ttl=3600 * 6)
        return kline["code"].unique().tolist()

    if name.upper() == "ALL":
        symbols = get_symbols("股票") + get_symbols("ETF")
        symbols += get_symbols("A股指数") + get_symbols("南华指数") + get_symbols("期货主力")
        return symbols

    raise ValueError(f"{name} 分组无法识别，获取标的列表失败！")


def get_min_future_klines(code, sdt, edt, freq="1m", **kwargs):
    """分段获取期货1分钟K线后合并"""
    logger = kwargs.pop("logger", loguru.logger)

    sdt = pd.to_datetime(sdt).strftime("%Y%m%d")
    edt = pd.to_datetime(edt).strftime("%Y%m%d")
    # dates = pd.date_range(start=sdt, end=edt, freq='1M')
    dates = pd.date_range(start="20000101", end="20300101", freq="365D")

    dates = [d.strftime("%Y%m%d") for d in dates]
    dates = sorted(list(set(dates)))

    rows = []
    for sdt_, edt_ in tqdm(zip(dates[:-1], dates[1:]), total=len(dates) - 1):
        if edt_ < sdt:
            continue

        if pd.to_datetime(sdt_).date() >= datetime.now().date():
            break

        ttl = kwargs.get("ttl", 60 * 60) if pd.to_datetime(edt_).date() >= datetime.now().date() else -1
        df = dc.future_klines(code=code, sdt=sdt_, edt=edt_, freq=freq, ttl=ttl)
        if df.empty:
            continue
        logger.info(f"{code}获取K线范围：{df['dt'].min()} - {df['dt'].max()}")
        rows.append(df)

    df = pd.concat(rows, ignore_index=True)
    df.rename(columns={"code": "symbol"}, inplace=True)
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.drop_duplicates(subset=["dt", "symbol"], keep="last")

    if code in ["SFIC9001", "SFIF9001", "SFIH9001"]:
        # 股指：仅保留 09:31 - 11:30, 13:01 - 15:00
        dt1 = datetime.strptime("09:31:00", "%H:%M:%S")
        dt2 = datetime.strptime("11:30:00", "%H:%M:%S")
        c1 = (df["dt"].dt.time >= dt1.time()) & (df["dt"].dt.time <= dt2.time())

        dt3 = datetime.strptime("13:01:00", "%H:%M:%S")
        dt4 = datetime.strptime("15:00:00", "%H:%M:%S")
        c2 = (df["dt"].dt.time >= dt3.time()) & (df["dt"].dt.time <= dt4.time())

        df = df[c1 | c2].copy().reset_index(drop=True)

    df = df[(df["dt"] >= pd.to_datetime(sdt)) & (df["dt"] <= pd.to_datetime(edt))].copy().reset_index(drop=True)
    return df


def get_raw_bars(symbol, freq, sdt, edt, fq="前复权", **kwargs):
    """获取 CZSC 库定义的标准 RawBar 对象列表

    :param symbol: 标的代码
    :param freq: 周期，支持 Freq 对象，或者字符串，如
            '1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线'
    :param sdt: 开始时间
    :param edt: 结束时间
    :param fq: 除权类型，可选值：'前复权', '后复权', '不复权'
    :param kwargs:
    :return: RawBar 对象列表 or DataFrame

    >>> from czsc.connectors import cooperation as coo
    >>> df = coo.get_raw_bars(symbol="000001.SH#INDEX", freq="日线", sdt="2001-01-01", edt="2021-12-31", fq='后复权', raw_bars=False)
    """
    logger = kwargs.pop("logger", loguru.logger)

    freq = czsc.Freq(freq)
    raw_bars = kwargs.get("raw_bars", True)
    ttl = kwargs.get("ttl", -1)
    sdt = pd.to_datetime(sdt).strftime("%Y%m%d")
    edt = pd.to_datetime(edt).strftime("%Y%m%d")

    if "SH" in symbol or "SZ" in symbol:
        fq_map = {"前复权": "qfq", "后复权": "hfq", "不复权": None}
        adj = fq_map.get(fq, None)

        code, asset = symbol.split("#")

        if freq.value.endswith("分钟"):
            df = dc.pro_bar(code=code, sdt=sdt, edt=edt, freq="min", adj=adj, asset=asset[0].lower(), v=2, ttl=ttl)
            df = df[~df["dt"].str.endswith("09:30:00")].reset_index(drop=True)
            df.rename(columns={"code": "symbol"}, inplace=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars, base_freq="1分钟")

        else:
            df = dc.pro_bar(code=code, sdt=sdt, edt=edt, freq="day", adj=adj, asset=asset[0].lower(), v=2, ttl=ttl)
            df.rename(columns={"code": "symbol"}, inplace=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars)

    if symbol.endswith("9001"):
        # https://s0cqcxuy3p.feishu.cn/wiki/WLGQwJLWQiWPCZkPV7Xc3L1engg
        if fq == "前复权":
            logger.warning("期货主力合约暂时不支持前复权，已自动切换为后复权")

        freq_rd = "1m" if freq.value.endswith("分钟") else "1d"
        if freq.value.endswith("分钟"):
            df = get_min_future_klines(code=symbol, sdt=sdt, edt=edt, freq="1m", ttl=ttl)
            if df.empty:
                return df

            if "amount" not in df.columns:
                df["amount"] = df["vol"] * df["close"]

            df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]].copy().reset_index(drop=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars, base_freq="1分钟")

        else:
            df = dc.future_klines(code=symbol, sdt=sdt, edt=edt, freq=freq_rd, ttl=ttl)
            if df.empty:
                return df

            df.rename(columns={"code": "symbol"}, inplace=True)
            if "amount" not in df.columns:
                df["amount"] = df["vol"] * df["close"]

            df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]].copy().reset_index(drop=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars)

    if symbol.endswith(".NH"):
        if freq != Freq.D:
            raise ValueError("南华指数只支持日线数据")
        df = dc.nh_daily(code=symbol, sdt=sdt, edt=edt, ttl=ttl, v=2)
        df.rename(columns={"code": "symbol", "volume": "vol"}, inplace=True)
        df["dt"] = pd.to_datetime(df["dt"])
        return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars)

    raise ValueError(f"symbol {symbol} 无法识别，获取数据失败！")


@czsc.disk_cache(path=cache_path, ttl=-1)
def stocks_daily_klines(sdt="20170101", edt="20240101", **kwargs):
    """获取全市场A股的日线数据"""
    adj = kwargs.get("adj", "hfq")
    sdt = pd.to_datetime(sdt).year
    edt = pd.to_datetime(edt).year
    years = [str(year) for year in range(sdt, edt + 1)]

    res = []
    for year in years:
        ttl = 3600 * 6 if year == str(datetime.now().year) else -1
        kline = dc.pro_bar(trade_year=year, adj=adj, v=2, ttl=ttl)
        res.append(kline)

    dfk = pd.concat(res, ignore_index=True)
    dfk["dt"] = pd.to_datetime(dfk["dt"])
    dfk = dfk.sort_values(["code", "dt"], ascending=True).reset_index(drop=True)
    if kwargs.get("exclude_bj", True):
        dfk = dfk[~dfk["code"].str.endswith(".BJ")].reset_index(drop=True)

    dfk = dfk.rename(columns={"code": "symbol"})
    dfk["price"] = dfk["close"]
    nxb = kwargs.get("nxb", [1, 2, 5, 10, 20, 30, 60])
    if nxb:
        dfk = czsc.update_nxb(dfk, nseq=nxb)
    return dfk


def upload_strategy(df, meta, token=None, **kwargs):
    """上传策略数据

    :param df: pd.DataFrame, 策略持仓权重数据，至少包含 dt, symbol, weight 三列, 例如：

        ===================  ========  ========
        dt                   symbol      weight
        ===================  ========  ========
        2017-01-03 09:01:00  ZZSF9001  0
        2017-01-03 09:01:00  DLj9001   0
        2017-01-03 09:01:00  SQag9001  0
        2017-01-03 09:06:00  ZZSF9001  0.136364
        2017-01-03 09:06:00  SQag9001  1
        ===================  ========  ========

    :param meta: dict, 策略元数据

        至少包含 name, description, base_freq, author, outsample_sdt 字段, 例如：

        {'name': 'TS001_3',
        'description': '测试策略：仅用于读写redis测试',
        'base_freq': '1分钟',
        'author': 'ZB',
        'outsample_sdt': '20220101'}

    :param token: str, 上传凭证码；如果不提供，将从环境变量 CZSC_TOKEN 中获取
    :param kwargs: dict, 其他参数

            - logger: loguru.logger, 日志记录器
    :return dict
    """
    logger = kwargs.pop("logger", loguru.logger)
    df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    logger.info(f"输入数据中有 {len(df)} 条权重信号")

    # 去除单个品种下相邻时间权重相同的数据
    _res = []
    for _, dfg in df.groupby("symbol"):
        dfg = dfg.sort_values("dt", ascending=True).reset_index(drop=True)
        dfg = dfg[dfg["weight"].diff().fillna(1) != 0].copy()
        _res.append(dfg)
    df = pd.concat(_res, ignore_index=True)
    df = df.sort_values(["dt"]).reset_index(drop=True)
    df["dt"] = df["dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"去除单个品种下相邻时间权重相同的数据后，剩余 {len(df)} 条权重信号")

    data = {
        "weights": df[["dt", "symbol", "weight"]].to_json(orient="split"),
        "token": token or os.getenv("CZSC_TOKEN"),
        "strategy_name": meta.get("name"),
        "meta": meta,
    }
    response = requests.post("http://zbczsc.com:9106/upload_strategy", json=data)

    logger.info(f"上传策略接口返回: {response.json()}")
    return response.json()
