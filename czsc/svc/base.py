"""
SVC模块的基础功能模块

提供统一的导入处理、样式配置等基础功能
"""

import pandas as pd
import streamlit as st


def safe_import_daily_performance():
    """安全导入daily_performance函数"""
    try:
        from rs_czsc import daily_performance

        return daily_performance
    except ImportError:
        try:
            from czsc import daily_performance

            return daily_performance
        except ImportError:
            st.error("无法导入daily_performance函数，请检查czsc或rs_czsc库的安装")
            return None


def safe_import_weight_backtest():
    """安全导入WeightBacktest类"""
    try:
        from rs_czsc import WeightBacktest

        return WeightBacktest
    except ImportError:
        try:
            from czsc.traders.weight_backtest import WeightBacktest

            return WeightBacktest
        except ImportError:
            st.error("无法导入WeightBacktest类，请检查czsc或rs_czsc库的安装")
            return None


def safe_import_top_drawdowns():
    """安全导入top_drawdowns函数"""
    try:
        from rs_czsc import top_drawdowns

        return top_drawdowns
    except ImportError:
        try:
            from czsc.utils.stats import top_drawdowns

            return top_drawdowns
        except ImportError:
            st.error("无法导入top_drawdowns函数，请检查czsc或rs_czsc库的安装")
            return None


def apply_stats_style(stats_df):
    """统一的绩效指标样式配置

    参数:
        stats_df: pd.DataFrame, 待样式化的统计数据

    返回:
        pandas.io.formats.style.Styler, 应用样式后的DataFrame

    功能增强:
        - 保留所有输入列，不删除非样式列
        - 只对已知的绩效指标列应用样式和格式化
        - 对其他列保持原样
    """
    # 定义已知的绩效指标列及其样式配置
    style_config = {
        # 正向指标（越大越好）- 使用 RdYlGn_r 配色
        "positive_indicators": {
            "columns": [
                "绝对收益",
                "年化",
                "夏普",
                "卡玛",
                "日胜率",
                "日盈亏比",
                "日赢面",
                "非零覆盖",
                "新高占比",
                "单笔收益",
                "回归年度回报率",
                "交易胜率",
                "持仓K线数",
                "与基准相关性",
                "与基准波动相关性",
            ],
            "cmap": "RdYlGn_r",
        },
        # 负向指标（越小越好）- 使用 RdYlGn 配色
        "negative_indicators": {
            "columns": ["最大回撤", "年化波动率", "下行波动率", "盈亏平衡点", "新高间隔", "回撤风险", "波动比"],
            "cmap": "RdYlGn",
        },
    }

    # 格式化配置
    format_dict = {
        # 百分比格式
        "绝对收益": "{:.2%}",
        "年化": "{:.2%}",
        "年化波动率": "{:.2%}",
        "下行波动率": "{:.2%}",
        "最大回撤": "{:.2%}",
        "日胜率": "{:.2%}",
        "日赢面": "{:.2%}",
        "非零覆盖": "{:.2%}",
        "新高占比": "{:.2%}",
        "回归年度回报率": "{:.2%}",
        "交易胜率": "{:.2%}",
        # 小数格式
        "夏普": "{:.2f}",
        "卡玛": "{:.2f}",
        "日盈亏比": "{:.2f}",
        "盈亏平衡点": "{:.2f}",
        "新高间隔": "{:.2f}",
        "回撤风险": "{:.2f}",
        "单笔收益": "{:.2f}",
        "持仓K线数": "{:.2f}",
        "多头占比": "{:.2%}",
        "空头占比": "{:.2%}",
        "与基准相关性": "{:.2f}",
        "波动比": "{:.2f}",
        "与基准波动相关性": "{:.2f}",
    }

    # 保留所有列，从原DataFrame开始应用样式
    stats_styled = stats_df.style

    # 应用正向指标样式
    for col in style_config["positive_indicators"]["columns"]:
        if col in stats_df.columns:
            stats_styled = stats_styled.background_gradient(
                cmap=style_config["positive_indicators"]["cmap"], axis=None, subset=[col]
            )

    # 应用负向指标样式
    for col in style_config["negative_indicators"]["columns"]:
        if col in stats_df.columns:
            stats_styled = stats_styled.background_gradient(
                cmap=style_config["negative_indicators"]["cmap"], axis=None, subset=[col]
            )

    # 应用格式化 - 只格式化存在的列
    format_dict_filtered = {k: v for k, v in format_dict.items() if k in stats_df.columns}
    if format_dict_filtered:
        stats_styled = stats_styled.format(format_dict_filtered)

    return stats_styled


def ensure_datetime_index(df, dt_col="dt"):
    """确保DataFrame的索引是datetime64[ns]类型"""
    if not df.index.dtype == "datetime64[ns]":
        if dt_col in df.columns:
            df[dt_col] = pd.to_datetime(df[dt_col]).astype('datetime64[ns]')
            df.set_index(dt_col, inplace=True)
        else:
            raise ValueError(f"DataFrame必须有datetime64[ns]类型的索引或包含'{dt_col}'列")

    assert df.index.dtype == "datetime64[ns]", f"index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    return df
