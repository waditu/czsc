//! Phase D.10b — RED test: Signal type (`SignalRef<'static>` aka `Signal`)
//! parses from the canonical k1_k2_k3_v1_v2_v3_score string and exposes
//! `key()` / `value()` / Display per the rs-czsc contract.

use std::str::FromStr;

use czsc_core::objects::signal::Signal;

#[test]
fn parses_canonical_signal_string() {
    let raw = "30分钟_D1_前高_看多_强_任意_0";
    let s = Signal::from_str(raw).unwrap();
    // key drops "任意" parts; here all of k1/k2/k3 are concrete
    assert_eq!(s.key(), "30分钟_D1_前高");
    // value is v1_v2_v3_score
    assert_eq!(s.value(), "看多_强_任意_0");
}

#[test]
fn display_round_trips_full_signal() {
    let raw = "30分钟_D1_前高_看多_强_任意_0";
    let s = Signal::from_str(raw).unwrap();
    assert_eq!(s.to_string(), raw);
}

#[test]
fn rejects_malformed_string() {
    assert!(Signal::from_str("only_three_fields").is_err());
}

#[test]
fn equality_is_full_signal_string() {
    let a = Signal::from_str("30分钟_D1_前高_看多_强_任意_0").unwrap();
    let b = Signal::from_str("30分钟_D1_前高_看多_强_任意_0").unwrap();
    assert_eq!(a, b);
    let c = Signal::from_str("30分钟_D1_前高_看空_强_任意_0").unwrap();
    assert_ne!(a, c);
}

#[test]
fn key_skips_wildcards() {
    let s = Signal::from_str("任意_D1_前高_看多_强_任意_0").unwrap();
    // k1 is 任意 → dropped from key
    assert_eq!(s.key(), "D1_前高");
}

#[test]
fn is_match_obeys_score_and_wildcards() {
    use std::collections::HashMap;
    let s = Signal::from_str("30分钟_D1_前高_看多_强_任意_50").unwrap();
    let mut dict = HashMap::new();
    dict.insert("30分钟_D1_前高".to_string(), "看多_强_中_60".to_string());
    assert!(
        s.is_match(&dict),
        "score 60 >= 50 with v3 wildcard should match"
    );

    let mut low_score = HashMap::new();
    low_score.insert("30分钟_D1_前高".to_string(), "看多_强_中_40".to_string());
    assert!(!s.is_match(&low_score), "score 40 < 50 must not match");
}
