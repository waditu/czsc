//! czsc-core —缠论 core analyzer (FX / BI / ZS / CZSC).
//!
//! Migrated from rs-czsc 47ef6efa. Submodules are added incrementally as
//! Phase D progresses; see docs/superpowers/plans/2026-05-03-rust-czsc-migration.md.

pub mod analyze;
pub mod objects;
pub mod utils;

#[cfg(feature = "python")]
pub mod python;
