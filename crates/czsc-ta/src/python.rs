//! PyO3 binding registry for czsc-ta.
//!
//! Mirrors the wrapper layer that rs-czsc kept inside its python crate
//! (rs_czsc/python/src/utils/ta.rs); we move the `#[pyfunction]` shells
//! into czsc-ta itself so czsc-python only orchestrates `register()`
//! calls. All wrappers are dormant unless the `python` feature
//! (or `rust-numpy` for the numpy-bound entries) is on.

use pyo3::prelude::*;

use crate::{mixed, pure};

#[pyfunction]
fn ultimate_smoother(close: Vec<f64>, period: f64) -> Vec<f64> {
    pure::ultimate_smoother(&close, period)
}

#[pyfunction]
fn rolling_rank(series: Vec<f64>, window: usize) -> Vec<f64> {
    // Convert Option<usize> -> f64 (None -> NaN) so `np.asarray(...)` lands
    // in float64 dtype and `np.isfinite(out[window:])` works as expected.
    // Python callers consuming the rank position can `.dropna()` instead of
    // filtering Nones.
    pure::rolling_rank(&series, window)
        .into_iter()
        .map(|opt| opt.map(|r| r as f64).unwrap_or(f64::NAN))
        .collect()
}

#[pyfunction]
#[pyo3(signature = (series, n=None, *, period=None, length=None))]
fn sma(
    series: Vec<f64>,
    n: Option<usize>,
    period: Option<usize>,
    length: Option<usize>,
) -> Vec<f64> {
    // Same kwarg story as `ema` — talib's keyword is `timeperiod` /
    // pandas-ta's is `length`; rs-czsc historical scripts pass `n` /
    // `period`. Phase A parity test calls `ta.sma(series, length=20)`.
    let p = n.or(period).or(length).unwrap_or(0);
    pure::sma(&series, p)
}

#[pyfunction]
fn single_sma_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::single_sma_positions(&series, n)
}

#[pyfunction]
fn single_ema_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::single_ema_positions(&series, n)
}

#[pyfunction]
fn mid_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::mid_positions(&series, n)
}

#[pyfunction]
fn double_sma_positions(series: Vec<f64>, n: usize, m: usize) -> Vec<f64> {
    pure::double_sma_positions(&series, n, m)
}

#[pyfunction]
fn triple_sma_positions(series: Vec<f64>, m1: usize, m2: usize, m3: usize) -> Vec<i32> {
    pure::triple_sma_positions(&series, m1, m2, m3)
}

#[pyfunction]
fn boll_positions(series: Vec<f64>, n: usize, k: f64) -> Vec<i32> {
    pure::boll_positions(&series, n, k)
}

#[pyfunction]
fn boll_reverse_positions(series: Vec<f64>, n: usize, k: f64) -> Vec<i32> {
    pure::boll_reverse_positions(&series, n, k)
}

#[pyfunction]
fn mms_positions(series: Vec<f64>, timeperiod: usize, window: usize) -> Vec<f64> {
    pure::mms_positions(&series, timeperiod, window)
}

#[pyfunction]
fn rsi_reverse_positions(
    series: Vec<f64>,
    n: usize,
    rsi_upper: f64,
    rsi_lower: f64,
    rsi_exit: f64,
) -> Vec<i32> {
    pure::rsi_reverse_positions(&series, n, rsi_upper, rsi_lower, rsi_exit)
}

#[pyfunction]
fn tanh_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::tanh_positions(&series, n)
}

#[pyfunction]
fn rank_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::rank_positions(&series, n)
}

#[pyfunction]
#[pyo3(signature = (series, n=None, *, period=None, length=None))]
fn ema(
    series: Vec<f64>,
    n: Option<usize>,
    period: Option<usize>,
    length: Option<usize>,
) -> Vec<f64> {
    // Accept any of: positional `n`, kwargs `period=` (legacy rs-czsc) or
    // `length=` (talib / pandas-ta convention). The Phase A parity test
    // in `test/unit/test_ta_parity.py::test_ema_matches_talib` calls
    // `ta.ema(series, length=14)`; rs-czsc historical scripts pass
    // `period=14`. Resolution order preserves the positional path first
    // so existing positional callers keep working.
    let p = n.or(period).or(length).unwrap_or(0);
    pure::ema(&series, p)
}

