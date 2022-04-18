# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/3/17 21:41
describe: 环境变量统一管理入口
"""

import os


def get_verbose(verbose=None):
    """verbose - 是否输出执行过程的详细信息"""
    valid_true = ['1', 'True', 'true', 'Y', 'y', 'yes', 'Yes']
    verbose = verbose if verbose else os.environ.get('czsc_verbose', None)
    v = True if verbose in valid_true else False
    return v


def get_min_bi_len(v: int = None) -> int:
    """min_bi_len - 一笔的最小长度，也就是无包含K线的数量，7是老笔的要求"""
    min_bi_len = v if v else os.environ.get('czsc_min_bi_len', 7)
    return int(float(min_bi_len))
