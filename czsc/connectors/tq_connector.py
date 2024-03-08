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
