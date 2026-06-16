use super::czsc_signals::{parse_signals_config, serde_value_to_py};
use chrono::{DateTime, FixedOffset};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::position::{LiteBar, Position, PyPosition};
use czsc_core::utils::common::create_naive_pandas_timestamp;
use czsc_trader::sig_parse::SignalConfig;
use czsc_trader::trader::CzscTrader;
use czsc_utils::bar_generator::BarGenerator;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList};
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};
use std::collections::HashMap;

/// CzscTrader 的 PyO3 包装
#[gen_stub_pyclass]
#[pyclass(name = "CzscTrader", module = "czsc._native")]
pub struct PyCzscTrader {
    inner: CzscTrader,
    signals_config: Vec<SignalConfig>,
    ensemble_method: String,
}

/// 从 Py<PyAny> 提取 Position：支持 PyPosition（Rust）和有 _inner 属性的 Python wrapper
fn extract_position(_py: Python, obj: &Bound<PyAny>) -> PyResult<Position> {
    // 优先尝试提取 PyPosition
    if let Ok(py_pos) = obj.extract::<PyPosition>() {
        return Ok(py_pos.inner);
    }
    // 尝试从 _inner 属性提取
    if let Ok(inner_attr) = obj.getattr("_inner")
        && let Ok(py_pos) = inner_attr.extract::<PyPosition>()
    {
        return Ok(py_pos.inner);
    }
    // 尝试从 inner 属性提取
    if let Ok(inner_attr) = obj.getattr("inner")
        && let Ok(py_pos) = inner_attr.extract::<PyPosition>()
    {
        return Ok(py_pos.inner);
    }
    Err(PyValueError::new_err(
        "positions 中的元素必须是 Position 或有 _inner/inner 属性的对象",
    ))
}

#[gen_stub_pymethods]
#[pymethods]
impl PyCzscTrader {
    #[new]
    #[pyo3(signature = (bg, positions, signals_config, ensemble_method = "mean".to_string()))]
    fn new(
        py: Python,
        bg: BarGenerator,
        positions: &Bound<PyList>,
        signals_config: &Bound<PyList>,
        ensemble_method: String,
    ) -> PyResult<Self> {
        let configs = parse_signals_config(signals_config)?;

        // 提取 positions
        let mut pos_vec = Vec::with_capacity(positions.len());
        for item in positions.iter() {
            let pos = extract_position(py, &item)?;
            pos_vec.push(pos);
        }

        let symbol = bg
            .freq_bars
            .values()
            .next()
            .and_then(|v| v.read().back().cloned())
            .map(|b| b.symbol.to_string())
            .unwrap_or_default();

        let inner = CzscTrader::new(symbol, bg, pos_vec);

        Ok(Self {
            inner,
            signals_config: configs,
            ensemble_method,
        })
    }

    /// 返回类名
    #[getter]
    fn name(&self) -> &str {
        &self.inner.name
    }

    /// 返回标的代码
    #[getter]
    fn symbol(&self) -> &str {
        &self.inner.signals.symbol
    }

    /// 返回信号字典 s
    #[getter]
    fn s(&self, py: Python) -> PyResult<Py<PyAny>> {
        let dict = PyDict::new(py);
        for (k, v) in &self.inner.signals.s {
            dict.set_item(k, v)?;
        }
        Ok(dict.into_any().unbind())
    }

    /// 返回各周期 CZSC 分析引擎
    #[getter]
    fn kas(&self) -> PyResult<HashMap<String, CZSC>> {
        Ok(self.inner.signals.kas.clone().into_iter().collect())
    }

    /// 返回所有周期字符串列表
    #[getter]
    fn freqs(&self) -> Vec<String> {
        self.inner
            .signals
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
            .signals
            .bg
            .freq_bars
            .keys()
            .next()
            .map(|f| f.to_string())
            .unwrap_or_default()
    }

