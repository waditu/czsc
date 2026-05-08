//! 交易时间判定。czsc-only 新增；详见 docs/MIGRATION_NOTES.md §2.2。
//!
//! 输入按市场本地的 naive datetime 解释（不附带 tz）：
//! A股 → CST，港股 → HKT，crypto → 任意。Python wrapper
//! `czsc.is_trading_time` 保持相同的契约。

use chrono::{Datelike, NaiveDateTime, Timelike, Weekday};

const MIN_PER_HOUR: u32 = 60;

const fn hm_minutes(h: u32, m: u32) -> u32 {
    h * MIN_PER_HOUR + m
}

fn minute_of_day(dt: &NaiveDateTime) -> u32 {
    hm_minutes(dt.hour(), dt.minute())
}

fn is_weekday(dt: &NaiveDateTime) -> bool {
    !matches!(dt.weekday(), Weekday::Sat | Weekday::Sun)
}

/// 当且仅当 `dt`（市场本地时间）落在 `market` 的常规交易时段内时返回 true。
/// 识别的取值：`astock`、`hk`、`crypto`。其他字符串一律返回 `false`。
pub fn is_trading_time(dt: NaiveDateTime, market: &str) -> bool {
    match market {
        "crypto" => true,
        "astock" => {
            if !is_weekday(&dt) {
                return false;
            }
            let m = minute_of_day(&dt);
            (hm_minutes(9, 30)..=hm_minutes(11, 30)).contains(&m)
                || (hm_minutes(13, 0)..=hm_minutes(15, 0)).contains(&m)
        }
        "hk" => {
            if !is_weekday(&dt) {
                return false;
            }
            let m = minute_of_day(&dt);
            // 港股午休：12:00-13:00（12:00 已闭市）
            (hm_minutes(9, 30)..hm_minutes(12, 0)).contains(&m)
                || (hm_minutes(13, 0)..=hm_minutes(16, 0)).contains(&m)
        }
        _ => false,
    }
}
