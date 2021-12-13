# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/12 22:00
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
import traceback
import pandas as pd
from czsc.data.ts_cache import TsDataCache
from czsc.analyze import CZSC, OrderedDict
from czsc.objects import Factor, Signal, Event, Operate
from czsc.signals.bxt import get_s_three_bi
from czsc.signals.ta import get_s_macd
from czsc.traders.utils import fast_back_test


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


if __name__ == '__main__':
    data_path = r"D:\research\ts_data"
    dc = TsDataCache(data_path, sdt='2000-01-01', edt='20211211', verbose=True)

    # 对若干只股票进行买卖点快照验证
    ops, pairs_list, p_list = [], [], []
    stocks = ['000001.SZ', '300033.SZ']
    for ts_code in stocks:
        html_path = os.path.join(data_path, ts_code)
        os.makedirs(html_path, exist_ok=True)
        try:
            bars = dc.pro_bar_minutes(ts_code, dc.sdt, dc.edt, freq='15min', asset="E", adj='hfq', raw_bar=True)
            operates, pairs, p = fast_back_test(bars, 30000, strategy, html_path)
            print(p)
            ops.extend(operates)
            pairs_list.extend(pairs)
            p_list.append(p)
            f = pd.ExcelWriter(os.path.join(data_path, f"{strategy.__name__}_with_snapshots.xlsx"))
            pd.DataFrame(ops).to_excel(f, sheet_name="操作", index=False)
            pd.DataFrame(pairs_list).to_excel(f, sheet_name="交易", index=False)
            pd.DataFrame(p_list).to_excel(f, sheet_name="评估", index=False)
            f.close()
        except:
            traceback.print_exc()

    # 执行批量回测：对2014年之前上市的股票进行快速回测
    ops, pairs_list, p_list = [], [], []
    stocks = dc.stock_basic()
    stocks = stocks[stocks['list_date'] < '2014-01-01']
    for ts_code in stocks.ts_code.to_list():
        try:
            bars = dc.pro_bar_minutes(ts_code, dc.sdt, dc.edt, freq='15min', asset="E", adj='hfq', raw_bar=True)
            operates, pairs, p = fast_back_test(bars, 30000, strategy)
            print(p)
            ops.extend(operates)
            pairs_list.extend(pairs)
            p_list.append(p)
            f = pd.ExcelWriter(os.path.join(data_path, f"{strategy.__name__}.xlsx"))
            pd.DataFrame(ops).to_excel(f, sheet_name="操作", index=False)
            pd.DataFrame(pairs_list).to_excel(f, sheet_name="交易", index=False)
            pd.DataFrame(p_list).to_excel(f, sheet_name="评估", index=False)
            f.close()
        except:
            traceback.print_exc()
