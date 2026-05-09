//! czsc-core —— 缠论核心分析器（FX / BI / ZS / CZSC）。
//!
//! 由 rs-czsc 47ef6efa 迁移而来。子模块随着 Phase D 的推进逐步加入；
//! 参见 docs/superpowers/plans/2026-05-03-rust-czsc-migration.md。

pub mod analyze;
pub mod error_chain;
pub mod objects;
pub mod utils;

#[cfg(feature = "python")]
pub mod python;

// 旧 `error-support` crate 的对外 API 在内部继续可用：
//   `use czsc_core::error_chain::{expand_error_chain, czsc_bail}`
// 旧路径 `error_support::*` 已废弃。`czsc_bail!` 通过 `#[macro_export]`
// 暴露在 crate 顶层，调用方写 `czsc_core::czsc_bail!(...)` 即可。
