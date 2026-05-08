//! Core data objects (FX / BI / ZS / RawBar / Freq / Mark / ...).
//!
//! Migrated from rs-czsc 47ef6efa per docs/MIGRATION_NOTES.md §1. Submodules
//! are added incrementally as Phase D sub-loops complete.

pub mod bar;
pub mod bi;
pub mod direction;
pub mod errors;
pub mod event;
pub mod fake_bi;
pub mod freq;
pub mod fx;
pub mod mark;
pub mod market;
pub mod operate;
pub mod position;
pub mod signal;
pub mod state;
pub mod zs;
