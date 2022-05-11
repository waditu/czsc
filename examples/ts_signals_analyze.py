# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/3/24 16:33
describe: 使用 Tushare 数据分析信号表现
"""
import os
import traceback
import pandas as pd
from czsc import CZSC, Freq, CzscAdvancedTrader
from collections import OrderedDict
from czsc.data.ts_cache import TsDataCache
from czsc.sensors.utils import read_cached_signals, generate_stocks_signals, SignalsPerformance
from czsc import signals


pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 20)


def generate_all_signals(data_path=r"C:\ts_data", name="signals_b"):
    """给出信号定义函数，计算全市场股票的所有信号"""
    def get_v1_signals(cat: CzscAdvancedTrader):
        s = OrderedDict()
        for freq, c in cat.kas.items():
            if c.freq == Freq.D:
                s.update(signals.bxt.get_s_three_bi(c, di=1))
                s.update(signals.vol.get_s_vol_single_sma(c, di=1, t_seq=(10, 20)))
        return s

    def __strategy(symbol):
        return {
            "symbol": symbol,
            "get_signals": get_v1_signals,
            "base_freq": '日线',
            "freqs": ['周线', '月线'],
        }

    # tushare 研究数据缓存，一次缓存，可以重复使用
    dc = TsDataCache(data_path, sdt='2000-01-01', edt='2022-02-18')

    signals_path = os.path.join(data_path, name)
    generate_stocks_signals(dc, signals_path, sdt='20100101', edt='20220101', strategy=__strategy)


def analyze_signals():
    results_path = r"C:\ts_data\signals_b_analyze"
    signals_path = r"C:\ts_data\signals_b"
    path_pat = f"{signals_path}\*_signals.pkl"
    sdt = "20150101"
    edt = "20220101"
    file_output = os.path.join(signals_path, f"{sdt}_{edt}_merged.pkl")
    dfs = read_cached_signals(file_output, path_pat, sdt, edt)
    # 为了方便逐年查看信号表现，新增 year
    dfs['year'] = dfs['dt'].apply(lambda x: x.year)

    os.makedirs(results_path, exist_ok=True)

    for col in [x for x in dfs.columns if len(x.split("_")) == 3]:
        try:
            sp = SignalsPerformance(dfs, keys=[col])
            file_res = os.path.join(results_path, f"{col}_{sdt}_{edt}.xlsx")
            sp.report(file_res)
            print(f"signal results saved into {file_res}")
        except:
            print(f"signal analyze failed: {col}")
            traceback.print_exc()


if __name__ == '__main__':
    generate_all_signals(data_path=r"C:\ts_data_czsc", name="signals_b")
    analyze_signals()

