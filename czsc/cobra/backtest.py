# coding: utf-8
"""
快速回测框架：
1. 准备阶段
    1.1 配置回测参数
    1.2 下载历史数据
    1.3 数据预处理
2. 生成交易序列
3. 评估交易序列的绩效
"""
import os
from collections import OrderedDict
import numpy as np
import pandas as pd
from tqdm import tqdm
from pyecharts.charts import Page
from typing import List, Tuple, Dict, Union
import seaborn as sns
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

from ..objects import RawBar
from ..factors.factors import CZSC, CzscFactors, KlineGeneratorBy1Min, factors_func
from ..utils.echarts_plot import box_plot


class Backtest:
    def __init__(self):
        self.name = "backtest"


def factors_to_bs(factors: pd.DataFrame, opens: List, exits: List, direction="long", cost=0.3):
    """从因子生成交易序列

    :param cost: 每一个交易对的固定交易成本
    :param factors:
    :param opens:
    :param exits:
    :param direction:
    :return:
    """
    name = opens[0].split("@")[0]
    last_op = "exit"
    ops = []
    for i, row in tqdm(factors.iterrows()):
        op = {"dt": row['dt'], "symbol": row['symbol'], "price": row['close'], "direction": direction}
        if last_op == 'exit' and f"{name}@{row[name]}" in opens:
            op.update({'op': "long_open", 'op_detail': f"{name}@{row[name]}"})
            last_op = 'open'
            ops.append(op)

        elif last_op == 'open' and f"{name}@{row[name]}" in exits:
            op.update({'op': "long_exit", 'op_detail': f"{name}@{row[name]}"})
            last_op = 'exit'
            ops.append(op)
    if ops:
        df = pd.DataFrame(ops)
    else:
        df = pd.DataFrame()

    # 构造成交易对形式输出
    if len(ops) % 2 != 0:
        ops.pop(-1)

    pairs = []
    for i in range(0, len(ops), 2):
        b, s = ops[i: i + 2]
        pair = OrderedDict({
            "标的代码": b['symbol'],
            "开仓时间": b['dt'],
            "开仓价格": b['price'],
            "开仓因子": b['op_detail'],
            "平仓时间": s['dt'],
            "平仓价格": s['price'],
            "平仓因子": s['op_detail'],
            "持仓天数": (s['dt'] - b['dt']).days,
            "盈亏(%)": round((s['price'] - b['price']) / b['price'] * 100 - cost, 2),
        })

        if pairs:
            pair['净值(%)'] = round((pairs[-1]['净值(%)']) * (1 + pair['盈亏(%)'] / 100), 2)
        else:
            pair['净值(%)'] = round(100 * (1 + pair['盈亏(%)'] / 100), 2)
        pairs.append(pair)
    if pairs:
        df1 = pd.DataFrame(pairs)
    else:
        df1 = pd.DataFrame()

    return df, df1


def generate_snapshots_by_dts(bars: List[Union[RawBar, Dict]],
                              dts: List[Union[datetime, str]],
                              html_path: str,
                              factors: List = None):
    """多时刻截面走势分析结果生成

    :param bars: 1分钟K线
    :param dts: 时间截面数组
    :param html_path: html 文件保存路径
    :param factors: 因子对应的函数
    :return:
    """
    os.makedirs(html_path, exist_ok=True)
    dt_fmt = "%Y%m%d%H%M"

    dts = [pd.to_datetime(x) for x in dts]
    dts = [x.strftime(dt_fmt) for x in dts]

    kg = KlineGeneratorBy1Min(max_count=3000, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
    for row in tqdm(bars, desc='generate_snapshots'):
        if isinstance(row, Dict):
            bar = RawBar(symbol=row['symbol'], open=round(row['open'], 2), dt=row['dt'], vol=row['vol'],
                         close=round(row['close'], 2), high=round(row['high'], 2), low=round(row['low'], 2))
        else:
            bar = row

        kg.update(bar)
        if bar.dt.strftime(dt_fmt) in dts:
            file_html = os.path.join(html_path, f"{bar.symbol}_{bar.dt.strftime(dt_fmt)}_{bar.close}.html")
            print(file_html)
            if os.path.exists(file_html):
                continue
            cf = CzscFactors(kg, factors=factors)
            cf.take_snapshot(file_html)
