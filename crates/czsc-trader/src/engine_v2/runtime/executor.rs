use crate::czsc_signals::CzscSignals;
use crate::engine_v2::catalog::SignalCategory;
use crate::engine_v2::compiler::ExecutionPlan;
use chrono::{DateTime, NaiveDate, NaiveDateTime, Utc};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::market::Market;
use czsc_core::objects::position::{LiteBar, Position};
use czsc_core::objects::state::TraderState;
use czsc_signals::registry::TRADER_SIGNAL_REGISTRY;
use czsc_signals::types::TraderSignalFn;
use czsc_utils::bar_generator::BarGenerator;
use czsc_utils::freq_data::infer_market_from_bars;
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::time::Instant;

#[derive(Debug, Clone, Copy, Default)]
pub struct CoreLoopProfileV2 {
    pub bars: usize,
    pub signals_update_ns: u128,
    pub trader_signals_ns: u128,
    pub position_update_ns: u128,
    pub pos_event_match_ns: u128,
    pub pos_fsm_ns: u128,
    pub pos_risk_ns: u128,
    pub pos_holds_ns: u128,
}

impl CoreLoopProfileV2 {
    pub fn total_ns(&self) -> u128 {
        self.signals_update_ns + self.trader_signals_ns + self.position_update_ns
    }
}

pub struct RunOutput {
    pub bars_count: usize,
    pub signal_rows: Vec<HashMap<String, String>>,
    pub positions: Vec<czsc_core::objects::position::Position>,
    pub elapsed_ms: i64,
    pub profile: Option<CoreLoopProfileV2>,
}

pub struct UnifiedExecEngine;

#[derive(Clone)]
struct CompiledTraderSignalOp {
    func: TraderSignalFn,
    params: HashMap<String, Value>,
}

struct RuntimeTraderState<'a> {
    positions: &'a [Position],
    kas: &'a std::collections::BTreeMap<String, CZSC>,
    latest_price: Option<f64>,
}

impl TraderState for RuntimeTraderState<'_> {
    #[inline]
    fn get_position(&self, name: &str) -> Option<&Position> {
        self.positions.iter().find(|p| p.name == name)
    }

    #[inline]
    fn get_czsc(&self, freq: &str) -> Option<&CZSC> {
        self.kas.get(freq)
    }

    #[inline]
    fn latest_price(&self) -> Option<f64> {
        self.latest_price
    }
}

fn compile_trader_ops(plan: &ExecutionPlan) -> Result<Vec<CompiledTraderSignalOp>, String> {
    let mut ops = Vec::new();
    for op in &plan.signal_plan.ops {
        if matches!(op.category, SignalCategory::Trader)
            && let Some(meta) = TRADER_SIGNAL_REGISTRY.get(op.name.as_str())
        {
            ops.push(CompiledTraderSignalOp {
                func: meta.func,
                params: serde_json::from_value(op.params.clone())
                    .map_err(|e| format!("trader 信号参数解析失败 {}: {e}", op.name))?,
            });
        }
    }
    Ok(ops)
}

