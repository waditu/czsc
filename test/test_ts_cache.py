# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/24 16:20
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

import os
from czsc.data.ts_cache import TsDataCache


def offline_test_ts_cache():
    dc = TsDataCache(data_path='.', sdt='20200101', edt='20211024', verbose=True)
    cache_path = './TS_CACHE_20200101_20211024'
    assert os.path.exists(cache_path)

    df = dc.ths_index('A')
    assert not df.empty and os.path.exists(os.path.join(cache_path, "ths_index_A.pkl"))
    df = dc.ths_index('A')
    assert not df.empty

    bars = dc.pro_bar(ts_code='000001.SZ', asset='E', freq='D',
                      start_date='20200101', end_date='20211024', raw_bar=True)
    assert len(bars) == 436
    df = dc.pro_bar(ts_code='000001.SZ', asset='E', freq='D',
                    start_date='20200101', end_date='20211024', raw_bar=False)
    assert len(df) == 436
    df = dc.pro_bar(ts_code='000001.SZ', asset='E', freq='D',
                    start_date='20210108', end_date='20210108', raw_bar=False)
    assert len(df) == 1

    hk_holds = dc.hk_hold('20211103')
    assert hk_holds.shape[0] == 2965
    hk_holds = dc.hk_hold('20211103')
    assert hk_holds.shape[0] == 2965

    news = dc.cctv_news('20211103')
    assert news.shape[0] == 14
    news = dc.cctv_news('20211103')
    assert news.shape[0] == 14

    dc.clear()
    assert not os.path.exists(cache_path)

