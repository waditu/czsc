# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/12 22:00
"""
import os
import pandas as pd
from czsc.traders.ts_backtest import TsDataCache, TsStocksBacktest, freq_cn2ts
from czsc.strategies import trader_strategy_a as strategy

os.environ['czsc_verbose'] = "0"        # 是否输出详细执行信息，包括一些用于debug的信息，0 不输出，1 输出
os.environ['czsc_min_bi_len'] = "6"     # 通过环境变量设定最小笔长度，6 对应新笔定义，7 对应老笔定义

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 20)


# data_path 是 TS_CACHE 缓存数据文件夹所在目录
dc = TsDataCache(data_path=r"C:\ts_data_czsc", refresh=False, sdt="20120101", edt="20221001")

# 获取策略的基础K线周期，回测开始时间 sdt，回测结束时间 edt，初始化K线数量init_n
freq = freq_cn2ts[strategy('000001.SH')['base_freq']]
sdt = '20140101'
edt = "20211216"
init_n = 1000*4


def run_backtest(step_seq=('check', 'index', 'etfs', 'train', 'valid', 'stock')):
    """

    :param step_seq: 回测执行顺序
    :return:
    """
    tsb = TsStocksBacktest(dc, strategy, init_n, sdt, edt)
    for step in step_seq:
        tsb.batch_backtest(step.lower())
        tsb.analyze_results(step, 'long')
        # tsb.analyze_results(step, 'short')
        print(f"results saved into {tsb.res_path}")


def run_more_backtest(step, ts_codes):
    """指定在某个阶段多回测一些标的，最常见的需求是在 check 阶段多检查几个标的

    :param step: 阶段名称
    :param ts_codes: 新增回测标的列表
    :return:
    """
    tsb = TsStocksBacktest(dc, strategy, init_n, sdt, edt)
    tsb.update_step(step, ts_codes)
    tsb.batch_backtest(step.lower())
    tsb.analyze_results(step, 'long')
    # tsb.analyze_results(step, 'short')
    print(f"results saved into {tsb.res_path}")


if __name__ == '__main__':
    # run_more_backtest(step='check', ts_codes=['000002.SZ'])
    # run_backtest(step_seq=('index',))
    run_backtest(step_seq=('train',))
    # run_backtest(step_seq=('etfs',))
    # run_backtest(step_seq=('index', 'train'))
    # run_backtest(step_seq=('check', 'index', 'train'))
    # run_backtest(step_seq=('check', 'index', 'train', 'valid'))