impl UnifiedExecEngine {
    pub fn run(
        plan: &ExecutionPlan,
        mut bars: Vec<RawBar>,
        sdt_override: Option<&str>,
        emit_signals: bool,
        enable_profile: bool,
    ) -> Result<RunOutput, String> {
        let t0 = Instant::now();
        if bars.is_empty() {
            return Err("bars 为空，无法执行回测".to_string());
        }

        let base_freq = plan
            .base_freq
            .parse::<Freq>()
            .map_err(|_| "strategy.base_freq 解析失败".to_string())?;

        let requested_market = parse_market(plan.market.as_deref());
        let market = infer_effective_market(&bars, base_freq, requested_market);
        let freqs = collect_freqs(base_freq, &plan.signals_config)?;
        let trader_ops = compile_trader_ops(plan)?;
        // 对齐 Python 基线 `generate_czsc_signals(init_n=500)` 的左右分段逻辑：
        // 1) bars_left = bars[dt < sdt]
        // 2) 若 len(bars_left) <= init_n，则 bars_left=bars[:init_n], bars_right=bars[init_n:]
        // 3) 否则 bars_right = bars[dt >= sdt]
        // 当 bars_right 为空时，不执行回测主循环。
        const INIT_N: usize = 500;
        // 对齐 Python `CzscStrategyBase.init_bar_generator`：
        // - 默认 sdt = "20200101"
        // - bars_init 使用 `dt <= sdt`
        // - 若 len(bars_init) > n(500): bars1=bars_init, bars2=dt > sdt
        // - 否则 bars1=bars[:n], bars2=bars[n:]
        let sdt_final = sdt_override
            .map(|x| x.to_string())
            .or_else(|| plan.sdt.clone())
            .or_else(|| Some("20200101".to_string()));
        let cutoff = sdt_final.as_deref().and_then(parse_sdt_utc);
        let bars_len = bars.len();
        let start_idx = if let Some(c) = cutoff {
            let bars_init_count = if plan.include_sdt_bar {
                bars.iter().take_while(|b| b.dt < c).count()
            } else {
                bars.iter().take_while(|b| b.dt <= c).count()
            };
            if !trader_ops.is_empty() {
                // Trader 对照链路（benchmarks/generate_py_trader_signals_df）使用显式 warmup_n，
                // 调用侧会将 sdt 设为 bars[warmup_n - 1].dt；这里按 sdt 精确预热，
                // 避免被固定 INIT_N=500 覆盖导致状态路径错位。
                bars_init_count.clamp(1, bars_len.saturating_sub(1))
            } else if bars_init_count > INIT_N {
                bars_init_count
            } else {
                bars_len.min(INIT_N)
            }
        } else {
            bars_len.min(INIT_N)
        };

        let bg = BarGenerator::new(base_freq, freqs, plan.bg_max_count, market)
            .map_err(|e| format!("初始化 BarGenerator 失败: {e:?}"))?;

        let mut signals = CzscSignals::new(plan.symbol.clone(), bg);
        signals
            .load_compiled_signal_plan(&plan.signal_plan)
            .map_err(|e| format!("装载编译信号计划失败: {e}"))?;
        let mut positions = plan.positions.clone();

        // 先用左侧 bars 初始化 BG / CZSC。
        // warmup_bar 现在 propagate BarGenerator 的硬错（NaN OHLCV / freq mismatch / 非交易时间），
        // 避免上游脏数据让 BG 进入 stale 状态后续算出"幻象"信号。
        for bar in bars.iter().take(start_idx) {
            signals
                .warmup_bar(bar)
                .map_err(|e| format!("warmup_bar 失败 (dt={}): {e}", bar.dt))?;
        }

        // 对齐 Python `CzscSignals(bg)`：warmup 完成后会立刻计算一次当前信号，
        // 用于初始化 bar.cache / 指标缓存，但不会把这一时刻计入 bars_right 输出，
        // 也不会推进 Position。
        if start_idx > 0 {
            let prime_bar = &bars[start_idx - 1];
            signals.prime_signals(prime_bar, &plan.signals_config);

            if !trader_ops.is_empty() {
                let latest_price = signals
                    .s
                    .get("close")
                    .and_then(|x| x.parse::<f64>().ok())
                    .or(Some(prime_bar.close));
                let state = RuntimeTraderState {
                    positions: &positions,
                    kas: &signals.kas,
                    latest_price,
                };
                for op in &trader_ops {
                    for sig in (op.func)(&state, &op.params) {
                        let (k, v) = (sig.key(), sig.value());
                        signals.s.insert(k.clone(), v.clone());
                        signals.signal_map.insert(k, v);
                        signals.sigs.insert(sig);
                    }
                }
            }
        }

        let bars_count = bars_len.saturating_sub(start_idx);
        let mut rows = if emit_signals {
            Vec::with_capacity(bars_count)
        } else {
            Vec::new()
        };
        let mut profile = CoreLoopProfileV2::default();

        for bar in bars.drain(start_idx..) {
            let t_signals = Instant::now();
            signals
                .update_signals(&bar, &plan.signals_config)
                .map_err(|e| format!("update_signals 失败 (dt={}): {e}", bar.dt))?;
            let signals_update_ns = t_signals.elapsed().as_nanos();

            let t_trader_sig = Instant::now();
            if !trader_ops.is_empty() {
                let latest_price = signals
                    .s
                    .get("close")
                    .and_then(|x| x.parse::<f64>().ok())
                    .or(Some(bar.close));
                let state = RuntimeTraderState {
                    positions: &positions,
                    kas: &signals.kas,
                    latest_price,
                };
                for op in &trader_ops {
                    for sig in (op.func)(&state, &op.params) {
                        let (k, v) = (sig.key(), sig.value());
                        signals.s.insert(k.clone(), v.clone());
                        signals.signal_map.insert(k, v);
                        signals.sigs.insert(sig);
                    }
                }
            }
            let trader_signals_ns = t_trader_sig.elapsed().as_nanos();

            let lite_bar = LiteBar {
                id: bar.id,
                dt: bar.dt.into(),
                price: bar.close,
            };
            let t_pos = Instant::now();
            let mut pos_event_match_ns = 0u128;
            let mut pos_fsm_ns = 0u128;
            let mut pos_risk_ns = 0u128;
            let mut pos_holds_ns = 0u128;
            for pos in &mut positions {
                let p =
                    pos.update_profiled_with_signal_map(lite_bar, None, Some(&signals.signal_map));
                pos_event_match_ns += p.event_match_ns;
                pos_fsm_ns += p.fsm_ns;
                pos_risk_ns += p.risk_ns;
                pos_holds_ns += p.holds_ns;
            }
            let position_update_ns = t_pos.elapsed().as_nanos();

            if enable_profile {
                profile.bars += 1;
                profile.signals_update_ns += signals_update_ns;
                profile.trader_signals_ns += trader_signals_ns;
                profile.position_update_ns += position_update_ns;
                profile.pos_event_match_ns += pos_event_match_ns;
                profile.pos_fsm_ns += pos_fsm_ns;
                profile.pos_risk_ns += pos_risk_ns;
                profile.pos_holds_ns += pos_holds_ns;
            }
            if emit_signals {
                rows.push(signals.s.clone());
            }
        }

        Ok(RunOutput {
            bars_count,
            signal_rows: rows,
            positions,
            elapsed_ms: t0.elapsed().as_millis() as i64,
            profile: enable_profile.then_some(profile),
        })
    }
}

