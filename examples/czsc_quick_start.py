# coding: utf-8
"""
目前 czsc 库处于开发阶段，不同版本之间的 API 兼容性较差。

注意：czsc 是针对程序化实盘进行设计的，用来做研究需要自己按需求改动代码，强烈建议研究、实盘使用统一的代码。
"""

from czsc.data.jq import *
import traceback
from datetime import datetime
from typing import List
from czsc.analyze import CZSC
from czsc.signals.signals import get_default_signals
from czsc.objects import Signal, Factor

# 首次使用需要设置聚宽账户，以下大部分案例依赖聚宽数据
# set_token("phone number", 'password') # 第一个参数是JQData的手机号，第二个参数是登录密码

print("聚宽剩余调用次数：{}".format(get_query_count()))

# ======================================================================================================================
# 使用单个级别的信号进行选股


def is_third_buy(symbol):
    """判断一个股票现在是否有日线三买"""
    bars = get_kline(symbol, freq="D", end_date=datetime.now(), count=1000)
    c = CZSC(bars, get_signals=get_default_signals)

    factor_ = Factor(
        name="类三买选股因子",
        signals_any=[
            Signal("日线_倒1笔_基础形态_类三买_任意_任意_0"),
            Signal("日线_倒1笔_类买卖点_类三买_任意_任意_0"),
        ],
        signals_all=[
            Signal("日线_倒1笔_拟合优度_小于0.2_任意_任意_0")
        ]
    )
    if factor_.is_match(c.signals):
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


if __name__ == '__main__':
    run_jq_selector()







