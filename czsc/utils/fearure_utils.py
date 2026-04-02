# 工具函数
import numpy as np
import pandas as pd
from loguru import logger


def is_event_feature(df, col, **kwargs):
    """事件类因子的判断函数

    事件因子的特征：多头事件发生时，因子值为1；空头事件发生时，因子值为-1；其他情况，因子值为0。

    :param df: DataFrame
    :param col: str, 因子字段名称
    """
    unique_values = df[col].unique()
    return all(x in [0, 1, -1] for x in unique_values)


def feature_returns(df, factor, target="n1b", **kwargs):
    """计算因子特征截面收益率

    :param df: pd.DataFrame, 必须包含 dt、symbol、factor, target 列
    :param factor: str, 因子列名
    :param target: str, 预测目标收益率列名
    :param kwargs:

        - fit_intercept: bool, 是否拟合截距项，默认为 False

    :return: pd.DataFrame, 新增 returns 列
    """
    from sklearn.linear_model import LinearRegression

    df = df.copy()
    fit_intercept = kwargs.get("fit_intercept", False)

    ret = []
    for dt, dfg in df.groupby("dt"):
        dfg = dfg.copy().dropna(subset=[factor, target])
        if dfg.empty or len(dfg) < 5:
            ret.append([dt, 0])
            logger.warning(f"{dt} has no enough data, only {len(dfg)} rows")
            continue

        x = dfg[factor].values.reshape(-1, 1)
        y = dfg[target].values.reshape(-1, 1)
        model = LinearRegression(fit_intercept=fit_intercept).fit(x, y)
        ret.append([dt, model.coef_[0][0]])

    dft = pd.DataFrame(ret, columns=["dt", "returns"])
    return dft


def feature_sectional_corr(df, factor, target="n1b", method="pearson", **kwargs):
    """计算因子特征截面相关性（IC）

    :param df：数据，DateFrame格式
    :param factor：因子列名，一般采用F#开头的列
    :param target：目标列名，一般为n1b
    :param method：{'pearson', 'kendall', 'spearman'} or callable

            * pearson : standard correlation coefficient
            * kendall : Kendall Tau correlation coefficient
            * spearman : Spearman rank correlation
            * callable: callable with input two 1d ndarrays and returning a float

    :return：df，res: 前者是每日相关系数结果，后者是每日相关系数的统计结果
    """
    from czsc.utils import single_linear

    df = df.copy()
    corr = []
    for dt, dfg in df.groupby("dt"):
        dfg = dfg.copy().dropna(subset=[factor, target])

        if dfg.empty or len(dfg) < 5:
            corr.append([dt, 0])
            logger.warning(f"{dt} has no enough data, only {len(dfg)} rows")
        else:
            c = dfg[factor].corr(dfg[target], method=method)
            corr.append([dt, c])

    dft = pd.DataFrame(corr, columns=["dt", "corr"])

    res = {
        "factor": factor,
        "target": target,
        "method": method,
        "IC均值": 0,
        "IC标准差": 0,
        "ICIR": 0,
        "IC胜率": 0,
        "累计IC回归R2": 0,
        "累计IC回归斜率": 0,
    }
    if dft.empty:
        return dft, res

    dft = dft[~dft["ic"].isnull()].copy()
    ic_avg = dft["ic"].mean()
    ic_std = dft["ic"].std()

    res["IC均值"] = round(ic_avg, 4)
    res["IC标准差"] = round(ic_std, 4)
    res["ICIR"] = round(ic_avg / ic_std, 4) if ic_std != 0 else 0
    if ic_avg > 0:
        res["IC胜率"] = round(len(dft[dft["ic"] > 0]) / len(dft), 4)
    else:
        res["IC胜率"] = round(len(dft[dft["ic"] < 0]) / len(dft), 4)

    lr_ = single_linear(y=dft["ic"].cumsum().to_list())
    res.update({"累计IC回归R2": lr_["r2"], "累计IC回归斜率": lr_["slope"]})
    return dft, res
