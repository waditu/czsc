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

## 联合信号的指标状态

`cat_macd_V230518` / `cat_macd_V230520` 读取 `CzscSignals.ta_cache` 中各周期的
`MACD12#26#9`，与单周期信号共用预热和增量状态。只配置联合信号时也由该 owner
准备缓存；同一 owner 计算轮内，同 key 的多个单周期/联合信号只刷新一次，避免长预热
首轮先全量初始化、后重复增量更新造成同公式数值分叉。轮结束即清除标记，独立调用
`update_macd_cache` 仍逐次处理输入。`CzscTrader` 和 compiled runtime
采用同一规则。联合信号的周期发现复用 `get_signals_freqs`，包含两个 MACD 联合信号
及 `cxt_zhong_shu_gong_zhen_V221221` 自身声明的缺省周期。

Rust 自定义 `TraderState` 实现必须通过 `get_macd` 提供频率 owner 的缓存引用。
`MacdSeries` 的唯一类型定义为 `czsc_core::objects::state::MacdSeries`；旧的
`czsc_signals::types::MacdSeries` 路径已删除。Python 公共 API 不暴露该内部缓存类型。
`dump_state` / `restore_state` 保留增量缓存；Python `pickle` 仍按已有合同重建 fresh trader。

## 用法

```toml
[dependencies]
czsc-trader = "1.0"
```

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
- Python 入口：`czsc.CzscTrader` / `czsc.CzscSignals`
