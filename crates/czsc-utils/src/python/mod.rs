//! czsc-utils 的 PyO3 binding。通过 `python` feature 来开关，
//! 这样下游 Rust 消费者就不会传递性地引入 pyo3。

use chrono::{DateTime, Utc};
use czsc_core::objects::{freq::Freq, market::Market};
use pyo3::prelude::*;

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

/// 在父 `_native` 模块上注册 utils 子模块。Phase H 把它变成
/// `czsc.is_trading_time`、`czsc.freq_end_time` 和 `czsc.BarGenerator` 的规范入口。
pub fn register(py: Python<'_>, parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let utils = PyModule::new(py, "utils")?;
    utils.add_function(wrap_pyfunction!(is_trading_time, &utils)?)?;
    utils.add_function(wrap_pyfunction!(freq_end_time, &utils)?)?;
    utils.add_class::<BarGenerator>()?;
    parent.add_submodule(&utils)?;

    // 同时在顶层暴露一份，这样 `from czsc._native import *` 时
    // 规范名称可以直接可见（按 design doc §3.1）。
    parent.add_function(wrap_pyfunction!(is_trading_time, parent)?)?;
    parent.add_function(wrap_pyfunction!(freq_end_time, parent)?)?;
    parent.add_class::<BarGenerator>()?;
    Ok(())
}
