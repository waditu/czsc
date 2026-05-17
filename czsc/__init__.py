"""CZSC（缠中说禅）量化分析框架——顶层包入口。

按 spec §3.1，所有公共 API 在导入期一次性 import；不再使用 PEP 562 lazy loading。
- ``czsc._native``：Rust 扩展（PyO3），提供缠论核心类型、信号、交易器、TA 算子。
- ``czsc.{connectors,traders,utils,fsa,aphorism,mock,envs}``：Python 子包。
- ``czsc.{ema,sma,...,ultimate_smoother,...}``：Rust TA 算子的顶层别名。
- ``czsc.{WeightBacktest,daily_performance,top_drawdowns}``：来自硬依赖 ``wbt``。

作者: zengbin93 <zeng_bin8888@163.com>，创建于 2019/10/29。
"""

# isort: skip_file
# 顶层包的 import 顺序经过手工设计以处理子包间的循环依赖，
# 不要让 isort/ruff 重排——会触发 partially-initialized module 错误。

# 第一批：纯薄壳子包（不会回头 import czsc 顶层符号）。
# fsa/aphorism/mock 中含 ``from czsc import top_drawdowns`` 等回环 import，
# 必须放到 wbt / .traders / .utils 之后再加载，避免循环 import。
from . import _native as _native  # noqa: F401  # 通过 czsc._native.* 暴露
from . import connectors, envs, traders, utils

# === 缠论核心数据类型与算法（来自 Rust 扩展 czsc._native）===
# === wbt（硬依赖，提供回测/绩效组件）===
from wbt import WeightBacktest, daily_performance, top_drawdowns

# format_standard_kline: Python 适配层，把 DataFrame -> List[RawBar]（详见模块 docstring）
from czsc._format_standard_kline import format_standard_kline

# === 之前的 lazy 属性，改为静态 import（spec §3.1 移除 lazy loading）===
from czsc.utils.kline_quality import check_kline_quality
from czsc.utils.log import log_strategy_info
from czsc.utils.trade import adjust_holding_weights
from czsc.utils.warning_capture import capture_warnings, execute_with_warning_capture

# 第二批：会回头 import czsc 顶层符号（如 ``from czsc import top_drawdowns``）的重型子包。
# 必须放在所有顶层符号都已经绑定之后，否则会触发 partially-initialized module 循环 import。
from . import aphorism, fsa, mock
from ._native import (
    BI,
    CZSC,
    FX,
    ZS,
    BarGenerator,
    Direction,
    Event,
    FakeBI,
    Freq,
    Mark,
    NewBar,
    Operate,
    ParsedSignalDoc,
    Position,
    RawBar,
    Signal,
    boll_positions,
    check_bi,
    check_fx,
    check_fxs,
    ema,
    freq_end_time,
    is_trading_time,
    parse_signal_doc,
    remove_include,
    rolling_rank,
    sma,
    ultimate_smoother,
)

# === EDA 工具（来自 czsc.eda）===
from .eda import (
    mark_cta_periods,
    mark_volatility,
    monotonicity,
)

# === 研究/优化入口（czsc.research，Rust 后端）===
from .research import (
    build_exit_optim_positions,
    build_open_optim_positions,
    run_optimize_batch,
    run_replay,
    run_research,
)

# === 策略门面（czsc.strategies；Python 层对 Rust Trader 的薄封装）===
from .strategies import CzscJsonStrategy, CzscStrategyBase

# === 交易器与信号管理 API（czsc.traders）===
from .traders import (
    CzscSignals,
    CzscTrader,
    derive_signals_config,
    derive_signals_freqs,
    generate_czsc_signals,
    get_signals_config,
    get_signals_freqs,
    get_unique_signals,
)

# === 通用工具函数（czsc.utils）===
from .utils import (
    DataClient,
    DiskCache,
    clear_cache,
    clear_expired_cache,
    code_namespace,
    cross_sectional_ic,
    dill_dump,
    dill_load,
    disk_cache,
    empty_cache_path,
    freqs_sorted,
    get_dir_size,
    get_py_namespace,
    get_url_token,
    home_path,
    import_by_name,
    index_composition,
    print_df_sample,
    psi,
    read_json,
    resample_to_daily,
    risk_free_returns,
    save_json,
    set_url_token,
    to_arrow,
    update_bbars,
    update_nxb,
    update_tbars,
)

