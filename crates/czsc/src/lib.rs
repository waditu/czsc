//! czsc — facade crate, re-exports the full czsc Rust workspace under one name.
//!
//! 业务实现拆分在 [`czsc-core`] / [`czsc-utils`] / [`czsc-ta`] /
//! [`czsc-signals`] / [`czsc-trader`] 几个 crate 里；本 crate 只做 re-export，
//! 让终端用户写
//!
//! ```toml
//! [dependencies]
//! czsc = "1.0"
//! ```
//!
//! 即可拿到全部公共 API，无需逐个 add 子 crate。
//!
//! 命名空间约定：
//!
//! | 子模块                  | 来源                                  |
//! |-------------------------|---------------------------------------|
//! | `czsc::analyze`         | [`czsc_core::analyze`]                |
//! | `czsc::objects::*`      | [`czsc_core::objects`] 的所有数据类型 |
//! | `czsc::error_chain`     | [`czsc_core::error_chain`]            |
//! | `czsc::ta`              | [`czsc_ta`] 的纯算子（`pure`）        |
//! | `czsc::bar_generator`   | [`czsc_utils::bar_generator`]         |
//! | `czsc::freq_data`       | [`czsc_utils::freq_data`]             |
//! | `czsc::trading_time`    | [`czsc_utils::trading_time`]          |
//! | `czsc::signals`         | [`czsc_signals`]                      |
//! | `czsc::trader`          | [`czsc_trader`] 的全部对外公共面      |
//!
//! 顶层 re-export 的核心类型（最常用）：[`CZSC`] / [`RawBar`] / [`NewBar`] /
//! [`Freq`] / [`FX`] / [`BI`] / [`ZS`] / [`Mark`] / [`Direction`] /
//! [`Operate`] / [`Event`] / [`Position`] / [`Market`] /
//! [`BarGenerator`] / [`is_trading_time`]。

#![doc(html_root_url = "https://docs.rs/czsc/1.0.0")]

// ── 子模块命名空间 ─────────────────────────────────────────────────────────
pub use czsc_core::analyze;
pub use czsc_core::error_chain;
pub use czsc_core::objects;

pub use czsc_utils::bar_generator;
pub use czsc_utils::freq_data;
pub use czsc_utils::trading_time;

/// 技术分析算子（EMA / SMA / rolling_rank / ultimate_smoother / ...）。
///
/// 本模块就是 [`czsc_ta::pure`]，只 re-export 不带 numpy 互操作的纯 Rust 接口。
/// 想用 numpy 互操作请直接依赖 [`czsc_ta`] 并启用 `rust-numpy` feature。
pub mod ta {
    pub use czsc_ta::pure::*;
}

pub use czsc_signals as signals;

pub mod trader {
    //! 交易引擎、信号编译、参数优化。
    //! 来源 [`czsc_trader`]。
    pub use czsc_trader::czsc_signals::CzscSignals;
    pub use czsc_trader::sig_parse::{SignalConfig, get_signals_config, get_signals_freqs};
    pub use czsc_trader::{engine_v2, optimize, strategy, trader};
}

/// 策略门面（Strategy facade）—— 让 cargo 用户拿到与 Python
/// `czsc.CzscStrategyBase` / `czsc.CzscJsonStrategy` 等价的抽象。
/// 详见 [`czsc_trader::strategy`]。
pub use czsc_trader::strategy::{JsonStrategy, Strategy, unique_signals_across};

// ── 顶层 re-export：常用类型直接挂在 czsc::* ────────────────────────────────
pub use czsc_core::analyze::CZSC;
pub use czsc_core::objects::{
    bar::{NewBar, RawBar, Symbol},
    bi::BI,
    direction::Direction,
    event::Event,
    freq::Freq,
    fx::FX,
    mark::Mark,
    market::Market,
    operate::Operate,
    position::{OperateRecord, Position, PositionUpdateProfile},
    zs::ZS,
};

pub use czsc_utils::bar_generator::BarGenerator;
pub use czsc_utils::trading_time::is_trading_time;

pub use czsc_trader::czsc_signals::CzscSignals;
pub use czsc_trader::sig_parse::SignalConfig;
