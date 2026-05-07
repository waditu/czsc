//! PyO3 wrappers for czsc-trader public objects (CzscTrader / CzscSignals),
//! the `generate_czsc_signals` free function, and the research/optimize
//! orchestration entrypoints (`run_research`, `run_replay`,
//! `run_optimize_batch`, `build_*_optim_positions`).
//!
//! Mirrors `rs_czsc/python/src/trader/`. The `weight_backtest` submodule
//! from rs-czsc is intentionally NOT migrated — czsc relies on the
//! external `wbt` package for backtests (design doc §3.1 / §5.10).

pub mod api;
pub mod czsc_signals;
pub mod czsc_trader;
pub mod generate;
pub mod research;
