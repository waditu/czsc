# czsc-derive

> ⚙️ **本 crate 是 czsc 框架的内部 proc-macro，普通用户不需要直接依赖。**
> 想用 czsc 量化分析框架请 `cargo add czsc`（facade crate）。
> 本 crate 之所以独立发布是因为 cargo 强制 proc-macro 必须为单独的 crate，
> 仅供 [`czsc-core`](https://crates.io/crates/czsc-core) /
> [`czsc-utils`](https://crates.io/crates/czsc-utils) /
> [`czsc-trader`](https://crates.io/crates/czsc-trader) 等内部使用，也可被
> 其它需要 anyhow ↔ enum 自动桥接的 Rust 项目复用。

CZSC 工作区的过程式派生宏（procedural derive macros）。

当前提供 `#[derive(CZSCErrorDerive)]`：为枚举错误类型自动实现

- `From<anyhow::Error>` —— 把任意 `anyhow::Error` 装进枚举的 `#[from]` 变体
- `serde::Serialize` —— 让错误结构跨 FFI / API 边界可序列化为字符串

## 用法

```toml
[dependencies]
czsc-derive = "1.0"
anyhow      = "1"
thiserror   = "2"
serde       = { version = "1", features = ["derive"] }
```

```rust
use czsc_derive::CZSCErrorDerive;

#[derive(CZSCErrorDerive, thiserror::Error, Debug)]
pub enum MyError {
    #[error("invalid bar: {0}")]
    InvalidBar(String),
    #[from]
    #[error("other: {0}")]
    Other(anyhow::Error),
}
```

## 历史

本 crate 在 1.0.0 之前曾名为 `error-macros`。重命名为 `czsc-derive` 是为了
避免占用 crates.io 上「error-macros」这一过于通用的命名空间。API 完全保持
兼容，仅 `use` 路径与 Cargo.toml 依赖名变化。

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
