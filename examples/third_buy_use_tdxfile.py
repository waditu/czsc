# coding: utf-8

import pandas as pd
from datetime import datetime
from typing import List
from czsc.analyze import CZSC, RawBar
from czsc.enum import Signals
import struct
import os


TDX_DIR = r"D:\new_jyplug"   # 首先要设置通达信的安装目录

# 从通达信目录读入数据
def get_data_from_tdxfile(stock_code, type) -> List[RawBar]:
    '''
    stock_code:股票代码 600667
    type：市场代码，sh沪市，sz深市
    '''
    bars = []
    filepath = TDX_DIR + r'\vipdoc\\' + type + r'\lday\sh' + stock_code + '.day'
    with open(filepath, 'rb') as f:
        while True:
            stock_date = f.read(4)
            stock_open = f.read(4)
            stock_high = f.read(4)
            stock_low = f.read(4)
            stock_close = f.read(4)
            stock_amount = f.read(4)
            stock_vol = f.read(4)
            stock_reservation = f.read(4)
            if not stock_date:
                break
            stock_date = struct.unpack("l", stock_date)  # 4字节 如20091229
            stock_open = struct.unpack("l", stock_open)  # 开盘价*100
            stock_high = struct.unpack("l", stock_high)  # 最高价*100
            stock_low = struct.unpack("l", stock_low)  # 最低价*100
            stock_close = struct.unpack("l", stock_close)  # 收盘价*100
            stock_amount = struct.unpack("f", stock_amount)  # 成交额
            stock_vol = struct.unpack("l", stock_vol)  # 成交量
            stock_reservation = struct.unpack("l", stock_reservation)  # 保留值
            date_format = datetime.strptime(str(stock_date[0]), '%Y%M%d')  # 格式化日期
            date_format = date_format.strftime('%Y-%M-%d')

            bar = RawBar(symbol=stock_code, dt=pd.to_datetime(date_format), open=stock_open[0] / 100,
                         close=stock_close[0] / 100.0, high=stock_high[0] / 100.0, low=stock_low[0] / 100.0,
                         vol=stock_vol[0])
            bars.append(bar)
        return bars


def is_third_buy(stock_code, type):
    bars = get_data_from_tdxfile(stock_code, type)
    c = CZSC(bars, freq="日线")
    if c.signals['倒1形态'] in [Signals.LI0.value]:
        return True
    else:
        return False


if __name__ == '__main__':
    # 找出沪市6开头的，中三买的票
    rootdir = TDX_DIR + r"\vipdoc\sh\lday"
    list = os.listdir(rootdir)  # 列出文件夹下所有的目录与文件
    for i in range(0, len(list)):
        scode=list[i][2:8]
        if scode.startswith("6"):
            if is_third_buy(scode,"sh"):
                print("{} - 日线三买".format(scode))

    # 找出深圳中0开头的三买的票
    rootdir = TDX_DIR + r"\vipdoc\sz\lday"
    list = os.listdir(rootdir)  # 列出文件夹下所有的目录与文件
    for i in range(0, len(list)):
        scode=list[i][2:8]
        if scode.startswith("0"):
            if is_third_buy(scode,"sz"):
                print("{} - 日线三买".format(scode))
