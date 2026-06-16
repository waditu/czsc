use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use serde_json::Value;
use std::collections::HashMap;

/// MACD 缓存三元组
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct MacdSeries {
    pub ids: Vec<i32>,
    pub dif: Vec<f64>,
    pub dea: Vec<f64>,
    pub macd: Vec<f64>,
}

/// BOLL 缓存三元组
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct BollSeries {
    pub upper: Vec<f64>,
    pub mid: Vec<f64>,
    pub lower: Vec<f64>,
}

/// KDJ 缓存三元组
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct KdjSeries {
    pub ids: Vec<i32>,
    pub k: Vec<f64>,
    pub d: Vec<f64>,
    pub j: Vec<f64>,
}

/// TA 指标增量缓存，存放所有由纯 Rust 计算产生的序列数据
#[derive(Debug, Clone, Default, serde::Serialize, serde::Deserialize)]
pub struct TaCache {
    /// 简单单点序列（如 EMA/SMA/RSI/ATR）的缓存
    pub series: HashMap<String, Vec<f64>>,

    /// MACD 数据缓存
    pub macd: HashMap<String, MacdSeries>,

    /// BOLL 数据缓存
    pub boll: HashMap<String, BollSeries>,

    /// boll 对应的 bar id 序列（用于 bars_raw 截断后对齐）
    pub boll_ids: HashMap<String, Vec<i32>>,

    /// KDJ 数据缓存
    pub kdj: HashMap<String, KdjSeries>,

    /// series 对应的 bar id 序列（用于 bars_raw 截断后对齐）
    pub series_ids: HashMap<String, Vec<i32>>,

    /// 标记已缓存的最大长度，用于增量判断
    pub last_len: usize,
}

impl TaCache {
    pub fn new() -> Self {
        Self::default()
    }
}

/// 信号函数签名（单 freq 计算）
pub type SignalFn = fn(&CZSC, &HashMap<String, Value>, &mut TaCache) -> Vec<Signal>;
pub type FastKlineDecodeFn = fn(&HashMap<String, Value>) -> Option<Value>;
pub type FastKlineExecFn = fn(&CZSC, &Value, &mut TaCache) -> Vec<Signal>;

#[derive(Clone, Copy)]
pub struct FastKlineMeta {
    pub decode: FastKlineDecodeFn,
    pub exec: FastKlineExecFn,
}

/// 运行时 K 线信号元信息（由 `SignalDescriptor` 归并而来）。
pub struct SignalMeta {
    pub func: SignalFn,
    pub param_template: &'static str,
    pub fast_kline: Option<FastKlineMeta>,
}

/// 依赖 TraderState 的信号函数签名（pos 系列，需要仓位和K线的联合状态）
pub type TraderSignalFn = fn(
    cat: &dyn czsc_core::objects::state::TraderState,
    params: &HashMap<String, Value>,
) -> Vec<Signal>;

/// 运行时 Trader 信号元信息（由 `SignalDescriptor` 归并而来）。
pub struct TraderSignalMeta {
    pub func: TraderSignalFn,
    pub param_template: &'static str,
}

/// 对信号函数的类型化引用，用于在注册中心中区分 K 线级与 Trader 级信号。
#[derive(Clone, Copy)]
pub enum SignalFnRef {
    /// 仅依赖 `CZSC + params + TaCache` 的 K 线级信号函数。
    Kline(SignalFn),
    /// 依赖 `TraderState + params` 的 Trader/Position 级信号函数。
    Trader(TraderSignalFn),
}

/// 信号描述符（编译期元数据）。
///
/// 该结构由 `#[signal(...)]` 宏生成并通过 `inventory` 自动收集，
/// 作为信号注册、编译计划构建与执行分派的单一元数据来源。
#[derive(Clone, Copy)]
pub struct SignalDescriptor {
    /// 信号类别：`kline` 或 `trader`。
    pub category: &'static str,
    /// 信号名称（如 `tas_ma_base_V221101`）。
    pub name: &'static str,
    /// 参数模板（与 Python/策略配置保持一致）。
    pub template: &'static str,
    /// 内部操作码名称（用于执行层分派与冲突检测）。
    pub opcode: &'static str,
    /// 参数类型标识（用于后续 typed params 映射）。
    pub param_kind: &'static str,
    /// 函数指针引用（按 `category` 解释为 Kline 或 Trader 函数）。
    pub func_ref: SignalFnRef,
    /// 可选 fast-path 元信息；存在时可在执行层避免 HashMap 解释开销。
    pub fast_kline: Option<FastKlineMeta>,
}
