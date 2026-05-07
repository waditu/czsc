# Signal Function Patterns

## 0. 注释规范（必须）

每个新信号函数都必须包含以下注释层级：

- 函数文档注释（`///`）至少写清 4 件事：
  - 信号在策略中的业务含义
  - 参数模板字符串（`param_template`）
  - 核心判定逻辑（触发条件）
  - 边界行为（数据不足返回什么）
- 关键分支前写“原因注释”，解释判定依据和设计意图。
- 与 Python/旧版行为对齐时，标注“对齐对象”和“为何这样对齐”。

## 1. K线级函数模板（bar/tas/cxt）

```rust
use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_str_param, get_usize_param};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

/// xxx_v240101: 示例信号
///
/// 参数模板："{freq}_D{di}{key}_示例V240101"
/// 信号语义：当满足示例条件时输出目标状态，否则输出“其他”。
/// 边界行为：当 bars 不足以支持 di 回看时，返回空信号。
#[signal(
    category = "kline",
    name = "xxx_V240101",
    template = "{freq}_D{di}{key}_示例V240101",
    opcode = "XxxV240101",
    param_kind = "XxxV240101"
)]
pub fn xxx_v240101(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let key = get_str_param(params, "key", "DEFAULT");

    // 1) 边界检查：数据不足时不输出错误信号，直接返回空结果。
    if czsc.bars_raw.len() < di + 2 {
        return vec![];
    }

    // 2) 计算 k1/k2/k3 与 v1/v2/v3：
    // k1/k2/k3 用于事件匹配 key，v1/v2/v3 承载状态值语义。
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}{}", di, key);
    let k3 = "示例V240101";
    let v1 = "其他";
    let v2 = "任意";
    let v3 = "任意";

    // 3) 严格 7 段
    let sig_str = format!("{}_{}_{}_{}_{}_{}_0", k1, k2, k3, v1, v2, v3);
    Signal::from_str(&sig_str).map_or_else(|_| vec![], |s| vec![s])
}
```

## 2. Trader级函数模板（pos）

```rust
use crate::params::ParamView;
use crate::utils::sig::get_str_param;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::state::TraderState;
use czsc_signal_macros::signal;
use std::str::FromStr;

/// pos_xxx_v240101: 示例 Trader 级信号
///
/// 参数模板："{pos_name}_示例V240101"
/// 信号语义：根据仓位是否存在输出“有效/其他”。
/// 边界行为：缺少 pos_name 或查询不到仓位时输出“其他”。
#[signal(
    category = "trader",
    name = "pos_xxx_V240101",
    template = "{pos_name}_示例V240101",
    opcode = "PosXxxV240101",
    param_kind = "PosXxxV240101"
)]
pub fn pos_xxx_v240101(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "").to_string();

    let k1 = format!("{}_状态", pos_name);
    let k2 = "其他";
    let k3 = "示例V240101";

    // Trader 级信号必须解释“为何读取 trader 状态”，避免后续误改为纯 K线逻辑。
    let v1 = if cat.get_position(&pos_name).is_some() {
        "有效"
    } else {
        "其他"
    };

    let sig_str = format!("{}_{}_{}_{}_任意_任意_0", k1, k2, k3, v1);
    Signal::from_str(&sig_str).map_or_else(|_| vec![], |s| vec![s])
}
```

## 3. 注册模板

通过 `#[signal(...)]` 自动注册，无需手写 `registry.rs` 列表。
关键字段：

```rust
#[signal(
    category = "kline|trader",
    name = "..._Vxxxxxx",
    template = "...",
    opcode = "...",
    param_kind = "..."
)]
```

## 4. 参数与模板约束

- `params` key 名与模板占位符保持一致。
- 模板中 `freq` 表示周期；Trader 级常常不用 `freq` 字段做路由，依赖 `freq1` 之类业务参数。
- 维护 `k2/k3` 语义稳定，避免同名逻辑漂移。

## 5. 事件触发兼容性检查

新增信号用于事件时，先写出事件侧信号字符串，再倒推函数输出：

1. 事件侧 `Signal` 是否 7 段且 score 合法
2. 事件侧 `k1_k2_k3` 是否与函数输出完全一致
3. 事件侧 `v1/v2/v3` 是否允许 `任意`
4. 事件侧 score 是否不高于函数输出 score

## 6. 常见坑

- 在 `SignalConfig` 里用错注册名（尤其 `_V` 大写）
- `freq: None` / `Some` 配置反了，导致函数完全不被调度
- 直接 `unwrap` 导致边界数据 panic；优先 `map_or_else` 或早返回
- 函数输出多信号时 key 冲突未预期，后写会覆盖 `s` 字典同 key 值
