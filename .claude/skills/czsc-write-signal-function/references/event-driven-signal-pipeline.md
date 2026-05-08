# Event-Driven Signal Pipeline (rs_czsc)

## 1. 总体调用链

1. `CzscTrader::update` 接收一根 `RawBar`
2. `CzscSignals::update_signals` 计算本根所有 K线级信号
3. `CzscTrader::update` 额外执行 Trader 级信号（pos 系列）
4. 合并信号后调用每个 `Position::update`
5. `Position` 按 `opens + exits` 顺序匹配 `Event`
6. `Event` 内部通过 `signals_not -> signals_all -> signals_any` 判定
7. 匹配后产生命令（`LO/LE/SO/SE/...`）并更新持仓记录

## 2. 关键文件

- `crates/czsc-trader/src/trader.rs`
  - 交易主入口；组织信号计算与仓位更新
- `crates/czsc-trader/src/signals/czsc_signals.rs`
  - K线级信号执行器；维护 `s` 与 `sigs`
- `crates/czsc-signals/src/registry.rs`
  - 汇总 `inventory` 自动收集的 `SignalDescriptor` 到运行时注册表
- `crates/czsc-signals/src/types.rs`
  - 信号函数签名类型定义
- `crates/czsc-core/src/objects/signal.rs`
  - `Signal` 7段格式、`is_match`
- `crates/czsc-core/src/objects/event.rs`
  - `Event` 匹配逻辑
- `crates/czsc-core/src/objects/position.rs`
  - `Position::update` 执行开平仓规则
- `crates/czsc-core/src/objects/state.rs`
  - `TraderState` trait（给 Trader 级信号读状态）

## 3. 两类信号函数

### K线级信号（bar / tas / cxt）

- 签名：
`fn(&CZSC, &ParamView, &mut TaCache) -> Vec<Signal>`
- 注册方式：函数上 `#[signal(category = "kline", ...)]` 自动收集
- 调用路径：`CzscSignals::update_signals`
- 适用场景：仅依赖某个周期的 K 线结构和指标

### Trader级信号（pos）

- 签名：
`fn(&dyn TraderState, &ParamView) -> Vec<Signal>`
- 注册方式：函数上 `#[signal(category = "trader", ...)]` 自动收集
- 调用路径：`CzscTrader::update` 中 `freq.is_none()` 分支
- 适用场景：需要 `Position` + `CZSC` 联合状态

## 4. 信号字符串规则

`Signal` 必须满足：
- 格式：`k1_k2_k3_v1_v2_v3_score`
- 总段数：7 段
- `score`：0~100

`CzscSignals` 会把它拆成：
- key：`k1_k2_k3`
- value：`v1_v2_v3_score`

`Event` 匹配时用 `Signal::is_match`：
- `score >= 事件要求score`
- `v1/v2/v3` 精确匹配或事件侧为 `任意`

## 5. 开发时最常见断点

- 注册表 name 与 `SignalConfig.name` 不一致（大小写、`_V`/`_v`）
- 输出不是 7 段，导致 `Signal::from_str` 失败
- `freq` 设置错误：
  - K线级应为 `Some(freq)`
  - Trader级应为 `None`
- 数据不足未做边界检查，触发索引错误或无意义信号

## 6. 最小联调路径

1. 在 `czsc-signals` 实现函数并添加 `#[signal(...)]` 标注
2. 构造 `SignalConfig`
3. 用 `CzscTrader::update` 喂历史 bars
4. 检查：
   - `trader.signals.s` 中是否有目标 key
   - `trader.signals.sigs` 中是否出现目标 `Signal`
   - `position.operates` 是否按预期变化
