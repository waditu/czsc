# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:10
describe: 掘金量化基础utils
"""
import os
import inspect
import traceback
from gm.api import *
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
import pandas as pd
from typing import List, Callable
from czsc.analyze import CzscTrader, KlineGenerator, RawBar
from czsc.signals.signals import get_default_signals
from czsc.enum import Freq, Operate
from czsc.objects import Event
from czsc.utils.qywx import push_file, push_text, push_markdown
from czsc.utils.log import create_logger

dt_fmt = "%Y-%m-%d %H:%M:%S"


def set_gm_token(token):
    with open(os.path.join(os.path.expanduser("~"), "gm_token.txt"), 'w', encoding='utf-8') as f:
        f.write(token)


file_token = os.path.join(os.path.expanduser("~"), "gm_token.txt")
if not os.path.exists(file_token):
    print("{} 文件不存在，请单独启动一个 python 终端，调用 set_gm_token 方法创建该文件，再重新执行。".format(file_token))
else:
    gm_token = open(file_token, encoding="utf-8").read()
    set_token(gm_token)

freq_map = {"60s": "1分钟", "300s": "5分钟", "900s": "15分钟",
            "1800s": "30分钟", "3600s": "60分钟", "1d": "日线"}

indices = {
    "上证指数": 'SHSE.000001',
    "上证50": 'SHSE.000016',
    "沪深300": "SHSE.000300",
    "中证1000": "SHSE.000852",

    "深证成指": "SZSE.399001",
    "创业板指数": 'SZSE.399006',
    "深次新股": "SZSE.399678",
    "中小板指": "SZSE.399005",
    "中证500": "SZSE.399905",
    "国证2000": "SZSE.399303",
    "小盘成长": "SZSE.399376",
    "小盘价值": "SZSE.399377",
}


def get_shares():
    """获取股票列表"""
    df = get_instruments(exchanges='SZSE,SHSE', fields="symbol,sec_name", df=True)
    shares = {row['symbol']: row['sec_name'] for _, row in df.iterrows()}
    return shares


def get_index_shares(name, end_date=None):
    """获取某一交易日的指数成分股列表

    symbols = get_index_shares("上证50", "2019-01-01 09:30:00")
    """
    date_fmt = "%Y-%m-%d"
    if not end_date:
        end_date = datetime.now().strftime(date_fmt)
    else:
        # end_date = end_date.split(" ")[0]
        end_date = pd.to_datetime(end_date).strftime(date_fmt)
    constituents = get_history_constituents(indices[name], end_date, end_date)[0]
    symbol_list = [k for k, v in constituents['constituents'].items()]
    return list(set(symbol_list))


def get_contract_basic(symbol, trade_date=None):
    """获取合约信息

    https://www.myquant.cn/docs/python/python_select_api#8ba2064987fb1d1f

    https://www.myquant.cn/docs/python/python_select_api#8f28e1de81b80633
    """
    if not trade_date:
        res = get_instruments(symbol)
        if not res:
            return None
        return res[0]
    else:
        res = None


# ======================================================================================================================
# 行情数据获取
# ======================================================================================================================
def format_kline(df, freq: Freq):
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(symbol=row['symbol'], id=i, freq=freq, dt=row['eob'], open=round(row['open'], 2),
                     close=round(row['close'], 2), high=round(row['high'], 2),
                     low=round(row['low'], 2), vol=row['volume'])
        bars.append(bar)
    return bars


def get_kline(symbol, end_time, freq='60s', count=33000, adjust=ADJUST_PREV):
    """获取K线数据

    :param symbol:
    :param end_time:
    :param freq:
    :param count:
    :param adjust:
    :return:
    """
    if isinstance(end_time, datetime):
        end_time = end_time.strftime(dt_fmt)

    exchange = symbol.split(".")[0]
    freq_map_ = {'60s': Freq.F1, '300s': Freq.F5, '900s': Freq.F15, '1800s': Freq.F30,
                 '3600s': Freq.F60, '1d': Freq.D}

    if exchange in ["SZSE", "SHSE"]:
        df = history_n(symbol=symbol, frequency=freq, end_time=end_time, adjust=adjust,
                       fields='symbol,eob,open,close,high,low,volume', count=count, df=True)
    else:
        df = history_n(symbol=symbol, frequency=freq, end_time=end_time, adjust=adjust,
                       fields='symbol,eob,open,close,high,low,volume,position', count=count, df=True)
    return format_kline(df, freq_map_[freq])


def format_tick(tick):
    k = {'symbol': tick['symbol'],
         'dt': tick['created_at'],
         'price': tick['price'],
         'vol': tick['last_volume']}
    return k


def get_ticks(symbol, end_time, count=33000):
    if isinstance(end_time, datetime):
        end_time = end_time.strftime(dt_fmt)
    data = history_n(symbol=symbol, frequency="tick", end_time=end_time, count=count, df=False, adjust=1)
    return data


# ======================================================================================================================
# 实盘&仿真&回测共用函数
# ======================================================================================================================
def get_init_kg(symbol: str,
                end_dt: [str, datetime],
                generator: [KlineGenerator] = KlineGenerator,
                freqs=('1分钟', '5分钟', '15分钟', "30分钟", '60分钟', "日线"),
                max_count=1000,
                adjust=ADJUST_PREV):
    """获取symbol的初始化kline generator"""
    freq_map_ = {"1分钟": '60s', "5分钟": '300s', "15分钟": '900s', "30分钟": '1800s', "60分钟": '3600s', "日线": '1d'}
    end_dt = pd.to_datetime(end_dt, utc=True)
    end_dt = end_dt.tz_convert('dateutil/PRC')
    last_day = (end_dt - timedelta(days=1)).replace(hour=16, minute=0)

    kg = generator(max_count=max_count, freqs=freqs)

    for freq in freqs:
        bars = get_kline(symbol=symbol, end_time=last_day, freq=freq_map_[freq], count=max_count, adjust=adjust)
        kg.init_kline(freq, bars)
        print(f"{symbol} - {freq} - last_dt: {kg.get_kline(freq, 1)[-1].dt} - last_day: {last_day}")

    bars = get_kline(symbol=symbol, end_time=end_dt, freq="60s", count=300)
    data = [x for x in bars if x.dt > last_day]

    if data:
        print(f"{symbol}: 更新 kg 至 {end_dt.strftime(dt_fmt)}，共有{len(data)}行数据需要update")
        for row in data:
            kg.update(row)
    return kg


def write_bs(context, symbol, bs):
    """把bs详细信息写入文本文件"""
    file_bs = os.path.join(context.cache_path, "{}_bs.txt".format(symbol))
    with open(file_bs, 'a', encoding="utf-8") as f:
        row = dict(bs)
        row['dt'] = row['dt'].strftime("%Y-%m-%d %H:%M:%S")
        f.write(str(row) + "\n")


def take_snapshot(context, trader, name):
    """

    :param context:
    :param trader:
    :param name: str
        平多、平空、开多、开空、快照
    :return:
    """
    if context.mode != MODE_BACKTEST:
        return

    symbol = trader.symbol
    now_ = context.now.strftime('%Y%m%d_%H%M')
    price = trader.latest_price
    file_html = os.path.join(context.cache_path, f"{symbol}_{now_}_{name}_{price}.html")
    trader.take_snapshot(file_html, width="1400px", height="580px")
    print(f"snapshot saved into {file_html}")
    if context.mode != MODE_BACKTEST:
        push_file(file_html, key=context.wx_key)


class GmCzscTrader(CzscTrader):
    def __init__(self, symbol, end_dt=None, max_count=2000,
                 get_signals: Callable = get_default_signals,
                 events: List[Event] = None):
        self.symbol = symbol
        self.freq_map = {"1分钟": '60s', "5分钟": '300s', "15分钟": '900s', "30分钟": '1800s',
                         "60分钟": '3600s', "日线": '1d'}

        if not end_dt:
            end_dt = datetime.now(timezone(timedelta(hours=8)))
        kg = get_init_kg(symbol, end_dt, max_count=max_count, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
        super(GmCzscTrader, self).__init__(kg, get_signals=get_signals, events=events)

    def get_latest_f1(self) -> List[RawBar]:
        """获取最新的1分钟K线"""
        exchange = self.symbol.split('.')[0]
        if exchange in ["SZSE", "SHSE"]:
            fields = 'symbol,eob,open,close,high,low,volume'
        else:
            fields = 'symbol,eob,open,close,high,low,volume,position'
        df = history(self.symbol, '60s', start_time=self.end_dt, end_time=datetime.now(), fields=fields,
                     skip_suspended=True, fill_missing=None, adjust=ADJUST_NONE, adjust_end_time='', df=True)
        bars = format_kline(df, Freq.F1)
        return bars

    def update_factors(self):
        """更新K线数据到最新状态"""
        bars = self.get_latest_f1()
        if not bars or bars[-1].dt <= self.end_dt:
            return
        for bar in bars:
            self.check_operate(bar)


def gm_take_snapshot(gm_symbol, end_dt=None, file_html=None, get_signals: Callable = get_default_signals):
    """使用掘金的数据对任意标的、任意时刻的状态进行快照

    :param gm_symbol:
    :param end_dt:
    :param file_html:
    :param get_signals:
    :return:
    """
    ct = GmCzscTrader(gm_symbol, end_dt=end_dt, max_count=2000, get_signals=get_signals)
    if file_html:
        ct.take_snapshot(file_html)
        print(f'saved into {file_html}')
    else:
        ct.open_in_browser()
    return ct

