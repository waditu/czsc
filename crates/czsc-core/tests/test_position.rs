//! Phase D.10d — RED test: Position deserialises from JSON, computes
//! get_pos / get_pos_changed defaults, normalises event hashes via
//! normalize_runtime_fields, and Pos enum's f64 round-trip works.

use czsc_core::objects::position::{Pos, Position};

#[test]
fn pos_default_is_flat() {
    assert_eq!(Pos::default(), Pos::Flat);
}

#[test]
fn pos_to_f64_canonical() {
    assert!((Pos::Long.to_f64() - 1.0).abs() < f64::EPSILON);
    assert!((Pos::Flat.to_f64() - 0.0).abs() < f64::EPSILON);
    assert!((Pos::Short.to_f64() + 1.0).abs() < f64::EPSILON);
}

#[test]
fn pos_from_f64_threshold_at_half() {
    assert_eq!(Pos::from_f64(0.6), Pos::Long);
    assert_eq!(Pos::from_f64(-0.6), Pos::Short);
    assert_eq!(Pos::from_f64(0.0), Pos::Flat);
    assert_eq!(Pos::from_f64(0.4), Pos::Flat);
    assert_eq!(Pos::from_f64(-0.4), Pos::Flat);
}

#[test]
fn pos_display() {
    assert_eq!(Pos::Long.to_string(), "多");
    assert_eq!(Pos::Short.to_string(), "空");
    assert_eq!(Pos::Flat.to_string(), "空仓");
}

const POSITION_JSON: &str = r#"{
  "opens": [],
  "exits": [],
  "interval": 0,
  "timeout": 0,
  "stop_loss": 0.0,
  "T0": false,
  "name": "test_position",
  "symbol": "000001"
}"#;

#[test]
fn position_deserialises_minimal_json() {
    let mut p: Position = serde_json::from_str(POSITION_JSON).unwrap();
    p.normalize_runtime_fields();
    assert_eq!(p.symbol, "000001");
    assert_eq!(p.name, "test_position");
    assert_eq!(p.interval, 0);
    assert!(!p.t0);
}

#[test]
fn position_get_pos_starts_flat() {
    let mut p: Position = serde_json::from_str(POSITION_JSON).unwrap();
    p.normalize_runtime_fields();
    assert_eq!(p.get_pos(), Pos::Flat);
    assert!(!p.get_pos_changed());
}
