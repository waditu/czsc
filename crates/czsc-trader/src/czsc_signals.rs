use crate::engine_v2::catalog::SignalCategory;
use crate::engine_v2::compiler::CompiledSignalPlanV2;
use crate::sig_parse::SignalConfig;
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::signal::Signal;
use czsc_signals::registry;
use czsc_signals::types::TaCache;
use czsc_utils::bar_generator::BarGenerator;
use std::collections::{BTreeMap, HashMap, HashSet};

#[derive(Clone)]
enum CompiledKlineSignalOp {
    Fast {
        exec: czsc_signals::types::FastKlineExecFn,
        params: serde_json::Value,
    },
    Dynamic {
        func: czsc_signals::types::SignalFn,
        params: HashMap<String, serde_json::Value>,
    },
}

#[derive(Clone)]
struct CompiledKlineFreqGroup {
    freq: String,
    ops: Vec<CompiledKlineSignalOp>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct BarFingerprint {
    id: i32,
    dt_ns: i64,
    open_bits: u64,
    close_bits: u64,
    high_bits: u64,
    low_bits: u64,
    vol_bits: u64,
    amount_bits: u64,
}

impl BarFingerprint {
    #[inline]
    fn from_bar(bar: &RawBar) -> Self {
        Self {
            id: bar.id,
            dt_ns: bar.dt.timestamp_nanos_opt().unwrap_or_default(),
            open_bits: bar.open.to_bits(),
            close_bits: bar.close.to_bits(),
            high_bits: bar.high.to_bits(),
            low_bits: bar.low.to_bits(),
            vol_bits: bar.vol.to_bits(),
            amount_bits: bar.amount.to_bits(),
        }
    }
}

/// 多级别信号计算引擎
pub struct CzscSignals {
    /// K 线合成器
    pub bg: BarGenerator,

    /// 当次计算的基础周期标的代码，例如 "000001.SZ"
    pub symbol: String,

    /// 各周期的 CZSC 分析引擎（有序，通常按周期由小到大）
    pub kas: BTreeMap<String, CZSC>,

    /// TA 指标缓存容器，按 freq_str 分组，例如 "日线" -> TaCache
    pub ta_cache: HashMap<String, TaCache>,

    /// 信号结果字典（每根 K 线生成完后更新，完全涵盖 python 版的 __dict__ 与 signal_dict）
    pub s: HashMap<String, String>,

    /// 当前K线触发的原始 Signal 对象的全集（被 trader 的位置策略直接消耗）
    pub sigs: HashSet<Signal>,
    /// Position 事件匹配使用的信号字典：key -> value
    pub signal_map: HashMap<String, String>,

    /// 预编译后的 K 线信号执行计划
    compiled_kline_groups: Vec<CompiledKlineFreqGroup>,
    use_plan_compiled: bool,
    compiled_cfg_ptr: usize,
    compiled_cfg_len: usize,
    /// 需要维护 CZSC 的频率集合；存在 trader 级信号时退化为全量维护
    required_kas_freqs: HashSet<String>,
    maintain_all_kas: bool,

    /// 按 freq 门控信号执行：末根 bar 未变化时复用上次结果
    last_freq_fingerprints: HashMap<String, BarFingerprint>,
    cached_freq_signals: HashMap<String, Vec<Signal>>,
}

impl CzscSignals {
    pub fn new(symbol: String, bg: BarGenerator) -> Self {
        let mut kas = BTreeMap::new();
        for (freq, bars_lock) in &bg.freq_bars {
            let bars = bars_lock.read();
            if !bars.is_empty() {
                let bars_vec: Vec<RawBar> = bars.iter().cloned().collect();
                kas.insert(freq.to_string(), CZSC::new(bars_vec, 50));
            }
        }

        Self {
            bg,
            symbol,
            kas,
            ta_cache: HashMap::new(),
            s: HashMap::new(),
            sigs: HashSet::new(),
            signal_map: HashMap::new(),
            compiled_kline_groups: Vec::new(),
            use_plan_compiled: false,
            compiled_cfg_ptr: 0,
            compiled_cfg_len: 0,
            required_kas_freqs: HashSet::new(),
            maintain_all_kas: false,
            last_freq_fingerprints: HashMap::new(),
            cached_freq_signals: HashMap::new(),
        }
    }

