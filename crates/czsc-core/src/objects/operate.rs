// czsc-only: rs-czsc 的 `operate.rs` 里带了一大堆未使用的 import
// （polars / log / rayon / sha2 还有对 event / position / signal 的前向引用）。
// 由于这个文件实际上只定义了 `Operate` 枚举及其 `PyOperate` 包装器，
// 我们在这里裁剪掉这些 import，避免把那些重量级 crate 拉进 czsc-core。
// 原本的 `#![allow(unused)]` 保留下来，用于覆盖上游文件中尚存的少量
// 未使用项。参见 docs/MIGRATION_NOTES.md §2.4。
#![allow(unused)]
use serde::{Deserialize, Serialize};
use std::fmt;
use std::str::FromStr;
use strum::IntoEnumIterator;
use strum_macros::{AsRefStr, EnumIter, EnumString};

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::{Bound, FromPyObject, PyResult, Python, exceptions::PyValueError, types::PyAnyMethods};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

pub const ANY: &str = "任意";

#[derive(
    Clone, Copy, Debug, PartialEq, Eq, Hash, EnumString, EnumIter, AsRefStr, Serialize, Deserialize,
)]
pub enum Operate {
    /// 持多（Hold Long）
    #[serde(rename = "持多")]
    HL,
    /// 持空（Hold Short）
    #[serde(rename = "持空")]
    HS,
    /// 持币（Hold Other）
    #[serde(rename = "持币")]
    HO,
    /// 开多（Long Open）
    #[serde(rename = "开多")]
    LO,
    /// 平多（Long Exit）
    #[serde(rename = "平多")]
    LE,
    /// 开空（Short Open）
    #[serde(rename = "开空")]
    SO,
    /// 平空（Short Exit）
    #[serde(rename = "平空")]
    SE,
}

impl fmt::Display for Operate {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_ref())
    }
}

impl Operate {
    fn list_of_types() -> String {
        Self::iter()
            .map(|ot| ot.to_string())
            .collect::<Vec<_>>()
            .join(", ")
    }

    /// 返回操作类型的中文名称
    pub fn to_chinese(&self) -> &'static str {
        match self {
            Operate::HL => "持多",
            Operate::HS => "持空",
            Operate::HO => "持币",
            Operate::LO => "开多",
            Operate::LE => "平多",
            Operate::SO => "开空",
            Operate::SE => "平空",
        }
    }
}

#[cfg(feature = "python")]
impl<'py> FromPyObject<'_, 'py> for Operate {
    type Error = pyo3::PyErr;
    fn extract(ob: pyo3::Borrowed<'_, 'py, PyAny>) -> Result<Self, Self::Error> {
        if let Ok(s) = ob.extract::<String>() {
            let o = Self::from_str(&s).map_err(|_| {
                PyValueError::new_err(format!(
                    "无法解析 operate, 期望 str [ {} ]",
                    Self::list_of_types()
                ))
            })?;
            Ok(o)
        } else {
            Err(PyValueError::new_err(format!(
                "operate 类型不合法, 期望 str: [ {} ]",
                Self::list_of_types()
            )))
        }
    }
}

/// Python可见的Operate包装器
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(
    feature = "python",
    pyclass(from_py_object, name = "Operate", module = "czsc._native")
)]
#[derive(Debug, Clone)]
pub struct PyOperate {
    pub inner: Operate,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl PyOperate {
    #[allow(non_snake_case)]
    #[classattr]
    fn HL() -> PyOperate {
        PyOperate { inner: Operate::HL }
    }

    #[allow(non_snake_case)]
    #[classattr]
    fn HS() -> PyOperate {
        PyOperate { inner: Operate::HS }
    }

    #[allow(non_snake_case)]
    #[classattr]
    fn HO() -> PyOperate {
        PyOperate { inner: Operate::HO }
    }

    #[allow(non_snake_case)]
    #[classattr]
    fn LO() -> PyOperate {
        PyOperate { inner: Operate::LO }
    }

    #[allow(non_snake_case)]
    #[classattr]
    fn LE() -> PyOperate {
        PyOperate { inner: Operate::LE }
    }

    #[allow(non_snake_case)]
    #[classattr]
    fn SO() -> PyOperate {
        PyOperate { inner: Operate::SO }
    }

    #[allow(non_snake_case)]
    #[classattr]
    fn SE() -> PyOperate {
        PyOperate { inner: Operate::SE }
    }

    // 保留方法访问方式作为兼容性选项
    #[classmethod]
    fn hl(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Operate::HL }
    }

    #[classmethod]
    fn hs(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Operate::HS }
    }

    #[classmethod]
    fn ho(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Operate::HO }
    }

    #[classmethod]
    fn lo(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Operate::LO }
    }

    #[classmethod]
    fn le(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Operate::LE }
    }

    #[classmethod]
    fn so(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Operate::SO }
    }

    #[classmethod]
    fn se(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Operate::SE }
    }

    #[classmethod]
    fn from_str_py(_cls: &Bound<'_, pyo3::types::PyType>, s: String) -> PyResult<Self> {
        let inner = Operate::from_str(&s).map_err(|_| {
            PyValueError::new_err(format!(
                "无法解析操作类型: {}, 期望 [ {} ]",
                s,
                Operate::list_of_types()
            ))
        })?;
        Ok(Self { inner })
    }

    #[classmethod]
    fn from_str(_cls: &Bound<'_, pyo3::types::PyType>, s: String) -> PyResult<Self> {
        let inner = Operate::from_str(&s).map_err(|_| {
            PyValueError::new_err(format!(
                "无法解析操作类型: {}, 期望 [ {} ]",
                s,
                Operate::list_of_types()
            ))
        })?;
        Ok(Self { inner })
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        // 对齐 Python `enum.Enum` 的 `repr(EnumName.Variant) == "EnumName.Variant"` 约定，
        // 也与 Freq / Mark / Direction 的 __repr__ 形式一致；
        // 之前返回 "PyOperate::HL" 暴露了内部 Rust 结构名，是 pre-existing 不一致。
        format!("Operate.{:?}", self.inner)
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

    /// 兼容性属性：返回操作类型的中文字符串值
    #[getter]
    fn value(&self) -> String {
        self.inner.to_chinese().to_string()
    }

    /// 返回 Rust variant 名（"HL" / "HS" / "HO" / "LO" / "LE" / "SO" / "SE"），
    /// 对齐 Python `enum.Enum.name`：英文标识符稳定且与序列化路径
    /// (`from_str` / `to_string`) 一致，适合做配置 key / 日志短码。
    #[getter]
    fn name(&self) -> &'static str {
        match self.inner {
            Operate::HL => "HL",
            Operate::HS => "HS",
            Operate::HO => "HO",
            Operate::LO => "LO",
            Operate::LE => "LE",
            Operate::SO => "SO",
            Operate::SE => "SE",
        }
    }

    /// 支持pickle序列化
    fn __reduce__(&self, py: Python) -> PyResult<Py<PyAny>> {
        use pyo3::IntoPyObject;

        let class_method = py.get_type::<Self>().getattr("from_str")?;
        // 使用英文缩写而不是中文名称，因为from_str只解析英文
        let args = (self.inner.to_string(),).into_pyobject(py)?;
        let result = (class_method, args).into_pyobject(py)?;
        Ok(result.into())
    }
}