#[pyfunction]
fn true_range(high: Vec<f64>, low: Vec<f64>, close_prev: Vec<f64>) -> Vec<f64> {
    pure::true_range(&high, &low, &close_prev)
}

#[pyfunction]
fn rsx_ss2(close: Vec<f64>, period: usize, smooth_period: usize) -> Vec<f64> {
    pure::rsx_ss2(&close, period, smooth_period)
}

#[pyfunction]
fn jurik_volty(close: Vec<f64>, period: usize, power: f64) -> Vec<f64> {
    pure::jurik_volty(&close, period, power)
}

#[pyfunction]
fn ultimate_channel(
    high: Vec<f64>,
    low: Vec<f64>,
    close: Vec<f64>,
    period: usize,
    multiplier: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    pure::ultimate_channel(&high, &low, &close, period, multiplier)
}

#[pyfunction]
fn ultimate_bands(
    close: Vec<f64>,
    period: usize,
    std_multiplier: f64,
    smooth_period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    pure::ultimate_bands(&close, period, std_multiplier, smooth_period)
}

#[pyfunction]
fn ultimate_oscillator(
    high: Vec<f64>,
    low: Vec<f64>,
    close: Vec<f64>,
    short_period: usize,
    med_period: usize,
    long_period: usize,
) -> Vec<f64> {
    pure::ultimate_oscillator(&high, &low, &close, short_period, med_period, long_period)
}

#[pyfunction]
fn exponential_smoothing(series: Vec<f64>, alpha: f64) -> Vec<f64> {
    pure::exponential_smoothing(&series, alpha)
}

#[pyfunction]
fn holt_winters(
    series: Vec<f64>,
    season_length: usize,
    alpha: f64,
    beta: f64,
    gamma: f64,
) -> Vec<f64> {
    pure::holt_winters(&series, season_length, alpha, beta, gamma)
}

/// Add the migrated czsc-ta functions onto the parent module that
/// czsc-python passes in. Build a `ta` submodule mirroring the design
/// doc §3.1 namespace map (czsc.ta.* + repeated top-level exposure).
pub fn register(py: Python<'_>, parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let ta = PyModule::new(py, "ta")?;
    // Set the fully-qualified __name__ so `czsc.ta` (aliased via
    // sys.modules) reports `__name__ == "czsc._native.ta"`. Required
    // by the public-API parity test that checks namespace origin and
    // by pickle when classes living in this submodule get round-tripped.
    ta.setattr("__name__", "czsc._native.ta")?;

    macro_rules! add {
        ($($name:ident),+ $(,)?) => {{
            $(
                ta.add_function(wrap_pyfunction!($name, &ta)?)?;
                parent.add_function(wrap_pyfunction!($name, parent)?)?;
            )+
        }};
    }

    add!(
        ultimate_smoother,
        rolling_rank,
        sma,
        single_sma_positions,
        single_ema_positions,
        mid_positions,
        double_sma_positions,
        triple_sma_positions,
        boll_positions,
        boll_reverse_positions,
        mms_positions,
        rsi_reverse_positions,
        tanh_positions,
        rank_positions,
        ema,
        true_range,
        rsx_ss2,
        jurik_volty,
        ultimate_channel,
        ultimate_bands,
        ultimate_oscillator,
        exponential_smoothing,
        holt_winters,
    );

    // numpy-bound entries
    ta.add_function(wrap_pyfunction!(
        mixed::chip_dist::chip_distribution_triangle,
        &ta
    )?)?;
    parent.add_function(wrap_pyfunction!(
        mixed::chip_dist::chip_distribution_triangle,
        parent
    )?)?;

    // Register the submodule into sys.modules so `from czsc._native.ta
    // import ema` (and `import czsc._native.ta`) works the same as a
    // pure-Python package. `parent.add_submodule` only sets it as an
    // attribute of the parent — sys.modules is the bit Python's import
    // machinery actually consults for nested module resolution.
    let sys = py.import("sys")?;
    let py_modules = sys.getattr("modules")?;
    py_modules.set_item("czsc._native.ta", &ta)?;
    // Use `parent.add` instead of `add_submodule` so we control the
    // attribute key (`parent.ta`) independently of the module's
    // qualified __name__ (`czsc._native.ta`). add_submodule uses the
    // qualified name as the attribute, which would expose the
    // submodule as `parent.czsc._native.ta` instead of `parent.ta`.
    parent.add("ta", &ta)?;
    Ok(())
}
