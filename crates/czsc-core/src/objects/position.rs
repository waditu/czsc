// czsc-only: pyo3 与 Python wrapper 的 import 通过 `python` feature 进行门控，
// 以便 non-python 构建。polars 与 log 保持无条件 import，因为 Position
// 在 cfg 块外面也会用到它们。参见 docs/MIGRATION_NOTES.md §2.4。
#![allow(unused)]
use anyhow::{Context, anyhow};
use chrono::{DateTime, FixedOffset, NaiveDateTime};
use log::warn;
use polars::{df, prelude::*};
use serde::{Deserialize, Serialize};
use std::cell::{Ref, RefCell};
use std::collections::{HashMap, HashSet};
use std::fmt;
use std::fs;
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::str::FromStr;
use std::time::Instant;

use super::event::Event;
use super::operate::Operate;
use super::signal::{ANY, Signal};

#[cfg(feature = "python")]
use super::event::PyEvent;
#[cfg(feature = "python")]
use super::signal::PySignal;
#[cfg(feature = "python")]
use pyo3::exceptions::PyValueError;
#[cfg(feature = "python")]
use pyo3::prelude::*;
#[cfg(feature = "python")]
use pyo3::types::PyBytes;

/// 解析 operate 字符串，支持英文缩写和中文名称
fn parse_operate(s: &str) -> Result<Operate, String> {
    // 首先尝试英文缩写（EnumString）
    if let Ok(op) = Operate::from_str(s) {
        return Ok(op);
    }

    // 然后尝试中文名称
    match s {
        "持多" => Ok(Operate::HL),
        "持空" => Ok(Operate::HS),
        "持币" => Ok(Operate::HO),
        "开多" => Ok(Operate::LO),
        "平多" => Ok(Operate::LE),
        "开空" => Ok(Operate::SO),
        "平空" => Ok(Operate::SE),
        _ => Err(format!("未知的operate值: {s}")),
    }
}

#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

#[derive(Clone, Copy, Debug, Default, PartialEq)]
pub enum Pos {
    /// 空
    Short,
    /// 空仓
    #[default]
    Flat,
    /// 多
    Long,
}

impl fmt::Display for Pos {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let s = match self {
            Pos::Short => "空",
            Pos::Flat => "空仓",
            Pos::Long => "多",
        };
        write!(f, "{s}")
    }
}

impl Pos {
    /// 转换为数值，用于数学运算
    pub fn to_f64(self) -> f64 {
        match self {
            Pos::Short => -1.0,
            Pos::Flat => 0.0,
            Pos::Long => 1.0,
        }
    }

    /// 从数值创建Pos
    pub fn from_f64(value: f64) -> Self {
        if value > 0.5 {
            Pos::Long
        } else if value < -0.5 {
            Pos::Short
        } else {
            Pos::Flat
        }
    }
}

/// 精简版价格线
#[derive(Clone, Copy, Debug)]
pub struct LiteBar {
    pub id: i32,
    pub dt: DateTime<FixedOffset>,
    pub price: f64,
}

#[derive(Debug, Clone, Copy, Default)]
pub struct PositionUpdateProfile {
    pub event_match_ns: u128,
    pub fsm_ns: u128,
    pub risk_ns: u128,
    pub holds_ns: u128,
}

const ANY_CODE: i32 = -1;
const UNKNOWN_CODE: i32 = 0;

#[derive(Debug, Clone, Copy)]
struct EncodedSignalValue {
    v1_code: i32,
    v2_code: i32,
    v3_code: i32,
    score: i32,
}

#[derive(Debug, Clone)]
struct CachedEncodedSignalValue {
    raw: String,
    encoded: EncodedSignalValue,
}

#[derive(Debug, Clone, Copy)]
struct EncodedSignalClause {
    key_id: usize,
    v1_code: i32,
    v2_code: i32,
    v3_code: i32,
    min_score: i32,
}

#[derive(Debug, Clone)]
struct CompiledEventMatcher {
    signals_all: Vec<EncodedSignalClause>,
    signals_any: Vec<EncodedSignalClause>,
    signals_not: Vec<EncodedSignalClause>,
}

#[derive(Debug, Clone, Default)]
struct PositionEventMatcher {
    keys: Vec<String>,
    key_to_id: HashMap<String, usize>,
    value_to_code: HashMap<String, i32>,
    events: Vec<CompiledEventMatcher>,
}

impl PositionEventMatcher {
    fn key_id(&mut self, key: String) -> usize {
        if let Some(id) = self.key_to_id.get(key.as_str()) {
            return *id;
        }
        let id = self.keys.len();
        self.keys.push(key.clone());
        self.key_to_id.insert(key, id);
        id
    }

    fn value_code(&mut self, v: &str) -> i32 {
        if v == ANY {
            return ANY_CODE;
        }
        if let Some(code) = self.value_to_code.get(v) {
            return *code;
        }
        let code = self.value_to_code.len() as i32 + 1;
        self.value_to_code.insert(v.to_string(), code);
        code
    }

    fn parse_v123_score(v: &str) -> Option<(&str, &str, &str, i32)> {
        let mut it = v.splitn(4, '_');
        let v1 = it.next()?;
        let v2 = it.next()?;
        let v3 = it.next()?;
        let score = it.next()?.parse::<i32>().ok()?;
        Some((v1, v2, v3, score))
    }

    fn compile_signal_clause(&mut self, signal: &Signal) -> Option<EncodedSignalClause> {
        let key_id = self.key_id(signal.key());
        let value = signal.value();
        let (v1, v2, v3, score) = Self::parse_v123_score(value.as_str())?;
        Some(EncodedSignalClause {
            key_id,
            v1_code: self.value_code(v1),
            v2_code: self.value_code(v2),
            v3_code: self.value_code(v3),
            min_score: score,
        })
    }

    fn compile_from_position(position: &Position) -> Self {
        let mut matcher = Self::default();
        matcher
            .events
            .reserve(position.opens.len() + position.exits.len());
        for e in position.opens.iter().chain(position.exits.iter()) {
            let mut all = Vec::with_capacity(e.signals_all.len());
            let mut any = Vec::with_capacity(e.signals_any.len());
            let mut not = Vec::with_capacity(e.signals_not.len());
            for s in &e.signals_all {
                if let Some(c) = matcher.compile_signal_clause(s) {
                    all.push(c);
                }
            }
            for s in &e.signals_any {
                if let Some(c) = matcher.compile_signal_clause(s) {
                    any.push(c);
                }
            }
            for s in &e.signals_not {
                if let Some(c) = matcher.compile_signal_clause(s) {
                    not.push(c);
                }
            }
            matcher.events.push(CompiledEventMatcher {
                signals_all: all,
                signals_any: any,
                signals_not: not,
            });
        }
        matcher
    }

    #[inline]
    fn encode_runtime_values_inplace(
        &self,
        signal_map: &HashMap<String, String>,
        values: &mut [Option<EncodedSignalValue>],
        cache: &mut [Option<CachedEncodedSignalValue>],
    ) {
        for v in values.iter_mut() {
            *v = None;
        }
        for (key_id, key) in self.keys.iter().enumerate() {
            if let Some(raw) = signal_map.get(key.as_str()) {
                if let Some(Some(cached)) = cache.get(key_id)
                    && cached.raw == *raw
                {
                    values[key_id] = Some(cached.encoded);
                    continue;
                }

                if let Some((v1, v2, v3, score)) = Self::parse_v123_score(raw) {
                    let v1_code = self.value_to_code.get(v1).copied().unwrap_or(UNKNOWN_CODE);
                    let v2_code = self.value_to_code.get(v2).copied().unwrap_or(UNKNOWN_CODE);
                    let v3_code = self.value_to_code.get(v3).copied().unwrap_or(UNKNOWN_CODE);
                    let encoded = EncodedSignalValue {
                        v1_code,
                        v2_code,
                        v3_code,
                        score,
                    };
                    values[key_id] = Some(encoded);
                    if let Some(slot) = cache.get_mut(key_id) {
                        *slot = Some(CachedEncodedSignalValue {
                            raw: raw.clone(),
                            encoded,
                        });
                    }
                } else if let Some(slot) = cache.get_mut(key_id) {
                    *slot = None;
                }
            }
        }
    }

