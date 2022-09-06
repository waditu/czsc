# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:48
describe: A股股票回测研究

环境变量设置说明：
strategy_id                 掘金研究策略ID
wx_key                      企业微信群聊机器人Key
max_sym_pos                 单仓位限制
path_gm_logs                gm_logs的路径，默认值：C:/gm_logs
backtest_start_time         回测开始时间，如：2021-05-01 14:30:00
backtest_end_time           回测结束时间，如：2021-07-31 15:30:00
backtest_initial_cash       回测起始资金，如：100000000
backtest_transaction_ratio  回测成交比例，1表示100%成交
backtest_commission_ratio   回测手续费，如：0.001
backtest_slippage_ratio     回测滑点，如：0.0005

环境变量设置样例：

# 使用 os 模块设置
os.environ['strategy_id'] = 'c7991760-f389-11eb-b66a-00163e0c87d1'
os.environ['wx_key'] = '2****96b-****-4f83-818b-2952fe2731c0'
os.environ['max_sym_pos'] = '0.5'
os.environ['path_gm_logs'] = 'C:/gm_logs'
os.environ['backtest_start_time'] = '2020-01-01 14:30:00'
os.environ['backtest_end_time'] = '2020-12-31 15:30:00'
os.environ['backtest_initial_cash'] = '100000000'
os.environ['backtest_transaction_ratio'] = '1'
os.environ['backtest_commission_ratio'] = '0.001'
os.environ['backtest_slippage_ratio'] = '0.0005'
"""
from czsc.gms.gm_stocks import *
from czsc.strategies import trader_strategy_a as strategy


def init(context):
    symbols = [
        'SZSE.300014',
        'SHSE.600143',
        'SZSE.002216',
        'SZSE.300033',
        'SZSE.000795',
        'SZSE.002739',
        'SHSE.600000',
        'SHSE.600008',
        'SHSE.600006',
        'SHSE.600009',
        'SHSE.600010',
        'SHSE.600011'
    ]
    name = f"{strategy.__name__}"
    init_context_universal(context, name)
    init_context_env(context)
    init_context_traders(context, symbols, strategy)
    init_context_schedule(context)


if __name__ == '__main__':
    run(filename=os.path.basename(__file__), token=gm_token, mode=MODE_BACKTEST,
        strategy_id=os.environ['strategy_id'],
        backtest_start_time=os.environ['backtest_start_time'],
        backtest_end_time=os.environ['backtest_end_time'],
        backtest_initial_cash=int(os.environ['backtest_initial_cash']),
        backtest_transaction_ratio=float(os.environ['backtest_transaction_ratio']),
        backtest_commission_ratio=float(os.environ['backtest_commission_ratio']),
        backtest_slippage_ratio=float(os.environ['backtest_slippage_ratio']),
        backtest_adjust=ADJUST_PREV,
        backtest_check_cache=1)

