# coding: utf-8
"""
基于聚宽数据的单级别形态选股，以日线三买为例
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

# 首次使用需要设置聚宽账户
# from czsc.data.jq import set_token
# set_token("phone number", 'password') # 第一个参数是JQData的手机号，第二个参数是登录密码
from datetime import datetime
from typing import List
import traceback
from czsc.data.jq import get_kline, get_index_stocks
from czsc.analyze import CZSC
from czsc.enum import Signals


def is_third_buy(symbol):
    """判断一个股票现在是否有日线三买"""
    bars = get_kline(symbol, freq="D", end_date=datetime.now(), count=1000)
    c = CZSC(bars, freq="日线")

    # 在这里判断是否有五笔三买形态，也可以换成自己感兴趣的形态
    if c.signals['倒1五笔'] in [Signals.X5LB0.value]:
        return True
    else:
        return False


if __name__ == '__main__':
    # 获取上证50最新成分股列表，这里可以换成自己的股票池
    symbols: List = get_index_stocks("000016.XSHG")
    for symbol in symbols:
        try:
            if is_third_buy(symbol):
                print("{} - 日线三买".format(symbol))
        except:
            print("{} - 执行失败".format(symbol))
            traceback.print_exc()
