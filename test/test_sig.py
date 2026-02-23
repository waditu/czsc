# -*- coding: utf-8 -*-
"""
test_sig.py - czsc.utils.sig 信号辅助工具函数单元测试

Mock数据格式说明:
- check_cross_info/fast_slow_cross: 输入为等长数值列表或 numpy 数组
- same_dir_counts/count_last_same: 输入为数值列表
- get_sub_elements: 输入为任意类型列表
- cross_zero_axis: 输入为等长数值列表
- down_cross_count: 输入为等长数值列表
- cal_cross_num: 输入为 fast_slow_cross 返回的交叉信息列表

测试覆盖:
- 基本功能验证
- 边界情况: 空数据、单值、全同值
- 异常输入处理
"""
import numpy as np
import pytest
from czsc.utils.sig import (
    create_single_signal,
    check_cross_info,
    fast_slow_cross,
    same_dir_counts,
    count_last_same,
    get_sub_elements,
    cross_zero_axis,
    cal_cross_num,
    down_cross_count,
)


class TestCreateSingleSignal:
    """测试 create_single_signal 函数"""

    def test_basic(self):
        """测试基本信号创建"""
        s = create_single_signal(k1="1分钟", k2="倒1", k3="形态", v1="类一买")
        assert isinstance(s, dict)
        assert len(s) == 1

    def test_default_values(self):
        """测试默认值"""
        s = create_single_signal(k1="1分钟")
        assert isinstance(s, dict)
        assert len(s) == 1

    def test_with_score(self):
        """测试带分数的信号"""
        s = create_single_signal(k1="1分钟", k2="倒1", k3="形态", v1="看多", score=5)
        assert isinstance(s, dict)


class TestCheckCrossInfo:
    """测试 check_cross_info 函数"""

    def test_golden_cross(self):
        """测试金叉检测"""
        fast = [1, 2, 3, 4, 5, 6, 7]
        slow = [7, 6, 5, 4, 3, 2, 1]
        result = check_cross_info(fast, slow)
        assert isinstance(result, list)
        # fast从低于slow到高于slow，应该有金叉
        golden_crosses = [x for x in result if x["类型"] == "金叉"]
        assert len(golden_crosses) >= 1

    def test_death_cross(self):
        """测试死叉检测"""
        fast = [7, 6, 5, 4, 3, 2, 1]
        slow = [1, 2, 3, 4, 5, 6, 7]
        result = check_cross_info(fast, slow)
        death_crosses = [x for x in result if x["类型"] == "死叉"]
        assert len(death_crosses) >= 1

    def test_no_cross(self):
        """测试无交叉"""
        fast = [10, 11, 12, 13, 14]
        slow = [1, 2, 3, 4, 5]
        result = check_cross_info(fast, slow)
        assert len(result) == 0

    def test_numpy_input(self):
        """测试 numpy 数组输入"""
        fast = np.array([1, 2, 3, 4, 5, 6, 7])
        slow = np.array([7, 6, 5, 4, 3, 2, 1])
        result = check_cross_info(fast, slow)
        assert isinstance(result, list)

    def test_unequal_length_raises(self):
        """测试不等长输入应抛出异常"""
        with pytest.raises(AssertionError):
            check_cross_info([1, 2, 3], [1, 2])

    def test_cross_info_fields(self):
        """测试返回字段完整性"""
        fast = [1, 2, 3, 4, 5, 6, 7]
        slow = [7, 6, 5, 4, 3, 2, 1]
        result = check_cross_info(fast, slow)
        if result:
            expected_keys = {"位置", "类型", "快线", "慢线", "距离", "距今", "面积", "价差", "快线高点", "快线低点", "慢线高点", "慢线低点"}
            assert set(result[0].keys()) == expected_keys


class TestSameDirCounts:
    """测试 same_dir_counts 函数"""

    def test_all_positive(self):
        """测试全正数"""
        assert same_dir_counts([1, 2, 3]) == 3

    def test_all_negative(self):
        """测试全负数"""
        assert same_dir_counts([-1, -2, -3]) == 3

    def test_mixed(self):
        """测试混合序列"""
        assert same_dir_counts([-1, -2, 1, 2, 3]) == 3

    def test_single_element(self):
        """测试单元素"""
        assert same_dir_counts([5]) == 1
        assert same_dir_counts([-5]) == 1

    def test_direction_change(self):
        """测试方向变化"""
        # 最后是正数，往前数到第一个负数
        assert same_dir_counts([-1, -1, -2, -3, 0, 1, 2, 3, -1, -2, 1, 1, 2, 3]) == 4


