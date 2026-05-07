# coding: utf-8
"""
模块说明:
    聚宽（JQData）HTTP 数据接口的轻量封装。

    本模块通过聚宽提供的 HTTP API（``https://dataapi.joinquant.com/apis``）获取行情、
    财务、概念板块、指数成份等数据，并按照 CZSC 的标准数据结构返回，便于上层策略
    直接消费。

    职责：
        - 凭证管理：``set_token`` / ``get_token`` 负责持久化和刷新调用凭证；
        - 基础信息：股票/基金/指数/期货等基础信息表，行业归属，成份股；
        - 行情数据：分钟和日线 K 线获取（``get_kline`` / ``get_kline_period``），
          自动转换为 ``czsc.RawBar`` 列表；
        - 实时回测：``get_init_bg`` 提供 BarGenerator 的初始化能力；
        - 财务数据：``get_fundamental`` / ``run_query`` 拉取财务因子；
        - 综合 F10：``get_share_basic`` 一键获取个股基础面信息汇总。

    使用场景：
        当用户拥有有效的聚宽 JQData 账号且偏好通过 HTTP 接口拉取数据时使用本模块；
        若已经安装 ``jqdatasdk`` Python 包，可直接使用其 SDK，本模块作为 HTTP 备选方案。

    注意事项：
        - 调用前请先通过 ``set_token(jq_mob, jq_pwd)`` 持久化登录凭证（默认存放在
          ``~/jq.token``），否则 ``get_token`` 会抛出 ``ValueError``；
        - 聚宽免费账户每日的查询条数有限（``get_query_count``），请合理使用；
        - 单次 K 线请求最大 5000 条，超过会触发 warning 并被服务端截断；
        - 区间查询超过 1000 个交易日时同样可能失败，需要自行分段。
"""
import os
import pickle
import json
import requests
import warnings
from collections import OrderedDict
import pandas as pd
from datetime import datetime, timedelta
from typing import List
from urllib.parse import quote

from czsc import RawBar, Freq, BarGenerator, freq_end_time

# CZSC 内部周期字符串到聚宽 unit 字符串的映射
freq_cn2jq = {
    "1分钟": "1m",
    "5分钟": "5m",
    "15分钟": "15m",
    "30分钟": "30m",
    "60分钟": "60m",
    "日线": "1d",
    "周线": "1w",
    "月线": "1M",
}

# 聚宽 HTTP API 入口地址
url = "https://dataapi.joinquant.com/apis"
# 用户主目录路径：用于存放凭证文件
home_path = os.path.expanduser("~")
# 凭证文件路径：使用 pickle 序列化保存账号密码
file_token = os.path.join(home_path, "jq.token")

# 通用日期时间格式
dt_fmt = "%Y-%m-%d %H:%M:%S"
date_fmt = "%Y-%m-%d"

# 聚宽支持的 K 线粒度: 1m, 5m, 15m, 30m, 60m, 120m, 1d, 1w, 1M
# 下面的 freq_convert 把 czsc 内部使用的 pandas-style 频率字符串映射到聚宽 unit 字符串
freq_convert = {
    "1min": "1m",
    "5min": "5m",
    "15min": "15m",
    "30min": "30m",
    "60min": "60m",
    "D": "1d",
    "W": "1w",
    "M": "1M",
}

# pandas-style 频率字符串到 czsc.Freq 枚举的映射
freq_map = {
    "1min": Freq.F1,
    "5min": Freq.F5,
    "15min": Freq.F15,
    "30min": Freq.F30,
    "60min": Freq.F60,
    "D": Freq.D,
    "W": Freq.W,
    "M": Freq.M,
}


def set_token(jq_mob, jq_pwd):
    """持久化保存聚宽 JQData 登录凭证。

    将账号和密码以 pickle 形式写入用户主目录下的 ``jq.token`` 文件。
    后续 ``get_token`` 调用会读取该文件并向聚宽换取一次性的访问令牌。

    :param jq_mob: str, mob 是申请 JQData 时所填写的手机号
    :param jq_pwd: str, Password 为聚宽官网登录密码，新申请用户默认为手机号后 6 位
    :return: None
    """
    with open(file_token, "wb") as f:
        pickle.dump([jq_mob, jq_pwd], f)


