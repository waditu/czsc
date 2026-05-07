"""
CZSC（缠中说禅）量化分析框架的顶层包入口模块

职责：
    1. 统一对外暴露公共 API（缠论核心类、信号、交易器、策略、回测工具等）
    2. 完成 Rust 后端（czsc._native，由 PyO3 编译而来）与 Python 适配层之间的桥接
    3. 维护 ``__all__`` 公共契约，保证 ``from czsc import *`` 行为可控
    4. 通过模块级 ``__getattr__`` 提供按需加载（懒加载）的子模块与符号
       —— 仅在首次访问时才执行 ``importlib.import_module``，可显著降低冷启动耗时
       同时避免循环依赖

约定：
    - 所有以单下划线开头的对象（如 ``_sys``、``_LAZY_MODULES``）均为模块内部使用，
      不属于公共 API，禁止外部直接依赖
    - ``czsc.ta``、``czsc.CZSC`` 等高频符号优先来自 Rust 实现，性能更佳
    - 升级 Rust 版本时需同步检查 ``__all__`` 与本模块导入区，确保契约一致

作者: zengbin93
邮箱: zeng_bin8888@163.com
创建时间: 2019/10/29 15:01
"""

import sys as _sys

# 子包按"始终需要 / 启动期可加载"为标准统一引入：
# - _native: PyO3 编译的 Rust 扩展，缠论核心实现位于此
# - connectors/envs/sensors/signals/traders/utils: 业务层模块，多数函数会被立即用到
# 这些子包必须立即加载，因下方的 from ... import 语句直接依赖它们
from . import _native, connectors, envs, sensors, signals, traders, utils

# === Rust 扩展的 ta 命名空间桥接 ===
# 让 ``czsc.ta.*`` 直接来自 Rust 扩展（czsc._native.ta），不再使用 Python 包装层。
# 通过同时设置模块属性与 ``sys.modules``，保证以下两种导入方式都能命中 Rust 实现：
#     import czsc.ta            # 解析为 czsc._native.ta
#     from czsc.ta import ema   # 解析为 czsc._native.ta.ema
# 注意：在文件下方 ``from .utils import ...`` 之后还会重新赋值一次，避免
# 旧版包装模块在导入链上覆盖此处别名（见后文"重新应用 czsc.ta 别名"段）。
ta = _native.ta
_sys.modules["czsc.ta"] = _native.ta

# === 缠论核心数据类型与算法（来自 Rust 扩展） ===
# 这些符号是 CZSC 公共 API 的"硬契约"，在大量业务代码与下游项目中被直接 import。
# 命名与原 Python 实现保持一致，便于无缝迁移。各类型的语义：
#   BI  - 笔（缠论中由分型连接形成的最小走势单元）
#   CZSC - 缠论分析器主类，承载分型/笔/线段的识别管线
#   FX  - 分型（顶分型 / 底分型）
#   ZS  - 中枢（多笔重叠形成的盘整区间）
#   BarGenerator - K 线合成器，用于多周期联立
#   Direction/Mark/Operate - 方向/标记/操作枚举
#   Event/Signal/Position - 事件、信号、持仓三件套
#   ParsedSignalDoc - 信号文档解析结果
#   FakeBI/NewBar/RawBar - K 线及其衍生抽象（原始/合成/虚拟笔）
# 工具函数：
#   boll_positions/ema/sma/ultimate_smoother/rolling_rank - 技术指标
#   check_bi/check_fx/check_fxs/remove_include - 缠论结构校验
#   freq_end_time/is_trading_time - 周期与交易时段判定
#   parse_signal_doc - 信号声明字符串解析
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

