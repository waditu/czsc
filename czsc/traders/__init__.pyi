from czsc.traders.base import (
    CzscSignals as CzscSignals,
)
from czsc.traders.base import (
    CzscTrader as CzscTrader,
)
from czsc.traders.base import (
    check_signals_acc as check_signals_acc,
)
from czsc.traders.base import (
    generate_czsc_signals as generate_czsc_signals,
)
from czsc.traders.base import (
    get_unique_signals as get_unique_signals,
)
from czsc.traders.dummy import DummyBacktest as DummyBacktest
from czsc.traders.performance import (
    PairsPerformance as PairsPerformance,
)
from czsc.traders.performance import (
    combine_dates_and_pairs as combine_dates_and_pairs,
)
from czsc.traders.performance import (
    combine_holds_and_pairs as combine_holds_and_pairs,
)
from czsc.traders.sig_parse import (
    SignalsParser as SignalsParser,
)
from czsc.traders.sig_parse import (
    get_signals_config as get_signals_config,
)
from czsc.traders.sig_parse import (
    get_signals_freqs as get_signals_freqs,
)
from czsc.traders.weight_backtest import (
    get_ensemble_weight as get_ensemble_weight,
)
from czsc.traders.weight_backtest import (
    stoploss_by_direction as stoploss_by_direction,
)

def __getattr__(name): ...
