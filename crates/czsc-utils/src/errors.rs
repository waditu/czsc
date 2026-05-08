use chrono::NaiveDate;
use error_macros::CZSCErrorDerive;
use error_support::expand_error_chain;
use polars::error::PolarsError;
use thiserror::Error;

#[cfg(feature = "python")]
use pyo3::{PyErr, exceptions::PyException};

#[derive(Debug, Error, CZSCErrorDerive)]
pub enum UtilsError {
    // #[error("Object: {0}")]
    // Object(#[from] ObjectError),

    // #[error("Expected a value, but got None")]
    // NoneValue,
    #[error("Polars: {0}")]
    Polars(#[from] PolarsError),

    #[error("Invalid datetime")]
    InvalidDateTime,

    #[error("Invalid datetime in freq_end_date: {0}")]
    InvalidFreqEndDate(String),

    #[error("Return should not be empty!")]
    ReturnsEmpty,

    #[error("No weights available before: {0}!")]
    NoWeightsAvail(NaiveDate),

    #[error("{}", expand_error_chain(.0))]
    Unexpected(anyhow::Error),
}

#[cfg(feature = "python")]
impl From<UtilsError> for PyErr {
    fn from(e: UtilsError) -> Self {
        PyException::new_err(e.to_string())
    }
}
