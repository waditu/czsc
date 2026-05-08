"""
作者: zengbin93
邮箱: zeng_bin8888@163.com
创建时间: 2023/11/15 20:45
模块说明:
    CZSC 开源协作团队内部使用的数据接口模块。

    本模块封装了 CZSC 团队内部投研共享数据 API，提供统一的数据获取入口，主要职责包括：

    1. 行情数据接入：
       - 获取 A 股、ETF、A 股指数、南华指数、期货主力合约等品种列表
       - 获取上述品种的多周期 K 线数据（1 分钟到月线均支持）
       - 自动处理期货主力合约的分段下载与拼接、股指期货的有效交易时段过滤

    2. 全市场日线数据：
       - 提供 ``stocks_daily_klines`` 函数，按月分段下载全市场 A 股日线
       - 集成 ``czsc.disk_cache`` 磁盘缓存，加速重复研究

    3. 策略权重协作：
       - ``upload_strategy``：将本地策略持仓权重上传至共享服务器
       - ``get_stk_strategy``：获取 STK 系列子策略的历史持仓权重
       - ``get_strategy_dailys`` / ``get_strategy_weights``：带本地缓存的增量刷新接口
       - ``StrategyClient``：面向对象封装的策略管理 HTTP 客户端

    使用场景：
        团队成员在内部进行因子研究、策略回测、组合管理时调用，统一数据口径。

    注意事项：
        - 首次使用前需要在终端中通过 ``czsc.set_url_token`` 设置 token，
          或者通过环境变量 ``CZSC_TOKEN`` 配置；
        - 数据接口由内部服务 ``http://zbczsc.com:9106`` 提供，外网用户无权访问；
        - 缓存目录默认位于 ``~/.quant_data_cache``，可以通过环境变量 ``CZSC_CACHE_PATH`` 覆盖。
"""

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import loguru
import pandas as pd
import requests
from tqdm import tqdm

import czsc
from czsc import Freq

# 首次使用需要打开一个 Python 终端按如下方式设置 token，或者直接在环境变量中设置 CZSC_TOKEN
# 示例：czsc.set_url_token(token='your token', url='http://zbczsc.com:9106')

# 本地缓存目录：优先使用环境变量 CZSC_CACHE_PATH，否则使用用户主目录下的 .quant_data_cache
cache_path = os.getenv("CZSC_CACHE_PATH", os.path.expanduser("~/.quant_data_cache"))
# 数据 API 服务地址：优先使用环境变量 CZSC_DATA_API，否则使用默认内部服务地址
url = os.getenv("CZSC_DATA_API", "http://zbczsc.com:9106")
# 全局 DataClient 实例：复用同一份 token 和缓存目录，避免重复创建
dc = czsc.DataClient(token=os.getenv("CZSC_TOKEN"), url=url, cache_path=cache_path)


def get_groups():
    """获取投研共享数据的可选分组名称列表。

    用于上层在选择标的池时枚举可用分组，避免硬编码字符串。

    :return: list[str], 内置支持的分组名称集合，依次为：
             "A股指数"、"ETF"、"股票"、"期货主力"、"南华指数"
    """
    return ["A股指数", "ETF", "股票", "期货主力", "南华指数"]


def get_symbols(name, **kwargs):
    """获取指定分组下的所有标的代码。

    根据传入的分组名称，调用底层数据接口拉取对应的标的列表，并按照
    CZSC 内部约定的命名规范（``code#资产类型``）返回。

    :param name: str, 分组名称，可选值：
                 - "A股指数"：上交所/深交所指数，返回形如 ``000001.SH#INDEX``
                 - "ETF"：在 2024-04-02 仍有交易的 ETF，返回形如 ``510050.SH#ETF``
                 - "股票"：当前在交易的 A 股，返回形如 ``000001.SZ#STOCK``
                 - "期货主力"：期货主力合约 9001 系列，原样返回
                 - "南华指数"：南华商品指数，原样返回
                 - "ALL"：以上所有分组的并集
    :param kwargs: dict, 兼容参数，当前未使用，保留以兼容上层调用
    :return: list[str], 标的代码列表
    :raises ValueError: 当传入的分组名称无法识别时抛出
    """
    # 股票分组：从基础信息表中拉取所有正在交易的标的（status=1）
    if name == "股票":
        df = dc.stock_basic(nobj=1, status=1, ttl=3600 * 6)
        symbols = [f"{row['code']}#STOCK" for _, row in df.iterrows()]
        return symbols

    # ETF 分组：先拿到全量 ETF 基础信息，再用某一交易日的成交记录过滤掉已退市/无成交的
    if name == "ETF":
        df = dc.etf_basic(v="2", fields="code,name", ttl=3600 * 6)
        dfk = dc.pro_bar(trade_date="2024-04-02", asset="e", v="2")
        df = df[df["code"].isin(dfk["code"])].reset_index(drop=True)
        symbols = [f"{row['code']}#ETF" for _, row in df.iterrows()]
        return symbols

    # A 股指数：仅取上交所、深交所市场的指数代码
    if name == "A股指数":
        # 指数说明文档（仅限内部）：https://s0cqcxuy3p.feishu.cn/wiki/KuSAweAAhicvsGk9VPTc1ZWKnAd
        df = dc.index_basic(v="2", market="SSE,SZSE", ttl=3600 * 6)
        symbols = [f"{row['code']}#INDEX" for _, row in df.iterrows()]
        return symbols

    # 南华指数：商品期货综合指数序列
    if name == "南华指数":
        df = dc.index_basic(v="2", market="NH", ttl=3600 * 6)
        symbols = [row["code"] for _, row in df.iterrows()]
        return symbols

    # 期货主力：通过某一交易日的全量行情快照拿到所有主力合约代码
    if name == "期货主力":
        kline = dc.future_klines(v="2", trade_date="20240402", ttl=-1)
        return kline["code"].unique().tolist()

    # ALL：把上面所有分组拼接起来，得到全市场标的代码
    if name.upper() == "ALL":
        symbols = get_symbols("股票") + get_symbols("ETF")
        symbols += get_symbols("A股指数") + get_symbols("南华指数") + get_symbols("期货主力")
        return symbols

    raise ValueError(f"{name} 分组无法识别，获取标的列表失败！")


