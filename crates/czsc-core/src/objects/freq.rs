#[cfg(feature = "python")]
use std::str::FromStr;

use strum_macros::{AsRefStr, Display, EnumIter, EnumString};

#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass_enum, gen_stub_pymethods};

#[cfg(feature = "python")]
use pyo3::types::PyDict;
#[cfg(feature = "python")]
use pyo3::{
    Bound, PyAny, PyErr, PyResult, Python,
    exceptions::PyValueError,
    pyclass, pymethods,
    types::{PyAnyMethods, PyString},
};
#[cfg(feature = "python")]
use pyo3::{IntoPyObject, Py};

/// 时间周期
#[cfg_attr(feature = "python", gen_stub_pyclass_enum)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(
    Debug,
    PartialOrd,
    Ord,
    Clone,
    Copy,
    PartialEq,
    EnumIter,
    EnumString,
    AsRefStr,
    Display,
    Eq,
    Hash,
    serde::Serialize,
    serde::Deserialize,
)]
pub enum Freq {
    /// 逐笔
    #[strum(serialize = "Tick")]
    Tick,
    /// 1分钟
    #[strum(serialize = "1分钟")]
    F1,
    /// 2分钟
    #[strum(serialize = "2分钟")]
    F2,
    /// 3分钟
    #[strum(serialize = "3分钟")]
    F3,
    /// 4分钟
    #[strum(serialize = "4分钟")]
    F4,
    /// 5分钟
    #[strum(serialize = "5分钟")]
    F5,
    /// 6分钟
    #[strum(serialize = "6分钟")]
    F6,
    /// 10分钟
    #[strum(serialize = "10分钟")]
    F10,
    /// 12分钟
    #[strum(serialize = "12分钟")]
    F12,
    /// 15分钟
    #[strum(serialize = "15分钟")]
    F15,
    /// 20分钟
    #[strum(serialize = "20分钟")]
    F20,
    /// 30分钟
    #[strum(serialize = "30分钟")]
    F30,
    /// 60分钟
    #[strum(serialize = "60分钟")]
    F60,
    /// 120分钟
    #[strum(serialize = "120分钟")]
    F120,
    /// 240分钟
    #[strum(serialize = "240分钟")]
    F240,
    /// 360分钟
    #[strum(serialize = "360分钟")]
    F360,
    /// 日线
    #[strum(serialize = "日线")]
    D,
    /// 周线
    #[strum(serialize = "周线")]
    W,
    /// 月线
    #[strum(serialize = "月线")]
    M,
    /// 季线
    #[strum(serialize = "季线")]
    S,
    /// 年线
    #[strum(serialize = "年线")]
    Y,
}

#[cfg(feature = "python")]
pub fn freqs_from_str(s: &str) -> Vec<Freq> {
    use strum::IntoEnumIterator;
    Freq::iter().filter(|&f| s.contains(f.as_ref())).collect()
}

impl Freq {
    /// 判断是否为分钟级别的周期
    pub fn is_minute_freq(&self) -> bool {
        matches!(
            self,
            Freq::F1
                | Freq::F2
                | Freq::F3
                | Freq::F4
                | Freq::F5
                | Freq::F6
                | Freq::F10
                | Freq::F12
                | Freq::F15
                | Freq::F20
                | Freq::F30
                | Freq::F60
                | Freq::F120
                | Freq::F240
                | Freq::F360
        )
    }

    /// 获取对应的分钟数
    pub fn minutes(&self) -> Option<i64> {
        match self {
            Freq::F1 => Some(1),
            Freq::F2 => Some(2),
            Freq::F3 => Some(3),
            Freq::F4 => Some(4),
            Freq::F5 => Some(5),
            Freq::F6 => Some(6),
            Freq::F10 => Some(10),
            Freq::F12 => Some(12),
            Freq::F15 => Some(15),
            Freq::F20 => Some(20),
            Freq::F30 => Some(30),
            Freq::F60 => Some(60),
            Freq::F120 => Some(120),
            Freq::F240 => Some(240),
            Freq::F360 => Some(360),
            _ => None,
        }
    }
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg(feature = "python")]
#[cfg_attr(feature = "python", pymethods)]
impl Freq {
    /// 支持深拷贝
    fn __deepcopy__(&self, _memo: &Bound<PyAny>) -> PyResult<Self> {
        Ok(*self)
    }

    /// 支持pickle序列化
    fn __reduce__(&self) -> PyResult<(Py<PyAny>, Py<PyAny>)> {
        Python::attach(|py| {
            let cls = py.get_type::<Self>();
            let args = (format!("{self:?}"),);
            Ok((cls.into(), args.into_pyobject(py)?.into_any().unbind()))
        })
    }

