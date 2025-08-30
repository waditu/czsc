"""
工具类组件

包含代码编辑器等辅助功能
"""
import sys
import streamlit as st


def streamlit_run(file, port=8501, host="localhost"):
    """
    直接启动 Streamlit 应用，添加运行时检查
    """
    from loguru import logger
    from streamlit.web import cli as stcli

    logger.info("streamlit_run -- 启动 Streamlit 应用...")
    logger.info(f"UI 文件路径: {file}")

    # 使用 streamlit.web.cli.main
    sys.argv = [
        "streamlit", 
        "run", 
        str(file),
        "--server.port", str(port),
        "--server.address", host,
        "--server.headless", "true"
    ]

    stcli.main()
