//! czsc-trader — 多策略交易引擎、信号编译以及优化。
//! 按 docs/MIGRATION_NOTES.md §1 从 rs-czsc 47ef6efa 迁移而来。
//!
//! `weight_backtest` 故意没有迁移：按 design doc §5.8 item 3 和 §5.10，
//! 公开的 `WeightBacktest` API 从 Phase I 开始委托给外部 `wbt` 包。
//! Rust workspace 负责信号编译、trader 状态机，以及支撑 Python
//! `run_backtest` / `run_optimize` 调用的 v2 执行引擎。

pub mod engine_v2;
pub mod optimize;
pub mod signals;
pub mod trader;
