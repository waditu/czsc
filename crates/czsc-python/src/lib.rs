//! czsc-python — PyO3 aggregator that produces the `czsc._native` extension.
//!
//! Each business crate's PyO3 surface is registered here. The crate is
//! the only one that links `pyo3 = { features = ["extension-module"] }`
//! and produces the cdylib loaded by Python.

use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

mod errors;
mod signals_dispatcher;
mod trader;
mod utils;

#[pymodule]
fn _native(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    czsc_core::python::register(py, m)?;
    czsc_utils::python::register(py, m)?;
    czsc_ta::python::register(py, m)?;

    // czsc-signals contributes `SignalDescriptor` entries via
    // `inventory::collect!`. The dummy iterator forces the crate
    // into the final cdylib so the constructors run on import.
    let _signals_count = inventory::iter::<czsc_signals::types::SignalDescriptor>()
        .into_iter()
        .count();

    // Trader surface — CzscTrader, CzscSignals, generate_czsc_signals.
    m.add_class::<trader::czsc_trader::PyCzscTrader>()?;
    m.add_class::<trader::czsc_signals::PyCzscSignals>()?;
    m.add_function(wrap_pyfunction!(trader::generate::generate_czsc_signals, m)?)?;

    // Research / optimize entrypoints (mirrors rs_czsc/python/src/lib.rs).
    // These are the heavy-lift functions that strategies.py /
    // research.py / optimize.py wrap thinly on the Python side.
    m.add_function(wrap_pyfunction!(trader::api::list_all_signals, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::derive_signals_config, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::derive_signals_freqs, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::generate_signals, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::run_backtest, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::run_optimize, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::run_research, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::run_replay, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::run_optimize_batch, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::build_open_optim_positions, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::build_exit_optim_positions, m)?)?;

    // czsc._native.signals namespace + per-category sub-modules
    // (bar / cxt / tas / vol / pressure / obv / cvolp). The dispatcher
    // is registered on each so that
    //     from czsc._native.signals import call_signal
    // and
    //     from czsc._native.signals.bar import list_signal_names
    // both resolve. See `signals_dispatcher.rs` for the design.
    let signals = PyModule::new(py, "signals")?;
    signals.setattr("__name__", "czsc._native.signals")?;
    let sys = py.import("sys")?;
    let py_modules = sys.getattr("modules")?;
    py_modules.set_item("czsc._native.signals", &signals)?;
    m.add("signals", &signals)?;

    signals_dispatcher::register(py, m, &signals)?;

    Ok(())
}
