# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/23 19:13
describe: 测试策略基类
"""
import os
import shutil
import pandas as pd
from test.test_analyze import read_1min
from czsc.utils.bar_generator import resample_bars, Freq
from czsc.traders import generate_czsc_signals


def test_czsc_strategy_example2():
    """测试策略示例2：仅传入Positions构建策略"""
    from czsc.strategies import CzscStrategyExample2
    from czsc import mock
    from czsc.objects import RawBar

    # 使用mock数据替代hardcoded data
    df = mock.generate_symbol_kines("000001", "1分钟", sdt="20240101", edt="20240110", seed=42)
    bars_raw = []
    for i, row in df.iterrows():
        bar = RawBar(
            symbol=row['symbol'], 
            id=i, 
            freq=Freq.F1, 
            open=row['open'], 
            dt=row['dt'],
            close=row['close'], 
            high=row['high'], 
            low=row['low'], 
            vol=row['vol'], 
            amount=row['amount']
        )
        bars_raw.append(bar)
    
    df_bars = pd.DataFrame([bar.__dict__ for bar in bars_raw])
    bars = resample_bars(df_bars, Freq.F15)

    strategy = CzscStrategyExample2(symbol="000001.SH")

    trader1 = strategy.init_trader(bars=bars, init_n=2000, sdt="20170101")
    assert len(trader1.positions) == 2
    sigs = generate_czsc_signals(bars, freqs=strategy.sorted_freqs,
                                 init_n=2000, sdt="20170101", signals_config=strategy.signals_config)
    trader2 = strategy.dummy(sigs)
    assert len(trader2.positions) == 2
    trader3 = strategy.dummy(sigs, sleep_time=0.1)
    assert len(trader3.positions) == 2

    for i in [0, 1]:
        pos1 = trader1.positions[i]
        assert trader1.positions[i].evaluate()['日胜率'] == trader2.positions[i].evaluate()['日胜率']
        assert len(trader1.positions[i].pairs) == len(trader2.positions[i].pairs)
        assert round(pos1.evaluate("多空")['覆盖率'], 3) == round(pos1.evaluate("多头")['覆盖率'] + pos1.evaluate("空头")['覆盖率'], 3)

    strategy.replay(bars, res_path="trade_replay_test", sdt='20190101', refresh=True)
    assert len(os.listdir("trade_replay_test")) == 3
    shutil.rmtree("trade_replay_test")

    # 验证信号计算的准确性
    strategy.check(bars, res_path="trade_check_test", sdt='20190101', exist_ok=False)
    assert len(os.listdir("trade_check_test")) == 2
    assert os.path.exists(os.path.join("trade_check_test", "signals.xlsx"))
    assert os.path.exists(os.path.join("trade_check_test", "15分钟_D0停顿分型_BE辅助V230106"))
    shutil.rmtree("trade_check_test")
