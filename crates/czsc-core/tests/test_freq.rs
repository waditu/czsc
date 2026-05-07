//! Phase D.3 — RED test: Freq enum FromStr / Display, minutes() / is_minute_freq().

use std::str::FromStr;

use czsc_core::objects::freq::Freq;

#[test]
fn parses_minute_freqs() {
    assert_eq!(Freq::from_str("1分钟").unwrap(), Freq::F1);
    assert_eq!(Freq::from_str("30分钟").unwrap(), Freq::F30);
    assert_eq!(Freq::from_str("60分钟").unwrap(), Freq::F60);
}

#[test]
fn parses_higher_timeframes() {
    assert_eq!(Freq::from_str("日线").unwrap(), Freq::D);
    assert_eq!(Freq::from_str("周线").unwrap(), Freq::W);
    assert_eq!(Freq::from_str("月线").unwrap(), Freq::M);
}

#[test]
fn rejects_unknown_strings() {
    assert!(Freq::from_str("100分钟").is_err());
}

#[test]
fn display_round_trips() {
    assert_eq!(Freq::F30.to_string(), "30分钟");
    assert_eq!(Freq::D.to_string(), "日线");
}

#[test]
fn minutes_for_minute_freqs() {
    assert_eq!(Freq::F30.minutes(), Some(30));
    assert_eq!(Freq::F1.minutes(), Some(1));
    assert_eq!(Freq::F360.minutes(), Some(360));
}

#[test]
fn minutes_none_for_higher_timeframes() {
    assert_eq!(Freq::D.minutes(), None);
    assert_eq!(Freq::W.minutes(), None);
}

#[test]
fn is_minute_freq_classifies() {
    assert!(Freq::F30.is_minute_freq());
    assert!(Freq::F1.is_minute_freq());
    assert!(!Freq::D.is_minute_freq());
    assert!(!Freq::Tick.is_minute_freq());
}

#[test]
fn ordering_is_total_and_consistent() {
    // Freq derives PartialOrd + Ord. Minute timeframes should sort by enum
    // declaration order (rs-czsc baseline behaviour we are locking).
    assert!(Freq::F1 < Freq::F30);
    assert!(Freq::F30 < Freq::D);
}
