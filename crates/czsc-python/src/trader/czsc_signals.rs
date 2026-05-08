use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::utils::common::create_naive_pandas_timestamp;
use czsc_trader::signals::czsc_signals::CzscSignals;
use czsc_trader::signals::sig_parse::SignalConfig;
use czsc_utils::bar_generator::BarGenerator;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};
use serde_json::Value;
use std::collections::HashMap;

/// 将 Python list[dict] 解析为 Vec<SignalConfig>
pub(crate) fn parse_signals_config(configs: &Bound<PyList>) -> PyResult<Vec<SignalConfig>> {
    let mut result = Vec::with_capacity(configs.len());
    for item in configs.iter() {
        let dict = item
            .downcast::<PyDict>()
            .map_err(|_| PyValueError::new_err("signals_config 中每个元素必须是 dict"))?;

        let name: String = dict
            .get_item("name")?
            .ok_or_else(|| PyValueError::new_err("signals_config dict 缺少 'name' 字段"))?
            .extract()?;

        let freq: Option<String> = match dict.get_item("freq")? {
            Some(v) if !v.is_none() => Some(v.extract()?),
            _ => None,
        };

        let mut params: HashMap<String, Value> = HashMap::new();

        // 优先从 "params" 子字典取参数
        if let Some(params_obj) = dict.get_item("params")?
            && !params_obj.is_none()
            && let Ok(params_dict) = params_obj.downcast::<PyDict>()
        {
            for (k, v) in params_dict.iter() {
                let key: String = k.extract()?;
                let val = py_to_serde_value(&v)?;
                params.insert(key, val);
            }
        }

        // 也支持 flat params：dict 中除 name/freq/params 以外的 key 直接作为参数
        for (k, v) in dict.iter() {
            let key: String = k.extract()?;
            if key == "name" || key == "freq" || key == "params" {
                continue;
            }
            if let std::collections::hash_map::Entry::Vacant(e) = params.entry(key) {
                let val = py_to_serde_value(&v)?;
                e.insert(val);
            }
        }

        result.push(SignalConfig { name, freq, params });
    }
    Ok(result)
}

/// 将 Python 值转换为 serde_json::Value
pub(crate) fn py_to_serde_value(obj: &Bound<PyAny>) -> PyResult<Value> {
    // bool 必须在 int 前检查，因为 Python 的 bool 是 int 子类
    if let Ok(v) = obj.extract::<bool>() {
        return Ok(Value::from(v));
    }
    if let Ok(v) = obj.extract::<i64>() {
        return Ok(Value::from(v));
    }
    if let Ok(v) = obj.extract::<f64>() {
        return Ok(Value::from(v));
    }
    if let Ok(v) = obj.extract::<String>() {
        return Ok(Value::String(v));
    }
    if obj.is_none() {
        return Ok(Value::Null);
    }
    // 降级：用 repr 作字符串
    let repr = obj.repr()?.extract::<String>()?;
    Ok(Value::String(repr))
}

/// CzscSignals 的 PyO3 包装
#[gen_stub_pyclass]
#[pyclass(name = "CzscSignals", module = "czsc._native")]
pub struct PyCzscSignals {
    inner: CzscSignals,
    signals_config: Vec<SignalConfig>,
}

#[gen_stub_pymethods]
#[pymethods]
impl PyCzscSignals {
    #[new]
    #[pyo3(signature = (bg, signals_config))]
    fn new(bg: BarGenerator, signals_config: &Bound<PyList>) -> PyResult<Self> {
        let configs = parse_signals_config(signals_config)?;
        let symbol = bg
            .freq_bars
            .values()
            .next()
            .and_then(|v| v.read().back().cloned())
            .map(|b| b.symbol.to_string())
            .unwrap_or_default();
        let inner = CzscSignals::new(symbol, bg);
        Ok(Self {
            inner,
            signals_config: configs,
        })
    }

    /// 返回类名
    #[getter]
    fn name(&self) -> &str {
        "CzscSignals"
    }

    /// 返回标的代码
    #[getter]
    fn symbol(&self) -> &str {
        &self.inner.symbol
    }

