"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2024/4/27 15:01
describe: K线质量评估工具函数

https://hailuoai.com/?chat=241699282914746375
"""

import pandas as pd


def check_high_low(df):
    """
    检查是否存在 high < low 的情况。
    """
    df["high_low_error"] = df["high"] < df["low"]
    error_rate = df["high_low_error"].mean()
    error_klines = df[df["high_low_error"]].copy()
    return error_rate, error_klines


def check_price_gap(df, **kwargs):
    """
    检查是否存在超过阈值的大幅度缺口。
    """
    df = df.copy().sort_values(["dt", "symbol"]).reset_index(drop=True)
    errors = []
    for symbol in df["symbol"].unique():
        symbol_df = df[df["symbol"] == symbol]
        symbol_df["last_close"] = symbol_df["close"].shift(1)
        symbol_df["price_gap"] = (symbol_df["open"] - symbol_df["last_close"]).abs()
        gap_th = symbol_df["price_gap"].mean() + 3 * symbol_df["price_gap"].std()
        error_ = symbol_df[symbol_df["price_gap"] > gap_th].copy()
        if len(error_) > 0:
            errors.append(error_)

    error_klines = pd.concat(errors)
    error_rate = len(error_klines) / len(df)
    return error_rate, error_klines


def check_abnormal_volume(df, **kwargs):
    """
    检查是否存在异常成交量。
    """
    df = df.copy().sort_values(["dt", "symbol"]).reset_index(drop=True)
    errors = []
    for symbol in df["symbol"].unique():
        symbol_df = df[df["symbol"] == symbol]
        volume_threshold = symbol_df["vol"].mean() + 3 * symbol_df["vol"].std()
        error_ = symbol_df[symbol_df["vol"] > volume_threshold].copy()
        if len(error_) > 0:
            errors.append(error_)
    error_klines = pd.concat(errors)
    error_rate = len(error_klines) / len(df)
    return error_rate, error_klines


def check_zero_volume(df):
    """
    计算零成交量的K线占比。
    """
    df = df.copy().sort_values(["dt", "symbol"]).reset_index(drop=True)
    error_rate = df["vol"].eq(0).sum() / len(df)
    error_klines = df[df["vol"].eq(0)].copy()
    return error_rate, error_klines
