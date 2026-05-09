# czsc-derive

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