def get_min_future_klines(code, sdt, edt, freq="1m", **kwargs):
    """分段获取期货 1 分钟 K 线后合并为一个 DataFrame。

    由于 1 分钟 K 线数据量大，单次请求容易超时或被服务端截断，因此本函数
    将请求按年切分（最长 365 天为一个分段），分批拉取后再合并。
    同时会针对股指期货（IC/IF/IH）做盘中有效交易时段过滤，剔除集合竞价等无效分钟。

    :param code: str, 期货合约代码，例如 "SFIC9001"、"DLi9001"
    :param sdt: str | datetime, 开始日期，可任意常见格式
    :param edt: str | datetime, 结束日期
    :param freq: str, 频率字符串，默认为 "1m"
    :param kwargs: dict, 可选参数
                   - logger: 日志记录器，默认使用 loguru.logger
                   - ttl: int, 缓存有效期（秒），默认 3600；历史段落自动设为 -1 长期缓存
    :return: pd.DataFrame, 合并、去重后的 K 线数据，包含
             dt、symbol、open、close、high、low、vol 等字段
    """
    logger = kwargs.pop("logger", loguru.logger)

    sdt = pd.to_datetime(sdt).strftime("%Y%m%d")
    edt = pd.to_datetime(edt).strftime("%Y%m%d")
    # 按 365 天为一个分段，覆盖 2000~2030 年的全部时间区间
    # dates = pd.date_range(start=sdt, end=edt, freq='1M')  # 旧的按月切分方式，现已弃用
    dates = pd.date_range(start="20000101", end="20300101", freq="365D")

    dates = [d.strftime("%Y%m%d") for d in dates]
    dates = sorted(set(dates))

    rows = []
    # 遍历每一个分段区间 [sdt_, edt_)，按需要逐段拉取
    for sdt_, edt_ in tqdm(zip(dates[:-1], dates[1:], strict=False), total=len(dates) - 1):
        # 该段结束时间早于查询开始时间，跳过
        if edt_ < sdt:
            continue

        # 该段开始时间已经超过当前日期，后续段都是未来数据，直接终止
        if pd.to_datetime(sdt_).date() >= datetime.now().date():
            break

        # 历史已结束的段落使用永久缓存（ttl=-1），尚未结束的段落使用短期缓存
        ttl = kwargs.get("ttl", 60 * 60) if pd.to_datetime(edt_).date() >= datetime.now().date() else -1
        df = dc.future_klines(code=code, sdt=sdt_, edt=edt_, freq=freq, ttl=ttl, v="2")
        if df.empty:
            continue
        logger.info(f"{code}获取K线范围：{df['dt'].min()} - {df['dt'].max()}")
        rows.append(df)

    df = pd.concat(rows, ignore_index=True)
    df.rename(columns={"code": "symbol"}, inplace=True)
    df["dt"] = pd.to_datetime(df["dt"])
    # 不同段之间的边界可能重复，按 (dt, symbol) 去重，保留最后一次拉到的版本
    df = df.drop_duplicates(subset=["dt", "symbol"], keep="last")

    if code in ["SFIC9001", "SFIF9001", "SFIH9001"]:
        # 股指期货只保留连续竞价时段：09:31-11:30 与 13:01-15:00，剔除集合竞价及夜盘
        dt1 = datetime.strptime("09:31:00", "%H:%M:%S")
        dt2 = datetime.strptime("11:30:00", "%H:%M:%S")
        c1 = (df["dt"].dt.time >= dt1.time()) & (df["dt"].dt.time <= dt2.time())

        dt3 = datetime.strptime("13:01:00", "%H:%M:%S")
        dt4 = datetime.strptime("15:00:00", "%H:%M:%S")
        c2 = (df["dt"].dt.time >= dt3.time()) & (df["dt"].dt.time <= dt4.time())

        df = df[c1 | c2].copy().reset_index(drop=True)

    # 最后再按用户指定的 [sdt, edt] 区间裁剪结果
    df = df[(df["dt"] >= pd.to_datetime(sdt)) & (df["dt"] <= pd.to_datetime(edt))].copy().reset_index(drop=True)
    return df


