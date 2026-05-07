//! Phase D.10c — RED test: Event struct constructs from Operate + signals,
//! computes a stable sha8 hash, refresh_hash_name keeps it in sync, and
//! all_signals iterates the union.

use std::str::FromStr;

use czsc_core::objects::event::Event;
use czsc_core::objects::operate::Operate;
use czsc_core::objects::signal::Signal;

fn sample_event() -> Event {
    Event {
        operate: Operate::LO,
        signals_all: vec![
            Signal::from_str("30分钟_D1_前高_看多_强_任意_0").unwrap(),
        ],
        signals_any: vec![
            Signal::from_str("日线_D1_趋势_看多_中_任意_0").unwrap(),
            Signal::from_str("日线_D2_趋势_看多_弱_任意_0").unwrap(),
        ],
        signals_not: vec![],
        name: String::new(),
        sha256: String::new(),
    }
}

#[test]
fn struct_holds_signals() {
    let e = sample_event();
    assert_eq!(e.signals_all.len(), 1);
    assert_eq!(e.signals_any.len(), 2);
    assert_eq!(e.signals_not.len(), 0);
    assert_eq!(e.operate, Operate::LO);
}

#[test]
fn compute_sha8_returns_4_hex_chars() {
    let e = sample_event();
    let h = e.compute_sha8();
    assert_eq!(h.len(), 4, "sha8 prefix must be 4 chars, got {h:?}");
    assert!(h.chars().all(|c| c.is_ascii_hexdigit() && c.is_ascii_uppercase() || c.is_ascii_digit()),
        "expected uppercase hex, got {h:?}");
}

#[test]
fn compute_sha8_is_deterministic() {
    let e = sample_event();
    let a = e.compute_sha8();
    let b = e.compute_sha8();
    assert_eq!(a, b, "sha8 must be a pure function of the event payload");
}

#[test]
fn refresh_hash_name_updates_sha256_field() {
    let mut e = sample_event();
    assert_eq!(e.sha256, "");
    e.refresh_hash_name();
    assert!(!e.sha256.is_empty(), "refresh should populate sha256");
}

#[test]
fn all_signals_iterates_union() {
    let e = sample_event();
    let all: Vec<_> = e.all_signals().collect();
    // 1 (signals_all) + 2 (signals_any) + 0 (signals_not) = 3
    assert_eq!(all.len(), 3);
}

#[test]
fn dump_load_roundtrip_via_json() {
    let mut e = sample_event();
    e.refresh_hash_name();
    let dumped = e.dump();
    let loaded = Event::load(&dumped).unwrap();
    assert_eq!(loaded.operate, e.operate);
    assert_eq!(loaded.signals_all.len(), e.signals_all.len());
    assert_eq!(loaded.signals_any.len(), e.signals_any.len());
}
