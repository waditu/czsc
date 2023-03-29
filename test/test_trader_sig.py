# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/3/29 15:28
describe: 
"""
import re
from czsc.traders.sig_parse import SignalsParser


def test_signals_parser():
    sp = SignalsParser()
    conf = sp.parse(['日线_D1MO3_BE辅助V230222_新低_第2次_任意_0'])
    assert not conf

    def cxt_bi_end_V230222(signal):
        # https://czsc.readthedocs.io/en/0.9.13/api/czsc.signals.cxt_bi_end_V230222.html
        pats = re.findall(r"(.*?)_D(\d+)MO(\d+)_", signal)[0]
        _row = {"freq": pats[0], "di": int(pats[1]), 'max_overlap': int(pats[2])}
        return _row

    sp = SignalsParser(usr_parse_map={'cxt_bi_end_V230222': cxt_bi_end_V230222})
    conf = sp.parse(['日线_D1MO3_BE辅助V230222_新低_第2次_任意_0'])
    assert not conf
