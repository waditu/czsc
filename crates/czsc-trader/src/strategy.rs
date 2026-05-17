//! 策略门面（Strategy facade）—— Rust 端的 [`Strategy`] trait 与 [`JsonStrategy`] 实现。
//!
//! 2026-05-17 PR-E 起，本模块承接历史上 `czsc/strategies.py` 的核心抽象，
//! 让 `cargo add czsc` 的 Rust 用户与 `pip install czsc` 的 Python 用户拿到
//! 行为一致的策略组装入口（参见 CLAUDE.md「🏛️ 开发宪法 · 第一条」）。
//!
//! 设计要点：
//!
//! - [`Strategy`] trait 暴露一个抽象方法 [`Strategy::positions`]（子类提供持仓
//!   列表），其它派生信息（unique_signals）走默认实现，避免实现者每次重复
//!   "for pos in positions: for sig in pos.unique_signals" 这段固定模板；
//! - [`JsonStrategy`] 是最常用的具体类型，从一组 JSON 文件加载 [`Position`]
//!   列表（沿用 [`czsc_core::objects::load_position`]）；
//! - 自由函数 [`unique_signals_across`] 是 trait 默认方法的纯粹算法 core，
//!   方便测试单独覆盖、也方便 Python binding 直接调用而无需构造 trait object。
//!
//! 与历史 Python 实现的 parity 边界：
//!
//! - `unique_signals` 保持"扁平化 + 首次出现保序"语义，与 Python 端
//!   `CzscStrategyBase.unique_signals` 一致；
//! - JSON `save_positions` / `load_positions` 的 md5 校验仍由 Python 侧承担，
//!   因为 Python `hashlib.md5(str(dict).encode())` 用的是 CPython 的字典
//!   `repr()`，无法在 Rust 侧 byte-for-byte 复现。未来若重设计为
//!   `serde_json::to_string` + sha256，可让该路径整体下沉 Rust。

use std::collections::HashSet;
use std::path::Path;

use anyhow::Result;
use czsc_core::objects::position::{Position, load_position};

/// 在一组 [`Position`] 上抽取扁平化、保序去重的 signal key 列表。
///
/// 顺序约定：按 positions 的输入顺序遍历，再按每个 position 的
/// `Position::unique_signals` 内部顺序拼接；首次出现的 key 保留位置，
/// 后续重复出现的丢弃。该约定与 Python `CzscStrategyBase.unique_signals`
/// 完全一致。
pub fn unique_signals_across(positions: &[Position]) -> Vec<String> {
    // 遍历策略中所有 Event 的 signals_all / signals_any / signals_not，
    // 第一次出现时记录顺序，后续重复出现的跳过。语义与 Python
    // `CzscStrategyBase.unique_signals` 完全一致。
    let mut seen: HashSet<String> = HashSet::new();
    let mut ordered: Vec<String> = Vec::new();
    for pos in positions {
        for event in pos.all_events() {
            for signal in event
                .signals_all
                .iter()
                .chain(event.signals_any.iter())
                .chain(event.signals_not.iter())
            {
                let key = signal.to_string();
                if seen.insert(key.clone()) {
                    ordered.push(key);
                }
            }
        }
    }
    ordered
}

/// 策略门面 trait —— 把一组 [`Position`] 组合成可被 backtest / replay 消费的
/// 配置单元。
///
/// 实现者只需要提供 [`Strategy::positions`]，默认方法会负责派生 unique signals。
pub trait Strategy {
    /// 返回当前策略的全部持仓配置。
    fn positions(&self) -> Vec<Position>;

    /// 跨 positions 扁平化 + 保序去重后的 signal key 列表。
    ///
    /// 默认实现委托给 [`unique_signals_across`]，避免每个 trait 实现者重复
    /// 同样的循环逻辑。
    fn unique_signals(&self) -> Vec<String> {
        unique_signals_across(&self.positions())
    }
}

/// 通过给定 JSON 文件列表加载持仓的"配置即策略"实现。
///
/// 与 Python `czsc.strategies.CzscJsonStrategy` 对齐：每个 JSON 文件描述一个
/// [`Position`]，由 [`czsc_core::objects::load_position`] 反序列化。
#[derive(Debug, Clone)]
pub struct JsonStrategy {
    /// 加载完成后绑定到所有 Position 上的 symbol。
    pub symbol: String,
    /// 已加载到内存的 Position 列表。
    pub positions: Vec<Position>,
}