    #[new]
    fn new(value: &str) -> PyResult<Self> {
        Ok(match value {
            "Tick" | "逐笔" => Freq::Tick,
            "1分钟" | "F1" => Freq::F1,
            "2分钟" | "F2" => Freq::F2,
            "3分钟" | "F3" => Freq::F3,
            "4分钟" | "F4" => Freq::F4,
            "5分钟" | "F5" => Freq::F5,
            "6分钟" | "F6" => Freq::F6,
            "10分钟" | "F10" => Freq::F10,
            "12分钟" | "F12" => Freq::F12,
            "15分钟" | "F15" => Freq::F15,
            "20分钟" | "F20" => Freq::F20,
            "30分钟" | "F30" => Freq::F30,
            "60分钟" | "F60" => Freq::F60,
            "120分钟" | "F120" => Freq::F120,
            "240分钟" | "F240" => Freq::F240,
            "360分钟" | "F360" => Freq::F360,
            "日线" | "D" => Freq::D,
            "周线" | "W" => Freq::W,
            "月线" | "M" => Freq::M,
            "季线" | "S" => Freq::S,
            "年线" | "Y" => Freq::Y,
            _ => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Unknown freq value: {value}"
                )));
            }
        })
    }
    #[cfg(feature = "python")]
    #[getter]
    fn value(&self) -> &'static str {
        match self {
            Freq::Tick => "Tick",
            Freq::F1 => "1分钟",
            Freq::F2 => "2分钟",
            Freq::F3 => "3分钟",
            Freq::F4 => "4分钟",
            Freq::F5 => "5分钟",
            Freq::F6 => "6分钟",
            Freq::F10 => "10分钟",
            Freq::F12 => "12分钟",
            Freq::F15 => "15分钟",
            Freq::F20 => "20分钟",
            Freq::F30 => "30分钟",
            Freq::F60 => "60分钟",
            Freq::F120 => "120分钟",
            Freq::F240 => "240分钟",
            Freq::F360 => "360分钟",
            Freq::D => "日线",
            Freq::W => "周线",
            Freq::M => "月线",
            Freq::S => "季线",
            Freq::Y => "年线",
        }
    }

    fn __str__(&self) -> &'static str {
        self.value()
    }

    fn __repr__(&self) -> String {
        format!("Freq.{self:?}")
    }

    /// 返回 Rust variant 名（"F30" / "D" / "Tick" / ...），
    /// 对齐 Python `enum.Enum.name` 的习惯——便于在序列化、日志、
    /// 配置文件里使用稳定且语言无关的英文标识符。
    #[getter]
    fn name(&self) -> &'static str {
        match self {
            Freq::Tick => "Tick",
            Freq::F1 => "F1",
            Freq::F2 => "F2",
            Freq::F3 => "F3",
            Freq::F4 => "F4",
            Freq::F5 => "F5",
            Freq::F6 => "F6",
            Freq::F10 => "F10",
            Freq::F12 => "F12",
            Freq::F15 => "F15",
            Freq::F20 => "F20",
            Freq::F30 => "F30",
            Freq::F60 => "F60",
            Freq::F120 => "F120",
            Freq::F240 => "F240",
            Freq::F360 => "F360",
            Freq::D => "D",
            Freq::W => "W",
            Freq::M => "M",
            Freq::S => "S",
            Freq::Y => "Y",
        }
    }

    /// 用 derived `Hash` 暴露 `__hash__`：PyO3 不会自动从 Rust 端
    /// `#[derive(Hash)]` 派生 Python `__hash__`，且一旦写了 `__richcmp__`
    /// 又不显式给 `__hash__`，PyO3 会把 `__hash__` 显式设为 `None`，导致
    /// 实例不可哈希（无法做 dict/set 的 key）。这里显式实现以恢复
    /// 与 Python `enum.Enum` 一致的可哈希语义。
    fn __hash__(&self) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        self.hash(&mut hasher);
        hasher.finish()
    }

    #[classattr]
    fn __members__(py: Python) -> PyResult<Py<PyAny>> {
        let dict = PyDict::new(py);
        dict.set_item("Tick", Freq::Tick)?;
        dict.set_item("F1", Freq::F1)?;
        dict.set_item("F2", Freq::F2)?;
        dict.set_item("F3", Freq::F3)?;
        dict.set_item("F4", Freq::F4)?;
        dict.set_item("F5", Freq::F5)?;
        dict.set_item("F6", Freq::F6)?;
        dict.set_item("F10", Freq::F10)?;
        dict.set_item("F12", Freq::F12)?;
        dict.set_item("F15", Freq::F15)?;
        dict.set_item("F20", Freq::F20)?;
        dict.set_item("F30", Freq::F30)?;
        dict.set_item("F60", Freq::F60)?;
        dict.set_item("F120", Freq::F120)?;
        dict.set_item("F240", Freq::F240)?;
        dict.set_item("F360", Freq::F360)?;
        dict.set_item("D", Freq::D)?;
        dict.set_item("W", Freq::W)?;
        dict.set_item("M", Freq::M)?;
        dict.set_item("S", Freq::S)?;
        dict.set_item("Y", Freq::Y)?;
        Ok(dict.into())
    }

    fn __richcmp__(
        &self,
        other: pyo3::Bound<'_, pyo3::PyAny>,
        op: pyo3::basic::CompareOp,
    ) -> pyo3::PyResult<bool> {
        use pyo3::basic::CompareOp;
        match op {
            CompareOp::Eq => {
                if let Ok(other_freq) = other.extract::<Freq>() {
                    return Ok(*self == other_freq);
                }
                if let Ok(other_value) = other.getattr("value")
                    && let Ok(other_str) = other_value.extract::<String>()
                {
                    return Ok(self.value() == other_str.as_str());
                }
                Ok(false)
            }
            CompareOp::Ne => {
                if let Ok(other_freq) = other.extract::<Freq>() {
                    return Ok(*self != other_freq);
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

#[cfg(feature = "python")]
impl TryFrom<&Bound<'_, PyAny>> for Freq {
    type Error = PyErr;

    fn try_from(value: &Bound<'_, PyAny>) -> PyResult<Self> {
        if let Ok(py_str) = value.cast::<PyString>() {
            let py_str = py_str.to_string();
            Freq::from_str(&py_str)
                .map_err(|e| PyValueError::new_err(format!("解析成 Freq 失败: {e}")))
        } else if let Ok(self_) = value.extract::<Self>() {
            Ok(self_)
        } else {
            Err(PyValueError::new_err("无法解析 Freq 对象"))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::str::FromStr;

    #[test]
    fn test_string_to_freq() {
        // 测试从字符串解析为 Freq (EnumString)
        assert_eq!(Freq::from_str("Tick").unwrap(), Freq::Tick);
        assert_eq!(Freq::from_str("1分钟").unwrap(), Freq::F1);
        assert_eq!(Freq::from_str("15分钟").unwrap(), Freq::F15);
        assert_eq!(Freq::from_str("日线").unwrap(), Freq::D);
        assert_eq!(Freq::from_str("周线").unwrap(), Freq::W);
        assert_eq!(Freq::from_str("月线").unwrap(), Freq::M);
        assert_eq!(Freq::from_str("季线").unwrap(), Freq::S);
        assert_eq!(Freq::from_str("年线").unwrap(), Freq::Y);

        // 测试无效输入
        assert!(Freq::from_str("7分钟").is_err());
    }

    #[test]
    fn test_freq_to_string() {
        // 测试 Display trait
        assert_eq!(Freq::Tick.to_string(), "Tick");
        assert_eq!(Freq::F1.to_string(), "1分钟");
        assert_eq!(Freq::F15.to_string(), "15分钟");
        assert_eq!(Freq::D.to_string(), "日线");
        assert_eq!(Freq::W.to_string(), "周线");

        // 测试 AsRefStr trait
        assert_eq!(Freq::Tick.as_ref(), "Tick");
        assert_eq!(Freq::F1.as_ref(), "1分钟");
        assert_eq!(Freq::F15.as_ref(), "15分钟");
        assert_eq!(Freq::D.as_ref(), "日线");
        assert_eq!(Freq::W.as_ref(), "周线");
    }

    #[test]
    fn test_debug_format() {
        // 测试 Debug trait
        assert_eq!(format!("{:?}", Freq::Tick), "Tick");
        assert_eq!(format!("{:?}", Freq::F1), "F1");
        assert_eq!(format!("{:?}", Freq::D), "D");
        assert_eq!(format!("{:?}", Freq::W), "W");
    }

    #[test]
    fn test_clone_and_eq() {
        // 测试 Clone 和 PartialEq
        let freq1 = Freq::F15;
        let freq2 = freq1;
        assert_eq!(freq1, freq2);

        let freq3 = Freq::F30;
        assert_ne!(freq1, freq3);
    }
}