    #[inline]
    fn clause_match(values: &[Option<EncodedSignalValue>], c: EncodedSignalClause) -> bool {
        if let Some(value) = values.get(c.key_id).and_then(|v| *v) {
            value.score >= c.min_score
                && (c.v1_code == ANY_CODE || c.v1_code == value.v1_code)
                && (c.v2_code == ANY_CODE || c.v2_code == value.v2_code)
                && (c.v3_code == ANY_CODE || c.v3_code == value.v3_code)
        } else {
            false
        }
    }

    fn find_first_match(
        &self,
        signal_map: &HashMap<String, String>,
        values: &mut [Option<EncodedSignalValue>],
        cache: &mut [Option<CachedEncodedSignalValue>],
    ) -> Option<usize> {
        self.encode_runtime_values_inplace(signal_map, values, cache);
        for (idx, evt) in self.events.iter().enumerate() {
            if evt
                .signals_not
                .iter()
                .any(|c| Self::clause_match(values, *c))
            {
                continue;
            }
            if evt
                .signals_all
                .iter()
                .any(|c| !Self::clause_match(values, *c))
            {
                continue;
            }
            if !evt.signals_any.is_empty()
                && !evt
                    .signals_any
                    .iter()
                    .any(|c| Self::clause_match(values, *c))
            {
                continue;
            }
            return Some(idx);
        }
        None
    }
}

#[derive(Debug, Clone)]
pub struct TempState {
    /// 最近一次信号传入的时间
    pub end_dt: DateTime<FixedOffset>,
    /// 最近一次开多交易的时间（可无）
    pub last_lo_dt: Option<DateTime<FixedOffset>>,
    /// 最近一次开空交易的时间（可无）
    pub last_so_dt: Option<DateTime<FixedOffset>>,
}

/// 操作记录（push 到 operates）
#[allow(unused)]
#[derive(Debug, Clone)]
pub struct OperateRecord {
    pub symbol: String,
    pub dt: DateTime<FixedOffset>,
    pub bar_id: i32,
    pub price: f64,
    pub op: Operate,
    pub op_desc: Option<String>,
    pub pos: Pos,
}

/// 持仓快照（push 到 holds）
#[derive(Debug, Clone)]
pub struct HoldRecord {
    pub dt: DateTime<FixedOffset>,
    pub pos: Pos,
    pub price: f64,
    pub n1b: Option<f64>, // 下一K线的收益率，用于计算截面等权收益
}

#[derive(Default)]
pub struct HoldColumns {
    pub dt: Vec<NaiveDateTime>, // NaiveDateTime兼容Polars格式
    pub pos: Vec<i32>,
    pub price: Vec<f64>,
    pub n1b: Vec<Option<f64>>, // 下一K线的收益率
}

impl HoldColumns {
    pub fn from_records(records: Vec<HoldRecord>) -> Self {
        let mut cols = HoldColumns::default();
        cols.dt.reserve(records.len());
        cols.pos.reserve(records.len());
        cols.price.reserve(records.len());
        cols.n1b.reserve(records.len());

        for r in records {
            cols.dt.push(r.dt.naive_local());
            cols.pos.push(r.pos.to_f64() as i32);
            cols.price.push(r.price);
            cols.n1b.push(r.n1b);
        }

        cols
    }

    pub fn into_df(self) -> anyhow::Result<DataFrame> {
        let df = df![
            "dt" => self.dt,
            "pos" => self.pos,
            "price" => self.price,
            "n1b" => self.n1b,
        ]
        .context("创建 Hold DataFrame 失败")?;

        Ok(df)
    }
}

/// 记录最近一次用于计算止损/超时的开仓基准
#[allow(unused)]
#[derive(Debug, Clone)]
pub struct LastEvent {
    pub dt: DateTime<FixedOffset>,
    pub bar_id: i32,
    pub price: f64,
    pub op: Operate,
    pub op_desc: Option<String>,
}

/// 列式记录的交易集合（所有字段按列存放）
#[derive(Debug, Clone, Default)]
pub struct TradePairsColumns<'a> {
    /// 标的代码（例如 "000001.SH"）
    pub symbol: Vec<&'a str>,
    /// 策略标记（Position的名称）
    pub strategy_mark: Vec<&'a str>,
    /// 交易方向（例如 "多头" 或 "空头"）
    pub direction: Vec<&'a str>,
    /// 开仓时间（有明确时间的 DateTime）
    pub open_dt: Vec<NaiveDateTime>,
    /// 平仓时间（若仍持仓则为 None）, NaiveDateTime是为了兼容 Polars时间格式
    pub close_dt: Vec<NaiveDateTime>,
    /// 开仓价格
    pub open_price: Vec<f64>,
    /// 平仓价格（若仍持仓则为 None）
    pub close_price: Vec<f64>,
    /// 持仓 K 线数
    pub holding_bar: Vec<i32>,
    /// 事件序列（交易触发与出场说明）
    pub event_sequence: Vec<String>,
    /// 持仓天数（天数，浮点数以支持小于1天的持仓）
    pub holding_day: Vec<f64>,
    /// 盈亏比例（若未知则为 None）
    pub yield_profit_ratio: Vec<Option<f64>>,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct Position {
    /// 开仓交易事件列表
    pub opens: Vec<Event>,
    /// 平仓交易事件列表，允许为空
    pub exits: Vec<Event>,
    /// 同类型开仓间隔时间，单位：秒；默认值为 0，表示同类型开仓间隔没有约束
    pub interval: i64,
    /// 最大允许持仓K线数量限制为最近一个开仓事件触发后的 timeout 根基础周期K线
    pub timeout: i32,
    /// 最大允许亏损比例，单位：百分比（如0.05表示5%）；成本的计算以最近一个开仓事件触发价格为准
    pub stop_loss: f64,
    /// T0: 是否允许T0交易，默认为 False 表示不允许T0交易
    #[serde(rename = "T0")]
    pub t0: bool,
    /// 仓位名称，默认值为第一个开仓事件的名称
    pub name: String,
    /// 标的代码
    pub symbol: String,

    // 下面是运行时字段（不序列化）
    #[serde(skip)]
    temp_state: Option<TempState>,

    #[serde(skip)]
    pos_changed: bool,
    #[serde(skip)]
    pub operates: Vec<OperateRecord>,
    #[serde(skip)]
    holds: Vec<HoldRecord>,
    /// -1 空, 0 空仓, 1 多
    #[serde(skip)]
    pos: Pos,
    #[serde(skip)]
    last_event: Option<LastEvent>, // 基于最近一次 LO 或 SO（与 Python 对齐，单一 last_event）
    #[serde(skip)]
    event_matcher: Option<PositionEventMatcher>,
    #[serde(skip)]
    event_match_values: Vec<Option<EncodedSignalValue>>,
    #[serde(skip)]
    event_match_cache: Vec<Option<CachedEncodedSignalValue>>,
}

pub fn load_position(path: &Path) -> anyhow::Result<Position> {
    // 读取文件内容
    let content = fs::read_to_string(path).with_context(|| format!("读取文件失败: {path:?}"))?;
    // 反序列化 JSON
    let mut position: Position =
        serde_json::from_str(&content).with_context(|| format!("解析 JSON 失败: {path:?}"))?;
    position.init_runtime_fields();
    Ok(position)
}

impl Position {
    fn init_runtime_fields(&mut self) {
        self.normalize_event_hash_names();
        self.event_matcher = None;
        self.event_match_values.clear();
        self.event_match_cache.clear();
    }

    /// 规范化运行时字段，确保事件名称、匹配缓存与 Python 基线一致。
    pub fn normalize_runtime_fields(&mut self) {
        self.init_runtime_fields();
    }

    /// 获取当前仓位状态
    pub fn get_pos(&self) -> Pos {
        self.pos
    }

    /// 获取仓位是否发生变化
    pub fn get_pos_changed(&self) -> bool {
        self.pos_changed
    }

    fn normalize_event_hash_names(&mut self) {
        for event in self.opens.iter_mut().chain(self.exits.iter_mut()) {
            event.refresh_hash_name();
        }
    }

    fn ensure_event_matcher(&mut self) {
        if self.event_matcher.is_none() {
            let matcher = PositionEventMatcher::compile_from_position(self);
            self.event_match_values = vec![None; matcher.keys.len()];
            self.event_match_cache = vec![None; matcher.keys.len()];
            self.event_matcher = Some(matcher);
        }
    }

