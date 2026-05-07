use error_macros::CZSCErrorDerive;
use error_support::expand_error_chain;
use polars::error::PolarsError;
use thiserror::Error;

#[derive(Debug, Error, CZSCErrorDerive)]
pub enum CoreUtilsErorr {
    #[error("Polars: {0}")]
    Polars(#[from] PolarsError),

    #[error("{}", expand_error_chain(.0))]
    Unexpected(anyhow::Error),
}
