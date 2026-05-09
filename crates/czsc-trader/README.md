# czsc-trader

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
