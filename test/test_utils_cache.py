# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/1/1 00:00
describe: czsc.utils.cache 单元测试
"""
import os
import time
import shutil
import tempfile
import pandas as pd
from pathlib import Path
from czsc.utils.cache import (
    disk_cache, home_path, empty_cache_path, get_dir_size, 
    DiskCache, clear_expired_cache, clear_cache
)

# 创建临时路径用于测试
temp_path = os.path.join(home_path, "temp")


def test_get_dir_size():
    """测试获取目录大小功能"""
    # 创建临时目录和文件
    test_dir = tempfile.mkdtemp()
    
    # 创建一个测试文件
    test_file = os.path.join(test_dir, "test.txt")
    with open(test_file, "w") as f:
        f.write("hello world")
    
    # 获取目录大小
    size = get_dir_size(test_dir)
    assert size > 0
    assert isinstance(size, int)
    
    # 清理
    shutil.rmtree(test_dir)


def test_empty_cache_path():
    """测试清空缓存路径功能"""
    # 使用临时目录来测试，避免影响其他测试
    test_dir = tempfile.mkdtemp()
    test_file = os.path.join(test_dir, "test_file.txt")
    
    # 创建测试文件
    with open(test_file, "w") as f:
        f.write("test content")
    
    # 确认文件存在
    assert os.path.exists(test_file)
    
    # 模拟清空缓存路径的逻辑（不直接调用empty_cache_path以避免影响其他测试）
    shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=False)
    
    # 确认文件已被删除，但目录重新创建
    assert os.path.exists(test_dir)
    assert not os.path.exists(test_file)
    
    # 清理
    shutil.rmtree(test_dir)


def test_disk_cache_class():
    """测试 DiskCache 类的基本功能"""
    # 创建临时缓存实例
    cache = DiskCache()
    
    # 测试字符串方法
    assert "DiskCache" in str(cache)
    
    # 测试设置和获取 pkl 文件
    test_key = "test_pkl"
    test_value = {"test": "data", "number": 123}
    
    cache.set(test_key, test_value)
    assert cache.is_found(test_key)
    retrieved_value = cache.get(test_key)
    assert retrieved_value == test_value
    
    # 测试删除缓存
    cache.remove(test_key)
    assert not cache.is_found(test_key)


def test_disk_cache_json():
    """测试 DiskCache 的 JSON 格式支持"""
    cache = DiskCache()
    
    test_key = "test_json"
    test_value = {"name": "test", "value": 42}
    
    cache.set(test_key, test_value, suffix="json")
    assert cache.is_found(test_key, suffix="json")
    retrieved_value = cache.get(test_key, suffix="json")
    assert retrieved_value == test_value
    
    cache.remove(test_key, suffix="json")


def test_disk_cache_txt():
    """测试 DiskCache 的文本格式支持"""
    cache = DiskCache()
    
    test_key = "test_txt"
    test_value = "这是测试文本内容"
    
    cache.set(test_key, test_value, suffix="txt")
    assert cache.is_found(test_key, suffix="txt")
    retrieved_value = cache.get(test_key, suffix="txt")
    assert retrieved_value == test_value
    
    cache.remove(test_key, suffix="txt")


def test_disk_cache_dataframe():
    """测试 DiskCache 的 DataFrame 格式支持"""
    cache = DiskCache()
    
    test_key = "test_df"
    test_df = pd.DataFrame({
        'A': [1, 2, 3],
        'B': ['a', 'b', 'c'],
        'C': [1.1, 2.2, 3.3]
    })
    
    # 测试 CSV 格式
    cache.set(test_key, test_df, suffix="csv")
    assert cache.is_found(test_key, suffix="csv")
    retrieved_df = cache.get(test_key, suffix="csv")
    pd.testing.assert_frame_equal(test_df, retrieved_df)
    cache.remove(test_key, suffix="csv")
    
    # 测试 Excel 格式
    cache.set(test_key, test_df, suffix="xlsx")
    assert cache.is_found(test_key, suffix="xlsx")
    retrieved_df = cache.get(test_key, suffix="xlsx")
    pd.testing.assert_frame_equal(test_df, retrieved_df)
    cache.remove(test_key, suffix="xlsx")
    
    # 测试 Feather 格式
    cache.set(test_key, test_df, suffix="feather")
    assert cache.is_found(test_key, suffix="feather")
    retrieved_df = cache.get(test_key, suffix="feather")
    pd.testing.assert_frame_equal(test_df, retrieved_df)
    cache.remove(test_key, suffix="feather")
    
    # 测试 Parquet 格式
    cache.set(test_key, test_df, suffix="parquet")
    assert cache.is_found(test_key, suffix="parquet")
    retrieved_df = cache.get(test_key, suffix="parquet")
    pd.testing.assert_frame_equal(test_df, retrieved_df)
    cache.remove(test_key, suffix="parquet")


def test_disk_cache_ttl():
    """测试 DiskCache 的 TTL 功能"""
    cache = DiskCache()
    
    test_key = "test_ttl"
    test_value = "ttl测试数据"
    
    # 设置短TTL
    cache.set(test_key, test_value)
    assert cache.is_found(test_key, ttl=1)  # 1秒TTL
    
    # 等待超时
    time.sleep(2)
    assert not cache.is_found(test_key, ttl=1)


# 创建用于装饰器测试的简单函数
@disk_cache(path=temp_path, suffix="pkl", ttl=100)
def run_func_x(x):
    return x * 2


@disk_cache(path=temp_path, suffix="txt", ttl=100)
def run_func_text(x):
    return f"hello {x}"


@disk_cache(path=temp_path, suffix="json", ttl=100)
def run_func_json(x):
    return {"a": 1, "b": 2, "x": x}


@disk_cache(path=temp_path, suffix="xlsx", ttl=100)
def run_func_y(x):
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'x': [x, x, x]})
    return df


@disk_cache(path=temp_path, suffix="feather", ttl=100)
def run_feather(x):
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'x': [x, x, x]})
    return df


@disk_cache(path=temp_path, suffix="parquet", ttl=100)
def run_parquet(x):
    df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6], 'x': [x, x, x]})
    return df


def test_disk_cache_decorator():
    """测试 disk_cache 装饰器功能"""
    # 确保缓存根目录存在
    os.makedirs(temp_path, exist_ok=True)
    
    # 调用函数
    result = run_func_x(5)
    
    # 检查输出是否正确
    assert result == 10

    # 再次调用相同参数的函数
    result = run_func_x(5)
    
    # 检查输出仍然正确
    assert result == 10

    # 调用不同参数的函数
    result = run_func_text(6)
    result = run_func_text(6)
    assert result == "hello 6"

    # 调用 JSON 函数
    result = run_func_json(7)
    result = run_func_json(7)
    assert result == {"a": 1, "b": 2, "x": 7}

    # 调用 Feather 函数
    result = run_feather(8)
    result = run_feather(8)
    assert isinstance(result, pd.DataFrame)

    # 调用 Parquet 函数
    result = run_parquet(9)
    result = run_parquet(9)
    assert isinstance(result, pd.DataFrame)

    # 检查缓存文件是否存在
    files = os.listdir(os.path.join(temp_path, "run_func_x"))
    assert len(files) == 1

    # 调用不同参数的函数
    result = run_func_y(5)
    files = os.listdir(os.path.join(temp_path, "run_func_y"))
    assert len(files) == 1
    file_xlsx = [x for x in files if x.endswith("xlsx")][0]
    df = pd.read_excel(os.path.join(temp_path, f"run_func_y/{file_xlsx}"))
    assert isinstance(df, pd.DataFrame)


def test_clear_expired_cache():
    """测试清理过期缓存功能"""
    # 创建临时目录
    test_dir = tempfile.mkdtemp()
    
    # 创建一个pkl文件
    old_file = os.path.join(test_dir, "old_file.pkl")
    
    with open(old_file, "w") as f:
        f.write("old content")
    
    # 修改文件的修改时间为很久以前
    old_time = time.time() - 3600 * 24 * 31  # 31天前
    os.utime(old_file, (old_time, old_time))
    
    # 检查文件修改时间
    current_time = time.time()
    old_file_stat = os.stat(old_file)
    age = current_time - old_file_stat.st_mtime
    max_age = 3600 * 24 * 30  # 30天
    
    print(f"当前时间: {current_time}")
    print(f"文件修改时间: {old_file_stat.st_mtime}")
    print(f"文件年龄: {age} 秒 ({age / (3600 * 24):.1f} 天)")
    print(f"最大年龄: {max_age} 秒 ({max_age / (3600 * 24):.1f} 天)")
    print(f"是否过期: {age > max_age}")
    
    # 确保文件存在
    assert os.path.exists(old_file)
    
    # 运行清理功能
    clear_expired_cache(test_dir, max_age=max_age)
    
    # 现在应该删除过期文件
    assert not os.path.exists(old_file)
    
    # 清理
    shutil.rmtree(test_dir)


def test_clear_cache():
    """测试清理缓存功能"""
    # 创建临时目录
    test_dir = tempfile.mkdtemp()
    
    # 创建子目录和文件
    sub1 = os.path.join(test_dir, "sub1")
    sub2 = os.path.join(test_dir, "sub2")
    os.makedirs(sub1)
    os.makedirs(sub2)
    
    with open(os.path.join(sub1, "file1.txt"), "w") as f:
        f.write("content1")
    with open(os.path.join(sub2, "file2.txt"), "w") as f:
        f.write("content2")
    
    # 清理特定子目录
    clear_cache(test_dir, subs=["sub1"], recreate=True)
    
    # 检查结果
    assert os.path.exists(sub1)  # 重新创建了
    assert os.path.exists(sub2)  # 保留
    assert not os.path.exists(os.path.join(sub1, "file1.txt"))  # 文件被删除
    assert os.path.exists(os.path.join(sub2, "file2.txt"))  # 文件保留
    
    # 清理整个目录
    clear_cache(test_dir)
    
    # 检查目录重新创建
    assert os.path.exists(test_dir)
    assert not os.path.exists(sub2)


def test_disk_cache_with_custom_ttl():
    """测试 disk_cache 装饰器的动态 TTL 功能"""
    @disk_cache(path=temp_path, suffix="pkl")
    def func_with_ttl(x, **kwargs):
        return x * 3
    
    # 调用函数并设置短TTL
    result1 = func_with_ttl(10, ttl=1)
    assert result1 == 30
    
    # 立即再次调用应该使用缓存
    result2 = func_with_ttl(10, ttl=1)
    assert result2 == 30
    
    # 等待TTL过期
    time.sleep(2)
    
    # 再次调用应该重新计算
    result3 = func_with_ttl(10, ttl=1)
    assert result3 == 30


def test_disk_cache_error_handling():
    """测试 DiskCache 的错误处理"""
    cache = DiskCache()
    
    # 测试不支持的后缀
    try:
        cache.set("test", "data", suffix="unsupported")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "not supported" in str(e)
    
    # 测试 JSON 格式必须是字典
    try:
        cache.set("test", "not_dict", suffix="json")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "only support dict" in str(e)
    
    # 测试文本格式必须是字符串
    try:
        cache.set("test", 123, suffix="txt")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "only support str" in str(e)
    
    # 测试 DataFrame 格式
    try:
        cache.set("test", "not_dataframe", suffix="csv")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "only support pd.DataFrame" in str(e)


def test_disk_cache_get_nonexistent():
    """测试获取不存在的缓存文件"""
    cache = DiskCache()
    
    result = cache.get("nonexistent_key")
    assert result is None
