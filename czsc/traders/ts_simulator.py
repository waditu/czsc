# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/5 23:09
describe: 基于Tushare数据的仿真跟踪
"""
import os
import inspect
import pandas as pd
from tqdm import tqdm
from loguru import logger
from typing import Callable, List
from czsc import envs
from czsc.data import TsDataCache, freq_cn2ts
from czsc.utils import BarGenerator, dill_load, dill_dump
from czsc.objects import RawBar
from czsc.traders.advanced import CzscAdvancedTrader
from czsc.traders.performance import PairsPerformance


pd.set_option('display.max_rows', 600)
pd.set_option('display.max_columns', 30)


class TradeSimulator:
    """交易策略仿真跟踪"""

    def __init__(self, dc: TsDataCache, strategy: Callable, res_path=None, init_n=500):
        self.name = self.__class__.__name__
        self.dc = dc
        self.strategy = strategy
        self.tactic = strategy("000001")
        self.base_freq = self.tactic['base_freq']
        self.freqs = self.tactic['freqs']
        self.init_n = init_n

        self.data_path = dc.data_path
        if not res_path:
            self.res_path = os.path.join(self.data_path, f"simulator_{strategy.__name__}_mbl{envs.get_min_bi_len()}")
        else:
            self.res_path = res_path
        os.makedirs(self.res_path, exist_ok=True)
        os.makedirs(os.path.join(self.res_path, 'traders'), exist_ok=True)

        file_strategy = os.path.join(self.res_path, f'{strategy.__name__}_strategy.txt')
        with open(file_strategy, 'w', encoding='utf-8') as f:
            f.write(inspect.getsource(strategy))
        logger.info(f"strategy saved into {file_strategy}")

    def get_bars(self, ts_code: str, asset: str, sdt=None) -> List[RawBar]:
        """获取指定周期K线序列

        :param ts_code: 标的代码
        :param asset: 资产类别
        :param sdt: 开始时间
        :return:
        """
        base_freq = self.base_freq
        dc = self.dc
        freq = freq_cn2ts[base_freq]
        sdt = dc.sdt if not sdt else sdt
        if "分钟" in base_freq:
            bars = dc.pro_bar_minutes(ts_code, sdt, dc.edt, freq=freq, asset=asset, adj='hfq', raw_bar=True)
        else:
            bars = dc.pro_bar(ts_code, sdt, dc.edt, freq=freq, asset=asset, adj='hfq', raw_bar=True)
        return bars

    def get_file_trader(self, ts_code, asset):
        return os.path.join(self.res_path, f"traders/{ts_code}_{asset}.cat")

    def create_trader(self, ts_code, asset="E"):
        """创建单个标的交易员"""
        file_trader = self.get_file_trader(ts_code, asset)
        if os.path.exists(file_trader):
            trader: CzscAdvancedTrader = dill_load(file_trader)
            return trader

        # 获取K线，创建交易员
        init_ = self.init_n
        bars = self.get_bars(ts_code, asset)
        bg = BarGenerator(self.base_freq, self.freqs, max_count=5000)
        for bar in bars[:init_]:
            bg.update(bar)

        trader = CzscAdvancedTrader(bg, self.strategy)
        for bar in tqdm(bars[init_:], desc=f"{ts_code} trader"):
            trader.update(bar)

        dill_dump(trader, file_trader)
        return trader

    def get_trader(self, ts_code, asset="E"):
        """获取单个标的交易员"""
        file_trader = self.get_file_trader(ts_code, asset)
        if os.path.exists(file_trader):
            trader: CzscAdvancedTrader = dill_load(file_trader)
        else:
            trader: CzscAdvancedTrader = self.create_trader(ts_code, asset)
        return trader

    def update_trader(self, ts_code, asset="E"):
        """更新单个标的"""
        logger.info(f"{os.getpid()} {ts_code}#{asset} start updating")

        file_trader = self.get_file_trader(ts_code, asset)
        if os.path.exists(file_trader):
            trader: CzscAdvancedTrader = dill_load(file_trader)
        else:
            trader: CzscAdvancedTrader = self.create_trader(ts_code, asset)

        bars = self.get_bars(ts_code, asset, trader.end_dt)
        bars = [x for x in bars if x.dt > trader.bg.end_dt]
        logger.info(f"{os.getpid()} {ts_code}#{asset} 有{len(bars)}根K线需要更新")

        for bar in bars:
            trader.update(bar)
        dill_dump(trader, file_trader)
        return trader

    def update_traders(self, ts_codes, asset="E"):
        """批量执行更新

        :param ts_codes: 交易标的列表
        :param asset: 资产类别
        :return:
        """
        long_pairs = []
        for ts_code in tqdm(ts_codes, desc=f"update_traders | {asset}"):
            try:
                trader = self.update_trader(ts_code, asset)
                logger.info(f"\n{self.strategy.__name__} : {trader.results['long_performance']}")
                if trader.long_pos:
                    long_pairs.extend(trader.long_pos.pairs)
            except:
                logger.exception(f"fail on {ts_code}#{asset}")

        if long_pairs:
            # lpp = Long Pairs Performance
            lpp = PairsPerformance(pd.DataFrame(long_pairs))
            lpp.agg_to_excel(os.path.join(self.res_path, f'long_pairs_{asset}_report.xlsx'))
            lpp.df_pairs.to_feather(os.path.join(self.res_path, f'long_pairs_{asset}.feather'))
            logger.info(f"{lpp.basic_info}\n\n{lpp.agg_statistics('平仓年')}")
