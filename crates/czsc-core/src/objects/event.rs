// czsc-only: pyo3 imports + super::operate / super::signal Python wrappers
// gated behind the `python` feature for non-python builds. Sha256 is used in
// the (non-python) Event helpers so it stays unconditional.
// See docs/MIGRATION_NOTES.md §2.4.
#![allow(unused)]
use anyhow::{Context, anyhow};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::cell::Ref;
use std::collections::{HashMap, HashSet};
use std::str::FromStr;

use super::operate::Operate;
use super::signal::{ANY, Signal};

#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::{PyDict, PyDictMethods};
#[cfg(feature = "python")]
use super::operate::PyOperate;
#[cfg(feature = "python")]
use super::signal::PySignal;
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Event {
    pub operate: Operate,

    /// 必须全部满足的信号，允许为空
    pub signals_all: Vec<Signal>,

    /// 满足其中任一信号，允许为空
    pub signals_any: Vec<Signal>,

    /// 不能满足其中任一信号，允许为空
    pub signals_not: Vec<Signal>,

    /// 默认可以为""
    #[serde(default)]
    pub name: String,

    /// SHA256哈希
    #[serde(default)]
    pub sha256: String,
}

impl Event {
    fn py_repr_list_str(items: &[String]) -> String {
        if items.is_empty() {
            "[]".to_string()
        } else {
            let body = items
                .iter()
                .map(|x| format!("'{}'", x.replace('\'', "\\'")))
                .collect::<Vec<_>>()
                .join(", ");
            format!("[{body}]")
        }
    }

    fn py_repr_for_hash(&self) -> String {
        let operate = self.operate.to_chinese().replace('\'', "\\'");
        let all = self
            .signals_all
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>();
        let any = self
            .signals_any
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>();
        let not = self
            .signals_not
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>();
        // 对齐 Python Event.__post_init__:
        // hashlib.sha256(str({'operate':..., 'signals_all':..., 'signals_any':..., 'signals_not':...}).encode()).hexdigest()[:4]
        format!(
            "{{'operate': '{operate}', 'signals_all': {}, 'signals_any': {}, 'signals_not': {}}}",
            Self::py_repr_list_str(&all),
            Self::py_repr_list_str(&any),
            Self::py_repr_list_str(&not),
        )
    }

    #[allow(unused)]
    fn new(
        operate: Operate,
        signals_all: Vec<Signal>,
        signals_any: Vec<Signal>,
        signals_not: Vec<Signal>,
        name: Option<String>,
    ) -> anyhow::Result<Event> {
        let mut event = Self {
            operate,
            signals_all,
            signals_any,
            signals_not,
            name: name.unwrap_or_default(),
            sha256: String::new(),
        };

        event.compute_hash_name();
        Ok(event)
    }

    /// 计算 Hash (除了name字段)
    pub fn compute_sha8(&self) -> String {
        let mut hasher = Sha256::new();
        hasher.update(self.py_repr_for_hash().as_bytes());
        let result = hasher.finalize();
        hex::encode(result)[..4].to_uppercase()
    }

    /// 更新名称
    fn compute_hash_name(&mut self) {
        let digest = self.compute_sha8();
        self.sha256 = digest.clone();

        if !self.name.is_empty() {
            let base = self
                .name
                .split('#')
                .next()
                .map(|s| s.to_string())
                .unwrap_or_else(|| self.name.clone());
            self.name = format!("{base}#{digest}");
        } else {
            self.name = format!("{:?}#{}", self.operate, digest);
        }
    }

    /// 重新计算事件 hash 名称，确保与 Python 端一致（name#HASH）
    pub fn refresh_hash_name(&mut self) {
        self.compute_hash_name();
    }

    pub fn matches_signals(&self, signals: Ref<HashSet<Signal>>) -> bool {
        // 创建一个信号映射表，key为信号的key部分，value为信号的value部分
        let mut signal_map: HashMap<String, String> = HashMap::new();
        for signal in signals.iter() {
            signal_map.insert(signal.key(), signal.value());
        }
        self.matches_signals_dict(&signal_map)
    }

    /// 基于字典的信号匹配逻辑，支持"任意"关键字
    pub fn matches_signals_dict(&self, signal_dict: &HashMap<String, String>) -> bool {
        // 1) signals_not: 任何一个匹配 -> 不满足
        for s_not in &self.signals_not {
            if s_not.is_match(signal_dict) {
                return false;
            }
        }

        // 2) signals_all: 必须全部满足
        for s_all in &self.signals_all {
            if !s_all.is_match(signal_dict) {
                return false;
            }
        }

        // 3) signals_any: 如果非空，至少满足一个
        if !self.signals_any.is_empty() {
            let any_matched = self
                .signals_any
                .iter()
                .any(|s_any| s_any.is_match(signal_dict));
            if !any_matched {
                return false;
            }
        }

        true
    }

