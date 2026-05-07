//! czsc._native signal dispatcher (design doc §3.3).
//!
//! Per-signal PyO3 wrappers would require ~30+ hand-written `#[pyfunction]`
//! definitions; instead we expose a single dispatcher that looks the
//! signal up by name in the inventory table contributed by
//! `czsc-signals`. The Python-side ``czsc/signals/{bar,cxt,...}.py``
//! shims attach a per-name closure via ``__getattr__`` so user code
//! reads naturally:
//!
//! ```python
//! from czsc.signals.bar import bar_amount_acc_V230214
//! result = bar_amount_acc_V230214(czsc_obj, {"di": 1, "n": 5})
//! ```
//!
//! The dispatcher only handles **kline** signals (``fn(&CZSC, &params,
//! &mut TaCache) -> Vec<Signal>``). Trader-state signals require a
//! ``CzscTrader`` instance and are dispatched via
//! ``CzscTrader.update_signals`` / ``CzscSignals.update_signals``.

use crate::trader::czsc_signals::py_to_serde_value;
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::PySignal;
use czsc_signals::types::{SignalDescriptor, SignalFnRef, TaCache};
use pyo3::exceptions::{PyKeyError, PyTypeError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde_json::Value;
use std::collections::HashMap;

/// Find a signal descriptor by name. Returns `None` if no descriptor
/// has that name. Callers should treat this as a missing signal.
fn lookup(name: &str) -> Option<&'static SignalDescriptor> {
    inventory::iter::<SignalDescriptor>()
        .into_iter()
        .find(|d| d.name == name)
}

/// Extract the category prefix from a signal name (e.g. ``bar`` from
/// ``bar_amount_acc_V230214``). Returns ``None`` if the name has no
/// underscore.
fn name_prefix(name: &str) -> Option<&str> {
    name.split_once('_').map(|(p, _)| p)
}

/// Convert a Python params dict (or `None`) into the
/// ``HashMap<String, Value>`` shape used by all kline signal
/// functions. Accepts ``None`` as an empty dict.
fn extract_params(params: Option<&Bound<'_, PyDict>>) -> PyResult<HashMap<String, Value>> {
    let mut out: HashMap<String, Value> = HashMap::new();
    if let Some(d) = params {
        for (k, v) in d.iter() {
            let key: String = k.extract()?;
            let val = py_to_serde_value(&v)?;
            out.insert(key, val);
        }
    }
    Ok(out)
}

/// Invoke a kline signal by name on the supplied CZSC instance.
///
/// Returns a list of ``czsc.Signal`` objects (the same type
/// produced by ``CzscSignals.update_signals``).
#[pyfunction]
#[pyo3(signature = (name, czsc, params=None))]
pub fn call_signal(
    name: &str,
    czsc: &CZSC,
    params: Option<&Bound<'_, PyDict>>,
) -> PyResult<Vec<PySignal>> {
    let descriptor = lookup(name)
        .ok_or_else(|| PyKeyError::new_err(format!("unknown signal: {name}")))?;

    let kline_func = match descriptor.func_ref {
        SignalFnRef::Kline(f) => f,
        SignalFnRef::Trader(_) => {
            return Err(PyTypeError::new_err(format!(
                "{name} is a trader-state signal; dispatch via CzscTrader.update_signals"
            )));
        }
    };

    let params_map = extract_params(params)?;
    let mut cache = TaCache::default();
    let signals = kline_func(czsc, &params_map, &mut cache);
    Ok(signals.into_iter().map(PySignal::from).collect())
}

/// List signal names contributed by the inventory.
///
/// ``category`` is matched against the signal-name prefix (the part
/// before the first underscore). Common values: ``bar``, ``cxt``,
/// ``tas``, ``vol``, ``pressure``, ``obv``, ``cvolp``. Pass ``None``
/// to return every kline signal.
#[pyfunction]
#[pyo3(signature = (category=None))]
pub fn list_signal_names(category: Option<&str>) -> Vec<String> {
    let mut out: Vec<String> = inventory::iter::<SignalDescriptor>()
        .into_iter()
        .filter(|d| matches!(d.func_ref, SignalFnRef::Kline(_)))
        .filter(|d| match category {
            Some(c) => name_prefix(d.name).map(|p| p == c).unwrap_or(false),
            None => true,
        })
        .map(|d| d.name.to_string())
        .collect();
    out.sort();
    out
}

/// Return the parameter template for ``name``, or ``None`` if no signal
/// with that name is registered. The template is the schema string
/// declared in the `#[signal(...)]` macro and matches what the legacy
/// Python helpers parse.
#[pyfunction]
pub fn get_signal_template(name: &str) -> Option<String> {
    lookup(name).map(|d| d.template.to_string())
}

/// Return the category prefix for ``name`` (``"bar"`` / ``"cxt"`` /
/// ...). ``None`` when the signal isn't registered or its name has no
/// underscore.
#[pyfunction]
pub fn get_signal_category(name: &str) -> Option<String> {
    let descriptor = lookup(name)?;
    name_prefix(descriptor.name).map(|p| p.to_string())
}

/// Register the dispatcher symbols on both ``czsc._native`` (top-level)
/// and ``czsc._native.signals`` (submodule). The submodule entries
/// give design-doc §3.3 the path ``from czsc._native.signals import
/// call_signal``.
pub fn register(py: Python<'_>, m: &Bound<'_, PyModule>, signals_mod: &Bound<'_, PyModule>) -> PyResult<()> {
    use pyo3::wrap_pyfunction;

    m.add_function(wrap_pyfunction!(call_signal, m)?)?;
    m.add_function(wrap_pyfunction!(list_signal_names, m)?)?;
    m.add_function(wrap_pyfunction!(get_signal_template, m)?)?;
    m.add_function(wrap_pyfunction!(get_signal_category, m)?)?;

    signals_mod.add_function(wrap_pyfunction!(call_signal, signals_mod)?)?;
    signals_mod.add_function(wrap_pyfunction!(list_signal_names, signals_mod)?)?;
    signals_mod.add_function(wrap_pyfunction!(get_signal_template, signals_mod)?)?;
    signals_mod.add_function(wrap_pyfunction!(get_signal_category, signals_mod)?)?;

    // Per-category sub-modules: czsc._native.signals.{bar,cxt,...}.
    // Each gets the full dispatcher trio so user code can write:
    //
    //   import czsc._native.signals.bar as bar_mod
    //   bar_mod.list_signal_names()  # only bar_* names
    //
    // The Python-side `czsc/signals/<cat>.py` shim layers __getattr__
    // on top of these to expose individual functions.
    let categories = [
        "bar",
        "cxt",
        "tas",
        "vol",
        "pressure",
        "obv",
        "cvolp",
    ];
    let sys = py.import("sys")?;
    let py_modules = sys.getattr("modules")?;
    for cat in categories {
        let cat_mod = PyModule::new(py, cat)?;
        cat_mod.setattr("__name__", format!("czsc._native.signals.{cat}"))?;
        cat_mod.setattr("__category__", cat)?;
        cat_mod.add_function(wrap_pyfunction!(call_signal, &cat_mod)?)?;
        cat_mod.add_function(wrap_pyfunction!(list_signal_names, &cat_mod)?)?;
        cat_mod.add_function(wrap_pyfunction!(get_signal_template, &cat_mod)?)?;
        py_modules.set_item(format!("czsc._native.signals.{cat}"), &cat_mod)?;
        signals_mod.add(cat, &cat_mod)?;
    }

    Ok(())
}
