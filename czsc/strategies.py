# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/5/6 13:24
describe: 提供一些策略的编写案例

以 trader_ 开头的是择时交易策略案例
"""
import os
import time
import shutil
import hashlib
import pandas as pd
from tqdm import tqdm
from copy import deepcopy
from datetime import timedelta, datetime
from abc import ABC, abstractmethod
from loguru import logger
from typing import List
from czsc.traders.base import CzscTrader
from czsc.traders.sig_parse import get_signals_freqs, get_signals_config
from czsc.utils.io import dill_dump, save_json, read_json
from czsc.py.bar_generator import check_freq_and_market
from czsc.core import RawBar, Signal, Position, BarGenerator

class CzscStrategyBase(ABC):
    """
    择时交易策略的要素：

    1. 交易品种以及该品种对应的参数
    2. K线周期列表
    3. 交易信号参数配置
    4. 持仓策略列表
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.signals_module_name = kwargs.get("signals_module_name", "czsc.signals")

    @property
    def symbol(self):
        """交易标的"""
        return self.kwargs["symbol"]

    @property
    def unique_signals(self):
        """所有持仓策略中的交易信号列表"""
        sig_seq = []
        for pos in self.positions:  # type: ignore
            sig_seq.extend(pos.unique_signals)
        return list(set(sig_seq))

    @property
    def signals_config(self):
        """交易信号参数配置"""
        return get_signals_config(self.unique_signals, self.signals_module_name)

    @property
    def freqs(self):
        """K线周期列表"""
        return get_signals_freqs(self.unique_signals)

    @property
    def sorted_freqs(self):
        """排好序的 K 线周期列表"""
        from czsc.utils import freqs_sorted
        
        return freqs_sorted(self.freqs)

    @property
    def base_freq(self):
        """基础 K 线周期"""
        return self.sorted_freqs[0]

    @abstractmethod
    def positions(self) -> List[Position]:
        """持仓策略列表"""
        raise NotImplementedError

    def init_bar_generator(self, bars: List[RawBar], **kwargs):
        """使用策略定义初始化一个 BarGenerator 对象

        函数执行逻辑：

        - 该方法的目的是使用策略定义初始化一个BarGenerator对象。BarGenerator是用于生成K线数据的类。
        - 参数bars表示基础周期的K线数据，**kwargs用于接收额外的关键字参数。
        - 首先，方法获取了基础K线的频率，并检查了是否已经有一个初始化好的BarGenerator对象传入。
        - 然后，根据基础频率是否在排序后的频率列表中，确定要使用的频率列表。
        - 如果没有传入BarGenerator对象，则根据传入的基础K线数据和其他参数创建一个新的BarGenerator对象，
          并使用部分K线数据初始化它。余下的K线数据将用于trader的初始化区间。
        - 如果传入了BarGenerator对象，则会做一些断言检查，确保传入的基础K线数据与已有的BarGenerator对象的基础周期一致，
          并且BarGenerator的end_dt是datetime类型。然后，筛选出在BarGenerator的end_dt之后的K线数据。
        - 最后，返回BarGenerator对象和余下的K线数据。

        :param bars: 基础周期K线
        :param kwargs:

            bg   已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt  初始化开始日期
            n    初始化最小K线数量

        :return:
        """
        base_freq = str(bars[0].freq.value)
        bg: BarGenerator = kwargs.pop("bg", None)
        freqs = self.sorted_freqs[1:] if base_freq in self.sorted_freqs else self.sorted_freqs

        if bg is None:
            uni_times = sorted(list({x.dt.strftime("%H:%M") for x in bars}))
            _, market = check_freq_and_market(uni_times, freq=base_freq)

            sdt = pd.to_datetime(kwargs.get("sdt", "20200101"))
            n = int(kwargs.get("n", 500))
            bg = BarGenerator(base_freq, freqs=freqs, market=market)

            # 拆分基础周期K线，sdt 之前的用来初始化BarGenerator，随后的K线是 trader 初始化区间
            bars_init = [x for x in bars if x.dt <= sdt]
            if len(bars_init) > n:
                bars1 = bars_init
                bars2 = [x for x in bars if x.dt > sdt]
            else:
                bars1 = bars[:n]
                bars2 = bars[n:]

            for bar in bars1:
                bg.update(bar)

            return bg, bars2
        else:
            assert bg.base_freq == bars[-1].freq.value, "BarGenerator 的基础周期和 bars 的基础周期不一致"
            assert isinstance(bg.end_dt, datetime), "BarGenerator 的 end_dt 必须是 datetime 类型"
            bars2 = [x for x in bars if x.dt > bg.end_dt]
            return bg, bars2

    def init_trader(self, bars: List[RawBar], **kwargs) -> CzscTrader:
        """使用策略定义初始化一个 CzscTrader 对象

        **注意：** 这里会将所有持仓策略在 sdt 之后的交易信号计算出来并缓存在持仓策略实例内部，所以初始化的过程本身也是回测的过程。

        函数执行逻辑：

        - 首先，它通过调用init_bar_generator方法获取已经初始化好的BarGenerator对象和余下的K线数据。
        - 然后，它创建一个CzscTrader对象，将BarGenerator对象、持仓策略的深拷贝、交易信号配置的深拷贝等参数传递给CzscTrader的构造函数。
        - 接着，使用余下的K线数据对CzscTrader对象进行初始化，通过调用trader.on_bar(bar)方法处理每一根K线数据。
        - 最后，返回初始化完成的CzscTrader对象。

        :param bars: 基础周期K线
        :param kwargs:

            bg   已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt  初始化开始日期
            n    初始化最小K线数量

        :return: 完成策略初始化后的 CzscTrader 对象
        """
        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg=bg, positions=deepcopy(self.positions),  # type: ignore
                            signals_config=deepcopy(self.signals_config), **kwargs)
        for bar in bars2:
            trader.on_bar(bar)
        return trader

    def backtest(self, bars: List[RawBar], **kwargs) -> CzscTrader:
        trader = self.init_trader(bars, **kwargs)
        return trader

    def dummy(self, sigs: List[dict], **kwargs) -> CzscTrader:
        """使用信号缓存进行策略回测

        :param sigs: 信号缓存，一般指 generate_czsc_signals 函数计算的结果缓存
        :return: 完成策略回测后的 CzscTrader 对象
        """
        sleep_time = kwargs.get("sleep_time", 0)
        sleep_step = kwargs.get("sleep_step", 1000)

        trader = CzscTrader(positions=deepcopy(self.positions))     # type: ignore
        for i, sig in tqdm(enumerate(sigs), desc=f"回测 {self.symbol} {self.sorted_freqs}"):
            trader.on_sig(sig)

            if i % sleep_step == 0:
                time.sleep(sleep_time)

        return trader

    def replay(self, bars: List[RawBar], res_path, **kwargs):
        """交易策略交易过程回放

        函数执行逻辑：

        - 该方法用于交易策略交易过程的回放。它接受基础周期的K线数据、结果目录以及额外的关键字参数作为输入。
        - 首先，它检查refresh参数，如果为True，则使用shutil.rmtree删除已存在的结果目录。
        - 然后，它检查结果目录是否已存在，并且是否允许覆盖。如果目录已存在且不允许覆盖，则记录一条警告信息并返回。
        - 通过调用os.makedirs创建结果目录，确保目录的存在。
        - 接着，调用init_bar_generator方法初始化BarGenerator对象，并进行相关的初始化操作。
        - 创建一个CzscTrader对象，并将初始化好的BarGenerator对象、持仓策略的深拷贝、交易信号配置的深拷贝等参数传递给CzscTrader的构造函数。
        - 为每个持仓策略创建相应的目录。
        - 遍历K线数据，调用trader.on_bar(bar)方法处理每一根K线数据。
        - 在每根K线数据处理完成后，检查每个持仓策略是否有操作，并且操作的时间是否与当前K线的时间一致。
            如果有操作，则生成相应的HTML文件名，并调用trader.take_snapshot(file_html)方法生成交易快照。
        - 最后，遍历每个持仓策略，记录其评估信息，包括多空合并表现、多头表现、空头表现等。

        :param bars: 基础周期K线
        :param res_path: 结果目录
        :param kwargs:

            bg          已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt         初始化开始日期
            n           初始化最小K线数量
            refresh     是否刷新结果目录
        :return:
        """
        from czsc.utils import x_round
        
        if kwargs.get("refresh", False):
            shutil.rmtree(res_path, ignore_errors=True)

        exist_ok = kwargs.get("exist_ok", False)
        if os.path.exists(res_path) and not exist_ok:
            logger.warning(f"结果文件夹存在且不允许覆盖：{res_path}，如需执行，请先删除文件夹")
            return
        os.makedirs(res_path, exist_ok=exist_ok)

        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg=bg, positions=deepcopy(self.positions),  # type: ignore
                            signals_config=deepcopy(self.signals_config), **kwargs)
        for position in trader.positions:
            pos_path = os.path.join(res_path, position.name)
            os.makedirs(pos_path, exist_ok=exist_ok)

        for bar in bars2:
            trader.on_bar(bar)
            for position in trader.positions:
                pos_path = os.path.join(res_path, position.name)

                if position.operates and position.operates[-1]["dt"] == bar.dt:
                    op = position.operates[-1]
                    _dt = op["dt"].strftime("%Y%m%d#%H%M")
                    file_name = f"{_dt}_{op['op'].value}_{op['bid']}_{x_round(op['price'], 2)}_{op['op_desc']}.html"
                    file_html = os.path.join(pos_path, file_name)
                    trader.take_snapshot(file_html)
                    logger.info(f"{file_html}")

        for position in trader.positions:
            logger.info(
                f"{position.name}  "
                f"\n 多空合并：{position.evaluate()} "
                f"\n 多头表现：{position.evaluate('多头')} "
                f"\n 空头表现：{position.evaluate('空头')}"
            )

        file_trader = os.path.join(res_path, "trader.ct")
        try:
            dill_dump(trader, file_trader)
            logger.info(f"交易对象保存到：{file_trader}")
        except Exception as e:
            logger.error(f"交易对象保存失败：{e}；通常的原因是交易对象中包含了不支持序列化的对象，比如函数")
        return trader

    def check(self, bars: List[RawBar], res_path, **kwargs):
        """检查交易策略中的信号是否正确

        :param bars: 基础周期K线
        :param res_path: 结果目录
        :param kwargs:
            bg   已经初始化好的BarGenerator对象，如果传入了bg，则忽略sdt和n参数
            sdt  初始化开始日期
            n    初始化最小K线数量
        :return:
        """
        if kwargs.get("refresh", False):
            shutil.rmtree(res_path, ignore_errors=True)

        exist_ok = kwargs.get("exist_ok", False)
        if os.path.exists(res_path) and not exist_ok:
            logger.warning(f"结果文件夹存在且不允许覆盖：{res_path}，如需执行，请先删除文件夹")
            return
        os.makedirs(res_path, exist_ok=exist_ok)

        # 第一遍执行，获取信号
        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg=bg, positions=deepcopy(self.positions),  # type: ignore
                            signals_config=deepcopy(self.signals_config), **kwargs)

        _signals = []
        for bar in bars2:
            trader.on_bar(bar)
            _signals.append(trader.s)

        for position in trader.positions:
            print(f"{position.name}: {position.evaluate()}")

        df = pd.DataFrame(_signals)
        df.to_excel(os.path.join(res_path, "signals.xlsx"), index=False)
        unique_signals = {}
        for col in [x for x in df.columns if len(x.split("_")) == 3]:
            unique_signals[col] = [Signal(f"{col}_{v}") for v in df[col].unique() if "其他" not in v]

        print("\n", "+" * 100)
        for key, values in unique_signals.items():
            print(f"\n{key}:")
            for value in values:
                print(f"- {value}")
        print("\n", "+" * 100)

        # 第二遍执行，检查信号，生成html
        bg, bars2 = self.init_bar_generator(bars, **kwargs)
        trader = CzscTrader(bg=bg, positions=deepcopy(self.positions),  # type: ignore
                            signals_config=deepcopy(self.signals_config), **kwargs)

        # 记录每个信号最后一次出现的时间
        last_sig_dt = {y.key: trader.end_dt for x in unique_signals.values() for y in x}
        delta_days = kwargs.get("delta_days", 1)

        for bar in bars2:
            trader.on_bar(bar)

            for key, values in unique_signals.items():
                html_path = os.path.join(res_path, key)
                os.makedirs(html_path, exist_ok=True)

                for signal in values:
                    if bar.dt - last_sig_dt[signal.key] > timedelta(days=delta_days) and signal.is_match(trader.s):
                        file_html = f"{bar.dt.strftime('%Y%m%d_%H%M')}_{signal.signal}.html"
                        file_html = os.path.join(html_path, file_html)
                        print(file_html)
                        trader.take_snapshot(file_html, height=kwargs.get("height", "680px"))
                        last_sig_dt[signal.key] = bar.dt

    def save_positions(self, path):
        """保存持仓策略配置

        :param path: 结果路径
        :return: None
        """
        os.makedirs(path, exist_ok=True)
        for pos in self.positions:          # type: ignore
            pos_ = pos.dump()
            pos_.pop("symbol")
            hash_code = hashlib.md5(str(pos_).encode()).hexdigest()
            pos_["md5"] = hash_code
            save_json(pos_, os.path.join(path, f"{pos_['name']}.json"))

    def load_positions(self, files: List, check=True) -> List[Position]:
        """从配置文件中加载持仓策略

        :param files: 以json格式保存的持仓策略文件列表
        :param check: 是否校验 MD5 值，默认为 True
        :return: 持仓策略列表
        """
        positions = []
        for file in files:
            pos = read_json(file)
            md5 = pos.pop("md5")
            if check:
                assert md5 == hashlib.md5(str(pos).encode()).hexdigest()
            pos["symbol"] = self.symbol
            positions.append(Position.load(pos))
        return positions


