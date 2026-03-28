import pandas as pd

from czsc.core import CZSC as CZSC
from czsc.core import RawBar as RawBar

def calculate_bi_info(bars: list[RawBar], **kwargs) -> pd.DataFrame: ...
def symbols_bi_infos(
    symbols, read_bars, freq: str = "5分钟", sdt: str = "20130101", edt: str = "20190101", **kwargs
) -> pd.DataFrame: ...
