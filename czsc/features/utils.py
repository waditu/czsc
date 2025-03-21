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
    return all([x in [0, 1, -1] for x in unique_values])


def rolling_corr(df, col1, col2, window=300, min_periods=100, **kwargs):
    """滚动计算两个序列的相关系数

    :param df: pd.DataFrame
    :param col1: str
    :param col2: str
    :param window: int, default 300, 滚动窗口大小, None表示扩展窗口
    :param min_periods: int, default 100, 最小观测数量, 用于计算相关系数的最小观测数量
    """
    if kwargs.get("copy", False):
        df = df.copy()

    assert isinstance(df, pd.DataFrame), "df must be pd.DataFrame"
    assert col1 in df.columns, f"{col1} not in df.columns"
    assert col2 in df.columns, f"{col2} not in df.columns"

    new_col = kwargs.get("new_col", f"{col1}_corr_{col2}")
    assert min_periods < window, "min_periods must be less than window"
    df[new_col] = df[col1].rolling(window=window, min_periods=min_periods).corr(df[col2]).fillna(0)
    return df


def rolling_rank(df: pd.DataFrame, col, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动排名

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_rank' 作为新列名
    """
    if kwargs.get("copy", False):
        df = df.copy()

    min_periods = kwargs.get("min_periods", 2)
    new_col = new_col if new_col else f"{col}_rank"
    df[new_col] = df[col].rolling(window=window, min_periods=min_periods).rank(pct=True)
    df[new_col] = df[new_col].fillna(0)
    return df


def rolling_norm(df: pd.DataFrame, col, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动归一化值

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_norm' 作为新列名
    """
    if kwargs.get("copy", False):
        df = df.copy()

    min_periods = kwargs.get("min_periods", 2)
    new_col = new_col if new_col else f"{col}_norm"
    df[new_col] = (
        df[col].rolling(window=window, min_periods=min_periods).apply(lambda x: (x[-1] - x.mean()) / x.std(), raw=True)
    )
    df[new_col] = df[new_col].fillna(0)
    return df


def rolling_qcut(df: pd.DataFrame, col, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动分位数

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_qcut' 作为新列名
    """
    if kwargs.get("copy", False):
        df = df.copy()

    q = kwargs.get("q", 10)
    min_periods = kwargs.get("min_periods", q)
    new_col = new_col if new_col else f"{col}_qcut"

    def __qcut_func(x):
        return pd.qcut(x, q=q, labels=False, duplicates="drop")[-1]

    df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(__qcut_func, raw=True)
    df[new_col] = df[new_col].fillna(-1)
    return df


def rolling_compare(df, col1, col2, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动归一化值

    :param df: pd.DataFrame
        待计算的数据
    :param col1: str
        第一个列名
    :param col2: str
        第二个列名
    :param window: int
        滚动窗口大小, 默认为300
    :param new_col: str
        新列名，默认为 None, 表示使用 f'{col}_norm' 作为新列名
    :param kwargs:
        min_periods: int
            最小计算周期
    """
    from sklearn.linear_model import LinearRegression

    window = kwargs.get("window", 300)
    min_periods = kwargs.get("min_periods", 2)
    new_col = new_col if new_col else f"compare_{col1}_{col2}"
    method = kwargs.get("method", "sub")
    assert method in [
        "sub",
        "divide",
        "lr_intercept",
        "lr_coef",
    ], "method 必须为 sub, divide, lr_intercept, lr_coef 中的一种"

    for i in range(len(df)):
        dfi = df.loc[i - window + 1 : i, [col1, col2]]
        dfi = dfi.copy()
        if i < min_periods:
            df.loc[i, new_col] = 0
            continue

        if method == "sub":
            df.loc[i, new_col] = dfi[col1].sub(dfi[col2]).mean()

        elif method == "divide":
            df.loc[i, new_col] = dfi[col1].divide(dfi[col2]).mean()

        elif method == "lr_intercept":
            x = dfi[col2].values.reshape(-1, 1)
            y = dfi[col1].values.reshape(-1, 1)
            reg = LinearRegression().fit(x, y)
            df.loc[i, new_col] = reg.intercept_[0]

        elif method == "lr_coef":
            x = dfi[col2].values.reshape(-1, 1)
            y = dfi[col1].values.reshape(-1, 1)
            reg = LinearRegression().fit(x, y)
            df.loc[i, new_col] = reg.coef_[0][0]

        else:
            raise ValueError(f"method {method} not support")


def rolling_scale(df: pd.DataFrame, col: str, window=300, min_periods=100, new_col=None, **kwargs):
    """对序列进行滚动归一化

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_scale' 作为新列名
    """
    from sklearn.preprocessing import minmax_scale, scale, maxabs_scale, robust_scale

    if kwargs.get("copy", False):
        df = df.copy()

    df = df.sort_values("dt", ascending=True).reset_index(drop=True)
    new_col = new_col if new_col else f"{col}_scale"

    method = kwargs.get("method", "scale")
    method_map = {
        "scale": scale,
        "minmax_scale": minmax_scale,
        "maxabs_scale": maxabs_scale,
        "robust_scale": robust_scale,
    }
    assert method in method_map, f"method must be one of {list(method_map.keys())}"
    scale_method = method_map[method]

    if method == "minmax_scale":
        df[new_col] = (
            df[col]
            .rolling(window=window, min_periods=min_periods)
            .apply(lambda x: minmax_scale(x, feature_range=(-1, 1))[-1])
        )
    else:
        df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(lambda x: scale_method(x)[-1])

    df[new_col] = df[new_col].fillna(0)
    return df


def rolling_tanh(df: pd.DataFrame, col: str, window=300, min_periods=100, new_col=None, **kwargs):
    """对序列进行滚动 tanh 变换

    双曲正切函数：https://baike.baidu.com/item/%E5%8F%8C%E6%9B%B2%E6%AD%A3%E5%88%87%E5%87%BD%E6%95%B0/15469414

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_scale' 作为新列名
    """
    from sklearn.preprocessing import scale
    
    if kwargs.get("copy", False):
        df = df.copy()
    new_col = new_col if new_col else f"{col}_tanh"
    df = df.sort_values("dt", ascending=True).reset_index(drop=True)
    df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(lambda x: np.tanh(scale(x))[-1])  # type: ignore
    df[new_col] = df[new_col].fillna(0)
    return df


def rolling_slope(df: pd.DataFrame, col: str, window=300, min_periods=100, new_col=None, **kwargs):
    """计算序列的滚动斜率

    大于0表示序列的斜率向上，小于0表示序列的斜率向下，绝对值越大表示斜率越陡峭

    :param df: pd.DataFrame, 待计算的数据
    :param col: str, 待计算的列
    :param window: int, 滚动窗口大小, 默认为300
    :param min_periods: int, 最小计算周期, 默认为100
    :param new_col: str, 新列名，默认为 None, 表示使用 f'{col}_slope' 作为新列名
    :param kwargs:

        - min_periods: int, 最小计算周期
        - method: str, 计算方法

            - linear: 使用线性回归计算斜率
            - std/mean: 使用序列的 std/mean 计算斜率
            - snr: 使用序列的 snr 计算斜率
    """
    from sklearn.linear_model import LinearRegression

    method = kwargs.get("method", "linear")
    new_col = new_col if new_col else f"{col}_slope_{method}"

    if method == "linear":
        # 使用线性回归计算斜率
        def __lr_slope(x):
            return LinearRegression().fit(list(range(len(x))), x).coef_[0]

        df[new_col] = df[col].rolling(window=window, min_periods=min_periods).apply(__lr_slope, raw=True)

    elif method == "std/mean":
        # 用 window 内 std 的变化率除以 mean 的变化率，来衡量序列的斜率
        # 如果 std/mean > 0, 则表示序列的斜率在变大，反之则表示序列的斜率在变小
        df["temp_std"] = df[col].rolling(window=window, min_periods=min_periods).std().pct_change(window)
        df["temp_mean"] = df[col].rolling(window=window, min_periods=min_periods).mean().pct_change(window)
        df[new_col] = np.where(df["temp_mean"] != 0, df["temp_std"] / df["temp_mean"], 0)
        # 加入变化率的正负号
        df[new_col] = df[new_col] * np.sign(df[col].pct_change(window))
        df.drop(["temp_std", "temp_mean"], axis=1, inplace=True)

    elif method == "snr":
        # 用 window 内的信噪比变化率来衡量序列的斜率
        df[new_col] = df[col].diff(window) / df[col].diff().abs().rolling(window=window, min_periods=min_periods).sum()

    else:
        raise ValueError(f"Unknown method: {method}")

    df[new_col] = df[new_col].fillna(0)
    return df


def normalize_corr(df: pd.DataFrame, fcol, ycol=None, **kwargs):
    """标准化因子与收益相关性为正数

    方法说明：对因子进行滚动相关系数计算，因子乘以滚动相关系数的符号

    **注意：**

    1. simple 模式下，计算过程有一定的未来信息泄露，在回测中使用时需要注意
    2. rolling 模式下，计算过程依赖 window 参数，有可能调整后相关性为负数

    :param df: pd.DataFrame, 必须包含 dt、symbol、price 列，以及因子列
    :param fcol: str 因子列名
    :param kwargs: dict

        - window: int, 滚动窗口大小
        - min_periods: int, 最小计算周期
        - mode: str, 计算方法, rolling 表示使用滚动调整相关系数，simple 表示使用镜像反转相关系数
        - copy: bool, 是否复制 df

    :return: pd.DataFrame
    """
    window = kwargs.get("window", 1000)
    min_periods = kwargs.get("min_periods", 5)
    mode = kwargs.get("mode", "rolling")
    if kwargs.get("copy", False):
        df = df.copy()

    df = df.sort_values(["symbol", "dt"], ascending=True).reset_index(drop=True)
    for symbol, dfg in df.groupby("symbol"):
        dfg["ycol"] = dfg["price"].pct_change().shift(-1)

        if mode.lower() == "rolling":
            dfg["corr_sign"] = np.sign(dfg[fcol].rolling(window=window, min_periods=min_periods).corr(dfg["ycol"]))
            dfg[fcol] = (dfg["corr_sign"].shift(3) * dfg[fcol]).fillna(0)

        elif mode.lower() == "simple":
            corr_sign = np.sign(dfg[fcol].corr(dfg["ycol"]))
            dfg[fcol] = corr_sign * dfg[fcol]

        else:
            raise ValueError(f"Unknown mode: {mode}")

        df.loc[df["symbol"] == symbol, fcol] = dfg[fcol]
    return df


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
