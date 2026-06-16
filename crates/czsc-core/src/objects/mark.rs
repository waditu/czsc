use strum_macros::{AsRefStr, Display, EnumString};

#[cfg(feature = "python")]
use pyo3::pyclass;
#[cfg(feature = "python")]
use pyo3::pymethods;
#[cfg(feature = "python")]
use pyo3::types::PyAnyMethods;
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::gen_stub_pyclass_enum;
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::gen_stub_pymethods;

/// 分型类型
#[cfg_attr(feature = "python", gen_stub_pyclass_enum)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(
    Debug, Clone, PartialEq, EnumString, AsRefStr, Display, serde::Serialize, serde::Deserialize,
)]
pub enum Mark {
    /// 底分型
    #[strum(serialize = "底分型")]
    D,
    /// 顶分型
    #[strum(serialize = "顶分型")]
    G,
}
#[cfg(feature = "python")]
#[gen_stub_pymethods]
#[cfg(feature = "python")]
#[pymethods]
impl Mark {
    /// 获取标记的字符串值（与 czsc 库兼容）
    #[getter]
    fn value(&self) -> &'static str {
        match self {
            Mark::G => "顶分型",
            Mark::D => "底分型",
        }
    }

    fn __str__(&self) -> &'static str {
        self.value()
    }

    fn __repr__(&self) -> String {
        format!(
            "Mark.{}",
            match self {
                Mark::G => "G",
                Mark::D => "D",
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
                if let Ok(other_mark) = other.extract::<Mark>() {
                    return Ok(*self == other_mark);
                }
                if let Ok(other_value) = other.getattr("value")
                    && let Ok(other_str) = other_value.extract::<String>()
                {
                    return Ok(self.value() == other_str.as_str());
                }
                Ok(false)
            }
            CompareOp::Ne => {
                if let Ok(other_mark) = other.extract::<Mark>() {
                    return Ok(*self != other_mark);
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
    fn test_string_to_mark() {
        // 测试从字符串解析为 Mark (EnumString)
        assert_eq!(Mark::from_str("底分型").unwrap(), Mark::D);
        assert_eq!(Mark::from_str("顶分型").unwrap(), Mark::G);

        // 测试无效输入
        assert!(Mark::from_str("中分型").is_err());
    }

    #[test]
    fn test_mark_to_string() {
        // 测试 Display trait
        assert_eq!(Mark::D.to_string(), "底分型");
        assert_eq!(Mark::G.to_string(), "顶分型");

        // 测试 AsRefStr trait
        assert_eq!(Mark::D.as_ref(), "底分型");
        assert_eq!(Mark::G.as_ref(), "顶分型");
    }

    #[test]
    fn test_debug_format() {
        // 测试 Debug trait
        assert_eq!(format!("{:?}", Mark::D), "D");
        assert_eq!(format!("{:?}", Mark::G), "G");
    }

    #[test]
    fn test_clone_and_eq() {
        // 测试 Clone 和 PartialEq
        let mark1 = Mark::D;
        let mark2 = mark1.clone();
        assert_eq!(mark1, mark2);

        let mark3 = Mark::G;
        assert_ne!(mark1, mark3);
    }
}
