//! czsc-signals — signal function library.
//!
//! Migrated from rs-czsc 47ef6efa per docs/MIGRATION_NOTES.md §1.
//! Each signal sub-module is wrapped in `#[signal_module]` (proc-macro
//! from czsc-signal-macros) which validates signatures and registers
//! every `#[signal(...)]` function into the global inventory.

extern crate self as czsc_signals;

use czsc_signal_macros::signal_module;

#[signal_module(category = "kline")]
pub mod bar {
    include!("bar.rs");
}

#[signal_module(category = "kline")]
pub mod cxt {
    include!("cxt.rs");
}

#[signal_module(category = "trader")]
pub mod cxt_trader {
    include!("cxt_trader.rs");
}

#[signal_module(category = "trader")]
pub mod pos {
    include!("pos.rs");
}

#[signal_module(category = "trader")]
pub mod cat {
    include!("cat.rs");
}
pub mod params;
pub mod registry;

#[signal_module(category = "kline")]
pub mod tas {
    include!("tas.rs");
}

#[signal_module(category = "kline")]
pub mod vol {
    include!("vol.rs");
}

#[signal_module(category = "kline")]
pub mod pressure {
    include!("pressure.rs");
}

#[signal_module(category = "kline")]
pub mod obv {
    include!("obv.rs");
}

#[signal_module(category = "kline")]
pub mod cvolp {
    include!("cvolp.rs");
}

#[signal_module(category = "kline")]
pub mod ntmdk {
    include!("ntmdk.rs");
}

#[signal_module(category = "kline")]
pub mod kcatr {
    include!("kcatr.rs");
}

#[signal_module(category = "kline")]
pub mod clv {
    include!("clv.rs");
}

#[signal_module(category = "kline")]
pub mod ang {
    include!("ang.rs");
}

#[signal_module(category = "kline")]
pub mod coo {
    include!("coo.rs");
}

#[signal_module(category = "kline")]
pub mod byi {
    include!("byi.rs");
}

#[signal_module(category = "kline")]
pub mod jcc {
    include!("jcc.rs");
}

#[signal_module(category = "kline")]
pub mod xl {
    include!("xl.rs");
}

#[signal_module(category = "kline")]
pub mod zdy {
    include!("zdy.rs");
}

#[signal_module(category = "trader")]
pub mod zdy_trader {
    include!("zdy_trader.rs");
}
pub mod types;
pub mod utils;

inventory::collect!(crate::types::SignalDescriptor);
