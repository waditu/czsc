from czsc.data.jq import *
import traceback
from datetime import datetime
from typing import List
from czsc.analyze import CZSC, CzscTrader
from czsc.signals import get_default_signals
from czsc.objects import Signal, Factor


def test_get_data():
    bars = get_kline("002202.XSHE", freq="1min", end_date=datetime.now(), count=2)
    print(bars)


def test_data():
    factor_ = Factor(
        name="类三买选股因子",
        signals_any=[
            Signal("日线_倒1笔_基础形态_类三买_任意_任意_0"),
            Signal("日线_倒1笔_类买卖点_类三买_任意_任意_0"),
        ],
        signals_all=[
            Signal("日线_倒1笔_拟合优度_小于0.2_任意_任意_0")
        ]
    )

    trander = JqCzscTrader(symbol="002172.XSHE", max_count=1000)

    print(factor_.is_match(trander.s))
    trander.open_in_browser()
    # kg = KlineGenerator(max_count=1000, freqs=['5分钟', '30分钟', '日线'])
    # trader = CzscTrader(kg=kg, get_signals=get_default_signals)
    # trader.open_in_browser()
