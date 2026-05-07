use chrono::{DateTime, Datelike, Duration, NaiveDate, NaiveTime, Timelike, Utc};
use czsc_core::objects::{bar::RawBar, freq::Freq, market::Market};
use error_support::czsc_bail;
use hashbrown::HashMap;
use once_cell::sync::Lazy;
use polars::{frame::DataFrame, io::SerReader, prelude::IpcReader};
use std::{io::Cursor, str::FromStr};

use crate::errors::UtilsError;

static MINUTES_SPLIT_DF: Lazy<DataFrame> = Lazy::new(|| {
    // 将文件包含在二进制文件中
    const MINUTES_SPLIT_BYTES: &[u8] = include_bytes!("../data/minutes_split.feather");
    let cursor = Cursor::new(MINUTES_SPLIT_BYTES);
    IpcReader::new(cursor)
        .finish()
        .expect("failed to read minutes_split.feather")
});

static FREQ_EDT_MAP: Lazy<HashMap<(Market, Freq), HashMap<NaiveTime, NaiveTime>>> =
    Lazy::new(|| {
        let mut result: HashMap<(Market, Freq), HashMap<NaiveTime, NaiveTime>> = HashMap::new();

        let format = "%H:%M";

        // 按照market分组
        let groups = MINUTES_SPLIT_DF
            .partition_by(["market"], true)
            .expect("failed tp groupby markets");

        for g in groups {
            let market_type = g
                .column("market")
                .expect("failed to get market col")
                .str()
                .expect("failed to convert market col into str")
                .get(0)
                .expect("failed to get the first row for market col");
            let market_type = Market::from_str(market_type).expect("unregistered market type");

            // 遍历所有包含 "分钟" 的列名
            for minute in MINUTES_SPLIT_DF
                .get_column_names()
                .iter()
                .filter(|&col| col.contains("分钟"))
            {
                let time_col = g
                    .column("time")
                    .expect("failed to get time col")
                    .str()
                    .expect("failed to convert time col into str");
                let freq_of_time_col = g
                    .column(minute)
                    .expect("failed to get minute col")
                    .str()
                    .expect("failed to convert minute col into str");

                let mut time_map = HashMap::new();

                // 使用下标遍历确保不会遗漏数据
                for idx in 0..g.height() {
                    let time = time_col.get(idx).expect("failed to get idx of time col");
                    let freq_of_time = freq_of_time_col
                        .get(idx)
                        .expect("failed to get idx of minute col");

                    let time =
                        NaiveTime::parse_from_str(time, format).expect("failed to parse time str");
                    let freq_of_time = NaiveTime::parse_from_str(freq_of_time, format)
                        .expect("failed to parse time str");
                    time_map.insert(time, freq_of_time);
                }

                let minute_freq = Freq::from_str(minute).expect("unregistered freq");

                result.insert((market_type, minute_freq), time_map);
            }
        }
        result
    });

fn freq_market_times(freq: Freq, market: Market) -> Option<Vec<NaiveTime>> {
    let time_map = FREQ_EDT_MAP.get(&(market, freq))?;
    let mut times: Vec<NaiveTime> = time_map.keys().cloned().collect();
    times.sort();
    Some(times)
}

/// 依据分钟级 bars 的时间轴推断市场类型，对齐 Python `check_freq_and_market`。
///
/// 当显式 market 与 bars 的交易时间不匹配时，Python 会回退到 `默认`；
/// Rust 执行引擎也应按同一口径处理，否则会把基础周期错误地重采样到别的时间轴。
pub fn infer_market_from_bars(bars: &[RawBar], freq: Freq) -> Market {
    if !freq.is_minute_freq() {
        return Market::Default;
    }

    let mut time_seq: Vec<NaiveTime> = bars.iter().rev().take(2000).map(|b| b.dt.time()).collect();
    time_seq.sort();
    time_seq.dedup();
    if time_seq.len() < 2 {
        return Market::Default;
    }

    let min_time = *time_seq.first().unwrap();
    let max_time = *time_seq.last().unwrap();
    for market in [Market::AShare, Market::Futures, Market::Default] {
        let Some(times) = freq_market_times(freq, market) else {
            continue;
        };
        let sub_times: Vec<NaiveTime> = times
            .into_iter()
            .filter(|t| *t >= min_time && *t <= max_time)
            .collect();
        if sub_times == time_seq {
            return market;
        }
    }

    Market::Default
}

