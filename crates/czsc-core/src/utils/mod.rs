//! Internal utilities for czsc-core. Migration is incremental: members
//! land as their consumers (BI / ZS / ...) get migrated.

pub mod common;
pub mod corr;
pub mod errors;
pub mod rounded;
