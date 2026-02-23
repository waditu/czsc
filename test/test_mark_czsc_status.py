#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
V字反转识别功能测试脚本

该脚本用于测试 mark_czsc_status.py 模块的功能，验证V字反转识别是否正常工作。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_mark_czsc_status():
    """测试 mark_czsc_status 函数的基本功能"""
    from czsc.utils.mark_czsc_status import mark_czsc_status
    import czsc
    dfk = czsc.mock.generate_klines()
    assert len(dfk) > 0, "生成的测试数据不应为空"

    # 调用状态标记函数
    dfr, bi_stats_marked = mark_czsc_status(dfk, verbose=True)

    assert len(dfr) > 0, "处理后K线数据不应为空"
    assert len(bi_stats_marked) > 0, "笔统计数据不应为空"

    # 检查新增的标记列
    mark_cols = ['is_reversal', 'is_trend', 'is_oscillation', 'is_normal']
    for col in mark_cols:
        assert col in dfr.columns, f"应包含标记列 {col}"

    # 检查笔统计数据中的 mark 列
    assert 'mark' in bi_stats_marked.columns, "笔统计数据应包含 mark 列"