    fn event_tag_from_desc(desc: &str) -> &'static str {
        if desc.starts_with("开多#") || desc.starts_with("LO#") {
            "LO"
        } else if desc.starts_with("开空#") || desc.starts_with("SO#") {
            "SO"
        } else if desc.starts_with("平多#") || desc.starts_with("LE#") {
            "LE"
        } else if desc.starts_with("平空#") || desc.starts_with("SE#") {
            "SE"
        } else {
            "is_match"
        }
    }

    fn format_event_desc_for_python(desc: &str) -> String {
        if desc.contains('@') {
            desc.to_string()
        } else {
            format!("{desc}@{}", Self::event_tag_from_desc(desc))
        }
    }

    pub fn save(&self, path: &Path) -> anyhow::Result<()> {
        // 将 Position 序列化为 JSON 字符串
        let content = serde_json::to_string_pretty(self)
            .with_context(|| format!("序列化 Position 失败: {path:?}"))?;

        // 将 JSON 写入文件
        fs::write(path, content).with_context(|| format!("写入文件失败: {path:?}"))?;

        Ok(())
    }

    /// 仅用于平仓优化
    pub fn with_event_hash_name(mut self, mode: &str, event_hash: &str) -> Self {
        // 更新 name
        if let Some(pos) = self.name.find('#') {
            // 已有 # -> 替换
            self.name.truncate(pos);
        }
        self.name.push('#');
        self.name.push_str(mode);
        self.name.push_str(event_hash);
        self
    }

    /// 仅用于开仓优化
    pub fn compute_md5_name(mut self) -> Self {
        let mut context = md5::Context::new();
        context.consume(format!("{:?}", self.opens));
        context.consume(format!("{:?}", self.exits));
        context.consume(format!("{:?}", self.interval));
        context.consume(format!("{:?}", self.timeout));
        context.consume(format!("{:?}", self.stop_loss));
        context.consume(format!("{:?}", self.t0));
        context.consume(format!("{:?}", self.symbol));
        // context.consume(format!("{:?}", self.name));

        let digest = context.finalize();
        let digest = hex::encode(*digest)[..8].to_uppercase();

        // 更新 name
        if let Some(pos) = self.name.find('#') {
            // 已有 # -> 替换
            self.name.truncate(pos);
        }
        self.name.push('#');
        self.name.push_str(&digest);
        self
    }

    /// 返回一个迭代器，可以依次遍历 opens 和 exits
    pub fn all_events(&self) -> impl Iterator<Item = &Event> {
        self.opens.iter().chain(self.exits.iter())
    }

    /// 创建一个操作记录
    fn create_operate_record(
        &mut self,
        dt: DateTime<FixedOffset>,
        bar_id: i32,
        price: f64,
        op: Operate,
        op_desc: Option<String>,
    ) -> OperateRecord {
        self.pos_changed = true;
        OperateRecord {
            symbol: self.symbol.to_string(),
            dt,
            bar_id,
            price,
            op,
            op_desc,
            pos: self.pos,
        }
    }

    /// 判断是否"非同日"（用于 T0 检测）
    fn is_different_day(dt: DateTime<FixedOffset>, other: Option<DateTime<FixedOffset>>) -> bool {
        match other {
            Some(o) => dt.date_naive() != o.date_naive(),
            None => true,
        }
    }

    /// 更新持仓状态（对齐 Python czsc/py/objects.py Position.update）
    pub fn update(&mut self, last_bar: LiteBar, last_signals: Rc<RefCell<HashSet<Signal>>>) {
        let _ = self.update_profiled(last_bar, last_signals);
    }

    pub fn update_profiled(
        &mut self,
        last_bar: LiteBar,
        last_signals: Rc<RefCell<HashSet<Signal>>>,
    ) -> PositionUpdateProfile {
        self.update_profiled_with_signal_map(last_bar, Some(last_signals), None)
    }

    pub fn update_profiled_with_signal_map(
        &mut self,
        last_bar: LiteBar,
        last_signals: Option<Rc<RefCell<HashSet<Signal>>>>,
        signal_map: Option<&HashMap<String, String>>,
    ) -> PositionUpdateProfile {
        if let Some(ref temp_state) = self.temp_state {
            if temp_state.end_dt >= last_bar.dt {
                warn!(
                    "请检查信号传入：最新信号时间: {} 在上次信号时间 {} 之前",
                    last_bar.dt, temp_state.end_dt
                );
                return PositionUpdateProfile::default();
            }
        } else {
            // 初始化
            self.temp_state = Some(TempState {
                end_dt: last_bar.dt,
                last_lo_dt: None,
                last_so_dt: None,
            });
        }
        let dt = last_bar.dt.fixed_offset();
        let price = last_bar.price;
        let bar_id = last_bar.id;

        self.pos_changed = false;
        let mut op = Operate::HO;
        let mut op_desc: Option<String> = None;

        let t_event = Instant::now();
        let owned_signal_map;
        let signal_map = if let Some(m) = signal_map {
            m
        } else if let Some(last_signals) = last_signals {
            owned_signal_map = {
                let signals = last_signals.borrow();
                let mut m = HashMap::with_capacity(signals.len());
                for s in signals.iter() {
                    m.insert(s.key(), s.value());
                }
                m
            };
            &owned_signal_map
        } else {
            return PositionUpdateProfile::default();
        };
        // 事件匹配: 固定顺序 opens + exits（与 Python self.events = self.opens + self.exits 对齐）
        self.ensure_event_matcher();
        if let Some(matcher) = self.event_matcher.as_ref()
            && let Some(event_idx) = matcher.find_first_match(
                signal_map,
                &mut self.event_match_values,
                &mut self.event_match_cache,
            )
        {
            let e = if event_idx < self.opens.len() {
                &self.opens[event_idx]
            } else {
                &self.exits[event_idx - self.opens.len()]
            };
            op = e.operate;
            op_desc = Some(e.name.to_string());
        }
        let event_match_ns = t_event.elapsed().as_nanos();

        let t_fsm = Instant::now();
        // 更新 temp_state.end_dt 为当前信号时间
        if let Some(ref mut ts) = self.temp_state {
            ts.end_dt = dt;
        }

        // Python: 当有新的开仓 event 发生，更新 last_event
        if op == Operate::LO || op == Operate::SO {
            self.last_event = Some(LastEvent {
                dt,
                bar_id,
                price,
                op,
                op_desc: op_desc.clone(),
            });
        }

        // ---------- 开仓逻辑 ----------
        // Python L996-1009: if op == Operate.LO
        if op == Operate::LO {
            let allow_open_long = match self.temp_state.as_ref().and_then(|t| t.last_lo_dt) {
                None => true,
                Some(prev_dt) => {
                    let interval_secs = (dt - prev_dt).num_seconds();
                    interval_secs > self.interval
                }
            };

            if self.pos != Pos::Long && allow_open_long {
                // 直接开多
                self.pos = Pos::Long;
                if let Some(ref mut ts) = self.temp_state {
                    ts.last_lo_dt = Some(dt);
                }
                let rec =
                    self.create_operate_record(dt, bar_id, price, Operate::LO, op_desc.clone());
                self.operates.push(rec);
            } else {
                // interval 限制导致不能再次开多；如果当前是空头，则仅平空
                let can_close_short = self.pos == Pos::Short
                    && (self.t0
                        || Self::is_different_day(
                            dt,
                            self.temp_state.as_ref().and_then(|t| t.last_so_dt),
                        ));
                if can_close_short {
                    self.pos = Pos::Flat;
                    let rec =
                        self.create_operate_record(dt, bar_id, price, Operate::SE, op_desc.clone());
                    self.operates.push(rec);
                }
            }
        }

        // Python L1011-1024: if op == Operate.SO
        if op == Operate::SO {
            let allow_open_short = match self.temp_state.as_ref().and_then(|t| t.last_so_dt) {
                None => true,
                Some(prev_dt) => (dt - prev_dt).num_seconds() > self.interval,
            };

            if self.pos != Pos::Short && allow_open_short {
                // 直接开空
                self.pos = Pos::Short;
                if let Some(ref mut ts) = self.temp_state {
                    ts.last_so_dt = Some(dt);
                }
                let rec =
                    self.create_operate_record(dt, bar_id, price, Operate::SO, op_desc.clone());
                self.operates.push(rec);
            } else {
                // interval 限制导致不能再次开空；如果当前是多头，则仅平多
                let can_close_long = self.pos == Pos::Long
                    && (self.t0
                        || Self::is_different_day(
                            dt,
                            self.temp_state.as_ref().and_then(|t| t.last_lo_dt),
                        ));
                if can_close_long {
                    self.pos = Pos::Flat;
                    let rec =
                        self.create_operate_record(dt, bar_id, price, Operate::LE, op_desc.clone());
                    self.operates.push(rec);
                }
            }
        }
        let fsm_ns = t_fsm.elapsed().as_nanos();

        let t_risk = Instant::now();
        // ---------- 多头出场判断 ----------
        // Rust 侧保持“单 bar 只落一条有效平仓记录”：
        // 事件平仓优先，其次止损，最后超时。
        if self.pos == Pos::Long {
            let allowed_by_t0 = if let Some(ref ts) = self.temp_state {
                self.t0 || Self::is_different_day(dt, ts.last_lo_dt)
            } else {
                true
            };

            // 提取 last_event 的值避免借用冲突
            let last_ev_snapshot = self.last_event.as_ref().map(|e| (e.price, e.bar_id));

            if allowed_by_t0 && let Some((ev_price, ev_bar_id)) = last_ev_snapshot {
                let exit_desc = if op == Operate::LE {
                    Some(op_desc.clone())
                } else if price / ev_price - 1.0 < -self.stop_loss / 10000.0 {
                    Some(Some(format!("平多@{}BP止损", self.stop_loss)))
                } else if bar_id - ev_bar_id > self.timeout {
                    Some(Some(format!("平多@{}K超时", self.timeout)))
                } else {
                    None
                };

                if let Some(exit_desc) = exit_desc {
                    self.pos = Pos::Flat;
                    let rec = self.create_operate_record(dt, bar_id, price, Operate::LE, exit_desc);
                    self.operates.push(rec);
                }
            }
        }

        // ---------- 空头出场判断 ----------
        // Rust 侧保持“单 bar 只落一条有效平仓记录”：
        // 事件平仓优先，其次止损，最后超时。
        if self.pos == Pos::Short {
            let allowed_by_t0 = if let Some(ref ts) = self.temp_state {
                self.t0 || Self::is_different_day(dt, ts.last_so_dt)
            } else {
                true
            };

            let last_ev_snapshot = self.last_event.as_ref().map(|e| (e.price, e.bar_id));

            if allowed_by_t0 && let Some((ev_price, ev_bar_id)) = last_ev_snapshot {
                let exit_desc = if op == Operate::SE {
                    Some(op_desc.clone())
                } else if 1.0 - price / ev_price < -self.stop_loss / 10000.0 {
                    Some(Some(format!("平空@{}BP止损", self.stop_loss)))
                } else if bar_id - ev_bar_id > self.timeout {
                    Some(Some(format!("平空@{}K超时", self.timeout)))
                } else {
                    None
                };

                if let Some(exit_desc) = exit_desc {
                    self.pos = Pos::Flat;
                    let rec = self.create_operate_record(dt, bar_id, price, Operate::SE, exit_desc);
                    self.operates.push(rec);
                }
            }
        }
        let risk_ns = t_risk.elapsed().as_nanos();

        let t_holds = Instant::now();
        // Python L1072: self.holds.append({"dt": self.end_dt, "pos": self.pos, "price": price})
        if let Some(last_hold) = self.holds.last_mut()
            && last_hold.price > 0.0
        {
            let n1b_value = (price / last_hold.price - 1.0) * 10000.0;
            last_hold.n1b = Some(n1b_value);
        }

        self.holds.push(HoldRecord {
            dt,
            pos: self.pos,
            price,
            n1b: None,
        });
        let holds_ns = t_holds.elapsed().as_nanos();

        PositionUpdateProfile {
            event_match_ns,
            fsm_ns,
            risk_ns,
            holds_ns,
        }
    }

    pub fn pairs(&self) -> anyhow::Result<DataFrame> {
        let mut trade_pairs = TradePairsColumns::default();
        for (op1, op2) in self.operates.iter().zip(self.operates.iter().skip(1)) {
            if op1.op != Operate::LO && op1.op != Operate::SO {
                continue;
            }
            // 盈亏比例计算:
            // 做多: 平仓价/开仓价 - 1
            // 做空 1 - 平仓价/开仓价
            let yield_profit_ratio = if op1.price == 0.0 {
                None
            } else if op1.op == Operate::LO {
                Some(op2.price / op1.price - 1.0)
            } else {
                Some(1.0 - op2.price / op1.price)
            };

            // 按照Python版本添加策略标记字段
            trade_pairs.symbol.push(&self.symbol);
            trade_pairs.strategy_mark.push(&self.name);
            trade_pairs.direction.push(if op1.op == Operate::LO {
                "多头"
            } else {
                "空头"
            });
            trade_pairs.open_dt.push(op1.dt.naive_local());
            trade_pairs.close_dt.push(op2.dt.naive_local());
            trade_pairs.open_price.push(op1.price);
            trade_pairs.close_price.push(op2.price);
            trade_pairs.holding_bar.push(op2.bar_id - op1.bar_id);
            trade_pairs
                .event_sequence
                .push(match (&op1.op_desc, &op2.op_desc) {
                    (None, None) => OP_DESC_NONE.to_string(),
                    (None, Some(desc)) => Self::format_event_desc_for_python(desc),
                    (Some(desc), None) => Self::format_event_desc_for_python(desc),
                    (Some(desc1), Some(desc2)) => format!(
                        "{} -> {}",
                        Self::format_event_desc_for_python(desc1),
                        Self::format_event_desc_for_python(desc2)
                    ),
                });

            // 按照Python版本计算持仓天数：使用浮点除法以支持小于1天的持仓
            // Python: (op2["dt"] - op1["dt"]).total_seconds() / (24 * 3600)
            let holding_seconds = (op2.dt - op1.dt).num_seconds() as f64;
            let holding_days = holding_seconds / 86400.0; // 86400 = 24 * 3600
            trade_pairs.holding_day.push(holding_days);

            // 转换为 BP 单位并按Python版本舍入到小数点后2位
            let yield_profit_ratio_bp =
                yield_profit_ratio.map(|r| (r * 10000.0 * 100.0).round() / 100.0);
            trade_pairs.yield_profit_ratio.push(yield_profit_ratio_bp);
        }

        let df = df![
            "标的代码" => trade_pairs.symbol,
            "策略标记" => trade_pairs.strategy_mark,
            "交易方向" => trade_pairs.direction,
            "开仓时间" => trade_pairs.open_dt,
            "平仓时间" => trade_pairs.close_dt,
            "开仓价格" => trade_pairs.open_price,
            "平仓价格" => trade_pairs.close_price,
            "持仓K线数" => trade_pairs.holding_bar,
            "事件序列" => trade_pairs.event_sequence,
            "持仓天数" => trade_pairs.holding_day,
            "盈亏比例" => trade_pairs.yield_profit_ratio,
        ]
        .context("创建 Polars df 失败")?;

        Ok(df)
    }

    pub fn holds(&self) -> anyhow::Result<DataFrame> {
        let holds = self.holds.clone();
        let holds = HoldColumns::from_records(holds);

        let df = holds
            .into_df()?
            .lazy()
            .with_columns([
                // symbol 列
                lit(self.symbol.to_string()).alias("symbol"),
            ])
            .collect()
            .context("新增列 symbol 失败")?;

        Ok(df)
    }
}

