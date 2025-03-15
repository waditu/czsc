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


# def test_subtract_fee():
#     from czsc.utils.stats import subtract_fee

#     # 构造测试数据
#     data = {
#         "dt": pd.date_range("2022-01-01", periods=20, freq="D"),
#         "pos": [0, 1, 1, -1, -1, -1, 0, 0, 1, 1, 1, 1, 1, 0, 0, -1, -1, 0, 1, 1],
#         "price": [10, 11, 12, 13, 14, 10, 11, 12, 13, 14, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
#     }
#     df = pd.DataFrame(data)

#     # 执行函数
#     df = subtract_fee(df, fee=100)

#     # 验证结果
#     assert int(df["edge_pre_fee"].sum()) == 2748
#     assert int(df["edge_post_fee"].sum()) == 1848

#     # 构造测试数据
#     data = {
#         "dt": pd.date_range("2022-01-01", periods=5, freq="D"),
#         "pos": [0, 1, 1, -1, 0],
#     }
#     df = pd.DataFrame(data)

#     # 执行函数并捕获异常
#     with pytest.raises(AssertionError):
#         subtract_fee(df, fee=1)

#     # 构造测试数据
#     data = {
#         "dt": pd.date_range("2022-01-01", periods=5, freq="D"),
#         "pos": [0, 1, 2, -1, 0],
#         "price": [10, 11, 12, 13, 14],
#     }
#     df = pd.DataFrame(data)

#     # 执行函数并捕获异常
#     with pytest.raises(AssertionError):
#         subtract_fee(df, fee=1)


def test_ranker():
    import numpy as np
    import pandas as pd
    from czsc.utils.cross import cross_sectional_ranker

    np.random.seed(42)
    dates = pd.date_range("2021-01-01", "2023-01-05")
    symbols = ["AAPL", "GOOG", "TSLA", "MSFT"]
    data = {"date": [], "symbol": [], "return": [], "factor1": [], "factor2": []}
    for date in dates:
        returns = np.random.randn(len(symbols))
        ranks = np.argsort(returns) + 1
        for ticker, rank in zip(symbols, ranks):
            data["date"].append(date)
            data["symbol"].append(ticker)
            data["return"].append(rank)  # 'return' 现在代表了每天的收益率排名
            data["factor1"].append(np.random.randn())
            data["factor2"].append(np.random.randn())
    df = pd.DataFrame(data)
    df["dt"] = df["date"]

    x_cols = ["factor1", "factor2"]
    y_col = "return"

    dfp = cross_sectional_ranker(df, x_cols, y_col)
    assert dfp["rank"].max() == len(symbols)
    assert dfp["rank"].min() == 1
    assert dfp["rank"].mean() == 2.5


# def test_daily_performance():
#     from czsc.utils.stats import daily_performance

#     # Test case 1: empty daily returns
#     result = daily_performance([])
#     assert result == {
#         "绝对收益": 0,
#         "年化": 0,
#         "夏普": 0,
#         "最大回撤": 0,
#         "卡玛": 0,
#         "日胜率": 0,
#         "日盈亏比": 0,
#         "日赢面": 0,
#         "年化波动率": 0,
#         "下行波动率": 0,
#         "非零覆盖": 0,
#         "盈亏平衡点": 0,
#         "新高间隔": 0,
#         "新高占比": 0,
#         "回撤风险": 0,
#     }

#     # Test case 2: daily returns with zero standard deviation
#     result = daily_performance([1, 1, 1, 1, 1])
#     assert result == {
#         "绝对收益": 0,
#         "年化": 0,
#         "夏普": 0,
#         "最大回撤": 0,
#         "卡玛": 0,
#         "日胜率": 0,
#         "日盈亏比": 0,
#         "日赢面": 0,
#         "年化波动率": 0,
#         "下行波动率": 0,
#         "非零覆盖": 0,
#         "盈亏平衡点": 0,
#         "新高间隔": 0,
#         "新高占比": 0,
#         "回撤风险": 0,
#     }

#     # Test case 3: daily returns with all zeros
#     result = daily_performance([0, 0, 0, 0, 0])
#     assert result == {
#         "绝对收益": 0,
#         "年化": 0,
#         "夏普": 0,
#         "最大回撤": 0,
#         "卡玛": 0,
#         "日胜率": 0,
#         "日盈亏比": 0,
#         "日赢面": 0,
#         "年化波动率": 0,
#         "下行波动率": 0,
#         "非零覆盖": 0,
#         "盈亏平衡点": 0,
#         "新高间隔": 0,
#         "新高占比": 0,
#         "回撤风险": 0,
#     }

#     # Test case 4: normal daily returns
#     daily_returns = np.array([0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01])
#     result = daily_performance(daily_returns)
#     assert result == {
#         "绝对收益": 0.08,
#         "年化": 2.016,
#         "夏普": 5,
#         "最大回撤": 0.02,
#         "卡玛": 10,
#         "日胜率": 0.7,
#         "日盈亏比": 1.2857,
#         "日赢面": 0.6,
#         "年化波动率": 0.2439,
#         "下行波动率": 0.0748,
#         "非零覆盖": 1.0,
#         "盈亏平衡点": 0.7,
#         "新高间隔": 5,
#         "新高占比": 0.6,
#         "回撤风险": 0.082,
#     }

#     # Test case 5: normal daily returns with different input type
#     result = daily_performance([0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01])
#     assert result == {
#         "绝对收益": 0.08,
#         "年化": 2.016,
#         "夏普": 5,
#         "最大回撤": 0.02,
#         "卡玛": 10,
#         "日胜率": 0.7,
#         "日盈亏比": 1.2857,
#         "日赢面": 0.6,
#         "年化波动率": 0.2439,
#         "下行波动率": 0.0748,
#         "非零覆盖": 1.0,
#         "盈亏平衡点": 0.7,
#         "新高间隔": 5,
#         "新高占比": 0.6,
#         "回撤风险": 0.082,
#     }


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
