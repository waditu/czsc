# czsc

[![crates.io](https://img.shields.io/crates/v/czsc.svg)](https://crates.io/crates/czsc)
[![docs.rs](https://docs.rs/czsc/badge.svg)](https://docs.rs/czsc)

CZSC（缠中说禅）量化分析框架的 Rust 入口。

本 crate 是一个 **facade**：本身不实现任何功能，只把 czsc Rust workspace 中
的 5 个业务 crate（[`czsc-core`] / [`czsc-utils`] / [`czsc-ta`] /
[`czsc-signals`] / [`czsc-trader`]）汇总到一个 crate 名下，让纯 Rust 用户
不用一行一行加 5 个依赖。

> 想用 Python 接口？请直接 `pip install czsc`，那是基于 `maturin` 编译的
> CPython 扩展，与本 facade 同源但接口面不同。

## 用法

```toml
[dependencies]
czsc = "1.0"
```

```rust
use czsc::{CZSC, RawBar, Freq, BarGenerator, is_trading_time};
use czsc::analyze::CZSC as Analyzer;

let bars: Vec<RawBar> = /* ... */;
let analyzer = Analyzer::new(bars, 50);
println!("最新一笔方向: {:?}", analyzer.bi_list.last().map(|b| b.direction));
```

也可以按子模块组织 import：

```rust
use czsc::objects::bi::BI;
use czsc::ta::ema;
use czsc::signals::registry::TRADER_SIGNAL_REGISTRY;
use czsc::trader::{CzscSignals, SignalConfig};
```

## 命名空间速查

| 路径 | 等价于 |
|---|---|
| `czsc::analyze` | `czsc_core::analyze` |
| `czsc::objects::*` | `czsc_core::objects::*` |
| `czsc::error_chain` | `czsc_core::error_chain` |
| `czsc::ta` | `czsc_ta::pure` |
| `czsc::bar_generator` | `czsc_utils::bar_generator` |
| `czsc::freq_data` | `czsc_utils::freq_data` |
| `czsc::trading_time` | `czsc_utils::trading_time` |
| `czsc::signals` | `czsc_signals` |
| `czsc::trader` | `czsc_trader` 的对外公共面 |

顶层 `czsc::*` 还直接挂了最常用的核心类型：`CZSC` / `RawBar` / `NewBar` /
`Freq` / `FX` / `BI` / `ZS` / `Mark` / `Direction` / `Operate` / `Event` /
`Position` / `Market` / `BarGenerator` / `CzscSignals` / `SignalConfig` /
`is_trading_time`。

## Features

- **(default)** —— 纯 Rust API
- `python` —— 透传给 `czsc-core` / `czsc-utils` / `czsc-ta`，给嵌入 PyO3
  的下游使用。一般用户不需要

## 工作区其它 crate

| crate | 说明 |
|---|---|
| [`czsc-core`](https://crates.io/crates/czsc-core) | 缠论核心数据结构与算法 |
| [`czsc-utils`](https://crates.io/crates/czsc-utils) | BarGenerator / freq_data / trading_time |
| [`czsc-ta`](https://crates.io/crates/czsc-ta) | 技术分析算子 |
| [`czsc-signals`](https://crates.io/crates/czsc-signals) | 30+ 量化信号函数 |
| [`czsc-trader`](https://crates.io/crates/czsc-trader) | 交易引擎与信号编译 |
| [`czsc-derive`](https://crates.io/crates/czsc-derive) | 错误派生宏（内部用） |
| [`czsc-signal-macros`](https://crates.io/crates/czsc-signal-macros) | 信号注册宏（内部用） |

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
- Python 包：<https://pypi.org/project/czsc/>

[`czsc-core`]: https://crates.io/crates/czsc-core
[`czsc-utils`]: https://crates.io/crates/czsc-utils
[`czsc-ta`]: https://crates.io/crates/czsc-ta
[`czsc-signals`]: https://crates.io/crates/czsc-signals
[`czsc-trader`]: https://crates.io/crates/czsc-trader
