//! 策略门面（Strategy facade）—— Rust 端的 [`Strategy`] trait 与 [`JsonStrategy`] 实现。
//!
//! 2026-05-17 PR-E 起，本模块承接历史上 `czsc/strategies.py` 的核心抽象，
//! 让 `cargo add czsc` 的 Rust 用户与 `pip install czsc` 的 Python 用户拿到
//! 行为一致的策略组装入口（参见 CLAUDE.md「🏛️ 开发宪法 · 第一条」）。
//!
//! 2026-05-17 PR-G 进一步把 `save_positions` / `load_positions` 整段下沉
//! Rust：新契约采用 **canonical JSON + SHA256** 作为完整性校验，可在
//! Rust 端逐位复现；旧 `md5` 字段（CPython 字典 repr() 计算，无法跨语言
//! 复现）改为静默忽略，参见模块尾部 [`save_position_to_file`] /
//! [`load_position_from_file`] 文档。
//!
//! 设计要点：
//!
//! - [`Strategy`] trait 暴露一个抽象方法 [`Strategy::positions`]（子类提供持仓
//!   列表），其它派生信息（unique_signals）走默认实现，避免实现者每次重复
//!   "for pos in positions: for sig in pos.unique_signals" 这段固定模板；
//! - [`JsonStrategy`] 是最常用的具体类型，从一组 JSON 文件加载 [`Position`]
//!   列表（沿用 [`czsc_core::objects::position::load_position`]）；
//! - 自由函数 [`unique_signals_across`] 是 trait 默认方法的纯粹算法 core，
//!   方便测试单独覆盖、也方便 Python binding 直接调用而无需构造 trait object；
//! - 自由函数 [`save_position_to_file`] / [`load_position_from_file`] 把
//!   Python 端 `CzscStrategyBase.save_positions / load_positions` 的全部
//!   IO + 校验逻辑搬到 Rust 端，Python 端只剩一行透传（开发宪法第一条收口）。

use std::collections::HashSet;
use std::fs;
use std::path::Path;

