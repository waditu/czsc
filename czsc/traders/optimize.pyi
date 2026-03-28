from collections.abc import Callable
from typing import AnyStr

from _typeshed import Incomplete

from czsc.core import Event as Event
from czsc.core import Position as Position
from czsc.core import Signal as Signal
from czsc.strategies import CzscStrategyBase as CzscStrategyBase

class CzscOpenOptimStrategy(CzscStrategyBase):
    @staticmethod
    def update_beta_opens(beta: Position, open_signals_all: list[AnyStr] | AnyStr): ...
    @property
    def positions(self): ...

class CzscExitOptimStrategy(CzscStrategyBase):
    @staticmethod
    def update_beta_exits(beta: Position, event_dict: dict, mode: str = "replace"): ...
    @property
    def positions(self): ...

def one_symbol_optim(symbol, read_bars: Callable, path: str, **kwargs): ...
def one_position_stats(path, pos_name): ...

class OpensOptimize:
    version: str
    symbols: Incomplete
    read_bars: Incomplete
    kwargs: Incomplete
    task_name: Incomplete
    candidate_signals: Incomplete
    task_hash: Incomplete
    poss_path: Incomplete
    results_path: Incomplete
    def __init__(self, read_bars: Callable, **kwargs) -> None: ...
    def execute(self, n_jobs: int = 1) -> None: ...

class ExitsOptimize:
    version: str
    symbols: Incomplete
    read_bars: Incomplete
    kwargs: Incomplete
    task_name: Incomplete
    candidate_events: Incomplete
    task_hash: Incomplete
    poss_path: Incomplete
    results_path: Incomplete
    def __init__(self, read_bars: Callable, **kwargs) -> None: ...
    def execute(self, n_jobs: int = 1) -> None: ...