const OP_DESC_NONE: &str = "无";

/// Python可见的Pos枚举包装器
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, name = "Pos", module = "czsc._native"))]
#[derive(Debug, Clone)]
pub struct PyPos {
    pub inner: Pos,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl PyPos {
    #[classmethod]
    fn short(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Pos::Short }
    }

    #[classmethod]
    fn flat(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Pos::Flat }
    }

    #[classmethod]
    fn long(_cls: &Bound<'_, pyo3::types::PyType>) -> Self {
        Self { inner: Pos::Long }
    }

    fn __str__(&self) -> String {
        self.inner.to_string()
    }

    fn __repr__(&self) -> String {
        format!("PyPos::{:?}", self.inner)
    }

    fn __eq__(&self, other: &Self) -> bool {
        self.inner == other.inner
    }

    /// 加法运算，用于numpy.mean等数学操作
    fn __add__(&self, other: &Self) -> f64 {
        self.inner.to_f64() + other.inner.to_f64()
    }

    /// 右加法运算
    fn __radd__(&self, other: f64) -> f64 {
        other + self.inner.to_f64()
    }

    /// 转换为浮点数，用于数学运算
    fn __float__(&self) -> f64 {
        self.inner.to_f64()
    }

    /// 整数转换
    fn __int__(&self) -> i32 {
        self.inner.to_f64() as i32
    }

    /// 比较运算符 - 小于
    fn __lt__(&self, other: &Self) -> bool {
        self.inner.to_f64() < other.inner.to_f64()
    }

    /// 比较运算符 - 小于等于
    fn __le__(&self, other: &Self) -> bool {
        self.inner.to_f64() <= other.inner.to_f64()
    }

    /// 比较运算符 - 大于
    fn __gt__(&self, other: &Self) -> bool {
        self.inner.to_f64() > other.inner.to_f64()
    }

    /// 比较运算符 - 大于等于
    fn __ge__(&self, other: &Self) -> bool {
        self.inner.to_f64() >= other.inner.to_f64()
    }
}

