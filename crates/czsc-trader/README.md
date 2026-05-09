# czsc-trader

> 💡 **大多数用户应优先使用 facade crate [`czsc`](https://crates.io/crates/czsc)**：
> `cargo add czsc` 一行拿到全部公共 API，`CzscTrader` / `CzscSignals` /
> `SignalConfig` 等核心类型已在 facade 顶层 re-export。仅当你**已经
> 单独依赖 czsc-core/signals 并自己组装 trader 状态机**时才直接依赖本
> crate。

缠论多策略交易引擎、信号编译与参数优化。

核心组件：

- `engine_v2` —— 事件驱动式 v2 执行引擎
- `signals` —— 信号字符串 → SignalConfig 编译，与 `czsc-signals` 配合
- `trader` —— `CzscTrader` / `CzscSignals` 状态机
- `optimize` —— 持仓策略参数网格搜索

权重回测（`WeightBacktest`）按 czsc 设计文档由外部 [`wbt`](https://pypi.org/project/wbt/)
crate 提供，`czsc-trader` 只负责生成信号与持仓权重序列。

## 用法

```toml
[dependencies]
czsc-trader = "1.0"
```

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
- Python 入口：`czsc.CzscTrader` / `czsc.CzscSignals`
