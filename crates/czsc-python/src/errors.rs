//! czsc-python error type.
//!
//! Lifted from rs-czsc `python/src/errors.rs`, but the
//! `WeightBackTest` variant is dropped — czsc relies on the external
//! `wbt` crate for weight backtests, so its error chain doesn't
//! flow through this binding.

use czsc_core::error_chain::expand_error_chain;
use czsc_core::utils::errors::CoreUtilsErorr;
use czsc_derive::CZSCErrorDerive;
use czsc_utils::errors::UtilsError;
use numpy::AsSliceError;
use polars::error::PolarsError;
use pyo3::{PyErr, create_exception, exceptions::PyException};
use thiserror::Error;

create_exception!(_native, CZSCError, PyException);

#[derive(Debug, Error, CZSCErrorDerive)]
pub enum PythonError {
    #[error("Utils: {0}")]
    Utils(#[from] UtilsError),

    #[error("Polars: {0}")]
    Polars(#[from] PolarsError),

    #[error("{}", expand_error_chain(.0))]
    Unexpected(anyhow::Error),

    #[error("CoreUtils: {0}")]
    CoreUtils(#[from] CoreUtilsErorr),

    #[error("Numpy: {0}")]
    NotContiguous(#[from] AsSliceError),

    #[error("NotFound: {0}")]
    NotFound(String),
}

impl From<PythonError> for PyErr {
    fn from(e: PythonError) -> Self {
        PyException::new_err(e.to_string())
    }
}
