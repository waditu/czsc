//! czsc-trader 公共对象（CzscTrader / CzscSignals）的 PyO3 包装层、
//! `generate_czsc_signals` 自由函数，以及 research/optimize 编排入口
//! (`run_research`、`run_replay`、`run_optimize_batch`、
//! `build_*_optim_positions`)。
//!
//! 对齐 `rs_czsc/python/src/trader/`。rs-czsc 中的 `weight_backtest`
//! 子模块**有意**不迁移过来 —— czsc 依赖外部 `wbt` 包做回测
//! （design doc §3.1 / §5.10）。

pub mod api;
pub mod czsc_signals;
pub mod czsc_trader;
pub mod generate;
pub mod research;
