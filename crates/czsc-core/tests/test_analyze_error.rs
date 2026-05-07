//! Phase D.E — RED test: AnalyzeErorr formats with thiserror, accepts
//! a PolarsError via the From blanket, and round-trips through serde
//! via CZSCErrorDerive.

use czsc_core::analyze::errors::AnalyzeErorr;

#[test]
fn from_polars_routes_to_polars_variant() {
    use polars::error::PolarsError;
    let pe = PolarsError::ComputeError("compute boom".into());
    let err: AnalyzeErorr = pe.into();
    assert!(matches!(err, AnalyzeErorr::Polars(_)));
    assert!(err.to_string().contains("compute boom"));
}

#[test]
fn from_anyhow_routes_to_unexpected() {
    let any: anyhow::Error = anyhow::anyhow!("ka-boom");
    let err: AnalyzeErorr = any.into();
    assert!(matches!(err, AnalyzeErorr::Unexpected(_)));
}

#[test]
fn serialize_emits_string_payload() {
    let pe = polars::error::PolarsError::ComputeError("x".into());
    let err: AnalyzeErorr = pe.into();
    let json = serde_json::to_string(&err).unwrap();
    assert!(json.starts_with('"'), "expected JSON string, got {json}");
}
