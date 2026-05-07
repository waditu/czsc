//! Core data objects (FX / BI / ZS / RawBar / Freq / Mark / ...).
//!
//! Migrated from rs-czsc 47ef6efa per docs/MIGRATION_NOTES.md §1. Submodules
//! are added incrementally as Phase D sub-loops complete.

pub mod errors;
pub mod market;
pub mod freq;
pub mod bar;
pub mod mark;
pub mod direction;
pub mod fx;
pub mod fake_bi;
pub mod bi;
pub mod zs;
pub mod operate;
pub mod signal;
pub mod event;
pub mod position;
pub mod state;
