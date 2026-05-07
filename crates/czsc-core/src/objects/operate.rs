// czsc-only: rs-czsc's `operate.rs` carried a wide collection of unused
// imports (polars / log / rayon / sha2 / and forward references to
// event / position / signal). Since the file only really defines the
// `Operate` enum + its `PyOperate` wrapper, we trim the imports here to
// avoid pulling those heavy crates into czsc-core. The original
// `#![allow(unused)]` is kept for the few remaining unused items the
// upstream file carries. See docs/MIGRATION_NOTES.md §2.4.
#![allow(unused)]
use serde::{Deserialize, Serialize};
use std::fmt;
use std::str::FromStr;
use strum::IntoEnumIterator;
use strum_macros::{AsRefStr, EnumIter, EnumString};

#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::{
    Bound, FromPyObject, PyResult, Python, exceptions::PyValueError,
    types::PyAnyMethods,
};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

pub const ANY: &str = "任意";

#[derive(
    Clone, Copy, Debug, PartialEq, Hash, EnumString, EnumIter, AsRefStr, Serialize, Deserialize,
)]
pub enum Operate {
    /// Hold Long 持多
    #[serde(rename = "持多")]
    HL,
    /// Hold Short 持空
    #[serde(rename = "持空")]
    HS,
    /// Hold Other 持币
    #[serde(rename = "持币")]
    HO,
    /// Long Open 开多
    #[serde(rename = "开多")]
    LO,
    /// Long Exit 平多
    #[serde(rename = "平多")]
    LE,
    /// Short Open 开空
    #[serde(rename = "开空")]
    SO,
    /// Short Exit 平空
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
impl<'py> FromPyObject<'py> for Operate {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
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
#[cfg_attr(feature = "python", pyclass(name = "Operate", module = "czsc._native"))]
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
        format!("PyOperate::{:?}", self.inner)
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

    /// 支持pickle序列化
    fn __reduce__(&self, py: Python) -> PyResult<PyObject> {
        use pyo3::IntoPyObject;

        let class_method = py.get_type::<Self>().getattr("from_str")?;
        // 使用英文缩写而不是中文名称，因为from_str只解析英文
        let args = (self.inner.to_string(),).into_pyobject(py)?;
        let result = (class_method, args).into_pyobject(py)?;
        Ok(result.into())
    }
}
