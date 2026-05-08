//! czsc._native 信号分发器（设计文档 §3.3）。
//!
//! 若给每个信号写独立的 PyO3 wrapper，会有 30+ 个手写的 `#[pyfunction]`；
//! 这里改为暴露一个统一的分发器，通过名字在 `czsc-signals` 贡献的 inventory
//! 表里查找信号。Python 端的 ``czsc/signals/{bar,cxt,...}.py`` 通过
//! ``__getattr__`` 给每个名字挂上一个闭包，使用方代码因而读起来很自然：
//!
//! ```python
//! from czsc.signals.bar import bar_amount_acc_V230214
//! result = bar_amount_acc_V230214(czsc_obj, {"di": 1, "n": 5})
//! ```
//!
//! 本分发器只处理 **K 线** 类信号（签名为 ``fn(&CZSC, &params,
//! &mut TaCache) -> Vec<Signal>``）。依赖 trader 状态的信号需要
//! ``CzscTrader`` 实例，走 ``CzscTrader.update_signals`` /
//! ``CzscSignals.update_signals`` 路径分发。

use crate::trader::czsc_signals::py_to_serde_value;
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::PySignal;
use czsc_signals::types::{SignalDescriptor, SignalFnRef, TaCache};
use pyo3::exceptions::{PyKeyError, PyTypeError};
use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde_json::Value;
use std::collections::HashMap;

/// 按名字查找信号 descriptor。找不到时返回 `None`，调用方应将其视为
/// 信号未注册。
fn lookup(name: &str) -> Option<&'static SignalDescriptor> {
    inventory::iter::<SignalDescriptor>()
        .into_iter()
        .find(|d| d.name == name)
}

/// 从信号名中提取分类前缀（如从 ``bar_amount_acc_V230214`` 中取出
/// ``bar``）。名字里不含下划线时返回 ``None``。
fn name_prefix(name: &str) -> Option<&str> {
    name.split_once('_').map(|(p, _)| p)
}

/// 把 Python 端传入的 params 字典（或 ``None``）转换为所有 K 线类信号函数
/// 都接受的 ``HashMap<String, Value>``。``None`` 视为空字典。
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

/// 在给定的 CZSC 实例上按名字调用一个 K 线类信号。
///
/// 返回 ``czsc.Signal`` 列表（与 ``CzscSignals.update_signals`` 产出的
/// 类型一致）。
#[pyfunction]
#[pyo3(signature = (name, czsc, params=None))]
pub fn call_signal(
    name: &str,
    czsc: &CZSC,
    params: Option<&Bound<'_, PyDict>>,
) -> PyResult<Vec<PySignal>> {
    let descriptor =
        lookup(name).ok_or_else(|| PyKeyError::new_err(format!("unknown signal: {name}")))?;

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

/// 列出 inventory 中注册的所有信号名。
///
/// ``category`` 用来按信号名前缀（首个下划线之前的部分）过滤；常见取值：
/// ``bar``、``cxt``、``tas``、``vol``、``pressure``、``obv``、``cvolp``。
/// 传 ``None`` 返回所有 K 线类信号。
#[pyfunction]
#[pyo3(signature = (category=None))]
pub fn list_signal_names(category: Option<&str>) -> Vec<String> {
    let mut out: Vec<String> = inventory::iter::<SignalDescriptor>()
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

/// 返回 ``name`` 对应信号的参数模板字符串；若未注册则返回 ``None``。
/// 模板即 `#[signal(...)]` 宏里声明的 schema，与历史 Python 辅助代码
/// 解析的字符串保持一致。
#[pyfunction]
pub fn get_signal_template(name: &str) -> Option<String> {
    lookup(name).map(|d| d.template.to_string())
}

/// 返回 ``name`` 的分类前缀（``"bar"`` / ``"cxt"`` / ...）。信号未注册
/// 或名字里不含下划线时返回 ``None``。
#[pyfunction]
pub fn get_signal_category(name: &str) -> Option<String> {
    let descriptor = lookup(name)?;
    name_prefix(descriptor.name).map(|p| p.to_string())
}

/// 把分发器相关符号同时挂到 ``czsc._native``（顶层）和
/// ``czsc._native.signals``（子模块）下。子模块入口对应设计文档 §3.3
/// 描述的导入路径 ``from czsc._native.signals import call_signal``。
pub fn register(
    py: Python<'_>,
    m: &Bound<'_, PyModule>,
    signals_mod: &Bound<'_, PyModule>,
) -> PyResult<()> {
    use pyo3::wrap_pyfunction;

    m.add_function(wrap_pyfunction!(call_signal, m)?)?;
    m.add_function(wrap_pyfunction!(list_signal_names, m)?)?;
    m.add_function(wrap_pyfunction!(get_signal_template, m)?)?;
    m.add_function(wrap_pyfunction!(get_signal_category, m)?)?;

    signals_mod.add_function(wrap_pyfunction!(call_signal, signals_mod)?)?;
    signals_mod.add_function(wrap_pyfunction!(list_signal_names, signals_mod)?)?;
    signals_mod.add_function(wrap_pyfunction!(get_signal_template, signals_mod)?)?;
    signals_mod.add_function(wrap_pyfunction!(get_signal_category, signals_mod)?)?;

    // 按分类创建子模块：czsc._native.signals.{bar,cxt,...}。
    // 每个子模块都挂上完整的分发器三件套，使用方代码可以这样写：
    //
    //   import czsc._native.signals.bar as bar_mod
    //   bar_mod.list_signal_names()  # 只列 bar_* 信号
    //
    // Python 侧的 `czsc/signals/<cat>.py` 在此基础上叠加 __getattr__，
    // 把单个信号函数暴露成可直接调用的属性。
    let categories = ["bar", "cxt", "tas", "vol", "pressure", "obv", "cvolp"];
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