def get_token():
    """获取聚宽 JQData 调用凭证 token。

    流程：
        1. 从本地 ``~/jq.token`` 加载用户名 / 密码；
        2. 通过 ``get_current_token`` 接口换取一次性的访问令牌；
        3. 直接返回令牌字符串，调用者把它放进后续请求的 ``token`` 字段。

    :return: str, 聚宽接口访问令牌
    :raises ValueError: 当本地凭证文件不存在时抛出，需要先调用 ``set_token``
    """
    if not os.path.exists(file_token):
        raise ValueError(f"{file_token} 文件不存在，请先调用 set_token 进行设置")

    with open(file_token, "rb") as f:
        jq_mob, jq_pwd = pickle.load(f)

    body = {
        "method": "get_current_token",
        "mob": jq_mob,  # mob 是申请 JQData 时所填写的手机号
        "pwd": quote(jq_pwd),  # Password 为聚宽官网登录密码，新申请用户默认为手机号后 6 位
    }
    response = requests.post(url, data=json.dumps(body))
    token = response.text
    return token


def text2df(text):
    """将聚宽接口返回的 CSV 风格文本转换为 ``pd.DataFrame``。

    聚宽 HTTP 接口的返回值通常是以 ``\\n`` 分隔的多行文本，第一行是表头，
    其余每行为以逗号分隔的字段值。

    :param text: str, 接口原始返回文本
    :return: pd.DataFrame, 解析后的表格数据
    """
    rows = [x.split(",") for x in text.strip().split("\n")]
    df = pd.DataFrame(rows[1:], columns=rows[0])
    return df


def get_query_count() -> int:
    """获取当前账号剩余的查询条数。

    用于在大批量查询前先判断额度是否充足，避免中途被限流中断。

    接口文档: https://dataapi.joinquant.com/docs#get_query_count---%E8%8E%B7%E5%8F%96%E6%9F%A5%E8%AF%A2%E5%89%A9%E4%BD%99%E6%9D%A1%E6%95%B0

    :return: int, 当前剩余可用的查询条数
    """
    data = {
        "method": "get_query_count",
        "token": get_token(),
    }
    r = requests.post(url, data=json.dumps(data))
    return int(r.text)


def get_concepts():
    """获取聚宽全部概念板块列表。

    接口文档:
        https://dataapi.joinquant.com/docs#get_concepts---%E8%8E%B7%E5%8F%96%E6%A6%82%E5%BF%B5%E5%88%97%E8%A1%A8

    :return: pd.DataFrame, 包含概念代码、名称等字段
    """
    data = {
        "method": "get_concepts",
        "token": get_token(),
    }
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    return df


def get_concept_stocks(symbol, date=None):
    """获取指定概念在指定日期下的成份股代码列表。

    接口文档:
        https://dataapi.joinquant.com/docs#get_concept_stocks---%E8%8E%B7%E5%8F%96%E6%A6%82%E5%BF%B5%E6%88%90%E4%BB%BD%E8%82%A1

    :param symbol: str, 概念代码，如 ``GN036``
    :param date: str | datetime, 日期，如 ``2020-08-08``；为空时使用当前日期
    :return: list[str], 该日期下的成份股代码列表（含交易所后缀）

    示例：
        >>> symbols1 = get_concept_stocks("GN036", date="2020-07-08")
        >>> symbols2 = get_concept_stocks("GN036", date=datetime.now())
    """
    if not date:
        date = str(datetime.now().date())
    else:
        date = pd.to_datetime(date)

    if isinstance(date, datetime):
        date = str(date.date())

    data = {"method": "get_concept_stocks", "token": get_token(), "code": symbol, "date": date}
    r = requests.post(url, data=json.dumps(data))
    return r.text.split("\n")


