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
///
/// naive datetime（无 tzinfo）的数值直接当 UTC 解释，不经过 .timestamp()
/// 的系统时区转换，与项目"市场本地时间以 UTC 数值存储"的约定一致。
#[cfg(feature = "python")]
pub fn parse_python_datetime(dt: &Bound<PyAny>) -> PyResult<DateTime<Utc>> {
    let py = dt.py();

    let datetime_utc = if dt.hasattr("timestamp")? {
        if dt.getattr("tzinfo")?.is_none() {
            // Naive datetime: 数值直接当 UTC，用 calendar.timegm 避免 .timestamp()
            // 引入系统时区偏移（如 UTC+8 上 15:00 → 07:00 的 bug）
            let calendar = py.import("calendar")?;
            let timetuple = dt.call_method0("timetuple")?;
            let secs: i64 = calendar.call_method1("timegm", (timetuple,))?.extract()?;
            let microsecond: u32 = dt.getattr("microsecond")?.extract()?;
            DateTime::from_timestamp(secs, microsecond * 1_000)
                .ok_or(ObjectError::Unexpected(anyhow!("Invalid datetime")))?
        } else {
            // Aware datetime: .timestamp() 已正确处理时区
            let ts: f64 = dt.call_method0("timestamp")?.extract()?;
            DateTime::from_timestamp(ts as i64, (ts.fract() * 1_000_000_000.0) as u32)
                .ok_or(ObjectError::Unexpected(anyhow!("Invalid datetime")))?
        }
    } else if let Ok(timestamp) = dt.extract::<i64>() {
        // 如果是时间戳（保持向后兼容）
        DateTime::from_timestamp(timestamp, 0).ok_or(ObjectError::Unexpected(anyhow!(
            "Invalid timestamp for building object"
        )))?
    } else if let Ok(ts) = dt.extract::<f64>() {
        DateTime::from_timestamp(ts as i64, (ts.fract() * 1_000_000_000.0) as u32)
            .ok_or(ObjectError::Unexpected(anyhow!("Invalid timestamp")))?
    } else {
        return Err(ObjectError::Unexpected(anyhow!(
            "dt must be datetime, Timestamp, or numeric timestamp"
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
