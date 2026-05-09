# czsc-signal-macros

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
