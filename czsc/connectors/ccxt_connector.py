import os
import time
from pathlib import Path
import czsc
import ccxt
import pandas as pd
import loguru
from tenacity import retry, stop_after_attempt, wait_fixed


def __get_exchange(exchange="币安期货"):
    """获取交易所连接"""
    if exchange == "币安期货":
        e = ccxt.binanceusdm()
    elif exchange == "币安现货":
        e = ccxt.binance()
    else:
        raise ValueError(f"不支持的交易类型: {exchange}")

    use_proxy = os.getenv("USE_PROXY", "0") == "1"
    proxies = {
        "http": os.getenv("HTTP_PROXY", "http://127.0.0.1:10808"),
        "https": os.getenv("HTTPS_PROXY", "http://127.0.0.1:10808"),
    }
    if use_proxy:
        # v2rayN的http代理设置样例
        # proxies = {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
        e.proxies = proxies
    return e


def get_symbols(exchange="币安期货", **kwargs):
    """获取交易品种列表

    df = get_symbols(kind="币安期货")
    df = get_symbols(kind="币安现货")
    """
    exchange = __get_exchange(exchange=exchange)

    markets = exchange.load_markets()
    df = pd.DataFrame(
        [
            {
                "ccxt_symbol": symbol,
                "base": market["base"],
                "quote": market["quote"],
                "price_size": market["precision"]["price"],
            }
            for symbol, market in markets.items()
        ]
    )
    df["symbol"] = df["base"] + df["quote"]
    return df


@czsc.disk_cache(ttl=-1)
def __binance_fetch_ohlcv_once(exchange, symbol, since, interval, logger=loguru.logger):
    """获取币安交易所的K线数据"""
    all_klines = []
    params = {
        "symbol": symbol.replace("/", ""),  # 转换为币安格式
        "interval": interval,
        "startTime": since,
        "limit": 1000,
    }
    if exchange.name == "Binance USDⓈ-M":
        raw_klines = exchange.fapiPublicGetKlines(params)
        logger.info(f"{exchange.name} - 获取 {params} K线数据量为 {len(raw_klines)}")
    elif exchange.name == "Binance":
        raw_klines = exchange.publicGetKlines(params)
        logger.info(f"{exchange.name} - 获取 {params} K线数据量为 {len(raw_klines)}")
    else:
        raise ValueError(f"不支持的交易所: {exchange.name}")

    if not raw_klines:
        logger.warning(f"获取 {params} K线数据量为 0 ")
        return [], since

    # 转换数据结构
    for kline in raw_klines:
        processed_kline = {
            "start_time": int(kline[0]),  # timestamp
            "open": float(kline[1]),  # open
            "high": float(kline[2]),  # high
            "low": float(kline[3]),  # low
            "close": float(kline[4]),  # close
            "vol": float(kline[5]),  # volume (base)
            "dt": int(kline[6]) + 1,  # close time
            "amount": float(kline[7]),  # quote volume
            "trades": int(kline[8]),  # number of trades
            "taker_buy_volume": float(kline[9]),  # taker buy base volume
            "taker_buy_quote_volume": float(kline[10]),  # taker buy quote volume
        }
        all_klines.append(processed_kline)

    logger.info(f"获取 {params} K线数据量为 {len(all_klines)}")
    since = int(raw_klines[-1][0]) + 1
    return all_klines, since


# @retry(stop=stop_after_attempt(3), wait=wait_fixed(3))
def __binance_fetch_ohlcv(exchange, symbol, sdt, edt, interval):
    """获取币安交易所的K线数据"""
    # 转换时间戳
    since = int(pd.to_datetime(sdt).timestamp() * 1000)
    until = int(pd.to_datetime(edt).timestamp() * 1000)

    all_klines = []
    while since < until:
        _klines, _since = __binance_fetch_ohlcv_once(exchange, symbol, since, interval)
        if not _klines:
            break
        all_klines.extend(_klines)
        since = _since
        time.sleep(exchange.rateLimit / 1000)

    if not all_klines:
        return pd.DataFrame()

    df = pd.DataFrame(all_klines)
    # dt 是K线结束时间；时区转换：UTC -> Asia/Shanghai
    df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(hours=8)
    df = df[["dt", "open", "high", "low", "close", "vol", "amount"]]
    return df


def __exchange_fetch_ohlcv(exchange, symbol, sdt, edt, interval):
    """获取交易所的K线数据"""
    # 转换时间戳
    since = int(pd.to_datetime(sdt).timestamp() * 1000)
    until = int(pd.to_datetime(edt).timestamp() * 1000)

    all_klines = []
    while since < until:
        klines = exchange.fetch_ohlcv(symbol=symbol, timeframe=interval, since=since, limit=1000)
        if not klines:
            break

        all_klines.extend(klines)
        since = klines[-1][0] + 1  # 更新获取时间

        # 添加延时避免超过API限制
        time.sleep(0.5)

    if not all_klines:
        return pd.DataFrame()

    df = pd.DataFrame(all_klines, columns=["dt", "open", "high", "low", "close", "vol"])
    df["amount"] = df["vol"] * df["close"]

    # dt 转成K线结束时间
    if interval == "4h":
        df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(hours=4)

    elif interval == "2h":
        df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(hours=2)

    elif interval == "1h":
        df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(hours=1)

    elif interval == "30m":
        df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(minutes=30)

    elif interval == "15m":
        df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(minutes=15)

    elif interval == "5m":
        df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(minutes=5)

    elif interval == "1m":
        df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(minutes=1)

    # dt 是K线结束时间；时区转换：UTC -> Asia/Shanghai
    df["dt"] = pd.to_datetime(df["dt"], unit="ms") + pd.Timedelta(hours=8)
    return df


