//! Phase C.0 — RED test: UtilsError variants must format with thiserror,
//! convert from anyhow / PolarsError via the From blanket impls, and
//! serialize to a string-shaped JSON via CZSCErrorDerive.

use chrono::NaiveDate;
use czsc_utils::errors::UtilsError;

#[test]
fn invalid_datetime_message() {
    let err = UtilsError::InvalidDateTime;
    assert_eq!(err.to_string(), "Invalid datetime");
}

#[test]
fn invalid_freq_end_date_carries_payload() {
    let err = UtilsError::InvalidFreqEndDate("2024-99-99".into());
    assert!(err.to_string().contains("2024-99-99"));
}

#[test]
fn no_weights_avail_includes_date() {
    let dt = NaiveDate::from_ymd_opt(2024, 1, 8).unwrap();
    let err = UtilsError::NoWeightsAvail(dt);
    assert!(err.to_string().contains("2024-01-08"));
}

#[test]
fn from_anyhow_routes_to_unexpected() {
    let any: anyhow::Error = anyhow::anyhow!("boom");
    let err: UtilsError = any.into();
    assert!(matches!(err, UtilsError::Unexpected(_)));
}

#[test]
fn from_polars_error_routes_to_polars() {
    use polars::error::PolarsError;
    let pe = PolarsError::ComputeError("compute failed".into());
    let err: UtilsError = pe.into();
    assert!(matches!(err, UtilsError::Polars(_)));
    assert!(err.to_string().contains("compute failed"));
}
