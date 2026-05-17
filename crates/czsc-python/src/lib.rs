//! czsc-python —— 产生 `czsc._native` 扩展的 PyO3 聚合器。
//!
//! 每个业务 crate 的 PyO3 表面都在这里注册。这个 crate 是 workspace
//! 中唯一启用 `pyo3 = { features = ["extension-module"] }` 的，它产出
//! Python 加载的 cdylib。

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

    // czsc-signals 通过 `inventory::collect!` 贡献 `SignalDescriptor`
    // 条目。这里用一次哑迭代强制把该 crate 链入最终的 cdylib，
    // 这样 import 时构造器就会跑起来。
    let _signals_count = inventory::iter::<czsc_signals::types::SignalDescriptor>().count();

    // Trader 表面 —— CzscTrader、CzscSignals、generate_czsc_signals。
    m.add_class::<trader::czsc_trader::PyCzscTrader>()?;
    m.add_class::<trader::czsc_signals::PyCzscSignals>()?;
    m.add_function(wrap_pyfunction!(
        trader::generate::generate_czsc_signals,
        m
    )?)?;

    // Research / optimize 入口（对齐 rs_czsc/python/src/lib.rs）。
    // 这些是干重活的函数，Python 侧的 strategies.py / research.py /
    // optimize.py 只做薄薄一层包装。
    m.add_function(wrap_pyfunction!(trader::api::list_all_signals, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::derive_signals_config, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::derive_signals_freqs, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::get_unique_signals, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::strategy_unique_signals, m)?)?;
    // 别名：`get_signals_config` / `get_signals_freqs` 复用 derive_* 实现
    // Python 端 `from czsc._native import get_signals_config` 即可纯透传。
    m.add("get_signals_config", m.getattr("derive_signals_config")?)?;
    m.add("get_signals_freqs", m.getattr("derive_signals_freqs")?)?;
    m.add_function(wrap_pyfunction!(trader::api::generate_signals, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::run_backtest, m)?)?;
    m.add_function(wrap_pyfunction!(trader::api::run_optimize, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::run_research, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::run_replay, m)?)?;
    m.add_function(wrap_pyfunction!(trader::research::run_optimize_batch, m)?)?;
    m.add_function(wrap_pyfunction!(
        trader::research::build_open_optim_positions,
        m
    )?)?;
    m.add_function(wrap_pyfunction!(
        trader::research::build_exit_optim_positions,
        m
    )?)?;

    // czsc._native.signals 命名空间 + 按类别分的子模块
    // (bar / cxt / tas / vol / pressure / obv / cvolp)。分发器在每个子模块
    // 上都注册一次，使得
    //     from czsc._native.signals import call_signal
    // 和
    //     from czsc._native.signals.bar import list_signal_names
    // 都能解析。设计细节见 `signals_dispatcher.rs`。
    let signals = PyModule::new(py, "signals")?;
    signals.setattr("__name__", "czsc._native.signals")?;
    let sys = py.import("sys")?;
    let py_modules = sys.getattr("modules")?;
    py_modules.set_item("czsc._native.signals", &signals)?;
    m.add("signals", &signals)?;

    signals_dispatcher::register(py, m, &signals)?;

    Ok(())
}

// === pyo3-stub-gen 收集器 ===
// 收集所有 #[gen_stub_pyclass] / #[gen_stub_pyfunction] / #[gen_stub_pymethods]
// 装饰器注册的 Rust 端类型 / 函数信息。配套 binary `cargo run --bin stub_gen`
// 调用 stub_info() 后写出 czsc/_native.pyi（spec §2.4 / Q4）。
//
// 注：由于 czsc 的 pyproject.toml 在 workspace 根（不是 crate 根），
// 这里**手写**一个等价于 `define_stub_info_gatherer!` 的入口，把 pyproject 路径
// 显式指向上两级目录。
pub fn stub_info() -> pyo3_stub_gen::Result<pyo3_stub_gen::StubInfo> {
    let manifest_dir: &std::path::Path = env!("CARGO_MANIFEST_DIR").as_ref();
    let workspace_root = manifest_dir
        .parent() // crates/
        .and_then(|p| p.parent()) // workspace 根
        .ok_or_else(|| anyhow::anyhow!("无法定位 workspace 根目录"))?;
    pyo3_stub_gen::StubInfo::from_pyproject_toml(workspace_root.join("pyproject.toml"))
}
