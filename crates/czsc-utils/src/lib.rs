//! czsc-utils — utilities crate.
//!
//! Phase C scope so far:
//! - [`trading_time`] — `is_trading_time` (czsc-only NEW per design doc §2.5)
//!
//! Pending (deferred until Phase D unlocks `czsc-core`):
//! - `freq_data` — depends on `czsc_core::objects::{RawBar, Freq, Market}`
//! - `bar_generator` — depends on `czsc-core`

pub mod bar_generator;
pub mod errors;
pub mod freq_data;
pub mod trading_time;

pub use trading_time::is_trading_time;

#[cfg(feature = "python")]
pub mod python;
