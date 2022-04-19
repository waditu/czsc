# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/3/10 12:22
describe: 请描述文件用途
"""
from datetime import timedelta
from czsc.ai import utils


def test_datetime_spans():
    spans = utils.get_datetime_spans(sdt='20170101', edt='20220101', train_days=365, valid_days=7, method='rolling')
    assert len(spans) == 209
    assert spans[-2][1] - spans[-2][0] == timedelta(days=365)

    spans = utils.get_datetime_spans(sdt='20170101', edt='20220101', train_days=400, valid_days=7, method='rolling')
    assert len(spans) == 204
    assert spans[-2][1] - spans[-2][0] == timedelta(days=400)

    spans = utils.get_datetime_spans(sdt='20170101', edt='20220101', train_days=400, valid_days=30, method='rolling')
    assert len(spans) == 48
    assert spans[-2][1] - spans[-2][0] == timedelta(days=400)

    spans = utils.get_datetime_spans(sdt='20170101', edt='20220101', train_days=400, valid_days=30, method='expanding')
    assert len(spans) == 48
    assert spans[-2][1] - spans[-2][0] != timedelta(days=400)