def get_index_stocks(symbol, date=None):
    """获取指定指数在指定日期的成份股代码列表。

    接口文档:
        https://dataapi.joinquant.com/docs#get_index_stocks---%E8%8E%B7%E5%8F%96%E6%8C%87%E6%95%B0%E6%88%90%E4%BB%BD%E8%82%A1

    :param symbol: str, 指数代码，如 ``000300.XSHG``
    :param date: str | datetime, 日期，如 ``2020-08-08``；为空时使用当前日期
    :return: list[str], 指定日期下的成份股代码列表

    示例：
        >>> symbols1 = get_index_stocks("000300.XSHG", date="2020-07-08")
        >>> symbols2 = get_index_stocks("000300.XSHG", date=datetime.now())
    """
    if not date:
        date = str(datetime.now().date())

    if isinstance(date, datetime):
        date = str(date.date())

    data = {"method": "get_index_stocks", "token": get_token(), "code": symbol, "date": date}
    r = requests.post(url, data=json.dumps(data))
    return r.text.split("\n")


def get_industry(symbol):
    """查询股票所属的行业归属信息。

    一次性返回证监会、聚宽（一级、二级）、申万（一级、二级、三级）共三套行业分类，
    便于上层根据需要选择对应分类体系做横截面分析。

    接口文档:
        https://www.joinquant.com/help/api/help#JQDataHttp:get_industry-%E6%9F%A5%E8%AF%A2%E8%82%A1%E7%A5%A8%E6%89%80%E5%B1%9E%E8%A1%8C%E4%B8%9A

    :param symbol: str, 股票代码，含交易所后缀，例如 ``000001.XSHE``
    :return: dict, 包含股票代码、各行业分类的代码和名称
    """
    data = {"method": "get_industry", "token": get_token(), "code": symbol, "date": str(datetime.now().date())}
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    # 把不同分类体系（zjw/jq_l1/jq_l2/sw_l1/sw_l2/sw_l3）的行业代码与名称分别提取出来
    res = {
        "股票代码": symbol,
        "证监会行业代码": df[df["industry"] == "zjw"]["industry_code"].iloc[0],
        "证监会行业名称": df[df["industry"] == "zjw"]["industry_name"].iloc[0],
        "聚宽一级行业代码": df[df["industry"] == "jq_l1"]["industry_code"].iloc[0],
        "聚宽一级行业名称": df[df["industry"] == "jq_l1"]["industry_name"].iloc[0],
        "聚宽二级行业代码": df[df["industry"] == "jq_l2"]["industry_code"].iloc[0],
        "聚宽二级行业名称": df[df["industry"] == "jq_l2"]["industry_name"].iloc[0],
        "申万一级行业代码": df[df["industry"] == "sw_l1"]["industry_code"].iloc[0],
        "申万一级行业名称": df[df["industry"] == "sw_l1"]["industry_name"].iloc[0],
        "申万二级行业代码": df[df["industry"] == "sw_l2"]["industry_code"].iloc[0],
        "申万二级行业名称": df[df["industry"] == "sw_l2"]["industry_name"].iloc[0],
        "申万三级行业代码": df[df["industry"] == "sw_l3"]["industry_code"].iloc[0],
        "申万三级行业名称": df[df["industry"] == "sw_l3"]["industry_name"].iloc[0],
    }
    return res


def get_all_securities(code, date=None) -> pd.DataFrame:
    """获取平台支持的所有标的基础信息。

    接口文档:
        https://dataapi.joinquant.com/docs#get_all_securities---%E8%8E%B7%E5%8F%96%E6%89%80%E6%9C%89%E6%A0%87%E7%9A%84%E4%BF%A1%E6%81%AF

    :param code: str, 证券类型，可选值：stock, fund, index, futures, etf, lof, fja, fjb,
                 QDII_fund, open_fund, bond_fund, stock_fund, money_market_fund, mixture_fund, options
    :param date: str | datetime, 日期，用于获取某日期还在上市的证券信息；为空时表示获取所有日期的标的信息
    :return: pd.DataFrame, 标的基础信息表
    """
    if not date:
        date = str(datetime.now().date())

    if isinstance(date, datetime):
        date = str(date.date())

    data = {"method": "get_all_securities", "token": get_token(), "code": code, "date": date}
    r = requests.post(url, data=json.dumps(data))
    return text2df(r.text)


