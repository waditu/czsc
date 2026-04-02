from lightweight_charts import Chart
from pyecharts.charts import Boxplot as Boxplot
from pyecharts.charts import Grid
from pyecharts.charts import HeatMap as HeatMap

from czsc.core import Operate as Operate

from .ta import MACD as MACD
from .ta import SMA as SMA

def kline_pro(
    kline: list[dict],
    fx: list[dict] = [],
    bi: list[dict] = [],
    xd: list[dict] = [],
    bs: list[dict] = [],
    title: str = "缠中说禅K线分析",
    t_seq: list[int] = [],
    width: str = "1400px",
    height: str = "580px",
) -> Grid: ...
def trading_view_kline(
    kline: list[dict],
    fx: list[dict] | None = None,
    bi: list[dict] | None = None,
    xd: list[dict] | None = None,
    bs: list[dict] | None = None,
    title: str = "缠中说禅K线分析",
    t_seq: list[int] | None = None,
    **kwargs,
) -> Chart | None: ...