// #[allow(unused)]
// static FREQ_MARKET_TIMES: Lazy<HashMap<String, Vec<String>>> = Lazy::new(|| {
//     let mut result: HashMap<String, Vec<String>> = HashMap::new();

//     // 按照market分组
//     let groups = MINUTES_SPLIT_DF
//         .partition_by(["market"], true)
//         .expect("failed tp groupby markets");

//     for g in groups {
//         let market_type = g
//             .column("market")
//             .expect("failed to get market col")
//             .str()
//             .expect("failed to convert market col into str")
//             .get(0)
//             .expect("failed to get the first row for market col");

//         // 遍历所有包含 "分钟" 的列名
//         for minute in MINUTES_SPLIT_DF
//             .get_column_names()
//             .iter()
//             .filter(|&col| col.contains("分钟"))
//         {
//             let mut v: Vec<_> = MINUTES_SPLIT_DF
//                 .column(&minute)
//                 .expect("failed to get minute col")
//                 .str()
//                 .expect("failed to convert minute col into str")
//                 .into_iter()
//                 .flatten()
//                 .map(String::from)
//                 .collect();
//             // 去除连续的重复元素
//             v.dedup();

//             let key = format!("{}_{}", minute, market_type);
//             result.insert(key, v);
//         }
//     }

//     result
// });

/// 计算目标周期的结束时间(仅日期)
fn freq_end_date(dt: NaiveDate, freq: Freq) -> Result<NaiveDate, UtilsError> {
    match freq {
        Freq::D => Ok(dt),
        Freq::W => {
            // ISO weekday: 星期一是1, 星期日是7
            let weekday = dt.weekday().number_from_monday();
            // 计算到周五的天数
            let days_to_add = if weekday <= 5 {
                5 - weekday
            } else {
                // 周末到下个周五：7 - (weekday - 5) = 7 - weekday + 5 = 12 - weekday
                12 - weekday
            };
            Ok(dt + Duration::days(days_to_add as i64))
        }
        Freq::Y => {
            // 设置为12月31日
            NaiveDate::from_ymd_opt(dt.year(), 12, 31).ok_or_else(|| {
                UtilsError::InvalidFreqEndDate(format!("Y freq: year={}", dt.year()))
            })
        }
        Freq::M => {
            // 性能优化：直接计算月末日期，避免创建不必要的DateTime对象
            let year = dt.year();
            let month = dt.month();

            // 计算下个月的第一天，然后减去一天得到本月最后一天
            let (next_year, next_month) = if month == 12 {
                (year + 1, 1)
            } else {
                (year, month + 1)
            };

            // 直接创建下个月第一天的日期，然后减去一天
            NaiveDate::from_ymd_opt(next_year, next_month, 1)
                .ok_or_else(|| {
                    UtilsError::InvalidFreqEndDate(format!(
                        "M freq: next_year={next_year}, next_month={next_month}"
                    ))
                })?
                .pred_opt()
                .ok_or_else(|| {
                    UtilsError::InvalidFreqEndDate("M freq: failed to get previous day".to_string())
                })
        }
        Freq::S => {
            // 性能优化：直接计算季度末日期，避免创建不必要的DateTime对象
            let year = dt.year();
            let month = dt.month();

            // 确定下个季度的第一天
            let (next_quarter_year, next_quarter_month) = match month {
                1..=3 => (year, 4),       // Q1 -> Q2 starts in April
                4..=6 => (year, 7),       // Q2 -> Q3 starts in July
                7..=9 => (year, 10),      // Q3 -> Q4 starts in October
                10..=12 => (year + 1, 1), // Q4 -> Q1 next year starts in January
                _ => unreachable!(),
            };

            // 直接创建下个季度第一天，然后减去一天得到本季度最后一天
            NaiveDate::from_ymd_opt(next_quarter_year, next_quarter_month, 1)
                .ok_or_else(|| {
                    UtilsError::InvalidFreqEndDate(format!(
                        "S freq: next_quarter_year={next_quarter_year}, next_quarter_month={next_quarter_month}"
                    ))
                })?
                .pred_opt()
                .ok_or_else(|| {
                    UtilsError::InvalidFreqEndDate("S freq: failed to get previous day".to_string())
                })
        }
        // 对于其他周期，直接返回输入日期
        _ => Ok(dt),
    }
}

