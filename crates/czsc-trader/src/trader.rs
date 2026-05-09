use crate::czsc_signals::CzscSignals;
use crate::sig_parse::SignalConfig;
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::position::{LiteBar, Position};
use czsc_core::objects::state::TraderState;
use czsc_signals::types::TraderSignalFn;
use czsc_utils::bar_generator::BarGenerator;
use polars::prelude::*;
use serde_json::Value;
use std::collections::HashMap;
use std::fs::File;
use std::path::Path;
use std::time::Instant;

#[derive(Debug, Clone, Copy, Default)]
pub struct UpdateProfile {
    pub signals_update_ns: u128,
    pub trader_signals_ns: u128,
    pub position_update_ns: u128,
    pub pos_event_match_ns: u128,
    pub pos_fsm_ns: u128,
    pub pos_risk_ns: u128,
    pub pos_holds_ns: u128,
}

#[derive(Clone)]
struct CompiledTraderSignalOp {
    func: TraderSignalFn,
    params: HashMap<String, Value>,
}

/// 多策略联合交易引擎
pub struct CzscTrader {
    /// 交易引擎名称
    pub name: String,
    /// 内部驱动所有K线和信号的引擎
    pub signals: CzscSignals,
    /// 仓位策略实例
    pub positions: Vec<Position>,
    compiled_trader_ops: Vec<CompiledTraderSignalOp>,
    compiled_cfg_ptr: usize,
    compiled_cfg_len: usize,
}

impl CzscTrader {
    /// 构造一个新的 Trader
    pub fn new(symbol: String, bg: BarGenerator, positions: Vec<Position>) -> Self {
        Self {
            name: "CzscTrader".to_string(),
            signals: CzscSignals::new(symbol, bg),
            positions,
            compiled_trader_ops: Vec::new(),
            compiled_cfg_ptr: 0,
            compiled_cfg_len: 0,
        }
    }

    fn ensure_compiled_trader_ops(&mut self, signals_config: &[SignalConfig]) {
        let ptr = signals_config.as_ptr() as usize;
        let len = signals_config.len();
        if self.compiled_cfg_ptr == ptr && self.compiled_cfg_len == len {
            return;
        }

        self.compiled_trader_ops.clear();
        self.compiled_trader_ops.reserve(signals_config.len());
        for config in signals_config {
            if config.freq.is_none()
                && let Some(meta) =
                    czsc_signals::registry::TRADER_SIGNAL_REGISTRY.get(config.name.as_str())
            {
                self.compiled_trader_ops.push(CompiledTraderSignalOp {
                    func: meta.func,
                    params: config.params.clone(),
                });
            }
        }
        self.compiled_cfg_ptr = ptr;
        self.compiled_cfg_len = len;
    }

    /// 输入基础周期已完成K线，更新信号，更新仓位
    pub fn update(&mut self, bar: &RawBar, signals_config: &[SignalConfig]) {
        let _ = self.update_profiled(bar, signals_config);
    }

    /// 与 update 行为一致，但返回分段耗时（纳秒）
    pub fn update_profiled(
        &mut self,
        bar: &RawBar,
        signals_config: &[SignalConfig],
    ) -> UpdateProfile {
        self.ensure_compiled_trader_ops(signals_config);

        let t_signals = Instant::now();
        // 1. 调用 signals 获得本根K线上的所有状态更新
        self.signals.update_signals(bar, signals_config);
        let signals_update_ns = t_signals.elapsed().as_nanos();

        // 1.5 执行 trader 级别的 signals（pos 系列：需要访问仓位状态）
        let t_trader_sig = Instant::now();
        let mut trader_sigs = Vec::new();
        for op in &self.compiled_trader_ops {
            let sigs = (op.func)(self, &op.params);
            trader_sigs.extend(sigs);
        }
        let trader_signals_ns = t_trader_sig.elapsed().as_nanos();

        let t_pos = Instant::now();
        for sig in trader_sigs {
            let (k, v) = (sig.key(), sig.value());
            self.signals.s.insert(k.clone(), v.clone());
            self.signals.signal_map.insert(k, v);
            self.signals.sigs.insert(sig);
        }

        // 2. 构建需要输入给 position 的上下文
        let lite_bar = LiteBar {
            id: bar.id,
            dt: bar.dt.into(),
            price: bar.close,
        };
        // 3. 遍历更新所有策略仓位
        let mut pos_event_match_ns = 0u128;
        let mut pos_fsm_ns = 0u128;
        let mut pos_risk_ns = 0u128;
        let mut pos_holds_ns = 0u128;
        for pos in &mut self.positions {
            let p =
                pos.update_profiled_with_signal_map(lite_bar, None, Some(&self.signals.signal_map));
            pos_event_match_ns += p.event_match_ns;
            pos_fsm_ns += p.fsm_ns;
            pos_risk_ns += p.risk_ns;
            pos_holds_ns += p.holds_ns;
        }
        let position_update_ns = t_pos.elapsed().as_nanos();

        UpdateProfile {
            signals_update_ns,
            trader_signals_ns,
            position_update_ns,
            pos_event_match_ns,
            pos_fsm_ns,
            pos_risk_ns,
            pos_holds_ns,
        }
    }

    /// 将各个仓位的交易对与持仓结果输出到指定目录的 parquet 文件中
    pub fn dump_results(&self, out_dir: &str) -> anyhow::Result<()> {
        let path = Path::new(out_dir);
        if !path.exists() {
            std::fs::create_dir_all(path)?;
        }

        let mut all_pairs = Vec::new();
        let mut all_holds = Vec::new();

        for pos in &self.positions {
            if let Ok(df) = pos.pairs()
                && df.height() > 0
            {
                all_pairs.push(df.lazy());
            }
            if let Ok(df) = pos.holds()
                && df.height() > 0
            {
                all_holds.push(df.lazy());
            }
        }

        if !all_pairs.is_empty() {
            let mut combined_pairs = concat(all_pairs, UnionArgs::default())?.collect()?;
            let mut file = File::create(path.join("pairs.parquet"))?;
            ParquetWriter::new(&mut file).finish(&mut combined_pairs)?;
        }

        if !all_holds.is_empty() {
            let mut combined_holds = concat(all_holds, UnionArgs::default())?.collect()?;
            let mut file = File::create(path.join("holds.parquet"))?;
            ParquetWriter::new(&mut file).finish(&mut combined_holds)?;
        }

        Ok(())
    }
}

impl TraderState for CzscTrader {
    #[inline]
    fn get_position(&self, name: &str) -> Option<&Position> {
        self.positions.iter().find(|p| p.name == name)
    }

    #[inline]
    fn get_czsc(&self, freq: &str) -> Option<&CZSC> {
        self.signals.kas.get(freq)
    }

    #[inline]
    fn latest_price(&self) -> Option<f64> {
        self.signals
            .s
            .get("close")
            .and_then(|x| x.parse::<f64>().ok())
    }
}
