# -*- coding: utf-8 -*-
"""
author: Napoleon
create_dt: 2024/03/13 12:14
describe: psi模型稳定性评估


"""
import numpy as np
import pandas as pd


def psi(df: pd.DataFrame, col, n=10, **kwargs):
    """PSI 群体稳定性指标，反映数据在不同分箱中的分布变化

    PSI = ∑(实际占比 - 基准占比) * ln(实际占比 / 基准占比)

    参考：https://zhuanlan.zhihu.com/p/79682292  风控模型—群体稳定性指标(PSI)深入理解应用

    :param df: 数据, 必须包含 dt 和 col 列
    :param col: 要计算的列
    :param n: 分箱数
    :param kwargs:

        - scale: 是否进行标准化
        - window: 滚动窗口
        - min_periods: 最小观测数
        - dt_pattern: 时间分组格式，默认 '%Y' 表示按年分组; '%Y-%m' 表示按月分组; 按季度分组 '%Y-%q'

    :return: pd.DataFrame
    """
    assert 'dt' in df.columns, '时间列必须为 dt'
    assert col in df.columns, f'数据中没有 {col} 列'
    df['dt'] = pd.to_datetime(df['dt'])
    dt_pattern = kwargs.get('dt_pattern', '%Y')
    df['key'] = df['dt'].dt.strftime(dt_pattern)

    if kwargs.get('scale', False):
        window = kwargs.get('window', 2000)
        min_periods = kwargs.get('min_periods', 100)

        df[col] = df[col].rolling(window=window, min_periods=min_periods).apply(
            lambda x: ((x - x.mean()) / x.std())[-1], raw=True).fillna(0)

    df['bin'] = pd.qcut(df[col], n)
    dfg = df.groupby(['bin', 'key'], observed=False).size().unstack().fillna(0).apply(lambda x: x / x.sum(), axis=0)
    dfg['PSI'] = dfg.diff(axis=1).abs().mean(axis=1)

    # base_col = dfg.columns[0]
    # for rate_col in dfg.columns[1:]:
    #     dfg[f"{col}_PSI"] = (dfg[rate_col] - dfg[base_col]) * np.log((dfg[rate_col] / dfg[base_col]))
    # psi_cols = [x for x in dfg.columns if x.endswith('_PSI')]
    # dfg['PSI'] = dfg[psi_cols].sum(axis=1)
    return dfg


if __name__ == '__main__':
    from czsc.connectors import research
    df = research.get_raw_bars('000001.SH', '日线', '20170101', '20230101', fq='前复权', raw_bars=False)

    dfs = psi(df, 'close', 10, dt_pattern='%Y', scale=True)