# === 包元信息 ===
# 版本号唯一来源是 Cargo.toml [workspace.package].version；maturin 在打 wheel
# 时把它写进 dist-info，这里通过 importlib.metadata 反查，杜绝硬编码漂移。
# 本文件顶部 `# isort: skip_file` 禁止重排，importlib.metadata 必须放在
# 前面 from . import _native 等 import 之后，因此带 noqa: E402 抑制。
from importlib.metadata import PackageNotFoundError as _PackageNotFoundError  # noqa: E402
from importlib.metadata import version as _pkg_version  # noqa: E402

try:
    __version__ = _pkg_version("czsc")
except _PackageNotFoundError:
    # 未安装（如直接从源码 tree 运行）时退化为占位值，避免 import 失败
    __version__ = "0.0.0+unknown"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20260507"

# === 公共 API 契约 ===
# 修改本列表等价于修改公共契约；新增/移除符号必须在 release notes 与 MIGRATION_NOTES 中说明。
__all__ = [
    # 缠论核心
    "BI",
    "CZSC",
    "FX",
    "ZS",
    "BarGenerator",
    "Direction",
    "Event",
    "FakeBI",
    "Freq",
    "Mark",
    "NewBar",
    "Operate",
    "ParsedSignalDoc",
    "Position",
    "RawBar",
    "Signal",
    "boll_positions",
    "check_bi",
    "check_fx",
    "check_fxs",
    "ema",
    "format_standard_kline",
    "freq_end_time",
    "is_trading_time",
    "parse_signal_doc",
    "remove_include",
    "rolling_rank",
    "sma",
    "ultimate_smoother",
    # 来自 wbt
    "WeightBacktest",
    "daily_performance",
    "top_drawdowns",
    # 始终预加载的子包
    "connectors",
    "envs",
    "traders",
    "utils",
    "fsa",
    "aphorism",
    "mock",
    # 交易器 / 信号 API
    "CzscSignals",
    "CzscTrader",
    "derive_signals_config",
    "derive_signals_freqs",
    "generate_czsc_signals",
    "get_signals_config",
    "get_signals_freqs",
    "get_unique_signals",
    # 策略门面
    "CzscStrategyBase",
    "CzscJsonStrategy",
    # 研究/优化入口
    "build_exit_optim_positions",
    "build_open_optim_positions",
    "run_optimize_batch",
    "run_replay",
    "run_research",
    # 通用工具
    "DataClient",
    "DiskCache",
    "clear_cache",
    "clear_expired_cache",
    "code_namespace",
    "cross_sectional_ic",
    "dill_dump",
    "dill_load",
    "disk_cache",
    "empty_cache_path",
    "freqs_sorted",
    "get_dir_size",
    "get_py_namespace",
    "get_url_token",
    "home_path",
    "import_by_name",
    "index_composition",
    "print_df_sample",
    "psi",
    "read_json",
    "resample_to_daily",
    "risk_free_returns",
    "save_json",
    "set_url_token",
    "to_arrow",
    "update_bbars",
    "update_nxb",
    "update_tbars",
    # 静态 import 的高频符号（曾经走 _LAZY_ATTRS）
    "capture_warnings",
    "execute_with_warning_capture",
    "adjust_holding_weights",
    "log_strategy_info",
    "check_kline_quality",
    # EDA
    "monotonicity",
    "mark_cta_periods",
    "mark_volatility",
    # 元信息
    "__version__",
    "__author__",
    "__email__",
    "__date__",
    "welcome",
]


def welcome():
    """打印 CZSC 版本号、随机格言与缓存目录提示，用于 CLI/交互式环境。"""
    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()
    print(f"CZSC环境变量：czsc_min_bi_len = {envs.get_min_bi_len()}; czsc_max_bi_num = {envs.get_max_bi_num()}; ")
    # 1 GiB 阈值：超出即提示用户主动清理，避免缓存目录无限膨胀。
    if get_dir_size(home_path) > pow(1024, 3):
        print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")
