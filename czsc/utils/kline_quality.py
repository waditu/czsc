"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/4/27 15:01
describe: K线质量评估工具函数
"""

import pandas as pd
import numpy as np


# 1. 缺失值检查
def check_missing_values(df):
    """
    检查各列是否存在缺失值，并返回有缺失值的行。

    :param df: 单个 symbol 的 DataFrame
    :return: {'description': ..., 'rows': ...} 或 {'description': '无缺失值', 'rows': None}
    """
    missing = df[df.isnull().any(axis=1)]
    if not missing.empty:
        return {"description": f"存在 {len(missing)} 条记录包含缺失值", "rows": missing}
    else:
        return {"description": "无缺失值", "rows": None}


# 2. 数据类型检查
def check_data_types(df):
    """
    检查各列的数据类型是否符合预期，并返回类型不匹配的行。

    :param df: 单个 symbol 的 DataFrame
    :return: {'description': ..., 'rows': ...} 或 {'description': '数据类型均符合预期', 'rows': None}
    """
    expected_types = {
        "dt": "datetime64[ns]",
        "symbol": "object",
        "open": "float",
        "close": "float",
        "high": "float",
        "low": "float",
        "vol": "int64",
        "amount": "float",
    }
    type_mismatches = {}
    mismatch_rows = pd.DataFrame()

    for column, expected in expected_types.items():
        if column not in df.columns:
            type_mismatches[column] = f"缺少列 {column}"
            continue
        actual_type = df[column].dtype
        if expected.startswith("datetime"):
            if not pd.api.types.is_datetime64_any_dtype(df[column]):
                type_mismatches[column] = f"期望类型 {expected}，但实际类型 {actual_type}"
                mismatch_rows = pd.concat(
                    [mismatch_rows, df[df[column].apply(lambda x: not pd.api.types.is_datetime64_any_dtype([x]))]],
                    ignore_index=True,
                )
        elif expected.startswith("float"):
            if not pd.api.types.is_float_dtype(df[column]):
                type_mismatches[column] = f"期望类型 {expected}，但实际类型 {actual_type}"
                mismatch_rows = pd.concat(
                    [mismatch_rows, df[df[column].apply(lambda x: not isinstance(x, float))]], ignore_index=True
                )
        elif expected.startswith("int"):
            if not pd.api.types.is_integer_dtype(df[column]):
                type_mismatches[column] = f"期望类型 {expected}，但实际类型 {actual_type}"
                mismatch_rows = pd.concat(
                    [mismatch_rows, df[df[column].apply(lambda x: not isinstance(x, (int, np.integer)))]],
                    ignore_index=True,
                )
        else:
            if df[column].dtype != expected:
                type_mismatches[column] = f"期望类型 {expected}，但实际类型 {actual_type}"
                mismatch_rows = pd.concat(
                    [mismatch_rows, df[df[column].apply(lambda x: not isinstance(x, str))]], ignore_index=True
                )

    if type_mismatches:
        # 去重，避免同一行多次添加
        mismatch_rows = mismatch_rows.drop_duplicates()
        return {"description": type_mismatches, "rows": mismatch_rows}
    else:
        return {"description": "数据类型均符合预期", "rows": None}


# 3. 日期时间顺序检查
def check_datetime_order(df):
    """
    检查日期时间是否按升序排列，以及是否存在重复的日期时间，并返回相关的有问题的行。

    :param df: 单个 symbol 的 DataFrame
    :return: {'description': ..., 'rows': ...} 字典
    """
    results = {}
    problem_rows = pd.DataFrame()

    # 检查是否按升序排列
    dt_sorted = df["dt"].is_monotonic_increasing
    if not dt_sorted:
        results["dt_order"] = "日期时间未按升序排列"
        # 标记不按顺序的行
        sorted_df = df.sort_values("dt").reset_index(drop=True)
        mismatched = df[df["dt"] != sorted_df["dt"]]
        problem_rows = pd.concat([problem_rows, mismatched], ignore_index=True)
    else:
        results["dt_order"] = "日期时间按升序排列"

    # 检查重复的日期时间
    duplicate_dt = df.duplicated(subset=["dt"]).sum()
    if duplicate_dt > 0:
        results["duplicate_dt"] = f"存在 {duplicate_dt} 个重复的日期时间"
        duplicates = df[df.duplicated(subset=["dt"], keep=False)]
        problem_rows = pd.concat([problem_rows, duplicates], ignore_index=True)
    else:
        results["duplicate_dt"] = "无重复的日期时间"

    if not problem_rows.empty:
        # 去重
        problem_rows = problem_rows.drop_duplicates()
        return {"description": results, "rows": problem_rows}
    else:
        return {"description": results, "rows": None}


# 4. 价格合理性检查
def check_price_reasonableness(df):
    """
    检查价格数据的合理性，并返回有问题的行。

    :param df: 单个 symbol 的 DataFrame
    :return: {'description': ..., 'rows': ...} 或 {'description': '所有价格数据合理', 'rows': None}
    """
    issues = {}
    problem_rows = pd.DataFrame()

    # high >= open, close
    invalid_high = df[df["high"] < df[["open", "close"]].max(axis=1)]
    if not invalid_high.empty:
        issues["high_less_than_open_close"] = f"存在 {len(invalid_high)} 条记录，'high' 小于 'open' 或 'close'"
        problem_rows = pd.concat([problem_rows, invalid_high], ignore_index=True)

    # low <= open, close
    invalid_low = df[df["low"] > df[["open", "close"]].min(axis=1)]
    if not invalid_low.empty:
        issues["low_greater_than_open_close"] = f"存在 {len(invalid_low)} 条记录，'low' 大于 'open' 或 'close'"
        problem_rows = pd.concat([problem_rows, invalid_low], ignore_index=True)

    # 价格不为负，且不为零
    negative_prices = df[(df[["open", "close", "high", "low"]] <= 0).any(axis=1)]
    if not negative_prices.empty:
        issues["negative_prices"] = f"存在 {len(negative_prices)} 条记录，价格为负数或零"
        problem_rows = pd.concat([problem_rows, negative_prices], ignore_index=True)

    if issues:
        # 去重
        problem_rows = problem_rows.drop_duplicates()
        return {"description": issues, "rows": problem_rows}
    else:
        return {"description": "所有价格数据合理", "rows": None}


# 5. 成交量和金额检查
def check_volume_amount(df):
    """
    检查成交量和金额的数据合理性，并返回有问题的行。

    :param df: 单个 symbol 的 DataFrame
    :return: {'description': ..., 'rows': ...} 或 {'description': '成交量和金额数据合理', 'rows': None}
    """
    issues = {}
    problem_rows = pd.DataFrame()

    # vol 和 amount 非负
    negative_vol = df[df["vol"] < 0]
    if not negative_vol.empty:
        issues["negative_vol"] = f"存在 {len(negative_vol)} 条记录，'vol' 为负数"
        problem_rows = pd.concat([problem_rows, negative_vol], ignore_index=True)

    negative_amount = df[df["amount"] < 0]
    if not negative_amount.empty:
        issues["negative_amount"] = f"存在 {len(negative_amount)} 条记录，'amount' 为负数"
        problem_rows = pd.concat([problem_rows, negative_amount], ignore_index=True)

    # vol 为零时 amount 也应为零
    zero_vol_nonzero_amount = df[(df["vol"] == 0) & (df["amount"] != 0)]
    if not zero_vol_nonzero_amount.empty:
        issues["zero_vol_nonzero_amount"] = f"存在 {len(zero_vol_nonzero_amount)} 条记录，'vol' 为零但 'amount' 不为零"
        problem_rows = pd.concat([problem_rows, zero_vol_nonzero_amount], ignore_index=True)

    if issues:
        # 去重
        problem_rows = problem_rows.drop_duplicates()
        return {"description": issues, "rows": problem_rows}
    else:
        return {"description": "成交量和金额数据合理", "rows": None}


# 6. 符号一致性检查
def check_symbol_consistency(df):
    """
    检查符号数据的一致性和有效性，并返回有问题的行。

    :param df: 单个 symbol 的 DataFrame
    :return: {'description': ..., 'rows': ...} 或 {'description': '符号数据一致且有效', 'rows': None}
    """
    # 检查符号是否为非空字符串
    invalid_symbols = df[df["symbol"].isnull() | (df["symbol"].astype(str).str.strip() == "")]
    if not invalid_symbols.empty:
        return {"description": f"存在 {len(invalid_symbols)} 条记录，符号为空或无效", "rows": invalid_symbols}
    else:
        return {"description": "符号数据一致且有效", "rows": None}


# 7. 重复记录检查
def check_duplicate_records(df):
    """
    检查是否存在完全重复的记录，并返回重复的行。

    :param df: 单个 symbol 的 DataFrame
    :return: {'description': ..., 'rows': ...} 或 {'description': '无重复记录', 'rows': None}
    """
    duplicate_records = df[df.duplicated()]
    if not duplicate_records.empty:
        return {"description": f"存在 {len(duplicate_records)} 条完全重复的记录", "rows": duplicate_records}
    else:
        return {"description": "无重复记录", "rows": None}


# 8. 异常值检查
def check_extreme_values(df, threshold=0.2):
    """
    检查价格日涨跌幅是否超过指定阈值，作为异常值，并返回有问题的行。

    :param df: 单个 symbol 的 DataFrame
    :param threshold: 涨跌幅阈值，默认为 50%
    :return: {'description': ..., 'rows': ...} 或 {'description': '无异常的价格涨跌幅', 'rows': None}
    """
    if "close" not in df.columns:
        return {"description": "缺少 'close' 列，无法进行异常值检查", "rows": None}

    df = df.copy()
    df["pct_change"] = df["close"].pct_change().abs()
    extreme_changes = df[df["pct_change"] > threshold]
    if not extreme_changes.empty:
        return {
            "description": f"存在 {len(extreme_changes)} 条记录，价格涨跌幅超过 {threshold*100}%",
            "rows": extreme_changes,
        }
    else:
        return {"description": "无异常的价格涨跌幅", "rows": None}


# 主检查函数
def check_kline_quality(df):
    """
    检查包含多个 symbol 的 K 线数据的质量问题，并返回有问题的行。

    :param df: 包含 K 线数据的 DataFrame，必须包含以下列:
               ['dt', 'symbol', 'open', 'close', 'high', 'low', 'vol', 'amount']
    :return: 嵌套字典，按 symbol 组织的检查结果，包含问题描述和有问题的行
    """
    required_columns = ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"输入数据缺少必要的列: {missing_columns}")

    # 确保 'dt' 列为 datetime 类型
    if not pd.api.types.is_datetime64_any_dtype(df["dt"]):
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")

    # 按 symbol 分组
    grouped = df.groupby("symbol")

    quality_issues = {}

    for symbol, group in grouped:
        symbol_issues = {}

        # 按日期排序
        group_sorted = group.sort_values("dt").reset_index(drop=True)

        # 逐个检查
        symbol_issues["missing_values"] = check_missing_values(group_sorted)
        symbol_issues["type_mismatches"] = check_data_types(group_sorted)
        symbol_issues["datetime_order"] = check_datetime_order(group_sorted)
        symbol_issues["price_reasonableness"] = check_price_reasonableness(group_sorted)
        symbol_issues["volume_amount"] = check_volume_amount(group_sorted)
        symbol_issues["symbol_consistency"] = check_symbol_consistency(group_sorted)
        symbol_issues["duplicate_records"] = check_duplicate_records(group_sorted)
        symbol_issues["extreme_values"] = check_extreme_values(group_sorted)

        quality_issues[symbol] = symbol_issues

    # 输出检查结果
    for symbol, symbol_issues in quality_issues.items():
        for check, result in symbol_issues.items():

            if result["rows"] is not None:
                print(f"\n检查点: {symbol} - {check}")
                print(f"结果描述: {result['description']}")

                print("有问题的数据行:")
                print(result["rows"])
                print("\n\n")

    return quality_issues
