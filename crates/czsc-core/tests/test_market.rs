//! Phase D.2 — RED test: Market enum parses Chinese names via FromStr,
//! formats back through Display, and survives equality / hash semantics.

use std::str::FromStr;

use czsc_core::objects::market::Market;

#[test]
fn parses_chinese_names() {
    assert_eq!(Market::from_str("A股").unwrap(), Market::AShare);
    assert_eq!(Market::from_str("期货").unwrap(), Market::Futures);
    assert_eq!(Market::from_str("默认").unwrap(), Market::Default);
}

#[test]
fn rejects_unknown_strings() {
    assert!(Market::from_str("invalid").is_err());
}

#[test]
fn display_round_trips() {
    assert_eq!(Market::AShare.to_string(), "A股");
    assert_eq!(Market::Futures.to_string(), "期货");
}

#[test]
fn copy_and_equality() {
    let a = Market::AShare;
    let b = a;
    assert_eq!(a, b);
}
