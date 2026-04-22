import pandas as pd

from .base import (
    apply_stats_style as apply_stats_style,
)
from .base import (
    ensure_datetime_index as ensure_datetime_index,
)
from .base import (
    generate_component_key as generate_component_key,
)

def show_daily_return(df: pd.DataFrame, key=None, **kwargs): ...
def show_cumulative_returns(df, key=None, **kwargs) -> None: ...
def show_monthly_return(df, ret_col: str = "total", sub_title: str = "月度累计收益", **kwargs): ...
def show_drawdowns(df: pd.DataFrame, ret_col, key=None, **kwargs): ...
def show_rolling_daily_performance(df, ret_col, key=None, **kwargs) -> None: ...
