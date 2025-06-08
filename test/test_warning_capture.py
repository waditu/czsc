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