    /// 返回信号字典 s
    #[getter]
    fn s(&self, py: Python) -> PyResult<PyObject> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.s {
            dict.set_item(k, v)?;
        }
        Ok(dict.into_any().unbind())
    }

    /// 返回各周期 CZSC 分析引擎
    #[getter]
    fn kas(&self) -> PyResult<HashMap<String, CZSC>> {
        Ok(self.inner.kas.clone().into_iter().collect())
    }

    /// 返回所有周期字符串列表
    #[getter]
    fn freqs(&self) -> Vec<String> {
        self.inner
            .bg
            .freq_bars
            .keys()
            .map(|f| f.to_string())
            .collect()
    }

    /// 返回基准周期字符串
    #[getter]
    fn base_freq(&self) -> String {
        self.inner
            .bg
            .freq_bars
            .keys()
            .next()
            .map(|f| f.to_string())
            .unwrap_or_default()
    }

    /// 返回最新时间，作为 pandas Timestamp
    #[getter]
    fn end_dt(&self, py: Python) -> PyResult<Option<PyObject>> {
        if let Some(dt_str) = self.inner.s.get("dt")
            && let Ok(dt) = chrono::DateTime::parse_from_rfc3339(dt_str)
        {
            let utc_dt = dt.with_timezone(&chrono::Utc);
            let timestamp = create_naive_pandas_timestamp(py, utc_dt)?;
            return Ok(Some(timestamp));
        }
        Ok(None)
    }

    /// 返回当前 bar id
    #[getter]
    fn bid(&self) -> PyResult<Option<i64>> {
        if let Some(id_str) = self.inner.s.get("id") {
            let id = id_str
                .parse::<i64>()
                .map_err(|e| PyValueError::new_err(format!("解析 id 失败: {e}")))?;
            return Ok(Some(id));
        }
        Ok(None)
    }

    /// 返回最新价格
    #[getter]
    fn latest_price(&self) -> PyResult<Option<f64>> {
        if let Some(close_str) = self.inner.s.get("close") {
            let price = close_str
                .parse::<f64>()
                .map_err(|e| PyValueError::new_err(format!("解析 close 失败: {e}")))?;
            return Ok(Some(price));
        }
        Ok(None)
    }

    /// 返回原始信号配置
    #[getter]
    fn signals_config(&self, py: Python) -> PyResult<PyObject> {
        let list = PyList::empty(py);
        for cfg in &self.signals_config {
            let dict = PyDict::new(py);
            dict.set_item("name", &cfg.name)?;
            match &cfg.freq {
                Some(f) => dict.set_item("freq", f)?,
                None => dict.set_item("freq", py.None())?,
            }
            let params_dict = PyDict::new(py);
            for (k, v) in &cfg.params {
                let py_val = serde_value_to_py(py, v)?;
                params_dict.set_item(k, py_val)?;
            }
            dict.set_item("params", params_dict)?;
            list.append(dict)?;
        }
        Ok(list.into_any().unbind())
    }

    /// 更新信号
    fn update_signals(&mut self, bar: &RawBar) {
        self.inner.update_signals(bar, &self.signals_config);
    }

    /// 获取当前信号字典（同 s 属性）
    fn get_signals_by_conf(&self, py: Python) -> PyResult<PyObject> {
        self.s(py)
    }

    /// Pickle 支持：返回 ``(cls, (bg_clone, signals_config_list))``。
    /// 反序列化时 PyCzscSignals 由原 ``__new__`` 重新构造；缓存的信号
    /// 状态不持久化（与 design doc §2.4 的 multiprocessing 用例一致：
    /// 子进程拿到的是构造参数 fresh trader）。
    fn __reduce__(&self, py: Python) -> PyResult<PyObject> {
        let bg_clone = self.inner.bg.clone();
        let configs_list = signal_configs_to_pylist(py, &self.signals_config)?;
        let constructor = py.get_type::<Self>();
        let args = (bg_clone, configs_list).into_pyobject(py)?;
        let result = (constructor, args).into_pyobject(py)?;
        Ok(result.into_any().unbind())
    }
}

/// Helper: convert `Vec<SignalConfig>` back to a Python ``list[dict]``
/// shaped exactly like ``parse_signals_config`` expects, so
/// ``__reduce__`` -> ``__new__`` round-trips cleanly.
pub(crate) fn signal_configs_to_pylist(py: Python, configs: &[SignalConfig]) -> PyResult<PyObject> {
    let list = PyList::empty(py);
    for cfg in configs {
        let dict = PyDict::new(py);
        dict.set_item("name", &cfg.name)?;
        match &cfg.freq {
            Some(f) => dict.set_item("freq", f)?,
            None => dict.set_item("freq", py.None())?,
        }
        let params_dict = PyDict::new(py);
        for (k, v) in &cfg.params {
            params_dict.set_item(k, serde_value_to_py(py, v)?)?;
        }
        dict.set_item("params", params_dict)?;
        list.append(dict)?;
    }
    Ok(list.into_any().unbind())
}

/// 将 serde_json::Value 转换为 Python 对象
pub(crate) fn serde_value_to_py(py: Python, val: &Value) -> PyResult<PyObject> {
    match val {
        Value::Null => Ok(py.None()),
        Value::Bool(b) => Ok(b.into_pyobject(py)?.to_owned().into_any().unbind()),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_pyobject(py)?.into_any().unbind())
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_pyobject(py)?.into_any().unbind())
            } else {
                Ok(py.None())
            }
        }
        Value::String(s) => Ok(s.as_str().into_pyobject(py)?.into_any().unbind()),
        Value::Array(_) | Value::Object(_) => {
            let json_str = serde_json::to_string(val)
                .map_err(|e| PyValueError::new_err(format!("JSON 序列化失败: {e}")))?;
            Ok(json_str.into_pyobject(py)?.into_any().unbind())
        }
    }
}
