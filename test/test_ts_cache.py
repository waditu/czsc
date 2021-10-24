# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/24 16:20
"""
import os
from czsc.data.ts_cache import TsDataCache

def test_ts_cache():
    dc = TsDataCache(data_path='.', sdt='20200101', edt='20211024', verbose=True)
    cache_path = './TS_CACHE_20200101_20211024'
    assert os.path.exists(cache_path)

    df = dc.ths_index('A')
    assert not df.empty and os.path.exists(os.path.join(cache_path, "ths_index_A.pkl"))
    df = dc.ths_index('A')
    assert not df.empty

    dc.clear()
    assert not os.path.exists(cache_path)

