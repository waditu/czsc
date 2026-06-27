//! czsc-core 的 PyO3 binding 注册表。
//!
//! Phase D 的逐类型子循环会给每个迁移过来的类型加 `#[cfg_attr(feature = "python", pyclass)]`。
//! 本模块把它们汇总到一个 `register()` 入口，由 `czsc-python` 在
//! `_native` aggregator 中调用。
//!
//! 按 design doc §2.4 的 Pickle（`__getstate__` / `__setstate__`）将会
//! 在 Phase E/F/G 落地后做一次后续提交，到时各类的 identity 测试可以充分覆盖它。

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

/// 对 `analyze::utils::check_fx` 的 Python 友好的薄 wrapper。
#[pyfunction]
#[pyo3(name = "check_fx")]
fn check_fx_py(k1: NewBar, k2: NewBar, k3: NewBar) -> Option<FX> {
    analyze_utils::check_fx(&k1, &k2, &k3)
}

/// 对 `analyze::utils::check_fxs` 的 Python 友好的薄 wrapper。
#[pyfunction]
#[pyo3(name = "check_fxs")]
fn check_fxs_py(bars: Vec<NewBar>) -> Vec<FX> {
    analyze_utils::check_fxs(&bars)
}

/// 对 `analyze::utils::check_bi` 的 Python 友好的薄 wrapper。
/// 丢弃未使用的剩余切片；Python 调用方只消费可选的 BI 值。
#[pyfunction]
#[pyo3(name = "check_bi")]
#[pyo3(signature = (bars, min_bi_len=0))]
fn check_bi_py(bars: Vec<NewBar>, min_bi_len: usize) -> Option<BI> {
    let n = if min_bi_len > 0 {
        min_bi_len
    } else {
        crate::analyze::resolve_min_bi_len(min_bi_len)
    };
    let (bi, _) = analyze_utils::check_bi(&bars, n);
    bi
}

/// 对 `analyze::utils::remove_include` 的 Python 友好的薄 wrapper。
#[pyfunction]
#[pyo3(name = "remove_include")]
fn remove_include_py(k1: NewBar, k2: NewBar, k3: RawBar) -> PyResult<(bool, NewBar)> {
    analyze_utils::remove_include(&k1, &k2, k3)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))
}

/// 对 `analyze::utils::format_standard_kline` 的 Python 友好的薄 wrapper。
/// Polars DataFrame 通过标准的 pyo3-polars / arrow 路径桥接；目前
/// 我们接受一个预构建好的 RawBar 列表，以避免在 D.A 阶段引入 polars/python 的耦合。
/// 完整的 DataFrame 入口会等到 Phase E/F 接入 polars Python 桥时再添加（详见 design doc §2.3）。
#[pyfunction]
#[pyo3(name = "format_standard_kline")]
fn format_standard_kline_py(bars: Vec<RawBar>) -> Vec<RawBar> {
    bars
}

/// 把迁移过来的 czsc-core 类型添加到 czsc-python 传入的父模块上。
/// 隐藏在 `python` feature 后面，这样普通 Rust 消费者就不会传递性地引入 pyo3。
pub fn register(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // 枚举
    m.add_class::<Freq>()?;
    m.add_class::<Market>()?;
    m.add_class::<Mark>()?;
    m.add_class::<Direction>()?;
    m.add_class::<PyOperate>()?;
    m.add_class::<PyPos>()?;

    // Bar 基础类型
    m.add_class::<RawBar>()?;
    m.add_class::<NewBar>()?;
    m.add_class::<PyLiteBar>()?;

    // 缠论数据结构
    m.add_class::<FX>()?;
    m.add_class::<FakeBI>()?;
    m.add_class::<BI>()?;
    m.add_class::<ZS>()?;

    // Signal / Event / Position
    m.add_class::<PySignal>()?;
    m.add_class::<PyParsedSignalDoc>()?;
    m.add_class::<PyEvent>()?;
    m.add_class::<PyPosition>()?;

    // 分析器（CZSC）
    m.add_class::<CZSC>()?;

    // 自由函数：signal-doc 解析器 + analyze helpers（来自 design doc §2.5
    // 的 4 个 promotion）
    m.add_function(wrap_pyfunction!(parse_signal_doc_py, m)?)?;
    m.add_function(wrap_pyfunction!(check_fx_py, m)?)?;
    m.add_function(wrap_pyfunction!(check_fxs_py, m)?)?;
    m.add_function(wrap_pyfunction!(check_bi_py, m)?)?;
    m.add_function(wrap_pyfunction!(remove_include_py, m)?)?;
    m.add_function(wrap_pyfunction!(format_standard_kline_py, m)?)?;

    Ok(())
}
