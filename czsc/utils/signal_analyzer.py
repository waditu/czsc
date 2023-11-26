# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/30 21:13
describe:
"""
import os
import hashlib
import pandas as pd
from copy import deepcopy
from tqdm import tqdm
from loguru import logger
from typing import List, AnyStr
from concurrent.futures import ProcessPoolExecutor


class SignalPerformance:
    """信号表现分析"""

    def __init__(self, dfs: pd.DataFrame, keys: List[AnyStr]):
        """

        :param dfs: 信号表
        :param keys: 信号列，支持一个或多个信号列组合分析
        """
        base_cols = [x for x in dfs.columns if len(x.split("_")) != 3]
        dfs = dfs[base_cols + keys].copy()

        if 'year' not in dfs.columns:
            y = dfs['dt'].apply(lambda x: x.year)
            dfs['year'] = y.values

        self.dfs = dfs
        self.keys = keys
        self.b_cols = [x for x in dfs.columns if x[0] == 'b' and x[-1] == 'b']
        self.n_cols = [x for x in dfs.columns if x[0] == 'n' and x[-1] == 'b']

    def __return_performance(self, dfs: pd.DataFrame, mode: str = '1b') -> pd.DataFrame:
        """分析信号组合的分类能力，也就是信号出现前后的收益情况

        :param dfs: 信号数据表，
        :param mode: 分析模式，
            0b 截面向前看
            0n 截面向后看
            1b 时序向前看
            1n 时序向后看
        :return:
        """
        mode = mode.lower()
        assert mode in ['0b', '0n', '1b', '1n']
        keys = self.keys
        len_dfs = len(dfs)
        cols = self.b_cols if mode.endswith('b') else self.n_cols

        sdt = dfs['dt'].min().strftime("%Y%m%d")
        edt = dfs['dt'].max().strftime("%Y%m%d")

        def __static(_df, _name):
            _res = {"name": _name, "date_span": f"{sdt} ~ {edt}",
                    "count": len(_df), "cover": round(len(_df) / len_dfs, 4)}
            if mode.startswith('0'):
                _r = _df.groupby('dt')[cols].mean().mean().to_dict()
            else:
                _r = _df[cols].mean().to_dict()
            _res.update(_r)
            return _res

        results = [__static(dfs, "基准")]

        for values, dfg in dfs.groupby(by=keys if len(keys) > 1 else keys[0]):
            if isinstance(values, str):
                values = [values]
            assert isinstance(keys, (list, tuple)) and isinstance(values, (list, tuple))
            assert len(keys) == len(values)

            name = "#".join([f"{key1}_{name1}" for key1, name1 in zip(keys, values)])
            results.append(__static(dfg, name))

        dfr = pd.DataFrame(results)
        dfr[cols] = dfr[cols].round(2)
        return dfr

    def analyze(self, mode='0b') -> pd.DataFrame:
        """分析信号出现前后的收益情况

        :param mode: 分析模式，
            0b 截面向前看
            0n 截面向后看
            1b 时序向前看
            1n 时序向后看
        :return:
        """
        dfr = self.__return_performance(self.dfs, mode)
        results = [dfr]
        for year, df_ in self.dfs.groupby('year'):
            dfr_ = self.__return_performance(df_, mode)
            results.append(dfr_)
        dfr = pd.concat(results, ignore_index=True)
        return dfr

    def report(self, file_xlsx=None):
        res = {
            '向后看截面': self.analyze('0n'),
            '向后看时序': self.analyze('1n'),
        }
        if file_xlsx:
            writer = pd.ExcelWriter(file_xlsx)
            for sn, df_ in res.items():
                df_.to_excel(writer, sheet_name=sn, index=False)
            writer.close()
        return res


class SignalAnalyzer:
    def __init__(self, symbols, read_bars, signals_config, results_path, **kwargs):
        """信号分析

        :param symbols: 品种列表
        :param read_bars: 读取K线的函数
        :param signals_config: 信号配置
        :param results_path: 结果保存路径
        :param kwargs: 其他参数
            - sdt: 信号生成的开始时间
            - edt: 信号生成的结束时间
            - bar_sdt: 读取K线的开始时间
        """
        self.version = 'V230520'
        self.symbols = symbols
        self.read_bars = read_bars
        self.signals_config = signals_config
        self.results_path = results_path
        os.makedirs(self.results_path, exist_ok=True)
        self.signals_path = os.path.join(self.results_path, 'signals')
        os.makedirs(self.signals_path, exist_ok=True)
        self.kwargs = kwargs
        self.task_hash = hashlib.sha256((str(signals_config) + str(symbols)).encode('utf-8')).hexdigest()[:8].upper()

    def generate_symbol_signals(self, symbol):
        from czsc.traders.sig_parse import get_signals_freqs
        from czsc.traders.base import generate_czsc_signals
        from czsc.utils.trade import update_nbars

        try:
            file_cache = os.path.join(self.signals_path, f"{symbol}.parquet")
            if os.path.exists(file_cache):
                sigs = pd.read_parquet(file_cache)
            else:
                freqs = get_signals_freqs(deepcopy(self.signals_config))
                sdt = self.kwargs.get('sdt', '20170101')
                edt = self.kwargs.get('edt', '20220101')
                bar_sdt = self.kwargs.get('bar_sdt', '20150101')
                bars = self.read_bars(symbol, freqs[0], bar_sdt, edt, fq='后复权')
                if len(bars) < 100:
                    logger.error(f"{symbol} 信号生成失败：数据量不足")
                    return pd.DataFrame()

                sigs: pd.DataFrame = generate_czsc_signals(bars, deepcopy(self.signals_config), sdt=sdt, df=True) # type: ignore
                if sigs.empty:
                    logger.error(f"{symbol} 信号生成失败：数据量不足")
                    return pd.DataFrame()

                sigs.drop(['freq', 'cache'], axis=1, inplace=True)
                update_nbars(sigs, price_col='open', move=1,
                             numbers=(1, 2, 3, 5, 8, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100))
                sigs.to_parquet(file_cache)
            return sigs
        except Exception as e:
            logger.exception(e)
            logger.error(f"{symbol} 信号生成失败: {e}")
            return pd.DataFrame()

    @staticmethod
    def find_valuable_signals(dfp):
        """根据信号表现，找出表现好的信号

        :param dfp: 信号表现分析结果
        :return: 表现好的信号
        """
        n_cols = [x for x in dfp.columns if x.startswith('n') and x.endswith('b')]
        # 价值描述：1）与基准的差值越大越好；2）与基准的差值越大，且胜率越高越好
        rows = []
        for _, dfg in dfp.groupby('date_span'):
            base = dfg[dfg['name'] == '基准'].iloc[0].to_dict()
            olds = dfg[dfg['name'] != '基准'].to_dict(orient='records')
            sum_base = sum([base[x] for x in n_cols])

            for row in olds:
                if '其他' in row['name']:
                    continue

                delta = [row[x] - base[x] for x in n_cols]
                win_rate = sum([1 if x > 0 else 0 for x in delta]) / len(delta)
                row['delta_win_rate'] = win_rate
                sum_delta = sum(delta)
                if abs(sum_delta) / sum_base < 0.1:
                    continue

                if (win_rate > 0.7 and sum_delta > 0) or (win_rate < 0.3 and sum_delta < 0):
                    rows.append(row)

        return pd.DataFrame(rows)

    def execute(self, max_workers=10):
        """执行信号分析"""
        symbols_sig = []
        if max_workers <= 1:
            for symbol in tqdm(self.symbols, desc="生成信号"):
                sigs = self.generate_symbol_signals(symbol)
                if not sigs.empty:
                    symbols_sig.append(sigs)
        else:
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                results = executor.map(self.generate_symbol_signals, self.symbols)
                for result in results:
                    if not result.empty:
                        symbols_sig.append(result)

        results_path = self.results_path
        dfs = pd.concat(symbols_sig, ignore_index=True)

        sig_keys = [x for x in dfs.columns if len(x.split("_")) == 3]
        sps = {'向后看截面': [], '向后看时序': []}

        raw_results_path = os.path.join(results_path, 'raw_results')
        os.makedirs(raw_results_path, exist_ok=True)
        for key in tqdm(sig_keys, desc="分析信号表现"):
            sp = SignalPerformance(dfs, keys=[key])
            res = sp.report(os.path.join(raw_results_path, f'{key}.xlsx'))
            for k, v in res.items():
                sps[k].append(v)

        for k, v in sps.items():
            dfp = pd.concat(v, ignore_index=True)
            dfp.drop_duplicates(subset=['name', 'date_span'], inplace=True, ignore_index=True)
            dfp.to_excel(os.path.join(results_path, f'{self.task_hash}_{k}_汇总.xlsx'), index=False)
            dfp_valuable = self.find_valuable_signals(dfp)
            dfp_valuable.to_excel(os.path.join(results_path, f'{self.task_hash}_{k}_有价值信号.xlsx'), index=False)