# === format_standard_kline 的 Python 包装 ===
# Rust 扩展仅提供一个直通桩（``Vec<RawBar> -> Vec<RawBar>``），无法直接接受
# pandas DataFrame。但下游用户期望的签名是 ``DataFrame + Freq -> List[RawBar]``。
# 因此 ``czsc/_format_standard_kline.py`` 是一个 Python 适配层，逐行通过
# PyO3 构造器创建 RawBar 实例，签名与 rs-czsc 提供的 Python 端 API 完全一致。
# 这样既保留了"用户传 DataFrame 即可"的便利性，又复用了 Rust 端的内存布局与类型校验。
from czsc._format_standard_kline import format_standard_kline

# === 回测引擎（来自第三方包 wbt） ===
# WeightBacktest    - 基于权重序列的向量化回测器
# daily_performance - 日度绩效统计（年化、夏普、最大回撤等）
# top_drawdowns     - 提取前 N 大回撤区间，用于风险归因分析
from wbt import WeightBacktest, daily_performance, top_drawdowns

from typing import TYPE_CHECKING

# === 探索性数据分析（EDA）相关函数 ===
# 这些工具函数用于因子研究、特征工程与轻量级策略评估，
# 在多数交易研究流程中是高频使用项，因此选择在导入期就一并暴露：
#   cal_symbols_factor / cal_trade_price - 多品种因子计算与交易价归一化
#   cal_yearly_days                       - 计算年化基准日数（区分 A 股/期货/数字货币）
#   cross_sectional_strategy              - 横截面排序策略
#   dif_long_bear / sma_long_bear         - 多/空趋势判定
#   limit_leverage                        - 杠杆约束
#   make_price_features                   - 价格类特征工厂
#   mark_cta_periods / mark_volatility    - CTA 区间与波动率分段
#   min_max_limit                         - 数值裁剪
#   monotonicity                          - 单调性检验
#   remove_beta_effects                   - 去除 Beta 系统性影响
#   rolling_layers                        - 分层回看
#   tsf_type                              - 时序特征类别标注
#   turnover_rate                         - 换手率统计
#   twap / vwap                           - 时间/成交量加权均价
#   unify_weights / weights_simple_ensemble - 权重归一与简单集成
from .eda import (
    cal_symbols_factor,
    cal_trade_price,
    cal_yearly_days,
    cross_sectional_strategy,
    dif_long_bear,
    limit_leverage,
    make_price_features,
    mark_cta_periods,
    mark_volatility,
    min_max_limit,
    monotonicity,
    remove_beta_effects,
    rolling_layers,
    sma_long_bear,
    tsf_type,
    turnover_rate,
    twap,
    unify_weights,
    vwap,
    weights_simple_ensemble,
)

# 仅在类型检查阶段（如 mypy / pyright / IDE 静态分析）暴露这些懒加载子模块，
# 运行期它们会经由下方的 ``__getattr__`` 按需导入。这种写法既能让静态工具
# 正确解析 ``czsc.svc`` 等用法，又不会在导入 czsc 时就把这些重量级子包
# （例如 svc 依赖 plotly/streamlit）拉起来。
if TYPE_CHECKING:
    from . import aphorism, fsa, mock, svc

# === 策略门面（Facade） ===
# strategies.py 是 Python 端的薄封装：在 Rust 实现的 Trader 基础上，提供
# CzscStrategyBase（策略开发抽象基类）与 CzscJsonStrategy（JSON 配置式策略），
# 隔离用户层 API 与底层 Rust 类型，便于策略快速搭建与序列化。
from .strategies import CzscJsonStrategy, CzscStrategyBase

# === 交易器与信号管理 API ===
# traders 子包对外暴露的统一入口，由 Rust 后端驱动：
#   CzscSignals/CzscTrader - 多周期信号合成与交易调度核心
#   SignalsParser          - 信号声明字符串解析器
#   derive_signals_*       - 从持仓/事件反推所需信号配置或周期集合
#   generate_czsc_signals  - 标准化信号生成入口
#   get_signals_*          - 信号配置/周期获取辅助函数
#   get_unique_signals     - 信号去重工具，回测前置预处理常用
from .traders import (
    CzscSignals,
    CzscTrader,
    SignalsParser,
    derive_signals_config,
    derive_signals_freqs,
    generate_czsc_signals,
    get_signals_config,
    get_signals_freqs,
    get_unique_signals,
)

