// czsc-only: pyo3 imports gated behind the `python` feature (rs-czsc 47ef6efa
// relied on `#![allow(unused)]` to mask the bare imports when the feature was
// off; we make the gating explicit so czsc-core builds in non-python mode).
// See docs/MIGRATION_NOTES.md §2.4.
#![allow(unused)]
use anyhow::{Context, anyhow, bail};
use serde::{Deserialize, Deserializer, Serialize, Serializer, de::Visitor};
use std::borrow::Cow;
use std::fmt::{self, Display};
use std::hash::{Hash, Hasher};
use std::str::FromStr;

#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::{PyDict, PyDictMethods};
#[cfg(feature = "python")]
use pyo3::{IntoPyObject, Py, PyObject, PyResult, Python};

#[cfg(feature = "python")]
use super::operate::Operate;
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::gen_stub_pyfunction;
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};
pub(crate) const ANY: &str = "任意";

#[derive(Clone, Debug)]
pub struct SignalRef<'a> {
    // 完整的信号字符串
    signal: Cow<'a, str>,

    // 信号名称字段 (k1_k2_k3)
    k1: Cow<'a, str>,
    k2: Cow<'a, str>,
    k3: Cow<'a, str>,

    // 信号值字段 (v1_v2_v3)
    v1: Cow<'a, str>,
    v2: Cow<'a, str>,
    v3: Cow<'a, str>,

    // 分数
    score: i32,
}

impl<'a> Hash for SignalRef<'a> {
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.signal.hash(state);
    }
}

pub type Signal = SignalRef<'static>;

/// Python可见的Signal包装器
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(name = "Signal", module = "czsc._native"))]
#[derive(Debug, Clone)]
pub struct PySignal {
    pub(crate) inner: Signal,
}

impl PySignal {
    /// Wrap an inner [`Signal`] for Python exposure. The constructor is
    /// public so downstream crates (notably `czsc-python`'s signal
    /// dispatcher) can return signal objects without round-tripping
    /// through the string parser.
    pub fn from_inner(inner: Signal) -> Self {
        Self { inner }
    }
}

impl From<Signal> for PySignal {
    fn from(inner: Signal) -> Self {
        Self::from_inner(inner)
    }
}

impl FromStr for Signal {
    type Err = anyhow::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        // Python格式: k1_k2_k3_v1_v2_v3_score (7个部分，6个下划线)
        let parts: Vec<&str> = s.split('_').collect();
        if parts.len() != 7 {
            bail!("Signal格式无效：应该为 k1_k2_k3_v1_v2_v3_score 格式 (7个部分)")
        }

        // 验证score
        let score: i32 = parts[6].parse().context("无法解析score")?;
        if !(0..=100).contains(&score) {
            bail!("score 必须在0~100之间");
        }

        Ok(SignalRef {
            signal: Cow::Owned(s.to_string()),
            k1: Cow::Owned(parts[0].to_string()),
            k2: Cow::Owned(parts[1].to_string()),
            k3: Cow::Owned(parts[2].to_string()),
            v1: Cow::Owned(parts[3].to_string()),
            v2: Cow::Owned(parts[4].to_string()),
            v3: Cow::Owned(parts[5].to_string()),
            score,
        })
    }
}

impl<'a> SignalRef<'a> {
    /// 获取信号的key部分，按照Python逻辑过滤掉"任意"
    pub fn key(&self) -> String {
        let mut key_parts = Vec::new();
        for k in [&self.k1, &self.k2, &self.k3] {
            if k.as_ref() != ANY {
                key_parts.push(k.as_ref());
            }
        }
        if key_parts.is_empty() {
            String::new()
        } else {
            key_parts.join("_")
        }
    }

    /// 获取信号的value部分：v1_v2_v3_score
    pub fn value(&self) -> String {
        format!("{}_{}_{}_{}", self.v1, self.v2, self.v3, self.score)
    }

    /// 按照Python逻辑实现信号匹配
    pub fn is_match(&self, signal_dict: &std::collections::HashMap<String, String>) -> bool {
        let key = self.key();
        if let Some(value) = signal_dict.get(&key) {
            // 解析字典中的value为v1, v2, v3, score
            let value_parts: Vec<&str> = value.split('_').collect();
            if value_parts.len() != 4 {
                return false;
            }

            let (v1, v2, v3, score_str) = (
                value_parts[0],
                value_parts[1],
                value_parts[2],
                value_parts[3],
            );
            let score: i32 = score_str.parse().unwrap_or(0);

            // 匹配逻辑：score >= self.score 且各值匹配或为"任意"
            if score >= self.score
                && (v1 == self.v1.as_ref() || self.v1.as_ref() == ANY)
                && (v2 == self.v2.as_ref() || self.v2.as_ref() == ANY)
                && (v3 == self.v3.as_ref() || self.v3.as_ref() == ANY)
            {
                return true;
            }
        }
        false
    }
}

