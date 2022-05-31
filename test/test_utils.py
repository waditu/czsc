# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/16 20:31
describe: czsc.utils 单元测试
"""
from czsc import utils


def test_x_round():
    assert utils.x_round(100, 3) == 100
    assert utils.x_round(1.000342, 3) == 1.0
    assert utils.x_round(1.000342, 4) == 1.0003
    assert utils.x_round(1.000342, 5) == 1.00034


