# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/3/7 18:49
describe: 对接天勤量化

1. [使用 tqsdk 进行期货交易](https://s0cqcxuy3p.feishu.cn/wiki/wikcn41lQIAJ1f8v41Dj5eAmrub)
2. [使用 tqsdk 查看期货实时行情](https://s0cqcxuy3p.feishu.cn/wiki/SH3mwOU6piPqnGkRRiocQrhAnrh)
"""
import czsc
import pandas as pd
from loguru import logger
from typing import List, Union, Optional
from datetime import date, datetime, timedelta
from czsc import Freq, RawBar
from tqsdk import TqApi, TqAuth, TqSim, TqBacktest, TargetPosTask, BacktestFinished, TqAccount, TqKq  # noqa


# https://doc.shinnytech.com/tqsdk/latest/usage/mddatas.html 代码规则
symbols = [
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/SHFE
    "KQ.m@SHFE.rb",
    "KQ.m@SHFE.fu",
    "KQ.m@SHFE.ag",
    "KQ.m@SHFE.hc",
    "KQ.m@SHFE.sp",
    "KQ.m@SHFE.ru",
    "KQ.m@SHFE.bu",
    "KQ.m@SHFE.ni",
    "KQ.m@SHFE.ss",
    "KQ.m@SHFE.au",
    "KQ.m@SHFE.sn",
    "KQ.m@SHFE.al",
    "KQ.m@SHFE.zn",
    "KQ.m@SHFE.cu",
    "KQ.m@SHFE.pb",
    "KQ.m@SHFE.wr",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/CZCE
    "KQ.m@CZCE.SA",
    "KQ.m@CZCE.FG",
    "KQ.m@CZCE.TA",
    "KQ.m@CZCE.MA",
    "KQ.m@CZCE.RM",
    "KQ.m@CZCE.CF",
    "KQ.m@CZCE.OI",
    "KQ.m@CZCE.SR",
    "KQ.m@CZCE.UR",
    "KQ.m@CZCE.PF",
    "KQ.m@CZCE.AP",
    "KQ.m@CZCE.SF",
    "KQ.m@CZCE.PK",
    "KQ.m@CZCE.SM",
    "KQ.m@CZCE.RS",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/DCE
    "KQ.m@DCE.m",
    "KQ.m@DCE.p",
    "KQ.m@DCE.i",
    "KQ.m@DCE.v",
    "KQ.m@DCE.y",
    "KQ.m@DCE.eg",
    "KQ.m@DCE.c",
    "KQ.m@DCE.pp",
    "KQ.m@DCE.l",
    "KQ.m@DCE.cs",
    "KQ.m@DCE.a",
    "KQ.m@DCE.eb",
    "KQ.m@DCE.jm",
    "KQ.m@DCE.b",
    "KQ.m@DCE.pg",
    "KQ.m@DCE.jd",
    "KQ.m@DCE.j",
    "KQ.m@DCE.lh",
    "KQ.m@DCE.rr",
    "KQ.m@DCE.fb",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/GFEX
    "KQ.m@GFEX.si",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/INE
    "KQ.m@INE.lu",
    "KQ.m@INE.sc",
    "KQ.m@INE.nr",
    "KQ.m@INE.bc",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/CFFEX
    "KQ.m@CFFEX.T",
    "KQ.m@CFFEX.TF",
    "KQ.m@CFFEX.IF",
    "KQ.m@CFFEX.IC",
    "KQ.m@CFFEX.IH",
    "KQ.m@CFFEX.IM",
    "KQ.m@CFFEX.TS",
]


future_name_map = {
    "PG": "LPG",
    "EB": "苯乙烯",
    "CS": "玉米淀粉",
    "C": "玉米",
    "V": "PVC",
    "J": "焦炭",
    "BB": "胶合板",
    "M": "豆粕",
    "A": "豆一",
    "PP": "聚丙烯",
    "P": "棕榈油",
    "FB": "纤维板",
    "B": "豆二",
    "JD": "鸡蛋",
    "JM": "焦煤",
    "L": "塑料",
    "I": "铁矿石",
    "Y": "豆油",
    "RR": "粳米",
    "EG": "乙二醇",
    "LH": "生猪",
    "CJ": "红枣",
    "UR": "尿素",
    "TA": "PTA",
    "OI": "菜油",
    "MA": "甲醇",
    "RS": "菜籽",
    "ZC": "动力煤",
    "LR": "晚籼稻",
    "PM": "普麦",
    "SR": "白糖",
    "RI": "早籼稻",
    "SF": "硅铁",
    "WH": "强麦",
    "JR": "粳稻",
    "SM": "锰硅",
    "FG": "玻璃",
    "CF": "棉花",
    "RM": "菜粕",
    "PF": "短纤",
    "AP": "苹果",
    "CY": "棉纱",
    "ER": "早籼稻",
    "ME": "甲醇",
    "RO": "菜油",
    "TC": "动力煤",
    "WS": "强麦",
    "WT": "硬麦",
    "SA": "纯碱",
    "PK": "花生",
    "SS": "不锈钢",
    "AL": "沪铝",
    "CU": "沪铜",
    "ZN": "沪锌",
    "AG": "白银",
    "RB": "螺纹钢",
    "SN": "沪锡",
    "NI": "沪镍",
    "WR": "线材",
    "FU": "燃油",
    "AU": "黄金",
    "PB": "沪铅",
    "RU": "橡胶",
    "HC": "热轧卷板",
    "BU": "沥青",
    "SP": "纸浆",
    "NR": "20号胶",
    "SC": "原油",
    "LU": "低硫燃料油",
    "BC": "国际铜",
    "SCTAS": "原油TAS指令",
    "SI": "工业硅",
}


def get_symbols(**kwargs):
    return symbols


def get_raw_bars(symbol, freq, sdt, edt, fq="前复权", **kwargs):
    """获取 CZSC 库定义的标准 RawBar 对象列表

    **注意：** 免费账户只能获取 8000 根K线数据，如果需要更多数据，请购买天勤账户

    :param symbol: 标的代码
    :param freq: 周期，支持 Freq 对象，或者字符串，如
            '1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线'
    :param sdt: 开始时间
    :param edt: 结束时间
    :param fq: 除权类型，可选值：'前复权', '后复权', '不复权'
    :param kwargs:

        - tq_user: str, 天勤账户
        - tq_pass: str, 天勤密码
        - raw_bars: bool, 是否返回 RawBar 对象列表，默认为 True

    :return: RawBar 对象列表 or DataFrame
    """
    freq = czsc.Freq(freq)

    api = TqApi(auth=TqAuth(user_name=kwargs["tq_user"], password=kwargs["tq_pass"]), web_gui=False)
    if freq.value == "日线":
        duration_seconds = 86400
    else:
        assert "分钟" in freq.value, f"未知的周期：{freq.value}"
        duration_seconds = int(freq.value.replace("分钟", "")) * 60

    fq_map = {"前复权": "F", "后复权": "B", "不复权": None}

    df = api.get_kline_serial(symbol, duration_seconds=duration_seconds, data_length=8000, adj_type=fq_map[fq])
    df["dt"] = pd.to_datetime(df["datetime"], unit="ns", utc=True).dt.tz_convert("Asia/Shanghai").dt.tz_localize(None)
    df["dt"] = df["dt"] + timedelta(seconds=duration_seconds)
    df.rename(columns={"volume": "vol"}, inplace=True)
    df["amount"] = df["vol"] * df["close"]
    df = df[["symbol", "dt", "open", "close", "high", "low", "vol", "amount"]].copy()

    df = df[(df["dt"] >= pd.to_datetime(sdt)) & (df["dt"] <= pd.to_datetime(edt))].reset_index(drop=True)
    return czsc.resample_bars(df, target_freq=freq, raw_bars=kwargs.get("raw_bars", True))


def get_daily_backup(api: TqApi, **kwargs):
    """获取每日账户中需要备份的信息

    https://doc.shinnytech.com/tqsdk/latest/reference/tqsdk.objs.html?highlight=account#tqsdk.objs.Order
    https://doc.shinnytech.com/tqsdk/latest/reference/tqsdk.objs.html?highlight=account#tqsdk.objs.Position
    https://doc.shinnytech.com/tqsdk/latest/reference/tqsdk.objs.html?highlight=account#tqsdk.objs.Account

    :param api: TqApi, 天勤API实例
    """
    orders = api.get_order()
    trades = api.get_trade()
    position = api.get_position()
    account = api.get_account()

    order_ids = [x for x in list(orders.__dict__.keys()) if x not in ["_data", "_path", "_listener"]]
    orders = pd.DataFrame([orders.__dict__[x] for x in order_ids])

    trade_ids = [x for x in list(trades.__dict__.keys()) if x not in ["_data", "_path", "_listener"]]
    trades = pd.DataFrame([trades.__dict__[x] for x in trade_ids])

    position_ids = [x for x in list(position.__dict__.keys()) if x not in ["_data", "_path", "_listener"]]
    positions = pd.DataFrame([position.__dict__[x] for x in position_ids])

    account_ids = [x for x in list(account.__dict__.keys()) if x not in ["_data", "_path", "_listener", "_api"]]
    account = {x: account.__dict__[x] for x in account_ids}

    backup = {
        "orders": orders,
        "trades": trades,
        "positions": positions,
        "account": account,
    }
    return backup


def is_trade_time(quote):
    """判断当前是否是交易时间"""
    trade_time = pd.Timestamp.now().strftime("%H:%M:%S")
    times = quote["trading_time"]["day"] + quote["trading_time"]["night"]

    for sdt, edt in times:
        if trade_time >= sdt and trade_time <= edt:
            logger.info(f"当前时间：{trade_time}，交易时间：{sdt} - {edt}")
            return True
    return False


def adjust_portfolio(api: TqApi, portfolio, account=None, **kwargs):
    """调整账户组合

    **注意：** 此函数会阻塞，直到调仓完成；使用前请仔细阅读 TargetPosTask 的源码和文档，确保了解其工作原理

    :param api: TqApi, 天勤API实例
    :param account: str, 天勤账户
    :param portfolio: dict, 组合配置，key 为合约代码，value 为配置信息; 样例数据：

        {
            "KQ.m@CFFEX.T": {"target_volume": 10, "price": "PASSIVE", "offset_priority": "今昨,开"},
            "KQ.m@CFFEX.TS": {"target_volume": 0, "price": "ACTIVE", "offset_priority": "今昨,开"},
            "KQ.m@CFFEX.TF": {"target_volume": 30, "price": "PASSIVE", "offset_priority": "今昨,开"}
        }

    :param kwargs: dict, 其他参数
    """
    timeout = kwargs.get("timeout", 600)
    start_time = datetime.now()

    symbol_infos = {}
    for symbol, conf in portfolio.items():
        quote = api.get_quote(symbol)
        if not is_trade_time(quote):
            logger.warning(f"{symbol} 当前时间不是交易时间，跳过调仓")
            continue

        lots = conf.get("target_volume", None)
        if lots is None:
            logger.warning(f"{symbol} 目标手数为 None，跳过调仓")
            continue

        price = conf.get("price", "PASSIVE")
        offset_priority = conf.get("offset_priority", "今昨,开")

        # 踩坑记录：TargetPosTask 的 symbol 必须是合约代码
        contract = quote.underlying_symbol if "@" in symbol else symbol
        target_pos = TargetPosTask(api, contract, price=price, offset_priority=offset_priority, account=account)
        target_pos.set_target_volume(int(lots))
        symbol_infos[symbol] = {"quote": quote, "target_pos": target_pos, "lots": lots}

    while True:
        api.wait_update()

        completed = []
        for symbol, info in symbol_infos.items():
            quote = info["quote"]
            target_pos: TargetPosTask = info["target_pos"]
            lots = info["lots"]
            contract = quote.underlying_symbol if "@" in symbol else symbol

            logger.info(
                f"调整仓位：{quote.datetime} - {contract}; 目标持仓：{lots}手; 当前持仓：{target_pos._pos.pos}手"
            )

            if target_pos._pos.pos == lots or target_pos.is_finished():
                completed.append(True)
                logger.info(
                    f"调仓完成：{quote.datetime} - {contract}; 目标持仓：{lots}手; 当前持仓：{target_pos._pos.pos}手"
                )
            else:
                completed.append(False)

        if all(completed):
            break

        if (datetime.now() - start_time).seconds > timeout:
            logger.error(f"调仓超时，已运行 {timeout} 秒")
            break

    return api
