#[cfg(feature = "python")]
use pyo3::pyclass;
#[cfg(feature = "python")]
use pyo3::types::PyAnyMethods;
#[cfg(feature = "python")]
use pyo3::{Bound, IntoPyObject, Py, PyAny, PyErr, PyResult, Python, pymethods};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::gen_stub_pyclass_enum;
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::gen_stub_pymethods;
use strum_macros::{AsRefStr, Display, EnumString};

/// 方向
#[cfg_attr(feature = "python", gen_stub_pyclass_enum)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(
    Debug,
    Clone,
    Copy,
    PartialEq,
    EnumString,
    AsRefStr,
    Display,
    serde::Serialize,
    serde::Deserialize,
)]
pub enum Direction {
    /// 向上
    #[strum(serialize = "向上")]
    Up,
    /// 向下
    #[strum(serialize = "向下")]
    Down,
}
#[cfg(feature = "python")]
#[gen_stub_pymethods]
#[cfg(feature = "python")]
#[pymethods]
impl Direction {
    /// 支持深拷贝
    fn __deepcopy__(&self, _memo: &Bound<PyAny>) -> PyResult<Self> {
        Ok(*self)
    }

    /// 支持pickle序列化
    fn __reduce__(&self) -> PyResult<(Py<PyAny>, Py<PyAny>)> {
        Python::attach(|py| {
            let cls = py.get_type::<Self>();
            let args = match self {
                Direction::Up => ("Up",),
                Direction::Down => ("Down",),
            };
            Ok((cls.into(), args.into_pyobject(py)?.into_any().unbind()))
        })
    }

    #[new]
    fn new(value: &str) -> PyResult<Self> {
        Ok(match value {
            "Up" | "向上" => Direction::Up,
            "Down" | "向下" => Direction::Down,
            _ => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Unknown direction value: {value}"
                )));
            }
        })
    }

    /// 获取方向的字符串值（与 czsc 库兼容）
    #[getter]
    fn value(&self) -> &'static str {
        match self {
            Direction::Up => "向上",
            Direction::Down => "向下",
        }
    }

    fn __str__(&self) -> &'static str {
        self.value()
    }

    fn __repr__(&self) -> String {
        format!(
            "Direction.{}",
            match self {
                Direction::Up => "Up",
                Direction::Down => "Down",
            }
        )
    }

    fn __richcmp__(
        &self,
        other: pyo3::Bound<'_, pyo3::PyAny>,
        op: pyo3::basic::CompareOp,
    ) -> pyo3::PyResult<bool> {
        use pyo3::basic::CompareOp;
        match op {
            CompareOp::Eq => {
                if let Ok(other_dir) = other.extract::<Direction>() {
                    return Ok(*self == other_dir);
                }
                if let Ok(other_value) = other.getattr("value")
                    && let Ok(other_str) = other_value.extract::<String>()
                {
                    return Ok(self.value() == other_str.as_str());
                }
                Ok(false)
            }
            CompareOp::Ne => {
                if let Ok(other_dir) = other.extract::<Direction>() {
                    return Ok(*self != other_dir);
                }
                if let Ok(other_value) = other.getattr("value")
                    && let Ok(other_str) = other_value.extract::<String>()
                {
                    return Ok(self.value() != other_str.as_str());
                }
                Ok(true)
            }
            _ => Ok(false),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    #[test]
    fn test_string_to_direction() {
        // 测试从字符串解析为 Direction (EnumString)
        assert_eq!(Direction::from_str("向上").unwrap(), Direction::Up);
        assert_eq!(Direction::from_str("向下").unwrap(), Direction::Down);

        // 测试无效输入
        assert!(Direction::from_str("向左").is_err());
    }

    #[test]
    fn test_direction_to_string() {
        // 测试 Display trait
        assert_eq!(Direction::Up.to_string(), "向上");
        assert_eq!(Direction::Down.to_string(), "向下");

        // 测试 AsRefStr trait
        assert_eq!(Direction::Up.as_ref(), "向上");
        assert_eq!(Direction::Down.as_ref(), "向下");
    }

    #[test]
    fn test_debug_format() {
        // 测试 Debug trait
        assert_eq!(format!("{:?}", Direction::Up), "Up");
        assert_eq!(format!("{:?}", Direction::Down), "Down");
    }

    #[test]
    fn test_clone_and_eq() {
        // 测试 Clone 和 PartialEq
        let dir1 = Direction::Up;
        let dir2 = dir1;
        assert_eq!(dir1, dir2);

        let dir3 = Direction::Down;
        assert_ne!(dir1, dir3);
    }
}