def get_raw_bars(symbol, freq, sdt, edt, fq="前复权", **kwargs):
    """获取 CZSC 库定义的标准 RawBar 对象列表（统一数据入口）。

    本函数是协作数据源的统一行情接口，根据标的后缀自动分发到不同的底层取数函数：
        - ``9001`` 结尾：期货主力合约
        - ``.NH`` 结尾：南华指数（仅支持日线）
        - 含 ``SH`` 或 ``SZ``：A 股 / ETF / 指数

    :param symbol: str, 标的代码，需符合 ``code#资产类型`` 规范，例如：
                   - "000001.SH#INDEX"
                   - "510050.SH#ETF"
                   - "000001.SZ#STOCK"
                   - "SFIC9001"（期货主力）
                   - "NHCI.NH"（南华指数）
    :param freq: str | czsc.Freq, K 线周期。支持字符串 "1分钟"、"5分钟"、"15分钟"、
                 "30分钟"、"60分钟"、"日线"、"周线"、"月线"、"季线"、"年线"
    :param sdt: str | datetime, 开始时间
    :param edt: str | datetime, 结束时间
    :param fq: str, 除权类型，可选 "前复权"、"后复权"、"不复权"。
               注意：期货主力合约暂不支持前复权，会自动切换为后复权
    :param kwargs: dict, 可选参数
                   - logger: 日志记录器
                   - raw_bars: bool, 是否返回 RawBar 对象列表，False 时返回 DataFrame，默认 True
                   - ttl: int, 缓存有效期（秒），默认 -1（永久缓存）
    :return: list[RawBar] | pd.DataFrame, 取决于 ``raw_bars`` 参数
    :raises ValueError: 当 symbol 无法识别，或南华指数请求非日线周期时抛出

    示例：
        >>> from czsc.connectors import cooperation as coo
        >>> df = coo.get_raw_bars(symbol="000001.SH#INDEX", freq="日线",
        ...                       sdt="2001-01-01", edt="2021-12-31",
        ...                       fq='后复权', raw_bars=False)
    """
    logger = kwargs.pop("logger", loguru.logger)

    freq = czsc.Freq(freq)
    raw_bars = kwargs.get("raw_bars", True)
    ttl = kwargs.get("ttl", -1)
    sdt = pd.to_datetime(sdt).strftime("%Y%m%d")
    edt = pd.to_datetime(edt).strftime("%Y%m%d")

    # 分支一：期货主力合约（代码以 9001 结尾）
    if symbol.endswith("9001"):
        # 期货主力合约的复权说明（仅限内部）：
        # https://s0cqcxuy3p.feishu.cn/wiki/WLGQwJLWQiWPCZkPV7Xc3L1engg
        if fq == "前复权":
            logger.warning("期货主力合约暂时不支持前复权，已自动切换为后复权")

        # 根据目标频率判断底层基础周期：分钟取 1m，日及以上取 1d
        freq_rd = "1m" if freq.value.endswith("分钟") else "1d"
        if freq.value.endswith("分钟"):
            df = get_min_future_klines(code=symbol, sdt=sdt, edt=edt, freq="1m", ttl=ttl)
            if df.empty:
                return df

            # 接口返回缺失成交额时，用 vol*close 近似估算
            if "amount" not in df.columns:
                df["amount"] = df["vol"] * df["close"]

            df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]].copy().reset_index(drop=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars, base_freq="1分钟")

        else:
            df = dc.future_klines(code=symbol, sdt=sdt, edt=edt, freq=freq_rd, ttl=ttl, v="2")
            if df.empty:
                return df

            df.rename(columns={"code": "symbol"}, inplace=True)
            if "amount" not in df.columns:
                df["amount"] = df["vol"] * df["close"]

            df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]].copy().reset_index(drop=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars)

    # 分支二：南华指数（代码以 .NH 结尾），仅日线
    if symbol.endswith(".NH"):
        if freq != Freq.D:
            raise ValueError("南华指数只支持日线数据")
        df = dc.nh_daily(code=symbol, sdt=sdt, edt=edt, ttl=ttl, v="2")
        df.rename(columns={"code": "symbol", "volume": "vol"}, inplace=True)
        df["dt"] = pd.to_datetime(df["dt"])
        return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars)

    # 分支三：A 股 / ETF / 指数（代码包含 SH 或 SZ 后缀）
    if "SH" in symbol or "SZ" in symbol:
        # 复权类型映射：本地中文枚举到底层接口缩写
        fq_map = {"前复权": "qfq", "后复权": "hfq", "不复权": None}
        adj = fq_map.get(fq)

        # 标的代码格式为 "code#asset"，asset 取首字母即可（s/e/i 等）
        code, asset = symbol.split("#")

        if freq.value.endswith("分钟"):
            df = dc.pro_bar(code=code, sdt=sdt, edt=edt, freq="min", adj=adj, asset=asset[0].lower(), v="2", ttl=ttl)
            # 09:30:00 是集合竞价撮合时间，剔除该时刻避免与 09:31 重复
            df = df[~df["dt"].str.endswith("09:30:00")].reset_index(drop=True)
            df.rename(columns={"code": "symbol"}, inplace=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars, base_freq="1分钟")

        else:
            df = dc.pro_bar(code=code, sdt=sdt, edt=edt, freq="day", adj=adj, asset=asset[0].lower(), v="2", ttl=ttl)
            df.rename(columns={"code": "symbol"}, inplace=True)
            df["dt"] = pd.to_datetime(df["dt"])
            return czsc.resample_bars(df, target_freq=freq, raw_bars=raw_bars)

    raise ValueError(f"symbol {symbol} 无法识别，获取数据失败！")


