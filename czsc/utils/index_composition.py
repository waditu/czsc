# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/10/13 15:01
describe: 因子（特征）处理
"""
import pandas as pd


def index_composition(klines, weights=None, base_point=1000, **kwagrs):
    """设置基点，按收益率加权合成指数

    输入：

    1. 成分标的K线行情
    2. 每个时刻的成分权重
    3. 基点

    过程：

    1. 计算成分标的每根K线的收益
    2. 在每个时刻，按成分权重对标的收益加权计算，得到每个时刻的指数涨跌幅
    3. 用基点和每个时刻的涨跌幅计算出每个时刻的指数价

    输出：指数K线行情

    :param klines: K线行情，样例如下：

        =========  ===================  =======  =======  =======  =======  ==========  ===========
        symbol     dt                      open    close     high      low         vol       amount
        =========  ===================  =======  =======  =======  =======  ==========  ===========
        000001.SH  2021-01-04 09:31:00  3473.82  3469.37  3474.33  3468.86  1041014208  13018854400
        000001.SH  2021-01-04 09:32:00  3470.18  3467.58  3471.95  3467.58   570367232   7721827328
        000001.SH  2021-01-04 09:33:00  3467.11  3466.98  3468.53  3466.94   660060480   8371049984
        000001.SH  2021-01-04 09:34:00  3466.83  3463.5   3466.83  3463.4    563931392   7435783168
        000001.SH  2021-01-04 09:35:00  3463.23  3460.33  3463.75  3460.33   504271904   6500695552
        =========  ===================  =======  =======  =======  =======  ==========  ===========

    :param weights: 权重调整记录；索引为dt，columns为成分权重，每个时间截面的权重之和可以不为1，样例如下：

        ===================  ===========  ===========  ===========  ===========
        dt                     000001.SH    000016.SH    000300.SH    000905.SH
        ===================  ===========  ===========  ===========  ===========
        2021-01-04 09:31:00     0.244275     0.236822     0.271415     0.204674
        2021-01-04 10:10:00     0.250273     0.140398     0.151955     0.294418
        2021-01-04 10:54:00     0.127531     0.123941     0.199969     0.19682
        ===================  ===========  ===========  ===========  ===========

        注意：权重调整记录的时间截面必须是K线行情的时间截面的子集，且必须包含K线行情的第一根K线的时间截面

    :param base_point: 基点，默认为1000
    :return: 指数K线行情，样例如下：

        ===================  ============  ========  ==========  ===========
        dt                        returns     price         vol       amount
        ===================  ============  ========  ==========  ===========
        2021-01-04 09:31:00   0            1000      2195268112  31725149952
        2021-01-04 09:32:00  -0.000230561   999.769  1187524832  18900989440
        2021-01-04 09:33:00  -0.000165153   999.604  1330775568  19418287360
        2021-01-04 09:34:00  -0.00103582    998.569  1133046300  17488768512
        2021-01-04 09:35:00  -0.00067244    997.897  1025222108  15351070080
        ===================  ============  ========  ==========  ===========
    """
    klines["dt"] = pd.to_datetime(klines["dt"])

    if 'returns' not in klines.columns.tolist():
        data = []
        for _, kline in klines.groupby("symbol"):
            kline = kline.sort_values("dt", ascending=True).reset_index(drop=True)
            kline["returns"] = kline["close"].pct_change()
            kline["returns"] = kline["returns"].fillna(0)
            data.append(kline)
        klines = pd.concat(data, ignore_index=True)

    returns = klines.pivot_table(index="dt", columns="symbol", values="returns")

    if weights is None:
        weights = returns.copy()
        weights[:] = 1 / len(returns.columns.tolist())
    else:
        weights['dt'] = pd.to_datetime(weights['dt'])
        assert weights['dt'].min() <= klines['dt'].min(), "权重调整记录的首个时刻必须小于等于成分K线首个时刻"
        weights.set_index("dt", inplace=True)
        weights = weights.reindex(returns.index, method="ffill", copy=True)

    index_ = (returns * weights).sum(axis=1).to_frame("returns")
    index_["price"] = base_point * (1 + index_["returns"]).cumprod()
    index_['vol'] = klines.groupby("dt")["vol"].sum()
    index_['amount'] = klines.groupby("dt")["amount"].sum()
    index_ = index_.reset_index()
    return index_