// 这个impl块在前面已经有了，删除这个重复的块

impl<'a> Display for SignalRef<'a> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}", self.signal)
    }
}

impl<'a> PartialEq for SignalRef<'a> {
    fn eq(&self, other: &Self) -> bool {
        self.signal == other.signal
    }
}

impl<'a> Eq for SignalRef<'a> {}

#[cfg(feature = "python")]
impl<'py> FromPyObject<'py> for Signal {
    fn extract_bound(ob: &Bound<'py, pyo3::PyAny>) -> PyResult<Self> {
        // 如果是 str，直接解析
        if let Ok(s) = ob.extract::<String>() {
            let signal = Self::from_str(&s).map_err(|err| {
                pyo3::exceptions::PyValueError::new_err(format!("无法解析 Signal：{err}"))
            })?;
            return Ok(signal);
        }

        // 非法类型
        Err(pyo3::exceptions::PyValueError::new_err(
            "期望 str：示例 'k1_k2_k3_v1_v2_v3_score'。",
        ))
    }
}

impl<'a> Serialize for SignalRef<'a> {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        serializer.serialize_str(&format!("{self}"))
    }
}

impl<'de> Deserialize<'de> for SignalRef<'static> {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        struct SignalVisitor<'a> {
            marker: std::marker::PhantomData<&'a ()>,
        }

        impl<'de, 'a> Visitor<'de> for SignalVisitor<'a> {
            type Value = SignalRef<'a>;

            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                f.write_str("键(3 个段)_值(4 个段，最后一段是分数)")
            }

            fn visit_str<E>(self, s: &str) -> Result<Self::Value, E>
            where
                E: serde::de::Error,
            {
                Signal::from_str(s).map_err(|e| E::custom(e))
            }
        }

        deserializer.deserialize_str(SignalVisitor {
            marker: std::marker::PhantomData,
        })
    }
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub(crate) struct ParsedSignalDoc {
    /// 参数模板，例如: Some("{freq}_D1_表里关系V230101")
    pub param_template: Option<String>,
    /// Signal 列表，顺序保留
    pub signals: Vec<Signal>,
}

