# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:48
describe: A股股票回测研究

环境变量设置说明：
strategy_id                 掘金研究策略ID
wx_key                      企业微信群聊机器人Key
stoploss                    止损/止盈比例
timeout                     超时退出，默认值600，表示最多持有600根1分钟K线的时间
wait_time                   开仓等待时间，分钟
max_open_tolerance          开仓最大容错百分比
max_total_position          总仓位限制
max_share_position          单仓位限制
path_gm_logs                gm_logs的路径，默认值：C:/gm_logs
backtest_start_time         回测开始时间，如：2021-05-01 14:30:00
backtest_end_time           回测结束时间，如：2021-07-31 15:30:00
backtest_initial_cash       回测起始资金，如：100000000
backtest_transaction_ratio  回测成交比例，1表示100%成交
backtest_commission_ratio   回测手续费，如：0.001
backtest_slippage_ratio     回测滑点，如：0.0005

环境变量设置样例：

# 方法一：在 pycharm 执行环境中设置
strategy_id=692dc7b5-d19f-11eb-af0a-38f3abf8ed06
wx_key=2daec96b-****-4f83-****-2952fe2731c0
stoploss=0.05
timeout=600
wait_time=30
max_open_tolerance=0.03
max_total_position=0.8
max_share_position=0.5
path_gm_logs=C:/gm_logs
backtest_start_time=2021-05-01 14:30:00
backtest_end_time=2021-07-31 15:30:00
backtest_initial_cash=100000000
backtest_transaction_ratio=1
backtest_commission_ratio=0.001
backtest_slippage_ratio=0.0005

# 方法二：使用 os 模块设置
os.environ['strategy_id'] = 'c7991760-f389-11eb-b66a-00163e0c87d1'
os.environ['wx_key'] = '2daec96b-****-4f83-****-2952fe2731c0'
os.environ['stoploss'] = '0.08'
os.environ['timeout'] = '600'
os.environ['wait_time'] = '30'
os.environ['max_open_tolerance'] = '0.03'
os.environ['max_total_position'] = '0.8'
os.environ['max_share_position'] = '0.5'
os.environ['path_gm_logs'] = 'D:\\research\\gm_logs'
os.environ['backtest_start_time'] = '2020-01-01 14:30:00'
os.environ['backtest_end_time'] = '2020-12-31 15:30:00'
os.environ['backtest_initial_cash'] = '100000000'
os.environ['backtest_transaction_ratio'] = '1'
os.environ['backtest_commission_ratio'] = '0.001'
os.environ['backtest_slippage_ratio'] = '0.0005'
"""
import sys
sys.path.insert(0, '')
sys.path.insert(0, '../..')
from src.utils.bt import *
from src.tactics.share import TacticShareA as Tactic


def init(context):
    symbols = [
        'SZSE.300014',
        'SHSE.600143',
        'SZSE.002216',
    ]
    tactic = Tactic()
    name = f"{tactic.name.lower()}_{tactic.like_bs_rt_v1.__name__}"
    op_freq, freqs, get_signals, get_events = tactic.like_bs_rt_v1()
    init_context_bt(context, name, symbols, op_freq, freqs, get_signals, get_events)


if __name__ == '__main__':
    run(filename=os.path.basename(__file__), token=gm_token, mode=MODE_BACKTEST,
        strategy_id=os.environ['strategy_id'],
        backtest_start_time=os.environ['backtest_start_time'],
        backtest_end_time=os.environ['backtest_end_time'],
        backtest_initial_cash=int(os.environ['backtest_initial_cash']),
        backtest_transaction_ratio=float(os.environ['backtest_transaction_ratio']),
        backtest_commission_ratio=float(os.environ['backtest_commission_ratio']),
        backtest_slippage_ratio=float(os.environ['backtest_slippage_ratio']),
        backtest_adjust=ADJUST_POST,
        backtest_check_cache=1)

