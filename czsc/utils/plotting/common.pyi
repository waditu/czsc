import pandas as pd
import plotly.graph_objects as go
from _typeshed import Incomplete

COLOR_DRAWDOWN: str
COLOR_RETURN: str
COLOR_ANNO_GRAY: str
COLOR_ANNO_RED: str
COLOR_BORDER: str
COLOR_HEADER_BG: str
QUANTILES_DRAWDOWN: Incomplete
QUANTILES_DRAWDOWN_ANALYSIS: Incomplete
SIGMA_LEVELS: Incomplete
MONTH_LABELS: Incomplete
TemplateType: Incomplete

def figure_to_html(fig: go.Figure, to_html: bool = False, include_plotlyjs: bool = True) -> go.Figure | str: ...
def add_year_boundary_lines(
    fig: go.Figure,
    dates: pd.DatetimeIndex,
    row: int | None = None,
    col: int | None = None,
    line_color: str = "red",
    opacity: float = 0.3,
    line_dash: str = "dash",
) -> None: ...
