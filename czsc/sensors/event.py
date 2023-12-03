# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/7/7 22:42
describe: Event 相关的传感器
"""
import os
import shutil
import pandas as pd
from copy import deepcopy
from loguru import logger
from czsc.objects import Event
from typing import List, Dict, Callable, Any, Union
from czsc.traders.sig_parse import get_signals_freqs
from czsc.traders.base import generate_czsc_signals
from czsc.utils.io import save_json
from concurrent.futures import ProcessPoolExecutor, as_completed


class EventMatchSensor:
    def __init__(self, events: List[Union[Dict[str, Any], Event]], symbols: List[str], read_bars: Callable, **kwargs) -> None:
        """
        事件匹配传感器

        :param event: 事件配置
        :param symbols: 事件匹配的标的
        :param read_bars: 读取K线数据的函数，函数签名如下：
            read_bars(symbol, freq, sdt, edt, fq='前复权', **kwargs) -> List[RawBar]

        :param kwargs: 读取K线数据的函数的参数

            - bar_sdt: K线数据的开始时间，格式：2020-01-01
            - sdt: 事件匹配的开始时间，格式：2020-01-01
            - edt: 事件匹配的结束时间，格式：2020-01-01
            - max_workers: 读取K线数据的函数的最大进程数
            - signals_module: 信号解析模块，如：czsc.signals
            - results_path: 事件匹配结果的保存路径

        """
        self.symbols = symbols
        self.read_bars = read_bars
        self.events = [Event.load(event) if isinstance(event, dict) else event for event in events]
        self.events_map = {event.name: event for event in self.events}
        self.events_name = [event.name for event in self.events]
        self.results_path = kwargs.pop("results_path")
        self.refresh = kwargs.pop("refresh", False)
        if os.path.exists(self.results_path) and self.refresh:
            shutil.rmtree(self.results_path)
            logger.warning(f"文件夹 {self.results_path} 已存在，程序将覆盖该文件夹下的所有文件")
        os.makedirs(self.results_path, exist_ok=True)
        save_json({e.name: e.dump() for e in self.events}, os.path.join(self.results_path, "events.json"))

        logger.add(os.path.join(self.results_path, "event_match_sensor.log"), rotation="1 day", encoding="utf-8")
        logger.info(f"事件匹配传感器初始化，共有{len(self.events)}个事件，{len(self.symbols)}个标的")

        self.signals_module = kwargs.pop("signals_module", "czsc.signals")
        self.signals_config = self._get_signals_config()
        self.freqs = get_signals_freqs(self.signals_config)
        self.base_freq = self.freqs[0]
        logger.info(
            f"signals_moudle: {self.signals_module}, signals_config: {self.signals_config}, freqs: {self.freqs}"
        )

        self.bar_sdt = kwargs.pop("bar_sdt", "2017-01-01")
        self.sdt = kwargs.pop("sdt", "2018-01-01")
        self.edt = kwargs.pop("edt", "2022-01-01")
        logger.info(f"bar_sdt: {self.bar_sdt}, sdt: {self.sdt}, edt: {self.edt}")

        self.kwargs = kwargs
        logger.info(f"事件匹配传感器初始化完成，共有{len(self.events)}个事件，{len(self.symbols)}个标的")
        file_data = os.path.join(self.results_path, "data.feather")
        if os.path.exists(file_data):
            self.data = pd.read_feather(file_data)
            logger.info(f"读取事件匹配数据：{file_data}")
        else:
            self.data = self._multi_symbols(self.symbols, max_workers=self.kwargs.pop("max_workers", 1))
            self.data.to_feather(os.path.join(self.results_path, "data.feather"))

        _res = []
        for event_name in self.events_name:
            df = self.get_event_csc(event_name)
            df = df.set_index("dt")
            _res.append(df)
        df = pd.concat(_res, axis=1, ignore_index=False).reset_index()
        file_csc = os.path.join(self.results_path, "cross_section_counts.csv")
        df.to_csv(file_csc, index=False)
        logger.info(f"截面匹配次数计算完成，结果保存至：{file_csc}")

        # csc = cross section count，表示截面匹配次数
        self.csc = df

    def _get_signals_config(self):
        """获取所有事件的信号配置，并将其合并为一个不包含重复项的列表。
        该列表包含了所有事件所需的信号计算和解析规则，以便于后续的事件匹配过程。

        1. 创建一个空列表 config，用于存储所有的信号配置。
        2. 遍历 self.events 中的所有事件（Event 对象）。对于每个事件，调用其 get_signals_config 方法，
            传入 signals_module 参数，并将返回值（即该事件的信号配置）添加到 config 列表中。
        3. 通过 list comprehension 生成一个新的列表 config。对 config 列表中的每个字典 d
            使用 tuple(d.items()) 转换为元组，然后将这些元组转换回 dict 并加入新列表中。
        4. 返回处理后的 config 列表。
        """
        config = []
        for event in self.events:
            _c = event.get_signals_config(signals_module=self.signals_module)
            config.extend(_c)
        config = [dict(t) for t in {tuple(d.items()) for d in config}]
        return config

    def _single_symbol(self, symbol):
        """单个symbol的事件匹配

        对单个标的（symbol）进行事件匹配。它首先获取 K 线数据，然后生成 CZSC 信号，接着遍历每个事件并计算匹配情况，
        最后整理数据框并返回。如果在过程中遇到问题，则记录错误并返回一个空 DataFrame。

        函数执行逻辑：

        1. 调用 self.read_bars 方法读取指定 symbol、频率（self.base_freq）、开始时间（self.bar_sdt）
           和结束时间（self.edt）的 K 线数据，并将返回值赋给 bars。
        2. 使用 generate_czsc_signals 函数生成 CZSC 信号。这里传入了 bars、复制后的
           signals_config（以防止修改原始配置）、开始时间（self.sdt）以及 df=False（表示返回一个字典列表而非 DataFrame 对象）。
        3. 将上一步生成的信号转换为 DataFrame 并保存到 sigs 变量中。
        4. 创建一个新的 events 复制品（以防止修改原始事件列表），并创建一个空列表 new_cols，用于存储新添加的列名。
        5. 遍历新的 events 列表，对于每个 event：
            a. 获取 event 的名称 e_name。
            b. 使用 apply 函数应用 is_match 方法来判断每行数据是否与该事件相匹配。
                结果是一个布尔值和一个 float 值（表示匹配得分），它们分别被保存为 e_name 和 f'{e_name}_F' 列。
            c. 将这两个新列名添加到 new_cols 列表中。
        6. 在 sigs 数据框中添加一列 n1b，表示涨跌幅。
        7. 最后，重新组织 sigs 数据框的列顺序，使其包含以下列：symbol、dt、open、close、high、low、vol、amount、n1b 以及所有新添加的列。

        """
        try:
            bars = self.read_bars(symbol, freq=self.base_freq, sdt=self.bar_sdt, edt=self.edt, **self.kwargs)
            sigs = generate_czsc_signals(bars, deepcopy(self.signals_config), sdt=self.sdt, df=False)
            sigs = pd.DataFrame(sigs)
            events = deepcopy(self.events)
            new_cols = []
            for event in events:
                e_name = event.name
                sigs[[e_name, f'{e_name}_F']] = sigs.apply(event.is_match, axis=1, result_type="expand")  # type: ignore
                new_cols.extend([e_name, f'{e_name}_F'])
            sigs['n1b'] = (sigs['close'].shift(-1) / sigs['close'] - 1) * 10000
            sigs = sigs[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol', 'amount', 'n1b'] + new_cols]  # type: ignore
            return sigs
        except Exception as e:
            logger.error(f"{symbol} 事件匹配失败：{e}")
            return pd.DataFrame()

    def _multi_symbols(self, symbols: List[str], max_workers=1):
        """多个symbol的事件匹配"""
        logger.info(f"开始事件匹配，共有{len(symbols)}个标的，max_workers={max_workers}")
        dfs = []
        if max_workers == 1:
            for symbol in symbols:
                dfs.append(self._single_symbol(symbol))
        else:
            with ProcessPoolExecutor(max_workers) as executor:
                futures = [executor.submit(self._single_symbol, symbol) for symbol in symbols]
                for future in as_completed(futures):
                    dfs.append(future.result())
        df = pd.concat(dfs, ignore_index=True)
        for event_name in self.events_name:
            df[event_name] = df[event_name].astype(int)
        return df

    def get_event_csc(self, event_name: str):
        """获取事件的截面匹配次数

        csc = cross section count，表示截面匹配次数

        函数执行逻辑：

        1. 创建一个 self.data 的副本 df。
        2. 在 df 中筛选出 event_name 列等于 1 的行。
        3. 使用 groupby 方法按 symbol 和 dt 对筛选后的数据进行分组，并计算 event_name 列的总和。
            结果将形成一个新的 DataFrame，其中索引为 (symbol, dt) 组合，只有一个列 event_name，表示每个组合的匹配次数。
        4. 再次使用 groupby 方法按 dt 对上一步的结果进行分组，并计算 event_name 列的总和。这次得到的新 DataFrame
            只有一个列 event_name，表示在每个时间点所有标的的事件匹配总数。

        :param event_name: 事件名称
        :return: DataFrame
        """
        df = self.data.copy()
        df = df[df[event_name] == 1]
        df = df.groupby(["symbol", "dt"])[event_name].sum().reset_index()
        df = df.groupby("dt")[event_name].sum().reset_index()
        return df
