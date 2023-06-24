# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/14 17:48
describe: 
"""
import os
import sys

sys.path.insert(0, r'D:\ZB\git_repo\waditu\czsc\examples\signals_dev')
os.environ['czsc_verbose'] = '1'
import pandas as pd
from typing import List
from loguru import logger
from czsc import CzscStrategyBase, Position
from czsc.connectors import research
from czsc.analyze import CZSC
from collections import OrderedDict
from czsc.traders.base import CzscTrader
from czsc.utils import create_single_signal
from czsc.objects import Operate, Direction, Mark
from czsc.signals.tas import update_ma_cache

logger.enable('czsc.analyze')

pd.set_option('expand_frame_repr', False)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)
pd.set_option('display.width', 1000)


def pos_fix_exit_V230624(cat: CzscTrader, **kwargs) -> OrderedDict:
    """固定比例止损，止盈

    参数模板："{pos_name}_固定{th}BP止盈止损_出场V230624"

    **信号逻辑：**

    以多头为例，如果持有收益超过 th 个BP，则止盈；如果亏损超过 th 个BP，则止损。

    **信号列表：**

    - Signal('日线三买多头_固定100BP止盈止损_出场V230624_多头止损_任意_任意_0')
    - Signal('日线三买多头_固定100BP止盈止损_出场V230624_空头止损_任意_任意_0')

    :param cat: CzscTrader对象
    :param kwargs: 参数字典
        - pos_name: str，开仓信号的名称
        - freq1: str，给定的K线周期
        - n: int，向前找的K线个数，默认为 3
    :return:
    """
    pos_name = kwargs["pos_name"]
    th = int(kwargs.get('th', 300))
    k1, k2, k3 = f"{pos_name}_固定{th}BP止盈止损_出场V230624".split("_")
    v1 = '其他'
    if not hasattr(cat, "positions"):
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    pos_ = [x for x in cat.positions if x.name == pos_name][0]
    if len(pos_.operates) == 0 or pos_.operates[-1]['op'] in [Operate.SE, Operate.LE]:
        return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)

    op = pos_.operates[-1]
    op_price = op['price']

    if op['op'] == Operate.LO:
        if cat.latest_price < op_price * (1 - th / 10000):
            v1 = '多头止损'
        if cat.latest_price > op_price * (1 + th / 10000):
            v1 = '多头止盈'

    if op['op'] == Operate.SO:
        if cat.latest_price > op_price * (1 + th / 10000):
            v1 = '空头止损'
        if cat.latest_price < op_price * (1 - th / 10000):
            v1 = '空头止盈'

    return create_single_signal(k1=k1, k2=k2, k3=k3, v1=v1)


class MyStrategy(CzscStrategyBase):
    def create_pos(self, freq='60分钟', freq1='15分钟'):
        _pos_name = f'{freq}通道突破'
        _pos = {
            'symbol': self.symbol,
            'name': _pos_name,
            'opens': [
                {
                    'operate': '开多',
                    'factors': [
                        {'name': f'{freq}看多', 'signals_all': [f'{freq}_D1通道突破#5#30#30_BS辅助V230403_看多_任意_任意_0']}
                    ],
                },
                {
                    'operate': '开空',
                    'factors': [
                        {'name': f'{freq}看空', 'signals_all': [f'{freq}_D1通道突破#5#30#30_BS辅助V230403_看空_任意_任意_0']}
                    ],
                },
            ],
            'exits': [
                {
                    'operate': '平多',
                    'factors': [
                        {'name': '止损出场V230624', 'signals_all': [f'{_pos_name}_固定{200}BP止盈止损_出场V230624_空头止损_任意_任意_0']},
                        {'name': '止损出场V230624', 'signals_all': [f'{_pos_name}_固定{200}BP止盈止损_出场V230624_空头止盈_任意_任意_0']},
                    ],
                },
                {
                    'operate': '平空',
                    'factors': [
                        {'name': '止损出场V230624', 'signals_all': [f'{_pos_name}_固定{200}BP止盈止损_出场V230624_空头止损_任意_任意_0']},
                        {'name': '止损出场V230624', 'signals_all': [f'{_pos_name}_固定{200}BP止盈止损_出场V230624_空头止盈_任意_任意_0']},
                    ],
                },
            ],
            'interval': 7200,
            'timeout': 100,
            'stop_loss': 500,
            'T0': True,
        }

        return Position.load(_pos)

    @property
    def positions(self) -> List[Position]:
        _pos_list = [self.create_pos(freq='日线', freq1='60分钟')]
        return _pos_list


def check():
    from czsc.connectors import research

    symbols = research.get_symbols('A股主要指数')
    tactic = MyStrategy(symbol=symbols[0], signals_module_name='czsc.signals')
    bars = research.get_raw_bars(symbols[0], tactic.base_freq, '20151101', '20210101', fq='前复权')

    tactic.check(bars, res_path=r'C:\Users\zengb\.czsc\策略信号验证', refresh=True)


if __name__ == '__main__':
    check()
