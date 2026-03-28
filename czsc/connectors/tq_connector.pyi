from _typeshed import Incomplete
from tqsdk import (
    BacktestFinished as BacktestFinished,
)
from tqsdk import (
    TqAccount as TqAccount,
)
from tqsdk import (
    TqApi,
)
from tqsdk import (
    TqBacktest as TqBacktest,
)
from tqsdk import (
    TqKq as TqKq,
)
from tqsdk import (
    TqSim as TqSim,
)

from czsc import Freq as Freq
from czsc import RawBar as RawBar

def format_kline(df, freq=...): ...
def is_trading_end(): ...
def create_symbol_trader(api: TqApi, symbol, **kwargs): ...

symbols: Incomplete
future_name_map: Incomplete

def get_symbols(**kwargs): ...
def get_raw_bars(symbol, freq, sdt, edt, fq: str = "前复权", **kwargs): ...
def get_daily_backup(api: TqApi, **kwargs): ...
def is_trade_time(quote, **kwargs): ...
def adjust_portfolio(api: TqApi, portfolio, account=None, **kwargs): ...
