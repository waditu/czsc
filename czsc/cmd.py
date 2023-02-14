# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/10/14 22:54
describe: 命令行工具集

https://click.palletsprojects.com/en/8.0.x/quickstart/
"""
import click
from loguru import logger


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
def dummy(file_strategy):
    """使用 CzscDummyTrader 进行快速的择时策略研究"""
    pass


@czsc.command()
@click.option('-f', '--file_strategy', type=str, required=True, help="Python择时策略文件路径")
def replay(file_strategy):
    """执行择时策略在某个品种上的交易回放"""
    pass


@czsc.command()
@click.option('-f', '--file_strategy', type=str, required=True, help="Python信号检查文件路径")
@click.option('-d', '--delta_days', type=int, required=False, default=1, help="两次相同信号之间的间隔天数")
def check(file_strategy, delta_days):
    """执行择时策略中使用的信号在某个品种上的校验"""
    from czsc.traders import check_signals_acc
    from czsc.utils import get_py_namespace

    py = get_py_namespace(file_strategy)
    get_signals = py['get_signals']
    check_params = py.get('check_params', None)

    if not check_params:
        logger.warning(f"{file_strategy} 中没有设置策略回放参数，将使用默认参数执行")

    # 获取单个品种的基础周期K线
    symbol = check_params.get('symbol', "000001.SZ#E")
    sdt = check_params.get('sdt', '20200101')
    edt = check_params.get('edt', '20220101')
    bars = py['read_bars'](symbol, sdt, edt)
    logger.info(f"信号检查参数 | {symbol} - sdt: {sdt} - edt: {edt}")

    check_signals_acc(bars, get_signals=get_signals, delta_days=delta_days)
