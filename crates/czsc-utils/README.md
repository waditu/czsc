# czsc-utils

缠论分析的 K 线合成与交易日历工具。

提供：

- `BarGenerator` —— 多周期 K 线合成器
- `freq_data` —— 频率周期与对齐时间计算
- `is_trading_time` —— 国内 A 股 / 期货市场交易时段判断

## 用法

```toml
[dependencies]
czsc-utils = "1.0"
```

```rust
use czsc_utils::is_trading_time;
use chrono::NaiveDateTime;

let dt: NaiveDateTime = "2024-01-02 10:30:00".parse().unwrap();
assert!(is_trading_time("000001.SZ", dt));
```

## 特性

- `python`：启用 PyO3 binding。

## 项目主页

- 仓库：<https://github.com/waditu/czsc>
