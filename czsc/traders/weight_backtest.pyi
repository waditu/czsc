from czsc.traders.base import CzscTrader
from typing import AnyStr, Callable

__all__ = ['get_ensemble_weight', 'stoploss_by_direction']

def get_ensemble_weight(trader: CzscTrader, method: AnyStr | Callable = 'mean'): ...
def stoploss_by_direction(dfw, stoploss: float = 0.03, **kwargs): ...