fn collect_freqs(
    base_freq: Freq,
    signals_config: &[crate::sig_parse::SignalConfig],
) -> Result<Vec<Freq>, String> {
    let push_freq = |freq_str: &str, freq_set: &mut HashSet<Freq>| {
        if let Ok(f) = freq_str.parse::<Freq>()
            && f != base_freq
        {
            freq_set.insert(f);
        }
    };

    let mut freq_set: HashSet<Freq> = HashSet::new();
    for sc in signals_config {
        if let Some(freq_str) = &sc.freq {
            push_freq(freq_str, &mut freq_set);
        }
        // 兼容 trader 级信号通过 params 传入多周期字段（freq/freq1/freq2/...）
        for (k, v) in &sc.params {
            if !k.starts_with("freq") {
                continue;
            }
            if let Some(freq_str) = v.as_str() {
                push_freq(freq_str, &mut freq_set);
            }
        }
    }

    let mut freqs: Vec<Freq> = freq_set.into_iter().collect();
    freqs.sort();
    Ok(freqs)
}

fn parse_market(market: Option<&str>) -> Market {
    match market.unwrap_or("默认") {
        "A股" | "AShare" | "ashare" => Market::AShare,
        "期货" | "Futures" | "futures" => Market::Futures,
        _ => Market::Default,
    }
}

fn infer_effective_market(bars: &[RawBar], base_freq: Freq, requested: Market) -> Market {
    let detected = infer_market_from_bars(bars, base_freq);
    if matches!(requested, Market::Default) || requested != detected {
        detected
    } else {
        requested
    }
}

