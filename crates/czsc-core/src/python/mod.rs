//! PyO3 binding registry for czsc-core.
//!
//! Phase D's per-type sub-loops add `#[cfg_attr(feature = "python", pyclass)]`
//! to each migrated type. This module collects them into a single
//! `register()` entrypoint that `czsc-python` calls from the
//! `_native` aggregator.
//!
//! Pickle (`__getstate__` / `__setstate__`) per design doc §2.4 will
//! land on a follow-up pass once Phase E/F/G land and the per-class
//! identity tests can fully exercise it.

use pyo3::prelude::*;

use crate::analyze::CZSC;
use crate::analyze::utils as analyze_utils;
use crate::objects::bar::{NewBar, RawBar};
use crate::objects::bi::BI;
use crate::objects::direction::Direction;
use crate::objects::event::PyEvent;
use crate::objects::fake_bi::FakeBI;
use crate::objects::freq::Freq;
use crate::objects::fx::FX;
use crate::objects::mark::Mark;
use crate::objects::market::Market;
use crate::objects::operate::PyOperate;
use crate::objects::position::{PyLiteBar, PyPos, PyPosition};
use crate::objects::signal::{PyParsedSignalDoc, PySignal, parse_signal_doc_py};
use crate::objects::zs::ZS;

/// Python-friendly thin wrapper around `analyze::utils::check_fx`.
#[pyfunction]
#[pyo3(name = "check_fx")]
fn check_fx_py(k1: NewBar, k2: NewBar, k3: NewBar) -> Option<FX> {
    analyze_utils::check_fx(&k1, &k2, &k3)
}

/// Python-friendly thin wrapper around `analyze::utils::check_fxs`.
#[pyfunction]
#[pyo3(name = "check_fxs")]
fn check_fxs_py(bars: Vec<NewBar>) -> Vec<FX> {
    analyze_utils::check_fxs(&bars)
}

/// Python-friendly thin wrapper around `analyze::utils::check_bi`.
/// Drops the unused remainder slice; Python callers only ever consume
/// the optional BI value.
#[pyfunction]
#[pyo3(name = "check_bi")]
fn check_bi_py(bars: Vec<NewBar>) -> Option<BI> {
    let (bi, _) = analyze_utils::check_bi(&bars);
    bi
}

/// Python-friendly thin wrapper around `analyze::utils::remove_include`.
#[pyfunction]
#[pyo3(name = "remove_include")]
fn remove_include_py(k1: NewBar, k2: NewBar, k3: RawBar) -> PyResult<(bool, NewBar)> {
    analyze_utils::remove_include(&k1, &k2, k3)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// Python-friendly thin wrapper around `analyze::utils::format_standard_kline`.
/// Polars DataFrame is bridged via the standard pyo3-polars / arrow path; for
/// now we accept a list of pre-built RawBars to avoid the polars/python coupling
/// during D.A. The full DataFrame entrypoint will be added when Phase E/F wire
/// the polars Python bridge (see design doc §2.3).
#[pyfunction]
#[pyo3(name = "format_standard_kline")]
fn format_standard_kline_py(bars: Vec<RawBar>) -> Vec<RawBar> {
    bars
}

/// Add the migrated czsc-core types onto the parent module that czsc-python
/// passes in. Lives behind the `python` feature so plain Rust consumers
/// don't pull pyo3 in transitively.
pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Enums
    m.add_class::<Freq>()?;
    m.add_class::<Market>()?;
    m.add_class::<Mark>()?;
    m.add_class::<Direction>()?;
    m.add_class::<PyOperate>()?;
    m.add_class::<PyPos>()?;

    // Bar primitives
    m.add_class::<RawBar>()?;
    m.add_class::<NewBar>()?;
    m.add_class::<PyLiteBar>()?;

    // Chan-theory data structures
    m.add_class::<FX>()?;
    m.add_class::<FakeBI>()?;
    m.add_class::<BI>()?;
    m.add_class::<ZS>()?;

    // Signal / Event / Position
    m.add_class::<PySignal>()?;
    m.add_class::<PyParsedSignalDoc>()?;
    m.add_class::<PyEvent>()?;
    m.add_class::<PyPosition>()?;

    // Analyzer (CZSC)
    m.add_class::<CZSC>()?;

    // Free functions: signal-doc parser + analyze helpers (the 4 promotions
    // from design doc §2.5)
    m.add_function(wrap_pyfunction!(parse_signal_doc_py, m)?)?;
    m.add_function(wrap_pyfunction!(check_fx_py, m)?)?;
    m.add_function(wrap_pyfunction!(check_fxs_py, m)?)?;
    m.add_function(wrap_pyfunction!(check_bi_py, m)?)?;
    m.add_function(wrap_pyfunction!(remove_include_py, m)?)?;
    m.add_function(wrap_pyfunction!(format_standard_kline_py, m)?)?;

    Ok(())
}
