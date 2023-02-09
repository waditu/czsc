# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 15:58
describe: 请描述文件用途
"""
import pandas as pd
from czsc.data import TsDataCache, freq_cn2ts
from czsc.utils import BarGenerator
from czsc.traders.utils import trade_replay
from czsc.strategies import trader_strategy_a as strategy


# data_path 是 TS_CACHE 缓存数据文件夹所在目录
dc = TsDataCache(data_path=r"C:\ts_data_czsc", refresh=False, sdt="20120101", edt="20221001")

# 获取单个品种的基础周期K线
tactic = strategy("000001.SZ")
base_freq = tactic['base_freq']
bars = dc.pro_bar_minutes('000001.SZ', "20150101", "20220101", freq=freq_cn2ts[base_freq], asset="E", adj="hfq")

# 设置回放快照文件保存目录
res_path = r"C:\ts_data_czsc\replay_trader_strategy_a"


# 拆分基础周期K线，一部分用来初始化BarGenerator，随后的K线是回放区间
start_date = pd.to_datetime("20200101")
bg = BarGenerator(base_freq, freqs=tactic['freqs'])
bars1 = [x for x in bars if x.dt <= start_date]
bars2 = [x for x in bars if x.dt > start_date]
for bar in bars1:
    bg.update(bar)


if __name__ == '__main__':
    trade_replay(bg, bars2, strategy, res_path)