fn parse_sdt_utc(s: &str) -> Option<DateTime<Utc>> {
    if s.is_empty() {
        return None;
    }
    if let Ok(dt) = DateTime::parse_from_rfc3339(s) {
        return Some(dt.with_timezone(&Utc));
    }
    if let Ok(ndt) = NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S") {
        return Some(DateTime::from_naive_utc_and_offset(ndt, Utc));
    }
    if let Ok(ndt) = NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S") {
        return Some(DateTime::from_naive_utc_and_offset(ndt, Utc));
    }
    if let Ok(ndt) = NaiveDateTime::parse_from_str(s, "%Y-%m-%dT%H:%M:%S%.f") {
        return Some(DateTime::from_naive_utc_and_offset(ndt, Utc));
    }
    if let Ok(d) = NaiveDate::parse_from_str(s, "%Y-%m-%d")
        && let Some(ndt) = d.and_hms_opt(0, 0, 0)
    {
        return Some(DateTime::from_naive_utc_and_offset(ndt, Utc));
    }
    if let Ok(d) = NaiveDate::parse_from_str(s, "%Y%m%d")
        && let Some(ndt) = d.and_hms_opt(0, 0, 0)
    {
        return Some(DateTime::from_naive_utc_and_offset(ndt, Utc));
    }
    None
}

#[cfg(test)]
mod tests {
    use super::{collect_freqs, infer_effective_market};
    use crate::sig_parse::SignalConfig;
    use chrono::{NaiveDateTime, TimeZone, Utc};
    use czsc_core::objects::{bar::RawBarBuilder, freq::Freq, market::Market};
    use serde_json::json;
    use std::collections::HashMap;

    #[test]
    fn test_collect_freqs_includes_trader_freq_params() {
        let mut trader_params = HashMap::new();
        trader_params.insert("freq1".to_string(), json!("日线"));
        trader_params.insert("freq2".to_string(), json!("60分钟"));
        let mut kline_params = HashMap::new();
        kline_params.insert("di".to_string(), json!(1));

        let cfgs = vec![
            SignalConfig {
                name: "cat_macd_V230518".to_string(),
                freq: None,
                params: trader_params,
            },
            SignalConfig {
                name: "tas_ma_base_V221101".to_string(),
                freq: Some("15分钟".to_string()),
                params: kline_params,
            },
        ];
        let freqs = collect_freqs(Freq::F60, &cfgs).expect("collect freqs should succeed");
        assert!(freqs.contains(&Freq::D));
        assert!(freqs.contains(&Freq::F15));
        assert!(!freqs.contains(&Freq::F60));
    }

    #[test]
    fn test_collect_freqs_keeps_freq_enum_order() {
        let mut trader_params = HashMap::new();
        trader_params.insert("freq1".to_string(), json!("5分钟"));
        trader_params.insert("freq2".to_string(), json!("日线"));
        let cfgs = vec![
            SignalConfig {
                name: "cat_macd_V230518".to_string(),
                freq: None,
                params: trader_params,
            },
            SignalConfig {
                name: "tas_ma_base_V221101".to_string(),
                freq: Some("15分钟".to_string()),
                params: HashMap::new(),
            },
        ];
        let freqs = collect_freqs(Freq::F60, &cfgs).expect("collect freqs should succeed");
        assert_eq!(freqs, vec![Freq::F5, Freq::F15, Freq::D]);
    }

    #[test]
    fn test_infer_effective_market_falls_back_to_detected_default_for_utc_intraday_bars() {
        let mk = |dt: &str| {
            RawBarBuilder::default()
                .symbol("000001.SZ".to_string())
                .id(0)
                .dt(Utc.from_utc_datetime(
                    &NaiveDateTime::parse_from_str(dt, "%Y-%m-%d %H:%M:%S").unwrap(),
                ))
                .freq(Freq::F30)
                .open(1.0)
                .close(1.0)
                .high(1.0)
                .low(1.0)
                .vol(1.0)
                .amount(1.0)
                .build()
                .unwrap()
        };
        let bars = vec![
            mk("2015-03-30 17:30:00"),
            mk("2015-03-30 18:00:00"),
            mk("2015-03-30 18:30:00"),
            mk("2015-03-30 19:00:00"),
            mk("2015-03-30 19:30:00"),
            mk("2015-03-30 21:30:00"),
            mk("2015-03-30 22:00:00"),
            mk("2015-03-30 22:30:00"),
            mk("2015-03-30 23:00:00"),
        ];

        assert_eq!(
            infer_effective_market(&bars, Freq::F30, Market::AShare),
            Market::Default
        );
    }
}
