//! Phase D.0a — RED test: CZSCErrorDerive must produce From<anyhow::Error>
//! and serde::Serialize impls for an annotated enum.

use error_macros::CZSCErrorDerive;
use thiserror::Error;

#[derive(Debug, Error, CZSCErrorDerive)]
enum DummyError {
    #[error("unexpected: {0}")]
    Unexpected(anyhow::Error),
}

#[test]
fn from_anyhow_blanket_impl_exists() {
    let err: anyhow::Error = anyhow::anyhow!("boom");
    let dummy: DummyError = err.into();
    assert!(matches!(dummy, DummyError::Unexpected(_)));
}

#[test]
fn serialize_emits_string() {
    let dummy = DummyError::Unexpected(anyhow::anyhow!("boom"));
    let json = serde_json::to_string(&dummy).unwrap();
    assert!(
        json.contains("boom"),
        "expected serialized payload, got {json}"
    );
}
