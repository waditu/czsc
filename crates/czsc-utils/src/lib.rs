//! czsc-utils — 工具 crate。
//!
//! 目前 Phase C 范围：
//! - [`trading_time`] — `is_trading_time`（czsc-only NEW，按 design doc §2.5）
//!
//! 待办（延后到 Phase D 解锁 `czsc-core` 再做）：
//! - `freq_data` — 依赖 `czsc_core::objects::{RawBar, Freq, Market}`
//! - `bar_generator` — 依赖 `czsc-core`

pub mod bar_generator;
pub mod errors;
pub mod freq_data;
pub mod monotonicity;
pub mod trading_time;

pub use monotonicity::monotonicity;
pub use trading_time::is_trading_time;

#[cfg(feature = "python")]
pub mod python;
