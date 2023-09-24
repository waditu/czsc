# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/24 13:33
describe: 择时策略开平仓优化
"""
import os
import czsc
import time
import hashlib
import pandas as pd
from tqdm import tqdm
from loguru import logger
from copy import deepcopy
from pathlib import Path
from typing import Callable, Union, List, AnyStr
from czsc.strategies import CzscStrategyBase
from czsc.objects import Position, Event
from concurrent.futures import ProcessPoolExecutor, as_completed


class CzscOpenOptimStrategy(CzscStrategyBase):

    @staticmethod
    def update_beta_opens(beta: Position, open_signals_all: Union[List[AnyStr], AnyStr]):
        """更新 beta 出场信号"""
        pos = deepcopy(beta)
        assert len(pos.opens) == 1, "基础策略入场信号必须为单个Event"
        if isinstance(open_signals_all, str):
            open_signals_all = [open_signals_all]

        pos_dict = pos.dump()
        sig_hash = hashlib.md5(f"{open_signals_all}".encode('utf-8')).hexdigest()[:8].upper()
        pos_dict['name'] = f"{pos.name}#{sig_hash}"
        pos_dict['opens'][0]['signals_all'].extend(open_signals_all)
        return Position.load(pos_dict)

    @property
    def positions(self):
        betas = self.load_positions(self.kwargs['files_position'])
        candidate_signals = deepcopy(self.kwargs['candidate_signals'])
        pos_list = deepcopy(betas)
        for beta in betas:
            for sigs_ in candidate_signals:
                pos = self.update_beta_opens(beta, sigs_)
                pos_list.append(pos)
        return pos_list


class CzscExitOptimStrategy(CzscStrategyBase):

    @staticmethod
    def update_beta_exits(beta: Position, event_dict: dict, mode='replace'):
        """更新 beta 出场信号

        出场优化，有三种路径：

        1. 开仓后识别走势加速，找个合适的机会提前平仓
        2. 根据开仓后一段时间内的走势，如果发现异样，提前平仓
        3. 用新的出场信号完全替换旧的出场信号

        """
        pos = deepcopy(beta)
        event: Event = Event.load(deepcopy(event_dict))
        event_hash = hashlib.md5(f"{event.dump()}".encode('utf-8')).hexdigest()[:8].upper()
        open_ops = [x.operate.value for x in pos.opens]

        if all(x == '开多' for x in open_ops) and event.operate.value != '平多':
            return None

        if all(x == '开空' for x in open_ops) and event.operate.value != '平空':
            return None

        assert mode in ['replace', 'append'], "mode must be replace or append"
        if mode == 'replace':
            pos.exits = [deepcopy(event)]
            pos.name = f"{beta.name}#替换{event_hash}"
        else:
            pos.exits.append(deepcopy(event))
            pos.name = f"{beta.name}#追加{event_hash}"

        # 踩坑记录：对于 dataclass 对象，如果直接修改属性，会导致原对象也被修改，因此这里需要重新创建一个对象
        return Position.load(pos.dump())

    @property
    def positions(self):
        betas = self.load_positions(self.kwargs['files_position'])
        candidate_events = deepcopy(self.kwargs['candidate_events'])  # 优化出场信号
        pos_list = deepcopy(betas)

        for beta in betas:
            for event in candidate_events:

                pos1 = self.update_beta_exits(beta, event, mode='append')
                pos2 = self.update_beta_exits(beta, event, mode='replace')

                if pos1 is not None:
                    pos_list.append(pos1)
                if pos2 is not None:
                    pos_list.append(pos2)

        return pos_list


def one_symbol_optim(symbol, read_bars: Callable, path: str, **kwargs):
    """单个标的优化

    :param symbol: 标的代码
    :param read_bars: K线数据读取函数
    :param path: 优化结果保存路径
    :param kwargs: 其他参数

        - bar_sdt: K线数据开始日期
        - bar_edt: K线数据结束日期
        - sdt: 优化开始日期
        - optim_type: 优化类型，open 或 exit

    """
    symbol_path = Path(path) / symbol
    if symbol_path.exists():
        logger.info(f"{symbol} dummy 结果已经存在")
        return
    symbol_path.mkdir(parents=True, exist_ok=True)

    bar_sdt = kwargs.get('bar_sdt', '20150101')
    bar_edt = kwargs.get('bar_edt', '20220101')
    sdt = kwargs.get('sdt', '20170101')
    assert bar_sdt < sdt < bar_edt, "sdt 必须在 bar_sdt 和 bar_edt 之间"

    start_time = time.time()
    optim_type = kwargs.get('optim_type', 'open')
    if optim_type == 'open':
        tactic = CzscOpenOptimStrategy(symbol=symbol, **kwargs)
    else:
        assert optim_type == 'exit', "optim_type must be open or exit"
        tactic = CzscExitOptimStrategy(symbol=symbol, **kwargs)

    try:
        bars = read_bars(symbol, tactic.base_freq, bar_sdt, bar_edt, fq='后复权', raw_bar=True)
        if len(bars) < 100:
            logger.warning(f"{symbol} K线数量不足，无法优化")
            return None

        trader = tactic.backtest(bars, sdt=sdt)
    except Exception as e:
        logger.exception(f"{symbol} 优化失败，原因：{e}")
        return None

    for pos in trader.positions:            # type: ignore
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

    logger.info(f"{symbol} - {optim_type} 优化完成，耗时 {time.time() - start_time:.2f} 秒")


def one_position_stats(path, pos_name):
    """分析单个 pos 的表现"""
    path = Path(path)
    files_p = path.glob(f"**/{pos_name}.pairs")
    files_h = path.glob(f"**/{pos_name}.holds")

    pos_pairs = []
    for file_p in files_p:
        try:
            dfp = pd.read_parquet(file_p)
            pos_pairs.append(dfp)
        except Exception as e:
            logger.debug(f"{file_p} 读取失败，原因：{e}")

    pos_holds = []
    for file_h in files_h:
        try:
            dfh = pd.read_parquet(file_h)
            pos_holds.append(dfh)
        except Exception as e:
            logger.debug(f"{file_h} 读取失败，原因：{e}")

    pairs = pd.concat(pos_pairs, ignore_index=True)
    holds = pd.concat(pos_holds, ignore_index=True)

    if len(pairs) == 0 or len(holds) == 0:
        return None

    try:
        pp = czsc.PairsPerformance(pairs)
        stats = dict(pp.basic_info)
        # 加入截面等权评价
        cross = holds.groupby('dt').apply(lambda x: (x['n1b'] * x['pos']).sum() / (sum(x['pos'] != 0) + 1)).sum()
        stats['截面等权收益'] = cross
        cross1 = holds.groupby('dt').apply(lambda x: (x['n1b'] * x['pos']).mean()).sum()
        stats['截面品种等权'] = cross1
        stats['pos_name'] = pos_name
        return stats
    except Exception as e:
        logger.exception(f"{pos_name} 分析失败，原因：{e}")
        return None


class OpensOptimize:
    """基础策略入场优化流程"""

    def __init__(self, read_bars: Callable, **kwargs):
        """

        :param read_bars: K线数据读取函数
        :param kwargs: 其他参数

            - symbols: 优化标的列表
            - candidate_events: 优化出场信号列表
            - results_path: 优化结果保存路径
            - files_position: 优化入场信号文件路径列表
            - signals_module_name: 信号模块名
            - bar_sdt: K线数据开始日期
            - bar_edt: K线数据结束日期

        """
        self.version = 'OpensOptimizeV230924'
        self.symbols = sorted(kwargs['symbols'])
        self.read_bars = read_bars
        self.kwargs = kwargs
        self.task_name = kwargs.get('task_name', '出场优化')
        self.candidate_signals = sorted(kwargs.pop('candidate_signals'))
        self.task_hash = hashlib.md5(f"{self.candidate_signals}_{self.symbols}".encode('utf-8')).hexdigest()[:8].upper()

        results_path = os.path.join(kwargs['results_path'], f"{self.task_name}_{self.task_hash}")
        os.makedirs(results_path, exist_ok=True)
        self.poss_path = os.path.join(results_path, 'poss')
        os.makedirs(self.poss_path, exist_ok=True)

        self.results_path = results_path
        logger.add(f"{self.results_path}\\信号优化.log", encoding='utf-8', enqueue=True)
        logger.info(f"{self.task_name} | {self.candidate_signals} | 其他参数：{kwargs}")

    def _one_symbol_optim(self, symbol):
        one_symbol_optim(symbol, self.read_bars, self.poss_path, optim_type='open',
                         candidate_signals=self.candidate_signals, **self.kwargs)

    def _one_pos_stats(self, pos_name):
        return one_position_stats(self.poss_path, pos_name)

    def __symbols_optim(self, n_jobs=1):
        symbols = self.symbols
        if n_jobs <= 1:
            for symbol in tqdm(sorted(symbols), desc="优化进度"):
                self._one_symbol_optim(symbol)
            return

        with ProcessPoolExecutor(n_jobs) as pool:
            pool.map(self._one_symbol_optim, sorted(symbols))

    def _positions_stats(self, dumps_map, n_jobs=1):
        """统计所有 pos 的表现"""
        if n_jobs <= 1:
            all_stats = [self._one_pos_stats(pos_name) for pos_name in dumps_map.keys()]
            for s, pos_name in zip(all_stats, dumps_map.keys()):
                if not s:
                    continue
                s['pos_dump'] = dumps_map[pos_name]
            return all_stats

        all_stats = []
        with ProcessPoolExecutor(n_jobs) as pool:
            futures = [pool.submit(self._one_pos_stats, pos_name) for pos_name in dumps_map.keys()]
            for future in as_completed(futures):
                s = future.result()
                if s:
                    s['pos_dump'] = dumps_map[s['pos_name']]
                    all_stats.append(s)
        return all_stats

    def execute(self, n_jobs=1):
        """批量优化策略

        :param n_jobs: 进程数量
        :return:
        """
        symbols, results_path = self.symbols, self.results_path
        tactic = CzscOpenOptimStrategy(symbol='symbol', candidate_signals=self.candidate_signals, **self.kwargs)
        tactic.save_positions(os.path.join(results_path, 'positions'))

        dumps_map = {pos.name: pos.dump() for pos in tactic.positions}
        logger.info(f"{self.version} 开始优化策略，策略数量：{len(tactic.positions)}，共 {len(symbols)} 只标的，进程数量：{n_jobs}；"
                    f"结果保存在 {results_path}，请耐心等待...")

        self.__symbols_optim(n_jobs=n_jobs)
        all_stats = self._positions_stats(dumps_map, n_jobs=n_jobs)

        file_report = os.path.join(results_path, f"入场优化_{self.task_name}_{self.task_hash}.xlsx")
        if all_stats:
            logger.info(f"优化完成，共 {len(all_stats)} 个策略，结果保存在 {file_report}")
            report_df = pd.DataFrame(all_stats).sort_values(['截面等权收益'], ascending=False, ignore_index=True)
            report_df.to_excel(file_report, index=False)
        else:
            logger.warning("优化结果为空！")

        if self.kwargs.get('feishu_app_id') and self.kwargs.get('feishu_app_secret'):
            if os.path.exists(file_report):
                czsc.fsa.push_message(file_report, msg_type='file', **self.kwargs)
            else:
                czsc.fsa.push_message(f"开仓策略优化任务【{self.task_name} 优化结果为空！", **self.kwargs)


class ExitsOptimize:
    """基础策略出场优化流程"""

    def __init__(self, read_bars: Callable, **kwargs):
        """

        :param read_bars: K线数据读取函数
        :param kwargs: 其他参数

            - symbols: 优化标的列表
            - candidate_events: 优化出场信号列表
            - results_path: 优化结果保存路径
            - files_position: 优化入场信号文件路径列表
            - signals_module_name: 信号模块名

        """
        self.version = 'ExitsOptimizeV230924'
        self.symbols = kwargs['symbols']
        self.read_bars = read_bars
        self.kwargs = kwargs
        self.task_name = kwargs.get('task_name', '出场优化')
        self.candidate_events = kwargs.pop('candidate_events')
        self.task_hash = hashlib.md5(f"{self.candidate_events}_{self.symbols}".encode('utf-8')).hexdigest()[:8].upper()

        results_path = os.path.join(kwargs['results_path'], f"{self.task_name}_{self.task_hash}")
        os.makedirs(results_path, exist_ok=True)
        self.poss_path = os.path.join(results_path, 'poss')
        os.makedirs(self.poss_path, exist_ok=True)

        self.results_path = results_path
        logger.add(f"{self.results_path}\\信号优化.log", encoding='utf-8', enqueue=True)
        logger.info(f"{self.task_name} | {self.candidate_events} | 其他参数：{kwargs}")

    def _one_symbol_optim(self, symbol):
        one_symbol_optim(symbol, self.read_bars, self.poss_path, optim_type='exit',
                         candidate_events=self.candidate_events, **self.kwargs)

    def _one_pos_stats(self, pos_name):
        return one_position_stats(self.poss_path, pos_name)

    def __symbols_optim(self, n_jobs=1):
        symbols = self.symbols
        if n_jobs <= 1:
            for symbol in tqdm(sorted(symbols), desc="优化进度"):
                self._one_symbol_optim(symbol)
            return

        with ProcessPoolExecutor(n_jobs) as pool:
            pool.map(self._one_symbol_optim, sorted(symbols))

    def _positions_stats(self, dumps_map, n_jobs=1):
        """统计所有 pos 的表现"""
        if n_jobs <= 1:
            all_stats = [self._one_pos_stats(pos_name) for pos_name in dumps_map.keys()]
            for s, pos_name in zip(all_stats, dumps_map.keys()):
                if not s:
                    continue
                s['pos_dump'] = dumps_map[pos_name]
            return all_stats

        all_stats = []
        with ProcessPoolExecutor(n_jobs) as pool:
            futures = [pool.submit(self._one_pos_stats, pos_name) for pos_name in dumps_map.keys()]
            for future in as_completed(futures):
                s = future.result()
                if s:
                    s['pos_dump'] = dumps_map[s['pos_name']]
                    all_stats.append(s)
        return all_stats

    def execute(self, n_jobs=1):
        """批量优化策略

        :param n_jobs: 进程数量
        :return:
        """
        symbols = self.symbols
        results_path = self.results_path
        tactic = CzscExitOptimStrategy(symbol='symbol', candidate_events=self.candidate_events, **self.kwargs)
        tactic.save_positions(os.path.join(results_path, 'positions'))

        dumps_map = {pos.name: pos.dump() for pos in tactic.positions}
        logger.info(f"{self.version} 开始优化策略，策略数量：{len(tactic.positions)}，共 {len(symbols)} 只标的，进程数量：{n_jobs}；"
                    f"结果保存在 {results_path}，请耐心等待...")

        self.__symbols_optim(n_jobs=n_jobs)
        all_stats = self._positions_stats(dumps_map, n_jobs=n_jobs)

        file_report = os.path.join(results_path, f"出场优化_{self.task_name}_{self.task_hash}.xlsx")
        if all_stats:
            logger.info(f"策略出场优化完成，共 {len(all_stats)} 个策略，结果保存在 {file_report}")
            report_df = pd.DataFrame(all_stats).sort_values(['截面等权收益'], ascending=False, ignore_index=True)
            report_df.to_excel(file_report, index=False)
        else:
            logger.warning("策略出场优化结果为空！请检查执行日志！")

        if self.kwargs.get('feishu_app_id') and self.kwargs.get('feishu_app_secret'):
            if os.path.exists(file_report):
                czsc.fsa.push_message(file_report, msg_type='file', **self.kwargs)
            else:
                czsc.fsa.push_message("优化结果为空！", **self.kwargs)
