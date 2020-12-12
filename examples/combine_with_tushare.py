# coding: utf-8
"""
结合 tushare.pro 的数据使用 czsc 进行缠论技术分析

author: zengbin93
email: zeng_bin8888@163.com
date: 2020-02-02
========================================================================================================================
"""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "..")

import czsc
print(czsc.__version__)
from czsc import KlineAnalyze
from czsc.data.ts import get_kline

# 首次使用，需要在这里设置你的 tushare token，用于获取数据；在同一台机器上，tushare token 只需要设置一次
# 没有 token，到 https://tushare.pro/register?reg=7 注册获取
# import tushare as ts
# ts.set_token("your tushare token")

def use_kline_analyze():
    print('=' * 100, '\n')
    print("KlineAnalyze 的使用方法：\n")
    ts_code = "300033.SZ"
    asset = "E"
    kline = get_kline("{}-{}".format(ts_code, asset), end_date="20201212", freq='30min', count=2000)
    ka = KlineAnalyze(kline, name="本级别", bi_mode="new", max_count=2000, use_ta=False, use_xd=True)
    print("分型：", ka.fx_list, "\n")
    print("线段：", ka.xd_list, "\n")


if __name__ == '__main__':
    use_kline_analyze()

