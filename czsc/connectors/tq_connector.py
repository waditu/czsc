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
import loguru
import pandas as pd
from datetime import datetime, timedelta
from czsc import Freq, RawBar
from tqsdk import TqApi, TqAuth, TqSim, TqBacktest, TargetPosTask, BacktestFinished, TqAccount, TqKq  # noqa


def format_kline(df, freq=Freq.F1):
    """对分钟K线进行格式化"""
    freq = Freq(freq)
    rows = df.to_dict("records")
    raw_bars = []
    for i, row in enumerate(rows):
        bar = RawBar(
            symbol=row["symbol"],
            id=i,
            freq=freq,
            dt=datetime.fromtimestamp(row["datetime"] / 1e9) + timedelta(minutes=1),
            open=row["open"],
            close=row["close"],
            high=row["high"],
            low=row["low"],
            vol=row["volume"],
            amount=row["volume"] * row["close"],
        )
        raw_bars.append(bar)
    return raw_bars


def is_trading_end():
    """判断交易时间是否结束"""
    now = pd.Timestamp.now().strftime("%H:%M")

    if "08:30" <= now <= "16:35":
        if now >= "15:16":
            # 日盘交易结束
            return True

    if "00:30" <= now <= "04:00":
        if now >= "02:31":
            # 夜盘交易结束
            return True

    return False


def create_symbol_trader(api: TqApi, symbol, **kwargs):
    """创建一个品种的 CzscTrader, 回测与实盘场景同样适用

    :param api: TqApi, 天勤API实例
    :param symbol: str, 合约代码，要求符合天勤的规范
    :param kwargs: dict, 其他参数

        - sdt: str, 开始日期
        - files_position: list[str], 策略配置文件路径
        - adj_type: str, 复权类型，可选值：'F', 'B', 'N'，默认为 'F'，前复权

        - price (str / Callable): [可选]下单方式, 默认为 "ACTIVE"
            * "ACTIVE"：对价下单，在持仓调整过程中，若下单方向为买，对价为卖一价；若下单方向为卖，对价为买一价。
            * "PASSIVE"：排队价下单，在持仓调整过程中，若下单方向为买，对价为买一价；若下单方向为卖，对价为卖一价，该种方式可能会造成较多撤单.
            * Callable[[str], Union[float, int]]: 函数参数为下单方向，函数返回值是下单价格。如果返回 nan，程序会抛错。

        - offset_priority (str): [可选]开平仓顺序，昨=平昨仓，今=平今仓，开=开仓，逗号=等待之前操作完成

                               对于下单指令区分平今/昨的交易所(如上期所)，按照今/昨仓的数量计算是否能平今/昨仓
                               对于下单指令不区分平今/昨的交易所(如中金所)，按照“先平当日新开仓，再平历史仓”的规则计算是否能平今/昨仓，如果这些交易所设置为"昨开"在有当日新开仓和历史仓仓的情况下，会自动跳过平昨仓进入到下一步

                               * "今昨,开" 表示先平今仓，再平昨仓，等待平仓完成后开仓，对于没有单向大边的品种避免了开仓保证金不足
                               * "今昨开" 表示先平今仓，再平昨仓，并开仓，所有指令同时发出，适合有单向大边的品种
                               * "昨开" 表示先平昨仓，再开仓，禁止平今仓，适合股指这样平今手续费较高的品种
                               * "开" 表示只开仓，不平仓，适合需要进行锁仓操作的品种

    """
    adj_type = kwargs.get("adj_type", "F")
    files_position = kwargs.get("files_position")
    price = kwargs.get("price", "PASSIVE")
    offset_priority = kwargs.get("offset_priority", "今昨,开")

    tactic = czsc.CzscJsonStrategy(symbol=symbol, files_position=files_position)
    kline = api.get_kline_serial(symbol, int(tactic.base_freq.strip("分钟")) * 60, data_length=10000, adj_type=adj_type)
    quote = api.get_quote(symbol)
    raw_bars = format_kline(kline, freq=tactic.base_freq)

    # tqsdk 的一个特性：返回的K线中，默认最后一根K线是刚开始的K线，对应0成交；这里过滤掉这种K线
    raw_bars = [x for x in raw_bars if x.vol > 0]

    if kwargs.get("sdt"):
        sdt = pd.to_datetime(kwargs.get("sdt")).date()
    else:
        sdt = (pd.Timestamp.now() - pd.Timedelta(days=1)).date()
    trader = tactic.init_trader(raw_bars, sdt=sdt)
    target_pos = TargetPosTask(api, quote.underlying_symbol, price=price, offset_priority=offset_priority)

    meta = {
        "symbol": symbol,
        "kline": kline,
        "quote": quote,
        "trader": trader,
        "base_freq": tactic.base_freq,
        "target_pos": target_pos,
    }
    return meta


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
    "KQ.m@SHFE.ao",
    "KQ.m@SHFE.zn",
    "KQ.m@SHFE.cu",
    "KQ.m@SHFE.pb",
    # "KQ.m@SHFE.wr",
    "KQ.m@SHFE.br",
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
    "KQ.m@CZCE.PX",
    "KQ.m@CZCE.CJ",
    "KQ.m@CZCE.PK",
    "KQ.m@CZCE.SM",
    "KQ.m@CZCE.CY",
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
    "KQ.m@DCE.bb",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/GFEX
    "KQ.m@GFEX.si",
    "KQ.m@GFEX.lc",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/INE
    "KQ.m@INE.lu",
    "KQ.m@INE.sc",
    "KQ.m@INE.nr",
    "KQ.m@INE.bc",
    "KQ.m@INE.ec",
    # https://www.jiaoyixingqiu.com/shouxufei/jiaoyisuo/CFFEX
    "KQ.m@CFFEX.T",
    "KQ.m@CFFEX.TF",
    "KQ.m@CFFEX.TS",
    "KQ.m@CFFEX.TL",
    "KQ.m@CFFEX.IF",
    "KQ.m@CFFEX.IC",
    "KQ.m@CFFEX.IH",
    "KQ.m@CFFEX.IM",
]


future_name_map = {
    "AO": "氧化铝",
    "PX": "对二甲苯",
    "EC": "欧线集运",
    "LC": "碳酸锂",
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
    "BR": "合成橡胶",
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


def is_trade_time(quote, **kwargs):
    """判断当前是否是交易时间"""
    logger = kwargs.get("logger", loguru.logger)
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
    logger = kwargs.get("logger", loguru.logger)
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

    if not symbol_infos:
        logger.warning(f"没有需要调仓的品种，跳过调仓")
        return api
    else:
        logger.info(f"开始调仓：{[x for x in symbol_infos.keys()]}")

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
            for symbol, info in symbol_infos.items():
                target_pos: TargetPosTask = info["target_pos"]
                target_pos.cancel()
                logger.info(f"取消调仓：{symbol}")
            break

    return api
