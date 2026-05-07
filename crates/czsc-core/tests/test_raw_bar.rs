//! Phase D.5 — RED test: RawBar must construct via RawBarBuilder, expose
//! upper/lower/solid (non-python builds), and round-trip equality based on
//! the rs-czsc-defined fields.

use chrono::{TimeZone, Utc};
use czsc_core::objects::bar::{RawBar, RawBarBuilder};
use czsc_core::objects::freq::Freq;

fn sample(open: f64, close: f64, high: f64, low: f64) -> RawBar {
    RawBarBuilder::default()
        .symbol("000001")
        .dt(Utc.with_ymd_and_hms(2024, 1, 8, 9, 30, 0).unwrap())
        .freq(Freq::F30)
        .id(0)
        .open(open)
        .close(close)
        .high(high)
        .low(low)
        .vol(1000.0_f64)
        .amount(1_000_000.0_f64)
        .build()
        .unwrap()
}

#[test]
fn builder_populates_fields() {
    let bar = sample(10.0, 11.0, 12.0, 9.5);
    assert_eq!(&*bar.symbol, "000001");
    assert_eq!(bar.freq, Freq::F30);
    assert_eq!(bar.open, 10.0);
    assert_eq!(bar.close, 11.0);
    assert_eq!(bar.high, 12.0);
    assert_eq!(bar.low, 9.5);
}

#[test]
fn upper_shadow_is_high_minus_max_of_open_close() {
    let bar = sample(10.0, 11.0, 12.0, 9.0);
    // max(open, close) = 11; upper = 12 - 11 = 1
    assert_eq!(bar.upper(), 1.0);
}

#[test]
fn lower_shadow_is_min_of_open_close_minus_low() {
    let bar = sample(10.0, 11.0, 12.0, 9.0);
    // min(open, close) = 10; lower = 10 - 9 = 1
    assert_eq!(bar.lower(), 1.0);
}

#[test]
fn solid_is_abs_diff_of_open_close() {
    let bull = sample(10.0, 11.0, 12.0, 9.0);
    let bear = sample(11.0, 10.0, 12.0, 9.0);
    assert!((bull.solid() - 1.0).abs() < f64::EPSILON);
    assert!((bear.solid() - 1.0).abs() < f64::EPSILON);
}

#[test]
fn equality_matches_rs_czsc_baseline() {
    let a = sample(10.0, 11.0, 12.0, 9.0);
    let b = sample(10.0, 11.0, 12.0, 9.0);
    assert_eq!(a, b);
}
