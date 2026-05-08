"""
SVC 模块的基础工具集

本模块为 ``czsc.svc`` 子包内其他可视化组件提供通用的基础设施，主要包含：

1. :func:`apply_stats_style`：为绩效统计 DataFrame 统一应用条件格式与数值格式化，
   保证不同组件展示风格一致；
2. :func:`ensure_datetime_index`：把任意可能的 dt 列规范成 ``datetime64[ns]`` 类型
   的索引，是大多数时间序列绘图函数的前置处理；
3. :func:`generate_component_key`：根据数据内容自动生成 Streamlit 组件的唯一 key，
   避免在同一页面多次调用相同组件时出现 ``duplicate widget key`` 报错。

这些工具被回测、收益、统计等多个子模块复用，需要保持稳定且向后兼容。
"""

import hashlib
import json

import pandas as pd


def apply_stats_style(stats_df):
    """统一的绩效指标样式配置

    根据预定义的"正向指标 / 负向指标"分类，对 DataFrame 中已知的绩效指标列应用
    背景色梯度（``RdYlGn`` 系列）以及格式化字符串（百分比、两位小数等），未知列
    保持原样输出。

    :param stats_df: pd.DataFrame，待样式化的绩效统计数据；不要求包含全部已知列
    :return: pandas.io.formats.style.Styler，应用样式后的 Styler 对象
    :note:
        - 保留所有输入列，不删除非样式列；
        - 只对已知的绩效指标列应用样式和格式化；
        - 对其他列保持原样，便于扩展自定义指标。
    """
    # 已知绩效指标列及其样式配置（按"越大越好""越小越好"两类区分）
    style_config = {
        # 正向指标（越大越好）：使用反转的红黄绿配色，让大值偏绿
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
        # 负向指标（越小越好）：使用正向的红黄绿配色，让小值偏绿
        "negative_indicators": {
            "columns": ["最大回撤", "年化波动率", "下行波动率", "盈亏平衡点", "新高间隔", "回撤风险", "波动比"],
            "cmap": "RdYlGn",
        },
    }

    # 数值格式化配置：分百分比与小数两类
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

    # 从原 DataFrame 构造 Styler，保留全部列
    stats_styled = stats_df.style

    # 正向指标：仅对存在的列应用反向梯度
    for col in style_config["positive_indicators"]["columns"]:
        if col in stats_df.columns:
            stats_styled = stats_styled.background_gradient(
                cmap=style_config["positive_indicators"]["cmap"], axis=None, subset=[col]
            )

    # 负向指标：仅对存在的列应用正向梯度
    for col in style_config["negative_indicators"]["columns"]:
        if col in stats_df.columns:
            stats_styled = stats_styled.background_gradient(
                cmap=style_config["negative_indicators"]["cmap"], axis=None, subset=[col]
            )

    # 仅对存在的列应用格式化字符串，避免 KeyError
    format_dict_filtered = {k: v for k, v in format_dict.items() if k in stats_df.columns}
    if format_dict_filtered:
        stats_styled = stats_styled.format(format_dict_filtered)

    return stats_styled


def ensure_datetime_index(df, dt_col="dt"):
    """确保 DataFrame 的索引是 ``datetime64[ns]`` 类型

    若索引已经是 datetime64[ns] 则原样返回；否则会尝试用 ``dt_col`` 列设置为索引，
    并强制转换为 ``datetime64[ns]``。

    :param df: pd.DataFrame，输入数据
    :param dt_col: str，作为时间索引的列名，默认 ``"dt"``
    :return: pd.DataFrame，索引为 ``datetime64[ns]`` 的 DataFrame
    :raises ValueError: 当 df 既没有 datetime64[ns] 索引也不存在 ``dt_col`` 列时
    """
    if df.index.dtype != "datetime64[ns]":
        if dt_col in df.columns:
            df[dt_col] = pd.to_datetime(df[dt_col]).astype("datetime64[ns]")
            df.set_index(dt_col, inplace=True)
        else:
            raise ValueError(f"DataFrame必须有datetime64[ns]类型的索引或包含'{dt_col}'列")

    assert df.index.dtype == "datetime64[ns]", "index必须是datetime64[ns]类型, 请先使用 pd.to_datetime 进行转换"
    return df


def generate_component_key(data, prefix="component", **kwargs):
    """根据输入数据生成唯一的组件 key

    Streamlit 在同一页面多次出现相同组件时需要不同的 key 来区分，本函数通过对
    数据内容、附加参数与高精度时间戳进行 md5 哈希，给出短而稳定的 key。

    :param data: 输入数据（``pd.DataFrame``、``Figure``、``dict``、``str`` 等）
    :param prefix: str，key 前缀，建议使用函数名缩写，便于调试
    :param kwargs: 其他影响输出的参数；会一并参与哈希
    :return: str，形如 ``"<prefix>_<8位hex>"`` 的唯一 key
    """
    import time

    key_parts = [prefix]

    if isinstance(data, pd.DataFrame):
        # DataFrame 使用 hash_pandas_object 求 sum，避免对每一行单独构造字符串
        from pandas.util import hash_pandas_object

        key_parts.append(str(hash_pandas_object(data).sum()))
    elif isinstance(data, dict):
        key_parts.append(json.dumps(data, sort_keys=True, default=str))
    else:
        key_parts.append(str(data))

    if kwargs:
        key_parts.append(json.dumps(kwargs, sort_keys=True, default=str))

    # 加入纳秒时间戳确保多次调用时绝对不重复
    timestamp = time.time_ns()
    key_parts.append(str(timestamp))

    key_str = "|".join(str(p) for p in key_parts)
    hash_value = hashlib.md5(key_str.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{hash_value}"
