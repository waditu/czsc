use proc_macro::TokenStream;
use quote::quote;

pub fn err_gen_code(ast: &mut syn::DeriveInput) -> TokenStream {
    let name = &ast.ident;

    // 生成 `From<anyhow::Error>` 实现
    let from_impl = quote! {
        impl std::convert::From<anyhow::Error> for #name {
            fn from(error: anyhow::Error) -> Self {
                Self::Unexpected(error)
            }
        }
    };

    // 生成 `serde::Serialize` 实现
    let serialize_impl = quote! {
        impl serde::Serialize for #name {
            fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
            where
                S: serde::ser::Serializer,
            {
                serializer.serialize_str(&self.to_string())
            }
        }
    };

    // 汇总并返回生成的代码
    let expanded = quote! {
        #from_impl
        #serialize_impl
    };

    TokenStream::from(expanded)
}
