"""
工具类组件

包含代码编辑器等辅助功能
"""

import streamlit as st


def show_code_editor(text: str = "", **kwargs):
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