/// Python可见的LiteBar包装器
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, name = "LiteBar", module = "czsc._native"))]
#[derive(Debug, Clone)]
pub struct PyLiteBar {
    pub inner: LiteBar,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl PyLiteBar {
    #[new]
    fn new_py(id: i32, dt: f64, price: f64) -> PyResult<Self> {
        use chrono::{DateTime, FixedOffset, TimeZone, Utc};

        let dt_utc = DateTime::from_timestamp(dt as i64, 0)
            .ok_or_else(|| PyValueError::new_err("无效的时间戳"))?;
        let dt = dt_utc.with_timezone(&FixedOffset::east_opt(0).unwrap());

        Ok(Self {
            inner: LiteBar { id, dt, price },
        })
    }

    #[getter]
    fn id(&self) -> i32 {
        self.inner.id
    }

    #[getter]
    fn dt(&self) -> f64 {
        self.inner.dt.timestamp() as f64
    }

    #[getter]
    fn price(&self) -> f64 {
        self.inner.price
    }

    fn __repr__(&self) -> String {
        format!(
            "PyLiteBar(id={}, dt={}, price={})",
            self.inner.id,
            self.inner.dt.timestamp(),
            self.inner.price
        )
    }
}

/// Python可见的Position包装器
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(
    feature = "python",
    pyclass(from_py_object, name = "Position", module = "czsc._native")
)]
#[derive(Debug, Clone)]
pub struct PyPosition {
    pub inner: Position,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl PyPosition {
    #[new]
    #[pyo3(signature = (symbol, opens, exits = vec![], interval = 0, timeout = 1000, stop_loss = 1000.0, t0 = false, name = None))]
    #[allow(clippy::too_many_arguments)]
    fn new_py(
        symbol: String,
        opens: Vec<PyEvent>,
        exits: Vec<PyEvent>,
        interval: i64,
        timeout: i32,
        stop_loss: f64,
        t0: bool,
        name: Option<String>,
    ) -> Self {
        let opens: Vec<Event> = opens.into_iter().map(|e| e.inner).collect();
        let exits: Vec<Event> = exits.into_iter().map(|e| e.inner).collect();

        let name = name.unwrap_or_else(|| {
            if !opens.is_empty() {
                opens[0].name.clone()
            } else {
                "DefaultPosition".to_string()
            }
        });

        let inner = Position {
            opens,
            exits,
            interval,
            timeout,
            stop_loss,
            t0,
            name,
            symbol,
            temp_state: None,
            pos_changed: false,
            operates: Vec::new(),
            holds: Vec::new(),
            pos: Pos::Flat,
            last_event: None,
            event_matcher: None,
            event_match_values: Vec::new(),
            event_match_cache: Vec::new(),
        };
        let mut inner = inner;
        inner.init_runtime_fields();

        Self { inner }
    }

    #[classmethod]
    fn load_from_file(_cls: &Bound<'_, pyo3::types::PyType>, path: String) -> PyResult<Self> {
        let position = load_position(Path::new(&path))
            .map_err(|e| PyValueError::new_err(format!("加载Position失败: {e}")))?;
        Ok(Self { inner: position })
    }

    #[classmethod]
    fn from_json(_cls: &Bound<'_, pyo3::types::PyType>, json_str: String) -> PyResult<Self> {
        let mut inner: Position = serde_json::from_str(&json_str)
            .map_err(|e| PyValueError::new_err(format!("JSON解析失败: {e}")))?;
        inner.init_runtime_fields();
        Ok(Self { inner })
    }

    #[getter]
    fn opens(&self) -> Vec<PyEvent> {
        self.inner
            .opens
            .iter()
            .map(|e| PyEvent { inner: e.clone() })
            .collect()
    }

    #[getter]
    fn exits(&self) -> Vec<PyEvent> {
        self.inner
            .exits
            .iter()
            .map(|e| PyEvent { inner: e.clone() })
            .collect()
    }

    #[getter]
    fn interval(&self) -> i64 {
        self.inner.interval
    }

    #[getter]
    fn timeout(&self) -> i32 {
        self.inner.timeout
    }

    #[getter]
    fn stop_loss(&self) -> f64 {
        self.inner.stop_loss
    }

    #[getter]
    fn t0(&self) -> bool {
        self.inner.t0
    }

    #[getter]
    fn name(&self) -> String {
        self.inner.name.clone()
    }

    #[getter]
    fn symbol(&self) -> String {
        self.inner.symbol.clone()
    }

    #[getter]
    fn pos(&self) -> f64 {
        self.inner.pos.to_f64()
    }

    #[getter]
    fn pos_changed(&self) -> bool {
        self.inner.pos_changed
    }

    /// 获取最新信号时间
    #[getter]
    fn end_dt(&self) -> Option<f64> {
        self.inner
            .temp_state
            .as_ref()
            .map(|ts| ts.end_dt.timestamp() as f64)
    }

    /// 获取操作记录列表
    #[getter]
    fn operates(&self, py: Python) -> PyResult<Vec<Py<PyAny>>> {
        let mut result = Vec::new();

        for op_record in &self.inner.operates {
            let dict = pyo3::types::PyDict::new(py);

            // 转换时间戳为 pandas 兼容格式
            let timestamp = op_record.dt.timestamp() as f64;
            dict.set_item("dt", timestamp)?;
            dict.set_item("symbol", &op_record.symbol)?;
            dict.set_item("bar_id", op_record.bar_id)?;
            dict.set_item("price", op_record.price)?;
            dict.set_item("op", op_record.op.to_string())?;
            dict.set_item("op_desc", &op_record.op_desc)?;
            dict.set_item("pos", op_record.pos.to_string())?;

            result.push(dict.into());
        }

        Ok(result)
    }

    /// 保存到文件
    fn save(&self, path: String) -> PyResult<()> {
        self.inner
            .save(Path::new(&path))
            .map_err(|e| PyValueError::new_err(format!("保存Position失败: {e}")))
    }

    /// 转换为JSON字符串
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(&self.inner)
            .map_err(|e| PyValueError::new_err(format!("JSON序列化失败: {e}")))
    }

    /// 获取所有相关事件
    fn all_events(&self) -> Vec<PyEvent> {
        self.inner
            .all_events()
            .map(|e| PyEvent { inner: e.clone() })
            .collect()
    }

