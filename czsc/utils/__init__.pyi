import pandas as pd
from _typeshed import Incomplete

from . import analysis as analysis
from . import crypto as crypto
from . import data as data
from . import io as io
from . import ta as ta
from .analysis import (
    cross_sectional_ic as cross_sectional_ic,
)
from .analysis import (
    daily_performance as daily_performance,
)
from .analysis import (
    holds_performance as holds_performance,
)
from .analysis import (
    nmi_matrix as nmi_matrix,
)
from .analysis import (
    overlap as overlap,
)
from .analysis import (
    psi as psi,
)
from .analysis import (
    rolling_daily_performance as rolling_daily_performance,
)
from .analysis import (
    single_linear as single_linear,
)
from .analysis import (
    top_drawdowns as top_drawdowns,
)
from .cross import cross_sectional_ranker as cross_sectional_ranker
from .crypto import (
    fernet_decrypt as fernet_decrypt,
)
from .crypto import (
    fernet_encrypt as fernet_encrypt,
)
from .crypto import (
    generate_fernet_key as generate_fernet_key,
)
from .data import (
    DataClient as DataClient,
)
from .data import (
    DiskCache as DiskCache,
)
from .data import (
    clear_cache as clear_cache,
)
from .data import (
    clear_expired_cache as clear_expired_cache,
)
from .data import (
    disk_cache as disk_cache,
)
from .data import (
    empty_cache_path as empty_cache_path,
)
from .data import (
    get_dir_size as get_dir_size,
)
from .data import (
    get_url_token as get_url_token,
)
from .data import (
    home_path as home_path,
)
from .data import (
    set_url_token as set_url_token,
)
from .index_composition import index_composition as index_composition
from .io import dill_dump as dill_dump
from .io import dill_load as dill_load
from .io import read_json as read_json
from .io import save_json as save_json
from .oss import AliyunOSS as AliyunOSS
from .plotting.kline import KlineChart as KlineChart
from .plotting.kline import plot_czsc_chart as plot_czsc_chart
from .trade import (
    resample_to_daily as resample_to_daily,
)
from .trade import (
    risk_free_returns as risk_free_returns,
)
from .trade import (
    update_bbars as update_bbars,
)
from .trade import (
    update_nxb as update_nxb,
)
from .trade import (
    update_tbars as update_tbars,
)

sorted_freqs: Incomplete

def x_round(x: float | int, digit: int = 4) -> float | int: ...
def get_py_namespace(file_py: str, keys: list = []) -> dict: ...
def code_namespace(code: str, keys: list = []) -> dict: ...
def import_by_name(name): ...
def freqs_sorted(freqs): ...
def create_grid_params(prefix: str = "", multiply: int = 3, **kwargs) -> dict: ...
def print_df_sample(df, n: int = 5) -> None: ...
def mac_address(): ...
def to_arrow(df: pd.DataFrame): ...
def timeout_decorator(timeout): ...
def __getattr__(name): ...