    fn ensure_compiled_kline_ops(&mut self, signals_config: &[SignalConfig]) {
        if self.use_plan_compiled {
            return;
        }
        let ptr = signals_config.as_ptr() as usize;
        let len = signals_config.len();
        if self.compiled_cfg_ptr == ptr && self.compiled_cfg_len == len {
            return;
        }

        let mut grouped: HashMap<String, Vec<CompiledKlineSignalOp>> = HashMap::new();
        self.required_kas_freqs.clear();
        self.maintain_all_kas = false;
        for config in signals_config {
            if config.freq.is_none() {
                // trader 级信号可能访问任意频率 CZSC，保守退化为全量维护
                self.maintain_all_kas = true;
            }
            if let Some(freq) = &config.freq
                && let Some(meta) = registry::SIGNAL_REGISTRY.get(config.name.as_str())
            {
                let op = if let Some(fast) = meta.fast_kline {
                    if let Some(p) = (fast.decode)(&config.params) {
                        CompiledKlineSignalOp::Fast {
                            exec: fast.exec,
                            params: p,
                        }
                    } else {
                        CompiledKlineSignalOp::Dynamic {
                            func: meta.func,
                            params: config.params.clone(),
                        }
                    }
                } else {
                    CompiledKlineSignalOp::Dynamic {
                        func: meta.func,
                        params: config.params.clone(),
                    }
                };
                grouped.entry(freq.clone()).or_default().push(op);
                self.required_kas_freqs.insert(freq.clone());
            }
        }
        let mut freqs: Vec<String> = grouped.keys().cloned().collect();
        freqs.sort();
        self.compiled_kline_groups.clear();
        self.compiled_kline_groups.reserve(freqs.len());
        for freq in freqs {
            if let Some(ops) = grouped.remove(&freq) {
                self.compiled_kline_groups
                    .push(CompiledKlineFreqGroup { freq, ops });
            }
        }
        self.compiled_cfg_ptr = ptr;
        self.compiled_cfg_len = len;
    }

    /// 使用 ExecutionPlan 的 signal_plan 一次性装载 K线信号执行计划。
    ///
    /// 该接口会切换到 plan 驱动模式，后续 `update_signals` 不再尝试按
    /// `signals_config` 进行运行期编译。
    pub fn load_compiled_signal_plan(&mut self, plan: &CompiledSignalPlanV2) -> Result<(), String> {
        let mut grouped: HashMap<String, Vec<CompiledKlineSignalOp>> = HashMap::new();
        self.required_kas_freqs.clear();
        self.maintain_all_kas = false;

        for op in &plan.ops {
            if matches!(op.category, SignalCategory::Trader) {
                // trader 级信号可能访问任意频率 CZSC，保守退化为全量维护
                self.maintain_all_kas = true;
                continue;
            }
            let Some(freq) = &op.freq else {
                continue;
            };
            let meta = registry::SIGNAL_REGISTRY
                .get(op.name.as_str())
                .ok_or_else(|| format!("未注册 K 线信号: {}", op.name))?;
            let sig_op = if let Some(fast) = meta.fast_kline {
                if let Some(p) = (fast.decode)(
                    &serde_json::from_value(op.params.clone())
                        .map_err(|e| format!("信号参数解析失败 {}: {e}", op.name))?,
                ) {
                    CompiledKlineSignalOp::Fast {
                        exec: fast.exec,
                        params: p,
                    }
                } else {
                    CompiledKlineSignalOp::Dynamic {
                        func: meta.func,
                        params: serde_json::from_value(op.params.clone())
                            .map_err(|e| format!("信号参数解析失败 {}: {e}", op.name))?,
                    }
                }
            } else {
                CompiledKlineSignalOp::Dynamic {
                    func: meta.func,
                    params: serde_json::from_value(op.params.clone())
                        .map_err(|e| format!("信号参数解析失败 {}: {e}", op.name))?,
                }
            };
            grouped.entry(freq.clone()).or_default().push(sig_op);
            self.required_kas_freqs.insert(freq.clone());
        }

        let mut freqs: Vec<String> = grouped.keys().cloned().collect();
        freqs.sort();
        self.compiled_kline_groups.clear();
        self.compiled_kline_groups.reserve(freqs.len());
        for freq in freqs {
            if let Some(ops) = grouped.remove(&freq) {
                self.compiled_kline_groups
                    .push(CompiledKlineFreqGroup { freq, ops });
            }
        }

        self.use_plan_compiled = true;
        self.compiled_cfg_ptr = 0;
        self.compiled_cfg_len = 0;
        Ok(())
    }

    /// 执行主更新流程
    pub fn update_signals(&mut self, bar: &RawBar, signals_config: &[SignalConfig]) {
        self.ensure_compiled_kline_ops(signals_config);

        // 1. 驱动 bg 喂入新 Bar，并同步各周期 CZSC
        let changed_freqs = self.advance_kas(bar, true);

        self.reset_signal_state(bar);
        self.compute_kline_signals(Some(&changed_freqs));
    }

    /// 预热后用当前状态 prime 一次信号缓存，对齐 Python `CzscSignals(bg)` 构造语义。
    ///
    /// Python 基线会在 `bg` 初始化完成后立刻调用 `get_signals_by_conf()`，因此像 ER
    /// 这类“历史 bar 只计算一次后缓存”的信号，必须在右侧主循环前先对当前末 bar
    /// 状态做一次信号计算，否则后续流式更新会与 Python 基线永久错位。
    pub fn prime_signals(&mut self, bar: &RawBar, signals_config: &[SignalConfig]) {
        self.ensure_compiled_kline_ops(signals_config);
        // 对齐 Python `CzscSignals(bg)`：预热后先基于 BG 快照一次性重建各频率 CZSC，
        // 再做首轮信号计算；避免 warmup 期间对同一高周期 dt 的增量更新造成路径漂移。
        self.rebuild_kas_from_bg();
        self.reset_signal_state(bar);
        self.compute_kline_signals(None);
    }

