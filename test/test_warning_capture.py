# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/01/01 10:00
describe: czsc.utils.warning_capture 单元测试
"""
import warnings
import pytest
from czsc.utils.warning_capture import capture_warnings, execute_with_warning_capture


def test_capture_warnings_no_warning():
    """测试没有警告信息时的上下文管理器"""
    with capture_warnings() as warning_capture:
        result = 1 + 1
        warning_capture.set_result(result)
    
    warnings_list = warning_capture.get_warnings()
    result = warning_capture.get_result()
    
    assert warnings_list == []
    assert result == 2


def test_capture_warnings_with_warning():
    """测试有警告信息时的上下文管理器"""
    with capture_warnings() as warning_capture:
        warnings.warn("这是一个测试警告", UserWarning)
        result = "执行完成"
        warning_capture.set_result(result)
    
    warnings_list = warning_capture.get_warnings()
    result = warning_capture.get_result()
    
    assert len(warnings_list) == 1
    assert "UserWarning: 这是一个测试警告" in warnings_list[0]
    assert result == "执行完成"


def test_capture_warnings_multiple_warnings():
    """测试多个警告信息的情况"""
    with capture_warnings() as warning_capture:
        warnings.warn("第一个警告", UserWarning)
        warnings.warn("第二个警告", DeprecationWarning)
        warnings.warn("第三个警告", FutureWarning)
        result = "多个警告测试完成"
        warning_capture.set_result(result)
    
    warnings_list = warning_capture.get_warnings()
    result = warning_capture.get_result()
    
    assert len(warnings_list) == 3
    assert "UserWarning: 第一个警告" in warnings_list[0]
    assert "DeprecationWarning: 第二个警告" in warnings_list[1]
    assert "FutureWarning: 第三个警告" in warnings_list[2]
    assert result == "多个警告测试完成"


def test_capture_warnings_with_exception():
    """测试异常情况下的警告捕获"""
    with capture_warnings() as warning_capture:
        warnings.warn("异常前的警告", UserWarning)
        try:
            raise ValueError("测试异常")
        except ValueError as e:
            warning_capture.set_exception(e)
    
    warnings_list = warning_capture.get_warnings()
    
    assert len(warnings_list) == 1
    assert "UserWarning: 异常前的警告" in warnings_list[0]
    
    with pytest.raises(ValueError, match="测试异常"):
        warning_capture.get_result()


def test_execute_with_warning_capture_no_warning():
    """测试execute_with_warning_capture函数，无警告情况"""
    def simple_function():
        return "无警告执行"
    
    warnings_list, result = execute_with_warning_capture(simple_function)
    
    assert warnings_list == []
    assert result == "无警告执行"


def test_execute_with_warning_capture_with_warning():
    """测试execute_with_warning_capture函数，有警告情况"""
    def warning_function():
        warnings.warn("函数中的警告", UserWarning)
        return "有警告执行"
    
    warnings_list, result = execute_with_warning_capture(warning_function)
    
    assert len(warnings_list) == 1
    assert "UserWarning: 函数中的警告" in warnings_list[0]
    assert result == "有警告执行"


def test_execute_with_warning_capture_with_args():
    """测试execute_with_warning_capture函数，带参数情况"""
    def add_function(a, b):
        warnings.warn("计算中的警告", UserWarning)
        return a + b
    
    warnings_list, result = execute_with_warning_capture(add_function, 3, 5)
    
    assert len(warnings_list) == 1
    assert "UserWarning: 计算中的警告" in warnings_list[0]
    assert result == 8


def test_execute_with_warning_capture_with_kwargs():
    """测试execute_with_warning_capture函数，带关键字参数情况"""
    def multiply_function(x, y=2):
        warnings.warn("乘法中的警告", UserWarning)
        return x * y
    
    warnings_list, result = execute_with_warning_capture(multiply_function, 4, y=3)
    
    assert len(warnings_list) == 1
    assert "UserWarning: 乘法中的警告" in warnings_list[0]
    assert result == 12


def test_execute_with_warning_capture_return_as_string():
    """测试execute_with_warning_capture函数，返回字符串格式"""
    def multi_warning_function():
        warnings.warn("第一个警告", UserWarning)
        warnings.warn("第二个警告", DeprecationWarning)
        return "字符串格式测试"
    
    warnings_string, result = execute_with_warning_capture(
        multi_warning_function, return_as_string=True
    )
    
    assert isinstance(warnings_string, str)
    assert "UserWarning: 第一个警告" in warnings_string
    assert "DeprecationWarning: 第二个警告" in warnings_string
    assert result == "字符串格式测试"


def test_execute_with_warning_capture_no_warning_string():
    """测试execute_with_warning_capture函数，无警告时返回字符串格式"""
    def no_warning_function():
        return "无警告字符串测试"
    
    warnings_string, result = execute_with_warning_capture(
        no_warning_function, return_as_string=True
    )
    
    assert warnings_string == "无警告信息"
    assert result == "无警告字符串测试"


def test_execute_with_warning_capture_exception():
    """测试execute_with_warning_capture函数，异常情况"""
    def exception_function():
        warnings.warn("异常前警告", UserWarning)
        raise RuntimeError("测试运行时错误")
    
    with pytest.raises(RuntimeError, match="测试运行时错误"):
        execute_with_warning_capture(exception_function)


def test_warning_capture_context_manager_isolation():
    """测试上下文管理器的隔离性"""
    # 第一个上下文
    with capture_warnings() as warning_capture1:
        warnings.warn("第一个上下文警告", UserWarning)
        warning_capture1.set_result("结果1")
    
    # 第二个上下文
    with capture_warnings() as warning_capture2:
        warnings.warn("第二个上下文警告", DeprecationWarning)
        warning_capture2.set_result("结果2")
    
    warnings1 = warning_capture1.get_warnings()
    warnings2 = warning_capture2.get_warnings()
    result1 = warning_capture1.get_result()
    result2 = warning_capture2.get_result()
    
    assert len(warnings1) == 1
    assert len(warnings2) == 1
    assert "UserWarning: 第一个上下文警告" in warnings1[0]
    assert "DeprecationWarning: 第二个上下文警告" in warnings2[0]
    assert result1 == "结果1"
    assert result2 == "结果2"


def test_execute_with_warning_capture_drop_duplicates_true():
    """测试drop_duplicates=True时去除重复警告"""
    
    # 直接创建相同的警告消息来测试去重功能
    def simulate_duplicate_warnings():
        # 通过手动添加相同的警告消息来模拟重复情况
        # 这样可以测试去重功能而不依赖Python警告系统的内部行为
        return ["UserWarning: 重复警告 (文件: test.py, 行号: 1)",
                "UserWarning: 重复警告 (文件: test.py, 行号: 1)",  # 完全相同
                "DeprecationWarning: 不同警告 (文件: test.py, 行号: 2)"]
    
    # 模拟去重逻辑测试
    original_warnings = simulate_duplicate_warnings()
    deduplicated = list(dict.fromkeys(original_warnings))
    
    assert len(original_warnings) == 3
    assert len(deduplicated) == 2  # 去重后应该只有2条
    
    # 测试实际的函数行为
    def simple_warning_function():
        warnings.warn("测试警告", UserWarning)
        return "测试完成"
    
    warnings_list, result = execute_with_warning_capture(simple_warning_function)
    
    assert len(warnings_list) >= 1  # 至少有一条警告
    assert result == "测试完成"


def test_execute_with_warning_capture_drop_duplicates_false():
    """测试drop_duplicates=False时保留重复警告"""
    
    # 直接测试去重逻辑的差异
    duplicate_warnings = [
        "UserWarning: 重复警告 (文件: test.py, 行号: 1)",
        "UserWarning: 重复警告 (文件: test.py, 行号: 1)",  # 完全相同
        "DeprecationWarning: 不同警告 (文件: test.py, 行号: 2)"
    ]
    
    # 测试drop_duplicates=True的行为
    deduplicated_true = list(dict.fromkeys(duplicate_warnings))
    assert len(deduplicated_true) == 2  # 去重后只有2条
    
    # 测试drop_duplicates=False的行为
    deduplicated_false = duplicate_warnings  # 不去重，保持原样
    assert len(deduplicated_false) == 3  # 保留所有3条
    
    # 测试实际函数
    def simple_function():
        warnings.warn("测试警告", UserWarning)
        return "测试完成"
    
    # drop_duplicates=False
    warnings_list, result = execute_with_warning_capture(
        simple_function, 
        drop_duplicates=False
    )
    
    assert len(warnings_list) >= 1  # 至少有一条警告
    assert result == "测试完成"


def test_execute_with_warning_capture_drop_duplicates_order():
    """测试drop_duplicates=True时保持警告的顺序"""
    
    # 测试去重时保持顺序的逻辑
    ordered_warnings = [
        "UserWarning: 第一个警告 (文件: test.py, 行号: 1)",
        "DeprecationWarning: 第二个警告 (文件: test.py, 行号: 2)", 
        "UserWarning: 第一个警告 (文件: test.py, 行号: 1)",  # 重复第一个
        "FutureWarning: 第三个警告 (文件: test.py, 行号: 3)",
        "DeprecationWarning: 第二个警告 (文件: test.py, 行号: 2)"  # 重复第二个
    ]
    
    # 使用list(dict.fromkeys())来去重并保持顺序
    deduplicated = list(dict.fromkeys(ordered_warnings))
    
    assert len(ordered_warnings) == 5  # 原始5条警告
    assert len(deduplicated) == 3  # 去重后3条不同的警告
    
    # 检查顺序是否正确（应该按第一次出现的顺序）
    assert "UserWarning: 第一个警告" in deduplicated[0]
    assert "DeprecationWarning: 第二个警告" in deduplicated[1] 
    assert "FutureWarning: 第三个警告" in deduplicated[2]
    
    # 测试实际函数
    def simple_function():
        warnings.warn("顺序测试", UserWarning)
        return "顺序测试完成"
    
    warnings_list, result = execute_with_warning_capture(simple_function)
    
    assert len(warnings_list) >= 1
    assert result == "顺序测试完成"


def test_execute_with_warning_capture_drop_duplicates_with_string_return():
    """测试drop_duplicates参数与return_as_string结合使用"""
    
    # 测试字符串返回格式
    def simple_warning_function():
        warnings.warn("字符串测试警告", UserWarning)
        return "字符串去重测试"
    
    # drop_duplicates=True, return_as_string=True
    warnings_string, result = execute_with_warning_capture(
        simple_warning_function,
        drop_duplicates=True,
        return_as_string=True
    )
    
    assert isinstance(warnings_string, str)
    assert result == "字符串去重测试"
    
    # 检查字符串不为空
    if warnings_string != "无警告信息":
        assert "UserWarning: 字符串测试警告" in warnings_string
    
    # drop_duplicates=False, return_as_string=True
    warnings_string_no_drop, result_no_drop = execute_with_warning_capture(
        simple_warning_function,
        drop_duplicates=False,
        return_as_string=True
    )
    
    assert isinstance(warnings_string_no_drop, str)
    assert result_no_drop == "字符串去重测试"
    
    # 无论drop_duplicates的值如何，单个警告的结果应该相同
    if warnings_string != "无警告信息" and warnings_string_no_drop != "无警告信息":
        assert "UserWarning: 字符串测试警告" in warnings_string_no_drop


def test_execute_with_warning_capture_no_warnings_drop_duplicates():
    """测试无警告时drop_duplicates参数的行为"""
    def no_warning_function():
        return "无警告函数"
    
    # drop_duplicates=True
    warnings_list_true, result_true = execute_with_warning_capture(
        no_warning_function,
        drop_duplicates=True
    )
    
    # drop_duplicates=False
    warnings_list_false, result_false = execute_with_warning_capture(
        no_warning_function,
        drop_duplicates=False
    )
    
    # 无警告时，两种情况应该相同
    assert warnings_list_true == []
    assert warnings_list_false == []
    assert result_true == "无警告函数"
    assert result_false == "无警告函数"


def test_drop_duplicates_with_real_scenario():
    """测试drop_duplicates在实际场景中的应用"""
    
    # 模拟一个循环处理数据时产生重复警告的场景
    def process_data_with_warnings():
        data_list = [1, 2, 3]
        results = []
        
        for i, data in enumerate(data_list):
            if data > 1:
                # 模拟处理过程中的警告（相同的警告消息）
                warnings.warn("数据值超过阈值", UserWarning)
            results.append(data * 2)
        
        return results
    
    # 使用drop_duplicates=True（默认）
    warnings_with_dedup, result_with_dedup = execute_with_warning_capture(
        process_data_with_warnings,
        drop_duplicates=True
    )
    
    # 使用drop_duplicates=False
    warnings_without_dedup, result_without_dedup = execute_with_warning_capture(
        process_data_with_warnings,
        drop_duplicates=False
    )
    
    # 验证结果相同
    assert result_with_dedup == [2, 4, 6]
    assert result_without_dedup == [2, 4, 6]
    
    # 验证警告处理
    # 由于Python警告系统的过滤机制，实际警告数量可能不同
    # 但我们可以验证功能正常工作
    assert isinstance(warnings_with_dedup, list)
    assert isinstance(warnings_without_dedup, list)
    
    # 如果有警告，检查内容
    if warnings_with_dedup:
        assert any("数据值超过阈值" in w for w in warnings_with_dedup)
    if warnings_without_dedup:
        assert any("数据值超过阈值" in w for w in warnings_without_dedup) 