# === 研究/优化入口（research.py，Rust 后端） ===
# 这些函数是策略研究流程的主入口，封装了"参数批量回测""开仓/平仓优化""复盘"
# 等高层操作，对应 czsc/research.py 中的统一研究 API：
#   build_open_optim_positions  - 构造开仓参数优化所需的 Position 列表
#   build_exit_optim_positions  - 构造平仓参数优化所需的 Position 列表
#   run_optimize_batch          - 多参数组合批量优化
#   run_replay                  - 单标的回放
#   run_research                - 顶层一键式研究流水线
from .research import (
    build_exit_optim_positions,
    build_open_optim_positions,
    run_optimize_batch,
    run_replay,
    run_research,
)

# === 通用工具函数集合（czsc.utils） ===
# 这些工具按使用频率从 czsc.utils 中提升至顶级命名空间，便于直接 ``czsc.xxx`` 调用。
# 主要分组：
#   - 缓存类：DiskCache / disk_cache / clear_cache / clear_expired_cache /
#             empty_cache_path / get_dir_size / home_path
#   - 数据源/IO：DataClient / AliyunOSS / read_json / save_json / to_arrow
#   - 加解密：fernet_encrypt / fernet_decrypt / generate_fernet_key /
#             get_url_token / set_url_token
#   - 序列化：dill_dump / dill_load
#   - 时间/周期：freqs_sorted / resample_to_daily
#   - 命名空间/反射：code_namespace / get_py_namespace / import_by_name
#   - 绩效统计：cross_sectional_ic / holds_performance /
#               rolling_daily_performance / risk_free_returns
#   - 调试：print_df_sample / mac_address / x_round
#   - PSI：psi（群体稳定性指数）
#   - 网格/装饰器：create_grid_params / timeout_decorator
#   - 指标增量更新：update_bbars / update_nxb / update_tbars
#   - 指数成分：index_composition
from .utils import (
    AliyunOSS,
    DataClient,
    DiskCache,
    clear_cache,
    clear_expired_cache,
    code_namespace,
    create_grid_params,
    cross_sectional_ic,
    dill_dump,
    dill_load,
    disk_cache,
    empty_cache_path,
    fernet_decrypt,
    fernet_encrypt,
    freqs_sorted,
    generate_fernet_key,
    get_dir_size,
    get_py_namespace,
    get_url_token,
    holds_performance,
    home_path,
    import_by_name,
    index_composition,
    mac_address,
    print_df_sample,
    psi,
    read_json,
    resample_to_daily,
    risk_free_returns,
    rolling_daily_performance,
    save_json,
    set_url_token,
    timeout_decorator,
    to_arrow,
    update_bbars,
    update_nxb,
    update_tbars,
    x_round,
)

# === 重新应用 czsc.ta 别名（关键步骤，勿删） ===
# 必须在 ``from .utils import ...`` 之后再次执行一次 czsc.ta 的别名绑定，
# 原因：旧版 utils 模块在导入链上可能间接触发 ``czsc.utils.ta`` 子模块的
# 副作用导入，从而将 sys.modules['czsc.ta'] 指向 Python 包装版本，覆盖
# 文件顶部设置的 Rust 版本。这里再绑定一次确保 Rust 实现胜出。
ta = _native.ta
_sys.modules["czsc.ta"] = _native.ta

