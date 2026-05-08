//! Phase C.3 — RED 测试：is_trading_time 覆盖 A股 / 港股 / crypto。
//!
//! 镜像 test/unit/test_trading_time.py（Phase A.6）锁定的用例。
//! 该函数为 czsc-only —— 见 docs/MIGRATION_NOTES.md §2.2。

use chrono::NaiveDate;
use czsc_utils::is_trading_time;

fn dt(y: i32, mo: u32, d: u32, h: u32, mi: u32) -> chrono::NaiveDateTime {
    NaiveDate::from_ymd_opt(y, mo, d)
        .unwrap()
        .and_hms_opt(h, mi, 0)
        .unwrap()
}

#[test]
fn astock_regular_session() {
    // 2024-01-08 是周一
    assert!(is_trading_time(dt(2024, 1, 8, 9, 30), "astock"));
    assert!(is_trading_time(dt(2024, 1, 8, 10, 0), "astock"));
    assert!(is_trading_time(dt(2024, 1, 8, 11, 30), "astock"));
    assert!(is_trading_time(dt(2024, 1, 8, 13, 0), "astock"));
    assert!(is_trading_time(dt(2024, 1, 8, 15, 0), "astock"));
}

#[test]
fn astock_lunch_break_and_off_hours() {
    assert!(!is_trading_time(dt(2024, 1, 8, 12, 30), "astock"));
    assert!(!is_trading_time(dt(2024, 1, 8, 15, 30), "astock"));
}

#[test]
fn astock_weekend_closed() {
    // 2024-01-06 是周六
    assert!(!is_trading_time(dt(2024, 1, 6, 10, 0), "astock"));
}

#[test]
fn hk_regular_session_and_lunch() {
    assert!(is_trading_time(dt(2024, 1, 8, 9, 30), "hk"));
    assert!(!is_trading_time(dt(2024, 1, 8, 12, 0), "hk"));
    assert!(is_trading_time(dt(2024, 1, 8, 16, 0), "hk"));
}

#[test]
fn crypto_always_open() {
    assert!(is_trading_time(dt(2024, 1, 6, 3, 0), "crypto"));
    assert!(is_trading_time(dt(2024, 12, 25, 0, 0), "crypto"));
}

#[test]
fn unknown_market_returns_false() {
    assert!(!is_trading_time(dt(2024, 1, 8, 10, 0), "unknown_xyz"));
}
