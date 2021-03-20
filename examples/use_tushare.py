# coding: utf-8
"""
基于Tushare数据的单级别形态选股，以日线三买为例
"""

import pandas as pd
import traceback
import tushare as ts
from datetime import datetime, timedelta
from typing import List
import czsc
from czsc.analyze import CZSC, RawBar
from czsc.enum import Signals

assert czsc.__version__ >= '0.6.7'

# 使用第三方数据，只需要定义一个K线转换函数
def format_kline(kline: pd.DataFrame) -> List[RawBar]:
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
    return bars


def is_third_buy(ts_code):
    """判断一个股票现在是否有日线三买"""
    # 调用tushare的K线获取方法，Tushare数据的使用方法，请参考：https://tushare.pro/document/2
    end_date = datetime.now()
    start_date = end_date - timedelta(days=1000)
    df = ts.pro_bar(ts_code=ts_code, adj='qfq', asset="E",
                    start_date=start_date.strftime("%Y%m%d"),
                    end_date=end_date.strftime("%Y%m%d"))
    bars = format_kline(df)
    c = CZSC(bars, freq="日线")

    # 在这里判断是否有五笔三买形态，也可以换成自己感兴趣的形态
    if c.signals['倒1五笔'] in [Signals.X5LB0.value]:
        return True
    else:
        return False


if __name__ == '__main__':
    # 这里可以换成自己的股票池
    ts_codes = ['603259.SH', '603288.SH', '603501.SH', '603986.SH']
    for ts_code in ts_codes:
        try:
            if is_third_buy(ts_code):
                print("{} - 日线三买".format(ts_code))
        except:
            traceback.print_exc()
            print("{} - 执行失败".format(ts_code))
