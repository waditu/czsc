use error_macros::CZSCErrorDerive;
use error_support::expand_error_chain;
use thiserror::Error;

#[cfg(feature = "python")]
use pyo3::{PyErr, exceptions::PyException};

#[derive(Debug, Error, CZSCErrorDerive)]
pub enum ObjectError {
    // Factor
    #[error("Factor.signals_all must contain at least one signal")]
    FactorSignalsAllEmpty,
    #[error("Invalid signals array format: {0:?}")]
    InvalidSignalsArrayFormat(Option<String>),

    // Signals
    #[error("Signal.score {0} must be between 0 and 100")]
    ScoreOutOfRange(i32),
    #[error("Invalid signal format: {0:?}")]
    InvalidSignalsFormat(Option<String>),
    #[error("Invalid score format: {0}")]
    InvalidScoreFormat(String),
    #[error("Signal key '{0}' does not exist in signals collection")]
    SignalKeyNotFound(String),
    #[error("Invalid signal format: missing underscore separator in '{0}'")]
    MalformedSignalValue(String),

    #[error("{}", expand_error_chain(.0))]
    Unexpected(anyhow::Error),
}

#[cfg(feature = "python")]
impl From<ObjectError> for PyErr {
    fn from(e: ObjectError) -> Self {
        PyException::new_err(e.to_string())
    }
}
