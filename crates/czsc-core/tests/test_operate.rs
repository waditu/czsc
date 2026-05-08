//! Phase D.10a — RED test: Operate enum parses from English short codes
//! (HL/HS/HO/LO/LE/SO/SE), formats back via Display, and exposes
//! to_chinese() for the canonical labels.

use std::str::FromStr;

use czsc_core::objects::operate::Operate;

#[test]
fn parses_all_short_codes() {
    assert_eq!(Operate::from_str("HL").unwrap(), Operate::HL);
    assert_eq!(Operate::from_str("HS").unwrap(), Operate::HS);
    assert_eq!(Operate::from_str("HO").unwrap(), Operate::HO);
    assert_eq!(Operate::from_str("LO").unwrap(), Operate::LO);
    assert_eq!(Operate::from_str("LE").unwrap(), Operate::LE);
    assert_eq!(Operate::from_str("SO").unwrap(), Operate::SO);
    assert_eq!(Operate::from_str("SE").unwrap(), Operate::SE);
}

#[test]
fn rejects_unknown_string() {
    assert!(Operate::from_str("XYZ").is_err());
}

#[test]
fn display_round_trips_short_codes() {
    assert_eq!(Operate::HL.to_string(), "HL");
    assert_eq!(Operate::LO.to_string(), "LO");
}

#[test]
fn to_chinese_returns_canonical_labels() {
    assert_eq!(Operate::HL.to_chinese(), "持多");
    assert_eq!(Operate::HS.to_chinese(), "持空");
    assert_eq!(Operate::HO.to_chinese(), "持币");
    assert_eq!(Operate::LO.to_chinese(), "开多");
    assert_eq!(Operate::LE.to_chinese(), "平多");
    assert_eq!(Operate::SO.to_chinese(), "开空");
    assert_eq!(Operate::SE.to_chinese(), "平空");
}

#[test]
fn copy_and_equality() {
    let a = Operate::LO;
    let b = a;
    assert_eq!(a, b);
    assert_ne!(Operate::LO, Operate::SO);
}
