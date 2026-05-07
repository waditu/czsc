//! Trading-time predicate. czsc-only addition; see docs/MIGRATION_NOTES.md §2.2.
//!
//! Inputs are interpreted as the market's local naive datetime (no tz
//! attached): A股 → CST, 港股 → HKT, crypto → any. The Python wrapper at
//! `czsc.is_trading_time` keeps the same contract.

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

/// Return true iff `dt` (local market time) falls inside the regular trading
/// session for `market`. Recognised values: `astock`, `hk`, `crypto`. Any
/// other string returns `false`.
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
            // HK lunch break: 12:00-13:00 (12:00 is closed)
            (hm_minutes(9, 30)..hm_minutes(12, 0)).contains(&m)
                || (hm_minutes(13, 0)..=hm_minutes(16, 0)).contains(&m)
        }
        _ => false,
    }
}
