# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/15 12:54
describe: Event Match Sensor
"""
import sys

sys.path.insert(0, '..')
sys.path.insert(0, '../..')

import os
import pandas as pd
from copy import deepcopy
from loguru import logger
from czsc.objects import Event
from typing import List, Dict, Callable, Any
from czsc.traders.sig_parse import get_signals_freqs
from czsc.traders.base import generate_czsc_signals
from czsc.utils import save_json
from concurrent.futures import ProcessPoolExecutor, as_completed


class EventMatchSensor:
    def __init__(self, events: List[Dict[str, Any] | Event], symbols: List[str], read_bars: Callable, **kwargs) -> None:
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
        if os.path.exists(self.results_path):
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
        self.data = self._multi_symbols(self.symbols, max_workers=self.kwargs.pop("max_workers", 1))
        self.data.to_feather(os.path.join(self.results_path, "data.feather"))

        _res = []
        for event_name in self.events_name:
            df = self.get_event_csc(event_name)
            df = df.set_index("dt")
            _res.append(df)
        df = pd.concat(_res, axis=1, ignore_index=False).reset_index()
        file_csc = os.path.join(self.results_path, f"cross_section_counts.xlsx")
        df.to_excel(file_csc, index=False)
        logger.info(f"截面匹配次数计算完成，结果保存至：{file_csc}")

        # csc = cross section count，表示截面匹配次数
        self.csc = df

    def _get_signals_config(self):
        config = []
        for event in self.events:
            _c = event.get_signals_config(signals_module=self.signals_module)
            config.extend(_c)
        config = [dict(t) for t in {tuple(d.items()) for d in config}]
        return config

    def _single_symbol(self, symbol):
        """单个symbol的事件匹配"""
        try:
            bars = self.read_bars(symbol, freq=self.base_freq, sdt=self.bar_sdt, edt=self.edt, **self.kwargs)
            sigs = generate_czsc_signals(bars, deepcopy(self.signals_config), sdt=self.sdt, df=True)
            events = deepcopy(self.events)
            new_cols = []
            for event in events:
                e_name = event.name
                sigs[[e_name, f'{e_name}_F']] = sigs.apply(event.is_match, axis=1, result_type="expand")  # type: ignore
                new_cols.extend([e_name, f'{e_name}_F'])

            sigs = sigs[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol', 'amount'] + new_cols]  # type: ignore
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

        :param event_name: 事件名称
        :return: DataFrame
        """
        df = self.data.copy()
        df = df[df[event_name] == 1]
        df = df.groupby(["symbol", "dt"])[event_name].sum().reset_index()
        df = df.groupby("dt")[event_name].sum().reset_index()
        return df


def use_event_matcher():
    from czsc.connectors.research import get_raw_bars, get_symbols
    from czsc import EventMatchSensor

    symbols = get_symbols("中证500成分股")
    events = [
        {
            "operate": "开多",
            "signals_not": ["日线_D1_涨跌停V230331_跌停_任意_任意_0", "日线_D1_涨跌停V230331_涨停_任意_任意_0"],
            "factors": [{"name": "CCI看多", "signals_all": ["日线_D1CCI14#3#10_BS辅助V230402_多头_任意_任意_0"]}],
        },
        {"operate": "开多", "factors": [{"name": "CCI看多", "signals_all": ["日线_D1CCI14#3#10_BS辅助V230402_多头_任意_任意_0"]}]},
    ]

    ems_params = {
        "events": events,
        "symbols": symbols,
        "read_bars": get_raw_bars,
        "bar_sdt": "2017-01-01",
        "sdt": "2018-01-01",
        "edt": "2023-01-01",
        "max_workers": 10,
        "results_path": r"D:\QMT投研\EMS测试A",
    }

    ems = EventMatchSensor(**ems_params)


if __name__ == '__main__':
    use_event_matcher()