@czsc.disk_cache(path=cache_path, ttl=-1)
def stocks_daily_klines(sdt="20170101", edt="20240101", **kwargs):
    """获取全市场 A 股的日线数据（按月分段拉取并拼接，结果带磁盘缓存）。

    为避免单次接口请求数据量过大被服务端截断，本函数会把 ``[sdt, edt]`` 区间
    按自然月切分成多个子区间，逐月拉取再合并；并通过 ``czsc.disk_cache``
    把整个结果缓存到磁盘，重复研究时直接命中缓存。

    :param sdt: str, 开始日期，默认 "20170101"
    :param edt: str, 结束日期，默认 "20240101"
    :param kwargs: dict, 可选参数
                   - adj: str, 复权类型，传给底层 ``pro_bar``，默认 "hfq"（后复权）
                   - exclude_bj: bool, 是否剔除北交所标的（.BJ 结尾），默认 True
                   - nxb: tuple[int], 未来 N 日收益的窗口列表，默认 [1, 2, 5, 10, 20, 30, 60]；
                          传入空值时跳过未来收益计算
    :return: pd.DataFrame, 字段包含 symbol、dt、open、close、high、low、vol、amount、price，
             以及由 ``nxb`` 生成的 n1b、n2b 等未来收益列
    """
    adj = kwargs.get("adj", "hfq")

    # 转换为 datetime 对象，便于后续计算
    start_dt = pd.to_datetime(sdt)
    end_dt = pd.to_datetime(edt)

    # 计算 sdt 和 edt 之间的每个月 1 号，得到分段下载的 [sdt_, edt_) 区间列表
    date_spans = []
    current = start_dt.replace(day=1)  # 从月初开始
    while current <= end_dt:
        sdt_ = current.strftime("%Y%m%d")
        edt_ = (current + pd.DateOffset(months=1)).replace(day=1).strftime("%Y%m%d")
        date_spans.append((sdt_, edt_))
        current = (current + pd.DateOffset(months=1)).replace(day=1)

    res = []
    for sdt_, edt_ in date_spans:
        # 当前月份使用较短缓存时间（6 小时），历史月份使用永久缓存
        ttl = 3600 * 6 if edt_ < pd.Timestamp.now().strftime("%Y%m%d") else -1
        kline = dc.pro_bar(sdt=sdt_, edt=edt_, adj=adj, v="2", ttl=ttl)
        res.append(kline)

    dfk = pd.concat(res, ignore_index=True)
    dfk["dt"] = pd.to_datetime(dfk["dt"])
    dfk = dfk.sort_values(["code", "dt"], ascending=True).reset_index(drop=True)
    # 默认剔除北交所（.BJ），数据可能不完整且大多数策略并不交易北交所
    if kwargs.get("exclude_bj", True):
        dfk = dfk[~dfk["code"].str.endswith(".BJ")].reset_index(drop=True)

    dfk = dfk.rename(columns={"code": "symbol"})
    # 跨月份拼接可能存在重复行，按 (symbol, dt) 去重，保留最后一次出现的记录
    dfk = dfk.drop_duplicates(subset=["symbol", "dt"], keep="last").reset_index(drop=True)
    dfk["price"] = dfk["close"]
    nxb = kwargs.get("nxb", [1, 2, 5, 10, 20, 30, 60])
    if nxb:
        dfk = czsc.update_nxb(dfk, nseq=nxb)
    return dfk


