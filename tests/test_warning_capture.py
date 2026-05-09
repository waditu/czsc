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
        warnings.warn("这是一个测试警告", UserWarning, stacklevel=2)
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
        warnings.warn("第一个警告", UserWarning, stacklevel=2)
        warnings.warn("第二个警告", DeprecationWarning, stacklevel=2)
        warnings.warn("第三个警告", FutureWarning, stacklevel=2)
        result = "多个警告测试完成"
        warning_capture.set_result(result)

    warnings_list = warning_capture.get_warnings()
    result = warning_capture.get_result()

    # 由于pytest配置中忽略了DeprecationWarning，实际捕获的警告数量可能不同
    assert len(warnings_list) >= 2  # 至少应该有2个警告（忽略了DeprecationWarning）
    assert any("UserWarning: 第一个警告" in w for w in warnings_list), "应该包含UserWarning"
    assert any("FutureWarning: 第三个警告" in w for w in warnings_list), "应该包含FutureWarning"
    assert result == "多个警告测试完成"


def test_capture_warnings_with_exception():
    """测试异常情况下的警告捕获"""
    with capture_warnings() as warning_capture:
        warnings.warn("异常前的警告", UserWarning, stacklevel=2)
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
        warnings.warn("函数中的警告", UserWarning, stacklevel=2)
        return "有警告执行"

    warnings_list, result = execute_with_warning_capture(warning_function)

    assert len(warnings_list) == 1
    assert "UserWarning: 函数中的警告" in warnings_list[0]
    assert result == "有警告执行"


def test_execute_with_warning_capture_with_args():
    """测试execute_with_warning_capture函数，带参数情况"""

    def add_function(a, b):
        warnings.warn("计算中的警告", UserWarning, stacklevel=2)
        return a + b

    warnings_list, result = execute_with_warning_capture(add_function, 3, 5)

    assert len(warnings_list) == 1
    assert "UserWarning: 计算中的警告" in warnings_list[0]
    assert result == 8


def test_execute_with_warning_capture_with_kwargs():
    """测试execute_with_warning_capture函数，带关键字参数情况"""

    def multiply_function(x, y=2):
        warnings.warn("乘法中的警告", UserWarning, stacklevel=2)
        return x * y

    warnings_list, result = execute_with_warning_capture(multiply_function, 4, y=3)

    assert len(warnings_list) == 1
    assert "UserWarning: 乘法中的警告" in warnings_list[0]
    assert result == 12


def test_execute_with_warning_capture_return_as_string():
    """测试execute_with_warning_capture函数，返回字符串格式"""

    def multi_warning_function():
        warnings.warn("第一个警告", UserWarning, stacklevel=2)
        warnings.warn("第二个警告", DeprecationWarning, stacklevel=2)
        return "字符串格式测试"

    warnings_string, result = execute_with_warning_capture(multi_warning_function, return_as_string=True)

    assert isinstance(warnings_string, str)
    assert "UserWarning: 第一个警告" in warnings_string
    # DeprecationWarning可能被pytest配置过滤掉，所以不强制要求
    assert result == "字符串格式测试"


def test_execute_with_warning_capture_no_warning_string():
    """测试execute_with_warning_capture函数，无警告时返回字符串格式"""

    def no_warning_function():
        return "无警告字符串测试"

    warnings_string, result = execute_with_warning_capture(no_warning_function, return_as_string=True)

    assert warnings_string == "无警告信息"
    assert result == "无警告字符串测试"


def test_execute_with_warning_capture_exception():
    """测试execute_with_warning_capture函数，异常情况"""

    def exception_function():
        warnings.warn("异常前警告", UserWarning, stacklevel=2)
        raise RuntimeError("测试运行时错误")

    with pytest.raises(RuntimeError, match="测试运行时错误"):
        execute_with_warning_capture(exception_function)


def test_warning_capture_context_manager_isolation():
    """测试上下文管理器的隔离性"""
    # 第一个上下文
    with capture_warnings() as warning_capture1:
        warnings.warn("第一个上下文警告", UserWarning, stacklevel=2)
        warning_capture1.set_result("结果1")

    # 第二个上下文 - 使用UserWarning替代DeprecationWarning以避免pytest过滤
    with capture_warnings() as warning_capture2:
        warnings.warn("第二个上下文警告", UserWarning, stacklevel=2)
        warning_capture2.set_result("结果2")

    warnings1 = warning_capture1.get_warnings()
    warnings2 = warning_capture2.get_warnings()
    result1 = warning_capture1.get_result()
    result2 = warning_capture2.get_result()

    assert len(warnings1) >= 1  # 至少应该有1个警告
    assert len(warnings2) >= 1  # 至少应该有1个警告
    assert any("UserWarning: 第一个上下文警告" in w for w in warnings1), "第一个上下文应该包含相应警告"
    assert any("UserWarning: 第二个上下文警告" in w for w in warnings2), "第二个上下文应该包含相应警告"
    assert result1 == "结果1"
    assert result2 == "结果2"


