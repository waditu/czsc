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
    print("开始测试 V字反转识别功能...")
    from czsc.utils.mark_czsc_status import mark_czsc_status
    # 使用czsc的mock数据生成功能
    import czsc
    dfk = czsc.mock.generate_klines()
    print(f"生成的测试数据形状: {dfk.shape}")
    print(f"数据列: {dfk.columns.tolist()}")

    # 调用状态标记函数
    dfr, bi_stats_marked = mark_czsc_status(dfk, verbose=True)

    print(f"\n处理后K线数据形状: {dfr.shape}")
    print(f"笔统计数据形状: {bi_stats_marked.shape}")

    # 检查新增的标记列
    mark_cols = ['is_reversal', 'is_trend', 'is_oscillation', 'is_normal']
    print("\n新增标记列统计:")
    for col in mark_cols:
        if col in dfr.columns:
            count = dfr[col].sum()
            percentage = count / len(dfr) * 100
            print(f"  {col}: {count} 根K线 ({percentage:.2f}%)")

    # 检查笔统计数据
    if 'mark' in bi_stats_marked.columns:
        mark_counts = bi_stats_marked['mark'].value_counts()
        print("\n笔状态类型统计:")
        for mark_type, count in mark_counts.items():
            percentage = count / len(bi_stats_marked) * 100
            print(f"  {mark_type}: {count} 笔 ({percentage:.2f}%)")

    print("\n[SUCCESS] V字反转识别功能测试成功！")
    return True