def upload_strategy(df, meta, token=None, **kwargs):
    """上传策略数据到协作服务器。

    将本地策略生成的持仓权重以及策略元数据上传至 ``http://zbczsc.com:9106``，
    用于团队内部的共享研究、批量回测或风险监控。

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
    :return: dict, 服务端响应结果
    """
    logger = kwargs.pop("logger", loguru.logger)
    df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    logger.info(f"输入数据中有 {len(df)} 条权重信号")

    # 去除单个品种下相邻时间权重相同的数据，节省传输与存储成本
    _res = []
    for _, dfg in df.groupby("symbol"):
        dfg = dfg.sort_values("dt", ascending=True).reset_index(drop=True)
        dfg = dfg[dfg["weight"].diff().fillna(1) != 0].copy()
        _res.append(dfg)
    df = pd.concat(_res, ignore_index=True)
    df = df.sort_values(["dt"]).reset_index(drop=True)
    df["dt"] = df["dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"去除单个品种下相邻时间权重相同的数据后，剩余 {len(df)} 条权重信号")

    # 构造上传 payload：weights 字段使用 split 方向的 JSON 以便服务端高效解析
    data = {
        "weights": df[["dt", "symbol", "weight"]].to_json(orient="split"),
        "token": token or os.getenv("CZSC_TOKEN"),
        "strategy_name": meta.get("name"),
        "meta": meta,
    }
    response = requests.post("http://zbczsc.com:9106/upload_strategy", json=data)

    logger.info(f"上传策略接口返回: {response.json()}")
    return response.json()


def get_stk_strategy(name="STK_001", **kwargs):
    """获取 STK 系列子策略的持仓权重数据，并匹配未来 1 日收益。

    本函数面向选股策略的研究场景，会自动拼接持仓权重与对应日期的下一日收益（n1b），
    便于直接进行 IC 分析、组合收益归因等。

    :param name: str, 子策略名称，例如 "STK_001"、"STK_002"
    :param kwargs: dict
        sdt: str, 可选, 开始日期，默认 "20170101"
        edt: str, 可选, 结束日期，默认当前日期
        ttl: int, 可选, 接口缓存时间（秒），默认 6 小时
    :return: pd.DataFrame, 字段包含 dt、symbol、weight、n1b
    """
    dfw = dc.post_request(api_name=name, v="2", hist=1, ttl=kwargs.get("ttl", 3600 * 6))
    dfw["dt"] = pd.to_datetime(dfw["dt"])
    sdt = kwargs.get("sdt", "20170101")
    edt = pd.Timestamp.now().strftime("%Y%m%d")
    edt = kwargs.get("edt", edt)
    dfw = dfw[(dfw["dt"] >= pd.to_datetime(sdt)) & (dfw["dt"] <= pd.to_datetime(edt))].copy().reset_index(drop=True)

    # 拉取同区间的全市场日线（含未来 1、2 日收益），与权重表做左连接
    dfb = stocks_daily_klines(sdt=sdt, edt=edt, nxb=(1, 2))
    dfw = pd.merge(dfw, dfb, on=["dt", "symbol"], how="left")
    dfh = dfw[["dt", "symbol", "weight", "n1b"]].copy()
    return dfh


# ======================================================================================================================
# 增量更新本地缓存数据
# ----------------------------------------------------------------------------------------------------------------------
# 下面这一组函数（get_all_strategies / get_strategy_dailys / get_strategy_weights）共同构成了
# “首次全量、后续增量”的本地缓存机制：
#   - 第一次调用时一次性拉取全部历史数据，落盘成 feather 文件；
#   - 后续调用时只拉取最近几天的新数据，与本地缓存做合并、去重，再写回缓存；
#   - 当缓存能完全覆盖请求区间时直接返回，避免任何远程请求。
# ======================================================================================================================
def get_all_strategies(ttl=3600 * 24 * 7, logger=loguru.logger, path=cache_path):
    """获取所有策略的元数据。

    元数据描述了每个策略的基本信息（名称、作者、基础频率、样本外起始日期等），
    主要用于在策略池中筛选、展示和组合。

    :param ttl: int, 可选, 缓存有效期（秒），默认 7 天
    :param logger: loguru.logger, 可选, 日志记录器
    :param path: str, 可选, 缓存根目录路径
    :return: pd.DataFrame, 包含字段 name, description, author, base_freq, outsample_sdt；示例如下：

        ===========  =====================  =========  =========  ============
        name         description            author     base_freq  outsample_sdt
        ===========  =====================  =========  =========  ============
        STK_001      A股选股策略               ZB         1分钟      20220101
        STK_002      A股选股策略               ZB         1分钟      20220101
        STK_003      A股选股策略               ZB         1分钟      20220101
        ===========  =====================  =========  =========  ============
    """
    path = Path(path) / "strategy"
    path.mkdir(exist_ok=True, parents=True)
    file_metas = path / "metas.feather"

    # 缓存文件存在且未过期：直接读取，避免远程请求
    if file_metas.exists() and (time.time() - file_metas.stat().st_mtime) < ttl:
        logger.info("【缓存命中】获取所有策略的元数据")
        dfm = pd.read_feather(file_metas)

    else:
        logger.info("【全量刷新】获取所有策略的元数据并刷新缓存")
        dfm = dc.get_all_strategies(v="2", ttl=0)
        dfm.to_feather(file_metas)

    return dfm


def __update_strategy_dailys(file_cache, strategy, logger=loguru.logger):
    """更新（增量或全量）策略的日收益缓存数据。

    内部辅助函数：
        - 若缓存文件已存在，从缓存最新日期向前回溯 3 天再向后拉取，做增量合并；
        - 若缓存文件不存在，自 20170101 起做全量拉取。

    :param file_cache: pathlib.Path, 缓存文件路径（feather 格式）
    :param strategy: str, 策略名称
    :param logger: loguru.logger, 日志记录器
    :return: pd.DataFrame, 更新后的完整日收益数据
    """
    # 增量刷新分支：基于缓存最新日期推断需要补齐的区间
    if file_cache.exists():
        df = pd.read_feather(file_cache)

        # 向前回溯 3 天作为缓冲，避免最新一日数据修订带来的差异
        cache_sdt = (df["dt"].max() - pd.Timedelta(days=3)).strftime("%Y%m%d")
        cache_edt = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y%m%d")
        logger.info(f"【增量刷新缓存】获取策略 {strategy} 的日收益数据：{cache_sdt} - {cache_edt}")

        dfc = dc.sub_strategy_dailys(strategy=strategy, v="2", sdt=cache_sdt, edt=cache_edt, ttl=0)
        dfc["dt"] = pd.to_datetime(dfc["dt"])
        df = pd.concat([df, dfc]).drop_duplicates(["dt", "symbol", "strategy"], keep="last")

    else:
        # 全量刷新分支：缓存不存在时一次性拉满历史数据
        cache_edt = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y%m%d")
        logger.info(f"【全量刷新缓存】获取策略 {strategy} 的日收益数据：20170101 - {cache_edt}")
        df = dc.sub_strategy_dailys(strategy=strategy, v="2", sdt="20170101", edt=cache_edt, ttl=0)

    df = df.reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["dt"])
    df.to_feather(file_cache)
    return df


def get_strategy_dailys(
    strategy="FCS001", symbol=None, sdt="20240101", edt=None, logger=loguru.logger, path=cache_path
):
    """获取策略的历史日收益数据（带本地缓存）。

    优先尝试命中本地缓存；若缓存数据不能覆盖请求的结束日期，则触发增量刷新。

    :param strategy: str, 策略名称
    :param symbol: str, 可选, 品种名称，传入后只返回该品种的数据
    :param sdt: str, 开始时间，默认 "20240101"
    :param edt: str, 可选, 结束时间，默认当前时间
    :param logger: loguru.logger, 可选, 日志记录器
    :param path: str, 可选, 缓存根目录路径
    :return: pd.DataFrame, 包含字段 dt, symbol, strategy, returns；示例如下：

        ===================  ==========  ========  =========
        dt                   strategy    symbol      returns
        ===================  ==========  ========  =========
        2017-01-10 00:00:00  STK_001     A股选股        0.001
        2017-01-11 00:00:00  STK_001     A股选股        0.012
        2017-01-12 00:00:00  STK_001     A股选股        0.011
        ===================  ==========  ========  =========
    """
    path = Path(path) / "strategy" / "dailys"
    path.mkdir(exist_ok=True, parents=True)
    file_cache = path / f"{strategy}.feather"

    if edt is None:
        edt = pd.Timestamp.now().strftime("%Y%m%d %H:%M:%S")

    # 判断缓存数据是否能满足需求：缓存最新日期 >= 请求结束日期即视为命中
    if file_cache.exists():
        df = pd.read_feather(file_cache)

        if df["dt"].max() >= pd.Timestamp(edt):
            logger.info(f"【缓存命中】获取策略 {strategy} 的日收益数据：{sdt} - {edt}")

            dfd = df[(df["dt"] >= pd.Timestamp(sdt)) & (df["dt"] <= pd.Timestamp(edt))].copy()
            if symbol:
                dfd = dfd[dfd["symbol"] == symbol].copy()
            return dfd

    # 缓存未命中或数据不全：触发刷新后再过滤返回
    logger.info(f"【缓存刷新】获取策略 {strategy} 的日收益数据：{sdt} - {edt}")
    df = __update_strategy_dailys(file_cache, strategy, logger=logger)
    dfd = df[(df["dt"] >= pd.Timestamp(sdt)) & (df["dt"] <= pd.Timestamp(edt))].copy()
    if symbol:
        dfd = dfd[dfd["symbol"] == symbol].copy()
    return dfd


