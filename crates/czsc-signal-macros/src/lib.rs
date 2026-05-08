use proc_macro::TokenStream;
use quote::{ToTokens, format_ident, quote};
use syn::parse::Parser;
use syn::punctuated::Punctuated;
use syn::{Expr, ExprLit, FnArg, Item, ItemFn, ItemMod, Lit, Meta, Token, Type};

fn type_tokens(t: &Type) -> String {
    t.to_token_stream().to_string()
}

fn nth_arg_type(f: &ItemFn, idx: usize) -> Option<Type> {
    f.sig.inputs.iter().nth(idx).and_then(|a| match a {
        FnArg::Typed(t) => Some((*t.ty).clone()),
        _ => None,
    })
}

#[proc_macro_attribute]
pub fn signal(attr: TokenStream, item: TokenStream) -> TokenStream {
    let parser = Punctuated::<Meta, Token![,]>::parse_terminated;
    let metas = match parser.parse(attr) {
        Ok(m) => m,
        Err(e) => return e.to_compile_error().into(),
    };

    let mut category: Option<String> = None;
    let mut name: Option<String> = None;
    let mut template: Option<String> = None;
    let mut opcode: Option<String> = None;
    let mut param_kind: Option<String> = None;
    let mut fast_exec: Option<String> = None;
    let mut fast_decode: Option<String> = None;

    for m in metas {
        if let Meta::NameValue(nv) = m
            && let Some(ident) = nv.path.get_ident()
            && let Expr::Lit(ExprLit {
                lit: Lit::Str(v), ..
            }) = nv.value
        {
            match ident.to_string().as_str() {
                "category" => category = Some(v.value()),
                "name" => name = Some(v.value()),
                "template" => template = Some(v.value()),
                "opcode" => opcode = Some(v.value()),
                "param_kind" => param_kind = Some(v.value()),
                "fast_exec" => fast_exec = Some(v.value()),
                "fast_decode" => fast_decode = Some(v.value()),
                _ => {}
            }
        }
    }

    let f: ItemFn = match syn::parse(item) {
        Ok(v) => v,
        Err(e) => return e.to_compile_error().into(),
    };

    let mut errors = Vec::new();
    let category = category.unwrap_or_default();
    let name = name.unwrap_or_default();
    let template = template.unwrap_or_default();
    let opcode = opcode.unwrap_or_default();
    let param_kind = param_kind.unwrap_or_default();
    let fast_exec = fast_exec.unwrap_or_default();
    let fast_decode = fast_decode.unwrap_or_default();

    if category != "kline" && category != "trader" {
        errors.push(quote! { compile_error!("#[signal] category 必须是 kline 或 trader"); });
    }
    if name.is_empty() || template.is_empty() || opcode.is_empty() || param_kind.is_empty() {
        errors
            .push(quote! { compile_error!("#[signal] name/template/opcode/param_kind 不能为空"); });
    }

    let fn_ident = f.sig.ident.to_string();
    if !fn_ident.contains("_v") {
        errors.push(quote! { compile_error!("#[signal] 函数名必须包含 _v<版本号>"); });
    } else {
        let expected = if let Some((head, tail)) = fn_ident.rsplit_once("_v") {
            if !tail.is_empty() && tail.chars().all(|c| c.is_ascii_digit()) {
                format!("{head}_V{tail}")
            } else {
                String::new()
            }
        } else {
            String::new()
        };
        if expected.is_empty() || (!name.is_empty() && expected != name) {
            errors.push(quote! { compile_error!("#[signal] name 必须与函数名版本后缀一致，例如 foo_v230101 <-> foo_V230101"); });
        }
        if !template.is_empty() {
            let ver = expected
                .rsplit_once("_V")
                .map(|(_, v)| v.to_string())
                .unwrap_or_default();
            if !ver.is_empty() && !template.contains(ver.as_str()) {
                errors.push(
                    quote! { compile_error!("#[signal] template 必须包含版本数字（如 230101）"); },
                );
            }
        }
    }

    let argc = f.sig.inputs.len();
    match category.as_str() {
        "kline" if argc != 3 => {
            errors.push(quote! { compile_error!("kline signal 函数必须有 3 个参数"); })
        }
        "trader" if argc != 2 => {
            errors.push(quote! { compile_error!("trader signal 函数必须有 2 个参数"); })
        }
        _ => {}
    }
    if category == "kline" && argc == 3 {
        let t0 = nth_arg_type(&f, 0)
            .map(|t| type_tokens(&t))
            .unwrap_or_default();
        let t1 = nth_arg_type(&f, 1)
            .map(|t| type_tokens(&t))
            .unwrap_or_default();
        let t2 = nth_arg_type(&f, 2)
            .map(|t| type_tokens(&t))
            .unwrap_or_default();
        if !t0.contains("CZSC") {
            errors.push(quote! { compile_error!("kline signal 第1个参数必须是 &CZSC"); });
        }
        if !t1.contains('&') {
            errors.push(quote! { compile_error!("kline signal 第2个参数必须为引用类型（如 &ParamView / &HashMap / &TypedParams）"); });
        }
        if !(t2.contains("TaCache") && t2.contains("mut")) {
            errors.push(quote! { compile_error!("kline signal 第3个参数必须是 &mut TaCache"); });
        }
    }
    if category == "trader" && argc == 2 {
        let t0 = nth_arg_type(&f, 0)
            .map(|t| type_tokens(&t))
            .unwrap_or_default();
        let t1 = nth_arg_type(&f, 1)
            .map(|t| type_tokens(&t))
            .unwrap_or_default();
        if !t0.contains("TraderState") {
            errors
                .push(quote! { compile_error!("trader signal 第1个参数必须是 &dyn TraderState"); });
        }
        if !t1.contains('&') {
            errors.push(quote! { compile_error!("trader signal 第2个参数必须为引用类型（如 &ParamView / &HashMap / &TypedParams）"); });
        }
    }

    let vis = &f.vis;
    let sig = &f.sig;
    let block = &f.block;
    let meta_const_ident = syn::Ident::new(
        &format!("__RS_CZSC_SIGNAL_META_{}", f.sig.ident).to_uppercase(),
        f.sig.ident.span(),
    );

    let fn_name = &f.sig.ident;
    let mut generated_wrappers = quote! {};
    let (func_ref_expr, auto_fast_expr) = if category == "kline" {
        let raw_param_ty = f.sig.inputs.iter().nth(1).and_then(|a| match a {
            FnArg::Typed(t) => Some((*t.ty).clone()),
            _ => None,
        });
        let param_ty = raw_param_ty.as_ref().map(|t| match t {
            Type::Reference(r) => (*r.elem).clone(),
            _ => t.clone(),
        });
        let raw_param_ty_tokens = raw_param_ty
            .as_ref()
            .map(|t| t.to_token_stream().to_string())
            .unwrap_or_default();
        let is_hashmap_params = raw_param_ty_tokens.contains("HashMap");
        let is_param_view = raw_param_ty_tokens.contains("ParamView");
        if is_hashmap_params {
            (
                quote! { czsc_signals::types::SignalFnRef::Kline(#fn_name as czsc_signals::types::SignalFn) },
                quote! { None },
            )
        } else if is_param_view {
            let dyn_wrap_ident = format_ident!("__rs_dyn_wrap_{}", fn_name);
            generated_wrappers = quote! {
                #[doc(hidden)]
                fn #dyn_wrap_ident(
                    czsc: &czsc_core::analyze::CZSC,
                    params: &std::collections::HashMap<String, serde_json::Value>,
                    cache: &mut czsc_signals::types::TaCache,
                ) -> Vec<czsc_core::objects::signal::Signal> {
                    let p = czsc_signals::params::ParamView::new(params);
                    #fn_name(czsc, &p, cache)
                }
            };
            (
                quote! { czsc_signals::types::SignalFnRef::Kline(#dyn_wrap_ident as czsc_signals::types::SignalFn) },
                quote! { None },
            )
        } else {
            let pty = param_ty.expect("checked");
            let dyn_wrap_ident = format_ident!("__rs_dyn_wrap_{}", fn_name);
            let fast_decode_ident = format_ident!("__rs_fast_decode_{}", fn_name);
            let fast_exec_ident = format_ident!("__rs_fast_exec_{}", fn_name);
            generated_wrappers = quote! {
                #[doc(hidden)]
                fn #dyn_wrap_ident(
                    czsc: &czsc_core::analyze::CZSC,
                    params: &std::collections::HashMap<String, serde_json::Value>,
                    cache: &mut czsc_signals::types::TaCache,
                ) -> Vec<czsc_core::objects::signal::Signal> {
                    let val = match serde_json::to_value(params) {
                        Ok(v) => v,
                        Err(_) => return Vec::new(),
                    };
                    let p: #pty = match serde_json::from_value(val) {
                        Ok(v) => v,
                        Err(_) => return Vec::new(),
                    };
                    #fn_name(czsc, &p, cache)
                }

                #[doc(hidden)]
                fn #fast_decode_ident(
                    params: &std::collections::HashMap<String, serde_json::Value>,
                ) -> Option<serde_json::Value> {
                    let val = serde_json::to_value(params).ok()?;
                    let p: #pty = serde_json::from_value(val).ok()?;
                    serde_json::to_value(p).ok()
                }

                #[doc(hidden)]
                fn #fast_exec_ident(
                    czsc: &czsc_core::analyze::CZSC,
                    p: &serde_json::Value,
                    cache: &mut czsc_signals::types::TaCache,
                ) -> Vec<czsc_core::objects::signal::Signal> {
                    let pp: #pty = match serde_json::from_value(p.clone()) {
                        Ok(v) => v,
                        Err(_) => return Vec::new(),
                    };
                    #fn_name(czsc, &pp, cache)
                }
            };
            (
                quote! { czsc_signals::types::SignalFnRef::Kline(#dyn_wrap_ident as czsc_signals::types::SignalFn) },
                quote! {
                    Some(czsc_signals::types::FastKlineMeta {
                        decode: #fast_decode_ident as czsc_signals::types::FastKlineDecodeFn,
                        exec: #fast_exec_ident as czsc_signals::types::FastKlineExecFn,
                    })
                },
            )
        }
    } else {
        let raw_param_ty = f.sig.inputs.iter().nth(1).and_then(|a| match a {
            FnArg::Typed(t) => Some((*t.ty).clone()),
            _ => None,
        });
        let raw_param_ty_tokens = raw_param_ty
            .as_ref()
            .map(|t| t.to_token_stream().to_string())
            .unwrap_or_default();
        let is_hashmap_params = raw_param_ty_tokens.contains("HashMap");
        let is_param_view = raw_param_ty_tokens.contains("ParamView");
        if is_hashmap_params {
            (
                quote! { czsc_signals::types::SignalFnRef::Trader(#fn_name as czsc_signals::types::TraderSignalFn) },
                quote! { None },
            )
        } else if is_param_view {
            let dyn_wrap_ident = format_ident!("__rs_dyn_wrap_{}", fn_name);
            generated_wrappers = quote! {
                #[doc(hidden)]
                fn #dyn_wrap_ident(
                    cat: &dyn czsc_core::objects::state::TraderState,
                    params: &std::collections::HashMap<String, serde_json::Value>,
                ) -> Vec<czsc_core::objects::signal::Signal> {
                    let p = czsc_signals::params::ParamView::new(params);
                    #fn_name(cat, &p)
                }
            };
            (
                quote! { czsc_signals::types::SignalFnRef::Trader(#dyn_wrap_ident as czsc_signals::types::TraderSignalFn) },
                quote! { None },
            )
        } else {
            let pty = raw_param_ty.expect("checked");
            let pty = match pty {
                Type::Reference(r) => *r.elem,
                t => t,
            };
            let dyn_wrap_ident = format_ident!("__rs_dyn_wrap_{}", fn_name);
            generated_wrappers = quote! {
                #[doc(hidden)]
                fn #dyn_wrap_ident(
                    cat: &dyn czsc_core::objects::state::TraderState,
                    params: &std::collections::HashMap<String, serde_json::Value>,
                ) -> Vec<czsc_core::objects::signal::Signal> {
                    let val = match serde_json::to_value(params) {
                        Ok(v) => v,
                        Err(_) => return Vec::new(),
                    };
                    let p: #pty = match serde_json::from_value(val) {
                        Ok(v) => v,
                        Err(_) => return Vec::new(),
                    };
                    #fn_name(cat, &p)
                }
            };
            (
                quote! { czsc_signals::types::SignalFnRef::Trader(#dyn_wrap_ident as czsc_signals::types::TraderSignalFn) },
                quote! { None },
            )
        }
    };
    let fast_kline_expr = if category == "kline" && !fast_exec.is_empty() && !fast_decode.is_empty()
    {
        let fast_exec_path: syn::Path = match syn::parse_str(&fast_exec) {
            Ok(p) => p,
            Err(e) => return e.to_compile_error().into(),
        };
        let fast_decode_path: syn::Path = match syn::parse_str(&fast_decode) {
            Ok(p) => p,
            Err(e) => return e.to_compile_error().into(),
        };
        quote! {
            Some(czsc_signals::types::FastKlineMeta {
                decode: #fast_decode_path as czsc_signals::types::FastKlineDecodeFn,
                exec: #fast_exec_path as czsc_signals::types::FastKlineExecFn,
            })
        }
    } else {
        auto_fast_expr
    };

    let out = quote! {
        #(#errors)*
        #vis #sig #block
        #generated_wrappers

        #[doc(hidden)]
        #[allow(non_upper_case_globals, dead_code)]
        pub const #meta_const_ident: czsc_signals::types::SignalDescriptor = czsc_signals::types::SignalDescriptor {
            category: #category,
            name: #name,
            template: #template,
            opcode: #opcode,
            param_kind: #param_kind,
            func_ref: #func_ref_expr,
            fast_kline: #fast_kline_expr,
        };

        inventory::submit! {
            #meta_const_ident
        }
    };
    out.into()
}

#[proc_macro_attribute]
pub fn signal_module(_attr: TokenStream, item: TokenStream) -> TokenStream {
    let parser = Punctuated::<Meta, Token![,]>::parse_terminated;
    let metas = match parser.parse(_attr) {
        Ok(m) => m,
        Err(e) => return e.to_compile_error().into(),
    };
    let mut module_category = String::new();
    for m in metas {
        if let Meta::NameValue(nv) = m
            && let Some(ident) = nv.path.get_ident()
            && ident == "category"
            && let Expr::Lit(ExprLit {
                lit: Lit::Str(v), ..
            }) = nv.value
        {
            module_category = v.value();
        }
    }
    if module_category != "kline" && module_category != "trader" {
        return quote! { compile_error!("#[signal_module] category 必须是 kline 或 trader"); }
            .into();
    }

    let m: ItemMod = match syn::parse(item.clone()) {
        Ok(v) => v,
        Err(_) => return item,
    };

    if m.content.is_none() {
        return quote! {
            compile_error!("#[signal_module] 仅支持内联模块，用于编译期收集与校验");
            #m
        }
        .into();
    }

    let (_, items) = m.content.as_ref().expect("checked is_some");
    let mut seen_names = std::collections::HashSet::new();
    let mut seen_opcodes = std::collections::HashSet::new();
    for it in items {
        if let Item::Fn(f) = it {
            let name = f.sig.ident.to_string();
            if f.vis.to_token_stream().to_string() == "pub" && name.contains("_v") {
                let signal_attr = f.attrs.iter().find(|a| a.path().is_ident("signal"));
                if signal_attr.is_none() {
                    return quote! {
                        compile_error!("signal_module: pub fn *_v* 必须显式添加 #[signal(...)] 标注");
                        #m
                    }
                    .into();
                }
                let argc = f.sig.inputs.len();
                if module_category == "kline" {
                    if argc != 3 {
                        return quote! { compile_error!("signal_module: kline 模块中的 pub fn *_v* 必须是 3 参数签名"); #m }.into();
                    }
                    let t0 = nth_arg_type(f, 0)
                        .map(|t| type_tokens(&t))
                        .unwrap_or_default();
                    let t2 = nth_arg_type(f, 2)
                        .map(|t| type_tokens(&t))
                        .unwrap_or_default();
                    if !(t0.contains("CZSC") && t2.contains("TaCache") && t2.contains("mut")) {
                        return quote! { compile_error!("signal_module: kline 模块函数签名必须为 (&CZSC, &Params, &mut TaCache)"); #m }.into();
                    }
                } else if module_category == "trader" {
                    if argc != 2 {
                        return quote! { compile_error!("signal_module: trader 模块中的 pub fn *_v* 必须是 2 参数签名"); #m }.into();
                    }
                    let t0 = nth_arg_type(f, 0)
                        .map(|t| type_tokens(&t))
                        .unwrap_or_default();
                    if !t0.contains("TraderState") {
                        return quote! { compile_error!("signal_module: trader 模块函数签名必须为 (&dyn TraderState, &Params)"); #m }.into();
                    }
                }
                if let Some(attr) = signal_attr {
                    let parser = Punctuated::<Meta, Token![,]>::parse_terminated;
                    let mut attr_name = String::new();
                    let mut attr_opcode = String::new();
                    if let syn::Meta::List(list) = &attr.meta
                        && let Ok(ms) = parser.parse2(list.tokens.clone())
                    {
                        for m in ms {
                            if let Meta::NameValue(nv) = m
                                && let Some(ident) = nv.path.get_ident()
                                && let Expr::Lit(ExprLit {
                                    lit: Lit::Str(v), ..
                                }) = nv.value
                            {
                                if ident == "name" {
                                    attr_name = v.value();
                                } else if ident == "opcode" {
                                    attr_opcode = v.value();
                                }
                            }
                        }
                    }
                    if !attr_name.is_empty() && !seen_names.insert(attr_name.clone()) {
                        return quote! { compile_error!("signal_module: duplicate signal name in module"); #m }.into();
                    }
                    if !attr_opcode.is_empty() && !seen_opcodes.insert(attr_opcode.clone()) {
                        return quote! { compile_error!("signal_module: duplicate signal opcode in module"); #m }.into();
                    }
                }
            }
        }
    }

    quote! { #m }.into()
}
