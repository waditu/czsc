"""
价格敏感性分析模块

用于分析策略对执行价格的敏感性。其典型应用场景是：同一份权重数据搭配不同的
执行价（如开盘价、加权平均价、TWAP、VWAP 等，列名以 ``TP`` 开头），分别构造
``WeightBacktest`` 进行回测，再比较核心绩效指标与累计收益曲线，从而评估策略
对价格执行的依赖程度。

主要功能：

1. :func:`show_price_sensitive`：核心入口，遍历所有 ``TP*`` 列，逐个完成回测、
   汇总绩效，并在 Streamlit 面板中以表格 + 折线图的形式展示。
2. 内部辅助 :func:`_show_sensitivity_assessment`：根据"年化收益的极差/均值"
   给出三档敏感性评估（低 / 中 / 高）。

输出统一通过 Streamlit 渲染；同时也以 ``(stats_df, daily_df)`` 二元组的形式返回，
方便上层进一步处理或导出。
"""

import pandas as pd
import streamlit as st
from loguru import logger
from wbt import WeightBacktest

from .base import apply_stats_style
from .returns import show_cumulative_returns


def show_price_sensitive(
    df: pd.DataFrame, fee: float = 2.0, digits: int = 2, weight_type: str = "ts", n_jobs: int = 1, **kwargs
) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """价格敏感性分析组件

    分析策略对执行价格的敏感性，通过对比不同交易价格的回测结果，评估价格执行
    对策略性能的影响。

    :param df: pd.DataFrame，必须包含以下列：
        - ``symbol``：合约代码
        - ``dt``：日期时间
        - ``weight``：仓位权重
        - ``TP*``：以 TP 开头的交易价格列（如 ``TP_open``、``TP_high`` 等）
    :param fee: float，单边费率（BP），默认 2.0
    :param digits: int，权重小数位数，默认 2
    :param weight_type: str，权重类型，可选 ``"ts"`` 或 ``"cs"``，默认 ``"ts"``
    :param n_jobs: int，并行进程数，默认 1
    :param kwargs: 其他参数
        - title_prefix: str，标题前缀，默认空字符串
        - show_detailed_stats: bool，是否展示更多绩效字段，默认 False
    :return: tuple[pd.DataFrame, pd.DataFrame] | None；
        分别为绩效汇总表和日收益宽表；若关键步骤失败则返回 None
    :example:
        >>> # 基本用法
        >>> dfr, dfd = show_price_sensitive(df, fee=2.0, digits=2)

        >>> # 自定义参数
        >>> dfr, dfd = show_price_sensitive(
        ...     df,
        ...     fee=1.5,
        ...     digits=3,
        ...     weight_type="cs",
        ...     n_jobs=4,
        ...     title_prefix="策略A - ",
        ...     show_detailed_stats=True
        ... )
    """
    from czsc.eda import cal_yearly_days

    # 提取展示相关参数
    title_prefix = kwargs.get("title_prefix", "")
    show_detailed_stats = kwargs.get("show_detailed_stats", False)

    # 校验必要列是否存在
    required_cols = ["symbol", "dt", "weight"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        error_msg = f"缺少必要的列: {missing_cols}"
        st.error(error_msg)
        logger.error(f"数据检查失败，{error_msg}")
        return None

    # 找出所有以 TP 开头的交易价格列
    tp_cols = [x for x in df.columns if x.startswith("TP")]
    if not tp_cols:
        error_msg = "没有找到交易价格列，请检查文件；交易价列名必须以 TP 开头"
        st.error(error_msg)
        logger.error("未找到以TP开头的交易价格列")
        return None

    logger.info(f"找到 {len(tp_cols)} 个交易价格列: {tp_cols}")

    # 根据 dt 列推断每年实际交易天数
    try:
        yearly_days = cal_yearly_days(dts=df["dt"].unique().tolist())
        logger.info(f"计算得到年化天数: {yearly_days}")
    except Exception as e:
        error_msg = f"计算年化天数失败: {e}"
        st.error(error_msg)
        logger.error(error_msg)
        return None

    # 收集每个 TP 列对应的回测结果
    c1 = st.container(border=True)
    rows = []
    dfd = pd.DataFrame()

    # 进度条与状态文本
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 逐列回测
    for i, tp_col in enumerate(tp_cols):
        try:
            progress = (i + 1) / len(tp_cols)
            progress_bar.progress(progress)
            status_text.text(f"正在处理第 {i + 1}/{len(tp_cols)} 个交易价格: {tp_col}")

            logger.info(f"正在处理第 {i + 1}/{len(tp_cols)} 个交易价格: {tp_col}")

            # 构造单次回测所需的数据：用对应的 TP 列填充缺失，再当作 price 列
            df_temp = df.copy()
            df_temp[tp_col] = df_temp[tp_col].fillna(df_temp["price"])
            dfw = df_temp[["symbol", "dt", "weight", tp_col]].copy()
            dfw.rename(columns={tp_col: "price"}, inplace=True)

            # 构造回测对象
            wb = WeightBacktest(
                dfw=dfw,
                digits=digits,
                fee_rate=fee / 10000,
                weight_type=weight_type,
                n_jobs=n_jobs,
                yearly_days=yearly_days,
            )

            # 把 daily_return 中的 total 列重命名为 TP 列名，便于多列横向合并
            daily = wb.daily_return.copy()
            daily.rename(columns={"total": tp_col}, inplace=True)

            if dfd.empty:
                dfd = daily[["date", tp_col]].copy()
            else:
                dfd = pd.merge(dfd, daily[["date", tp_col]], on="date", how="outer")

            # 保留绩效统计
            res = {"交易价格": tp_col}
            res.update(wb.stats)
            rows.append(res)

        except Exception as e:
            warning_msg = f"处理交易价格 {tp_col} 时出错: {e}"
            st.warning(warning_msg)
            logger.error(warning_msg)
            continue

    # 清除进度条
    progress_bar.empty()
    status_text.empty()

    if not rows:
        st.error("所有交易价格处理失败，无法生成报告")
        return None

    # 渲染绩效对比表
    with c1:
        st.markdown(f"##### :red[{title_prefix}不同交易价格回测核心指标对比]")
        dfr = pd.DataFrame(rows)

        # 多个 TP 列时给出敏感性评估
        if len(dfr) > 1 and "年化" in dfr.columns:
            _show_sensitivity_assessment(dfr)

        # 选择展示列
        if show_detailed_stats:
            display_cols = [
                "交易价格",
                "开始日期",
                "结束日期",
                "绝对收益",
                "年化",
                "年化波动率",
                "夏普",
                "最大回撤",
                "卡玛",
                "日胜率",
                "日盈亏比",
                "交易胜率",
                "单笔收益",
                "持仓K线数",
                "持仓天数",
                "多头占比",
                "空头占比",
            ]
        else:
            display_cols = [
                "交易价格",
                "开始日期",
                "结束日期",
                "绝对收益",
                "年化",
                "年化波动率",
                "夏普",
                "最大回撤",
                "卡玛",
                "交易胜率",
                "单笔收益",
                "持仓K线数",
            ]

        # 仅保留实际存在的列，避免 KeyError
        available_cols = [col for col in display_cols if col in dfr.columns]
        dfr_display = dfr[available_cols].copy()

        # 应用统一样式
        dfr_styled = apply_stats_style(dfr_display)
        st.dataframe(dfr_styled, width="stretch")

    # 累计收益对比图
    c2 = st.container(border=True)
    with c2:
        st.markdown(f"##### :red[{title_prefix}不同交易价格回测累计收益对比]")

        if not dfd.empty:
            dfd_plot = dfd.copy()
            dfd_plot["date"] = pd.to_datetime(dfd_plot["date"])
            dfd_plot.set_index("date", inplace=True)

            show_cumulative_returns(dfd_plot, fig_title=f"{title_prefix}不同交易价格累计收益对比")
        else:
            st.warning("没有有效的收益率数据用于绘制图表")

    logger.info(f"价格敏感性分析完成，共处理 {len(rows)} 个交易价格")
    return dfr, dfd


def _show_sensitivity_assessment(dfr: pd.DataFrame) -> None:
    """根据年化收益的极差/均值，给出敏感性评估文案

    :param dfr: pd.DataFrame，必须包含 ``"年化"`` 列
    :return: None；通过 ``streamlit`` 直接渲染
    """
    annual_returns = dfr["年化"]
    # 敏感度 = (max - min) / mean，反映不同 TP 之间收益的相对差距
    sensitivity_score = (annual_returns.max() - annual_returns.min()) / annual_returns.mean()

    st.markdown("**敏感性评估：**")
    if sensitivity_score < 0.1:
        st.success(f"🟢 策略对价格执行不敏感 (敏感度: {sensitivity_score:.2%})")
    elif sensitivity_score < 0.3:
        st.warning(f"🟡 策略对价格执行中等敏感 (敏感度: {sensitivity_score:.2%})")
    else:
        st.error(f"🔴 策略对价格执行高度敏感 (敏感度: {sensitivity_score:.2%})")


# 模块对外暴露的 API 列表
__all__ = [
    "show_price_sensitive",
]
