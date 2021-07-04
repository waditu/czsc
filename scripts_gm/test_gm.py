# coding: utf-8
from scripts_gm.gm_utils import *

def test_gm_czsc_trader():
    gt = GmCzscTrader('SZSE.300803', end_date='20210618')
    gt.update_factors()


def test_get_init_kg():
    kg = get_init_kg_v1(symbol='SZSE.300803', end_dt='2021-06-18 13:45:00+0800')

    assert kg.end_dt.minute == 45
    assert kg.end_dt.hour == 13

