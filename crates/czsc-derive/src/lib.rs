//! czsc-derive — CZSC procedural derive macros.
//!
//! 由 rs-czsc commit `47ef6efa` 迁移、Phase J 由 `error-macros` 重命名而来
//! （参见 docs/MIGRATION_NOTES.md §1）。当前提供：
//!
//! - `#[derive(CZSCErrorDerive)]`：为枚举错误类型自动实现
//!   `From<anyhow::Error>` 与 `serde::Serialize`，把任意 anyhow 错误装进
//!   带 `#[from]` 的「未分类」变体并序列化为字符串。

use proc_macro::TokenStream;
use syn::{DeriveInput, parse_macro_input};

mod err;

#[proc_macro_derive(CZSCErrorDerive, attributes(error, from))]
pub fn derive_utils_error(input: TokenStream) -> TokenStream {
    let mut ast = parse_macro_input!(input as DeriveInput);
    err::err_gen_code(&mut ast)
}