def __update_strategy_weights(file_cache, strategy, logger=loguru.logger):
    """更新（增量或全量）策略的持仓权重缓存数据。

    内部辅助函数，逻辑与 ``__update_strategy_dailys`` 类似，区别在于：
        - 数据接口为 ``post_request(api_name=strategy, hist=1)``；
        - 去重键使用 ``(dt, symbol, weight)``。

    :param file_cache: pathlib.Path, 缓存文件路径
    :param strategy: str, 策略名称
    :param logger: loguru.logger, 日志记录器
    :return: pd.DataFrame, 更新后的完整持仓权重数据
    """
    # 增量刷新分支
    if file_cache.exists():
        df = pd.read_feather(file_cache)

        cache_sdt = (df["dt"].max() - pd.Timedelta(days=3)).strftime("%Y%m%d")
        cache_edt = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y%m%d")
        logger.info(f"【增量刷新缓存】获取策略 {strategy} 的持仓权重数据：{cache_sdt} - {cache_edt}")

        dfc = dc.post_request(api_name=strategy, v="2", sdt=cache_sdt, edt=cache_edt, hist=1, ttl=0)
        dfc["dt"] = pd.to_datetime(dfc["dt"])
        dfc["strategy"] = strategy

        df = pd.concat([df, dfc]).drop_duplicates(["dt", "symbol", "weight"], keep="last")

    else:
        # 全量刷新分支
        cache_edt = (pd.Timestamp.now() + pd.Timedelta(days=1)).strftime("%Y%m%d")
        logger.info(f"【全量刷新缓存】获取策略 {strategy} 的持仓权重数据：20170101 - {cache_edt}")
        df = dc.post_request(api_name=strategy, v="2", sdt="20170101", edt=cache_edt, hist=1, ttl=0)
        df["dt"] = pd.to_datetime(df["dt"])
        df["strategy"] = strategy

    df = df.reset_index(drop=True)
    df.to_feather(file_cache)
    return df


def get_strategy_weights(strategy="FCS001", sdt="20240101", edt=None, logger=loguru.logger, path=cache_path):
    """获取策略的历史持仓权重数据（带本地缓存）。

    缓存命中策略与 ``get_strategy_dailys`` 一致：缓存最新日期不小于请求结束日期视为命中。

    :param strategy: str, 策略名称
    :param sdt: str, 开始时间，默认 "20240101"
    :param edt: str, 可选, 结束时间，默认当前时间
    :param logger: loguru.logger, 可选, 日志记录器
    :param path: str, 可选, 缓存根目录路径
    :return: pd.DataFrame, 包含字段 dt, symbol, weight, update_time, strategy；示例如下：

        ===================  =========  ========  ===================  ==========
        dt                   symbol       weight  update_time          strategy
        ===================  =========  ========  ===================  ==========
        2017-01-09 00:00:00  000001.SZ         0  2024-07-27 16:13:29  STK_001
        2017-01-10 00:00:00  000001.SZ         0  2024-07-27 16:13:29  STK_001
        2017-01-11 00:00:00  000001.SZ         0  2024-07-27 16:13:29  STK_001
        ===================  =========  ========  ===================  ==========
    """
    path = Path(path) / "strategy" / "weights"
    path.mkdir(exist_ok=True, parents=True)
    file_cache = path / f"{strategy}.feather"

    if edt is None:
        edt = pd.Timestamp.now().strftime("%Y%m%d %H:%M:%S")

    # 判断缓存数据是否能满足需求
    if file_cache.exists():
        df = pd.read_feather(file_cache)

        if df["dt"].max() >= pd.Timestamp(edt):
            logger.info(f"【缓存命中】获取策略 {strategy} 的历史持仓权重数据：{sdt} - {edt}")
            dfd = df[(df["dt"] >= pd.Timestamp(sdt)) & (df["dt"] <= pd.Timestamp(edt))].copy()
            return dfd

    # 缓存未命中或数据不全：触发增量刷新
    logger.info(f"【缓存刷新】获取策略 {strategy} 的历史持仓权重数据：{sdt} - {edt}")
    df = __update_strategy_weights(file_cache, strategy, logger=logger)
    dfd = df[(df["dt"] >= pd.Timestamp(sdt)) & (df["dt"] <= pd.Timestamp(edt))].copy()
    return dfd


