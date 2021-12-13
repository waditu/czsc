# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/13 17:48
describe: A股股票回测研究

环境变量设置说明：
strategy_id                 掘金研究策略ID
wx_key                      企业微信群聊机器人Key
max_all_pos                 总仓位限制
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
os.environ['max_all_pos'] = '0.8'
os.environ['max_sym_pos'] = '0.5'
os.environ['path_gm_logs'] = 'C:/gm_logs'
os.environ['backtest_start_time'] = '2020-01-01 14:30:00'
os.environ['backtest_end_time'] = '2020-12-31 15:30:00'
os.environ['backtest_initial_cash'] = '100000000'
os.environ['backtest_transaction_ratio'] = '1'
os.environ['backtest_commission_ratio'] = '0.001'
os.environ['backtest_slippage_ratio'] = '0.0005'
"""
from czsc import CZSC
from czsc.objects import Factor, Signal
from czsc.signals.bxt import get_s_three_bi
from czsc.signals.ta import get_s_macd
from gm_utils import *


def strategy():
    """股票15分钟策略的交易事件"""
    base_freq = '15分钟'

    freqs = ['30分钟', '60分钟']

    states_pos = {
        'hold_long_a': 0.5,
        'hold_long_b': 0.8,
        'hold_long_c': 1.0,
    }

    def get_signals(c: CZSC) -> OrderedDict:
        s = OrderedDict({"symbol": c.symbol, "dt": c.bars_raw[-1].dt, "close": c.bars_raw[-1].close})
        s.update(get_s_three_bi(c, di=1))
        s.update(get_s_macd(c, di=1))
        return s

    def get_events():
        events = [
            Event(name="开多", operate=Operate.LO, factors=[
                Factor(name="60分钟三笔买", signals_all=[
                    Signal("60分钟_倒1K_DIF多空_多头_任意_任意_0"),
                    Signal("60分钟_倒1K_MACD多空_多头_任意_任意_0"),
                ], signals_any=[
                    Signal("60分钟_倒1笔_三笔形态_向下扩张_任意_任意_0"),
                    Signal("60分钟_倒1笔_三笔形态_向下盘背_任意_任意_0"),
                    Signal("60分钟_倒1笔_三笔形态_向下无背_任意_任意_0"),
                ]),
            ]),

            Event(name="加多1", operate=Operate.LA1, factors=[
                Factor(name="30分钟三笔买", signals_all=[
                    Signal("60分钟_倒1K_DIF多空_多头_任意_任意_0"),
                    Signal("30分钟_倒1K_MACD多空_多头_任意_任意_0"),
                ], signals_any=[
                    Signal("30分钟_倒1笔_三笔形态_向下扩张_任意_任意_0"),
                    Signal("30分钟_倒1笔_三笔形态_向下盘背_任意_任意_0"),
                    Signal("30分钟_倒1笔_三笔形态_向下无背_任意_任意_0"),
                ]),
            ]),

            Event(name="加多2", operate=Operate.LA2, factors=[
                Factor(name="15分钟三笔买", signals_all=[
                    Signal("60分钟_倒1K_DIF多空_多头_任意_任意_0"),
                    Signal("15分钟_倒1K_MACD多空_多头_任意_任意_0"),
                ], signals_any=[
                    Signal("15分钟_倒1笔_三笔形态_向下扩张_任意_任意_0"),
                    Signal("15分钟_倒1笔_三笔形态_向下盘背_任意_任意_0"),
                    Signal("15分钟_倒1笔_三笔形态_向下无背_任意_任意_0"),
                ]),
            ]),

            Event(name="减多1", operate=Operate.LR1, factors=[
                Factor(name="15分钟三笔卖", signals_all=[
                    Signal("15分钟_倒1K_MACD多空_空头_任意_任意_0"),
                ], signals_any=[
                    Signal("15分钟_倒1笔_三笔形态_向上无背_任意_任意_0"),
                    Signal("15分钟_倒1笔_三笔形态_向上扩张_任意_任意_0"),
                ]),
            ]),

            Event(name="减多2", operate=Operate.LR2, factors=[
                Factor(name="30分钟三笔卖", signals_all=[
                    Signal("30分钟_倒1K_MACD多空_空头_任意_任意_0"),
                ], signals_any=[
                    Signal("30分钟_倒1笔_三笔形态_向上无背_任意_任意_0"),
                    Signal("30分钟_倒1笔_三笔形态_向上扩张_任意_任意_0"),
                ]),
            ]),

            Event(name="平多", operate=Operate.LE, factors=[
                Factor(name="60分钟三笔卖", signals_all=[
                    Signal("60分钟_倒1K_MACD多空_空头_任意_任意_0"),
                ], signals_any=[
                    Signal("60分钟_倒1笔_三笔形态_向上无背_任意_任意_0"),
                    Signal("60分钟_倒1笔_三笔形态_向上扩张_任意_任意_0"),
                ]),

                Factor(name="60分钟DIF空头", signals_all=[
                    Signal("60分钟_倒1K_DIF多空_空头_任意_任意_0"),
                ]),
            ]),
        ]
        return events

    return base_freq, freqs, states_pos, get_signals, get_events


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
    name = strategy.__name__
    base_freq, freqs, states_pos, get_signals, get_events = strategy()
    init_context_universal(context, name)
    init_context_env(context)
    init_context_traders(context, symbols, base_freq, freqs, states_pos, get_signals, get_events)
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
        backtest_adjust=ADJUST_POST,
        backtest_check_cache=1)
