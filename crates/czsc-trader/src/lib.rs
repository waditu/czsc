//! czsc-trader — multi-strategy trading engine, signal compilation, and
//! optimization. Migrated from rs-czsc 47ef6efa per docs/MIGRATION_NOTES.md §1.
//!
//! `weight_backtest` was deliberately not migrated: per design doc §5.8
//! item 3 and §5.10, the public `WeightBacktest` API is delegated to the
//! external `wbt` package starting in Phase I. The Rust workspace owns
//! signal compilation, the trader state machine, and the v2 execution
//! engine that backs Python's `run_backtest` / `run_optimize` calls.

pub mod engine_v2;
pub mod optimize;
pub mod signals;
pub mod trader;