    /// 更新仓位状态（兼容单参数调用）
    #[pyo3(signature = (arg1, arg2 = None))]
    fn update(&mut self, arg1: Py<PyAny>, arg2: Option<Py<PyAny>>) -> PyResult<()> {
        use pyo3::types::{PyDict, PyMapping};
        use std::collections::HashSet;

        Python::attach(|py| {
            if let Some(arg2_val) = arg2 {
                // 两个参数的情况：update(last_bar, last_signals)
                let last_bar: PyLiteBar = arg1.extract(py)?;
                let last_signals: Vec<PySignal> = arg2_val.extract(py)?;

                let signals: HashSet<Signal> = last_signals.into_iter().map(|s| s.inner).collect();
                let signals_ref = Rc::new(RefCell::new(signals));

                self.inner.update(last_bar.inner, signals_ref);
            } else {
                // 一个参数的情况：update(signals_dict)
                // Python版本期望字典格式: {'symbol': 'BTC', 'dt': Timestamp(...), 'id': 1, 'close': 100.0, '信号key': '信号value', ...}

                if let Ok(signals_dict) = arg1.cast_bound::<PyDict>(py) {
                    // 1. 提取必需字段：dt, id, close
                    let dt_obj = signals_dict.get_item("dt")?.ok_or_else(|| {
                        PyValueError::new_err("Missing 'dt' field in signals dict")
                    })?;
                    let id_obj = signals_dict.get_item("id")?.ok_or_else(|| {
                        PyValueError::new_err("Missing 'id' field in signals dict")
                    })?;
                    let close_obj = signals_dict.get_item("close")?.ok_or_else(|| {
                        PyValueError::new_err("Missing 'close' field in signals dict")
                    })?;

                    // 2. 转换dt - 支持多种格式
                    use chrono::{DateTime, FixedOffset, Utc};
                    let dt: DateTime<FixedOffset> = if let Ok(timestamp) = dt_obj.extract::<f64>() {
                        // Unix时间戳（秒）
                        DateTime::from_timestamp(timestamp as i64, 0)
                            .ok_or_else(|| PyValueError::new_err("Invalid timestamp"))?
                            .with_timezone(&FixedOffset::east_opt(0).unwrap())
                    } else {
                        // 尝试调用timestamp()方法（pandas.Timestamp对象）
                        if let Ok(timestamp_method) = dt_obj.getattr("timestamp") {
                            let timestamp: f64 = timestamp_method.call0()?.extract()?;
                            DateTime::from_timestamp(timestamp as i64, 0)
                                .ok_or_else(|| {
                                    PyValueError::new_err("Invalid timestamp from pandas")
                                })?
                                .with_timezone(&FixedOffset::east_opt(0).unwrap())
                        } else {
                            return Err(PyValueError::new_err("Cannot convert 'dt' to timestamp"));
                        }
                    };

                    // 3. 提取id和close
                    let bar_id: i32 = id_obj.extract()?;
                    let price: f64 = close_obj.extract()?;

                    // 4. 构造LiteBar
                    let lite_bar = LiteBar {
                        id: bar_id,
                        dt,
                        price,
                    };

                    // 5. 从字典中提取信号，构造Signal集合
                    let mut signal_set = HashSet::new();

                    for (key, value) in signals_dict.iter() {
                        let key_str = if let Ok(s) = key.extract::<String>() {
                            s
                        } else {
                            key.str()?.extract::<String>()?
                        };

                        // 跳过非信号字段
                        if key_str == "symbol"
                            || key_str == "dt"
                            || key_str == "id"
                            || key_str == "close"
                            || key_str == "open"
                            || key_str == "high"
                            || key_str == "low"
                            || key_str == "vol"
                            || key_str == "amount"
                            || key_str == "freq"
                        {
                            continue;
                        }

                        let value_str = if let Ok(s) = value.extract::<String>() {
                            s
                        } else {
                            value.str()?.extract::<String>()?
                        };

                        // 构造完整信号字符串
                        // 支持两种格式：
                        // 1. 简单值: value='看多' -> key_看多_任意_任意_0
                        // 2. 完整4段值: value='看多_任意_任意_0' -> key_看多_任意_任意_0
                        let signal_str = if value_str.split('_').count() == 4 {
                            // 已经是完整的4段值，直接拼接
                            format!("{key_str}_{value_str}")
                        } else {
                            // 简单值，添加默认后缀
                            format!("{key_str}_{value_str}_任意_任意_0")
                        };

                        // 尝试创建Signal并添加到集合
                        if let Ok(signal) = Signal::from_str(&signal_str) {
                            signal_set.insert(signal);
                        }
                    }

                    let signals_ref = Rc::new(RefCell::new(signal_set));
                    self.inner.update(lite_bar, signals_ref);
                } else if let Ok(signals_vec) = arg1.extract::<Vec<PySignal>>(py) {
                    // 如果是PySignal列表（向后兼容）
                    let signal_set: HashSet<Signal> =
                        signals_vec.into_iter().map(|s| s.inner).collect();
                    let signals_ref = Rc::new(RefCell::new(signal_set));

                    // 创建虚拟LiteBar（仅用于兼容旧接口）
                    use chrono::{DateTime, FixedOffset, Utc};
                    let dummy_bar = LiteBar {
                        id: 0,
                        dt: Utc::now().with_timezone(&FixedOffset::east_opt(0).unwrap()),
                        price: 0.0,
                    };
                    self.inner.update(dummy_bar, signals_ref);
                } else {
                    return Err(PyValueError::new_err(
                        "Expected dict with 'dt', 'id', 'close' fields, or Vec<Signal>",
                    ));
                }
            }
            Ok(())
        })
    }

    /// 获取交易对数据（返回记录列表，兼容pandas.DataFrame构造）
    #[getter]
    fn pairs(&self) -> PyResult<Py<pyo3::types::PyList>> {
        let df = self
            .inner
            .pairs()
            .map_err(|e| PyValueError::new_err(format!("生成交易对数据失败: {e}")))?;

        // 将DataFrame转换为记录列表
        Python::attach(|py| {
            let list = pyo3::types::PyList::empty(py);

            let height = df.height();
            for i in 0..height {
                let record = pyo3::types::PyDict::new(py);

                // 获取列数据（使用中文列名）

                if let Ok(symbol_col) = df.column("标的代码")
                    && let Ok(value) = symbol_col.get(i)
                {
                    record.set_item("标的代码", value.to_string())?;
                }

                if let Ok(direction_col) = df.column("交易方向")
                    && let Ok(value) = direction_col.get(i)
                {
                    record.set_item("交易方向", value.to_string())?;
                }

                if let Ok(open_dt_col) = df.column("开仓时间")
                    && let Ok(value) = open_dt_col.get(i)
                {
                    record.set_item("开仓时间", value.to_string())?;
                }

                if let Ok(close_dt_col) = df.column("平仓时间")
                    && let Ok(value) = close_dt_col.get(i)
                {
                    record.set_item("平仓时间", value.to_string())?;
                }

                if let Ok(open_price_col) = df.column("开仓价格")
                    && let Ok(value) = open_price_col.get(i)
                {
                    record.set_item("开仓价格", value.try_extract::<f64>().unwrap_or(0.0))?;
                }

                if let Ok(close_price_col) = df.column("平仓价格")
                    && let Ok(value) = close_price_col.get(i)
                {
                    record.set_item("平仓价格", value.try_extract::<f64>().unwrap_or(0.0))?;
                }

                if let Ok(holding_bar_col) = df.column("持仓K线数")
                    && let Ok(value) = holding_bar_col.get(i)
                {
                    record.set_item("持仓K线数", value.try_extract::<i32>().unwrap_or(0))?;
                }

                if let Ok(event_sequence_col) = df.column("事件序列")
                    && let Ok(value) = event_sequence_col.get(i)
                {
                    record.set_item("事件序列", value.to_string())?;
                }

                if let Ok(holding_day_col) = df.column("持仓天数")
                    && let Ok(value) = holding_day_col.get(i)
                {
                    record.set_item("持仓天数", value.try_extract::<f64>().unwrap_or(0.0))?;
                }

                if let Ok(yield_profit_ratio_col) = df.column("盈亏比例")
                    && let Ok(value) = yield_profit_ratio_col.get(i)
                {
                    match value {
                        polars::prelude::AnyValue::Null => {
                            record.set_item("盈亏比例", py.None())?;
                        }
                        _ => {
                            if let Ok(ratio) = value.try_extract::<f64>() {
                                record.set_item("盈亏比例", ratio)?;
                            } else {
                                record.set_item("盈亏比例", py.None())?;
                            }
                        }
                    }
                }

                list.append(record)?;
            }

            Ok(list.into())
        })
    }

