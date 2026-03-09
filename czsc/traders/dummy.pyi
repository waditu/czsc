from _typeshed import Incomplete
from czsc.traders.base import generate_czsc_signals as generate_czsc_signals

class DummyBacktest:
    strategy: Incomplete
    results_path: Incomplete
    signals_path: Incomplete
    poss_path: Incomplete
    read_bars: Incomplete
    kwargs: Incomplete
    sdt: Incomplete
    edt: Incomplete
    bars_sdt: Incomplete
    def __init__(self, strategy, signals_path, results_path, read_bars, **kwargs) -> None: ...
    def replay(self, symbol) -> None: ...
    def one_symbol_dummy(self, symbol) -> None: ...
    def one_pos_stats(self, pos_name): ...
    def execute(self, symbols, n_jobs: int = 2, **kwargs) -> None: ...
