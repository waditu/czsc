# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/16 20:31
describe: czsc.utils 单元测试
"""
import sys
import pytest
import time
import pandas as pd
import numpy as np
from czsc import utils
from czsc.utils import timeout_decorator


def test_x_round():
    assert utils.x_round(100, 3) == 100
    assert utils.x_round(1.000342, 3) == 1.0
    assert utils.x_round(1.000342, 4) == 1.0003
    assert utils.x_round(1.000342, 5) == 1.00034


def test_fernet():
    from czsc.utils.fernet import generate_fernet_key, fernet_encrypt, fernet_decrypt

    key = generate_fernet_key()
    text = {"account": "admin", "password": "123456"}
    encrypted = fernet_encrypt(text, key)
    decrypted = fernet_decrypt(encrypted, key, is_dict=True)
    assert text == decrypted, f"{text} != {decrypted}"


def test_find_most_similarity():
    """测试相似度查找功能"""
    from czsc.utils.features import find_most_similarity

    # 使用固定种子创建确定性的测试数据
    np.random.seed(42)
    vector = pd.Series(np.random.rand(10))
    matrix = pd.DataFrame(np.random.rand(10, 100))

    result = find_most_similarity(vector, matrix, n=5, metric="cosine")

    assert isinstance(result, pd.Series), "结果应该是pandas Series"
    assert len(result) == 5, "结果长度应该是5"
    assert all(isinstance(index, int) for index in result.index), "索引应该都是整数"
    assert all(0 <= value <= 1 for value in result.values), "相似度值应该在0-1之间"


def test_overlap():
    """测试重叠检测功能"""
    from czsc.utils import overlap

    df = pd.DataFrame(
        {
            "dt": pd.date_range(start="1/1/2022", periods=5),
            "symbol": ["AAPL", "AAPL", "AAPL", "AAPL", "AAPL"],
            "col": [1, 1, 2, 2, 1],
        }
    )

    result = overlap(df, "col")

    assert result["col_overlap"].tolist() == [1, 2, 1, 2, 1], "重叠检测结果不正确"


def test_timeout_decorator_success():
    """测试超时装饰器正常情况"""
    @timeout_decorator(2)
    def fast_function():
        time.sleep(1)
        return "Completed"

    assert fast_function() == "Completed", "快速函数应该正常返回结果"


def test_timeout_decorator_timeout():
    """测试超时装饰器超时情况"""
    @timeout_decorator(1)
    def slow_function():
        time.sleep(5)
        return "Completed"

    assert slow_function() is None, "慢函数应该超时返回None"