    fn reset_signal_state(&mut self, bar: &RawBar) {
        self.s.clear();
        self.sigs.clear();
        self.signal_map.clear();
        self.s.insert("symbol".to_string(), self.symbol.clone());
        self.s.insert("dt".to_string(), bar.dt.to_rfc3339());
        self.s.insert("id".to_string(), bar.id.to_string());
        self.s.insert("freq".to_string(), bar.freq.to_string());
        self.s.insert("open".to_string(), bar.open.to_string());
        self.s.insert("close".to_string(), bar.close.to_string());
        self.s.insert("high".to_string(), bar.high.to_string());
        self.s.insert("low".to_string(), bar.low.to_string());
        self.s.insert("vol".to_string(), bar.vol.to_string());
        self.s.insert("amount".to_string(), bar.amount.to_string());
    }

    fn compute_kline_signals(&mut self, changed_freqs: Option<&HashSet<String>>) {
        for group in &self.compiled_kline_groups {
            if let Some(changed_freqs) = changed_freqs
                && !changed_freqs.contains(group.freq.as_str())
                && let Some(cached_sigs) = self.cached_freq_signals.get(group.freq.as_str())
            {
                for sig in cached_sigs {
                    let (k, v) = (sig.key(), sig.value());
                    self.s.insert(k.clone(), v.clone());
                    self.signal_map.insert(k, v);
                    self.sigs.insert(sig.clone());
                }
                continue;
            }

            if let Some(czsc) = self.kas.get(group.freq.as_str()) {
                let cache = self.ta_cache.entry(group.freq.clone()).or_default();
                let mut freq_sigs = Vec::new();
                for op in &group.ops {
                    let sigs_res = match op {
                        CompiledKlineSignalOp::Fast { exec, params } => (exec)(czsc, params, cache),
                        CompiledKlineSignalOp::Dynamic { func, params } => {
                            (func)(czsc, params, cache)
                        }
                    };
                    for sig in sigs_res {
                        let (k, v) = (sig.key(), sig.value());
                        self.s.insert(k.clone(), v.clone());
                        self.signal_map.insert(k, v);
                        self.sigs.insert(sig.clone());
                        freq_sigs.push(sig);
                    }
                }
                self.cached_freq_signals
                    .insert(group.freq.clone(), freq_sigs);
            }
        }
    }

    /// 预热阶段仅推进 BG，不执行任何信号函数，也不增量维护 CZSC。
    ///
    /// 对齐 Python `generate_czsc_signals`：`bars_left` 只用于初始化 `BarGenerator`，
    /// 不会在 warmup 阶段调用 `update_signals`。CZSC 会在 warmup 结束后由
    /// `prime_signals` 基于 BG 快照一次性重建。
    pub fn warmup_bar(&mut self, bar: &RawBar) {
        let _ = self.bg.update_bar(bar);
    }

    fn rebuild_kas_from_bg(&mut self) {
        self.kas.clear();
        self.last_freq_fingerprints.clear();
        self.cached_freq_signals.clear();

        for (freq, bars_lock) in &self.bg.freq_bars {
            let bars = bars_lock.read();
            if bars.is_empty() {
                continue;
            }
            let bars_vec: Vec<RawBar> = bars.iter().cloned().collect();
            self.kas.insert(freq.to_string(), CZSC::new(bars_vec, 50));
        }
    }

    fn advance_kas(&mut self, bar: &RawBar, update_fingerprint: bool) -> HashSet<String> {
        let _ = self.bg.update_bar(bar);

        let mut changed_freqs: HashSet<String> = HashSet::new();
        for (freq, bars_lock) in &self.bg.freq_bars {
            let freq_str = freq.to_string();
            if !self.maintain_all_kas && !self.required_kas_freqs.contains(freq_str.as_str()) {
                continue;
            }
            let bars = bars_lock.read();
            if bars.is_empty() {
                continue;
            }

            let last_bar = bars.back().expect("bars not empty");
            let fingerprint = BarFingerprint::from_bar(last_bar);
            let is_changed = if update_fingerprint {
                let changed = self
                    .last_freq_fingerprints
                    .get(&freq_str)
                    .map(|prev| *prev != fingerprint)
                    .unwrap_or(true);
                self.last_freq_fingerprints
                    .insert(freq_str.clone(), fingerprint);
                changed
            } else {
                true
            };

            if !self.kas.contains_key(&freq_str) {
                let bars_vec: Vec<RawBar> = bars.iter().cloned().collect();
                let czsc = CZSC::new(bars_vec, 50);
                self.kas.insert(freq_str.clone(), czsc);
                changed_freqs.insert(freq_str);
            } else if is_changed {
                if let Some(czsc) = self.kas.get_mut(&freq_str) {
                    czsc.update_bar(last_bar.clone());
                }
                changed_freqs.insert(freq_str);
            }
        }
        changed_freqs
    }
}
