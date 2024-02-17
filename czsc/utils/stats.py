# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/19 23:27
describe: 绩效表现统计
"""
import numpy as np
import pandas as pd
from collections import Counter


def cal_break_even_point(seq) -> float:
    """计算单笔收益序列的盈亏平衡点

    :param seq: 单笔收益序列，数据样例：[0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01]
    :return: 盈亏平衡点
    """
    if sum(seq) < 0:
        return 1.0
    seq = np.cumsum(sorted(seq))                # type: ignore
    return (np.sum(seq < 0) + 1) / len(seq)     # type: ignore


def subtract_fee(df, fee=1):
    """依据单品种持仓信号扣除手续费

    函数执行逻辑：

    1. 首先，函数对输入的df进行检查，确保其包含所需的列：'dt'（日期时间）和'pos'（持仓）。同时，检查'pos'列的值是否符合要求，即只能是0、1或-1。
    2. 如果df中不包含'n1b'（名义收益率）列，函数会根据'price'列计算'n1b'列。
    3. 然后，函数为输入的DataFrame df添加一个新列'date'，该列包含交易日期（从'dt'列中提取）。
    4. 接下来，函数根据持仓（'pos'）和名义收益率（'n1b'）计算'edge_pre_fee'（手续费前收益）和'edge_post_fee'（手续费后收益）两列。
    5. 函数根据持仓信号计算开仓和平仓的位置。
        开仓位置（open_pos）是持仓信号发生变化的位置（即，当前持仓与前一个持仓不同），并且当前持仓不为0。
        平仓位置（exit_pos）是持仓信号发生变化的位置（即，当前持仓与前一个持仓不同），并且前一个持仓不为0。
    6. 根据手续费规则，开仓时在第一个持仓K线上扣除手续费，平仓时在最后一个持仓K线上扣除手续费。
       函数通过将'edge_post_fee'列的值在开仓和平仓位置上分别减去手续费（fee）来实现这一逻辑。
    7. 最后，函数返回修改后的DataFrame df。

    :param df: 包含dt、pos、price、n1b列的DataFrame
    :param fee: 手续费，单位：BP
    :return: 修改后的DataFrame
    """
    assert 'dt' in df.columns, 'dt 列必须存在'
    assert 'pos' in df.columns, 'pos 列必须存在'
    assert all(x in [0, 1, -1] for x in df['pos'].unique()), "pos 列的值必须是 0, 1, -1 中的一个"

    if 'n1b' not in df.columns:
        assert 'price' in df.columns, '当n1b列不存在时，price 列必须存在'
        df['n1b'] = (df['price'].shift(-1) / df['price'] - 1) * 10000

    df['date'] = df['dt'].dt.date
    df['edge_pre_fee'] = df['pos'] * df['n1b']
    df['edge_post_fee'] = df['pos'] * df['n1b']

    # 扣费规则, 开仓扣费在第一个持仓K线上，平仓扣费在最后一个持仓K线上
    open_pos = (df['pos'].shift() != df['pos']) & (df['pos'] != 0)
    exit_pos = (df['pos'].shift(-1) != df['pos']) & (df['pos'] != 0)
    df.loc[open_pos, 'edge_post_fee'] = df.loc[open_pos, 'edge_post_fee'] - fee
    df.loc[exit_pos, 'edge_post_fee'] = df.loc[exit_pos, 'edge_post_fee'] - fee
    return df


def daily_performance(daily_returns):
    """采用单利计算日收益数据的各项指标

    函数计算逻辑：

    1. 首先，将传入的日收益率数据转换为NumPy数组，并指定数据类型为float64。
    2. 然后，进行一系列判断：如果日收益率数据为空或标准差为零或全部为零，则返回一个字典，其中所有指标的值都为零。
    3. 如果日收益率数据满足要求，则进行具体的指标计算：

        - 年化收益率 = 日收益率列表的和 / 日收益率列表的长度 * 252
        - 夏普比率 = 日收益率的均值 / 日收益率的标准差 * 标准差的根号252
        - 最大回撤 = 累计日收益率的最高累积值 - 累计日收益率
        - 卡玛比率 = 年化收益率 / 最大回撤（如果最大回撤不为零，则除以最大回撤；否则为10）
        - 日胜率 = 大于零的日收益率的个数 / 日收益率的总个数
        - 年化波动率 = 日收益率的标准差 * 标准差的根号252
        - 非零覆盖 = 非零的日收益率个数 / 日收益率的总个数

    4. 将所有指标的值存储在一个字典中，其中键为指标名称，值为相应的计算结果。

    :param daily_returns: 日收益率数据，样例：
        [0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01]
    :return: dict
    """
    daily_returns = np.array(daily_returns, dtype=np.float64)

    if len(daily_returns) == 0 or np.std(daily_returns) == 0 or all(x == 0 for x in daily_returns):
        return {"绝对收益": 0, "年化": 0, "夏普": 0, "最大回撤": 0, "卡玛": 0, "日胜率": 0,
                "年化波动率": 0, "非零覆盖": 0, "盈亏平衡点": 0, "新高间隔": 0, "新高占比": 0}

    annual_returns = np.sum(daily_returns) / len(daily_returns) * 252
    sharpe_ratio = np.mean(daily_returns) / np.std(daily_returns) * np.sqrt(252)
    cum_returns = np.cumsum(daily_returns)
    dd = np.maximum.accumulate(cum_returns) - cum_returns
    max_drawdown = np.max(dd)
    kama = annual_returns / max_drawdown if max_drawdown != 0 else 10
    win_pct = len(daily_returns[daily_returns >= 0]) / len(daily_returns)
    annual_volatility = np.std(daily_returns) * np.sqrt(252)
    none_zero_cover = len(daily_returns[daily_returns != 0]) / len(daily_returns)

    # 计算最大新高间隔
    max_interval = Counter(np.maximum.accumulate(cum_returns).tolist()).most_common(1)[0][1]

    # 计算新高时间占比
    high_pct = len([i for i, x in enumerate(dd) if x == 0]) / len(dd)

    def __min_max(x, min_val, max_val, digits=4):
        if x < min_val:
            x1 = min_val
        elif x > max_val:
            x1 = max_val
        else:
            x1 = x
        return round(x1, digits)

    sta = {
        "绝对收益": round(np.sum(daily_returns), 4),
        "年化": round(annual_returns, 4),
        "夏普": __min_max(sharpe_ratio, -5, 5, 2),
        "最大回撤": round(max_drawdown, 4),
        "卡玛": __min_max(kama, -10, 10, 2),
        "日胜率": round(win_pct, 4),
        "年化波动率": round(annual_volatility, 4),
        "非零覆盖": round(none_zero_cover, 4),
        "盈亏平衡点": round(cal_break_even_point(daily_returns), 4),
        "新高间隔": max_interval,
        "新高占比": round(high_pct, 4),
    }
    return sta


def weekly_performance(weekly_returns):
    """采用单利计算周收益数据的各项指标

    :param weekly_returns: 周收益率数据，样例：
        [0.01, 0.02, -0.01, 0.03, 0.02, -0.02, 0.01, -0.01, 0.02, 0.01]
    :return: dict
    """
    weekly_returns = np.array(weekly_returns, dtype=np.float64)

    if len(weekly_returns) == 0 or np.std(weekly_returns) == 0 or all(x == 0 for x in weekly_returns):
        return {"年化": 0, "夏普": 0, "最大回撤": 0, "卡玛": 0, "周胜率": 0,
                "年化波动率": 0, "非零覆盖": 0, "盈亏平衡点": 0, "新高间隔": 0, "新高占比": 0}

    annual_returns = np.sum(weekly_returns) / len(weekly_returns) * 52
    sharpe_ratio = np.mean(weekly_returns) / np.std(weekly_returns) * np.sqrt(52)
    cum_returns = np.cumsum(weekly_returns)
    dd = np.maximum.accumulate(cum_returns) - cum_returns
    max_drawdown = np.max(dd)
    kama = annual_returns / max_drawdown if max_drawdown != 0 else 10
    win_pct = len(weekly_returns[weekly_returns >= 0]) / len(weekly_returns)
    annual_volatility = np.std(weekly_returns) * np.sqrt(52)
    none_zero_cover = len(weekly_returns[weekly_returns != 0]) / len(weekly_returns)

    # 计算最大新高间隔
    high_index = [i for i, x in enumerate(dd) if x == 0]
    max_interval = 0
    for i in range(len(high_index) - 1):
        max_interval = max(max_interval, high_index[i + 1] - high_index[i])

    # 计算新高时间占比
    high_pct = len(high_index) / len(dd)

    def __min_max(x, min_val, max_val, digits=4):
        if x < min_val:
            x1 = min_val
        elif x > max_val:
            x1 = max_val
        else:
            x1 = x
        return round(x1, digits)

    sta = {
        "年化": round(annual_returns, 4),
        "夏普": __min_max(sharpe_ratio, -5, 5, 2),
        "最大回撤": round(max_drawdown, 4),
        "卡玛": __min_max(kama, -10, 10, 2),
        "周胜率": round(win_pct, 4),
        "年化波动率": round(annual_volatility, 4),
        "非零覆盖": round(none_zero_cover, 4),
        "盈亏平衡点": round(cal_break_even_point(weekly_returns), 4),
        "新高间隔": max_interval,
        "时间占比": round(high_pct, 4),
    }
    return sta


def net_value_stats(nv: pd.DataFrame, exclude_zero: bool = False, sub_cost=True) -> dict:
    """统计净值曲线的年化收益、夏普等

    :param nv: 净值数据，格式如下：

                           dt  edge  cost
        0 2017-01-03 09:30:00   0.0   0.0
        1 2017-01-03 10:00:00   0.0   0.0
        2 2017-01-03 10:30:00   0.0   0.0
        3 2017-01-03 11:00:00   0.0   0.0
        4 2017-01-03 13:00:00   0.0   0.0

        列说明：
        dt: 交易时间
        edge: 单利收益，单位：BP
        cost: 交易成本，单位：BP；可选列，如果没有成本列，则默认为0

    :param exclude_zero: 是否排除收益为0的情况，一般认为收益为0的情况是没有持仓的
    :param sub_cost: 是否扣除成本
    :return:
    """
    nv = nv.copy(deep=True)
    nv['dt'] = pd.to_datetime(nv['dt'])

    if sub_cost:
        assert 'cost' in nv.columns, "成本列cost不存在"
        nv['edge'] = nv['edge'] - nv['cost']
    else:
        if 'cost' not in nv.columns:
            nv['cost'] = 0

    if exclude_zero:
        nv = nv[(nv['edge'] != 0) | (nv['cost'] != 0)]

    # 按日期聚合
    nv['date'] = nv['dt'].apply(lambda x: x.date())
    df_nav = nv.groupby('date')['edge'].sum() / 10000
    df_nav = df_nav.cumsum()

    if all(x == 0 for x in nv['edge']):
        # 处理没有持仓记录的情况
        sharp = 0
        y_ret = 0
        calmar = 0
        mdd = 0
    else:
        # y_ret = yearly return
        N = 252
        y_ret = df_nav.iloc[-1] * (N / len(df_nav))
        if df_nav.diff().std() != 0:
            sharp = df_nav.diff().mean() / df_nav.diff().std() * pow(N, 0.5)
        else:
            sharp = 0
        df0 = df_nav.shift(1).ffill().fillna(0)
        mdd = (1 - (df0 + 1) / (df0 + 1).cummax()).max()
        calmar = y_ret / mdd if mdd != 0 else 1

    prefix = "有持仓时间" if exclude_zero else ""
    res = {"夏普": round(sharp, 2), "卡玛": round(calmar, 2), "年化": round(y_ret, 4), "最大回撤": round(mdd, 4)}
    res = {f"{prefix}{k}": v for k, v in res.items()}

    if not exclude_zero:
        res['持仓覆盖'] = round(len(nv[(nv['edge'] != 0) | (nv['cost'] != 0)]) / len(nv), 4) if len(nv) > 0 else 0
    return res


def evaluate_pairs(pairs: pd.DataFrame, trade_dir: str = "多空") -> dict:
    """评估开平交易记录的表现

    :param pairs: 开平交易记录，数据样例如下：

        ==========  ==========  ===================  ===================  ==========  ==========  ===========  ============  ==========  ==========
        标的代码     交易方向     开仓时间              平仓时间              开仓价格    平仓价格     持仓K线数    事件序列        持仓天数     盈亏比例
        ==========  ==========  ===================  ===================  ==========  ==========  ===========  ============  ==========  ==========
        DLi9001     多头        2019-02-25 21:36:00  2019-02-25 21:51:00     1147.8      1150.72           16  开多 -> 平多           0       25.47
        DLi9001     多头        2021-09-15 14:06:00  2021-09-15 14:09:00     3155.88     3153.61            4  开多 -> 平多           0       -7.22
        DLi9001     多头        2019-08-29 21:01:00  2019-08-29 22:54:00     1445.86     1454.55          114  开多 -> 平多           0       60.09
        DLi9001     多头        2021-10-11 21:46:00  2021-10-11 22:11:00     3631.77     3622.66           26  开多 -> 平多           0      -25.08
        DLi9001     多头        2020-05-13 09:16:00  2020-05-13 09:26:00     1913.13     1917.64           11  开多 -> 平多           0       23.55
        ==========  ==========  ===================  ===================  ==========  ==========  ===========  ============  ==========  ==========

    :param trade_dir: 交易方向，可选值 ['多头', '空头', '多空']
    :return: 交易表现
    """
    from czsc.objects import cal_break_even_point
    assert trade_dir in ["多头", "空头", "多空"], "trade_dir 参数错误，可选值 ['多头', '空头', '多空']"

    pairs = pairs.copy()

    p = {
        "交易方向": trade_dir,
        "交易次数": 0,
        "累计收益": 0,
        "单笔收益": 0,
        "盈利次数": 0,
        "累计盈利": 0,
        "单笔盈利": 0,
        "亏损次数": 0,
        "累计亏损": 0,
        "单笔亏损": 0,
        "交易胜率": 0,
        "累计盈亏比": 0,
        "单笔盈亏比": 0,
        "盈亏平衡点": 1,
        "持仓天数": 0,
        "持仓K线数": 0,
    }

    if trade_dir in ["多头", "空头"]:
        pairs = pairs[pairs["交易方向"] == trade_dir]

    if len(pairs) == 0:
        return p

    pairs = pairs.to_dict(orient='records')
    p['交易次数'] = len(pairs)
    p["盈亏平衡点"] = round(cal_break_even_point([x['盈亏比例'] for x in pairs]), 4)
    p["累计收益"] = round(sum([x["盈亏比例"] for x in pairs]), 2)
    p["单笔收益"] = round(p["累计收益"] / p["交易次数"], 2)
    p["持仓天数"] = round(sum([x["持仓天数"] for x in pairs]) / len(pairs), 2)
    p["持仓K线数"] = round(sum([x["持仓K线数"] for x in pairs]) / len(pairs), 2)

    win_ = [x for x in pairs if x["盈亏比例"] >= 0]
    if len(win_) > 0:
        p["盈利次数"] = len(win_)
        p["累计盈利"] = sum([x["盈亏比例"] for x in win_])
        p["单笔盈利"] = round(p["累计盈利"] / p["盈利次数"], 4)
        p["交易胜率"] = round(p["盈利次数"] / p["交易次数"], 4)

    loss_ = [x for x in pairs if x["盈亏比例"] < 0]
    if len(loss_) > 0:
        p["亏损次数"] = len(loss_)
        p["累计亏损"] = sum([x["盈亏比例"] for x in loss_])
        p["单笔亏损"] = round(p["累计亏损"] / p["亏损次数"], 4)

        p["累计盈亏比"] = round(p["累计盈利"] / abs(p["累计亏损"]), 4)
        p["单笔盈亏比"] = round(p["单笔盈利"] / abs(p["单笔亏损"]), 4)

    return p
