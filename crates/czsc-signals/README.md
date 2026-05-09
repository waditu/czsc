# czsc-signals

缠论信号函数库 —— 30+ 量化信号函数，按类别分组：

- `bar`：基础 K 线形态信号
- `cxt`：缠论上下文信号（笔、中枢相关）
- `tas`：技术分析叠加信号（MACD、RSI 等）
- `vol`：成交量信号
- `pressure` / `obv` / `cvolp`：资金、压力、量价信号

每个信号通过 [`#[signal(...)]`](https://crates.io/crates/czsc-signal-macros)
属性宏在编译期自动注册到 inventory，运行期可按字符串配置（如
`"日线_D1#10_看多V240520"`）解析、调用。

## 用法

```toml
[dependencies]
czsc-signals = "1.0"
```

```rust
// 通过 inventory 拿到注册的信号函数
let funcs = czsc_signals::all_signals();
println!("registered: {}", funcs.len());
```

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
- Python 入口：`czsc._native.signals`
