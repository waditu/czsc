//! error-macros — proc-macro for CZSC error type generation.
//!
//! Migrated from rs-czsc commit `47ef6efa` (see docs/MIGRATION_NOTES.md §1).
//! Provides `CZSCErrorDerive` which auto-implements `From<anyhow::Error>` and
//! `serde::Serialize` for enum error types.

use proc_macro::TokenStream;
use syn::{DeriveInput, parse_macro_input};

mod err;

#[proc_macro_derive(CZSCErrorDerive, attributes(error, from))]
pub fn derive_utils_error(input: TokenStream) -> TokenStream {
    let mut ast = parse_macro_input!(input as DeriveInput);
    err::err_gen_code(&mut ast)
}
