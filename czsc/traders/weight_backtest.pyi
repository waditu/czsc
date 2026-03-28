from collections.abc import Callable
from typing import AnyStr

from czsc.traders.base import CzscTrader

__all__ = ["get_ensemble_weight", "stoploss_by_direction"]

def get_ensemble_weight(trader: CzscTrader, method: AnyStr | Callable = "mean"): ...
def stoploss_by_direction(dfw, stoploss: float = 0.03, **kwargs): ...
