# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/10 19:45
describe: 30分钟笔非多即空策略
"""
import os
import os
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '...')
sys.path.insert(0, '../../..')
# # 插入用户自定义信号函数模块所在目录
sys.path.insert(0, os.path.join(os.path.expanduser('~'), 'd:/stock/czsc/czsc/signals'))

import czsc
from pathlib import Path
from loguru import logger
from czsc.connectors import research
from czsc import Event, Position
from czsc.traders.sig_parse import SignalsParser
import czsc.connectors.qmt_connector as qn
from czsc.signals import dkx
import concurrent.futures
from tqdm import tqdm




def trading_strategy_dkx_V240427(symbol, **kwargs):
    """30分钟多空线非多即空策略

    使用的信号函数：

    https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230101.html
    """
    opens = [
        {
            "operate": "开多",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["30分钟_D1DKX#DEX_V240427_多头_向上_任意_0"],
                    "signals_any": [],
                    "signals_not": [],
                }
            ],
        },
        {
            "operate": "开空",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["日线_D1DKX#DEX_V240427_空头_向下_任意_0"],
                    "signals_any": [],
                    "signals_not": [],
                }
            ],
        },
    ]

    exits = []
    
    pos = Position(
        name="30分钟多空线非多即空",
        symbol=symbol,
        opens=[Event.load(x) for x in opens],
        exits=[Event.load(x) for x in exits],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )
    return pos

def trading_strategy_dkx_dir_V240428(symbol, **kwargs):
    """30分钟、日线、周线共振开多开空点

    使用的信号函数：

    https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230101.html
    """
    opens = [
        {
            "operate": "开多",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["30分钟_D1T3#3_V240428_买点_任意_任意_0","日线_D1DKX#DEX_V240427_其他_向上_任意_0","周线_D1DKX#DEX_V240427_其他_向上_任意_0","月线_D1DKX#DEX_V240427_其他_向上_任意_0"],
                    "signals_any": [],
                    "signals_not": [],
                }
            ],
        },
        {
            "operate": "平多",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["日线_D1T3#3_V240428_卖点_任意_任意_0"],
                    "signals_any": [],
                    "signals_not": [],
                }
            ],
        },
    ]

    exits = []

    pos = Position(
        name="30分钟开多开空点",
        symbol=symbol,
        opens=[Event.load(x) for x in opens],
        exits=[Event.load(x) for x in exits],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )
    return pos

def trading_strategy_dkx_dir_V240429(symbol, **kwargs):
    """30分钟开多开空点

    使用的信号函数：

    https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230101.html
    """
    opens = [
        {
            "operate": "开多",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["30分钟_D1T3#3_V240428_买点_任意_任意_0","日线_D1DKX#DEX_V240427_其他_向上_任意_0","周线_D1DKX#DEX_V240427_其他_向上_任意_0"],
                    "signals_any": [],
                    "signals_not": [],
                }
            ],
        },
        {
            "operate": "开空",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["30分钟_D1T3#3_V240428_卖点_任意_任意_0"],
                    "signals_any": [],
                    "signals_not": ["日线_D1DKX#DEX_V240427_其他_向上_任意_0"],
                }
            ],
        },
    ]

    exits = []

    pos = Position(
        name="30分钟开多开空点",
        symbol=symbol,
        opens=[Event.load(x) for x in opens],
        exits=[Event.load(x) for x in exits],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )
    return pos

def backtest(stock):
    results_path = Path(r'D:\CZSC投研数据\策略研究\双周期多点v0429')
    logger.add(results_path / f"czsc_{stock}.log", rotation="1 week", encoding="utf-8")
    results_path.mkdir(exist_ok=True, parents=True)

    tactic = Strategy(symbol=stock, is_stocks=True)

    # 使用 logger 记录策略的基本信息
    logger.info(f"K线周期列表：{tactic.freqs}")
    logger.info(f"信号函数配置列表：{tactic.signals_config}")

    bars = qn.get_raw_bars(stock, '30分钟', '20150101', '20240426', fq='不复权')
    trader = tactic.replay(bars, sdt='20210101', res_path=results_path / f"replay_{stock}", refresh=True)

    # 当策略执行过程符合预期后，将持仓策略保存到本地 json 文件中
    tactic.save_positions(results_path / f"positions_{stock}")

class Strategy(czsc.CzscStrategyBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_stocks = kwargs.get('is_stocks', True)

    @property
    def positions(self):
        pos_list = [
            # create_long_short_V230908(self.symbol),
            trading_strategy_dkx_dir_V240429(self.symbol, base_freq='30分钟'),
            
        ]
        return pos_list

if __name__ == '__main__':
    # 获取CPU的核心数
    cpu_count = os.cpu_count()
    
    '''从本地文件中读取股票列表,并整合股票代码'''
    # with open('d:/cldkx/天狼股池.txt', 'r') as file:
    #     stock_list = []
    #     for line in file.readlines():
    #         parts = line.strip().split()
    #         if len(parts) > 0:
    #             code, name = parts[0], parts[1]
    #             new_code = code[2:] + '.' + code[:2]
    #             stock_list.append(new_code)
    
    '''输入股票列表'''    
    stock_list = ['600519.SH']

    # 使用线程池进行并行处理，设定最大线程数为10
    with concurrent.futures.ThreadPoolExecutor(max_workers=24) as executor:
        list(tqdm(executor.map(backtest, stock_list), total=len(stock_list)))
