# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/3/10 12:21
describe: 搞人工智能模型需要用到的一些工具函数
"""
import pandas as pd
from typing import Union
from datetime import datetime, timedelta


def get_datetime_spans(sdt: Union[datetime, str],
                       edt: Union[datetime, str],
                       train_days: int,
                       valid_days: int,
                       method: str = 'rolling'):
    """滚动训练数据分割时间范围

    :param sdt: 开始时间
    :param edt: 结束时间
    :param train_days: 固定的训练集覆盖天数
    :param valid_days: 固定的验证集覆盖天数
    :param method: 时间滚动方法，rolling 表示固定天数滚动，expanding 表示扩张天数滚动
    :return:
    """
    method = method.lower()
    sdt = pd.to_datetime(sdt)
    edt = pd.to_datetime(edt)
    train_delta = timedelta(days=train_days)
    valid_delta = timedelta(days=valid_days)

    spans = []

    train_sdt = sdt
    train_edt = min(sdt + train_delta, edt)
    valid_sdt = train_edt
    valid_edt = min(train_edt + valid_delta, edt)

    spans.append([train_sdt, train_edt, valid_sdt, valid_edt])

    while valid_edt < edt:
        sdt1, edt1, sdt2, edt2 = spans[-1]

        if method == 'rolling':
            train_sdt = edt2 - train_delta
            train_edt = edt2
            valid_sdt = edt2
            valid_edt = min(edt2 + valid_delta, edt)
        elif method == 'expanding':
            train_sdt = sdt
            train_edt = edt2
            valid_sdt = edt2
            valid_edt = min(edt2 + valid_delta, edt)
        else:
            raise ValueError(f"method error, optional values are ['rolling', 'expanding']")

        spans.append([train_sdt, train_edt, valid_sdt, valid_edt])

    return spans



