"""
回测分析与可视化组件模块

本模块封装了一组基于 Streamlit 的回测可视化组件，主要用于在交互式仪表盘中展示
权重型策略的回测结果，包括以下核心功能：

1. 权重分布展示：观察各品种权重的分布特征与分位数；
2. 权重回测结果展示：基于 ``WeightBacktest`` 的核心绩效指标、日收益、回撤、
   月度收益、年度统计、分段绩效等多维度展示；
3. 持仓组合回测：基于持仓权重数据计算每日收益、交易成本与净收益；
4. 按方向止损分析：在回测前先做止损改写，再进行权重回测；
5. 阈值过滤回测：按权重的样本内分位数阈值过滤后再回测，对比不同阈值的效果；
6. 按年度/品种切片回测、多空分别回测、综合回测面板；

模块依赖：
- ``wbt.WeightBacktest``：底层 Rust 加速的权重回测器；
- ``streamlit``：负责所有前端展示；
- ``czsc.eda.cal_yearly_days``：根据交易日序列推断年化天数；
- 同包内 ``returns``、``statistics``、``strategy`` 子模块：共享的可视化组件。
"""

import numpy as np
import pandas as pd
import streamlit as st
from loguru import logger

from wbt import WeightBacktest


def show_weight_distribution(dfw, abs_weight=True, **kwargs):
    """展示权重分布

    按品种分组，对每个品种的权重序列调用 ``describe`` 计算分位数并展示，常用于
    观察策略在不同品种上的仓位规模与极端值情况。

    :param dfw: pd.DataFrame，必须包含 ``symbol``、``dt``、``price``、``weight`` 列
    :param abs_weight: bool，是否对权重取绝对值后再统计；多空策略一般置 True
    :param kwargs: 其他关键字参数
        - percentiles: list，``describe`` 使用的分位数序列，默认包含从 5% 到 95% 的常用分位
    :return: None；结果通过 :func:`statistics.show_df_describe` 写入 Streamlit 页面
    """
    dfw = dfw.copy()
    if abs_weight:
        # 多空策略下绝对值更能反映仓位规模
        dfw["weight"] = dfw["weight"].abs()

    default_percentiles = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]
    percentiles = kwargs.get("percentiles", default_percentiles)

    # 按 symbol 分组，得到每个品种的描述性统计并展开成宽表
    dfs = dfw.groupby("symbol")["weight"].apply(lambda x: x.describe(percentiles=percentiles)).unstack().reset_index()

    # 复用 statistics 模块中的 describe 渲染函数，确保样式与其他位置一致
    from .statistics import show_df_describe

    show_df_describe(dfs)


