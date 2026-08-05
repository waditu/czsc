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
use crate::objects::fake_bi::{FakeBI, create_fake_bis};
use crate::objects::freq::Freq;
use crate::objects::fx::FX;
use crate::objects::mark::Mark;
use crate::objects::market::Market;
use crate::objects::operate::PyOperate;
use crate::objects::position::{PyLiteBar, PyPos, PyPosition};
use crate::objects::signal::{PyParsedSignalDoc, PySignal, parse_signal_doc_py};
use crate::objects::zs::ZS;
use crate::utils::common::create_naive_pandas_timestamp;
use pyo3::types::{PyDict, PyDictMethods};
use pyo3_stub_gen::derive::gen_stub_pyfunction;

/// 对 `analyze::utils::check_fx` 的 Python 友好的薄 wrapper。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "check_fx")]
fn check_fx_py(k1: NewBar, k2: NewBar, k3: NewBar) -> Option<FX> {
    analyze_utils::check_fx(&k1, &k2, &k3)
}

/// 对 `analyze::utils::check_fxs` 的 Python 友好的薄 wrapper。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "check_fxs")]
fn check_fxs_py(bars: Vec<NewBar>) -> Vec<FX> {
    analyze_utils::check_fxs(&bars)
}

/// 对 `analyze::utils::check_bi` 的 Python 友好的薄 wrapper。
/// 丢弃未使用的剩余切片；Python 调用方只消费可选的 BI 值。
#[gen_stub_pyfunction]
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
#[gen_stub_pyfunction]
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
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "format_standard_kline")]
fn format_standard_kline_py(bars: Vec<RawBar>) -> Vec<RawBar> {
    bars
}

/// 将分型序列转换为虚拟笔；非法的非交替分型返回 ValueError。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "create_fake_bis")]
fn create_fake_bis_py(fxs: Vec<FX>) -> PyResult<Vec<FakeBI>> {
    if fxs.windows(2).any(|w| w[0].mark == w[1].mark) {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "相邻分型标记必须不同",
        ));
    }
    Ok(create_fake_bis(&fxs))
}

/// 将连续笔划分为中枢序列。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "get_zs_seq")]
fn get_zs_seq_py(bis: Vec<BI>) -> Vec<ZS> {
    analyze_utils::get_zs_seq(&bis)
}

/// 判断一组连续笔是否构成对称中枢。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "is_symmetry_zs", signature = (bis, th=0.3))]
fn is_symmetry_zs_py(bis: Vec<BI>, th: f64) -> bool {
    analyze_utils::is_symmetry_zs(&bis, th)
}

/// 判断连续奇数笔是否构成向上结构。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "is_bis_up")]
fn is_bis_up_py(bis: Vec<BI>) -> bool {
    analyze_utils::is_bis_up(&bis)
}

/// 判断连续奇数笔是否构成向下结构。
#[gen_stub_pyfunction]
#[pyfunction]
#[pyo3(name = "is_bis_down")]
fn is_bis_down_py(bis: Vec<BI>) -> bool {
    analyze_utils::is_bis_down(&bis)
}

/// 返回与历史 Python API 兼容的缺口字典列表。
#[gen_stub_pyfunction]
#[gen_stub(override_return_type(
    type_repr = "builtins.list[builtins.dict[builtins.str, typing.Any]]",
    imports = ("builtins", "typing")
))]
#[pyfunction]
#[pyo3(name = "check_gap_info")]
fn check_gap_info_py(py: Python<'_>, bars: Vec<RawBar>) -> PyResult<Vec<Py<PyDict>>> {
    analyze_utils::check_gap_info(&bars)
        .into_iter()
        .map(|gap| {
            let item = PyDict::new(py);
            item.set_item("kind", gap.kind)?;
            item.set_item("cover", gap.cover)?;
            item.set_item("sdt", create_naive_pandas_timestamp(py, gap.sdt)?)?;
            item.set_item("edt", create_naive_pandas_timestamp(py, gap.edt)?)?;
            item.set_item("high", gap.high)?;
            item.set_item("low", gap.low)?;
            item.set_item("delta", gap.delta)?;
            Ok(item.unbind())
        })
        .collect()
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
    m.add_function(wrap_pyfunction!(create_fake_bis_py, m)?)?;
    m.add_function(wrap_pyfunction!(get_zs_seq_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_symmetry_zs_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_bis_up_py, m)?)?;
    m.add_function(wrap_pyfunction!(is_bis_down_py, m)?)?;
    m.add_function(wrap_pyfunction!(check_gap_info_py, m)?)?;

    Ok(())
}
