# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/24 16:20
"""
import sys

sys.path.insert(0, '.')
sys.path.insert(0, '..')

from czsc.data.ts_cache import *


def offline_test_ts_cache():
    dc = TsDataCache(data_path='.', sdt='20200101', edt='20211024', verbose=True)
    cache_path = './TS_CACHE_20200101_20211024'
    assert os.path.exists(cache_path)

    df = dc.ths_index('A', 'N')
    assert not df.empty and os.path.exists(os.path.join(dc.api_path_map['ths_index'], "ths_index_A_N.pkl"))
    df = dc.ths_index('A')
    assert not df.empty
    df = dc.ths_index('A', None)
    assert not df.empty and os.path.exists(os.path.join(dc.api_path_map['ths_index'], "ths_index_A_None.pkl"))

    df = dc.get_all_ths_members('A', None)
    assert not df.empty and os.path.exists(os.path.join(dc.api_path_map['ths_index'], "A_None_ths_members.pkl"))

    bars = dc.ths_daily(ts_code='885566.TI', start_date='20200101', end_date='20211024', raw_bar=False)
    assert len(bars) == 436

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

    df_d = dc.daily_basic(ts_code='300033.SZ', start_date='20200101', end_date='20210101')
    assert len(df_d) == 243
    df_d = dc.daily_basic(ts_code='300033.SZ', start_date='20200101', end_date='20210101')
    assert len(df_d) == 243

    # 测试指数成分和权重数据缓存
    df = dc.index_weight('000905.SH', '20210923')
    assert len(df) == 500
    df = dc.index_weight('000905.SH', '20210901')
    assert len(df) == 500

    df = dc.index_weight('000300.SH', '20200208')
    assert len(df) == 300

    # 测试复权因子获取
    df = dc.adj_factor(ts_code='000001.SZ')
    assert not df.empty

    df = dc.get_all_ths_members(exchange='A', type_='N')
    assert not df.empty

    df = dc.limit_list(trade_date='20210324')
    assert not df.empty and os.path.exists(os.path.join(dc.api_path_map['limit_list'], "limit_list_20210324.pkl"))

    # 测试复权分钟线获取
    df1 = dc.pro_bar_minutes(ts_code='000002.SZ', asset='E', freq='30min',
                             sdt="20200101", edt="20210804 11:24", adj='hfq', raw_bar=False)

    df2 = dc.pro_bar_minutes(ts_code='000002.SZ', asset='E', freq='30min',
                             sdt="20200101", edt="20210804 11:24", adj='qfq', raw_bar=False)

    df3 = dc.pro_bar_minutes(ts_code='000002.SZ', asset='E', freq='30min',
                             sdt="20200101", edt="20210804 11:24", adj=None, raw_bar=False)
    assert len(df1) == len(df2) == len(df3) and df1.iloc[-1]['close'] > df3.iloc[-1]['close'] > df2.iloc[-1]['close']

    x1 = dc.get_next_trade_dates('2021-12-13', n=-1, m=None)
    assert x1 == '20211210'
    x1 = dc.get_next_trade_dates('2021-12-13', n=1, m=None)
    assert x1 == '20211214'
    x2 = dc.get_next_trade_dates('2021-12-13', n=1, m=6)
    assert x2 == ['20211214', '20211215', '20211216', '20211217', '20211220']

    dc.clear()
    assert not os.path.exists(cache_path)
