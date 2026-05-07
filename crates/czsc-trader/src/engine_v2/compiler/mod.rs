pub(crate) mod event;
pub(crate) mod optimize;
pub(crate) mod position;
mod signal;

use crate::engine_v2::catalog::{CatalogSignal, resolve_signal_category};
use crate::engine_v2::compiler::event::compile_events;
use crate::engine_v2::compiler::position::compile_positions;
use crate::engine_v2::compiler::signal::{CompiledSignalPlan, compile_signals};
use crate::signals::sig_parse::SignalConfig;
use czsc_core::objects::position::Position;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct ExecutionPlanInput {
    pub symbol: String,
    pub base_freq: String,
    #[serde(default)]
    pub signals_config: Vec<SignalConfig>,
    #[serde(default)]
    pub positions: Vec<Position>,
    pub market: Option<String>,
    pub bg_max_count: Option<usize>,
    /// 信号/策略正式起跑的时间分界点。
    ///
    /// 是否将 `sdt` 当根 K 线计入右侧正式运行，由 `include_sdt_bar` 决定。
    pub sdt: Option<String>,
    #[serde(default)]
    /// 控制 `sdt` 当根 K 线归属到左侧预热还是右侧正式运行。
    ///
    /// - `false`：左侧 `dt <= sdt`，右侧 `dt > sdt`
    /// - `true`：左侧 `dt < sdt`，右侧 `dt >= sdt`
    ///
    /// 默认值为 `false`，对齐 Python `CzscStrategyBase` 的回测 / replay 语义。
    /// 信号导出场景（例如 `generate_czsc_signals` / `signal_matrix`）如果要对齐
    /// Python 基线，需要显式传入 `true`。
    pub include_sdt_bar: Option<bool>,
}

#[derive(Debug, Clone)]
pub struct ExecutionPlan {
    pub symbol: String,
    pub base_freq: String,
    pub signals_config: Vec<SignalConfig>,
    pub positions: Vec<Position>,
    pub market: Option<String>,
    pub bg_max_count: usize,
    /// 编译后的 `sdt` 时间分界点，供执行器拆分预热区和正式运行区。
    pub sdt: Option<String>,
    /// 编译后的 `sdt` 边界模式。
    ///
    /// - `false`：`sdt` 当根 bar 只参与预热，不进入右侧正式输出
    /// - `true`：`sdt` 当根 bar 直接作为右侧第一根有效 bar
    pub include_sdt_bar: bool,
    pub catalog_signals: Vec<CatalogSignal>,
    pub signal_plan: CompiledSignalPlan,
    pub event_plan: event::CompiledEventPlan,
    pub position_plan: position::CompiledPositionPlan,
}

pub(crate) use signal::CompiledSignalPlan as CompiledSignalPlanV2;

impl ExecutionPlan {
    pub fn compile(input: ExecutionPlanInput) -> Result<Self, String> {
        if input.symbol.trim().is_empty() {
            return Err("strategy.symbol 不能为空".to_string());
        }
        if input.positions.is_empty() {
            return Err("strategy.positions 不能为空".to_string());
        }

        let ExecutionPlanInput {
            symbol,
            base_freq,
            signals_config,
            mut positions,
            market,
            bg_max_count,
            sdt,
            include_sdt_bar,
        } = input;

        for pos in &mut positions {
            pos.normalize_runtime_fields();
        }

        let mut catalog_signals = Vec::with_capacity(signals_config.len());
        for sc in &signals_config {
            catalog_signals.push(resolve_signal_category(sc)?);
        }
        let signal_plan = compile_signals(&signals_config, &catalog_signals)?;
        let event_plan = compile_events(&positions);
        let position_plan = compile_positions(&positions);

        Ok(Self {
            symbol,
            base_freq,
            signals_config,
            positions,
            market,
            bg_max_count: bg_max_count.unwrap_or(5000),
            sdt,
            include_sdt_bar: include_sdt_bar.unwrap_or(false),
            catalog_signals,
            signal_plan,
            event_plan,
            position_plan,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::{ExecutionPlan, ExecutionPlanInput};

    #[test]
    fn compile_rejects_empty_symbol() {
        let input = ExecutionPlanInput {
            symbol: String::new(),
            base_freq: "30分钟".to_string(),
            signals_config: vec![],
            positions: vec![],
            market: None,
            bg_max_count: None,
            sdt: None,
            include_sdt_bar: None,
        };
        assert!(ExecutionPlan::compile(input).is_err());
    }
}