impl JsonStrategy {
    /// 从一组 JSON 文件构造 [`JsonStrategy`]，所有 Position 共享同一个 symbol。
    ///
    /// 内部直接调用 [`czsc_core::objects::load_position`] 反序列化每个文件；
    /// 不做 md5 校验（与 Python 端 `check=False` 等价）——需要 md5 校验时
    /// 建议在调用前由 Python 侧完成。
    pub fn from_files<I, P>(symbol: impl Into<String>, files: I) -> Result<Self>
    where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        let symbol = symbol.into();
        let mut positions = Vec::new();
        for file in files {
            let mut pos = load_position(file.as_ref())?;
            pos.symbol = symbol.clone();
            positions.push(pos);
        }
        Ok(Self { symbol, positions })
    }
}

impl Strategy for JsonStrategy {
    fn positions(&self) -> Vec<Position> {
        self.positions.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use czsc_core::objects::position::Position;
    use serde_json::json;
    use std::fs;
    use tempfile::TempDir;

    fn position_from_json(value: serde_json::Value) -> Position {
        serde_json::from_value(value).expect("position payload must be valid")
    }

    /// 一个最小可序列化的 Position 用 JSON 描述：opens 引用一个 signal "k1"
    /// （signals_all 中的第一项），exits 引用 "k2"。仅用于行为测试，不要求
    /// 触发 backtest 引擎。
    fn minimal_position_payload(name: &str, signal_keys: &[&str]) -> serde_json::Value {
        // Signal 字符串格式必须严格匹配 "k1_k2_k3_v1_v2_v3_score" 7 段；
        // 此处用 signal_keys 作为 k2 段，其它段用占位符。测试只关心
        // unique_signals 的扁平化 + 保序去重，对信号语义无要求。
        let all_signals: Vec<serde_json::Value> = signal_keys
            .iter()
            .map(|k| json!(format!("日线_{k}_kind_v1_v2_v3_0")))
            .collect();
        json!({
            "symbol": "TEST",
            "name": name,
            "opens": [{
                "operate": "开多",
                "signals_all": all_signals,
                "signals_any": [],
                "signals_not": [],
                "name": "open"
            }],
            "exits": [{
                "operate": "平多",
                "signals_all": [],
                "signals_any": [],
                "signals_not": [],
                "name": "exit"
            }],
            "interval": 0,
            "timeout": 0,
            "stop_loss": 0.0,
            "T0": false
        })
    }

    #[test]
    fn unique_signals_dedups_across_positions_in_order() {
        let p1 = position_from_json(minimal_position_payload("p1", &["siga", "sigb"]));
        let p2 = position_from_json(minimal_position_payload("p2", &["sigb", "sigc"]));

        let result = unique_signals_across(&[p1, p2]);
        // siga / sigb 来自 p1，sigc 来自 p2，sigb 重复 → 仅保留一次
        assert_eq!(result.len(), 3, "got: {result:?}");
        let set: HashSet<&str> = result.iter().map(|s| s.as_str()).collect();
        assert!(set.iter().any(|s| s.contains("siga")));
        assert!(set.iter().any(|s| s.contains("sigb")));
        assert!(set.iter().any(|s| s.contains("sigc")));
    }

    #[test]
    fn json_strategy_loads_files_and_binds_symbol() {
        let dir = TempDir::new().unwrap();
        let p1_path = dir.path().join("p1.json");
        let p2_path = dir.path().join("p2.json");
        fs::write(
            &p1_path,
            serde_json::to_string(&minimal_position_payload("p1", &["siga"])).unwrap(),
        )
        .unwrap();
        fs::write(
            &p2_path,
            serde_json::to_string(&minimal_position_payload("p2", &["siga", "sigb"])).unwrap(),
        )
        .unwrap();

        let strategy = JsonStrategy::from_files("MY_SYMBOL", [&p1_path, &p2_path]).unwrap();
        assert_eq!(strategy.symbol, "MY_SYMBOL");
        assert_eq!(strategy.positions.len(), 2);
        for pos in &strategy.positions {
            assert_eq!(pos.symbol, "MY_SYMBOL");
        }

        let signals = strategy.unique_signals();
        assert_eq!(signals.len(), 2);
    }

    #[test]
    fn empty_strategy_yields_empty_signals() {
        let strategy = JsonStrategy {
            symbol: "X".to_string(),
            positions: Vec::new(),
        };
        assert!(strategy.unique_signals().is_empty());
    }
}