class CzscJsonStrategy(CzscStrategyBase):
    """仅传入Json配置的Positions就完成策略创建

    执行逻辑:

    1. 定义CzscJsonStrategy类，并继承自CzscStrategyBase。这个类可以通过仅传入Json配置的Positions来完成策略创建。
    2. 类中定义了一个名为positions的属性，使用@property装饰器将其标记为只读属性。
    3. 在positions属性的getter方法中，执行以下操作：
        - 从self.kwargs字典中获取键为"files_position"的值，并将其赋值给变量files。
            这里的self.kwargs可能是通过在实例化该类时传入的参数或其他方式设置的一个字典，其中包含了策略配置文件的路径列表。
        - 使用self.kwargs.get方法获取键为"check_position"的值，并设置默认值为True，将其赋值给变量check。这个值用于确定是否对JSON持仓策略进行MD5校验。
        - 调用self.load_positions(files, check)方法，并返回其结果。这个方法可能是从父类CzscStrategyBase中继承的方法，
            用于从配置文件中加载持仓策略。将文件列表和校验标志作为参数传递给该方法，并返回加载的持仓策略列表。

    必须参数：
        files_position: 以 json 文件配置的策略，每个json文件对应一个持仓策略配置
        check_position: 是否对 json 持仓策略进行 MD5 校验，默认为 True
    """

    @property
    def positions(self):
        files = self.kwargs["files_position"]
        check = self.kwargs.get("check_position", True)
        return self.load_positions(files, check)