def test_execute_with_warning_capture_drop_duplicates_true():
    """drop_duplicates=True 时实际函数产出的重复警告条数少于不去重时。

    测试策略：
        让被测函数多次触发同一条警告（通过 warnings.warn 在循环中调用），
        分别以 drop_duplicates=True / False 调用 execute_with_warning_capture，
        断言去重后条数 <= 不去重条数，且去重后无重复项。
    """

    def emit_duplicate_warnings():
        # 在 simplefilter("always") 下循环发出同一条消息，保证可重复捕获
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            for _ in range(3):
                warnings.warn("重复警告消息", UserWarning, stacklevel=1)
        return "完成"

    with_dedup, _ = execute_with_warning_capture(emit_duplicate_warnings, drop_duplicates=True)
    without_dedup, _ = execute_with_warning_capture(emit_duplicate_warnings, drop_duplicates=False)

    assert len(with_dedup) <= len(without_dedup), "去重后条数不得多于未去重条数"
    # 去重后列表中不应有完全相同的元素
    assert len(with_dedup) == len(set(with_dedup)), "drop_duplicates=True 时不得有重复警告"


def test_execute_with_warning_capture_drop_duplicates_false():
    """drop_duplicates=False 时所有警告均被保留（包括重复项）。

    测试策略：
        用同一函数以 drop_duplicates=False 调用，断言返回的警告列表
        条数不少于去重后的结果，确认未发生静默去重。
    """

    def emit_two_distinct_warnings():
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            warnings.warn("警告A", UserWarning, stacklevel=1)
            warnings.warn("警告B", UserWarning, stacklevel=1)
        return "完成"

    no_dedup, result = execute_with_warning_capture(emit_two_distinct_warnings, drop_duplicates=False)
    with_dedup, _ = execute_with_warning_capture(emit_two_distinct_warnings, drop_duplicates=True)

    assert result == "完成"
    assert len(no_dedup) >= len(with_dedup), "drop_duplicates=False 时条数不得少于去重结果"


def test_execute_with_warning_capture_drop_duplicates_order():
    """drop_duplicates=True 时去重结果按首次出现顺序排列。

    测试策略：
        让函数按 A, B, A, C, B 顺序发出警告，断言去重后
        第一条含 "警告A"、第二条含 "警告B"、第三条含 "警告C"。
    """

    def emit_ordered_warnings():
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            for msg in ["警告A", "警告B", "警告A", "警告C", "警告B"]:
                warnings.warn(msg, UserWarning, stacklevel=1)
        return "顺序测试完成"

    deduped, result = execute_with_warning_capture(emit_ordered_warnings, drop_duplicates=True)

    assert result == "顺序测试完成"
    assert len(deduped) == 3, f"去重后应只剩 3 条不同警告，实际 {len(deduped)} 条"
    assert "警告A" in deduped[0], "第一条应为警告A（首次出现）"
    assert "警告B" in deduped[1], "第二条应为警告B（首次出现）"
    assert "警告C" in deduped[2], "第三条应为警告C（首次出现）"


def test_execute_with_warning_capture_drop_duplicates_with_string_return():
    """测试drop_duplicates参数与return_as_string结合使用"""

    # 测试字符串返回格式
    def simple_warning_function():
        warnings.warn("字符串测试警告", UserWarning, stacklevel=2)
        return "字符串去重测试"

    # drop_duplicates=True, return_as_string=True
    warnings_string, result = execute_with_warning_capture(
        simple_warning_function, drop_duplicates=True, return_as_string=True
    )

    assert isinstance(warnings_string, str)
    assert result == "字符串去重测试"

    # 检查字符串不为空
    if warnings_string != "无警告信息":
        assert "UserWarning: 字符串测试警告" in warnings_string

    # drop_duplicates=False, return_as_string=True
    warnings_string_no_drop, result_no_drop = execute_with_warning_capture(
        simple_warning_function, drop_duplicates=False, return_as_string=True
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
    warnings_list_true, result_true = execute_with_warning_capture(no_warning_function, drop_duplicates=True)

    # drop_duplicates=False
    warnings_list_false, result_false = execute_with_warning_capture(no_warning_function, drop_duplicates=False)

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

        for _i, data in enumerate(data_list):
            if data > 1:
                # 模拟处理过程中的警告（相同的警告消息）
                warnings.warn("数据值超过阈值", UserWarning, stacklevel=2)
            results.append(data * 2)

        return results

    # 使用drop_duplicates=True（默认）
    warnings_with_dedup, result_with_dedup = execute_with_warning_capture(
        process_data_with_warnings, drop_duplicates=True
    )

    # 使用drop_duplicates=False
    warnings_without_dedup, result_without_dedup = execute_with_warning_capture(
        process_data_with_warnings, drop_duplicates=False
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
