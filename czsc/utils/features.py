"""
Feature processing helpers kept for the current retained utility surface.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_feature(df, x_col, method="standard", **kwargs):
    """Normalize a cross-sectional factor column by date."""
    from sklearn.preprocessing import minmax_scale, normalize, robust_scale, scale

    df = df.copy()
    assert df[x_col].isna().sum() == 0, f"factor has missing values: {df[x_col].isna().sum()}"
    q = kwargs.pop("q", 0.05)

    def _norm(x):
        x = x.clip(lower=x.quantile(q), upper=x.quantile(1 - q))
        if method == "minmax":
            return minmax_scale(x, **kwargs)
        if method == "robust":
            return robust_scale(x, **kwargs)
        if method.startswith("norm"):
            norm_type = method.split("-")[1] if "-" in method else "l2"
            return normalize(x.values.reshape(1, -1), norm=norm_type).flatten()
        if method == "standard":
            return scale(x, **kwargs)
        raise ValueError(f"unsupported normalize method: {method}")

    df[x_col] = df.groupby("dt")[x_col].transform(_norm)
    return df


def normalize_ts_feature(df, x_col, n=10, **kwargs):
    """Normalize a time-series factor into rolling quantile buckets."""
    assert df[x_col].nunique() > n * 2, "factor must have enough unique values for bucketing"
    assert df[x_col].isna().sum() == 0, f"factor has missing values: {df[x_col].isna().sum()}"
    min_periods = kwargs.get("min_periods", 300)

    if df.loc[df[x_col].isin([float("inf"), float("-inf")]), x_col].shape[0] > 0:
        raise ValueError(f"{x_col} contains inf or -inf")

    if f"{x_col}_qcut" not in df.columns:
        df[f"{x_col}_qcut"] = (
            df[x_col]
            .rolling(min_periods=min_periods, window=min_periods)
            .apply(lambda x: pd.qcut(x, q=n, labels=False, duplicates="drop", retbins=False).values[-1], raw=False)
        )
        df[f"{x_col}_qcut"] = df[f"{x_col}_qcut"].fillna(-1)
        df[f"{x_col}分层"] = df[f"{x_col}_qcut"].apply(lambda x: f"第{str(int(x + 1)).zfill(2)}层")

    return df


def feature_cross_layering(df, x_col, **kwargs):
    """Bucket cross-sectional factor values by date."""
    n = kwargs.get("n", 10)
    assert "dt" in df.columns, "factor data must contain dt"
    assert "symbol" in df.columns, "factor data must contain symbol"
    assert x_col in df.columns, f"factor data must contain {x_col}"
    assert df["symbol"].nunique() > n, "symbol count must be greater than layer count"

    if df[x_col].nunique() > n:

        def _layering(x):
            return pd.qcut(x, q=n, labels=False, duplicates="drop")

        df[f"{x_col}分层"] = df.groupby("dt")[x_col].transform(_layering)
    else:
        sorted_x = sorted(df[x_col].unique())
        df[f"{x_col}分层"] = df[x_col].apply(lambda x: sorted_x.index(x))

    df[f"{x_col}分层"] = df[f"{x_col}分层"].fillna(-1)
    df[f"{x_col}分层"] = df[f"{x_col}分层"].apply(lambda x: f"第{str(int(x + 1)).zfill(2)}层")
    return df


def find_most_similarity(vector: pd.Series, matrix: pd.DataFrame, n: int = 10, metric: str = "cosine", **kwargs):
    """Find the most similar columns in a matrix to the given vector."""
    del kwargs

    vec = pd.to_numeric(pd.Series(vector), errors="coerce")
    data = matrix.apply(pd.to_numeric, errors="coerce")

    if len(vec) != len(data.index):
        raise ValueError("vector length must match matrix row count")

    if metric == "corr":
        scores = data.corrwith(vec)
    elif metric == "cosine":
        vec_values = vec.fillna(0.0).to_numpy(dtype=float)
        vec_norm = np.linalg.norm(vec_values)
        if vec_norm == 0:
            scores = pd.Series(0.0, index=data.columns, dtype=float)
        else:
            filled = data.fillna(0.0)
            scores = filled.apply(
                lambda col: float(np.dot(col.to_numpy(dtype=float), vec_values) / (np.linalg.norm(col.to_numpy(dtype=float)) * vec_norm))
                if np.linalg.norm(col.to_numpy(dtype=float)) > 0
                else 0.0
            )
    else:
        raise ValueError(f"unsupported metric: {metric}")

    scores = scores.fillna(-1.0).sort_values(ascending=False)
    return scores.head(n)