def get_kline(
    symbol: str, end_date: [datetime, str], freq: str, start_date: [datetime, str] = None, count=None, fq: bool = True
) -> List[RawBar]:
    """获取 K 线数据并转换为 ``RawBar`` 列表。

    支持两种调用模式：
        - 指定 ``start_date`` + ``end_date``：调用 ``get_price_period`` 获取区间数据；
        - 指定 ``count`` + ``end_date``：调用 ``get_price`` 倒推获取最近 N 根。
    两者必须二选一。

    接口文档:
        https://www.joinquant.com/help/api/help#JQDataHttp:get_priceget_bars-%E8%8E%B7%E5%8F%96%E6%8C%87%E5%AE%9A%E6%97%B6%E9%97%B4%E5%91%A8%E6%9C%9F%E7%9A%84%E8%A1%8C%E6%83%85%E6%95%B0%E6%8D%AE

    :param symbol: str, 聚宽标的代码，例如 ``000001.XSHG``
    :param end_date: str | datetime, 截止日期
    :param freq: str, K 线级别，可选值 ``['1min', '5min', '30min', '60min', 'D', 'W', 'M']``
    :param start_date: str | datetime, 可选, 开始日期
    :param count: int, 可选, 从 end_date 倒推的 K 线数量，最大 5000
    :param fq: bool, 是否进行复权，True 时使用 end_date 作为复权基准
    :return: list[RawBar], 标准化后的 K 线对象列表（按时间升序）
    :raises ValueError: ``start_date`` 和 ``count`` 同时为空时抛出

    示例：
        >>> start_date = datetime.strptime("20200701", "%Y%m%d")
        >>> end_date = datetime.strptime("20200719", "%Y%m%d")
        >>> df1 = get_kline(symbol="000001.XSHG", start_date=start_date, end_date=end_date, freq="1min")
        >>> df2 = get_kline(symbol="000001.XSHG", end_date=end_date, freq="1min", count=1000)
        >>> df3 = get_kline(symbol="000001.XSHG", start_date='20200701', end_date='20200719', freq="1min", fq=True)
        >>> df4 = get_kline(symbol="000001.XSHG", end_date='20200719', freq="1min", count=1000)
    """
    if count and count > 5000:
        warnings.warn(f"count={count}, 超过5000的最大值限制，仅返回最后5000条记录")

    end_date = pd.to_datetime(end_date)

    # 根据是否提供 start_date 选择不同的接口：区间查询 vs 倒数 N 根
    if start_date:
        start_date = pd.to_datetime(start_date)
        data = {
            "method": "get_price_period",
            "token": get_token(),
            "code": symbol,
            "unit": freq_convert[freq],
            "date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
    elif count:
        data = {
            "method": "get_price",
            "token": get_token(),
            "code": symbol,
            "count": count,
            "unit": freq_convert[freq],
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
    else:
        raise ValueError("start_date 和 count 不能同时为空")

    if fq:
        # 指定复权基准日期，与 end_date 保持一致
        data.update({"fq_ref_date": end_date.strftime("%Y-%m-%d")})

    r = requests.post(url, data=json.dumps(data))
    # 接口返回 CSV 文本，跳过第一行表头，逐行解析
    rows = [x.split(",") for x in r.text.strip().split("\n")][1:]

    bars = []
    i = -1
    for row in rows:
        # 字段顺序：['date', 'open', 'close', 'high', 'low', 'volume', 'money']
        dt = pd.to_datetime(row[0])
        if freq == "D":
            # 日线统一规整为 00:00:00，避免出现非零的小时/分钟字段
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # 仅保留有成交量的 K 线，跳过停牌或集合竞价残留的空行
        if int(row[5]) > 0:
            i += 1
            bars.append(
                RawBar(
                    symbol=symbol,
                    dt=dt,
                    id=i,
                    freq=freq_map[freq],
                    open=round(float(row[1]), 4),
                    close=round(float(row[2]), 4),
                    high=round(float(row[3]), 4),
                    low=round(float(row[4]), 4),
                    vol=int(row[5]),
                    amount=int(float(row[6])),
                )
            )
            # amount 单位：元
    if start_date:
        # 双重保险：再次按 start_date 过滤，避免接口返回的边界数据
        bars = [x for x in bars if x.dt >= start_date]
    if "min" in freq:
        # 分钟线最后一根使用区间结束时间对齐，便于与 czsc 内部时间约定保持一致
        bars[-1].dt = freq_end_time(bars[-1].dt, freq=freq_map[freq])
    bars = [x for x in bars if x.dt <= end_date]
    return bars


def get_kline_period(
    symbol: str, start_date: [datetime, str], end_date: [datetime, str], freq: str, fq=True
) -> List[RawBar]:
    """获取指定时间段的行情数据（仅区间模式，固定使用 ``get_price_period``）。

    与 ``get_kline`` 的区别：本函数强制使用 start_date + end_date，对超长区间会发出告警。

    接口文档:
        https://www.joinquant.com/help/api/help#JQDataHttp:get_price_periodget_bars_period-%E8%8E%B7%E5%8F%96%E6%8C%87%E5%AE%9A%E6%97%B6%E9%97%B4%E6%AE%B5%E7%9A%84%E8%A1%8C%E6%83%85%E6%95%B0%E6%8D%AE

    :param symbol: str, 聚宽标的代码
    :param start_date: str | datetime, 开始日期
    :param end_date: str | datetime, 截止日期
    :param freq: str, K 线级别，可选值 ``['1min', '5min', '30min', '60min', 'D', 'W', 'M']``
    :param fq: bool, 是否进行复权
    :return: list[RawBar], 标准化后的 K 线对象列表
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # 粗略估算：(自然日 * 5/7) 近似得到交易日数；超 1000 个交易日可能触发服务端限制
    if (end_date - start_date).days * 5 / 7 > 1000:
        warnings.warn(f"{end_date.date()} - {start_date.date()} 超过1000个交易日，K线获取可能失败，返回为0")

    data = {
        "method": "get_price_period",
        "token": get_token(),
        "code": symbol,
        "unit": freq_convert[freq],
        "date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
    }
    if fq:
        data.update({"fq_ref_date": end_date.strftime("%Y-%m-%d")})

    r = requests.post(url, data=json.dumps(data))
    rows = [x.split(",") for x in r.text.strip().split("\n")][1:]
    bars = []
    i = -1
    for row in rows:
        # 字段顺序：['date', 'open', 'close', 'high', 'low', 'volume', 'money']
        dt = pd.to_datetime(row[0])
        if freq == "D":
            dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

        # 跳过无成交量的行
        if int(row[5]) > 0:
            i += 1
            bars.append(
                RawBar(
                    symbol=symbol,
                    dt=dt,
                    id=i,
                    freq=freq_map[freq],
                    open=round(float(row[1]), 4),
                    close=round(float(row[2]), 4),
                    high=round(float(row[3]), 4),
                    low=round(float(row[4]), 4),
                    vol=int(row[5]),
                    amount=int(float(row[6])),
                )
            )
            # amount 单位：元
    if start_date:
        bars = [x for x in bars if x.dt >= start_date]
    if "min" in freq and bars:
        # 分钟线对齐到周期结束时间
        bars[-1].dt = freq_end_time(bars[-1].dt, freq=freq_map[freq])
    bars = [x for x in bars if x.dt <= end_date]
    return bars


def get_init_bg(symbol: str, end_dt: [str, datetime], base_freq: str, freqs: List[str], max_count=1000, fq=True):
    """获取指定标的的初始化 BarGenerator 以及待重放数据。

    用于实时回放/回测的启动阶段：
        1. 以 ``end_dt - 180 天`` 为分界点，先拉取该时点之前的 K 线，初始化 BarGenerator；
        2. 再拉取从分界点到 ``end_dt`` 的基础周期 K 线，作为后续逐根 update 的回放数据。

    :param symbol: str, 聚宽标的代码
    :param end_dt: str | datetime, 回放的截止时间
    :param base_freq: str, 基础周期（CZSC 中文表达，如 "1分钟"）
    :param freqs: list[str], 需要联立的更高级别周期列表
    :param max_count: int, 各级别 K 线初始化时的最大根数，默认 1000
    :param fq: bool, 是否复权，默认 True（前复权）
    :return: tuple, (bg, data)
             - bg: BarGenerator, 已初始化好的 BarGenerator 实例
             - data: list[RawBar], 待逐根 update 的基础周期数据
    """
    if isinstance(end_dt, str):
        end_dt = pd.to_datetime(end_dt, utc=False)

    # 以 180 天为初始化窗口，分界点设在当天的 16:00（A 股收盘后）
    delta_days = 180
    last_day = (end_dt - timedelta(days=delta_days)).replace(hour=16, minute=0)

    bg = BarGenerator(base_freq, freqs, max_count)
    # 对 BarGenerator 中维护的每一个频率，分别拉取并初始化
    for freq in bg.bars.keys():
        bars_ = get_kline(symbol=symbol, end_date=last_day, freq=freq_cn2jq[freq], count=max_count, fq=fq)
        bg.init_freq_bars(freq, bars_)
        print(f"{symbol} - {freq} - {len(bg.bars[freq])} - last_dt: {bg.bars[freq][-1].dt} - last_day: {last_day}")

    # 准备分界点之后的基础周期数据，供后续 bg.update 逐根回放
    bars2 = get_kline_period(symbol, last_day, end_dt, freq=freq_cn2jq[base_freq], fq=fq)
    data = [x for x in bars2 if x.dt > last_day]
    assert len(data) > 0
    print(
        f"{symbol}: bar generator 最新时间 {bg.bars[base_freq][-1].dt.strftime(dt_fmt)}，还有{len(data)}行数据需要update"
    )
    return bg, data


def get_fundamental(table: str, symbol: str, date: str, columns: str = "") -> dict:
    """获取单个标的、指定日期的财务基础数据。

    接口文档:
        https://dataapi.joinquant.com/docs#get_fundamentals---%E8%8E%B7%E5%8F%96%E5%9F%BA%E6%9C%AC%E8%B4%A2%E5%8A%A1%E6%95%B0%E6%8D%AE

    财务数据列表:
        https://www.joinquant.com/help/api/help?name=Stock#%E8%B4%A2%E5%8A%A1%E6%95%B0%E6%8D%AE%E5%88%97%E8%A1%A8

    :param table: str, 财务数据表名，如 ``indicator``、``valuation``
    :param symbol: str, 股票代码
    :param date: str, 查询日期，可以是：
                 - 具体日期 ``2019-03-04``；
                 - 年度 ``2018``；
                 - 季度 ``2018q1`` / ``2018q2`` / ``2018q3`` / ``2018q4``
    :param columns: str, 可选, 需要查询的字段列表，逗号分隔；为空则查询全部字段
    :return: dict, 单条记录的字典；查询失败或为空时返回 ``{}``

    示例：
        >>> x1 = get_fundamental(table="indicator", symbol="300803.XSHE", date="2020-11-12")
        >>> x2 = get_fundamental(table="indicator", symbol="300803.XSHE", date="2020")
        >>> x3 = get_fundamental(table="indicator", symbol="300803.XSHE", date="2020q3")
    """
    data = {
        "method": "get_fundamentals",
        "token": get_token(),
        "table": table,
        "columns": columns,
        "code": symbol,
        "date": date,
        "count": 1,
    }
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    try:
        return df.iloc[0].to_dict()
    except:
        # 兼容数据为空、列缺失等多种异常，统一返回空字典
        return {}


def run_query(table: str, conditions: str, columns=None, count=1):
    """模拟 JQDataSDK 的 run_query 方法，按条件查询数据库表。

    接口文档:
        https://www.joinquant.com/help/api/help#JQDataHttp:run_query-%E6%A8%A1%E6%8B%9FJQDataSDK%E7%9A%84run_query%E6%96%B9%E6%B3%95

    :param table: str, 要查询的数据库和表名，格式为 ``database.tablename``，如 ``finance.STK_XR_XD``
    :param conditions: str, 查询条件，可以为空。
                       格式：``column # 判断符 # value``，多个条件用 ``&`` 分隔表示 AND，
                       例如：``report_date#>=#2006-12-01&report_date#<=#2006-12-31``。
                       注意条件字符串内不能包含空格等特殊字符。
    :param columns: str, 可选, 所查字段，多个字段用 ``,`` 分隔；为空则查询所有字段。
                    同样不能包含空格。
    :param count: int, 返回的最大记录数，默认 1
    :return: pd.DataFrame, 查询结果
    """
    data = {"method": "run_query", "token": get_token(), "table": table, "conditions": conditions, "count": count}
    if columns:
        data["columns"] = columns
    r = requests.post(url, data=json.dumps(data))
    df = text2df(r.text)
    return df


def get_share_basic(symbol):
    """获取单个标的的基本面汇总数据（一站式 F10 信息）。

    本函数会聚合公司基础信息、估值（PE/PB）、市值、近 4 年关键财务指标等，
    返回一个有序字典，并附带可直接推送的中文摘要文本（``msg`` 字段）。

    :param symbol: str, 股票代码（含交易所后缀），例如 ``000001.XSHE``
    :return: collections.OrderedDict, 基础面汇总信息
    """
    # 公司基础信息：股票名称、所属行业、地域、主营业务等
    basic_info = run_query(table="finance.STK_COMPANY_INFO", conditions="code#=#{}".format(symbol), count=1)
    basic_info = basic_info.iloc[0].to_dict()

    f10 = OrderedDict()
    f10["股票代码"] = basic_info["code"]
    f10["股票名称"] = basic_info["short_name"]
    f10["行业"] = "{}-{}".format(basic_info["industry_1"], basic_info["industry_2"])
    f10["地域"] = "{}{}".format(basic_info["province"], basic_info["city"])
    f10["主营"] = basic_info["main_business"]
    f10["同花顺F10"] = "http://basic.10jqka.com.cn/{}".format(basic_info["code"][:6])

    # 市盈率、总市值、流通市值、流通比
    # ------------------------------------------------------------------------------------------------------------------
    # 用昨日数据避免今日盘中估值跳变；valuation 表中的市值单位为亿元
    last_date = datetime.now() - timedelta(days=1)
    res = get_fundamental(table="valuation", symbol=symbol, date=last_date.strftime("%Y-%m-%d"))
    f10["总市值（亿）"] = float(res["market_cap"])
    f10["流通市值（亿）"] = float(res["circulating_market_cap"])
    f10["流通比（%）"] = round(float(res["circulating_market_cap"]) / float(res["market_cap"]) * 100, 2)
    f10["PE_TTM"] = float(res["pe_ratio"])
    f10["PE"] = float(res["pe_ratio_lyr"])
    f10["PB"] = float(res["pb_ratio"])

    # 近 4 年财务指标：净资产收益率、利润率、增长率、现金流等
    # ------------------------------------------------------------------------------------------------------------------
    for year in ["2017", "2018", "2019", "2020"]:
        indicator = get_fundamental(table="indicator", symbol=symbol, date=year)
        # indicator.get(key, 0) 可能返回 None 或空字符串，因此再做一次真值判断后再转 float
        f10["{}EPS".format(year)] = float(indicator.get("eps", 0)) if indicator.get("eps", 0) else 0
        f10["{}ROA".format(year)] = float(indicator.get("roa", 0)) if indicator.get("roa", 0) else 0
        f10["{}ROE".format(year)] = float(indicator.get("roe", 0)) if indicator.get("roe", 0) else 0
        f10["{}销售净利率(%)".format(year)] = (
            float(indicator.get("net_profit_margin", 0)) if indicator.get("net_profit_margin", 0) else 0
        )
        f10["{}销售毛利率(%)".format(year)] = (
            float(indicator.get("gross_profit_margin", 0)) if indicator.get("gross_profit_margin", 0) else 0
        )
        f10["{}营业收入同比增长率(%)".format(year)] = (
            float(indicator.get("inc_revenue_year_on_year", 0)) if indicator.get("inc_revenue_year_on_year", 0) else 0
        )
        f10["{}营业收入环比增长率(%)".format(year)] = (
            float(indicator.get("inc_revenue_annual", 0)) if indicator.get("inc_revenue_annual", 0) else 0
        )
        f10["{}营业利润同比增长率(%)".format(year)] = (
            float(indicator.get("inc_operation_profit_year_on_year", 0))
            if indicator.get("inc_operation_profit_year_on_year", 0)
            else 0
        )
        f10["{}经营活动产生的现金流量净额/营业收入(%)".format(year)] = (
            float(indicator.get("ocf_to_revenue", 0)) if indicator.get("ocf_to_revenue", 0) else 0
        )

    # 组合成可以用来推送的文本摘要
    msg = "{}（{}）@{}\n".format(f10["股票代码"], f10["股票名称"], f10["地域"])
    msg += "\n{}\n".format("*" * 30)
    for k in ["行业", "主营", "PE_TTM", "PE", "PB", "总市值（亿）", "流通市值（亿）", "流通比（%）", "同花顺F10"]:
        msg += "{}：{}\n".format(k, f10[k])

    msg += "\n{}\n".format("*" * 30)
    cols = [
        "EPS",
        "ROA",
        "ROE",
        "销售净利率(%)",
        "销售毛利率(%)",
        "营业收入同比增长率(%)",
        "营业利润同比增长率(%)",
        "经营活动产生的现金流量净额/营业收入(%)",
    ]
    msg += "2017~2020 财务变化\n\n"
    for k in cols:
        # 把 4 年同一指标横向拼接，便于一眼看出趋势
        msg += k + "：{} | {} | {} | {}\n".format(
            *[f10["{}{}".format(year, k)] for year in ["2017", "2018", "2019", "2020"]]
        )

    f10["msg"] = msg
    return f10


def get_symbols(name="ALL", **kwargs):
    """获取指定分组下的所有标的代码（聚宽数据源）。

    :param name: str, 分组名称，可选值：
                 - ``ALL``：表示 stock + index + futures + etf 的并集；
                 - 也可直接传入聚宽支持的具体类型：stock, fund, index, futures, etf, lof,
                   fja, fjb, QDII_fund, open_fund, bond_fund, stock_fund,
                   money_market_fund, mixture_fund, options
    :param kwargs: dict, 其他参数（保留以扩展，当前未使用）
    :return: list[str], 该分组下的所有标的代码列表
    """
    if name.upper() == "ALL":
        # ALL 分支：聚合 stock + index + futures + etf 四类标的
        codes = (
            get_all_securities("stock", date=None)["code"].unique().tolist()
            + get_all_securities("index", date=None)["code"].unique().tolist()
            + get_all_securities("futures", date=None)["code"].unique().tolist()
            + get_all_securities("etf", date=None)["code"].unique().tolist()
        )
    else:
        codes = get_all_securities(name, date=None)["code"].unique().tolist()
    return codes


def get_raw_bars(symbol, freq, sdt, edt, fq="前复权", **kwargs):
    """获取 CZSC 库定义的标准 RawBar 对象列表（聚宽数据源统一入口）。

    本函数将 CZSC 内部使用的中文周期字符串映射为聚宽的 pandas-style 频率字符串，
    并代理调用 ``get_kline``。复权方向通过 ``fq`` 参数指定。

    :param symbol: str, 标的代码
    :param freq: str | czsc.Freq, 周期，支持 Freq 对象，或者字符串：
                 ``'1分钟'``、``'5分钟'``、``'15分钟'``、``'30分钟'``、``'60分钟'``、
                 ``'日线'``、``'周线'``、``'月线'``、``'季线'``、``'年线'``
    :param sdt: str | datetime, 开始时间
    :param edt: str | datetime, 结束时间
    :param fq: str, 除权类型，可选 ``"前复权"``、``"后复权"``、``"不复权"``。
               注意：投研共享数据默认都是后复权，不需要再处理
    :param kwargs: dict, 其他参数（保留以扩展，当前未使用）
    :return: list[RawBar], K 线对象列表
    """
    kwargs["fq"] = fq
    freq = str(freq)
    # 仅 "前复权" 时设为 True，其他统一为 False
    fq = True if fq == "前复权" else False
    # CZSC 中文频率到聚宽 pandas-style 频率字符串的映射
    _map = {
        "1分钟": "1min",
        "5分钟": "5min",
        "15分钟": "15min",
        "30分钟": "30min",
        "60分钟": "60min",
        "日线": "D",
        "周线": "W",
        "月线": "M",
    }
    return get_kline(symbol, freq=_map[freq], start_date=sdt, end_date=edt, fq=fq)
