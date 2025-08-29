"""
回测相关的可视化组件

包含权重分布、权重回测、持仓回测、止损分析等回测功能
"""

import numpy as np
import pandas as pd
import streamlit as st
from loguru import logger
from .base import safe_import_weight_backtest, safe_import_daily_performance


def show_weight_distribution(dfw, abs_weight=True, **kwargs):
    """展示权重分布

    :param dfw: pd.DataFrame, 包含 symbol, dt, price, weight 列
    :param abs_weight: bool, 是否取权重的绝对值
    :param kwargs:
        - percentiles: list, 分位数
    """
    dfw = dfw.copy()
    if abs_weight:
        dfw["weight"] = dfw["weight"].abs()

    default_percentiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    percentiles = kwargs.get("percentiles", default_percentiles)

    dfs = dfw.groupby("symbol").apply(lambda x: x["weight"].describe(percentiles=percentiles)).reset_index()

    # 使用 show_df_describe 来显示结果
    from .statistics import show_df_describe

    show_df_describe(dfs)


def show_weight_backtest(dfw, **kwargs):
    """展示权重回测结果

    :param dfw: 回测数据，任何字段都不允许有空值；数据样例：
        ===================  ========  ========  =======
        dt                   symbol      weight    price
        ===================  ========  ========  =======
        2019-01-02 09:01:00  DLi9001       0.5   961.695
        2019-01-02 09:02:00  DLi9001       0.25  960.72
        2019-01-02 09:03:00  DLi9001       0.25  962.669
        2019-01-02 09:04:00  DLi9001       0.25  960.72
        2019-01-02 09:05:00  DLi9001       0.25  961.695
        ===================  ========  ========  =======

    :param kwargs:
        - fee: 单边手续费，单位为BP，默认为2BP
        - digits: 权重小数位数，默认为2
        - show_drawdowns: bool，是否展示最大回撤，默认为 False
        - show_daily_detail: bool，是否展示每日收益详情，默认为 False
        - show_backtest_detail: bool，是否展示回测详情，默认为 False
        - show_splited_daily: bool，是否展示分段日收益表现，默认为 False
        - show_yearly_stats: bool，是否展示年度绩效指标，默认为 False
        - show_monthly_return: bool，是否展示月度累计收益，默认为 False
        - n_jobs: int, 并行计算的进程数，默认为 1
    """
    WeightBacktest = safe_import_weight_backtest()
    if WeightBacktest is None:
        return

    from czsc.eda import cal_yearly_days

    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)
    n_jobs = kwargs.pop("n_jobs", 1)
    yearly_days = kwargs.pop("yearly_days", None)
    weight_type = kwargs.pop("weight_type", "ts")

    if not yearly_days:
        yearly_days = cal_yearly_days(dts=dfw["dt"].unique())

    if (dfw.isnull().sum().sum() > 0) or (dfw.isna().sum().sum() > 0):
        st.warning("权重数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(dfw[dfw.isnull().sum(axis=1) > 0], use_container_width=True)
        st.stop()

    wb = WeightBacktest(
        dfw=dfw, fee_rate=fee / 10000, digits=digits, n_jobs=n_jobs, yearly_days=yearly_days, weight_type=weight_type
    )
    stat = wb.stats

    st.divider()
    st.markdown(
        f"**回测参数：** 单边手续费 {fee} BP，权重小数位数 {digits} ，"
        f"年交易天数 {yearly_days}，品种数量：{dfw['symbol'].nunique()}"
    )

    # 显示核心指标
    c1, c2, c3, c4, c5, c6, c7, c8, c9, c10, c11 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    c1.metric("盈亏平衡点", f"{stat['盈亏平衡点']:.2%}")
    c2.metric("单笔收益（BP）", f"{stat['单笔收益']}")
    c3.metric("交易胜率", f"{stat['交易胜率']:.2%}")
    c4.metric("持仓K线数", f"{stat['持仓K线数']}")
    c5.metric("最大回撤", f"{stat['最大回撤']:.2%}")
    c6.metric("年化收益率", f"{stat['年化']:.2%}")
    c7.metric("夏普比率", f"{stat['夏普']:.2f}")
    c8.metric("卡玛比率", f"{stat['卡玛']:.2f}")
    c9.metric("年化波动率", f"{stat['年化波动率']:.2%}")
    c10.metric("多头占比", f"{stat['多头占比']:.2%}")
    c11.metric("空头占比", f"{stat['空头占比']:.2%}")

    # 显示交易方向统计
    with st.popover(label="交易方向统计", help="统计多头、空头交易次数、胜率、盈亏比等信息"):
        dfx = pd.DataFrame([wb.long_stats, wb.short_stats])
        dfx.index = ["多头", "空头"]
        dfx.index.name = "交易方向"
        st.dataframe(dfx.T.astype(str), use_container_width=True)

    # 显示日收益
    dret = wb.daily_return.copy()
    dret["dt"] = pd.to_datetime(dret["date"])
    dret = dret.set_index("dt").drop(columns=["date"])

    from .returns import show_daily_return, show_drawdowns, show_monthly_return
    from .statistics import show_splited_daily, show_yearly_stats

    show_daily_return(dret, legend_only_cols=dfw["symbol"].unique().tolist(), yearly_days=yearly_days, **kwargs)

    if kwargs.get("show_drawdowns", False):
        show_drawdowns(dret, ret_col="total", sub_title="")

    if kwargs.get("show_splited_daily", False):
        with st.expander("品种等权日收益分段表现", expanded=False):
            show_splited_daily(dret[["total"]].copy(), ret_col="total", yearly_days=yearly_days)

    if kwargs.get("show_yearly_stats", False):
        with st.expander("年度绩效指标", expanded=False):
            show_yearly_stats(dret, ret_col="total")

    if kwargs.get("show_monthly_return", False):
        with st.expander("月度累计收益", expanded=False):
            show_monthly_return(dret, ret_col="total", sub_title="")

    if kwargs.get("show_weight_distribution", True):
        with st.expander("策略分品种的 weight 分布", expanded=False):
            show_weight_distribution(dfw, abs_weight=True)

    return wb


def show_holds_backtest(df, **kwargs):
    """分析持仓组合的回测结果

    :param df: 回测数据，任何字段都不允许有空值；建议 weight 列在截面的和为 1；数据样例：
        ===================  ========  ========  =======
        dt                   symbol      weight    n1b
        ===================  ========  ========  =======
        2019-01-02 09:01:00  DLi9001       0.5   961.695
        2019-01-02 09:02:00  DLi9001       0.25  960.72
        2019-01-02 09:03:00  DLi9001       0.25  962.669
        2019-01-02 09:04:00  DLi9001       0.25  960.72
        2019-01-02 09:05:00  DLi9001       0.25  961.695
        ===================  ========  ========  =======

    :param kwargs:
        - fee: 单边手续费，单位为BP，默认为2BP
        - digits: 权重小数位数，默认为2
        - show_drawdowns: 是否展示最大回撤分析，默认为True
        - show_splited_daily: 是否展示分段收益表现，默认为False
        - show_yearly_stats: 是否展示年度绩效指标，默认为True
        - show_monthly_return: 是否展示月度累计收益，默认为True
    """
    from czsc.utils.stats import holds_performance

    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)

    if (df.isnull().sum().sum() > 0) or (df.isna().sum().sum() > 0):
        st.warning("数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(df[df.isnull().sum(axis=1) > 0], use_container_width=True)
        st.stop()

    # 计算每日收益、交易成本、净收益
    sdt = df["dt"].min().strftime("%Y-%m-%d")
    edt = df["dt"].max().strftime("%Y-%m-%d")
    dfr = holds_performance(df, fee=fee, digits=digits)
    st.write(f"回测时间：{sdt} ~ {edt}; 单边年换手率：{dfr['change'].mean() * 252:.2f} 倍; 单边费率：{fee}BP")

    daily = dfr[["date", "edge_post_fee"]].copy()
    daily.columns = ["dt", "return"]
    daily["dt"] = pd.to_datetime(daily["dt"])
    daily = daily.sort_values("dt").reset_index(drop=True)

    from .returns import show_daily_return, show_drawdowns, show_monthly_return
    from .statistics import show_splited_daily, show_yearly_stats

    show_daily_return(daily, stat_hold_days=False)

    if kwargs.get("show_drawdowns", True):
        st.write("最大回撤分析")
        show_drawdowns(daily, ret_col="return", sub_title="")

    if kwargs.get("show_splited_daily", False):
        st.write("分段收益表现")
        show_splited_daily(daily, ret_col="return")

    if kwargs.get("show_yearly_stats", True):
        st.write("年度绩效指标")
        show_yearly_stats(daily, ret_col="return", sub_title="")

    if kwargs.get("show_monthly_return", True):
        st.write("月度累计收益")
        show_monthly_return(daily, ret_col="return", sub_title="")


def show_stoploss_by_direction(dfw, **kwargs):
    """按方向止损分析的展示

    :param dfw: pd.DataFrame, 包含权重数据
    :param kwargs: dict, 其他参数
        - stoploss: float, 止损比例
        - show_detail: bool, 是否展示详细信息
        - digits: int, 价格小数位数, 默认2
        - fee_rate: float, 手续费率, 默认0.0002
    """
    from czsc.traders.weight_backtest import stoploss_by_direction

    dfw = dfw.copy()
    stoploss = kwargs.pop("stoploss", 0.08)
    dfw1 = stoploss_by_direction(dfw, stoploss=stoploss)

    # 找出逐笔止损点
    rows = []
    for symbol, dfg in dfw1.groupby("symbol"):
        for order_id, dfg1 in dfg.groupby("order_id"):
            if dfg1["is_stop"].any():
                row = {
                    "symbol": symbol,
                    "order_id": order_id,
                    "交易方向": "多头" if dfg1["weight"].iloc[0] > 0 else "空头",
                    "开仓时间": dfg1["dt"].iloc[0],
                    "平仓时间": dfg1["dt"].iloc[-1],
                    "平仓收益": dfg1["hold_returns"].iloc[-1],
                    "止损时间": dfg1[dfg1["is_stop"]]["dt"].iloc[0],
                    "止损收益": dfg1[dfg1["is_stop"]]["hold_returns"].iloc[0],
                }
                rows.append(row)

    dfr = pd.DataFrame(rows)
    with st.expander("逐笔止损点", expanded=False):
        st.dataframe(dfr, use_container_width=True)

    if kwargs.pop("show_detail", False):
        cols = [
            "dt",
            "symbol",
            "raw_weight",
            "weight",
            "price",
            "hold_returns",
            "min_hold_returns",
            "returns",
            "order_id",
            "is_stop",
        ]
        dfs = dfw1[dfw1["is_stop"]][cols].copy()
        with st.expander("止损点详情", expanded=False):
            st.dataframe(dfs, use_container_width=True)

    show_weight_backtest(dfw1[["dt", "symbol", "weight", "price"]].copy(), **kwargs)


def show_backtest_by_thresholds(df: pd.DataFrame, out_sample_sdt, **kwargs):
    """根据权重阈值进行回测对比的 Streamlit 组件

    :param df: pd.DataFrame, columns = ['dt', 'symbol', 'weight', 'price'], 含权重的K线数据
    :param kwargs: 其他参数

        - out_sample_sdt: str, 样本外开始时间，格式如 '2020-01-01'
        - percentiles: list, 样本内分位数比例序列，默认 [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        - fee_rate: float, 交易成本，默认 0.0002
        - digits: int, 权重保留小数位数，默认 2
        - weight_type: str, 权重类型，默认 'ts'
    """
    from czsc.svc.strategy import show_multi_backtest
    from czsc.svc.base import safe_import_weight_backtest
    from czsc.eda import cal_yearly_days

    # 安全导入 WeightBacktest
    WeightBacktest = safe_import_weight_backtest()
    if WeightBacktest is None:
        st.error("无法导入WeightBacktest类，请检查czsc或rs_czsc库的安装")
        return

    # 获取参数
    percentiles = kwargs.get("percentiles", [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    fee_rate = kwargs.get("fee_rate", 0.0002)
    digits = kwargs.get("digits", 2)
    weight_type = kwargs.get("weight_type", "ts")
    only_out_sample = kwargs.get("only_out_sample", False)
    sub_title = kwargs.get("sub_title", "不同权重阈值下的回测结果对比")

    # 验证输入数据
    required_cols = ["dt", "symbol", "weight", "price"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"数据缺少必需的列：{missing_cols}，当前数据列为：{list(df.columns)}")
        return

    st.subheader(sub_title, divider="rainbow")

    # 数据预处理
    df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["symbol", "dt"]).reset_index(drop=True)

    # 计算年化交易日数
    yearly_days = cal_yearly_days(df["dt"].unique().tolist())

    # 分割样本内外数据
    out_sample_sdt = pd.to_datetime(out_sample_sdt)
    df_in_sample = df[df["dt"] < out_sample_sdt].copy()
    df_out_sample = df[df["dt"] >= out_sample_sdt].copy()

    if len(df_in_sample) == 0:
        st.error("样本内数据为空，请检查 out_sample_sdt 参数")
        return

    df_analysis = df_out_sample.copy() if only_out_sample else df.copy()

    # 显示数据基本信息
    weight_stats = df_in_sample["weight"].describe()
    st.markdown(
        f"**数据基本信息：** 总记录数 {len(df)}，标的数量 {df['symbol'].nunique()}，样本内记录数 {len(df_in_sample)}，"
        f"样本外记录数 {len(df_out_sample)}，样本内权重均值 {weight_stats['mean']:.4f}，标准差 {weight_stats['std']:.4f}"
    )

    # 计算样本内权重绝对值的分位数阈值
    weight_abs = df_in_sample["weight"].abs()
    thresholds = {}

    for p in percentiles:
        threshold = weight_abs.quantile(p)
        thresholds[f"阈值_{int(p*100)}%"] = threshold

    # 创建不同阈值下的回测策略
    wbs = {}

    # 原始策略（无阈值过滤）
    try:
        wb_original = WeightBacktest(
            df_analysis[["dt", "symbol", "weight", "price"]],
            fee_rate=fee_rate,
            digits=digits,
            weight_type=weight_type,
            yearly_days=yearly_days,
        )
        wbs["原始策略"] = wb_original
    except Exception as e:
        st.error(f"原始策略回测失败：{e}")
        return

    # 不同阈值下的策略
    for p in percentiles:
        threshold_name = f"阈值_{int(p*100)}%"
        threshold_value = thresholds[threshold_name]

        # 创建过滤后的权重
        df_filtered = df_analysis.copy()
        # 仅当权重绝对值大于等于阈值时，使用 sign(weight) * 1，否则权重为0
        df_filtered["weight"] = np.where(
            df_filtered["weight"].abs() >= threshold_value, np.sign(df_filtered["weight"]), 0
        )

        try:
            wb_filtered = WeightBacktest(
                df_filtered[["dt", "symbol", "weight", "price"]],
                fee_rate=fee_rate,
                digits=digits,
                weight_type=weight_type,
                yearly_days=yearly_days,
            )
            wbs[threshold_name] = wb_filtered
        except Exception as e:
            logger.warning(f"阈值 {threshold_name} 回测失败：{e}")
            continue

    if len(wbs) == 0:
        st.error("所有策略回测都失败了")
        return

    # 显示回测结果对比
    st.caption(f"回测参数：fee_rate={fee_rate}, digits={digits}, weight_type={weight_type}")
    show_multi_backtest(wbs, show_describe=False)

    # 显示权重使用情况统计
    with st.container(border=True):
        st.markdown("#### :orange[权重使用情况统计]")

        # 计算不同阈值下的权重使用比例
        usage_stats = []
        for p in percentiles:
            threshold_name = f"阈值_{int(p*100)}%"
            threshold_value = thresholds[threshold_name]

            # 计算权重使用比例（非零权重的比例）
            total_records = len(df_analysis)
            used_records = len(df_analysis[df_analysis["weight"].abs() >= threshold_value])
            usage_ratio = used_records / total_records if total_records > 0 else 0

            usage_stats.append(
                {
                    "阈值名称": threshold_name,
                    "阈值数值": round(threshold_value, 4),
                    "使用记录数": used_records,
                    "总记录数": total_records,
                    "使用比例": f"{usage_ratio:.2%}",
                }
            )

        usage_df = pd.DataFrame(usage_stats)
        st.dataframe(usage_df, use_container_width=True)

    return wbs


def show_yearly_backtest(df: pd.DataFrame, **kwargs):
    """根据权重数据，按年回测分析绩效

    :param df: pd.DataFrame, columns = ['dt', 'symbol', 'weight', 'price'], 含权重的K线数据
    :param kwargs: 其他参数

        - fee_rate: float, 交易成本，默认 0.0002
        - digits: int, 权重保留小数位数，默认 2
        - weight_type: str, 权重类型，默认 'ts'
        - min_samples_per_year: int, 每年最少样本数，默认 60
        - only_complete_years: bool, 是否只展示完整年份，默认 True
    """
    from czsc.svc.strategy import show_multi_backtest
    from czsc.svc.base import safe_import_weight_backtest
    from czsc.eda import cal_yearly_days

    # 安全导入 WeightBacktest
    WeightBacktest = safe_import_weight_backtest()
    if WeightBacktest is None:
        st.error("无法导入WeightBacktest类，请检查czsc或rs_czsc库的安装")
        return

    # 获取参数
    fee_rate = kwargs.get("fee_rate", 0.0002)
    digits = kwargs.get("digits", 2)
    weight_type = kwargs.get("weight_type", "ts")
    sub_title = kwargs.get("sub_title", "按年度权重回测结果对比")

    # 验证输入数据
    required_cols = ["dt", "symbol", "weight", "price"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"数据缺少必需的列：{missing_cols}，当前数据列为：{list(df.columns)}")
        return

    st.subheader(sub_title, divider="rainbow")

    # 数据预处理
    df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["symbol", "dt"]).reset_index(drop=True)

    # 添加年份列
    df["year"] = df["dt"].dt.year

    # 计算年化交易日数
    yearly_days = cal_yearly_days(df["dt"].unique().tolist())

    # 获取所有年份
    years = sorted(df["year"].unique())

    if len(years) == 0:
        st.error("数据中没有有效的年份信息")
        return

    # 显示数据基本信息
    total_records = len(df)
    symbol_count = df["symbol"].nunique()
    weight_stats = df["weight"].describe()

    st.markdown(
        f"**数据基本信息：** 总记录数 {total_records}，标的数量 {symbol_count}，"
        f"时间范围 {years[0]}-{years[-1]}，权重均值 {weight_stats['mean']:.4f}，标准差 {weight_stats['std']:.4f}"
    )

    # 创建不同年份的回测策略
    wbs = {}

    # 全部数据回测（作为基准）
    try:
        wb_all = WeightBacktest(
            df[["dt", "symbol", "weight", "price"]],
            fee_rate=fee_rate,
            digits=digits,
            weight_type=weight_type,
            yearly_days=yearly_days,
        )
        wbs["全部年份"] = wb_all
    except Exception as e:
        st.error(f"全部数据回测失败：{e}")
        return

    # 各年份回测
    for year in years:
        year_data = df[df["year"] == year].copy()

        if len(year_data) == 0:
            logger.warning(f"{year}年数据为空，跳过")
            continue

        try:
            wb_year = WeightBacktest(
                year_data[["dt", "symbol", "weight", "price"]],
                fee_rate=fee_rate,
                digits=digits,
                weight_type=weight_type,
                yearly_days=yearly_days,
            )
            wbs[f"{year}年"] = wb_year
        except Exception as e:
            logger.warning(f"{year}年回测失败：{e}")
            continue

    if len(wbs) <= 1:  # 只有全部年份的回测
        st.error("没有足够的年份数据进行对比分析")
        return

    # 显示回测结果对比
    st.caption(f"回测参数：fee_rate={fee_rate}, digits={digits}, weight_type={weight_type}")
    show_multi_backtest(wbs, show_describe=False)
    return wbs
