# czsc-core

> 💡 **大多数用户应优先使用 facade crate [`czsc`](https://crates.io/crates/czsc)**：
> `cargo add czsc` 一行拿到全部公共 API，本 crate 中的核心类型已在 facade
> 顶层 re-export。仅当你**只想要缠论核心算法**、不需要工具/信号/trader 时
> 才单独依赖本 crate。

缠论（CZSC，缠中说禅技术分析理论）核心数据结构与算法的 Rust 实现。

提供分型（`FX`）、笔（`BI`）、中枢（`ZS`）、`CZSC` 分析器等核心类型，以及 K 线
包含关系处理（`remove_include`）、笔识别（`check_bi`）等基础算法。

## 用法

```toml
[dependencies]
czsc-core = "1.0"
```

```rust
use czsc_core::objects::{RawBar, Freq};
use czsc_core::analyze::CZSC;

let bars: Vec<RawBar> = /* ... */;
let czsc = CZSC::new(bars, 50, 6);
println!("最新一笔方向: {:?}", czsc.bi_list.last().map(|b| b.direction));
```

`update_bar` 接收与末根 K 线相同的 `dt` 时，完整替换该根输入；包含关系、分型和笔
与该版本只输入一次的结果一致。分析器只保存最近一次输入前的未完成笔状态，以及该次
更新删除或裁剪的数据；下一根输入会替换这份状态，不积累历史快照。

`Clone`、Serde 和 Python pickle 均保留这份修订状态。Serde 快照必须包含
`tail_update` 字段；旧快照缺失该字段时会在反序列化时返回错误，不能从已裁剪的
`bars_raw` 恢复。旧 pickle 仅包含构造参数，仍按旧参数重建，无法补回此前丢失的状态。
`CZSCBuilder` 仅支持空分析状态；分析现有 K 线请调用 `CZSC::new`。

## 特性

- `python`：启用 PyO3 binding，供 `czsc-python` crate 聚合到 `czsc._native` 扩展。

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
- Python 包：[`czsc` on PyPI](https://pypi.org/project/czsc/)
