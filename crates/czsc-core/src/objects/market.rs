#[cfg(feature = "python")]
use pyo3::{exceptions::PyValueError, prelude::*, types::PyString};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass_enum, gen_stub_pymethods};
#[cfg(feature = "python")]
use std::str::FromStr;
use strum_macros::{AsRefStr, Display, EnumString};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, EnumString, AsRefStr, Display)]
#[cfg_attr(feature = "python", gen_stub_pyclass_enum)]
#[cfg_attr(
    feature = "python",
    pyclass(from_py_object, eq, eq_int, module = "czsc._native")
)]
pub enum Market {
    /// A股
    #[strum(serialize = "A股")]
    AShare,
    /// 期货
    #[strum(serialize = "期货")]
    Futures,
    /// 默认
    #[strum(serialize = "默认")]
    Default,
}

#[cfg(feature = "python")]
#[gen_stub_pymethods]
#[pymethods]
impl Market {
    #[new]
    fn from_py_any<'py>(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        Self::try_from(ob)
    }
}

#[cfg(feature = "python")]
impl TryFrom<&Bound<'_, PyAny>> for Market {
    type Error = PyErr;

    fn try_from(value: &Bound<'_, PyAny>) -> Result<Self, Self::Error> {
        if let Ok(py_str) = value.cast::<PyString>() {
            let py_str = py_str.to_string();
            Market::from_str(&py_str)
                .map_err(|e| PyValueError::new_err(format!("解析成 Market 失败: {e}")))
        } else if let Ok(self_) = value.extract::<Self>() {
            Ok(self_)
        } else {
            Err(PyValueError::new_err("无法解析 Market 对象"))
        }
    }
}
