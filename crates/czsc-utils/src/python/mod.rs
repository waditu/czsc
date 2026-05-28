//! czsc-utils 的 PyO3 binding。通过 `python` feature 来开关，
//! 这样下游 Rust 消费者就不会传递性地引入 pyo3。

use chrono::{DateTime, Utc};
use czsc_core::objects::{bar::RawBar, freq::Freq, market::Market};
use pyo3::prelude::*;
use pyo3_stub_gen::derive::gen_stub_pyfunction;

use crate::bar_generator::BarGenerator;

/// `czsc.is_trading_time(dt, market="astock")` → bool。
///
/// `dt` 视为 naive 的 Python `datetime`（不附带 tz）。契约详见
/// design doc §2.5 + §6 F6。
#[pyfunction]
#[pyo3(signature = (dt, market="astock"))]
fn is_trading_time(dt: chrono::NaiveDateTime, market: &str) -> bool {
    crate::is_trading_time(dt, market)
}

/// `czsc.freq_end_time(dt, freq, market=Market.Default)` → datetime。
///
/// 包装 `czsc_utils::freq_data::freq_end_time`。错误通过 `UtilsError`
/// 的 PyErr 转换映射到 `PyValueError`。
#[pyfunction]
#[pyo3(signature = (dt, freq, market=Market::Default))]
fn freq_end_time(dt: DateTime<Utc>, freq: Freq, market: Market) -> PyResult<DateTime<Utc>> {
    crate::freq_data::freq_end_time(dt, freq, market)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// `czsc.monotonicity(sequence)` → float。
///
/// 计算序列与自然数序列的 Spearman 秩相关，等价于
/// `scipy.stats.spearmanr(sequence, range(len(sequence))).statistic`。
/// 详见 [`crate::monotonicity::monotonicity`] 的算法说明与对齐口径。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(signature = (sequence))]
fn monotonicity(sequence: Vec<f64>) -> f64 {
    crate::monotonicity::monotonicity(&sequence)
}

/// `czsc._native.resample_bars(bars, target_freq, drop_unfinished=True)` → list[RawBar]。
///
/// 纯透传，逻辑由 [`crate::resample::resample_bars`] 实现。
/// DataFrame 入参由 Python 端 wrapper 经 `format_standard_kline` 转 `List[RawBar]` 后再调用本函数。
///
/// `target_freq` 接受 `Freq` 枚举或中文周期字符串（如 "5分钟"），与 `BarGenerator.__new__`
/// 的 dual-input 约定一致。这里的 str→Freq 解析属于 PyO3 类型系统无法直接桥接的边界胶水。
#[pyfunction]
#[pyo3(signature = (bars, target_freq, drop_unfinished=true))]
fn resample_bars(
    py: Python<'_>,
    bars: Vec<RawBar>,
    target_freq: Py<PyAny>,
    drop_unfinished: bool,
) -> PyResult<Vec<RawBar>> {
    use std::str::FromStr;

    let target_freq = if let Ok(py_str) = target_freq.cast_bound::<pyo3::types::PyString>(py) {
        let s = py_str.to_string();
        Freq::from_str(&s).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("解析 target_freq 失败: {e}"))
        })?
    } else if let Ok(f) = target_freq.extract::<Freq>(py) {
        f
    } else {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "target_freq 必须是 Freq 枚举或中文周期字符串",
        ));
    };

    crate::resample::resample_bars(&bars, target_freq, drop_unfinished)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// 在父 `_native` 模块上注册 utils 子模块。Phase H 把它变成
/// `czsc.is_trading_time`、`czsc.freq_end_time` 和 `czsc.BarGenerator` 的规范入口。
pub fn register(py: Python<'_>, parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let utils = PyModule::new(py, "utils")?;
    utils.add_function(wrap_pyfunction!(is_trading_time, &utils)?)?;
    utils.add_function(wrap_pyfunction!(freq_end_time, &utils)?)?;
    utils.add_function(wrap_pyfunction!(monotonicity, &utils)?)?;
    utils.add_function(wrap_pyfunction!(resample_bars, &utils)?)?;
    utils.add_class::<BarGenerator>()?;
    parent.add_submodule(&utils)?;

    // 同时在顶层暴露一份，这样 `from czsc._native import *` 时
    // 规范名称可以直接可见（按 design doc §3.1）。
    parent.add_function(wrap_pyfunction!(is_trading_time, parent)?)?;
    parent.add_function(wrap_pyfunction!(freq_end_time, parent)?)?;
    parent.add_function(wrap_pyfunction!(monotonicity, parent)?)?;
    parent.add_function(wrap_pyfunction!(resample_bars, parent)?)?;
    parent.add_class::<BarGenerator>()?;
    Ok(())
}
