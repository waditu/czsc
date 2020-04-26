# coding: utf-8
import sys
from cobra.data.kline import get_kline
sys.path.insert(0, r'C:\git_repo\zengbin93\chan')
import chan
from chan import KlineAnalyze
from chan.analyze import is_bei_chi

print(chan.__version__)


def test_bei_chi():
    df = get_kline(ts_code="300008.SZ", end_dt="2020-03-23 15:00:00", freq='30min', asset='E')
    ka = KlineAnalyze(df)


def test_kline_analyze():
    df = get_kline(ts_code="300008.SZ", end_dt="2020-03-23 15:00:00", freq='30min', asset='E')
    ka = KlineAnalyze(df)

    # 测试笔的识别结果


