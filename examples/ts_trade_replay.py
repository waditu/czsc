# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 15:58
describe: 请描述文件用途
"""
from ts_fast_backtest import dc
from czsc.strategies import trader_strategy_a as strategy
from czsc.utils import BarGenerator
from czsc.traders.utils import trade_replay

bars = dc.pro_bar_minutes('000001.SZ', "20150101", "20220101", freq='15min', asset="I", adj="hfq", raw_bar=True)
res_path = r"C:\ts_data\trade_replay_test4"

tactic = strategy("000001.SH")
bg = BarGenerator(base_freq=tactic['base_freq'], freqs=tactic['freqs'])
bars1 = bars[:10000]
bars2 = bars[10000:]
for bar in bars1:
    bg.update(bar)
trade_replay(bg, bars2, strategy, res_path)