def show_weight_backtest(dfw, **kwargs):
    """展示权重回测结果

    将权重数据传入 ``WeightBacktest``，得到完整的回测对象后，把核心绩效指标、
    交易方向统计、日收益曲线、回撤、分段日收益、年度绩效、月度收益等内容
    渲染到 Streamlit 页面。

    :param dfw: 回测数据；任何字段都不允许有空值；数据样例如下：

        ===================  ========  ========  =======
        dt                   symbol      weight    price
        ===================  ========  ========  =======
        2019-01-02 09:01:00  DLi9001       0.5   961.695
        2019-01-02 09:02:00  DLi9001       0.25  960.72
        2019-01-02 09:03:00  DLi9001       0.25  962.669
        2019-01-02 09:04:00  DLi9001       0.25  960.72
        2019-01-02 09:05:00  DLi9001       0.25  961.695
        ===================  ========  ========  =======

    :param kwargs: 其他参数
        - fee: 单边手续费，单位为 BP，默认为 2BP
        - digits: 权重小数位数，默认为 2
        - show_drawdowns: bool，是否展示最大回撤，默认 False
        - show_daily_detail: bool，是否展示每日收益详情，默认 False
        - show_backtest_detail: bool，是否展示回测详情，默认 False
        - show_splited_daily: bool，是否展示分段日收益表现，默认 False
        - show_yearly_stats: bool，是否展示年度绩效指标，默认 False
        - show_monthly_return: bool，是否展示月度累计收益，默认 False
        - n_jobs: int，并行计算的进程数，默认为 1
    :return: WeightBacktest，构造好的回测对象，便于后续进一步分析
    """
    from czsc.eda import cal_yearly_days

    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)
    n_jobs = kwargs.pop("n_jobs", 1)
    yearly_days = kwargs.pop("yearly_days", None)
    weight_type = kwargs.pop("weight_type", "ts")

    if not yearly_days:
        # 未显式指定时，根据 dt 序列推断每年实际交易天数
        yearly_days = cal_yearly_days(dts=dfw["dt"].unique())

    # 严格校验缺失值；存在缺失时直接终止，避免回测结果失真
    if (dfw.isnull().sum().sum() > 0) or (dfw.isna().sum().sum() > 0):
        st.warning("权重数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(dfw[dfw.isnull().sum(axis=1) > 0], width="stretch")
        st.stop()

    # 构造回测对象；fee 在 BP 与小数之间转换
    wb = WeightBacktest(
        dfw=dfw, fee_rate=fee / 10000, digits=digits, n_jobs=n_jobs, yearly_days=yearly_days, weight_type=weight_type
    )
    stat = wb.stats

    st.divider()
    st.markdown(
        f"**回测参数：** 单边手续费 {fee} BP，权重小数位数 {digits} ，"
        f"年交易天数 {yearly_days}，品种数量：{dfw['symbol'].nunique()}"
    )

    # 顶部展示 11 个核心绩效指标
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

    # 多空分别统计：盈亏比、胜率等关键指标
    with st.popover(label="交易方向统计", help="统计多头、空头交易次数、胜率、盈亏比等信息"):
        dfx = pd.DataFrame([wb.long_stats, wb.short_stats])
        dfx.index = ["多头", "空头"]
        dfx.index.name = "交易方向"
        st.dataframe(dfx.T.astype(str), width="stretch")

    # 取出每日收益序列，转成 datetime 索引，便于下游绘图
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

    本函数面向截面持仓权重的回测场景，输入数据每行代表某个时间点对某个标的的目标持仓
    权重，并配合下一期收益（``n1b``）。函数会通过 :func:`holds_performance` 计算每日的
    交易成本、净收益与换手率，并展示日收益、回撤、分段表现、年度绩效与月度累计收益等。

    :param df: 回测数据；任何字段都不允许有空值；建议 ``weight`` 列在截面的和为 1，
        数据样例：

        ===================  ========  ========  =======
        dt                   symbol      weight    n1b
        ===================  ========  ========  =======
        2019-01-02 09:01:00  DLi9001       0.5   961.695
        2019-01-02 09:02:00  DLi9001       0.25  960.72
        2019-01-02 09:03:00  DLi9001       0.25  962.669
        2019-01-02 09:04:00  DLi9001       0.25  960.72
        2019-01-02 09:05:00  DLi9001       0.25  961.695
        ===================  ========  ========  =======

    :param kwargs: 其他参数
        - fee: 单边手续费，单位为 BP，默认为 2BP
        - digits: 权重小数位数，默认为 2
        - show_drawdowns: bool，是否展示最大回撤分析，默认 True
        - show_splited_daily: bool，是否展示分段收益表现，默认 False
        - show_yearly_stats: bool，是否展示年度绩效指标，默认 True
        - show_monthly_return: bool，是否展示月度累计收益，默认 True
    :return: None
    """
    from czsc.utils.analysis.stats import holds_performance

    fee = kwargs.get("fee", 2)
    digits = kwargs.get("digits", 2)

    if (df.isnull().sum().sum() > 0) or (df.isna().sum().sum() > 0):
        st.warning("数据中存在空值，请检查数据后再试；空值数据如下：")
        st.dataframe(df[df.isnull().sum(axis=1) > 0], width="stretch")
        st.stop()

    # 计算每日收益、交易成本与净收益
    sdt = df["dt"].min().strftime("%Y-%m-%d")
    edt = df["dt"].max().strftime("%Y-%m-%d")
    dfr = holds_performance(df, fee=fee, digits=digits)
    st.write(f"回测时间：{sdt} ~ {edt}; 单边年换手率：{dfr['change'].mean() * 252:.2f} 倍; 单边费率：{fee}BP")

    # 把"扣费后净收益"列提取为标准的日收益序列
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

    在执行权重回测之前，先调用 ``rs_czsc.stoploss_by_direction`` 对权重数据按交易方向
    进行止损改写：当一笔交易（同方向连续持仓）的浮亏达到 ``stoploss`` 时，将后续权重
    强制平仓。改写后再调用 :func:`show_weight_backtest` 进行回测和展示。

    :param dfw: pd.DataFrame，包含 ``symbol``、``dt``、``weight``、``price`` 等权重数据
    :param kwargs: 其他参数
        - stoploss: float，止损比例，例如 0.08 代表 8% 浮亏触发止损，默认 0.08
        - show_detail: bool，是否展示止损点的详细数据，默认 False
        - digits: int，价格小数位数，默认 2
        - fee_rate: float，手续费率，默认 0.0002
    :return: None
    """
    from rs_czsc import stoploss_by_direction

    dfw = dfw.copy()
    stoploss = kwargs.pop("stoploss", 0.08)
    # 按方向进行止损改写，返回带 ``hold_returns``、``is_stop`` 等附加列的数据
    dfw1 = stoploss_by_direction(dfw, stoploss=stoploss)

    # 找出每一笔交易的止损点：按 symbol/order_id 聚合，取首次 is_stop=True 的位置
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
        st.dataframe(dfr, width="stretch")

    # 可选：展示所有触发止损点对应的明细行
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
            st.dataframe(dfs, width="stretch")

    show_weight_backtest(dfw1[["dt", "symbol", "weight", "price"]].copy(), **kwargs)


def show_backtest_by_thresholds(df: pd.DataFrame, out_sample_sdt, **kwargs):
    """根据权重阈值进行回测对比的 Streamlit 组件

    按样本内权重绝对值的若干分位数生成阈值，分别对原始策略与"权重过阈值则取
    sign，否则置 0"的方案进行回测，并对比累计收益与核心指标。

    :param df: pd.DataFrame，columns = ['dt', 'symbol', 'weight', 'price']，含权重的 K 线数据
    :param out_sample_sdt: 样本外开始时间；样本内用于生成阈值，样本外可单独评估效果
    :param kwargs: 其他参数
        - percentiles: list，样本内分位数比例序列，默认 [0.0, 0.1, ..., 0.9]
        - fee_rate: float，交易成本，默认 0.0002
        - digits: int，权重保留小数位数，默认 2
        - weight_type: str，权重类型，默认 'ts'
        - only_out_sample: bool，是否仅在样本外评估过滤效果，默认 False
        - sub_title: str，标题文案
    :return: dict 或 None；返回 ``{阈值名: WeightBacktest}`` 映射，构造失败时返回 None
    """
    from czsc.eda import cal_yearly_days
    from czsc.svc.strategy import show_multi_backtest

    # 提取参数
    percentiles = kwargs.get("percentiles", [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
    fee_rate = kwargs.get("fee_rate", 0.0002)
    digits = kwargs.get("digits", 2)
    weight_type = kwargs.get("weight_type", "ts")
    only_out_sample = kwargs.get("only_out_sample", False)
    sub_title = kwargs.get("sub_title", "不同权重阈值下的回测结果对比")

    # 校验输入数据列是否齐全
    required_cols = ["dt", "symbol", "weight", "price"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        st.error(f"数据缺少必需的列：{missing_cols}，当前数据列为：{list(df.columns)}")
        return

    st.subheader(sub_title, divider="rainbow")

    # 数据预处理：保证 dt 类型与排序
    df = df.copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["symbol", "dt"]).reset_index(drop=True)

    # 计算年化交易日数
    yearly_days = cal_yearly_days(df["dt"].unique().tolist())

    # 切分样本内与样本外数据
    out_sample_sdt = pd.to_datetime(out_sample_sdt)
    df_in_sample = df[df["dt"] < out_sample_sdt].copy()
    df_out_sample = df[df["dt"] >= out_sample_sdt].copy()

    if len(df_in_sample) == 0:
        st.error("样本内数据为空，请检查 out_sample_sdt 参数")
        return

    # 根据 only_out_sample 决定回测时使用全部数据还是仅样本外
    df_analysis = df_out_sample.copy() if only_out_sample else df.copy()

    # 展示数据基本信息，便于诊断
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
        thresholds[f"阈值_{int(p * 100)}%"] = threshold

    # 构造不同阈值下的回测策略
    wbs = {}

    # 原始策略（不做任何过滤）
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

    # 不同阈值下的策略：权重绝对值大于等于阈值时取 sign(weight) * 1，否则置 0
    for p in percentiles:
        threshold_name = f"阈值_{int(p * 100)}%"
        threshold_value = thresholds[threshold_name]

        # 重新构造过滤后的权重
        df_filtered = df_analysis.copy()
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

    # 多策略绩效对比
    st.caption(f"回测参数：fee_rate={fee_rate}, digits={digits}, weight_type={weight_type}")
    show_multi_backtest(wbs, show_describe=False)

    # 不同阈值下权重的使用情况统计
    with st.container(border=True):
        st.markdown("#### :orange[权重使用情况统计]")

        usage_stats = []
        for p in percentiles:
            threshold_name = f"阈值_{int(p * 100)}%"
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
        st.dataframe(usage_df, width="stretch")

    return wbs


def show_backtest_by_year(df: pd.DataFrame, **kwargs):
    """按照年份进行回测

    将权重数据按自然年切片，分别构造 ``WeightBacktest`` 进行回测，并通过
    :func:`show_multi_backtest` 进行多策略对比，便于观察策略在不同年份的稳定性。

    :param df: pd.DataFrame，包含 dt/symbol/weight/price 列
    :param kwargs: 透传给 ``WeightBacktest`` 的参数（``fee_rate`` / ``digits`` / ``weight_type`` / ``yearly_days``）
    :return: dict 或 None；按年份组织的回测对象映射
    """
    if WeightBacktest is None:
        return

    from .strategy import show_multi_backtest

    yearly_days = kwargs.get("yearly_days", 252)
    digits = kwargs.get("digits", 2)
    fee_rate = kwargs.get("fee_rate", 0.0)
    weight_type = kwargs.get("weight_type", "ts")

    df = df[["dt", "symbol", "weight", "price"]].copy()
    df["year"] = df["dt"].dt.year
    wbs = {}
    for year, dfy in df.groupby("year"):
        # 每年单独排序、重设索引后再回测
        dfy = dfy.copy().sort_values(["symbol", "dt"]).reset_index(drop=True)
        wbs[f"{year}年"] = WeightBacktest(
            dfy, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days
        )

    show_multi_backtest(wbs)
    return wbs


def show_backtest_by_symbol(df: pd.DataFrame, **kwargs):
    """按照交易标的进行回测

    将权重数据按 symbol 切片，分别构造 ``WeightBacktest``，便于观察各品种的贡献。

    :param df: pd.DataFrame，包含 dt/symbol/weight/price 列
    :param kwargs: 透传给 ``WeightBacktest`` 的参数
    :return: dict 或 None；按 symbol 组织的回测对象映射
    """
    if WeightBacktest is None:
        return

    from .strategy import show_multi_backtest

    digits = kwargs.get("digits", 2)
    fee_rate = kwargs.get("fee_rate", 0.0)
    weight_type = kwargs.get("weight_type", "ts")
    yearly_days = kwargs.get("yearly_days", 252)

    df = df[["dt", "symbol", "weight", "price"]].copy()

    wbs = {}
    for symbol, dfs in df.groupby("symbol"):
        dfs = dfs.copy().sort_values(["dt"]).reset_index(drop=True)
        wbs[symbol] = WeightBacktest(
            dfs, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days
        )

    show_multi_backtest(wbs)
    return wbs


def show_long_short_backtest(df: pd.DataFrame, **kwargs):
    """分析多头、空头收益及基准等权对比

    将权重切分为：
    - 原始策略：保留正负权重不变；
    - 策略多头：仅保留正权重，负权重置 0；
    - 策略空头：仅保留负权重，正权重置 0；
    - 基准等权：所有权重置 1，作为多头满仓基准。

    四组策略统一回测后调用 :func:`show_multi_backtest` 进行对比。

    :param df: pd.DataFrame，包含 dt/symbol/weight/price 列
    :param kwargs: 透传给 ``WeightBacktest`` 的参数
    :return: dict 或 None；多空对比的回测对象映射
    """
    if WeightBacktest is None:
        return

    from .strategy import show_multi_backtest

    yearly_days = kwargs.get("yearly_days", 252)
    digits = kwargs.get("digits", 2)
    fee_rate = kwargs.get("fee_rate", 0.0)
    weight_type = kwargs.get("weight_type", "ts")

    df = df[["dt", "symbol", "weight", "price"]].copy()

    # 多头：负权重截断为 0
    dfl = df.copy()
    dfl["weight"] = dfl["weight"].clip(lower=0)

    # 空头：正权重截断为 0
    dfs = df.copy()
    dfs["weight"] = dfs["weight"].clip(upper=0)

    # 等权满仓基准
    dfb = df.copy()
    dfb["weight"] = 1

    wbs = {
        "原始策略": WeightBacktest(
            df, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days
        ),
        "策略多头": WeightBacktest(
            dfl, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days
        ),
        "策略空头": WeightBacktest(
            dfs, fee_rate=fee_rate, digits=digits, weight_type=weight_type, yearly_days=yearly_days
        ),
        "基准等权": WeightBacktest(dfb, fee_rate=fee_rate, digits=digits, weight_type="ts", yearly_days=yearly_days),
    }
    show_multi_backtest(wbs)
    return wbs


def show_comprehensive_weight_backtest(df: pd.DataFrame, **kwargs):
    """综合权重回测可视化展示

    将整体回测、标的基准、年度回测、标的回测、多空回测、原始数据下载等内容
    整合在 6 个 Tab 页中，便于用户在一个页面完成全方位的策略评估。

    :param df: pd.DataFrame，包含 dt/symbol/weight/price 列的权重数据
    :param kwargs: 透传给底层回测函数的参数（``yearly_days`` / ``fee`` / ``digits`` / ``weight_type``）
    :return: WeightBacktest，整体回测对象
    """
    yearly_days = kwargs.get("yearly_days", 252)
    fee = kwargs.get("fee", 0.0)
    digits = kwargs.get("digits", 2)
    weight_type = kwargs.get("weight_type", "ts")

    # fee 单位为 BP，需要换算成小数比率
    fee_rate = fee / 10000

    tabs = st.tabs(["整体回测", "标的基准", "年度回测", "标的回测", "多空回测", "下载数据"])
    with tabs[0]:
        wb = show_weight_backtest(
            df,
            fee=fee,
            digits=digits,
            yearly_days=yearly_days,
            show_drawdowns=True,
            show_splited_daily=True,
            weight_type=weight_type,
        )
    with tabs[1]:
        from .strategy import show_symbols_bench

        show_symbols_bench(df[["dt", "symbol", "price"]].copy())

    with tabs[2]:
        show_backtest_by_year(df, yearly_days=yearly_days, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    with tabs[3]:
        show_backtest_by_symbol(df, yearly_days=yearly_days, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    with tabs[4]:
        show_long_short_backtest(df, yearly_days=yearly_days, fee_rate=fee_rate, digits=digits, weight_type=weight_type)

    with tabs[5]:
        # 提供原始权重、整体收益、多头收益、空头收益的下载入口
        st.download_button(
            "下载原始数据",
            data=df.to_csv(index=False),
            on_click="ignore",
            file_name="original_weigts_data.csv",
            mime="text/csv",
        )
        st.download_button(
            "下载策略收益",
            data=wb.daily_return.to_csv(index=False),
            on_click="ignore",
            file_name="strategy_returns.csv",
            mime="text/csv",
        )
        st.download_button(
            "下载多头收益",
            data=wb.long_daily_return.to_csv(index=False),
            on_click="ignore",
            file_name="long_strategy_returns.csv",
            mime="text/csv",
        )
        st.download_button(
            "下载空头收益",
            data=wb.short_daily_return.to_csv(index=False),
            on_click="ignore",
            file_name="short_strategy_returns.csv",
            mime="text/csv",
        )
    return wb
