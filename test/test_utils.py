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
    from czsc.utils.features import find_most_similarity

    # 创建一个向量和一个矩阵
    vector = pd.Series(np.random.rand(10))
    matrix = pd.DataFrame(np.random.rand(10, 100))

    # 调用函数
    result = find_most_similarity(vector, matrix, n=5, metric="cosine")

    # 检查结果的类型
    assert isinstance(result, pd.Series)

    # 检查结果的长度im
    assert len(result) == 5

    # 检查结果的索引
    assert all(isinstance(index, int) for index in result.index)

    # 检查结果的值
    assert all(0 <= value <= 1 for value in result.values)


def test_overlap():
    from czsc.utils import overlap

    # 创建一个测试 DataFrame
    df = pd.DataFrame(
        {
            "dt": pd.date_range(start="1/1/2022", periods=5),
            "symbol": ["AAPL", "AAPL", "AAPL", "AAPL", "AAPL"],
            "col": [1, 1, 2, 2, 1],
        }
    )

    # 调用 overlap 函数
    result = overlap(df, "col")

    # 验证结果
    assert result["col_overlap"].tolist() == [1, 2, 1, 2, 1]


def test_timeout_decorator_success():
    @timeout_decorator(2)
    def fast_function():
        time.sleep(1)
        return "Completed"

    assert fast_function() == "Completed"


def test_timeout_decorator_timeout():
    @timeout_decorator(1)
    def slow_function():
        time.sleep(5)
        return "Completed"

    assert slow_function() is None