    /// 获取持仓历史数据（返回记录列表，兼容历史版本）
    #[getter]
    fn holds(&self) -> PyResult<Py<pyo3::types::PyList>> {
        Python::attach(|py| {
            let list = pyo3::types::PyList::empty(py);

            for hold_record in &self.inner.holds {
                let record = pyo3::types::PyDict::new(py);

                // 转换时间戳为 Python datetime 兼容格式
                let timestamp = hold_record.dt.timestamp() as f64;
                record.set_item("dt", timestamp)?;
                record.set_item("pos", hold_record.pos.to_f64() as i32)?;
                record.set_item("price", hold_record.price)?;

                // 添加n1b字段
                if let Some(n1b_value) = hold_record.n1b {
                    record.set_item("n1b", n1b_value)?;
                } else {
                    record.set_item("n1b", py.None())?;
                }

                list.append(record)?;
            }

            Ok(list.into())
        })
    }

    #[getter]
    fn unique_signals(&self) -> Vec<String> {
        let mut signals = HashSet::new();

        // 收集所有opens事件的信号字符串
        for event in &self.inner.opens {
            for signal in &event.signals_all {
                signals.insert(signal.to_string());
            }
            for signal in &event.signals_any {
                signals.insert(signal.to_string());
            }
            for signal in &event.signals_not {
                signals.insert(signal.to_string());
            }
        }

        // 收集所有exits事件的信号字符串
        for event in &self.inner.exits {
            for signal in &event.signals_all {
                signals.insert(signal.to_string());
            }
            for signal in &event.signals_any {
                signals.insert(signal.to_string());
            }
            for signal in &event.signals_not {
                signals.insert(signal.to_string());
            }
        }

        signals.into_iter().collect()
    }

    #[getter]
    fn events(&self) -> Vec<PyEvent> {
        self.all_events()
    }

    /// 支持 pickle 序列化 - 使用 __reduce__ 方法
    fn __reduce__(&self, py: Python) -> PyResult<Py<PyAny>> {
        use pyo3::IntoPyObject;

        // 构造函数参数
        let opens: Vec<PyEvent> = self
            .inner
            .opens
            .iter()
            .map(|e| PyEvent { inner: e.clone() })
            .collect();
        let exits: Vec<PyEvent> = self
            .inner
            .exits
            .iter()
            .map(|e| PyEvent { inner: e.clone() })
            .collect();

        let args = (
            self.inner.symbol.clone(),
            opens,
            exits,
            self.inner.interval,
            self.inner.timeout,
            self.inner.stop_loss,
            self.inner.t0,
            Some(self.inner.name.clone()),
        )
            .into_pyobject(py)?;

        // 返回 (constructor, args)
        let constructor = py.get_type::<Self>();
        let result = (constructor, args).into_pyobject(py)?;
        Ok(result.into())
    }

    /// 导出Position数据为Python字典
    #[pyo3(signature = (with_data = true))]
    fn dump(&self, with_data: bool) -> PyResult<Py<PyAny>> {
        Python::attach(|py| {
            let dict = pyo3::types::PyDict::new(py);

            // 基本属性 - 按期望顺序添加
            dict.set_item("symbol", &self.inner.symbol)?;
            dict.set_item("name", &self.inner.name)?;

            // opens和exits事件 - 使用中文 operate，保持key-value字典格式
            let opens_list = pyo3::types::PyList::empty(py);
            for event in &self.inner.opens {
                let event_dict = pyo3::types::PyDict::new(py);
                event_dict.set_item("name", &event.name)?;
                event_dict.set_item("operate", event.operate.to_chinese())?;

                let signals_all_list = pyo3::types::PyList::empty(py);
                for signal in &event.signals_all {
                    let signal_dict = pyo3::types::PyDict::new(py);
                    signal_dict.set_item("key", signal.key())?;
                    signal_dict.set_item("value", signal.value())?;
                    signals_all_list.append(signal_dict)?;
                }
                event_dict.set_item("signals_all", signals_all_list)?;

                let signals_any_list = pyo3::types::PyList::empty(py);
                for signal in &event.signals_any {
                    let signal_dict = pyo3::types::PyDict::new(py);
                    signal_dict.set_item("key", signal.key())?;
                    signal_dict.set_item("value", signal.value())?;
                    signals_any_list.append(signal_dict)?;
                }
                event_dict.set_item("signals_any", signals_any_list)?;

                let signals_not_list = pyo3::types::PyList::empty(py);
                for signal in &event.signals_not {
                    let signal_dict = pyo3::types::PyDict::new(py);
                    signal_dict.set_item("key", signal.key())?;
                    signal_dict.set_item("value", signal.value())?;
                    signals_not_list.append(signal_dict)?;
                }
                event_dict.set_item("signals_not", signals_not_list)?;

                opens_list.append(event_dict)?;
            }
            dict.set_item("opens", opens_list)?;

            let exits_list = pyo3::types::PyList::empty(py);
            for event in &self.inner.exits {
                let event_dict = pyo3::types::PyDict::new(py);
                event_dict.set_item("name", &event.name)?;
                event_dict.set_item("operate", event.operate.to_chinese())?;

                let signals_all_list = pyo3::types::PyList::empty(py);
                for signal in &event.signals_all {
                    let signal_dict = pyo3::types::PyDict::new(py);
                    signal_dict.set_item("key", signal.key())?;
                    signal_dict.set_item("value", signal.value())?;
                    signals_all_list.append(signal_dict)?;
                }
                event_dict.set_item("signals_all", signals_all_list)?;

                let signals_any_list = pyo3::types::PyList::empty(py);
                for signal in &event.signals_any {
                    let signal_dict = pyo3::types::PyDict::new(py);
                    signal_dict.set_item("key", signal.key())?;
                    signal_dict.set_item("value", signal.value())?;
                    signals_any_list.append(signal_dict)?;
                }
                event_dict.set_item("signals_any", signals_any_list)?;

                let signals_not_list = pyo3::types::PyList::empty(py);
                for signal in &event.signals_not {
                    let signal_dict = pyo3::types::PyDict::new(py);
                    signal_dict.set_item("key", signal.key())?;
                    signal_dict.set_item("value", signal.value())?;
                    signals_not_list.append(signal_dict)?;
                }
                event_dict.set_item("signals_not", signals_not_list)?;

                exits_list.append(event_dict)?;
            }
            dict.set_item("exits", exits_list)?;

            // 剩余的基本属性 - 按期望顺序
            dict.set_item("interval", self.inner.interval)?;
            dict.set_item("timeout", self.inner.timeout)?;
            dict.set_item("stop_loss", self.inner.stop_loss)?;
            dict.set_item("T0", self.inner.t0)?;

            // 如果需要包含数据
            if with_data {
                // 获取pairs数据
                if let Ok(pairs_list) = self.pairs() {
                    dict.set_item("pairs", pairs_list)?;
                }

                // 获取holds数据
                if let Ok(holds_list) = self.holds() {
                    dict.set_item("holds", holds_list)?;
                }
            }

            Ok(dict.into())
        })
    }

