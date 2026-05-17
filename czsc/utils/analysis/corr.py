"""相关性分析工具。

历史上本模块还包含 ``nmi_matrix`` 与 ``single_linear``，在 2026-05-17 PR-A
中已删除：

- ``nmi_matrix`` 依赖 ``scikit-learn``，是 czsc 唯一的 sklearn 调用点，删除后
  整个项目不再依赖 sklearn。
- ``single_linear`` 仅被 :func:`cross_sectional_ic` 内部使用，已在本文件中
  内联为最小二乘公式，不再暴露为公共 API。

References:
1. https://zhuanlan.zhihu.com/p/362258222
2. https://blog.csdn.net/qq_45538220/article/details/107429201
"""

import numpy as np
import pandas as pd


def cross_sectional_ic(df, x_col="open", y_col="n1b", method="spearman", **kwargs):
    """分析 df 中 x_col 和 y_col 列的截面相关性（IC）

    :param df：数据，DateFrame格式
    :param x_col：X列
    :param y_col：Y列，一般采用下期收益，也就是 n1b
    :param method：{'pearson', 'kendall', 'spearman'} or callable
            * pearson : standard correlation coefficient
            * kendall : Kendall Tau correlation coefficient
            * spearman : Spearman rank correlation
            * callable: callable with input two 1d ndarrays and returning a float
    :return：df，res: 前者是每日相关系数结果，后者是每日相关系数的统计结果
    """
    from tqdm import tqdm

    dt_col = kwargs.pop("dt_col", "dt")
    tqdm.pandas(desc="cross_section_ic")
    s = df.groupby(dt_col).progress_apply(lambda row: row[x_col].corr(row[y_col], method=method))
    df = pd.DataFrame(s, columns=["ic"]).reset_index(inplace=False)

    res = {
        "x_col": x_col,
        "y_col": y_col,
        "method": method,
        "IC均值": 0,
        "IC标准差": 0,
        "ICIR": 0,
        "IC胜率": 0,
        "IC绝对值>2%占比": 0,
        "累计IC回归R2": 0,
        "累计IC回归斜率": 0,
        "月胜率": 0,
        "月均值": 0,
        "年胜率": 0,
        "年均值": 0,
    }
    if df.empty:
        return df, res

    df = df[~df["ic"].isnull()].copy()
    ic_avg = df["ic"].mean()
    ic_std = df["ic"].std()

    res["IC均值"] = round(ic_avg, 4)
    res["IC标准差"] = round(ic_std, 4)
    res["ICIR"] = round(ic_avg / ic_std, 4) if ic_std != 0 else 0
    if ic_avg > 0:
        res["IC胜率"] = round(len(df[df["ic"] > 0]) / len(df), 4)
    else:
        res["IC胜率"] = round(len(df[df["ic"] < 0]) / len(df), 4)

    res["IC绝对值>2%占比"] = round(len(df[df["ic"].abs() > 0.02]) / len(df), 4)

    # 累计 IC 的线性回归：用最小二乘公式直接算出 slope / R²。
    # 内联原 ``single_linear`` 的算术（含 ss_tot += 1e-5 的稳定化项），保持
    # 输出与旧版 byte-for-byte 一致；不再依赖被删除的公共 API。
    y_arr = df["ic"].cumsum().to_numpy(dtype=np.float64)
    n = len(y_arr)
    if n >= 2:
        x_arr = np.arange(n, dtype=np.float64)
        x_sum = float(x_arr.sum())
        y_sum = float(y_arr.sum())
        x_sq_sum = float((x_arr * x_arr).sum())
        xy_sum = float((x_arr * y_arr).sum())
        delta = n * x_sq_sum - x_sum * x_sum
        if delta != 0:
            slope = (n * xy_sum - x_sum * y_sum) / delta
            intercept = (x_sq_sum * y_sum - x_sum * xy_sum) / delta
            ss_tot = float(((y_arr - y_arr.mean()) ** 2).sum()) + 0.00001
            ss_err = float(((y_arr - slope * x_arr - intercept) ** 2).sum())
            r2 = 1.0 - ss_err / ss_tot
            res["累计IC回归R2"] = round(r2, 4)
            res["累计IC回归斜率"] = round(slope, 4)

    monthly_ic = df.groupby(df["dt"].dt.strftime("%Y年%m月"))["ic"].mean().to_dict()
    monthly_win_rate = len([1 for x in monthly_ic.values() if np.sign(x) == np.sign(res["IC均值"])]) / len(monthly_ic)
    res["月胜率"] = round(monthly_win_rate, 4)
    res["月均值"] = round(np.mean(list(monthly_ic.values())), 4)

    yearly_ic = df.groupby(df["dt"].dt.strftime("%Y年"))["ic"].mean().to_dict()
    yearly_win_rate = len([1 for x in yearly_ic.values() if np.sign(x) == np.sign(res["IC均值"])]) / len(yearly_ic)
    res["年胜率"] = round(yearly_win_rate, 4)
    res["年均值"] = round(np.mean(list(yearly_ic.values())), 4)

    return df, res