class TestCountLastSame:
    """测试 count_last_same 函数"""

    def test_all_same(self):
        """测试全部相同"""
        assert count_last_same([1, 1, 1, 1]) == 4

    def test_last_different(self):
        """测试末尾不同"""
        assert count_last_same([1, 2, 3, 3, 3]) == 3

    def test_single_element(self):
        """测试单元素"""
        assert count_last_same([5]) == 1

    def test_no_repeat(self):
        """测试无重复"""
        assert count_last_same([1, 2, 3, 4]) == 1

    def test_tuple_input(self):
        """测试 tuple 输入"""
        assert count_last_same((1, 2, 2, 2)) == 3


class TestGetSubElements:
    """测试 get_sub_elements 函数"""

    def test_basic(self):
        """测试基本功能"""
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        result = get_sub_elements(x, di=1, n=3)
        assert result == [7, 8, 9]

    def test_di_2(self):
        """测试 di=2"""
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        result = get_sub_elements(x, di=2, n=3)
        assert result == [6, 7, 8]

    def test_n_larger_than_list(self):
        """测试 n 大于列表长度"""
        x = [1, 2, 3]
        result = get_sub_elements(x, di=1, n=10)
        assert result == [1, 2, 3]

    def test_di_0_raises(self):
        """测试 di=0 应抛出异常"""
        with pytest.raises(AssertionError):
            get_sub_elements([1, 2, 3], di=0, n=2)


class TestCrossZeroAxis:
    """测试 cross_zero_axis 函数"""

    def test_basic(self):
        """测试基本功能"""
        n1 = [1, 2, 3, -1, -2]
        n2 = [1, 1, 1, 1, 1]
        result = cross_zero_axis(n1, n2)
        assert isinstance(result, int)
        assert result >= 0

    def test_no_cross(self):
        """测试无交叉"""
        n1 = [1, 2, 3, 4, 5]
        n2 = [1, 2, 3, 4, 5]
        result = cross_zero_axis(n1, n2)
        assert isinstance(result, int)

    def test_unequal_length_raises(self):
        """测试不等长应抛出异常"""
        with pytest.raises(AssertionError):
            cross_zero_axis([1, 2], [1, 2, 3])


class TestCalCrossNum:
    """测试 cal_cross_num 函数"""

    def test_empty_cross(self):
        """测试空交叉列表"""
        jc, sc = cal_cross_num([])
        assert jc == 0
        assert sc == 0

    def test_single_cross(self):
        """测试单个交叉"""
        cross = [{"类型": "金叉", "距离": 5}]
        jc, sc = cal_cross_num(cross)
        assert jc == 1
        assert sc == 0

    def test_with_distance_filter(self):
        """测试距离过滤"""
        cross = [
            {"类型": "金叉", "距离": 5},
            {"类型": "死叉", "距离": 1},
        ]
        jc, sc = cal_cross_num(cross, distance=3)
        assert isinstance(jc, int)
        assert isinstance(sc, int)


class TestDownCrossCount:
    """测试 down_cross_count 函数"""

    def test_basic(self):
        """测试基本下穿计数"""
        x1 = [5, 4, 3, 2, 1]
        x2 = [1, 2, 3, 4, 5]
        result = down_cross_count(x1, x2)
        assert result >= 1

    def test_no_cross(self):
        """测试无下穿"""
        x1 = [10, 11, 12, 13, 14]
        x2 = [1, 2, 3, 4, 5]
        result = down_cross_count(x1, x2)
        assert result == 0

    def test_numpy_input(self):
        """测试 numpy 数组输入"""
        x1 = np.array([5, 4, 3, 2, 1])
        x2 = np.array([1, 2, 3, 4, 5])
        result = down_cross_count(x1, x2)
        assert isinstance(result, (int, np.integer))