    /// 序列化为字典
    pub fn dump(&self) -> serde_json::Value {
        serde_json::json!({
            "name": self.name,
            "operate": self.operate.to_chinese(),
            "signals_all": self.signals_all.iter().map(|s| format!("{s}")).collect::<Vec<_>>(),
            "signals_any": self.signals_any.iter().map(|s| format!("{s}")).collect::<Vec<_>>(),
            "signals_not": self.signals_not.iter().map(|s| format!("{s}")).collect::<Vec<_>>(),
        })
    }

    /// 从字典加载
    pub fn load(data: &serde_json::Value) -> anyhow::Result<Self> {
        let operate_str = data["operate"]
            .as_str()
            .ok_or_else(|| anyhow!("operate must be string"))?;

        let operate = match operate_str {
            "持多" | "HL" => Operate::HL,
            "持空" | "HS" => Operate::HS,
            "持币" | "HO" => Operate::HO,
            "开多" | "LO" => Operate::LO,
            "平多" | "LE" => Operate::LE,
            "开空" | "SO" => Operate::SO,
            "平空" | "SE" => Operate::SE,
            _ => return Err(anyhow!("Unknown operate: {operate_str}")),
        };

        let signals_all: Vec<Signal> = data
            .get("signals_all")
            .and_then(|v| v.as_array())
            .unwrap_or(&vec![])
            .iter()
            .map(|v| v.as_str().unwrap())
            .map(|s| s.parse())
            .collect::<Result<Vec<_>, _>>()?;

        let signals_any: Vec<Signal> = data
            .get("signals_any")
            .and_then(|v| v.as_array())
            .unwrap_or(&vec![])
            .iter()
            .map(|v| v.as_str().unwrap())
            .map(|s| s.parse())
            .collect::<Result<Vec<_>, _>>()?;

        let signals_not: Vec<Signal> = data
            .get("signals_not")
            .and_then(|v| v.as_array())
            .unwrap_or(&vec![])
            .iter()
            .map(|v| v.as_str().unwrap())
            .map(|s| s.parse())
            .collect::<Result<Vec<_>, _>>()?;

        let name = data
            .get("name")
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        Self::new(operate, signals_all, signals_any, signals_not, Some(name))
    }

    /// 返回一个迭代器，可以依次遍历 signals_all 和 signals_any 和 signals_not
    pub fn all_signals(&self) -> impl Iterator<Item = &Signal> {
        self.signals_all
            .iter()
            .chain(self.signals_any.iter().chain(self.signals_not.iter()))
    }
}

#[cfg(feature = "python")]
impl<'py> FromPyObject<'py> for Event {
    fn extract_bound(ob: &Bound<'py, pyo3::PyAny>) -> PyResult<Self> {
        // 接受 dict 形式输入
        if let Ok(dict) = ob.downcast::<PyDict>() {
            // 1) operate 必须存在
            let operate = dict
                .get_item("operate")?
                .ok_or(PyValueError::new_err("缺少字段: 'operate'"))?
                .extract::<Operate>()
                .map_err(|e| PyValueError::new_err(format!("无法解析字段 'operate': {e}")))?;

            // 2) name 可选，缺省为空字符串
            let name = match dict.get_item("name")? {
                Some(name) => name.extract::<String>().unwrap_or_default(),
                None => String::new(),
            };

            // 3) signals
            let signals_all = dict
                .get_item("signals_all")?
                .ok_or(PyValueError::new_err("缺少字段: 'signals_all'"))?
                .extract::<Vec<Signal>>()?;

            let signals_any = dict
                .get_item("signals_any")?
                .ok_or(PyValueError::new_err("缺少字段: 'signals_any'"))?
                .extract::<Vec<Signal>>()?;

            let signals_not = dict
                .get_item("signals_not")?
                .ok_or(PyValueError::new_err("缺少字段: 'signals_not'"))?
                .extract::<Vec<Signal>>()?;

            let mut event = Event {
                operate,
                signals_all,
                signals_any,
                signals_not,
                name,
                sha256: String::new(),
            };

            event.compute_hash_name();
            return Ok(event);
        }

        // 如果是 str
        if let Ok(s) = ob.extract::<String>() {
            let event = serde_json::from_str(&s)
                .map_err(|e| PyValueError::new_err(format!("str无法反序列化成 Event: {e}")))?;
            return Ok(event);
        }

        // 非 dict 类型：报错
        Err(PyValueError::new_err(
            "期望 dict：{ 'operate': ..., 'signals_all': [...], 'signals_any': [...], 'signals_not': [...], 'name': '...' }",
        ))
    }
}

