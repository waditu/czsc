//! czsc-ta — technical analysis operators.
//!
//! Migrated from rs-czsc 47ef6efa per docs/MIGRATION_NOTES.md §1.
//! Phase E call-graph analysis (recorded in §2.3) confirmed the full
//! operator set is consumed by Python via `rust-numpy`; nothing was
//! trimmed.

#![allow(clippy::needless_range_loop, clippy::manual_memcpy)]

pub mod pure;

#[cfg(feature = "rust-numpy")]
pub mod mixed;

#[cfg(feature = "rust-numpy")]
pub mod python;
