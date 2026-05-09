use crate::error_chain::expand_error_chain;
use czsc_derive::CZSCErrorDerive;
use polars::error::PolarsError;
use thiserror::Error;

#[derive(Debug, Error, CZSCErrorDerive)]
pub enum AnalyzeErorr {
    #[error("Polars: {0}")]
    Polars(#[from] PolarsError),

    #[error("{}", expand_error_chain(.0))]
    Unexpected(anyhow::Error),
}
