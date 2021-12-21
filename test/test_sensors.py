# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/12/21 21:59
"""

import warnings
import os

import czsc
from czsc.sensors.utils import compound_returns

warnings.warn(f"czsc version is {czsc.__version__}_{czsc.__date__}")

cur_path = os.path.split(os.path.realpath(__file__))[0]


def test_compound_returns():
    n1b = [100, -90, 234, -50, 300, -250]
    v = compound_returns(n1b)
    assert int(v[0]) == 235
    assert len(v[1]) == len(n1b)


