import pandas as pd
from _typeshed import Incomplete
from typing import Any

class StrategyCard:
    dfw: Incomplete
    strategy_name: Incomplete
    show_recent_detail: Incomplete
    wb: Incomplete
    out_sample_sdt: Incomplete
    describe: Incomplete
    latest_weights: Incomplete
    def __init__(self, strategy_name: str, dfw: pd.DataFrame, out_sample_sdt: str = '20250101', describe: str = '', show_recent_detail: bool = True, **kwargs) -> None: ...
    def build(self) -> dict[str, Any]: ...

def push_strategy_latest(strategy: str, dfw: pd.DataFrame, feishu_key: str, out_sample_sdt: str = '20250101', show_recent_detail: bool = True, **kwargs): ...
def test_push_strategy_latest() -> None: ...
