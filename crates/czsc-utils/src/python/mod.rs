//! PyO3 bindings for czsc-utils. Gated by the `python` feature so that
//! downstream Rust consumers don't pull pyo3 in transitively.

use chrono::{DateTime, Utc};
use czsc_core::objects::{freq::Freq, market::Market};
use pyo3::prelude::*;

use crate::bar_generator::BarGenerator;

/// `czsc.is_trading_time(dt, market="astock")` → bool.
///
/// `dt` is taken as a naive Python `datetime` (no tz attached). See
/// design doc §2.5 + §6 F6 for the contract.
#[pyfunction]
#[pyo3(signature = (dt, market="astock"))]
fn is_trading_time(dt: chrono::NaiveDateTime, market: &str) -> bool {
    crate::is_trading_time(dt, market)
}

/// `czsc.freq_end_time(dt, freq, market=Market.Default)` → datetime.
///
/// Wraps `czsc_utils::freq_data::freq_end_time`. Errors are mapped to
/// `PyValueError` via `UtilsError`'s PyErr conversion.
#[pyfunction]
#[pyo3(signature = (dt, freq, market=Market::Default))]
fn freq_end_time(
    dt: DateTime<Utc>,
    freq: Freq,
    market: Market,
) -> PyResult<DateTime<Utc>> {
    crate::freq_data::freq_end_time(dt, freq, market)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Register the utils submodule on the parent `_native` module. Phase H
/// turns this into the canonical entrypoint for `czsc.is_trading_time`,
/// `czsc.freq_end_time`, and `czsc.BarGenerator`.
pub fn register(py: Python<'_>, parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let utils = PyModule::new(py, "utils")?;
    utils.add_function(wrap_pyfunction!(is_trading_time, &utils)?)?;
    utils.add_function(wrap_pyfunction!(freq_end_time, &utils)?)?;
    utils.add_class::<BarGenerator>()?;
    parent.add_submodule(&utils)?;

    // Also expose top-level so `from czsc._native import *` makes the
    // canonical names directly visible (per design doc §3.1).
    parent.add_function(wrap_pyfunction!(is_trading_time, parent)?)?;
    parent.add_function(wrap_pyfunction!(freq_end_time, parent)?)?;
    parent.add_class::<BarGenerator>()?;
    Ok(())
}
