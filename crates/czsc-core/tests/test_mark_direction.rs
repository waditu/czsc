//! Phase D.6 — RED test: Mark + Direction enums parse from Chinese
//! serialised forms, format back via Display, and have stable equality.

use std::str::FromStr;

use czsc_core::objects::direction::Direction;
use czsc_core::objects::mark::Mark;

#[test]
fn mark_parses_chinese_names() {
    assert_eq!(Mark::from_str("底分型").unwrap(), Mark::D);
    assert_eq!(Mark::from_str("顶分型").unwrap(), Mark::G);
}

#[test]
fn mark_display_round_trips() {
    assert_eq!(Mark::D.to_string(), "底分型");
    assert_eq!(Mark::G.to_string(), "顶分型");
}

#[test]
fn mark_rejects_unknown_string() {
    assert!(Mark::from_str("分型X").is_err());
}

#[test]
fn direction_parses_chinese_names() {
    assert_eq!(Direction::from_str("向上").unwrap(), Direction::Up);
    assert_eq!(Direction::from_str("向下").unwrap(), Direction::Down);
}

#[test]
fn direction_display_round_trips() {
    assert_eq!(Direction::Up.to_string(), "向上");
    assert_eq!(Direction::Down.to_string(), "向下");
}

#[test]
fn direction_equality_and_clone() {
    let a = Direction::Up;
    let b = a.clone();
    assert_eq!(a, b);
    assert_ne!(Direction::Up, Direction::Down);
}
