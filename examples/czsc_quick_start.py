# coding: utf-8
"""
目前 czsc 库处于开发阶段，不同版本之间的 API 兼容性较差。
这个文件对应的 czsc 版本为 0.7.2，代码即文档，关于0.7.2的所有你想知道的都在代码里。

注意：czsc 是针对程序化实盘进行设计的，用来做研究需要自己按需求改动代码，强烈建议研究、实盘使用统一的代码。
"""

import czsc
from czsc.factors import CzscTrader
# 聚宽数据为目前支持的数据源，需要接入第三方数据源的请参考这个文件进行编写
from czsc.data.jq import *
import pandas as pd
import traceback
import tushare as ts
from datetime import datetime, timedelta
from typing import List
from czsc.analyze import CZSC, RawBar
from czsc.enum import Signals, Freq
from czsc.factors.utils import match_factor, match_factors

assert czsc.__version__ == '0.7.2'

# 首次使用需要设置聚宽账户，以下大部分案例依赖聚宽数据
# set_token("phone number", 'password') # 第一个参数是JQData的手机号，第二个参数是登录密码

print("聚宽剩余调用次数：{}".format(get_query_count()))

# ======================================================================================================================
# 使用单个级别的信号进行选股

def is_third_buy(symbol):
    """判断一个股票现在是否有日线三买"""
    bars = get_kline(symbol, freq="D", end_date=datetime.now(), count=1000)
    c = CZSC(bars, freq="日线")

    if c.signals['倒1形态'] in [Signals.LI0.value]:
        return True
    else:
        return False

def run_jq_selector():
    # 获取上证50最新成分股列表，这里可以换成自己的股票池
    symbols: List = get_index_stocks("000016.XSHG")
    for symbol in symbols:
        try:
            if is_third_buy(symbol):
                print("{} - 日线三买".format(symbol))
        except:
            print("{} - 执行失败".format(symbol))
            traceback.print_exc()


run_jq_selector()

# ======================================================================================================================
# CzscTrader 的使用案例

# 直接使用 CzscTrader 获取多级别K线分析结果，并在浏览器中打开
ct = CzscTrader(symbol="000001.XSHG", max_count=1000, end_date=datetime.now())
ct.open_in_browser(width="1400px", height="580px")
# open_in_browser 方法可以在windows系统中使用，如果无法使用，可以直接保存结果到 html 文件
# ct.take_snapshot(file_html="czsc_results.html", width="1400px", height="580px")

# 多级别联立三买因子
factor = [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.D.value}_倒1形态#{Signals.LH0.value}"]
if match_factor(ct.s, factor):
    print("is match")
else:
    print("is not match")

factors = [
    [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.D.value}_倒1形态#{Signals.LH0.value}"],
    [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.D.value}_倒2形态#{Signals.LH0.value}"],

    [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.F15.value}_倒5形态#{Signals.LA0.value}"],
    [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.F15.value}_倒4形态#{Signals.SH0.value}"],
    [f"{Freq.F15.value}_倒1形态#{Signals.LI0.value}", f"{Freq.F15.value}_倒6形态#{Signals.SI0.value}"],
]
if match_factors(ct.s, factors):
    print("is match")
else:
    print("is not match")

# 在默认浏览器中打开指定结束日期的分析结果）
ct = CzscTrader(symbol="000001.XSHG", end_date="2021-03-04")
ct.open_in_browser(width="1400px", height="580px")

# 推演分析：从某一天开始，逐步推进
ct = CzscTrader(symbol="000001.XSHG", end_date="2008-01-01")
ct.open_in_browser()
ct.forward(n=10)    # 行情向前推进十天
ct.open_in_browser()

# ----------------------------------------------------------------------------------------------------------------------
# 多级别联立


# ======================================================================================================================
# 对接第三方数据，以 Tushare 为例

# 使用第三方数据，只需要定义一个K线转换函数
def format_tushare_kline(kline: pd.DataFrame) -> List[RawBar]:
    """

    :param kline: Tushare 数据接口返回的K线数据
    :return: 转换好的K线数据
    """
    bars = []
    records = kline.to_dict('records')
    for record in records:
        # 将每一根K线转换成 RawBar 对象
        bar = RawBar(symbol=record['ts_code'], dt=pd.to_datetime(record['trade_date']), open=record['open'],
                     close=record['close'], high=record['high'], low=record['low'], vol=record['vol'])
        bars.append(bar)
    return bars[::-1]   # K线时间必须是从小到大


def is_tushathird_buy(ts_code):
    """判断一个股票现在是否有日线三买"""
    # 调用tushare的K线获取方法，Tushare数据的使用方法，请参考：https://tushare.pro/document/2
    end_date = datetime.now()
    start_date = end_date - timedelta(days=2000)
    df = ts.pro_bar(ts_code=ts_code, adj='qfq', asset="E", freq='D',
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"))
    bars = format_tushare_kline(df)
    c = CZSC(bars, freq="日线", max_bi_count=20)

    if c.signals['倒1形态'] in [Signals.LI0.value]:
        return True
    else:
        return False

def run_tushare_selector():
    # 这里可以换成自己的股票池
    ts_codes = ['603259.SH', '603288.SH', '603501.SH', '603986.SH']
    for ts_code in ts_codes:
        try:
            if is_third_buy(ts_code):
                print("{} - 日线三买".format(ts_code))
            else:
                print("{} - 不是日线三买".format(ts_code))
        except:
            traceback.print_exc()
            print("{} - 执行失败".format(ts_code))


run_tushare_selector()

# ======================================================================================================================











