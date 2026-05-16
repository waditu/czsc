"""lightweight_charts 渲染层用到的颜色 / 主题常量。

颜色取值与项目内 Plotly 版 ``czsc.utils.plotting.kline.KlineChart`` 对齐，避免两套
路径在视觉上出现"红绿互换"等迷惑性差异。
"""

from __future__ import annotations

from typing import Literal, TypedDict

ThemeName = Literal["light", "dark"]


class ThemeColors(TypedDict):
    background: str
    text: str
    grid: str
    up: str         # 阳线 / 多头
    down: str       # 阴线 / 空头
    sma5: str
    sma20: str
    fx_dashed: str  # 分型连线（虚线）
    bi: str         # 笔折线（实线）
    bi_active: str  # tab 激活状态色
    macd_diff: str
    macd_dea: str


THEMES: dict[ThemeName, ThemeColors] = {
    # Quant Almanac · 量化年鉴：暖纸色调，refined 红绿，cobalt 笔色
    "light": {
        "background": "#FBF9F4",   # warm paper
        "text": "#1A1A17",         # warm near-black
        "grid": "#E8E2D4",         # 沙色分隔线
        "up": "#C03A2B",           # 沉敛的中国红
        "down": "#2E7D32",         # 沉敛的森林绿
        "sma5": "#C78A2E",         # 古铜
        "sma20": "#2D6A8C",        # 钢蓝
        "fx_dashed": "#8B7E5E",    # 卡其虚线
        "bi": "#1F3C6E",           # 深靛蓝实线
        "bi_active": "#1F3C6E",
        "macd_diff": "#1F3C6E",
        "macd_dea": "#C78A2E",
    },
    # Deep Cosmos：深空配色，paper-white 文字
    "dark": {
        "background": "#0E1116",
        "text": "#EFEBE0",
        "grid": "#1F242E",
        "up": "#E94B3C",
        "down": "#5BB85B",
        "sma5": "#E6A93B",
        "sma20": "#6EB6E4",
        "fx_dashed": "#8B8678",
        "bi": "#A8B8E8",
        "bi_active": "#A8B8E8",
        "macd_diff": "#A8B8E8",
        "macd_dea": "#E6A93B",
    },
}


def get_theme(name: ThemeName = "light") -> ThemeColors:
    if name not in THEMES:
        raise ValueError(f"unknown theme: {name!r}; expected one of {list(THEMES)}")
    return THEMES[name]
