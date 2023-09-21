# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/3/17 21:41
describe: 环境变量统一管理入口
"""

import os

# True 的有效表达
valid_true = ['1', 'True', 'true', 'Y', 'y', 'yes', 'Yes', True]


def get_verbose(verbose=None):
    """verbose - 是否输出执行过程的详细信息"""
    verbose = verbose if verbose else os.environ.get('czsc_verbose', None)
    v = True if verbose in valid_true else False
    return v


def get_welcome():
    """welcome - 是否输出版本标识和缠中说禅博客摘记"""
    v = True if os.environ.get('czsc_welcome', '0') in valid_true else False
    return v


def get_min_bi_len(v: int = None) -> int:
    """min_bi_len - 一笔的最小长度，也就是无包含K线的数量，7是老笔的要求，6是新笔的要求"""
    min_bi_len = v if v else os.environ.get('czsc_min_bi_len', 6)
    return int(float(min_bi_len))


def get_max_bi_num(v: int = None) -> int:
    """max_bi_num - 单个级别K线分析中，程序最大保存的笔数量

    默认值为 50，仅使用内置的信号和因子，不需要调整这个参数。
    如果进行新的信号计算需要用到更多的笔，可以适当调大这个参数。
    """
    max_bi_num = v if v else os.environ.get('czsc_max_bi_num', 50)
    return int(float(max_bi_num))


def get_bi_change_th(v: float = None) -> float:
    """bi_change_th - 成笔需要超过benchmark的比例阈值

    benchmark 是上一笔涨跌幅与最近五笔平均涨跌幅均值的最小值

    设置成 -1，可以关闭根据当前笔涨跌幅达到benchmark的比例来确定笔
    """
    bi_change_th = v if v else os.environ.get('czsc_bi_change_th', '1')
    bi_change_th = float(bi_change_th)
    assert 2 >= bi_change_th >= 0.5 or bi_change_th == -1, "czsc_bi_change_th not in [0.5, 2]"
    return bi_change_th
