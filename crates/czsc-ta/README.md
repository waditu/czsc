# czsc-ta

> 💡 **如果你需要的是完整的缠论框架，请优先使用 facade crate
> [`czsc`](https://crates.io/crates/czsc)**：`cargo add czsc` 一行拿到
> 全部 API（含本 crate 的算子）。**本 crate 是少数适合单独依赖的场景**——
> 当你**只想要纯算子库**（EMA/SMA/rolling_rank/...）、不需要任何缠论
> 业务代码时，可以零额外依赖地 `cargo add czsc-ta`。

技术分析算子库 —— 缠论分析与量化策略常用的一组高性能数值算子。

包含 EMA、SMA、rolling_rank、ultimate_smoother 等纯 Rust 实现，附带可选的
numpy 互操作层（`rust-numpy` feature）以便供 PyO3 binding 直接零拷贝调用。

## 用法

```toml
[dependencies]
czsc-ta = "1.0"
```

```rust
use czsc_ta::pure::ema::ema;

let prices = vec![1.0, 2.0, 3.0, 4.0, 5.0];
let smoothed = ema(&prices, 3);
```

## 特性

- `python`：导出 PyO3 module。
- `rust-numpy`：在 `python` 之上加 numpy 数组互操作（零拷贝 in/out）。

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
