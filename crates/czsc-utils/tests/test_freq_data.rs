//! Phase C.1 — RED test：freq_end_time + infer_market_from_bars 与
//! rs-czsc 47ef6efa 基线行为一致。

use std::sync::Arc;

use chrono::{TimeZone, Utc};
use czsc_core::objects::bar::{RawBar, RawBarBuilder};
use czsc_core::objects::freq::Freq;
use czsc_core::objects::market::Market;
use czsc_utils::freq_data::{freq_end_time, infer_market_from_bars};

#[test]
fn freq_end_time_returns_some_datetime_for_30min_default_market() {
    // 对于任意一个盘中分钟，我们只想确认 helper 调用成功，并且
    // 结果是非递减的（具体的分钟表编码在 minutes_split.feather 中，
    // 即 rs-czsc 基线）。
    let dt = Utc.with_ymd_and_hms(2024, 1, 8, 9, 30, 0).unwrap();
    let edt = freq_end_time(dt, Freq::F30, Market::Default).unwrap();
    assert!(edt >= dt, "edt {edt} must be >= input dt {dt}");
}

#[test]
fn freq_end_time_idempotent_when_already_at_boundary() {
    // 如果一次查询已经正好落在边界上，函数必须能 round-trip
    // （即再调一次应该返回同一个时刻）。
    let dt = Utc.with_ymd_and_hms(2024, 1, 8, 10, 0, 0).unwrap();
    let edt1 = freq_end_time(dt, Freq::F30, Market::Default).unwrap();
    let edt2 = freq_end_time(edt1, Freq::F30, Market::Default).unwrap();
    assert_eq!(edt1, edt2);
}

#[test]
fn freq_end_time_handles_daily_freq() {
    // 对更高级别的时间周期，函数仍然可以调用且不应 panic；
    // 具体的边界语义编码在 rs-czsc 里，我们这里只锁定调用返回 Ok。
    let dt = Utc.with_ymd_and_hms(2024, 1, 8, 14, 30, 0).unwrap();
    let _ = freq_end_time(dt, Freq::D, Market::Default).unwrap();
}

fn raw_bar(ts_secs: i64, freq: Freq) -> RawBar {
    RawBarBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts_secs, 0).unwrap())
        .freq(freq)
        .id(0)
        .open(10.0)
        .close(11.0)
        .high(12.0)
        .low(9.5)
        .vol(1000.0)
        .amount(1_000_000.0)
        .build()
        .unwrap()
}

#[test]
fn infer_market_returns_default_for_non_minute_freq() {
    let bars = vec![raw_bar(1_700_000_000, Freq::D)];
    assert_eq!(infer_market_from_bars(&bars, Freq::D), Market::Default);
}

#[test]
fn infer_market_returns_default_for_empty_bars() {
    let bars: Vec<RawBar> = Vec::new();
    assert_eq!(infer_market_from_bars(&bars, Freq::F30), Market::Default);
}
