# -*- coding: utf-8 -*-
"""
表单相关的 Streamlit 组件

包含各种用户输入表单和交互组件
"""

import numpy as np
import pandas as pd
import streamlit as st


def weight_backtest_form():
    """创建权重回测用户输入表单"""
    file = st.file_uploader("上传文件", type=["csv", "feather"], accept_multiple_files=False)
    if not file:
        st.warning("请上传文件")
        st.stop()

    if file.name.endswith(".csv"):
        df = pd.read_csv(file)
    elif file.name.endswith(".feather"):
        df = pd.read_feather(file)
    else:
        raise ValueError(f"不支持的文件类型: {file.name}")

    symbols = df["symbol"].unique()
    with st.form(key="my_form"):
        sel_symbols = st.multiselect("选择品种", symbols, default=symbols)
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        fee = c1.number_input("单边费率（BP）", value=2.0, step=0.1, min_value=-100.0, max_value=100.0)
        digits = c2.number_input("小数位数", value=2, step=1, min_value=0, max_value=10)
        delay = c3.number_input("延迟执行", value=0, step=1, min_value=0, max_value=100, help="测试策略对执行是否敏感")
        only_direction = c4.selectbox("按方向测试", [False, True], index=0)
        submit_button = st.form_submit_button(label="开始测试")

    if not submit_button:
        st.warning("请选择品种和参数")
        st.stop()

    df = df[df["symbol"].isin(sel_symbols)].copy().reset_index(drop=True)
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["symbol", "dt"]).reset_index(drop=True)

    if delay > 0:
        for _, dfg in df.groupby("symbol"):
            df.loc[dfg.index, "weight"] = dfg["weight"].shift(delay).fillna(0)

    if only_direction:
        df["weight"] = np.sign(df["weight"])

    return df, fee, digits


def code_editor_form(text: str = "", **kwargs):
    """展示代码编辑器

    :param text: str, 初始代码文本
    :param kwargs:
        - language: str, 编程语言，默认为 'python'
        - theme: str, 主题，默认为 'monokai'
        - key: str, 组件的唯一标识符
        - height: int, 编辑器高度，默认为 400
        - auto_update: bool, 是否自动更新，默认为 False
        - wrap: bool, 是否自动换行，默认为 False
        - font_size: int, 字体大小，默认为 14
    """
    try:
        from streamlit_ace import st_ace
    except ImportError:
        st.error("请先安装 streamlit-ace: pip install streamlit-ace")
        return None

    language = kwargs.get("language", "python")
    theme = kwargs.get("theme", "monokai")
    key = kwargs.get("key", "code_editor")
    height = kwargs.get("height", 400)
    auto_update = kwargs.get("auto_update", False)
    wrap = kwargs.get("wrap", False)
    font_size = kwargs.get("font_size", 14)

    content = st_ace(
        value=text,
        language=language,
        theme=theme,
        key=key,
        height=height,
        auto_update=auto_update,
        wrap=wrap,
        font_size=font_size,
    )

    return content 