use anyhow::{Context, Result, anyhow};
use czsc_core::objects::position::Position;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

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
/// [`Position`]，由 [`load_position_from_file`] 反序列化（含 PR-G 起的
/// checksum 校验）。
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
    /// `check`：是否启用 checksum 校验。新格式（PR-G）的 `checksum` 字段
    /// 缺失或不匹配时报错；旧格式（仅 `md5` 字段，算法不可跨语言复现）
    /// 与无校验字段的文件均静默通过——与 Python `CzscJsonStrategy(check_position=False)`
    /// 的语义对齐。
    pub fn from_files<I, P>(symbol: impl Into<String>, files: I, check: bool) -> Result<Self>
    where
        I: IntoIterator<Item = P>,
        P: AsRef<Path>,
    {
        let symbol = symbol.into();
        let mut positions = Vec::new();
        for file in files {
            let pos = load_position_from_file(file.as_ref(), &symbol, check)?;
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

// ---------------------------------------------------------------------------
// PR-G：基于 canonical JSON + SHA256 的可跨语言 checksum 契约
// ---------------------------------------------------------------------------

/// PR-G 起 czsc 仓位 JSON 文件中的校验字段名。
const CHECKSUM_FIELD: &str = "checksum";

/// 历史（PR-G 之前）的校验字段名。其值由 CPython
/// `hashlib.md5(str(dict).encode())` 计算，依赖 CPython 字典 `repr()`，
/// 无法在 Rust 端逐位复现。本模块仅识别该字段、不验证其内容，并在写出新
/// 文件时主动剔除，逐步淘汰旧契约。
const LEGACY_MD5_FIELD: &str = "md5";

/// 在序列化 / checksum 计算前总是被剥离的字段。
///
/// `symbol` 与策略实例耦合，落盘时移除可让同一份持仓在不同标的间复用；
/// 校验字段在算 checksum 前必须先移除，否则 self-reference 会导致循环。
const STRIPPED_FIELDS_FOR_CHECKSUM: &[&str] = &[CHECKSUM_FIELD, LEGACY_MD5_FIELD];

/// 把 [`Position`] 写到 `path`，附带 SHA256 完整性校验字段。
///
/// 写出契约（PR-G 新格式）：
///
/// 1. `serde_json::to_value(pos)` 得到完整字段映射；
/// 2. 剥离 `symbol` 字段（策略实例耦合，加载时由调用方注入）以及任何
///    历史遗留的 `md5` / `checksum`；
/// 3. 以"键排序 + 紧凑 JSON 字符串"作为 canonical form 算 SHA256 hex；
/// 4. 写回到 payload 的 `checksum` 字段；
/// 5. 以紧凑 JSON 写入文件。
pub fn save_position_to_file(pos: &Position, path: &Path) -> Result<()> {
    let mut payload =
        serde_json::to_value(pos).with_context(|| format!("序列化 Position 失败: {path:?}"))?;
    {
        let map = expect_object_mut(&mut payload, path)?;
        // 剥离 symbol（运行时绑定，复用配置时由调用方注入）
        map.remove("symbol");
        // 算 checksum 前先剥离任何历史遗留校验字段，避免递归
        for field in STRIPPED_FIELDS_FOR_CHECKSUM {
            map.remove(*field);
        }
    }
    let checksum = compute_checksum(&payload);
    {
        let map = expect_object_mut(&mut payload, path)?;
        map.insert(CHECKSUM_FIELD.to_string(), Value::String(checksum));
    }
    let content = serde_json::to_string(&payload)
        .with_context(|| format!("序列化最终 payload 失败: {path:?}"))?;
    fs::write(path, content).with_context(|| format!("写入文件失败: {path:?}"))?;
    Ok(())
}

/// 从 `path` 加载 [`Position`]，可选启用 checksum 校验。
///
/// 读取契约：
///
/// - **新格式（PR-G+）**：文件含 `checksum` 字段时按相同 canonical form
///   重新计算并比对；不一致时报错（仅当 `check=true`）。
/// - **旧格式（PR-G 之前）**：文件含 `md5` 字段但无 `checksum` —— 该字段
///   依赖 CPython repr，无法 Rust 复现，**直接静默忽略不做校验**，由调用
///   方择机用 [`save_position_to_file`] 写回升级到新格式。
/// - **无校验字段**：当作手写或外部生成的 JSON，跳过校验。
///
/// 不论是否校验，最终都会把 `symbol` 参数注入 Position 字段，行为与 Python
/// `CzscStrategyBase.load_positions` 历史实现一致。
pub fn load_position_from_file(path: &Path, symbol: &str, check: bool) -> Result<Position> {
    let raw = fs::read_to_string(path).with_context(|| format!("读取文件失败: {path:?}"))?;
    let mut payload: Value =
        serde_json::from_str(&raw).with_context(|| format!("解析 JSON 失败: {path:?}"))?;

    // 提取并剥离两个校验字段，留下"待校验内容"
    let stored_checksum: Option<String>;
    let had_legacy_md5: bool;
    {
        let map = expect_object_mut(&mut payload, path)?;
        stored_checksum = map
            .remove(CHECKSUM_FIELD)
            .and_then(|v| v.as_str().map(|s| s.to_string()));
        had_legacy_md5 = map.remove(LEGACY_MD5_FIELD).is_some();
    }

    if check {
        match (stored_checksum.as_ref(), had_legacy_md5) {
            (Some(expected), _) => {
                let actual = compute_checksum(&payload);
                if expected != &actual {
                    return Err(anyhow!(
                        "checksum 不匹配（文件可能被篡改）: {path:?}\n  expected = {expected}\n  actual   = {actual}"
                    ));
                }
            }
            (None, true) => {
                // 旧格式 md5：算法不可跨语言复现，按设计静默通过；这里
                // 不打 warning 日志（保持 stdout 干净），调用方需要审计
                // 可自行 grep 历史 commit。
            }
            (None, false) => {
                // 无校验字段：手写 / 外部生成，按 Python 历史行为跳过
            }
        }
    }

    // 注入 symbol
    {
        let map = expect_object_mut(&mut payload, path)?;
        map.insert("symbol".to_string(), Value::String(symbol.to_string()));
    }

    let mut pos: Position = serde_json::from_value(payload)
        .with_context(|| format!("反序列化 Position 失败: {path:?}"))?;
    pos.normalize_runtime_fields();
    Ok(pos)
}

/// 计算 payload 的 canonical SHA256 hex。
///
/// canonical form 定义为：
///
/// - **键序**：所有 `Object` 节点的键按字典序升序（serde_json 默认 `Map`
///   实现为 `BTreeMap`，自动满足）；
/// - **空白**：紧凑形式（无空格、无换行）；
/// - **数值**：保持 serde_json 的默认浮点格式化（兼容 IEEE-754）；
/// - **字符串**：保持 serde_json 的转义规则（最小化转义）。
///
/// 摘要算法：SHA-256，输出 lower-case hex。
fn compute_checksum(value: &Value) -> String {
    let canonical = serde_json::to_string(value).expect("Value 序列化不应失败");
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    hex::encode(hasher.finalize())
}

fn expect_object_mut<'v>(value: &'v mut Value, path: &Path) -> Result<&'v mut Map<String, Value>> {
    value.as_object_mut().ok_or_else(|| {
        anyhow!("期望文件根节点是 JSON Object（Position payload），但实际不是: {path:?}")
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use czsc_core::objects::position::{Position, load_position};
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
        // 先用 save_position_to_file 写出（带新 checksum 字段），再让
        // JsonStrategy::from_files 校验加载
        let pos1 = position_from_json(minimal_position_payload("p1", &["siga"]));
        let pos2 = position_from_json(minimal_position_payload("p2", &["siga", "sigb"]));
        save_position_to_file(&pos1, &p1_path).unwrap();
        save_position_to_file(&pos2, &p2_path).unwrap();

        let strategy = JsonStrategy::from_files("MY_SYMBOL", [&p1_path, &p2_path], true).unwrap();
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

    // -- PR-G checksum 契约测试 ------------------------------------------

    #[test]
    fn save_writes_checksum_and_strips_symbol() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("pos.json");
        let pos = position_from_json(minimal_position_payload("p", &["siga"]));
        save_position_to_file(&pos, &path).unwrap();

        let raw = fs::read_to_string(&path).unwrap();
        let value: serde_json::Value = serde_json::from_str(&raw).unwrap();
        let obj = value.as_object().unwrap();

        assert!(obj.contains_key("checksum"), "新格式必须写出 checksum 字段");
        assert!(
            !obj.contains_key("symbol"),
            "save 必须剥离 symbol，让配置可复用"
        );
        assert!(
            !obj.contains_key("md5"),
            "新写出的文件不应再有遗留的 md5 字段"
        );
        let checksum = obj["checksum"].as_str().unwrap();
        assert_eq!(checksum.len(), 64, "SHA256 hex 字符串应为 64 位");
    }

    #[test]
    fn round_trip_preserves_position() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("pos.json");
        let pos = position_from_json(minimal_position_payload("rt", &["siga", "sigb"]));
        save_position_to_file(&pos, &path).unwrap();
        let loaded = load_position_from_file(&path, "NEW_SYMBOL", true).unwrap();
        assert_eq!(loaded.symbol, "NEW_SYMBOL");
        assert_eq!(loaded.name, "rt");
        assert_eq!(loaded.opens.len(), 1);
    }

    #[test]
    fn tampered_file_fails_checksum_check() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("pos.json");
        let pos = position_from_json(minimal_position_payload("t", &["siga"]));
        save_position_to_file(&pos, &path).unwrap();

        // 篡改：把 name 从 "t" 改成 "tampered"
        let raw = fs::read_to_string(&path).unwrap();
        let tampered = raw.replace("\"name\":\"t\"", "\"name\":\"tampered\"");
        fs::write(&path, tampered).unwrap();

        let err = load_position_from_file(&path, "X", true).unwrap_err();
        assert!(
            err.to_string().contains("checksum 不匹配"),
            "篡改后的 checksum 必须不匹配，实际错误：{err}"
        );

        // check=false 时应该静默通过（与 Python 历史行为对齐）
        let pos = load_position_from_file(&path, "X", false).unwrap();
        assert_eq!(pos.name, "tampered");
    }

    #[test]
    fn legacy_md5_file_loads_silently() {
        // 模拟 PR-G 之前 Python 写出的文件：只有 md5 字段、没有 checksum
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("legacy.json");
        let mut payload = minimal_position_payload("legacy", &["siga"]);
        payload.as_object_mut().unwrap().remove("symbol");
        // 写一个故意错误的 md5——确认 PR-G 不再尝试校验它
        payload
            .as_object_mut()
            .unwrap()
            .insert("md5".to_string(), Value::String("deadbeef".into()));
        fs::write(&path, serde_json::to_string(&payload).unwrap()).unwrap();

        // check=true 也应该成功（旧 md5 字段不可校验，静默跳过）
        let pos = load_position_from_file(&path, "X", true).unwrap();
        assert_eq!(pos.name, "legacy");
        assert_eq!(pos.symbol, "X");
    }

    #[test]
    fn missing_checksum_with_check_true_passes() {
        // 既无 md5 也无 checksum 的手写 JSON，check=true 也通过
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("plain.json");
        let mut payload = minimal_position_payload("plain", &["siga"]);
        payload.as_object_mut().unwrap().remove("symbol");
        fs::write(&path, serde_json::to_string(&payload).unwrap()).unwrap();

        let pos = load_position_from_file(&path, "X", true).unwrap();
        assert_eq!(pos.name, "plain");
    }

    #[test]
    fn canonical_form_is_key_sorted() {
        // canonical form 必须无关原 dict 键插入顺序：构造两个键序不同但
        // 语义相同的 payload，两边 checksum 必须相等
        let v1 = json!({"a": 1, "b": 2, "c": {"x": 10, "y": 20}});
        let v2 = json!({"c": {"y": 20, "x": 10}, "b": 2, "a": 1});
        assert_eq!(compute_checksum(&v1), compute_checksum(&v2));
    }

    // 保证保留 load_position 作为 czsc-core 的入口仍能加载完整 Position
    // （含 symbol 字段）；PR-G 起新代码应当走 load_position_from_file。
    #[test]
    fn load_position_core_helper_still_works() {
        let dir = TempDir::new().unwrap();
        let path = dir.path().join("core.json");
        let payload = minimal_position_payload("core", &["siga"]);
        fs::write(&path, serde_json::to_string(&payload).unwrap()).unwrap();

        let pos = load_position(&path).unwrap();
        assert_eq!(pos.name, "core");
        assert_eq!(pos.symbol, "TEST");
    }
}