/// 计算目标周期的结束时间
pub fn freq_end_time(
    dt: DateTime<Utc>,
    freq: Freq,
    market: Market,
) -> Result<DateTime<Utc>, UtilsError> {
    // 如果秒>0 找下1分钟，但要确保不超出有效时间范围
    let dt = if dt.second() > 0 || dt.nanosecond() > 0 {
        dt.with_second(0).unwrap().with_nanosecond(0).unwrap() + Duration::minutes(1)
    } else {
        dt
    };

    // 获取时间的HH:MM格式，与Python版本保持一致
    let hm_str = dt.format("%H:%M").to_string();
    let utc_time = dt.time();

    // 如果是分钟周期
    if freq.is_minute_freq() {
        if let Some(time_map) = FREQ_EDT_MAP.get(&(market, freq))
            && let Some(end_time) = time_map.get(&utc_time)
        {
            // 直接使用UTC时间来计算结束时间
            let edt = dt
                .with_hour(end_time.hour())
                .ok_or(UtilsError::InvalidDateTime)?
                .with_minute(end_time.minute())
                .ok_or(UtilsError::InvalidDateTime)?;

            // 修正跨天逻辑：与Python版本保持一致
            // Python版本：if h == m == 0 and freq != Freq.F1 and hm != "00:00"
            if end_time.hour() == 0
                && end_time.minute() == 0
                && freq != Freq::F1
                && hm_str != "00:00"
            {
                // 特殊情况处理：如果结束时间是 00:00 但输入时间不是 00:00
                return Ok(edt + Duration::days(1));
            }
            // 直接返回UTC时间，不需要时区转换
            return Ok(edt);
        }

        // 如果直接查找失败，尝试用字符串解析的方式查找
        if let Some(time_map) = FREQ_EDT_MAP.get(&(market, freq)) {
            // 尝试用 HH:MM 字符串格式查找
            if let Ok(parsed_time) = NaiveTime::parse_from_str(&hm_str, "%H:%M")
                && let Some(end_time) = time_map.get(&parsed_time)
            {
                let edt = dt
                    .with_hour(end_time.hour())
                    .ok_or(UtilsError::InvalidDateTime)?
                    .with_minute(end_time.minute())
                    .ok_or(UtilsError::InvalidDateTime)?;

                if end_time.hour() == 0
                    && end_time.minute() == 0
                    && freq != Freq::F1
                    && hm_str != "00:00"
                {
                    return Ok(edt + Duration::days(1));
                }
                return Ok(edt);
            }
        }

        // 对于非交易时间，寻找下一个交易时间
        if let Some(time_map) = FREQ_EDT_MAP.get(&(market, freq)) {
            let mut available_times: Vec<_> = time_map.keys().collect();
            available_times.sort();

            // 寻找下一个交易时间
            if let Ok(current_time) = NaiveTime::parse_from_str(&hm_str, "%H:%M") {
                for &next_time in &available_times {
                    if next_time > &current_time
                        && let Some(end_time) = time_map.get(next_time)
                    {
                        let edt = dt
                            .with_hour(end_time.hour())
                            .ok_or(UtilsError::InvalidDateTime)?
                            .with_minute(end_time.minute())
                            .ok_or(UtilsError::InvalidDateTime)?;

                        if end_time.hour() == 0
                            && end_time.minute() == 0
                            && freq != Freq::F1
                            && hm_str != "00:00"
                        {
                            return Ok(edt + Duration::days(1));
                        }
                        return Ok(edt);
                    }
                }

                // 如果当天没有更晚的交易时间，使用第二天的第一个交易时间
                if let Some(&first_time) = available_times.first()
                    && let Some(end_time) = time_map.get(first_time)
                {
                    let next_day = dt + Duration::days(1);
                    let edt = next_day
                        .with_hour(end_time.hour())
                        .ok_or(UtilsError::InvalidDateTime)?
                        .with_minute(end_time.minute())
                        .ok_or(UtilsError::InvalidDateTime)?;
                    return Ok(edt);
                }
            }
        }

        czsc_bail!(
            "无法找到对应的结束时间: 时间={}, 频率={:?}, 市场={:?}",
            hm_str,
            freq,
            market
        )
    }

    // 对于非分钟级别的周期
    // 计算出新的结束日期
    let utc_date = freq_end_date(dt.date_naive(), freq)?;

    // Rust 中需要 DateTime 类型，所以统一使用 00:00:00 时间
    // 这样可以确保同一天内的所有基础周期K线都会更新同一根日线
    let edt = utc_date
        .and_hms_opt(0, 0, 0)
        .ok_or(UtilsError::InvalidDateTime)?
        .and_utc();

    // 直接返回UTC时间，不需要时区转换
    Ok(edt)
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{NaiveDateTime, TimeZone};

    // #[test]
    // fn test_datetime() {
    //     use chrono::{Local, TimeZone};
    //     // 2024/12/12 1:31
    //     let naive_datetime = NaiveDateTime::new(
    //         chrono::NaiveDate::from_ymd_opt(2024, 12, 12).unwrap(), // 年月日
    //         chrono::NaiveTime::from_hms_opt(1, 31, 0).unwrap(),     // 时分秒
    //     );

    //     // 2024/12/12 9:31 GMT+08:00
    //     let local_datetime = Local.from_utc_datetime(&naive_datetime);

    //     assert_eq!(
    //         local_datetime.naive_utc().to_string().as_str(),
    //         "2024-12-12 01:31:00"
    //     );
    //     assert_eq!(
    //         local_datetime.naive_local().to_string().as_str(),
    //         "2024-12-12 09:31:00"
    //     );
    // }

    #[test]
    fn test_daily_freq_end_time() {
        // 测试日线 freq_end_time 是否返回 00:00:00

        let test_cases = vec![
            ("2025-08-31 23:45:00", "2025-08-31 00:00:00"),
            ("2025-09-01 00:00:00", "2025-09-01 00:00:00"),
            ("2025-09-01 00:15:00", "2025-09-01 00:00:00"),
            ("2025-09-01 00:30:00", "2025-09-01 00:00:00"),
            ("2025-09-01 01:00:00", "2025-09-01 00:00:00"),
            ("2025-09-01 12:00:00", "2025-09-01 00:00:00"),
            ("2025-09-01 23:45:00", "2025-09-01 00:00:00"),
        ];

        for (input_str, expected_str) in test_cases {
            let input_dt = Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str(input_str, "%Y-%m-%d %H:%M:%S").unwrap(),
            );

            let expected_dt = Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str(expected_str, "%Y-%m-%d %H:%M:%S").unwrap(),
            );

            let result = freq_end_time(input_dt, Freq::D, Market::AShare).unwrap();

            assert_eq!(
                result, expected_dt,
                "\n输入: {input_str}\n期望: {expected_str}\n实际: {result}"
            );
        }

        println!("✅ 所有日线 freq_end_time 测试通过");
    }

    trait TestDateTime {
        /// 将DateTime格式化为字符串(不带时区后缀)
        /// 注：系统内部以 UTC 存储 CST 交易时间
        fn to_dt_str(&self) -> String;
    }

    impl TestDateTime for DateTime<Utc> {
        fn to_dt_str(&self) -> String {
            self.format("%Y-%m-%d %H:%M:%S").to_string()
        }
    }

    #[test]
    fn test_freq_minute() {
        // 系统内部以 UTC 存储 CST 交易时间（10:01 CST → 存为 10:01 UTC）
        let dt = Utc.from_utc_datetime(
            &NaiveDateTime::parse_from_str("2024-12-12 10:01:00", "%Y-%m-%d %H:%M:%S").unwrap(),
        );

        // 1分钟
        assert_eq!(
            freq_end_time(dt, Freq::F1, Market::AShare)
                .unwrap()
                .to_dt_str(),
            "2024-12-12 10:01:00"
        );

        // 5分钟
        assert_eq!(
            freq_end_time(dt, Freq::F5, Market::AShare)
                .unwrap()
                .to_dt_str(),
            "2024-12-12 10:05:00"
        );

        // 30分钟
        assert_eq!(
            freq_end_time(dt, Freq::F30, Market::AShare)
                .unwrap()
                .to_dt_str(),
            "2024-12-12 10:30:00"
        );

        // 60分钟
        assert_eq!(
            freq_end_time(dt, Freq::F60, Market::AShare)
                .unwrap()
                .to_dt_str(),
            "2024-12-12 10:30:00"
        );
    }

    /// 非分钟K线的测试(年线)
    #[test]
    fn test_freq_year() {
        let dt = Utc.from_utc_datetime(
            &NaiveDateTime::parse_from_str("2024-12-12 10:01:00", "%Y-%m-%d %H:%M:%S").unwrap(),
        );

        let res = freq_end_time(dt, Freq::Y, Market::AShare)
            .unwrap()
            .to_dt_str();

        // 非分钟周期的结束时间：日期设为年末(12/31)，时间固定为 00:00:00
        assert_eq!(res, "2024-12-31 00:00:00");
    }
}
