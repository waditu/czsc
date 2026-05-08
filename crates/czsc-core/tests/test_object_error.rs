//! Phase D.1 — RED test: ObjectError variants must format with thiserror,
//! convert from anyhow::Error via the CZSCErrorDerive blanket, and serialize
//! to a string-shaped JSON.

use czsc_core::objects::errors::ObjectError;

#[test]
fn factor_signals_all_empty_message() {
    let err = ObjectError::FactorSignalsAllEmpty;
    assert_eq!(
        err.to_string(),
        "Factor.signals_all must contain at least one signal"
    );
}

#[test]
fn score_out_of_range_carries_value() {
    let err = ObjectError::ScoreOutOfRange(150);
    assert!(err.to_string().contains("150"));
}

#[test]
fn from_anyhow_blanket_routes_to_unexpected() {
    let any: anyhow::Error = anyhow::anyhow!("boom");
    let err: ObjectError = any.into();
    assert!(matches!(err, ObjectError::Unexpected(_)));
}

#[test]
fn serialize_emits_string_payload() {
    let err = ObjectError::SignalKeyNotFound("k1".into());
    let json = serde_json::to_string(&err).unwrap();
    assert!(json.contains("k1"), "expected key in payload, got {json}");
    assert!(json.starts_with("\""), "expected JSON string, got {json}");
}