class StrategyClient:
    """CZSC 策略管理 API 客户端。

    面向对象封装了一组策略管理相关的 HTTP 接口，相比上面以模块函数提供的能力，
    本类更适用于：
        - 需要在多个接口间共享同一个 token 与 ``requests.Session``；
        - 需要在同一进程内频繁地切换或更新 token；
        - 希望统一的错误处理与日志格式。

    主要功能：
        - 策略元数据：增、删、改、查；
        - 策略权重：查询、上传、删除；
        - 缓存清理：按 token 或角色清理服务端缓存。
    """

    def __init__(self, base_url: str, token: str = None, logger=loguru.logger):
        """初始化客户端。

        :param base_url: str, API 基础 URL，例如 ``http://zbczsc.com:9106``
        :param token: str, 可选, 访问令牌；可后续通过 ``set_token`` 设置
        :param logger: loguru.logger, 可选, 日志记录器
        """
        # 去除末尾斜杠，便于和 endpoint 拼接
        self.base_url = base_url.rstrip("/")
        self.token = token
        # 复用 Session 以利用底层 HTTP keep-alive，提升批量请求性能
        self.session = requests.Session()
        self._setup_headers()
        self.logger = logger

    def _setup_headers(self):
        """根据当前 token 设置统一的请求头（内部方法）。

        始终设置 ``Content-Type`` 与 ``Accept`` 为 JSON；
        当 token 存在时附加 Bearer 鉴权头。
        """
        self.session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def set_token(self, token: str):
        """更新当前客户端使用的访问令牌。

        :param token: str, 新的访问令牌
        """
        self.token = token
        self._setup_headers()
        self.logger.info("访问令牌已更新")

    def _make_request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """统一的 HTTP 请求底层方法（内部方法）。

        负责拼接 URL、根据 method 选择 GET/POST 调用、统一异常处理与日志输出。

        :param method: str, HTTP 方法，"GET" 或 "POST"，大小写不敏感
        :param endpoint: str, API 端点路径，需以 "/" 开头
        :param data: dict, 可选, 请求数据；GET 时作为 query string，POST 时作为 JSON body
        :return: dict, 服务端返回的 JSON 数据
        :raises requests.exceptions.RequestException: 网络异常或状态码非 2xx 时抛出
        :raises ValueError: 响应不是合法的 JSON 时抛出
        """
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=data)
            else:
                response = self.session.post(url, json=data)

            response.raise_for_status()
            result = response.json()

            self.logger.debug(f"API请求成功: {method} {endpoint}")
            return result

        except requests.exceptions.RequestException as e:
            self.logger.error(f"API请求失败: {method} {endpoint}, 错误: {e}")
            raise
        except ValueError as e:
            self.logger.error(f"响应解析失败: {e}")
            raise

    def get_all_strategy_metadata(self) -> list[dict]:
        """获取所有策略元数据。

        :return: list[dict], 策略元数据列表；接口失败时返回空列表
        """
        data = {"token": self.token}
        result = self._make_request("POST", "/get_all_strategy_metadata", data)

        # 接口约定 code=0 为成功
        if result.get("code") == 0:
            self.logger.info(f"成功获取{len(result.get('data', []))}个策略元数据")
            return result.get("data", [])
        else:
            self.logger.error(f"获取策略元数据失败: {result.get('msg', '未知错误')}")
            return []

    def add_strategy_meta(
        self,
        strategy_name: str,
        base_freq: str,
        description: str,
        author_id: int,
        outsample_sdt: str,
        weight_type: str,
        memo: str = "",
    ) -> bool:
        """添加策略元数据。

        :param strategy_name: str, 策略名称（全局唯一）
        :param base_freq: str, 基础频率，例如 "1分钟"、"日线"
        :param description: str, 策略描述
        :param author_id: int, 作者 ID
        :param outsample_sdt: str, 样本外开始日期，格式 YYYYMMDD
        :param weight_type: str, 权重类型
        :param memo: str, 备注信息，默认空字符串
        :return: bool, 是否添加成功
        """
        data = {
            "token": self.token,
            "strategy_name": strategy_name,
            "meta": {
                "base_freq": base_freq,
                "description": description,
                "author_id": author_id,
                "outsample_sdt": outsample_sdt,
                "weight_type": weight_type,
                "memo": memo,
            },
        }

        result = self._make_request("POST", "/add_strategy_meta", data)

        # 此接口约定 code=200 为成功（与 get_all_strategy_metadata 不同）
        if result.get("code") == 200:
            self.logger.info(f"成功添加策略元数据: {strategy_name}")
            return True
        else:
            self.logger.error(f"添加策略元数据失败: {result.get('msg', '未知错误')}")
            return False

    def update_strategy_meta(
        self,
        strategy_name: str,
        base_freq: str = None,
        description: str = None,
        author_id: int = None,
        outsample_sdt: str = None,
        weight_type: str = None,
        memo: str = None,
    ) -> bool:
        """更新策略元数据（仅更新非 None 的字段）。

        :param strategy_name: str, 策略名称（用于定位需要更新的策略）
        :param base_freq: str, 可选, 基础频率
        :param description: str, 可选, 策略描述
        :param author_id: int, 可选, 作者 ID（仅管理员可更改）
        :param outsample_sdt: str, 可选, 样本外开始日期
        :param weight_type: str, 可选, 权重类型
        :param memo: str, 可选, 备注信息
        :return: bool, 是否更新成功
        """
        meta = {}
        # 只把非 None 的字段加入更新载荷，避免误覆盖
        for key, value in [
            ("base_freq", base_freq),
            ("description", description),
            ("author_id", author_id),
            ("outsample_sdt", outsample_sdt),
            ("weight_type", weight_type),
            ("memo", memo),
        ]:
            if value is not None:
                meta[key] = value

        data = {"token": self.token, "strategy_name": strategy_name, "meta": meta}

        result = self._make_request("POST", "/update_strategy_meta", data)

        if result.get("code") == 200:
            self.logger.info(f"成功更新策略元数据: {strategy_name}")
            return True
        else:
            self.logger.error(f"更新策略元数据失败: {result.get('msg', '未知错误')}")
            return False

    def delete_strategy_meta(self, strategy_name: str) -> bool:
        """删除策略元数据（软删除，权重数据保留）。

        :param strategy_name: str, 策略名称
        :return: bool, 是否删除成功
        """
        data = {"token": self.token, "strategy_name": strategy_name, "meta": {}}

        result = self._make_request("POST", "/delete_strategy_meta", data)

        if result.get("code") == 200:
            self.logger.info(f"成功删除策略元数据: {strategy_name}")
            return True
        else:
            self.logger.error(f"删除策略元数据失败: {result.get('msg', '未知错误')}")
            return False

    def get_all_strategy_latest_weights(self) -> list[dict]:
        """获取所有策略的最新持仓权重快照。

        :return: list[dict], 策略权重数据列表；接口失败时返回空列表
        """
        data = {"token": self.token}
        result = self._make_request("POST", "/get_all_strategy_latest_weights", data)

        if result.get("code") == 0:
            self.logger.info(f"成功获取{len(result.get('data', []))}条最新权重数据")
            return result.get("data", [])
        else:
            self.logger.error(f"获取最新权重数据失败: {result.get('msg', '未知错误')}")
            return []

    def query_strategy_weight(self, strategy: str, sdt: str = "", edt: str = "", symbols: list[str] = None) -> dict:
        """查询单个策略的持仓权重。

        :param strategy: str, 策略名称
        :param sdt: str, 可选, 开始日期
        :param edt: str, 可选, 结束日期
        :param symbols: list[str], 可选, 限定的标的代码列表；不传则查询全部
        :return: dict, 包含 meta（元数据）和 weights（权重列表）的字典；失败时返回空字典
        """
        data = {"token": self.token, "strategy": strategy, "sdt": sdt, "edt": edt, "symbols": symbols or []}

        result = self._make_request("POST", "/query_strategy_weight", data)

        if result.get("code") == 0:
            data_result = result.get("data", {})
            weights_count = len(data_result.get("weights", []))
            self.logger.info(f"成功查询策略 {strategy} 的权重数据，共{weights_count}条记录")
            return data_result
        else:
            self.logger.error(f"查询策略权重失败: {result.get('msg', '未知错误')}")
            return {}

    def delete_strategy(self, strategy: str) -> bool:
        """彻底删除策略（同时清除持仓权重和元数据，不可恢复）。

        :param strategy: str, 策略名称
        :return: bool, 是否删除成功
        """
        data = {"token": self.token, "strategy": strategy}

        result = self._make_request("POST", "/delete_strategy", data)

        if result.get("code") == 200:
            self.logger.info(f"成功删除策略: {strategy}")
            return True
        else:
            self.logger.error(f"删除策略失败: {result.get('msg', '未知错误')}")
            return False

    def clear_cache(self, tokens: list[str] = None, roles: list[int] = None) -> bool:
        """清除服务端的接口缓存。

        :param tokens: list[str], 可选, 需要清除的 token 列表
        :param roles: list[int], 可选, 需要清除的角色 ID 列表
        :return: bool, 是否清除成功
        """
        data = {"tokens": tokens or [], "roles": roles or []}

        result = self._make_request("POST", "/clear_cache", data)

        # 兼容服务端未返回 code 的情况：默认认为成功
        if result.get("code", 200) == 200:
            self.logger.info("成功清除缓存")
            return True
        else:
            self.logger.error("清除缓存失败")
            return False

    def upload_strategy_weights(
        self,
        df: Any,
        strategy_name: str,
        description: str,
        base_freq: str,
        author: str,
        outsample_sdt: str,
        upload_token: str = None,
    ) -> dict:
        """上传策略权重数据。

        与模块级 ``upload_strategy`` 函数功能一致，区别在于参数以独立形参的形式暴露，
        且使用 ``self.session`` 共享连接。

        :param df: pd.DataFrame, 策略权重数据，必须包含 dt, symbol, weight 三列
        :param strategy_name: str, 策略名称
        :param description: str, 策略描述
        :param base_freq: str, 基础频率
        :param author: str, 作者
        :param outsample_sdt: str, 样本外开始日期
        :param upload_token: str, 可选, 上传凭证码；不提供则从环境变量 CZSC_TOKEN 读取
        :return: dict, 上传接口返回的结果
        :raises requests.exceptions.RequestException: 网络异常时抛出
        """
        import os

        import pandas as pd

        # 数据预处理：拷贝以避免污染外部数据
        df_copy = df.copy()
        df_copy["dt"] = pd.to_datetime(df_copy["dt"])

        self.logger.info(f"输入数据中有 {len(df_copy)} 条权重信号")

        # 去除单个品种下相邻时间权重相同的数据，减少冗余
        _res = []
        for _, dfg in df_copy.groupby("symbol"):
            dfg = dfg.sort_values("dt", ascending=True).reset_index(drop=True)
            dfg = dfg[dfg["weight"].diff().fillna(1) != 0].copy()
            _res.append(dfg)

        df_processed = pd.concat(_res, ignore_index=True)
        df_processed = df_processed.sort_values(["dt"]).reset_index(drop=True)
        df_processed["dt"] = df_processed["dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

        self.logger.info(f"去除单个品种下相邻时间权重相同的数据后，剩余 {len(df_processed)} 条权重信号")

        # 构造元数据
        meta = {
            "name": strategy_name,
            "description": description,
            "base_freq": base_freq,
            "author": author,
            "outsample_sdt": outsample_sdt,
        }

        # 构造上传数据：weights 字段使用 split 方向 JSON 减小体积
        data = {
            "weights": df_processed[["dt", "symbol", "weight"]].to_json(orient="split"),
            "token": upload_token or os.getenv("CZSC_TOKEN"),
            "strategy_name": strategy_name,
            "meta": meta,
        }

        # 使用专门的上传接口（与 base_url 不同），直接拼写完整地址
        upload_url = "http://zbczsc.com:9106/upload_strategy"

        try:
            response = self.session.post(upload_url, json=data)
            response.raise_for_status()
            result = response.json()

            self.logger.info(f"成功上传策略权重: {strategy_name}")
            self.logger.debug(f"上传接口返回: {result}")
            return result

        except requests.exceptions.RequestException as e:
            self.logger.error(f"上传策略权重失败: {strategy_name}, 错误: {e}")
            raise
