use crate::objects::freq::Freq;
use chrono::{DateTime, Utc};

#[cfg(feature = "python")]
use crate::objects::errors::ObjectError;
#[cfg(feature = "python")]
use anyhow::anyhow;
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::PyAnyMethods;

/// 创建 OrderedDict，与 czsc 库兼容
#[cfg(feature = "python")]
pub fn create_ordered_dict(py: Python) -> PyResult<Py<PyAny>> {
    let collections = py.import("collections")?;
    let ordered_dict = collections.getattr("OrderedDict")?;
    let result = ordered_dict.call0()?;
    Ok(result.into())
}

/// 创建不带时区信息的 pandas Timestamp，与原版CZSC保持一致
#[cfg(feature = "python")]
pub fn create_naive_pandas_timestamp(py: Python, dt: DateTime<chrono::Utc>) -> PyResult<Py<PyAny>> {
    let pandas = py.import("pandas")?;
    let timestamp_cls = pandas.getattr("Timestamp")?;
    let dt_naive = dt.naive_utc();
    let iso_string = dt_naive.format("%Y-%m-%d %H:%M:%S").to_string();

    // 创建不带时区的naive时间戳
    let ts = timestamp_cls.call((iso_string,), None)?;

    Ok(ts.into())
}

/// 通用的日期时间解析函数，支持多种Python日期时间格式
/// 这个函数被RawBar、NewBar和FX共同使用，避免重复代码
#[cfg(feature = "python")]
pub fn parse_python_datetime(dt: &Bound<PyAny>) -> PyResult<DateTime<Utc>> {
    // 尝试解析dt参数，支持多种输入格式
    let datetime_utc = if dt.hasattr("timestamp")? {
        // 如果是Python datetime对象（有timestamp方法）
        let timestamp = dt.call_method0("timestamp")?;
        let timestamp_f64: f64 = timestamp.extract()?;
        DateTime::from_timestamp(
            timestamp_f64 as i64,
            (timestamp_f64.fract() * 1_000_000_000.0) as u32,
        )
        .ok_or(ObjectError::Unexpected(anyhow!(
            "Invalid datetime for building object"
        )))?
    } else if dt.hasattr("tz_localize")? {
        // 如果是pandas Timestamp，可能没有时区信息
        let localized_dt = if dt.getattr("tz")?.is_none() {
            // 如果没有时区，添加UTC时区
            dt.call_method1("tz_localize", ("UTC",))?
        } else {
            dt.clone()
        };
        let timestamp = localized_dt.call_method0("timestamp")?;
        let timestamp_f64: f64 = timestamp.extract()?;
        DateTime::from_timestamp(
            timestamp_f64 as i64,
            (timestamp_f64.fract() * 1_000_000_000.0) as u32,
        )
        .ok_or(ObjectError::Unexpected(anyhow!(
            "Invalid datetime for building object"
        )))?
    } else if let Ok(timestamp) = dt.extract::<i64>() {
        // 如果是时间戳（保持向后兼容）
        DateTime::from_timestamp(timestamp, 0).ok_or(ObjectError::Unexpected(anyhow!(
            "Invalid timestamp for building object"
        )))?
    } else if let Ok(timestamp_f64) = dt.extract::<f64>() {
        // 如果是浮点数时间戳
        DateTime::from_timestamp(
            timestamp_f64 as i64,
            (timestamp_f64.fract() * 1_000_000_000.0) as u32,
        )
        .ok_or(ObjectError::Unexpected(anyhow!(
            "Invalid timestamp for building object"
        )))?
    } else {
        return Err(ObjectError::Unexpected(anyhow!(
            "dt parameter must be a Python datetime object, pandas Timestamp, integer timestamp, or float timestamp"
        ))
        .into());
    };

    Ok(datetime_utc)
}

/// 将频率枚举转换为中文字符串
/// 这个函数被多个结构体的Python绑定共同使用，避免重复代码
pub fn freq_to_chinese_string(freq: Freq) -> &'static str {
    match freq {
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