def get_raw_bars(symbol="BTCUSDT", period="4h", sdt="20240101", edt="20240308", **kwargs):
    """获取指定交易对的K线数据

    Args:
        symbol: 交易对，如 "BTCUSDT"
        period: 时间周期，支持 1m/5m/15m/1h/2h/4h/6h/8h/12h/1d
        sdt: 开始时间
        edt: 结束时间

    Returns:
        pandas.DataFrame: 包含K线数据的DataFrame
    """
    logger = kwargs.get("logger", loguru.logger)
    exchange = kwargs.get("exchange", "币安期货")
    e = __get_exchange(exchange=exchange)

    # 转换时间格式
    timeframes = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "6h": "6h",
        "8h": "8h",
        "12h": "12h",
        "1d": "1d",
    }
    if period not in timeframes:
        raise ValueError(f"不支持的时间周期: {period}")

    if exchange in ["币安期货", "币安现货"]:
        df = __binance_fetch_ohlcv(e, symbol, sdt, edt, timeframes[period])
    else:
        raise ValueError(f"不支持的交易所: {exchange}")
        # df = __exchange_fetch_ohlcv(e, symbol, sdt, edt, timeframes[period])

    df = df.sort_values("dt").reset_index(drop=True)
    df = df.drop_duplicates("dt", keep="last")
    df["symbol"] = symbol
    df = df[(df["dt"] <= pd.to_datetime(edt)) & (df["dt"] >= pd.to_datetime(sdt))]

    # 过滤未完成的K线
    if df["dt"].max() > pd.Timestamp.now():
        df = df.iloc[:-1]
    logger.info(f"get_raw_bars::获取 {symbol} {period} K线数据，时间段：{sdt} - {edt}，K线数量：{len(df)}")
    return df


def get_latest_klines(symbol, period, sdt=None, **kwargs):
    """获取最新的K线数据

    :param symbol: 交易对
    :param period: K线周期; 1m/5m/15m/30m/1h/2h/4h/1d
    :param sdt: 开始时间
    :param kwargs:

        - logger: loguru.logger, 默认为 loguru.logger
        - cache_path: str, 缓存路径，默认为 czsc.home_path
        - proxies: dict, 代理设置，默认为 None
        - kind: str, 交易类型，默认为 "币安期货"

    """
    logger = kwargs.get("logger", loguru.logger)
    cache_path = Path(kwargs.get("cache_path", czsc.home_path))
    cache_path.mkdir(exist_ok=True, parents=True)

    sdt = pd.to_datetime(sdt) if sdt else pd.to_datetime("20170101")
    edt = pd.Timestamp.now() + pd.Timedelta(days=2)
    file_cache = Path(f"{cache_path}/klines_{symbol}_{period}_{sdt.strftime('%Y%m%d')}.feather")

    if file_cache.exists():
        df = pd.read_feather(file_cache)
        logger.info(f"读取缓存数据：{file_cache}，最新时间：{df['dt'].max()}")
        _sdt = df["dt"].max() - pd.Timedelta(days=1)
    else:
        df = pd.DataFrame()
        _sdt = sdt

    proxies = kwargs.get("proxies")
    exchange = kwargs.get("exchange", "币安期货")

    df1 = get_raw_bars(symbol=symbol, period=period, sdt=_sdt, edt=edt, proxies=proxies, exchange=exchange)
    logger.info(f"获取 {symbol} {period} K线数据，时间段：{_sdt} - {edt}，K线数量：{len(df1)}")

    df2 = pd.concat([df, df1], ignore_index=True)
    df2 = df2.drop_duplicates("dt", keep="last")
    df2 = df2.sort_values("dt").reset_index(drop=True)
    df2.to_feather(file_cache)

    df3 = df2[df2["dt"] > sdt].reset_index(drop=True)
    logger.info(f"获取 {symbol} {period} K线数据，时间段：{df3['dt'].min()} - {df3['dt'].max()}，K线数量：{len(df3)}")
    return df3


def test_fetcher():
    import os

    os.environ["USE_PROXY"] = "1"

    df = get_symbols()
    print(df)

    # df1 = get_raw_bars(symbol="BTCUSDT", period="4h", sdt="2017-08-17 00:00:00", edt="20240817 20:00")
    df1 = get_raw_bars(
        symbol="ADABTC",
        period="8h",
        sdt="2024-08-17 00:00:00",
        edt="20241110 20:00",
        exchange="币安现货",
    )
    # symbols = ["ADABTC", "AVAXBTC", "BNBBTC", "DOGEBTC", "ETHBTC", "LTCBTC", "SOLBTC", "TRXBTC", "XRPBTC"]
    # rows = []
    # for symbol in symbols:
    #     df1 = get_raw_bars(
    #         symbol=symbol,
    #         period="1h",
    #         sdt="2024-08-17 00:00:00",
    #         edt="20241113 20:00",
    #         exchange="币安现货",
    #     )
    #     rows.append(df1)
    #
    # df = get_latest_klines(symbol="BTCUSDT", period="1h", sdt="2021-01-01", exchange="币安现货")
