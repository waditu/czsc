# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/23 19:12
describe:
"""
import os
import time
import pandas as pd
from tqdm import tqdm
from loguru import logger
from concurrent.futures import ProcessPoolExecutor
from czsc import fsa
from czsc.traders.base import generate_czsc_signals


class DummyBacktest:
    def __init__(self, strategy, signals_path, results_path, read_bars, **kwargs):
        """策略回测（支持多进程执行）

        :param strategy: CZSC择时策略
        :param signals_path: 信号文件存放路径
        :param results_path: 回测结果存放路径
        :param read_bars: 读入K线数据的函数
            函数签名为：read_bars(symbol, freq, sdt, edt, fq) -> List[RawBar]
        :param kwargs: 其他参数
            - signals_module_name: 信号函数模块名，用于动态加载信号文件，默认为 czsc.signals
        """
        from czsc.strategies import CzscStrategyBase
        assert issubclass(strategy, CzscStrategyBase), "strategy 必须是 CzscStrategyBase 的子类"
        self.strategy = strategy
        self.results_path = results_path
        os.makedirs(self.results_path, exist_ok=True)
        self.signals_path = signals_path
        os.makedirs(self.signals_path, exist_ok=True)
        # 缓存 poss 数据
        self.poss_path = os.path.join(results_path, 'poss')
        os.makedirs(self.poss_path, exist_ok=True)
        logger.add(os.path.join(self.results_path, 'dummy.log'), encoding='utf-8', enqueue=True)
        self.read_bars = read_bars
        self.kwargs = kwargs

        # 回测起止时间
        self.sdt = kwargs.get('sdt', '20100101')
        self.edt = kwargs.get('edt', '20230301')
        self.bars_sdt = pd.to_datetime(self.sdt) - pd.Timedelta(days=365*3)

    def replay(self, symbol):
        """回放单个品种的交易"""
        tactic = self.strategy(symbol=symbol, **self.kwargs)
        bars = self.read_bars(symbol, tactic.base_freq, self.sdt, self.edt, fq='后复权')
        tactic.replay(bars, os.path.join(self.results_path, f"{symbol}_replay"), sdt='20200101')

    def one_symbol_dummy(self, symbol):
        """回测单个品种"""
        start_time = time.time()
        tactic = self.strategy(symbol=symbol, **self.kwargs)
        symbol_path = os.path.join(self.poss_path, symbol)
        if os.path.exists(symbol_path):
            logger.info(f"{symbol} 已经回测过，跳过")
            return None

        os.makedirs(symbol_path, exist_ok=True)
        try:
            file_sigs = os.path.join(self.signals_path, f"{symbol}.sigs")
            if not os.path.exists(file_sigs):
                bars = self.read_bars(symbol, tactic.base_freq, self.bars_sdt, self.edt, fq='后复权')
                sigs = generate_czsc_signals(bars, signals_config=tactic.signals_config, sdt=self.sdt, df=True)
                sigs.drop(columns=['freq', 'cache'], inplace=True)
                sigs.to_parquet(file_sigs)
            else:
                sigs = pd.read_parquet(file_sigs)
                sigs = sigs[sigs['dt'] >= self.sdt]

            sigs = sigs.to_dict('records')
            trader = tactic.dummy(sigs)

        except Exception as e:
            logger.exception(e)
            return None

        for pos in trader.positions:
            try:
                file_pairs = os.path.join(symbol_path, f"{pos.name}.pairs")
                file_holds = os.path.join(symbol_path, f"{pos.name}.holds")

                pairs = pd.DataFrame(pos.pairs)
                pairs.to_parquet(file_pairs)

                dfh = pd.DataFrame(pos.holds)
                dfh['n1b'] = (dfh['price'].shift(-1) / dfh['price'] - 1) * 10000
                dfh.fillna(0, inplace=True)
                dfh['symbol'] = pos.symbol
                dfh.to_parquet(file_holds)
            except Exception as e:
                logger.debug(f"{symbol} {pos.name} 保存失败，原因：{e}")

        logger.info(f"{symbol} 回测完成，共 {len(trader.positions)} 个持仓策略，耗时 {time.time() - start_time:.2f} 秒")

    def one_pos_stats(self, pos_name):
        """分析单个持仓策略的表现"""
        from czsc.traders.performance import PairsPerformance

        symbols = os.listdir(self.poss_path)
        pos_pairs = []
        pos_holds = []
        for symbol in tqdm(symbols, desc=f"读取 {pos_name}"):
            try:
                dfp = pd.read_parquet(os.path.join(self.poss_path, f"{symbol}/{pos_name}.pairs"))
                pos_pairs.append(dfp)

                dfh = pd.read_parquet(os.path.join(self.poss_path, f"{symbol}/{pos_name}.holds"))
                pos_holds.append(dfh[dfh['pos'] != 0])
            except Exception as e:
                logger.debug(f"{symbol} 读取失败，原因：{e}")

        pairs = pd.concat(pos_pairs, ignore_index=True)
        if not pairs.empty:
            pp = PairsPerformance(pairs)
            pairs.to_feather(os.path.join(self.results_path, f"{pos_name}_pairs.feather"))
            pp.agg_to_excel(os.path.join(self.results_path, f"{pos_name}_回测结果.xlsx"))

            stats = dict(pp.basic_info)
            # 加入截面等权评价
            holds = pd.concat(pos_holds, ignore_index=True)
            cross = holds.groupby('dt').apply(lambda x: (x['n1b'] * x['pos']).sum() / sum(x['pos'] != 0))
            stats['截面等权收益'] = cross.sum()
            cross.to_excel(os.path.join(self.results_path, f"{pos_name}_截面等权收益.xlsx"), index=True)
            stats['pos_name'] = pos_name
            return stats
        else:
            return None

    def execute(self, symbols, n_jobs=2, **kwargs):
        """回测多个品种

        :param symbols: 品种列表
        :param n_jobs: 进程数量，默认为 2
            需要注意的是：
            1. 如果进程数过多，可能会导致内存不足
            2. 多进程在 pycharm 的 ipython 中无法使用，需要在命令行中运行
        :param kwargs:
        :return:
        """
        results_path = self.results_path
        tactic = self.strategy(symbol="symbol", **self.kwargs)
        dumps_map = {pos.name: pos.dump() for pos in tactic.positions}

        logger.info(f"策略回测，持仓策略数量：{len(tactic.positions)}，共 {len(symbols)} 只标的，使用 {n_jobs} 个进程；"
                    f"结果保存在 {results_path}。请耐心等待...")

        with ProcessPoolExecutor(n_jobs) as pool:
            pool.map(self.one_symbol_dummy, sorted(symbols))

        all_stats = []
        with ProcessPoolExecutor(max_workers=min(n_jobs, 6)) as pool:
            _stats = pool.map(self.one_pos_stats, list(dumps_map.keys()))
            for _s in _stats:
                if not _s:
                    continue
                _s['pos_dump'] = dumps_map[_s['pos_name']]
                all_stats.append(_s)

        file_report = os.path.join(results_path, f'{self.strategy.__name__}_回测结果汇总.xlsx')
        report_df = pd.DataFrame(all_stats).sort_values(['截面等权收益'], ascending=False, ignore_index=True)
        report_df.to_excel(file_report, index=False)
        logger.info(f"策略回测完成，结果保存在 {results_path}。")

        if kwargs.get('feishu_app_id') and kwargs.get('feishu_app_secret'):
            if os.path.exists(file_report):
                fsa.push_message(file_report, msg_type='file', **kwargs)
            else:
                fsa.push_message(f"{self.strategy.__name__} 回测结果为空，请检查原因！", **kwargs)
