# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/21 20:04
describe: 
"""
import os
import glob
import json
import shutil
import pandas as pd
from loguru import logger
from tqdm import tqdm
from datetime import datetime
from czsc.traders.utils import trade_replay
from czsc.traders.advanced import CzscDummyTrader
from czsc.sensors.utils import generate_signals
from czsc.traders.performance import PairsPerformance
from czsc.utils import BarGenerator, get_py_namespace, dill_dump, dill_load, WordWriter


class DummyBacktest:
    def __init__(self, file_strategy):
        """

        :param file_strategy: 策略定义文件，必须是 .py 结尾
        """
        res_path = get_py_namespace(file_strategy)['results_path']
        os.makedirs(res_path, exist_ok=True)
        self.signals_path = os.path.join(res_path, "signals")
        self.results_path = os.path.join(res_path, f"DEXP_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(self.signals_path, exist_ok=True)
        os.makedirs(self.results_path, exist_ok=True)

        # 创建 CzscDummyTrader 缓存路径
        self.cdt_path = os.path.join(self.results_path, 'cache')
        os.makedirs(self.cdt_path, exist_ok=True)

        self.strategy_file = os.path.join(self.results_path, os.path.basename(file_strategy))
        shutil.copy(file_strategy, self.strategy_file)

        self.__debug = get_py_namespace(self.strategy_file).get('debug', False)
        logger.add(os.path.join(self.results_path, 'dummy.log'))

    def replay(self):
        """执行策略回放"""
        py = get_py_namespace(self.strategy_file)
        strategy = py['trader_strategy']
        replay_params = py.get('replay_params', {})

        # 获取单个品种的基础周期K线
        tactic = strategy("000001.SZ")
        symbol = replay_params.get('symbol', py['dummy_params']['symbols'][0])
        sdt = pd.to_datetime(replay_params.get('sdt', '20170101'))
        mdt = pd.to_datetime(replay_params.get('mdt', '20200101'))
        edt = pd.to_datetime(replay_params.get('edt', '20220101'))
        bars = py['read_bars'](symbol, sdt, edt)
        logger.info(f"交易回放参数 | {symbol} | 时间区间：{sdt} ~ {edt}")

        # 设置回放快照文件保存目录
        res_path = os.path.join(self.results_path, f"replay_{symbol}")
        os.makedirs(res_path, exist_ok=True)

        # 拆分基础周期K线，一部分用来初始化BarGenerator，随后的K线是回放区间
        bg = BarGenerator(tactic['base_freq'], freqs=tactic['freqs'])
        bars1 = [x for x in bars if x.dt <= mdt]
        bars2 = [x for x in bars if x.dt > mdt]
        for bar in bars1:
            bg.update(bar)

        trade_replay(bg, bars2, strategy, res_path)

    def generate_symbol_signals(self, symbol):
        """生成指定品种的交易信号

        :param symbol:
        :return:
        """
        py = get_py_namespace(self.strategy_file)
        sdt, mdt, edt = py['dummy_params']['sdt'], py['dummy_params']['mdt'], py['dummy_params']['edt']

        bars = py['read_bars'](symbol, sdt, edt)
        signals = generate_signals(bars, sdt=mdt, strategy=py['trader_strategy'])

        df = pd.DataFrame(signals)
        if 'cache' in df.columns:
            del df['cache']

        c_cols = [k for k, v in df.dtypes.to_dict().items() if v.name.startswith('object')]
        df[c_cols] = df[c_cols].astype('category')

        float_cols = [k for k, v in df.dtypes.to_dict().items() if v.name.startswith('float')]
        df[float_cols] = df[float_cols].astype('float32')
        return df

    def execute(self):
        """执行策略文件中定义的内容"""
        signals_path = self.signals_path
        py = get_py_namespace(self.strategy_file)

        strategy = py['trader_strategy']
        symbols = py['dummy_params']['symbols']

        for symbol in symbols:
            file_dfs = os.path.join(signals_path, f"{symbol}_signals.pkl")

            try:
                # 可以直接生成信号，也可以直接读取信号
                if os.path.exists(file_dfs):
                    dfs = pd.read_pickle(file_dfs)
                else:
                    dfs = self.generate_symbol_signals(symbol)
                    dfs.to_pickle(file_dfs)

                if len(dfs) == 0:
                    continue

                cdt = CzscDummyTrader(dfs, strategy)
                dill_dump(cdt, os.path.join(self.cdt_path, f"{symbol}.cdt"))

                res = cdt.results
                if "long_performance" in res.keys():
                    logger.info(f"{res['long_performance']}")

                if "short_performance" in res.keys():
                    logger.info(f"{res['short_performance']}")
            except Exception as e:
                msg = f"fail on {symbol}: {e}"
                if self.__debug:
                    logger.exception(msg)
                else:
                    logger.warning(msg)

    def collect(self):
        """汇集回测结果"""
        res = {'long_pairs': [], 'lpf': [], 'short_pairs': [], 'spf': []}
        files = glob.glob(f"{self.cdt_path}/*.cdt")
        for file in tqdm(files, desc="DummyBacktest::collect"):
            cdt = dill_load(file)

            if cdt.results.get("long_pairs", None):
                res['lpf'].append(cdt.results['long_performance'])
                res['long_pairs'].append(pd.DataFrame(cdt.results['long_pairs']))

            if cdt.results.get("short_pairs", None):
                res['spf'].append(cdt.results['short_performance'])
                res['short_pairs'].append(pd.DataFrame(cdt.results['short_pairs']))

        if res['long_pairs'] and res['lpf']:
            long_ppf = PairsPerformance(pd.concat(res['long_pairs']))
            res['long_ppf_basic'] = long_ppf.basic_info
            res['long_ppf_year'] = long_ppf.agg_statistics('平仓年')
            long_ppf.agg_to_excel(os.path.join(self.results_path, 'long_ppf.xlsx'))

        if res['short_pairs'] and res['spf']:
            short_ppf = PairsPerformance(pd.concat(res['short_pairs']))
            res['short_ppf_basic'] = short_ppf.basic_info
            res['short_ppf_year'] = short_ppf.agg_statistics('平仓年')
            short_ppf.agg_to_excel(os.path.join(self.results_path, 'short_ppf.xlsx'))

        return res

    def report(self):
        py = get_py_namespace(self.strategy_file)
        strategy = py['trader_strategy']('symbol')

        res = self.collect()
        file_word = os.path.join(self.results_path, "report.docx")
        if os.path.exists(file_word):
            os.remove(file_word)
        writer = WordWriter(file_word)

        writer.add_title("策略Dummy回测分析报告")
        writer.add_heading("一、基础信息", level=1)
        if strategy.get('long_events', None):
            writer.add_heading("多头事件定义",  level=2)
            writer.add_paragraph(json.dumps([x.dump() for x in strategy['long_events']],
                                            ensure_ascii=False, indent=4), first_line_indent=0)

        if strategy.get('short_events', None):
            writer.add_heading("空头事件定义", level=2)
            writer.add_paragraph(json.dumps([x.dump() for x in strategy['short_events']], ensure_ascii=False, indent=4))
            writer.add_paragraph('\n')

        writer.add_heading("二、回测分析", level=1)
        if res.get("long_ppf_basic", None):
            writer.add_heading("多头表现",  level=2)
            lpb = pd.DataFrame([res['long_ppf_basic']]).T.reset_index()
            lpb.columns = ['名称', '取值']
            writer.add_df_table(lpb)
            writer.add_paragraph('\n')

            lpy = res['long_ppf_year'].T.reset_index()
            lpy.columns = lpy.iloc[0]
            lpy = lpy.iloc[1:]
            writer.add_df_table(lpy)
            writer.add_paragraph('\n')

        if res.get("short_ppf_basic", None):
            writer.add_heading("空头表现",  level=2)
            pb = pd.DataFrame([res['short_ppf_basic']]).T.reset_index()
            pb.columns = ['名称', '取值']
            writer.add_df_table(pb)
            writer.add_paragraph('\n')

            py = res['short_ppf_year'].T.reset_index()
            py.columns = py.iloc[0]
            py = py.iloc[1:]
            writer.add_df_table(py)
            writer.add_paragraph('\n')

        writer.save()



