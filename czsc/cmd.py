# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/14 22:54
describe: 命令行工具集

https://click.palletsprojects.com/en/8.0.x/quickstart/
"""
import os
import click
import pandas as pd
from loguru import logger
from czsc.utils import get_py_namespace


@click.group()
def czsc():
    """CZSC 命令行工具"""
    pass


@czsc.command()
def aphorism():
    """随机输出一条缠中说禅良言警句"""
    from czsc.aphorism import print_one

    print_one()


@czsc.command()
@click.option('-f', '--file_strategy', type=str, required=True, help="Python择时策略文件路径")
def backtest(file_strategy):
    """使用 TradeSimulator 进行择时策略回测/仿真研究"""
    from collections import Counter
    from czsc.traders.ts_simulator import TradeSimulator

    py = get_py_namespace(file_strategy)
    results_path = os.path.join(py['results_path'], "backtest")
    os.makedirs(results_path, exist_ok=True)

    strategy = py['trader_strategy']
    dc = py['dc']
    symbols = py['symbols']

    ts = TradeSimulator(dc, strategy, res_path=results_path)
    counter = Counter([x.split("#")[1] for x in symbols])
    for asset, c in counter.items():
        ts_codes = [x.split("#")[0] for x in symbols if x.endswith(asset)]
        ts.update_traders(ts_codes, asset)


@czsc.command()
@click.option('-f', '--file_strategy', type=str, required=True, help="Python择时策略文件路径")
def dummy(file_strategy):
    """使用 CzscDummyTrader 进行快速的择时策略研究"""

    from czsc.traders.advanced import CzscDummyTrader
    from czsc.sensors.utils import generate_symbol_signals

    py = get_py_namespace(file_strategy)
    results_path = os.path.join(py['results_path'], "dummy")
    os.makedirs(results_path, exist_ok=True)

    strategy = py['trader_strategy']
    dc = py['dc']
    symbols = py['symbols']

    for symbol in symbols:
        file_dfs = os.path.join(results_path, f"{symbol}_signals.pkl")

        try:
            # 可以直接生成信号，也可以直接读取信号
            if os.path.exists(file_dfs):
                dfs = pd.read_pickle(file_dfs)
            else:
                ts_code, asset = symbol.split('#')
                dfs = generate_symbol_signals(dc, ts_code, asset, "20150101", "20220101", strategy, 'hfq')
                dfs.to_pickle(file_dfs)

            cdt = CzscDummyTrader(dfs, strategy)
            logger.info(f"{cdt.results['long_performance']}")

        except:
            logger.exception(f"fail on {symbol}")


@czsc.command()
@click.option('-f', '--file_strategy', type=str, required=True, help="Python择时策略文件路径")
def replay(file_strategy):
    """执行择时策略在某个品种上的交易回放"""
    from czsc.data import freq_cn2ts
    from czsc.utils import BarGenerator
    from czsc.traders.utils import trade_replay

    py = get_py_namespace(file_strategy)
    strategy = py['trader_strategy']
    dc = py['dc']
    replay_params = py.get('replay_params', None)

    if not replay_params:
        logger.warning(f"{file_strategy} 中没有设置策略回放参数，将使用默认参数执行")

    # 获取单个品种的基础周期K线
    tactic = strategy("000001.SZ")
    base_freq = tactic['base_freq']
    symbol = replay_params.get('symbol', "000001.SZ#E")
    ts_code, asset = symbol.split("#")
    sdt = replay_params.get('sdt', '20150101')
    edt = replay_params.get('edt', '20220101')
    bars = dc.pro_bar_minutes(ts_code, sdt, edt, freq_cn2ts[base_freq], asset, adj="hfq")
    logger.info(f"交易回放参数 | {symbol} - sdt:{sdt} - edt: {edt}")

    # 设置回放快照文件保存目录
    res_path = os.path.join(py['results_path'], f"replay_{symbol}")
    os.makedirs(res_path, exist_ok=True)

    # 拆分基础周期K线，一部分用来初始化BarGenerator，随后的K线是回放区间
    start_date = pd.to_datetime(replay_params.get('mdt', '20200101'))
    bg = BarGenerator(base_freq, freqs=tactic['freqs'])
    bars1 = [x for x in bars if x.dt <= start_date]
    bars2 = [x for x in bars if x.dt > start_date]
    for bar in bars1:
        bg.update(bar)

    trade_replay(bg, bars2, strategy, res_path)


@czsc.command()
@click.option('-f', '--file_strategy', type=str, required=True, help="Python择时策略文件路径")
@click.option('-d', '--delta_days', type=int, required=False, default=5, help="两次相同信号之间的间隔天数")
def check(file_strategy, delta_days):
    """执行择时策略中使用的信号在某个品种上的校验"""
    from czsc.data import freq_cn2ts
    from czsc.sensors.utils import check_signals_acc

    py = get_py_namespace(file_strategy)
    strategy = py['trader_strategy']
    dc = py['dc']
    check_params = py.get('check_params', None)

    if not check_params:
        logger.warning(f"{file_strategy} 中没有设置策略回放参数，将使用默认参数执行")

    # 获取单个品种的基础周期K线
    tactic = strategy("000001.SZ")
    base_freq = tactic['base_freq']
    symbol = check_params.get('symbol', "000001.SZ#E")
    ts_code, asset = symbol.split("#")
    sdt = check_params.get('sdt', '20200101')
    edt = check_params.get('edt', '20220101')
    bars = dc.pro_bar_minutes(ts_code, sdt, edt, freq_cn2ts[base_freq], asset, adj="hfq")
    logger.info(f"信号检查参数 | {symbol} - sdt:{sdt} - edt: {edt}")

    check_signals_acc(bars, strategy=strategy, delta_days=delta_days)
