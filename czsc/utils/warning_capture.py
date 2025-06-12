"""
Warning信息捕获工具函数
"""
import warnings
from contextlib import contextmanager
from typing import Callable, Any, Tuple, List, Union
from loguru import logger


@contextmanager
def capture_warnings():
    """
    捕获代码执行过程中的warning信息的上下文管理器
    
    Returns:
        Tuple[List[str], Any]: (警告信息列表, 代码执行结果)
    
    Usage:
        with capture_warnings() as warning_capture:
            # 执行可能产生warning的代码
            result = some_function()
        
        warnings_list = warning_capture.get_warnings()
        result = warning_capture.get_result()
    """
    warnings_list = []
    result_container: dict[str, Any] = {"result": None, "exception": None}
    
    def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
        warning_msg = f"{category.__name__}: {message} (文件: {filename}, 行号: {lineno})"
        warnings_list.append(warning_msg)
        logger.warning(f"捕获到警告: {warning_msg}")
    
    # 保存原始的warning处理器
    original_showwarning = warnings.showwarning
    
    try:
        # 设置自定义warning处理器
        warnings.showwarning = custom_warning_handler
        
        class WarningCapture:
            def get_warnings(self) -> List[str]:
                return warnings_list.copy()
            
            def get_result(self) -> Any:
                if result_container["exception"] is not None:
                    raise result_container["exception"]
                return result_container["result"]
            
            def set_result(self, result: Any):
                result_container["result"] = result
            
            def set_exception(self, exception: Exception):
                result_container["exception"] = exception
        
        yield WarningCapture()
        
    finally:
        # 恢复原始的warning处理器
        warnings.showwarning = original_showwarning


def execute_with_warning_capture(
    func: Callable, 
    *args, 
    return_as_string: bool = False,
    drop_duplicates: bool = True,
    **kwargs
) -> Union[Tuple[List[str], Any], Tuple[str, Any]]:
    """
    执行函数并捕获过程中的warning信息
    
    Args:
        func: 要执行的函数
        *args: 函数的位置参数
        return_as_string: 是否以字符串格式返回警告信息，默认False返回列表
        drop_duplicates: 是否删除重复的警告信息，默认True
        **kwargs: 函数的关键字参数
    
    Returns:
        Union[Tuple[List[str], Any], Tuple[str, Any]]: 
        - 当return_as_string=False时: (警告信息列表, 函数执行结果)
        - 当return_as_string=True时: (警告信息字符串, 函数执行结果)
    
    Example:
        def test_func():
            warnings.warn("这是一个测试警告")
            return "执行完成"
        
        # 返回列表格式
        warnings_list, result = execute_with_warning_capture(test_func)
        print(f"警告信息: {warnings_list}")
        print(f"执行结果: {result}")
        
        # 返回字符串格式
        warnings_string, result = execute_with_warning_capture(test_func, return_as_string=True)
        print(f"警告信息: {warnings_string}")
        print(f"执行结果: {result}")
    """
    with capture_warnings() as warning_capture:
        try:
            result = func(*args, **kwargs)
            warning_capture.set_result(result)
        except Exception as e:
            warning_capture.set_exception(e)
            logger.error(f"函数执行出错: {e}")
            raise
    
    warnings_list = warning_capture.get_warnings()
    result = warning_capture.get_result()
    
    if drop_duplicates:
        warnings_list = list(dict.fromkeys(warnings_list))

    if return_as_string:
        warnings_string = "\n".join(warnings_list) if warnings_list else "无警告信息"
        logger.info(f"捕获到 {len(warnings_list)} 条警告信息")
        return warnings_string, result
    else:
        return warnings_list, result 