/// Python可见的Event包装器
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(name = "Event", module = "czsc._native"))]
#[derive(Debug, Clone)]
pub struct PyEvent {
    pub inner: Event,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl PyEvent {
    #[new]
    #[pyo3(signature = (operate, signals_all = vec![], signals_any = vec![], signals_not = vec![], name = String::new()))]
    fn new_py(
        operate: PyOperate,
        signals_all: Vec<PySignal>,
        signals_any: Vec<PySignal>,
        signals_not: Vec<PySignal>,
        name: String,
    ) -> PyResult<Self> {
        let signals_all: Vec<Signal> = signals_all.into_iter().map(|s| s.inner).collect();
        let signals_any: Vec<Signal> = signals_any.into_iter().map(|s| s.inner).collect();
        let signals_not: Vec<Signal> = signals_not.into_iter().map(|s| s.inner).collect();

        let inner = Event::new(
            operate.inner,
            signals_all,
            signals_any,
            signals_not,
            Some(name),
        )
        .map_err(|e| PyValueError::new_err(format!("创建Event失败: {e}")))?;
        Ok(Self { inner })
    }

    #[classmethod]
    fn from_dict(
        _cls: &Bound<'_, pyo3::types::PyType>,
        dict: &Bound<'_, PyDict>,
    ) -> PyResult<Self> {
        let event = Event::extract_bound(dict.as_any())?;
        Ok(Self { inner: event })
    }

    #[classmethod]
    fn from_json(_cls: &Bound<'_, pyo3::types::PyType>, json_str: String) -> PyResult<Self> {
        let inner = serde_json::from_str(&json_str)
            .map_err(|e| PyValueError::new_err(format!("JSON解析失败: {e}")))?;
        Ok(Self { inner })
    }

    #[getter]
    fn operate(&self) -> PyOperate {
        PyOperate {
            inner: self.inner.operate,
        }
    }

    #[getter]
    fn signals_all(&self) -> Vec<PySignal> {
        self.inner
            .signals_all
            .iter()
            .map(|s| PySignal { inner: s.clone() })
            .collect()
    }

    #[getter]
    fn signals_any(&self) -> Vec<PySignal> {
        self.inner
            .signals_any
            .iter()
            .map(|s| PySignal { inner: s.clone() })
            .collect()
    }

    #[getter]
    fn signals_not(&self) -> Vec<PySignal> {
        self.inner
            .signals_not
            .iter()
            .map(|s| PySignal { inner: s.clone() })
            .collect()
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }

    /// 计算SHA8哈希值
    fn compute_sha8(&self) -> String {
        self.inner.compute_sha8()
    }

    /// 获取所有唯一信号（字符串格式，兼容原Python API）
    #[getter]
    fn unique_signals(&self) -> Vec<String> {
        let mut signals = HashSet::new();

        // 收集所有信号的字符串表示
        for signal in &self.inner.signals_all {
            signals.insert(signal.to_string());
        }
        for signal in &self.inner.signals_any {
            signals.insert(signal.to_string());
        }
        for signal in &self.inner.signals_not {
            signals.insert(signal.to_string());
        }

        signals.into_iter().collect()
    }

    /// 获取SHA256哈希
    #[getter]
    fn sha256(&self) -> String {
        self.inner.sha256.clone()
    }

    /// 判断事件是否匹配信号集合，返回是否匹配
    /// 支持多种参数类型：Dict[str, str] 或 Dict[str, Signal] 或 Vec<PySignal>
    fn is_match(&self, signals: &Bound<'_, pyo3::PyAny>) -> PyResult<bool> {
        if let Ok(dict) = signals.downcast::<PyDict>() {
            // 处理字典输入：转换为HashMap<String, String>
            let mut signal_dict = HashMap::new();
            for (key, value) in dict.iter() {
                let key_str = key.extract::<String>()?;
                let value_str = if let Ok(signal_obj) = value.extract::<PySignal>() {
                    // 值是PySignal对象，取其value
                    signal_obj.inner.value()
                } else if let Ok(signal_str) = value.extract::<String>() {
                    // 值是字符串
                    signal_str
                } else {
                    return Err(PyValueError::new_err("字典值必须是Signal对象或字符串"));
                };
                signal_dict.insert(key_str, value_str);
            }

            // 使用新的基于字典的匹配逻辑
            Ok(self.inner.matches_signals_dict(&signal_dict))
        } else if let Ok(vec) = signals.extract::<Vec<PySignal>>() {
            // 处理向量输入 - 转换为字典
            let mut signal_dict = HashMap::new();
            for signal in vec {
                signal_dict.insert(signal.inner.key(), signal.inner.value());
            }
            Ok(self.inner.matches_signals_dict(&signal_dict))
        } else {
            Err(PyValueError::new_err(
                "参数必须是 Dict[str, str] 或 Dict[str, Signal] 或 List[Signal]",
            ))
        }
    }

    /// 转换为JSON字符串
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner)
            .map_err(|e| PyValueError::new_err(format!("JSON序列化失败: {e}")))
    }

    fn __repr__(&self) -> String {
        format!(
            "PyEvent(operate={:?}, name='{}', signals_all={}, signals_any={}, signals_not={})",
            self.inner.operate,
            self.inner.name,
            self.inner.signals_all.len(),
            self.inner.signals_any.len(),
            self.inner.signals_not.len()
        )
    }

    fn __str__(&self) -> String {
        format!(
            "Event[{}]: {:?} (all:{}, any:{}, not:{})",
            self.inner.name,
            self.inner.operate,
            self.inner.signals_all.len(),
            self.inner.signals_any.len(),
            self.inner.signals_not.len()
        )
    }

    /// 导出为字典
    fn dump(&self) -> PyResult<PyObject> {
        let json_value = self.inner.dump();
        Python::with_gil(|py| {
            let dict = pyo3::types::PyDict::new(py);

            dict.set_item("name", json_value["name"].as_str().unwrap_or(""))?;
            dict.set_item("operate", json_value["operate"].as_str().unwrap_or(""))?;

            let empty_array = vec![];
            let signals_all: Vec<&str> = json_value["signals_all"]
                .as_array()
                .unwrap_or(&empty_array)
                .iter()
                .map(|v| v.as_str().unwrap_or(""))
                .collect();
            dict.set_item("signals_all", signals_all)?;

            let signals_any: Vec<&str> = json_value["signals_any"]
                .as_array()
                .unwrap_or(&empty_array)
                .iter()
                .map(|v| v.as_str().unwrap_or(""))
                .collect();
            dict.set_item("signals_any", signals_any)?;

            let signals_not: Vec<&str> = json_value["signals_not"]
                .as_array()
                .unwrap_or(&empty_array)
                .iter()
                .map(|v| v.as_str().unwrap_or(""))
                .collect();
            dict.set_item("signals_not", signals_not)?;

            Ok(dict.into())
        })
    }

    /// 从字典加载
    #[classmethod]
    fn load(_cls: &Bound<'_, pyo3::types::PyType>, data: &Bound<'_, PyDict>) -> PyResult<Self> {
        // 转换Python字典为JSON Value
        let json_str = Python::with_gil(|py| -> PyResult<String> {
            let json_module = py.import("json")?;
            let json_str = json_module.call_method1("dumps", (data,))?;
            json_str.extract::<String>()
        })?;

        let json_value: serde_json::Value = serde_json::from_str(&json_str)
            .map_err(|e| PyValueError::new_err(format!("JSON解析失败: {e}")))?;

        let inner = Event::load(&json_value)
            .map_err(|e| PyValueError::new_err(format!("Event加载失败: {e}")))?;
        Ok(Self { inner })
    }

    /// 获取信号配置
    fn get_signals_config(&self) -> Vec<String> {
        self.inner.all_signals().map(|s| s.to_string()).collect()
    }

    /// 支持 pickle 序列化 - 使用 __reduce__ 方法
    fn __reduce__(&self, py: Python) -> PyResult<PyObject> {
        use super::operate::PyOperate;
        use super::signal::PySignal;
        use pyo3::IntoPyObject;

        // 构造函数参数
        let operate = PyOperate {
            inner: self.inner.operate,
        };
        let signals_all: Vec<PySignal> = self
            .inner
            .signals_all
            .iter()
            .map(|s| PySignal { inner: s.clone() })
            .collect();
        let signals_any: Vec<PySignal> = self
            .inner
            .signals_any
            .iter()
            .map(|s| PySignal { inner: s.clone() })
            .collect();
        let signals_not: Vec<PySignal> = self
            .inner
            .signals_not
            .iter()
            .map(|s| PySignal { inner: s.clone() })
            .collect();

        let args = (
            operate,
            signals_all,
            signals_any,
            signals_not,
            self.inner.name.clone(),
        )
            .into_pyobject(py)?;

        // 返回 (constructor, args)
        let constructor = py.get_type::<Self>();
        let result = (constructor, args).into_pyobject(py)?;
        Ok(result.into())
    }
}
