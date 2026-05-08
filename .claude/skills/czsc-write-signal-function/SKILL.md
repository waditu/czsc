---
name: czsc-write-signal-function
description: 为 rs_czsc 编写或重构 Rust 信号函数（bar/tas/cxt/pos）并接入事件驱动链路（`#[signal]` 自动注册、SignalConfig、Event/Position 匹配）的工作流。遇到“新增信号函数”“修改信号模板”“注册信号函数”“排查信号不触发”时使用。
---

# CZSC Signal Authoring

## Overview

用这个技能在 `rs_czsc` 中稳定完成信号函数开发：
1. 判断信号类型（K线级 / Trader级）
2. 编写函数并保持 `Signal` 7段格式
3. 注册到正确注册表
4. 用 `SignalConfig` 和测试验证是否能触发 `Event -> Position`

先读：
- `references/event-driven-signal-pipeline.md`
- `references/signal-function-patterns.md`

需要快速起草函数时，先运行：
- `scripts/new_signal_stub.py`

## Decision Tree

1. 需要访问仓位（`Position`）或策略状态吗？
- 是：写 Trader 级信号（`pos.rs` 风格），用 `#[signal(category = "trader", ...)]` 自动注册。
- 否：写 K线级信号（`bar/tas/cxt` 风格），用 `#[signal(category = "kline", ...)]` 自动注册。

2. 需要技术指标缓存吗？
- 是：使用 `TaCache`，优先走 `update_*_cache`。
- 否：保留 `_cache` 参数但不使用。

3. 需要多个输出信号吗？
- 是：返回 `Vec<Signal>`，每个信号都保持 7 段格式。
- 否：返回单元素 `Vec`。

## Workflow

1. 明确输入输出
- 明确函数输入参数（`params`）和默认值。
- 明确 `k1/k2/k3` 模板和 `v1/v2/v3` 语义。
- 明确“数据不足时”返回策略：通常返回 `vec![]` 或 `其他` 信号。

2. 实现函数
- K线级函数签名：`fn(&CZSC, &ParamView, &mut TaCache) -> Vec<Signal>`。
- Trader级函数签名：`fn(&dyn TraderState, &ParamView) -> Vec<Signal>`。
- 参数解析优先复用工具：`get_usize_param` / `get_str_param`。
- 必须写详细注释（硬性格式，不可省略小节）：
  - 标题行：`/// <func_name>：<一句话功能>`
  - `///`
  - `/// 参数模板：\`"..."\``
  - `///`
  - `/// 信号逻辑：`
  - `/// 1. ...`
  - `/// 2. ...`
  - `/// 3. ...`
  - `///`
  - `/// 信号列表示例：`
  - `/// - Signal('...')`
  - `/// - Signal('...')`
  - `///`
  - `/// 参数说明：`
  - `/// - <param>: <含义与默认值>`
  - `/// - <param>: <含义与默认值>`
  - 与 Python 或历史版本对齐时，必须补一行：`/// 对齐说明：...`
- 关键分支注释：说明为什么这么判定，而不是只写“做了什么”。
- 用 `format!` 拼出完整字符串：`k1_k2_k3_v1_v2_v3_score`。
- 用 `Signal::from_str(...)` 或 `parse::<Signal>()` 做最终构造。

3. 接入注册表
- 在函数上添加 `#[signal(...)]`，由 `inventory` 自动收集。
- 注册名与函数名保持一一对应（注意 `_V` 与 `_v` 大小写风格）。
- 在 `#[signal(...)]` 中给出 `template`，确保 `SignalConfig` 反解析和人类阅读一致。

4. 接入调用侧
- K线级：通过 `SignalConfig { name, freq: Some(...), params }` 在 `CzscSignals::update_signals` 中执行。
- Trader级：通过 `SignalConfig { name, freq: None, params }` 在 `CzscTrader::update` 的 Trader 信号分支执行。

5. 验证
- 至少验证：
  - 函数在样本上可运行，不 panic。
  - 输出信号可被 `Signal` 正常解析（7段、score 0~100）。
  - 注册后能被 `SignalConfig.name` 命中。
  - 若用于交易事件，`Event.matches_signals*` 能按预期触发。
  - 注释完整：他人仅看注释可理解参数、边界、输出语义和关键判定。
- 优先补充/运行相关测试：`signal_compare_tests`、`trader_tests` 或新增针对性测试。
- 注释格式校验（提交前必须人工检查）：
  - 每个新/改信号函数都包含 `参数模板/信号逻辑/信号列表示例/参数说明` 四段。
  - `信号列表示例` 至少 2 条，且与当前函数输出字段一致（`k1_k2_k3_v1_v2_v3_score`）。

## Guardrails

- 不要输出非 7 段信号；否则会在 `Signal::from_str` 失败。
- 不要忽略大小写差异；注册表键是精确匹配。
- 不要在数据长度不足时硬算；先做边界检查。
- 不要绕过 `TaCache` 重复全量计算重指标。
- 不要在函数里偷偷改全局状态；保持纯计算风格（Trader级仅读取状态）。
- 不要写空洞注释（如“计算信号”）；注释要解释判定依据和业务语义。

## Resources

- 架构与触发链路：`references/event-driven-signal-pipeline.md`
- 函数模板与常见坑：`references/signal-function-patterns.md`
- 骨架生成器：`scripts/new_signal_stub.py`