# === 公共 API 契约 ===
# ``__all__`` 显式声明 ``from czsc import *`` 行为暴露的符号集合。
# 维护规则：
#   1. 任何顶级 import 中出现的公共符号都需登记于此（按主题分组排列）
#   2. 私有符号（单下划线开头）禁止登记
#   3. 修改本列表等价于修改公共契约，必须在 CHANGELOG / 迁移指南中说明
__all__ = [
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
    # —— 来自 wbt 的回测组件 ——
    "WeightBacktest",
    "daily_performance",
    "top_drawdowns",
    # —— 始终预先加载的子包 ——
    "connectors",
    "envs",
    "sensors",
    "signals",
    "traders",
    "utils",
    # —— 交易器 API（czsc/traders/__init__.py，Rust 后端实现） ——
    "CzscSignals",
    "CzscTrader",
    "SignalsParser",
    "derive_signals_config",
    "derive_signals_freqs",
    "generate_czsc_signals",
    "get_signals_config",
    "get_signals_freqs",
    "get_unique_signals",
    # —— 策略门面（czsc/strategies.py，Python 层对 Rust Trader 的封装） ——
    "CzscStrategyBase",
    "CzscJsonStrategy",
    # —— 研究/优化入口（czsc/research.py，Rust 后端） ——
    "build_exit_optim_positions",
    "build_open_optim_positions",
    "run_optimize_batch",
    "run_replay",
    "run_research",
    # —— 通用工具（来自 czsc/utils） ——
    "AliyunOSS",
    "DataClient",
    "DiskCache",
    "clear_cache",
    "clear_expired_cache",
    "code_namespace",
    "create_grid_params",
    "cross_sectional_ic",
    "dill_dump",
    "dill_load",
    "disk_cache",
    "empty_cache_path",
    "fernet_decrypt",
    "fernet_encrypt",
    "freqs_sorted",
    "generate_fernet_key",
    "get_dir_size",
    "get_py_namespace",
    "get_url_token",
    "holds_performance",
    "home_path",
    "import_by_name",
    "index_composition",
    "mac_address",
    "print_df_sample",
    "psi",
    "read_json",
    "resample_to_daily",
    "risk_free_returns",
    "rolling_daily_performance",
    "save_json",
    "set_url_token",
    "ta",
    "timeout_decorator",
    "to_arrow",
    "update_bbars",
    "update_nxb",
    "update_tbars",
    "x_round",
    "svc",
    "fsa",
    "aphorism",
    "mock",
    "capture_warnings",
    "execute_with_warning_capture",
    "adjust_holding_weights",
    "log_strategy_info",
    "plot_czsc_chart",
    "KlineChart",
    "check_kline_quality",
    "remove_beta_effects",
    "vwap",
    "twap",
    "cross_sectional_strategy",
    "monotonicity",
    "min_max_limit",
    "rolling_layers",
    "cal_symbols_factor",
    "weights_simple_ensemble",
    "unify_weights",
    "sma_long_bear",
    "dif_long_bear",
    "tsf_type",
    "limit_leverage",
    "cal_trade_price",
    "mark_cta_periods",
    "mark_volatility",
    "cal_yearly_days",
    "turnover_rate",
    "make_price_features",
    "__version__",
    "__author__",
    "__email__",
    "__date__",
    "welcome",
]

# === 包元信息 ===
# 这些字段会被 setuptools / pip / sphinx 等工具读取，发布前需同步更新。
# __date__ 采用 ``YYYYMMDD`` 格式，便于排序与追溯。
__version__ = "0.10.12"
__author__ = "zengbin93"
__email__ = "zeng_bin8888@163.com"
__date__ = "20260308"

# === 懒加载子模块映射表 ===
# 键为公开访问名，值为完整模块路径。
# 这些子包通常依赖较重（如 svc 依赖 plotly/streamlit、fsa 依赖飞书 SDK、
# mock 涉及大量随机数生成器），若在 import czsc 时一次性全部加载，会显著
# 拖慢 CLI 工具与服务启动速度。延迟到首次访问时再加载，可保持冷启动轻量。
_LAZY_MODULES = {
    "svc": "czsc.svc",
    "fsa": "czsc.fsa",
    "aphorism": "czsc.aphorism",
    "mock": "czsc.mock",
}

