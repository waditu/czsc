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
from tqsdk import ( # noqa
    TqApi, TqAuth, TqSim, TqBacktest, TargetPosTask, BacktestFinished, TqAccount, TqKq
)


def format_kline(df, freq=Freq.F1):
    """对分钟K线进行格式化"""
    freq = Freq(freq)
    rows = df.to_dict('records')
    raw_bars = []
    for i, row in enumerate(rows):
        bar = RawBar(symbol=row['symbol'], id=i, freq=freq,
                     dt=datetime.fromtimestamp(row["datetime"] / 1e9) + timedelta(minutes=1),
                     open=row['open'], close=row['close'], high=row['high'],
                     low=row['low'], vol=row['volume'], amount=row['volume'] * row['close'])
        raw_bars.append(bar)
    return raw_bars


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
    'PG': 'LPG',
    'EB': '苯乙烯',
    'CS': '玉米淀粉',
    'C': '玉米',
    'V': 'PVC',
    'J': '焦炭',
    'BB': '胶合板',
    'M': '豆粕',
    'A': '豆一',
    'PP': '聚丙烯',
    'P': '棕榈油',
    'FB': '纤维板',
    'B': '豆二',
    'JD': '鸡蛋',
    'JM': '焦煤',
    'L': '塑料',
    'I': '铁矿石',
    'Y': '豆油',
    'RR': '粳米',
    'EG': '乙二醇',
    'LH': '生猪',
    'CJ': '红枣',
    'UR': '尿素',
    'TA': 'PTA',
    'OI': '菜油',
    'MA': '甲醇',
    'RS': '菜籽',
    'ZC': '动力煤',
    'LR': '晚籼稻',
    'PM': '普麦',
    'SR': '白糖',
    'RI': '早籼稻',
    'SF': '硅铁',
    'WH': '强麦',
    'JR': '粳稻',
    'SM': '锰硅',
    'FG': '玻璃',
    'CF': '棉花',
    'RM': '菜粕',
    'PF': '短纤',
    'AP': '苹果',
    'CY': '棉纱',
    'ER': '早籼稻',
    'ME': '甲醇',
    'RO': '菜油',
    'TC': '动力煤',
    'WS': '强麦',
    'WT': '硬麦',
    'SA': '纯碱',
    'PK': '花生',
    'SS': '不锈钢',
    'AL': '沪铝',
    'CU': '沪铜',
    'ZN': '沪锌',
    'AG': '白银',
    'RB': '螺纹钢',
    'SN': '沪锡',
    'NI': '沪镍',
    'WR': '线材',
    'FU': '燃油',
    'AU': '黄金',
    'PB': '沪铅',
    'RU': '橡胶',
    'HC': '热轧卷板',
    'BU': '沥青',
    'SP': '纸浆',
    'NR': '20号胶',
    'SC': '原油',
    'LU': '低硫燃料油',
    'BC': '国际铜',
    'SCTAS': '原油TAS指令',
    'SI': '工业硅',
}


def is_trade_time(trade_time: Optional[str] = None):
    """判断当前是否是交易时间"""
    if trade_time is None:
        trade_time = datetime.now().strftime("%H:%M:%S")

    if trade_time > "09:00:00" and trade_time < "11:30:00":
        return True

    if trade_time > "13:00:00" and trade_time < "15:00:00":
        return True

    if trade_time > "21:00:00" and trade_time < "02:30:00":
        return True

    return False


def get_daily_backup(api: TqApi, **kwargs):
    """获取每日账户中需要备份的信息"""
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

    account_ids = [x for x in list(account.__dict__.keys()) if x not in ["_data", "_path", "_listener", '_api']]
    account = {x: account.__dict__[x] for x in account_ids}

    backup = {
        "orders": orders,
        "trades": trades,
        "positions": positions,
        "account": account,
    }
    return backup