/// 从 doc 中查找第一个参数模板以及所有 Signal('...') 字符串。
/// 实现思路：手工扫描（find + 索引切片），兼容中/英引号。
pub(crate) fn parse_signal_doc(doc: &str) -> ParsedSignalDoc {
    let mut param_template: Option<String> = None;
    let mut signals: Vec<Signal> = Vec::new();

    // Helper: 给定起始索引，查找第一个引号并提取匹配的内容（支持中英文引号）
    fn extract_quoted(s: &str, start: usize) -> Option<(String, usize)> {
        // 支持的开引号及其对应的闭引号
        let pairs: &[(char, char)] = &[
            ('"', '"'),
            ('\'', '\''),
            ('"', '"'),
            ('‘', '’'),
            // 兼容性：有时候会只有右侧引号，仍然处理成成对查找同字符
            ('"', '"'),
            ('’', '’'),
        ];
        let hay = &s[start..];
        let chars = hay.char_indices();
        // 找到第一个开引号（在 pairs 中）
        for (i, ch) in chars {
            if let Some(&(_, closing)) = pairs.iter().find(|(o, _)| *o == ch) {
                // 从 i+1 开始继续寻找 closing
                let rest = &hay[i + ch.len_utf8()..];
                if let Some(j) = rest.find(closing) {
                    let content = &rest[..j];
                    // 返回 content 以及全局结束索引 (start + i + len(open) + j + len(close))
                    let end_idx = start + i + ch.len_utf8() + j + closing.len_utf8();
                    return Some((content.to_string(), end_idx));
                } else {
                    // 未找到 matching closing，尝试继续扫描（放弃这个开引号）
                    continue;
                }
            }
        }
        None
    }

    // 1) 提取参数模板：标签可能是 "参数模板：" 或 "参数模板："（注意中文冒号）
    let label_candidates = ["参数模板：", "参数模板:"];
    if let Some((label_start, label)) = label_candidates
        .iter()
        .filter_map(|lab| doc.find(lab).map(|p| (p, *lab)))
        .min_by_key(|(p, _)| *p)
    {
        // 从 label 之后开始找首个引号内容
        let start_idx = label_start + label.len();
        if let Some((s, _end)) = extract_quoted(doc, start_idx) {
            // 可能含有左右空白，trim
            param_template = Some(s.trim().to_string());
        }
    }

    // 2) 提取所有 Signal(...) 内容（支持 Signal('...') 或 Signal("...")
    let mut pos = 0usize;
    let needle = "Signal(";
    while let Some(found) = doc[pos..].find(needle) {
        let abs = pos + found + needle.len(); // index right after "("
        if let Some((content, end_idx)) = extract_quoted(doc, abs) {
            let s = Signal::from_str(&content).ok();
            if let Some(signal) = s {
                signals.push(signal);
            }
            pos = end_idx; // 继续从结束位置后搜索
        } else {
            // 如果未能找到成对引号，跳过这个 "Signal(" 并继续向后查找，避免死循环
            pos = abs;
        }
    }

    ParsedSignalDoc {
        param_template,
        signals,
    }
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl PySignal {
    #[new]
    #[pyo3(signature = (*args, signal = None, key = None, value = None, k1 = None, k2 = None, k3 = None, v1 = None, v2 = None, v3 = None, score = None))]
    #[allow(clippy::too_many_arguments)]
    fn new_py(
        args: &Bound<'_, pyo3::types::PyTuple>,
        signal: Option<String>,
        key: Option<String>,
        value: Option<String>,
        k1: Option<String>,
        k2: Option<String>,
        k3: Option<String>,
        v1: Option<String>,
        v2: Option<String>,
        v3: Option<String>,
        score: Option<u8>,
    ) -> PyResult<Self> {
        // 首先检查位置参数
        if args.len() == 1 {
            // 如果有一个位置参数，当作signal字符串处理
            let signal_str: String = args.get_item(0)?.extract()?;
            let inner = Signal::from_str(&signal_str)
                .map_err(|e| PyValueError::new_err(format!("从位置参数创建Signal失败: {e}")))?;
            return Ok(Self { inner });
        } else if args.len() > 1 {
            return Err(PyValueError::new_err("Signal构造函数最多接受1个位置参数"));
        }
        // 方式1: 如果提供了signal参数，直接解析
        if let Some(signal_str) = signal {
            let inner = Signal::from_str(&signal_str)
                .map_err(|e| PyValueError::new_err(format!("从signal字符串创建Signal失败: {e}")))?;
            return Ok(Self { inner });
        }

        // 方式2: 如果提供了key和value，组合创建
        if let (Some(key_str), Some(value_str)) = (key, value) {
            // 重构key+value为完整的信号字符串
            let signal_str = format!("{key_str}_{value_str}");
            let inner = Signal::from_str(&signal_str)
                .map_err(|e| PyValueError::new_err(format!("从key+value创建Signal失败: {e}")))?;
            return Ok(Self { inner });
        }

        // 方式3: 如果提供了k1, k2, k3, v1, v2, v3, score，组合成signal字符串
        if k1.is_some()
            || k2.is_some()
            || k3.is_some()
            || v1.is_some()
            || v2.is_some()
            || v3.is_some()
            || score.is_some()
        {
            let k1_val = k1.unwrap_or_else(|| "任意".to_string());
            let k2_val = k2.unwrap_or_else(|| "任意".to_string());
            let k3_val = k3.unwrap_or_else(|| "任意".to_string());
            let v1_val = v1.unwrap_or_else(|| "任意".to_string());
            let v2_val = v2.unwrap_or_else(|| "任意".to_string());
            let v3_val = v3.unwrap_or_else(|| "任意".to_string());
            let score_val = score.unwrap_or(0);

            let signal_str =
                format!("{k1_val}_{k2_val}_{k3_val}_{v1_val}_{v2_val}_{v3_val}_{score_val}");

            let inner = Signal::from_str(&signal_str)
                .map_err(|e| PyValueError::new_err(format!("从分字段创建Signal失败: {e}")))?;
            return Ok(Self { inner });
        }

        // 默认情况：创建空的默认Signal
        let default_signal = "任意_任意_任意_任意_任意_任意_0";
        let inner = Signal::from_str(default_signal)
            .map_err(|e| PyValueError::new_err(format!("创建默认Signal失败: {e}")))?;
        Ok(Self { inner })
    }

    #[classmethod]
    fn from_string(_cls: &Bound<'_, pyo3::types::PyType>, s: String) -> PyResult<Self> {
        let inner = Signal::from_str(&s).map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("从字符串解析Signal失败: {e}"))
        })?;
        Ok(Self { inner })
    }

    #[getter]
    fn key(&self) -> String {
        self.inner.key().to_string()
    }

    #[getter]
    fn value(&self) -> String {
        self.inner.value().to_string()
    }

    #[getter]
    fn k3(&self) -> String {
        self.inner.k3.to_string()
    }

    #[getter]
    fn v1(&self) -> String {
        self.inner.v1.to_string()
    }

    #[getter]
    fn v2(&self) -> String {
        self.inner.v2.to_string()
    }

    #[getter]
    fn v3(&self) -> String {
        self.inner.v3.to_string()
    }

    #[getter]
    fn score(&self) -> i32 {
        self.inner.score
    }

    /// 新增k1和k2属性getter，匹配Python版本
    #[getter]
    fn k1(&self) -> String {
        self.inner.k1.to_string()
    }

    #[getter]
    fn k2(&self) -> String {
        self.inner.k2.to_string()
    }

    /// 添加to_json方法以匹配Python版本
    fn to_json(&self) -> String {
        format!("{}", self.inner)
    }

    fn __str__(&self) -> String {
        format!("Signal('{}')", self.inner)
    }

    fn __repr__(&self) -> String {
        format!("Signal('{}')", self.inner)
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.inner.hash(&mut hasher);
        hasher.finish()
    }

    /// 检查Signal是否匹配另一个Signal
    fn matches(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// 判断信号是否与信号字典中的值匹配（Python版本is_match逻辑）
    fn is_match(&self, signals_dict: std::collections::HashMap<String, String>) -> PyResult<bool> {
        let key = self.inner.key();
        let value = signals_dict
            .get(&key)
            .ok_or_else(|| PyValueError::new_err(format!("{key} 不在信号列表中")))?;

        let parts: Vec<&str> = value.split('_').collect();
        if parts.len() != 4 {
            return Err(PyValueError::new_err("信号值格式错误"));
        }

        let v1 = parts[0];
        let v2 = parts[1];
        let v3 = parts[2];
        let score: i32 = parts[3]
            .parse()
            .map_err(|_| PyValueError::new_err("分数解析失败"))?;

        let self_v1 = self.inner.v1.as_ref();
        let self_v2 = self.inner.v2.as_ref();
        let self_v3 = self.inner.v3.as_ref();
        let self_score = self.inner.score;

        // Python版本匹配逻辑
        if score >= self_score
            && (v1 == self_v1 || self_v1 == "任意")
            && (v2 == self_v2 || self_v2 == "任意")
            && (v3 == self_v3 || self_v3 == "任意")
        {
            return Ok(true);
        }

        Ok(false)
    }

    /// 获取Signal的完整字符串表示
    #[allow(clippy::inherent_to_string)]
    fn to_string(&self) -> String {
        format!("{}", self.inner)
    }
}

/// Python可见的ParsedSignalDoc包装器
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(name = "ParsedSignalDoc", module = "czsc._native"))]
#[derive(Debug, Clone)]
pub struct PyParsedSignalDoc {
    pub(crate) inner: ParsedSignalDoc,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl PyParsedSignalDoc {
    #[getter]
    fn param_template(&self) -> Option<String> {
        self.inner.param_template.clone()
    }

    #[getter]
    fn signals(&self) -> Vec<PySignal> {
        self.inner
            .signals
            .iter()
            .map(|s| PySignal { inner: s.clone() })
            .collect()
    }

    fn __repr__(&self) -> String {
        format!(
            "PyParsedSignalDoc(param_template={:?}, signals_count={})",
            self.inner.param_template,
            self.inner.signals.len()
        )
    }
}

/// 解析文档中的Signal信息
#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pyfunction)]
#[pyfunction(name = "parse_signal_doc")]
pub fn parse_signal_doc_py(doc: String) -> PyParsedSignalDoc {
    let inner = parse_signal_doc(&doc);
    PyParsedSignalDoc { inner }
}