# === 懒加载属性映射表 ===
# 键为公开访问名，值为 (模块路径, 模块内符号名) 二元组。
# 用于把分散在工具子模块中的少量高频函数/类提升到顶级命名空间，
# 同时保留按需加载、避免在导入期触发不必要的副作用。
_LAZY_ATTRS = {
    "capture_warnings": ("czsc.utils.warning_capture", "capture_warnings"),
    "execute_with_warning_capture": ("czsc.utils.warning_capture", "execute_with_warning_capture"),
    "adjust_holding_weights": ("czsc.utils.trade", "adjust_holding_weights"),
    "log_strategy_info": ("czsc.utils.log", "log_strategy_info"),
    "plot_czsc_chart": ("czsc.utils.plotting.kline", "plot_czsc_chart"),
    "KlineChart": ("czsc.utils.plotting.kline", "KlineChart"),
    "check_kline_quality": ("czsc.utils.kline_quality", "check_kline_quality"),
}


def __getattr__(name):
    """
    模块级懒加载钩子（PEP 562）

    Python 在常规属性查找失败时会回退调用本函数，因此可借助它实现
    延迟导入，既不破坏 ``czsc.svc.xxx``、``czsc.capture_warnings`` 等
    用户期望的访问形式，又能避免导入开销。

    实现细节：
        1. 命中 ``_LAZY_MODULES`` —— 调用 ``importlib.import_module`` 加载，
           并把模块对象写入 ``globals()``，后续访问直接走常规路径，无再次开销
        2. 命中 ``_LAZY_ATTRS`` —— 加载子模块后取出指定属性，同样缓存到全局命名空间
        3. 全部未命中 —— 抛 ``AttributeError``（必须保留，否则 ``hasattr`` 会出错）

    参数:
        name: 用户尝试访问的属性名，例如 ``"svc"``、``"plot_czsc_chart"``

    返回:
        加载完成的模块对象或目标属性

    异常:
        AttributeError: 当 ``name`` 既不在 ``_LAZY_MODULES`` 也不在 ``_LAZY_ATTRS`` 中
    """
    import importlib

    # 路径 1：懒加载子模块（按需 import，再缓存到全局）
    if name in _LAZY_MODULES:
        module = importlib.import_module(_LAZY_MODULES[name])
        globals()[name] = module
        return module

    # 路径 2：懒加载子模块中的某个属性（先 import 再 getattr，最后缓存）
    if name in _LAZY_ATTRS:
        mod_path, attr_name = _LAZY_ATTRS[name]
        module = importlib.import_module(mod_path)
        attr = getattr(module, attr_name)
        globals()[name] = attr
        return attr

    # 路径 3：未注册的属性 —— 严格抛错以维持标准 Python 语义（hasattr 等场景依赖此行为）
    raise AttributeError(f"module 'czsc' has no attribute {name!r}")


def welcome():
    """
    CLI/交互式环境下的欢迎信息打印函数

    用途：
        - 打印当前 CZSC 版本号、日期与一段随机的"缠论格言"（aphorism 子模块）
        - 打印关键环境变量当前值，便于排查"实际生效配置"问题
        - 当本地缓存目录体积超过 1 GB 时，给出清理提示，避免长期堆积

    设计动机：
        把 aphorism 的导入推迟到函数体内（而非模块顶部），是为了避免
        ``import czsc`` 时强制依赖该子包；若用户没有调用 ``welcome()``，
        aphorism 就不会被加载。
    """
    from czsc import aphorism

    print(f"欢迎使用CZSC！当前版本标识为 {__version__}@{__date__}\n")
    aphorism.print_one()

    print(f"CZSC环境变量：czsc_min_bi_len = {envs.get_min_bi_len()}; czsc_max_bi_num = {envs.get_max_bi_num()}; ")
    # 1 GB 阈值：超出即提示用户主动清理，避免缓存目录无限膨胀；
    # 用 ``pow(1024, 3)`` 而非 ``10**9`` 是为了得到精确的二进制 GB（GiB）。
    if get_dir_size(home_path) > pow(1024, 3):
        print(f"{home_path} 目录缓存超过1GB，请适当清理。调用 czsc.empty_cache_path() 可以直接清空缓存")
