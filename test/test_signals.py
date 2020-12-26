import sys
import warnings

sys.path.insert(0, '.')
sys.path.insert(0, '..')

from czsc.data.jq import get_kline
from czsc.data import freq_map
from czsc.signals import KlineSignals

def test_signals():
    kline = get_kline(symbol="300033.XSHE", end_date="20201128", freq="5min", count=1000)
    ks = KlineSignals(kline, name=freq_map.get("5min", "本级别"), bi_mode="new", max_count=2000)
    print(ks.get_signals())


