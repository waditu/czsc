//! czsc-core —— 缠论核心分析器（FX / BI / ZS / CZSC）。
//!
//! 由 rs-czsc 47ef6efa 迁移而来。子模块随着 Phase D 的推进逐步加入；
//! 参见 docs/superpowers/plans/2026-05-03-rust-czsc-migration.md。

pub mod analyze;
pub mod objects;
pub mod utils;

#[cfg(feature = "python")]
pub mod python;