    /// 返回最新时间，作为 pandas Timestamp
    #[getter]
    fn end_dt(&self, py: Python) -> PyResult<Option<Py<PyAny>>> {
        if let Some(dt_str) = self.inner.signals.s.get("dt")
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
        if let Some(id_str) = self.inner.signals.s.get("id") {
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
        if let Some(close_str) = self.inner.signals.s.get("close") {
            let price = close_str
                .parse::<f64>()
                .map_err(|e| PyValueError::new_err(format!("解析 close 失败: {e}")))?;
            return Ok(Some(price));
        }
        Ok(None)
    }

    /// 返回原始信号配置
    #[getter]
    fn signals_config(&self, py: Python) -> PyResult<Py<PyAny>> {
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

    /// 返回仓位列表（PyPosition 包装）
    #[getter]
    fn positions(&self) -> Vec<PyPosition> {
        self.inner
            .positions
            .iter()
            .map(|p| PyPosition { inner: p.clone() })
            .collect()
    }

    /// 返回是否有仓位发生变化
    #[getter]
    fn pos_changed(&self) -> bool {
        self.inner.positions.iter().any(|p| p.get_pos_changed())
    }

    /// 更新信号和仓位
    fn update(&mut self, bar: &RawBar) {
        self.inner.update(bar, &self.signals_config);
    }

    /// 更新信号和仓位（同 update）
    fn on_bar(&mut self, bar: &RawBar) {
        self.inner.update(bar, &self.signals_config);
    }

    /// 基于信号字典更新仓位
    fn on_sig(&mut self, _py: Python, sig: &Bound<PyDict>) -> PyResult<()> {
        // 解析 sig dict 的 key-value 对，设置到 inner.signals.s 和 signal_map
        let mut s_map = HashMap::new();
        for (k, v) in sig.iter() {
            let key: String = k.extract()?;
            let val: String = v.str()?.to_string();
            s_map.insert(key, val);
        }

        // 提取必要字段
        let id: i32 = sig
            .get_item("id")?
            .ok_or_else(|| PyValueError::new_err("sig 缺少 'id'"))?
            .extract()
            .or_else(|_| {
                sig.get_item("id")?
                    .ok_or_else(|| PyValueError::new_err("sig 缺少 'id'"))?
                    .str()?
                    .to_string()
                    .parse::<i32>()
                    .map_err(|e| PyValueError::new_err(format!("解析 id 失败: {e}")))
            })?;

        let close: f64 = sig
            .get_item("close")?
            .ok_or_else(|| PyValueError::new_err("sig 缺少 'close'"))?
            .extract()
            .or_else(|_| {
                sig.get_item("close")?
                    .ok_or_else(|| PyValueError::new_err("sig 缺少 'close'"))?
                    .str()?
                    .to_string()
                    .parse::<f64>()
                    .map_err(|e| PyValueError::new_err(format!("解析 close 失败: {e}")))
            })?;

        let dt_obj = sig
            .get_item("dt")?
            .ok_or_else(|| PyValueError::new_err("sig 缺少 'dt'"))?;
        let dt = parse_dt_from_pyobj(&dt_obj)?;

        // 设置信号
        self.inner.signals.s = s_map.clone();
        self.inner.signals.signal_map = s_map;

        // 构建 LiteBar
        let lite_bar = LiteBar {
            id,
            dt,
            price: close,
        };

        // 更新所有仓位
        for pos in &mut self.inner.positions {
            pos.update_profiled_with_signal_map(
                lite_bar,
                None,
                Some(&self.inner.signals.signal_map),
            );
        }

        Ok(())
    }

    /// 获取集成后的仓位值
    #[pyo3(signature = (method=None))]
    fn get_ensemble_pos(&self, method: Option<&str>) -> f64 {
        let method = method.unwrap_or(&self.ensemble_method);
        let pos_values: Vec<f64> = self
            .inner
            .positions
            .iter()
            .map(|p| p.get_pos().to_f64())
            .collect();

        if pos_values.is_empty() {
            return 0.0;
        }

        match method {
            "mean" => pos_values.iter().sum::<f64>() / pos_values.len() as f64,
            "max" => pos_values.iter().cloned().fold(f64::NEG_INFINITY, f64::max),
            "min" => pos_values.iter().cloned().fold(f64::INFINITY, f64::min),
            "vote" => {
                let sum: f64 = pos_values.iter().sum();
                if sum > 0.0 {
                    1.0
                } else if sum < 0.0 {
                    -1.0
                } else {
                    0.0
                }
            }
            _ => pos_values.iter().sum::<f64>() / pos_values.len() as f64,
        }
    }

    /// 根据名称获取仓位
    fn get_position(&self, name: &str) -> Option<PyPosition> {
        self.inner
            .positions
            .iter()
            .find(|p| p.name == name)
            .map(|p| PyPosition { inner: p.clone() })
    }

    /// 获取当前信号字典
    fn get_signals_by_conf(&self, py: Python) -> PyResult<Py<PyAny>> {
        self.s(py)
    }

    /// 仅更新信号（不更新仓位）
    fn update_signals(&mut self, bar: &RawBar) {
        self.inner.signals.update_signals(bar, &self.signals_config);
    }

    /// 导出完整状态快照为 bytes（热启动用，零重放）。
    ///
    /// 快照含缠论计算状态（bg/kas/ta_cache 全历史）、仓位配置与运行时决策状态
    /// （pos/operates/holds 等）、信号配置与集成方式，可经 ``restore_state`` 单参还原。
    fn dump_state(&self, py: Python) -> PyResult<Py<PyBytes>> {
        let bytes = self
            .inner
            .dump_state(&self.signals_config, &self.ensemble_method)
            .map_err(|e| PyValueError::new_err(format!("dump_state 失败: {e}")))?;
        Ok(PyBytes::new(py, &bytes).unbind())
    }

    /// 从 ``dump_state`` 产生的 bytes 还原 trader（零重放热启动）。
    ///
    /// 信号配置与集成方式从快照内读回，无需额外参数。
    #[staticmethod]
    fn restore_state(data: &Bound<'_, PyBytes>) -> PyResult<Self> {
        let restored = CzscTrader::restore_state(data.as_bytes())
            .map_err(|e| PyValueError::new_err(format!("restore_state 失败: {e}")))?;
        Ok(Self {
            inner: restored.trader,
            signals_config: restored.signals_config,
            ensemble_method: restored.ensemble_method,
        })
    }

    /// Pickle 支持：返回构造参数 (bg, positions, signals_config, ensemble_method)。
    /// 反序列化时由 ``__new__`` 重新构造一个 fresh trader；缓存的运行
    /// 状态不持久化（与 design doc §2.4 multiprocessing 用例一致）。
    fn __reduce__(&self, py: Python) -> PyResult<Py<PyAny>> {
        let bg_clone = self.inner.signals.bg.clone();

        // positions：通过 PyPosition wrapper 克隆
        let positions_list = PyList::empty(py);
        for pos in &self.inner.positions {
            let py_pos = PyPosition { inner: pos.clone() };
            positions_list.append(py_pos)?;
        }

        let configs_list = super::czsc_signals::signal_configs_to_pylist(py, &self.signals_config)?;

        let constructor = py.get_type::<Self>();
        let args = (
            bg_clone,
            positions_list,
            configs_list,
            self.ensemble_method.clone(),
        )
            .into_pyobject(py)?;
        let result = (constructor, args).into_pyobject(py)?;
        Ok(result.into_any().unbind())
    }
}

/// 从 Python 对象解析 DateTime<FixedOffset>
fn parse_dt_from_pyobj(obj: &Bound<PyAny>) -> PyResult<DateTime<FixedOffset>> {
    // 尝试提取字符串
    if let Ok(s) = obj.extract::<String>() {
        // 尝试 RFC3339
        if let Ok(dt) = DateTime::parse_from_rfc3339(&s) {
            return Ok(dt);
        }
        // 尝试 "%Y-%m-%d %H:%M:%S"
        if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%d %H:%M:%S") {
            return Ok(DateTime::from_naive_utc_and_offset(
                naive,
                FixedOffset::east_opt(0).unwrap(),
            ));
        }
        // 尝试 "%Y-%m-%d"
        if let Ok(naive_date) = chrono::NaiveDate::parse_from_str(&s, "%Y-%m-%d") {
            let naive = naive_date.and_hms_opt(0, 0, 0).unwrap();
            return Ok(DateTime::from_naive_utc_and_offset(
                naive,
                FixedOffset::east_opt(0).unwrap(),
            ));
        }
        return Err(PyValueError::new_err(format!("无法解析时间字符串: {s}")));
    }

    // 尝试 pandas Timestamp: 调用 .isoformat() 或 str()
    if let Ok(iso) = obj.call_method0("isoformat")
        && let Ok(s) = iso.extract::<String>()
    {
        if let Ok(dt) = DateTime::parse_from_rfc3339(&s) {
            return Ok(dt);
        }
        // pandas isoformat 可能不带时区
        if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%dT%H:%M:%S") {
            return Ok(DateTime::from_naive_utc_and_offset(
                naive,
                FixedOffset::east_opt(0).unwrap(),
            ));
        }
    }

    // 最后降级：str(obj)
    let s = obj.str()?.to_string();
    if let Ok(naive) = chrono::NaiveDateTime::parse_from_str(&s, "%Y-%m-%d %H:%M:%S") {
        return Ok(DateTime::from_naive_utc_and_offset(
            naive,
            FixedOffset::east_opt(0).unwrap(),
        ));
    }

    Err(PyValueError::new_err(format!(
        "无法解析时间对象: {}",
        obj.repr()?
    )))
}