    /// 从字典数据加载Position
    #[classmethod]
    fn load(_cls: &Bound<'_, pyo3::types::PyType>, data: Py<PyAny>) -> PyResult<Self> {
        Python::attach(|py| {
            // 首先尝试直接转换为字典
            let dict = match data.cast_bound::<pyo3::types::PyDict>(py) {
                Ok(d) => d.clone(),
                Err(_) => {
                    // 如果失败，尝试作为字符串处理
                    if let Ok(s) = data.cast_bound::<pyo3::types::PyString>(py) {
                        let json_str: String = s.extract()?;
                        // 使用Python的json模块解析
                        let json_module = py.import("json")?;
                        let parsed = json_module.call_method1("loads", (json_str,))?;
                        parsed.cast::<pyo3::types::PyDict>()?.clone()
                    } else {
                        return Err(pyo3::exceptions::PyTypeError::new_err(
                            "Expected dict or JSON string",
                        ));
                    }
                }
            };

            // symbol字段可选，如果不存在则使用默认值
            let symbol: String = dict
                .get_item("symbol")?
                .map(|item| item.extract())
                .transpose()?
                .unwrap_or_else(|| "UNKNOWN".to_string());
            let name: String = dict
                .get_item("name")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'name' field"))?
                .extract()?;
            let interval: i64 = dict
                .get_item("interval")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'interval' field"))?
                .extract()?;
            let timeout: i32 = dict
                .get_item("timeout")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'timeout' field"))?
                .extract()?;
            let stop_loss: f64 = dict
                .get_item("stop_loss")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'stop_loss' field"))?
                .extract()?;
            let t0: bool = dict
                .get_item("T0")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'T0' field"))?
                .extract()?;

            // 解析opens事件
            let opens_data = dict
                .get_item("opens")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'opens' field"))?;
            let opens_list = opens_data.cast::<pyo3::types::PyList>()?;
            let mut opens = Vec::new();

            for item in opens_list.iter() {
                let event_dict = item.cast::<pyo3::types::PyDict>()?;
                let event_name: String = event_dict
                    .get_item("name")?
                    .ok_or_else(|| {
                        pyo3::exceptions::PyKeyError::new_err("Missing 'name' in event")
                    })?
                    .extract()?;
                let operate_str: String = event_dict
                    .get_item("operate")?
                    .ok_or_else(|| {
                        pyo3::exceptions::PyKeyError::new_err("Missing 'operate' in event")
                    })?
                    .extract()?;
                let operate = parse_operate(&operate_str)
                    .map_err(|e| PyValueError::new_err(format!("无法解析operate: {e}")))?;

                // 解析 signals_all
                let signals_all_data = event_dict.get_item("signals_all")?.ok_or_else(|| {
                    pyo3::exceptions::PyKeyError::new_err("Missing 'signals_all' in event")
                })?;
                let signals_all_list = signals_all_data.cast::<pyo3::types::PyList>()?;
                let mut signals_all = Vec::new();

                for signal_item in signals_all_list.iter() {
                    let signal_dict = signal_item.cast::<pyo3::types::PyDict>()?;
                    let key: String = signal_dict
                        .get_item("key")?
                        .ok_or_else(|| {
                            pyo3::exceptions::PyKeyError::new_err("Missing 'key' in signal")
                        })?
                        .extract()?;
                    let value: String = signal_dict
                        .get_item("value")?
                        .ok_or_else(|| {
                            pyo3::exceptions::PyKeyError::new_err("Missing 'value' in signal")
                        })?
                        .extract()?;
                    let signal_str = format!("{key}_{value}");
                    if let Ok(signal) = Signal::from_str(&signal_str) {
                        signals_all.push(signal);
                    }
                }

                // 解析 signals_any
                let mut signals_any = Vec::new();
                if let Some(signals_any_data) = event_dict.get_item("signals_any")? {
                    let signals_any_list = signals_any_data.cast::<pyo3::types::PyList>()?;
                    for signal_item in signals_any_list.iter() {
                        let signal_dict = signal_item.cast::<pyo3::types::PyDict>()?;
                        let key: String = signal_dict
                            .get_item("key")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'key' in signal")
                            })?
                            .extract()?;
                        let value: String = signal_dict
                            .get_item("value")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'value' in signal")
                            })?
                            .extract()?;
                        let signal_str = format!("{key}_{value}");
                        if let Ok(signal) = Signal::from_str(&signal_str) {
                            signals_any.push(signal);
                        }
                    }
                }

                // 解析 signals_not
                let mut signals_not = Vec::new();
                if let Some(signals_not_data) = event_dict.get_item("signals_not")? {
                    let signals_not_list = signals_not_data.cast::<pyo3::types::PyList>()?;
                    for signal_item in signals_not_list.iter() {
                        let signal_dict = signal_item.cast::<pyo3::types::PyDict>()?;
                        let key: String = signal_dict
                            .get_item("key")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'key' in signal")
                            })?
                            .extract()?;
                        let value: String = signal_dict
                            .get_item("value")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'value' in signal")
                            })?
                            .extract()?;
                        let signal_str = format!("{key}_{value}");
                        if let Ok(signal) = Signal::from_str(&signal_str) {
                            signals_not.push(signal);
                        }
                    }
                }

                let event = Event {
                    name: event_name,
                    operate,
                    signals_all,
                    signals_any,
                    signals_not,
                    sha256: String::new(),
                };
                opens.push(event);
            }

            let exits_data = dict
                .get_item("exits")?
                .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err("Missing 'exits' field"))?;
            let exits_list = exits_data.cast::<pyo3::types::PyList>()?;
            let mut exits = Vec::new();

            for item in exits_list.iter() {
                let event_dict = item.cast::<pyo3::types::PyDict>()?;
                let event_name: String = event_dict
                    .get_item("name")?
                    .ok_or_else(|| {
                        pyo3::exceptions::PyKeyError::new_err("Missing 'name' in event")
                    })?
                    .extract()?;
                let operate_str: String = event_dict
                    .get_item("operate")?
                    .ok_or_else(|| {
                        pyo3::exceptions::PyKeyError::new_err("Missing 'operate' in event")
                    })?
                    .extract()?;
                let operate = parse_operate(&operate_str)
                    .map_err(|e| PyValueError::new_err(format!("无法解析operate: {e}")))?;

                // 解析 signals_all
                let signals_all_data = event_dict.get_item("signals_all")?.ok_or_else(|| {
                    pyo3::exceptions::PyKeyError::new_err("Missing 'signals_all' in event")
                })?;
                let signals_all_list = signals_all_data.cast::<pyo3::types::PyList>()?;
                let mut signals_all = Vec::new();

                for signal_item in signals_all_list.iter() {
                    let signal_dict = signal_item.cast::<pyo3::types::PyDict>()?;
                    let key: String = signal_dict
                        .get_item("key")?
                        .ok_or_else(|| {
                            pyo3::exceptions::PyKeyError::new_err("Missing 'key' in signal")
                        })?
                        .extract()?;
                    let value: String = signal_dict
                        .get_item("value")?
                        .ok_or_else(|| {
                            pyo3::exceptions::PyKeyError::new_err("Missing 'value' in signal")
                        })?
                        .extract()?;
                    let signal_str = format!("{key}_{value}");
                    if let Ok(signal) = Signal::from_str(&signal_str) {
                        signals_all.push(signal);
                    }
                }

                // 解析 signals_any
                let mut signals_any = Vec::new();
                if let Some(signals_any_data) = event_dict.get_item("signals_any")? {
                    let signals_any_list = signals_any_data.cast::<pyo3::types::PyList>()?;
                    for signal_item in signals_any_list.iter() {
                        let signal_dict = signal_item.cast::<pyo3::types::PyDict>()?;
                        let key: String = signal_dict
                            .get_item("key")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'key' in signal")
                            })?
                            .extract()?;
                        let value: String = signal_dict
                            .get_item("value")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'value' in signal")
                            })?
                            .extract()?;
                        let signal_str = format!("{key}_{value}");
                        if let Ok(signal) = Signal::from_str(&signal_str) {
                            signals_any.push(signal);
                        }
                    }
                }

                // 解析 signals_not
                let mut signals_not = Vec::new();
                if let Some(signals_not_data) = event_dict.get_item("signals_not")? {
                    let signals_not_list = signals_not_data.cast::<pyo3::types::PyList>()?;
                    for signal_item in signals_not_list.iter() {
                        let signal_dict = signal_item.cast::<pyo3::types::PyDict>()?;
                        let key: String = signal_dict
                            .get_item("key")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'key' in signal")
                            })?
                            .extract()?;
                        let value: String = signal_dict
                            .get_item("value")?
                            .ok_or_else(|| {
                                pyo3::exceptions::PyKeyError::new_err("Missing 'value' in signal")
                            })?
                            .extract()?;
                        let signal_str = format!("{key}_{value}");
                        if let Ok(signal) = Signal::from_str(&signal_str) {
                            signals_not.push(signal);
                        }
                    }
                }

                let event = Event {
                    name: event_name,
                    operate,
                    signals_all,
                    signals_any,
                    signals_not,
                    sha256: String::new(),
                };
                exits.push(event);
            }

            let inner = Position {
                opens,
                exits,
                interval,
                timeout,
                stop_loss,
                t0,
                name,
                symbol,
                temp_state: None,
                pos_changed: false,
                operates: Vec::new(),
                holds: Vec::new(),
                pos: Pos::Flat,
                last_event: None,
                event_matcher: None,
                event_match_values: Vec::new(),
                event_match_cache: Vec::new(),
            };
            let mut inner = inner;
            inner.init_runtime_fields();

            Ok(Self { inner })
        })
    }

    fn __repr__(&self) -> String {
        format!(
            "PyPosition(name='{}', symbol='{}', opens={}, exits={}, interval={})",
            self.inner.name,
            self.inner.symbol,
            self.inner.opens.len(),
            self.inner.exits.len(),
            self.inner.interval
        )
    }
}
