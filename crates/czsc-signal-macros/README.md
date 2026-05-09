# czsc-signal-macros

> ⚙️ **本 crate 是 czsc 框架的内部 proc-macro，普通用户不需要直接依赖。**
> 想用 czsc 量化分析框架请 `cargo add czsc`（facade crate）。
> 本 crate 之所以独立发布是因为 cargo 强制 proc-macro 必须为单独的 crate，
> 由 [`czsc-signals`](https://crates.io/crates/czsc-signals) 内部使用；
> 仅当你想为自己的 Rust 项目集成 czsc 风格的 inventory 信号注册系统时才
> 需要直接依赖。

[`czsc-signals`](https://crates.io/crates/czsc-signals) 配套的过程宏 crate，
为缠论信号函数提供编译期签名校验与自动注册。

## 提供的宏

- `#[signal(category = "kline", template = "{freq}_{name}_{ver}")]`
  —— 标记一个函数为信号入口，校验签名并把元数据写入 `inventory`
- `#[signal_module(category = "kline")]`
  —— 标记一个 `mod` 为信号模块，统一应用类别默认值

## 用法

```toml
[dependencies]
czsc-signal-macros = "1.0"
czsc-signals       = "1.0"
inventory          = "0.3"
```

```rust
use czsc_signal_macros::{signal, signal_module};

#[signal_module(category = "kline")]
pub mod my_signals {
    use super::*;

    #[signal(template = "{freq}_我的信号_V250101")]
    pub fn sig_v250101(/* ... */) -> /* ... */ { /* ... */ }
}
```

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
