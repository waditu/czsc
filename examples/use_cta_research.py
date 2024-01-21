# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/6/7 21:12
describe:
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

from czsc import CTAResearch
from czsc.strategies import CzscStrategyExample2
from czsc.connectors.research import get_raw_bars, get_symbols

bot = CTAResearch(results_path=r"D:\CTA投研\策略测试", signals_module_name='czsc.signals',
                  strategy=CzscStrategyExample2, read_bars=get_raw_bars)

# 策略回放
# bot.replay(symbol='600256.SH', sdt='20220101', edt='20230101', refresh=True)


if __name__ == '__main__':
    # 策略回测，如果是使用多进程，必须在 __main__ 中执行，且必须是在命令行中执行
    bot.backtest(symbols=get_symbols("中证500成分股")[:10], max_workers=3, bar_sdt='20190101', edt='20220101', sdt='20200101')
