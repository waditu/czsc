//! czsc-trader — 多策略交易引擎、信号编译以及优化。
//! 按 docs/MIGRATION_NOTES.md §1 从 rs-czsc 47ef6efa 迁移而来。
//!
//! `weight_backtest` 故意没有迁移：按 design doc §5.8 item 3 和 §5.10，
//! 公开的 `WeightBacktest` API 从 Phase I 开始委托给外部 `wbt` 包。
//! Rust workspace 负责信号编译、trader 状态机，以及支撑 Python
//! `run_backtest` / `run_optimize` 调用的 v2 执行引擎。

pub mod czsc_signals;
pub mod engine_v2;
pub mod optimize;
pub mod sig_parse;
pub mod strategy;
pub mod trader;

pub use strategy::{JsonStrategy, Strategy, unique_signals_across};

// 旧 `czsc_trader::signals::{czsc_signals,sig_parse}::*` 路径的兼容别名。
// Phase J 把原 `signals/` 目录拍平了（避免与外部 `czsc-signals` crate 同名
// 混淆，且去掉无意义的中间层）。新代码用顶层路径，本 mod 只为外部用户保留
// 一个无破坏过渡。
#[doc(hidden)]
pub mod signals {
    pub use super::czsc_signals;
    pub use super::czsc_signals::CzscSignals;
    pub use super::sig_parse;
    pub use super::sig_parse::{SignalConfig, get_signals_config, get_signals_freqs};
}
