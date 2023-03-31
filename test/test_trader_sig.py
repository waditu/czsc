# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/29 15:28
describe: 
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import re
import czsc
from czsc.traders.sig_parse import SignalsParser
from test.test_analyze import read_daily


def test_generate_signals_by_conf():
    bars = read_daily()

    def get_signals(cat):
        conf = [
            {'freq1': '日线',
             'freq2': '日线',
             'name': 'czsc.signals.cxt_zhong_shu_gong_zhen_V221221'}
        ]

        return czsc.get_signals_by_conf(cat, conf)

    sigs = czsc.generate_czsc_signals(bars, get_signals, freqs=['日线'])
    assert len(sigs) == 860


def test_signals_parser():
    sp = SignalsParser()
    conf = sp.parse_params('byi_second_bs_V230324', '15分钟_D1MACD12#26#9回抽零轴_BS2辅助V230324_看空_任意_任意_0')
    assert conf

    conf = sp.parse_params('cxt_zhong_shu_gong_zhen_V221221', '日线_60分钟_中枢共振V221221_看多_任意_任意_0')
    assert conf

    conf = sp.parse(['日线_D1MO3_BE辅助V230222_新低_第2次_任意_0'])
    assert conf
