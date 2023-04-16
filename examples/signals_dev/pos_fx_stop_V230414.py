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
logger.enable('czsc.analyze')

pd.set_option('expand_frame_repr', False)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 1000)
pd.set_option('display.width', 1000)


class MyStrategy(CzscStrategyBase):

    def create_pos(self, freq='60分钟', freq1='15分钟'):
        _pos_name = f'{freq}通道突破'
        _pos = {'symbol': self.symbol,
                'name': _pos_name,
                'opens': [{'operate': '开多',
                           'factors': [
                               {'name': f'{freq}看多',
                                'signals_all': [f'{freq}_D1通道突破#5#30#30_BS辅助V230403_看多_任意_任意_0']},
                           ]},

                          {'operate': '开空',
                           'factors': [
                               {'name': f'{freq}看空',
                                'signals_all': [f'{freq}_D1通道突破#5#30#30_BS辅助V230403_看空_任意_任意_0']},
                           ]}
                          ],
                'exits': [
                    {'operate': '平多',
                     'factors': [
                         {'name': f'{freq1}_{_pos_name}_止损V230414',
                          'signals_all': [f'{freq1}_{_pos_name}N1_止损V230414_多头止损_任意_任意_0']},
                     ]},

                    {'operate': '平空',
                     'factors': [
                         {'name': f'{freq1}_{_pos_name}_止损V230414',
                          'signals_all': [f'{freq1}_{_pos_name}N1_止损V230414_空头止损_任意_任意_0']},
                     ]},
                ],
                'interval': 7200,
                'timeout': 100,
                'stop_loss': 500,
                'T0': True}

        return Position.load(_pos)

    @property
    def positions(self) -> List[Position]:
        _pos_list = [self.create_pos(freq='日线', freq1='60分钟')]
        return _pos_list


def check():
    from czsc.connectors import research

    symbols = research.get_symbols('A股主要指数')
    tactic = MyStrategy(symbol=symbols[0], signals_module_name='pos_signals')
    bars = research.get_raw_bars(symbols[0], tactic.base_freq, '20151101', '20210101', fq='前复权')

    tactic.check(bars, res_path=r'C:\Users\zengb\.czsc\策略信号验证', refresh=True)


if __name__ == '__main__':
    check()



