use crate::trader::api::{build_signals_dataframe, normalize_signals_dtypes, run_optimize};
use crate::utils::df_convert::{df_to_pyarrow, pyarrow_to_df};
#[cfg(test)]
use chrono::{DateTime, NaiveDate, NaiveDateTime, Utc};
use czsc_core::analyze::utils::format_standard_kline;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::position::Position;
use czsc_trader::engine_v2::{ExecutionPlan, ExecutionPlanInput, UnifiedExecEngine};
use czsc_trader::optimize::{get_exit_optim_positions, get_open_optim_positions};
use czsc_trader::signals::sig_parse::SignalConfig;
use czsc_signals::registry::{SIGNAL_REGISTRY, TRADER_SIGNAL_REGISTRY};
use polars::prelude::*;
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use serde::Deserialize;
use serde_json::Value;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Deserialize)]
struct StrategyConfig {
    pub name: Option<String>,
    pub symbol: String,
    pub base_freq: String,
    #[allow(dead_code)]
    pub signals_module: Option<String>,
    #[serde(default)]
    pub signals_config: Vec<SignalConfig>,
    pub positions: Vec<Position>,
    pub market: Option<String>,
    pub bg_max_count: Option<usize>,
    pub sdt: Option<String>,
    #[serde(default)]
    pub include_sdt_bar: Option<bool>,
}

#[derive(Debug, Deserialize, Default)]
struct RunOpts {
    pub emit_signals: Option<bool>,
}

#[cfg(test)]
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

fn validate_strategy(cfg: &StrategyConfig) -> PyResult<()> {
    if cfg.symbol.trim().is_empty() {
        return Err(PyValueError::new_err("strategy.symbol 不能为空"));
    }
    if cfg.positions.is_empty() {
        return Err(PyValueError::new_err("strategy.positions 不能为空"));
    }

    for sc in &cfg.signals_config {
        if sc.freq.is_some() {
            if !SIGNAL_REGISTRY.contains_key(sc.name.as_str()) {
                return Err(PyValueError::new_err(format!(
                    "signals_config 包含未注册 K 线信号: {}",
                    sc.name
                )));
            }
        } else if !TRADER_SIGNAL_REGISTRY.contains_key(sc.name.as_str()) {
            return Err(PyValueError::new_err(format!(
                "signals_config 包含未注册 Trader 信号: {}",
                sc.name
            )));
        }
    }

    Ok(())
}

fn combine_pairs_holds(positions: &[Position]) -> PyResult<(DataFrame, DataFrame)> {
    let mut all_pairs = Vec::new();
    let mut all_holds = Vec::new();

    for pos in positions {
        if let Ok(df) = pos.pairs() {
            all_pairs.push(df.lazy());
        }
        if let Ok(mut df) = pos.holds() {
            if df.height() == 0 {
                continue;
            }
            let pos_name = Series::new("pos_name", vec![pos.name.clone(); df.height()]);
            df.with_column(pos_name)
                .map_err(|e| PyRuntimeError::new_err(format!("追加 pos_name 列失败: {e}")))?;
            all_holds.push(df.lazy());
        }
    }

    let mut pairs_df = if all_pairs.is_empty() {
        DataFrame::default()
    } else {
        concat(all_pairs, UnionArgs::default())
            .and_then(|lf| lf.collect())
            .map_err(|e| PyRuntimeError::new_err(format!("合并 pairs 失败: {e}")))?
    };

    for (name, dtype) in [
        ("开仓时间", DataType::Datetime(TimeUnit::Nanoseconds, None)),
        ("平仓时间", DataType::Datetime(TimeUnit::Nanoseconds, None)),
        ("持仓K线数", DataType::Int64),
    ] {
        if pairs_df.column(name).is_ok() {
            let casted = pairs_df
                .column(name)
                .and_then(|s| s.cast(&dtype))
                .map_err(|e| {
                    PyRuntimeError::new_err(format!("pairs 列 {name} 类型转换失败: {e}"))
                })?;
            pairs_df
                .with_column(casted)
                .map_err(|e| PyRuntimeError::new_err(format!("pairs 写回列 {name} 失败: {e}")))?;
        }
    }

    let mut holds_df = if all_holds.is_empty() {
        DataFrame::default()
    } else {
        concat(all_holds, UnionArgs::default())
            .and_then(|lf| lf.collect())
            .map_err(|e| PyRuntimeError::new_err(format!("合并 holds 失败: {e}")))?
    };

    for (name, dtype) in [
        ("dt", DataType::Datetime(TimeUnit::Nanoseconds, None)),
        ("pos", DataType::Int64),
    ] {
        if holds_df.column(name).is_ok() {
            let casted = holds_df
                .column(name)
                .and_then(|s| s.cast(&dtype))
                .map_err(|e| {
                    PyRuntimeError::new_err(format!("holds 列 {name} 类型转换失败: {e}"))
                })?;
            holds_df
                .with_column(casted)
                .map_err(|e| PyRuntimeError::new_err(format!("holds 写回列 {name} 失败: {e}")))?;
        }
    }

    Ok((pairs_df, holds_df))
}

fn write_df_parquet(path: &Path, mut df: DataFrame) -> PyResult<()> {
    let mut file = fs::File::create(path)
        .map_err(|e| PyValueError::new_err(format!("创建输出文件失败: {e}")))?;
    ParquetWriter::new(&mut file)
        .finish(&mut df)
        .map_err(|e| PyRuntimeError::new_err(format!("写出 parquet 失败: {e}")))?;
    Ok(())
}

type ResearchCoreResult = (
    StrategyConfig,
    usize,
    Vec<HashMap<String, String>>,
    DataFrame,
    DataFrame,
    i64,
    Option<CoreLoopProfile>,
);

#[derive(Debug, Clone, Copy, Default)]
struct CoreLoopProfile {
    bars: usize,
    signals_update_ns: u128,
    trader_signals_ns: u128,
    position_update_ns: u128,
    pos_event_match_ns: u128,
    pos_fsm_ns: u128,
    pos_risk_ns: u128,
    pos_holds_ns: u128,
}

impl CoreLoopProfile {
    fn total_ns(&self) -> u128 {
        self.signals_update_ns + self.trader_signals_ns + self.position_update_ns
    }
}

fn event_to_py_dump(e: &czsc_core::objects::event::Event) -> Value {
    serde_json::json!({
        "name": e.name,
        "operate": e.operate.to_chinese(),
        "signals_all": e.signals_all.iter().map(|s| s.to_string()).collect::<Vec<_>>(),
        "signals_any": e.signals_any.iter().map(|s| s.to_string()).collect::<Vec<_>>(),
        "signals_not": e.signals_not.iter().map(|s| s.to_string()).collect::<Vec<_>>(),
    })
}

fn position_to_py_dump(p: &Position) -> Value {
    serde_json::json!({
        "name": p.name,
        "symbol": p.symbol,
        "opens": p.opens.iter().map(event_to_py_dump).collect::<Vec<_>>(),
        "exits": p.exits.iter().map(event_to_py_dump).collect::<Vec<_>>(),
        "interval": p.interval,
        "timeout": p.timeout,
        "stop_loss": p.stop_loss,
        "T0": p.t0,
    })
}

fn run_research_core(
    bars_raw: &[u8],
    strategy_json: &str,
    sdt_override: Option<&str>,
    emit_signals: bool,
) -> PyResult<ResearchCoreResult> {
    let cfg: StrategyConfig = serde_json::from_str(strategy_json)
        .map_err(|e| PyValueError::new_err(format!("strategy json 解析失败: {e}")))?;
    validate_strategy(&cfg)?;

    let df = pyarrow_to_df(bars_raw)
        .map_err(|e| PyValueError::new_err(format!("Arrow bytes 转 DataFrame 失败: {e}")))?;
    let base_freq = cfg
        .base_freq
        .parse::<Freq>()
        .map_err(|_| PyValueError::new_err("strategy.base_freq 解析失败"))?;
    let bars = format_standard_kline(df, base_freq)
        .map_err(|e| PyValueError::new_err(format!("K线标准化格式错误: {e}")))?;

    if bars.is_empty() {
        return Err(PyValueError::new_err("bars 为空，无法执行回测"));
    }

    let plan_input = ExecutionPlanInput {
        symbol: cfg.symbol.clone(),
        base_freq: cfg.base_freq.clone(),
        signals_config: cfg.signals_config.clone(),
        positions: cfg.positions.clone(),
        market: cfg.market.clone(),
        bg_max_count: cfg.bg_max_count,
        sdt: cfg.sdt.clone(),
        include_sdt_bar: cfg.include_sdt_bar,
    };
    let plan = ExecutionPlan::compile(plan_input)
        .map_err(|e| PyValueError::new_err(format!("ExecutionPlan 编译失败: {e}")))?;

    let enable_profile = std::env::var("RS_CZSC_PROFILE_CORE")
        .map(|v| v == "1" || v.eq_ignore_ascii_case("true"))
        .unwrap_or(false);
    let output = UnifiedExecEngine::run(&plan, bars, sdt_override, emit_signals, enable_profile)
        .map_err(|e| PyRuntimeError::new_err(format!("UnifiedExecEngine 执行失败: {e}")))?;
    let (pairs_df, holds_df) = combine_pairs_holds(&output.positions)?;
    let elapsed_ms = output.elapsed_ms;
    let rows = output.signal_rows;
    let bars_count = output.bars_count;
    let profile = output.profile.map(|p| CoreLoopProfile {
        bars: p.bars,
        signals_update_ns: p.signals_update_ns,
        trader_signals_ns: p.trader_signals_ns,
        position_update_ns: p.position_update_ns,
        pos_event_match_ns: p.pos_event_match_ns,
        pos_fsm_ns: p.pos_fsm_ns,
        pos_risk_ns: p.pos_risk_ns,
        pos_holds_ns: p.pos_holds_ns,
    });

    Ok((
        cfg, bars_count, rows, pairs_df, holds_df, elapsed_ms, profile,
    ))
}

#[allow(clippy::too_many_arguments)]
fn build_result_dict(
    py: Python<'_>,
    cfg: &StrategyConfig,
    bars_count: usize,
    rows: &[HashMap<String, String>],
    signals_df: &DataFrame,
    pairs_df: &DataFrame,
    holds_df: &DataFrame,
    elapsed_ms: i64,
    profile: Option<CoreLoopProfile>,
    extra_paths: Option<(&str, &str, &str)>,
) -> PyResult<Py<PyDict>> {
    let mut signals_df_mut = signals_df.clone();
    let mut pairs_df_mut = pairs_df.clone();
    let mut holds_df_mut = holds_df.clone();

    let signals_arrow = df_to_pyarrow(&mut signals_df_mut)
        .map_err(|e| PyRuntimeError::new_err(format!("signals Arrow 编码失败: {e}")))?;
    let pairs_arrow = df_to_pyarrow(&mut pairs_df_mut)
        .map_err(|e| PyRuntimeError::new_err(format!("pairs Arrow 编码失败: {e}")))?;
    let holds_arrow = df_to_pyarrow(&mut holds_df_mut)
        .map_err(|e| PyRuntimeError::new_err(format!("holds Arrow 编码失败: {e}")))?;

    let meta = PyDict::new(py);
    meta.set_item("symbol", cfg.symbol.clone())?;
    meta.set_item("strategy_name", cfg.name.clone().unwrap_or_default())?;
    meta.set_item("base_freq", cfg.base_freq.clone())?;
    meta.set_item("bars_count", bars_count)?;
    meta.set_item("signals_count", rows.len())?;
    meta.set_item("positions", cfg.positions.len())?;
    meta.set_item("elapsed_ms", elapsed_ms)?;
    meta.set_item("warning_count", 0)?;
    if let Some(p) = profile {
        let pyd = PyDict::new(py);
        let total_ns = p.total_ns() as f64;
        let signals_ns = p.signals_update_ns as f64;
        let trader_ns = p.trader_signals_ns as f64;
        let pos_ns = p.position_update_ns as f64;
        let pos_event_ns = p.pos_event_match_ns as f64;
        let pos_fsm_ns = p.pos_fsm_ns as f64;
        let pos_risk_ns = p.pos_risk_ns as f64;
        let pos_holds_ns = p.pos_holds_ns as f64;
        pyd.set_item("bars", p.bars)?;
        pyd.set_item("signals_update_ms", signals_ns / 1_000_000.0)?;
        pyd.set_item("trader_signals_ms", trader_ns / 1_000_000.0)?;
        pyd.set_item("position_update_ms", pos_ns / 1_000_000.0)?;
        pyd.set_item("total_profiled_ms", total_ns / 1_000_000.0)?;
        pyd.set_item("position_event_match_ms", pos_event_ns / 1_000_000.0)?;
        pyd.set_item("position_fsm_ms", pos_fsm_ns / 1_000_000.0)?;
        pyd.set_item("position_risk_ms", pos_risk_ns / 1_000_000.0)?;
        pyd.set_item("position_holds_ms", pos_holds_ns / 1_000_000.0)?;
        if total_ns > 0.0 {
            pyd.set_item("signals_update_pct", signals_ns * 100.0 / total_ns)?;
            pyd.set_item("trader_signals_pct", trader_ns * 100.0 / total_ns)?;
            pyd.set_item("position_update_pct", pos_ns * 100.0 / total_ns)?;
        } else {
            pyd.set_item("signals_update_pct", 0.0)?;
            pyd.set_item("trader_signals_pct", 0.0)?;
            pyd.set_item("position_update_pct", 0.0)?;
        }
        if pos_ns > 0.0 {
            pyd.set_item("position_event_match_pct", pos_event_ns * 100.0 / pos_ns)?;
            pyd.set_item("position_fsm_pct", pos_fsm_ns * 100.0 / pos_ns)?;
            pyd.set_item("position_risk_pct", pos_risk_ns * 100.0 / pos_ns)?;
            pyd.set_item("position_holds_pct", pos_holds_ns * 100.0 / pos_ns)?;
        } else {
            pyd.set_item("position_event_match_pct", 0.0)?;
            pyd.set_item("position_fsm_pct", 0.0)?;
            pyd.set_item("position_risk_pct", 0.0)?;
            pyd.set_item("position_holds_pct", 0.0)?;
        }
        meta.set_item("profile", pyd)?;
    }

    let out = PyDict::new(py);
    out.set_item("meta", meta)?;
    out.set_item("signals_arrow", PyBytes::new(py, &signals_arrow))?;
    out.set_item("pairs_arrow", PyBytes::new(py, &pairs_arrow))?;
    out.set_item("holds_arrow", PyBytes::new(py, &holds_arrow))?;

    if let Some((sp, pp, hp)) = extra_paths {
        out.set_item("signals_path", sp)?;
        out.set_item("pairs_path", pp)?;
        out.set_item("holds_path", hp)?;
    }

    Ok(out.into())
}

/// 高性能研究入口，返回内存中的 Arrow bytes 结果。
///
/// 与 `run_backtest` 的区别：
/// - 不要求事先准备 config 文件，策略直接用 `strategy_json` 传入
/// - 默认返回内存里的 `signals/pairs/holds` Arrow bytes，便于 Python 侧继续处理
/// - 可通过 `opts_json` 控制是否生成信号表等细节
///
/// 返回值是一个 `dict`，核心字段包括：
/// - `meta`: 执行元数据与 profile
/// - `signals_arrow`
/// - `pairs_arrow`
/// - `holds_arrow`
#[pyfunction]
#[pyo3(text_signature = "(bars_bytes, strategy_json, sdt=None, opts_json=None)")]
#[pyo3(signature = (bars_bytes, strategy_json, sdt=None, opts_json=None))]
pub fn run_research(
    py: Python<'_>,
    bars_bytes: &Bound<PyBytes>,
    strategy_json: &str,
    sdt: Option<&str>,
    opts_json: Option<&str>,
) -> PyResult<Py<PyDict>> {
    let opts = opts_json
        .map(|s| {
            serde_json::from_str::<RunOpts>(s)
                .map_err(|e| PyValueError::new_err(format!("opts_json 解析失败: {e}")))
        })
        .transpose()?
        .unwrap_or_default();
    let emit_signals = opts.emit_signals.unwrap_or(true);

    let (cfg, bars_count, rows, pairs_df, holds_df, elapsed_ms, profile) =
        run_research_core(bars_bytes.as_bytes(), strategy_json, sdt, emit_signals)?;
    let signals_df = normalize_signals_dtypes(build_signals_dataframe(&rows)?)?;

    build_result_dict(
        py,
        &cfg,
        bars_count,
        &rows,
        &signals_df,
        &pairs_df,
        &holds_df,
        elapsed_ms,
        profile,
        None,
    )
}

/// 回放入口，在 `run_research` 基础上可选把产物落盘为 parquet。
///
/// 适合策略开发和可视化回放：
/// - 若提供 `res_path`，会写出 `signals.parquet / pairs.parquet / holds.parquet`
/// - 若不提供 `res_path`，行为与 `run_research` 接近，仍返回内存结果
///
/// 返回值同样是一个 `dict`；当实际落盘时会额外带上三个输出文件路径。
#[pyfunction]
#[pyo3(text_signature = "(bars_bytes, strategy_json, res_path=None, sdt=None, opts_json=None)")]
#[pyo3(signature = (bars_bytes, strategy_json, res_path=None, sdt=None, opts_json=None))]
pub fn run_replay(
    py: Python<'_>,
    bars_bytes: &Bound<PyBytes>,
    strategy_json: &str,
    res_path: Option<&str>,
    sdt: Option<&str>,
    opts_json: Option<&str>,
) -> PyResult<Py<PyDict>> {
    let opts = opts_json
        .map(|s| {
            serde_json::from_str::<RunOpts>(s)
                .map_err(|e| PyValueError::new_err(format!("opts_json 解析失败: {e}")))
        })
        .transpose()?
        .unwrap_or_default();
    let emit_signals = opts.emit_signals.unwrap_or(true);

    let (cfg, bars_count, rows, pairs_df, holds_df, elapsed_ms, profile) =
        run_research_core(bars_bytes.as_bytes(), strategy_json, sdt, emit_signals)?;
    let signals_df = normalize_signals_dtypes(build_signals_dataframe(&rows)?)?;

    let mut extra_paths: Option<(String, String, String)> = None;
    if let Some(base) = res_path {
        let base_path = Path::new(base);
        if !base_path.exists() {
            fs::create_dir_all(base_path)
                .map_err(|e| PyValueError::new_err(format!("创建结果目录失败: {e}")))?;
        }

        let signals_path = base_path.join("signals.parquet");
        let pairs_path = base_path.join("pairs.parquet");
        let holds_path = base_path.join("holds.parquet");

        write_df_parquet(&signals_path, signals_df.clone())?;
        write_df_parquet(&pairs_path, pairs_df.clone())?;
        write_df_parquet(&holds_path, holds_df.clone())?;

        extra_paths = Some((
            signals_path.to_string_lossy().to_string(),
            pairs_path.to_string_lossy().to_string(),
            holds_path.to_string_lossy().to_string(),
        ));
    }

    let extra_refs = extra_paths
        .as_ref()
        .map(|(a, b, c)| (a.as_str(), b.as_str(), c.as_str()));

    build_result_dict(
        py,
        &cfg,
        bars_count,
        &rows,
        &signals_df,
        &pairs_df,
        &holds_df,
        elapsed_ms,
        profile,
        extra_refs,
    )
}

/// 优化批量入口，接受 JSON 字符串形式的优化配置。
///
/// 这是 Python facade 常用入口：
/// - Python 侧直接构造 `dict`
/// - 序列化成 JSON 字符串传给这里
/// - Rust 内部写入临时配置文件，再复用 `run_optimize`
///
/// 这样可以兼容旧版类式 API，同时保持底层只维护一套优化执行逻辑。
#[pyfunction]
#[pyo3(text_signature = "(bars_dir, optimize_config_json, res_path, n_threads=1)")]
#[pyo3(signature = (bars_dir, optimize_config_json, res_path, n_threads=1))]
pub fn run_optimize_batch(
    bars_dir: &str,
    optimize_config_json: &str,
    res_path: &str,
    n_threads: usize,
) -> PyResult<String> {
    let parsed: Value = serde_json::from_str(optimize_config_json)
        .map_err(|e| PyValueError::new_err(format!("optimize 配置 JSON 解析失败: {e}")))?;

    let temp_path = std::env::temp_dir().join("rs_czsc_optimize_config.json");
    fs::write(&temp_path, parsed.to_string())
        .map_err(|e| PyValueError::new_err(format!("写入临时优化配置失败: {e}")))?;

    run_optimize(
        bars_dir,
        temp_path
            .to_str()
            .ok_or_else(|| PyValueError::new_err("临时配置路径无效"))?,
        res_path,
        n_threads,
    )
}

/// 仅构建开仓优化候选策略，不运行回测。
///
/// 输入：
/// - `files_position`: 基准仓位 JSON 文件路径列表
/// - `candidate_signals`: 候选开仓信号列表
///
/// 输出：
/// - `Position.dump()` 风格的 JSON 字符串数组
///
/// 典型用法是先调用本函数生成候选仓位，再交给 `run_optimize_batch` 跑批。
#[pyfunction]
#[pyo3(text_signature = "(files_position, candidate_signals)")]
#[pyo3(signature = (files_position, candidate_signals))]
pub fn build_open_optim_positions(
    files_position: Vec<String>,
    candidate_signals: Vec<String>,
) -> PyResult<String> {
    let files: Vec<PathBuf> = files_position.into_iter().map(PathBuf::from).collect();
    let positions = get_open_optim_positions(&files, &candidate_signals)
        .map_err(|e| PyRuntimeError::new_err(format!("构建开仓优化策略失败: {e}")))?;
    let payload: Vec<Value> = positions.iter().map(position_to_py_dump).collect();
    serde_json::to_string(&payload)
        .map_err(|e| PyRuntimeError::new_err(format!("序列化开仓优化策略失败: {e}")))
}

/// 仅构建平仓优化候选策略，不运行回测。
///
/// 与 `build_open_optim_positions` 的区别在于输入是 `candidate_events_json`，
/// 即 Python 侧事件定义列表的 JSON 字符串。返回值仍是
/// `Position.dump()` 风格的 JSON 字符串数组。
#[pyfunction]
#[pyo3(text_signature = "(files_position, candidate_events_json)")]
#[pyo3(signature = (files_position, candidate_events_json))]
pub fn build_exit_optim_positions(
    files_position: Vec<String>,
    candidate_events_json: &str,
) -> PyResult<String> {
    let files: Vec<PathBuf> = files_position.into_iter().map(PathBuf::from).collect();
    let candidate_events: Vec<Value> = serde_json::from_str(candidate_events_json)
        .map_err(|e| PyValueError::new_err(format!("candidate_events_json 解析失败: {e}")))?;
    let positions = get_exit_optim_positions(&files, &candidate_events)
        .map_err(|e| PyRuntimeError::new_err(format!("构建平仓优化策略失败: {e}")))?;
    let payload: Vec<Value> = positions.iter().map(position_to_py_dump).collect();
    serde_json::to_string(&payload)
        .map_err(|e| PyRuntimeError::new_err(format!("序列化平仓优化策略失败: {e}")))
}

#[cfg(test)]
mod tests {
    use super::{StrategyConfig, parse_sdt_utc, validate_strategy};

    #[test]
    fn test_parse_sdt_utc_supports_iso_t_without_tz() {
        let dt = parse_sdt_utc("2023-02-28T12:00:00");
        assert!(dt.is_some());
    }

    #[test]
    fn test_strategy_config_json_deserialize() {
        let s = r#"{
            \"name\": \"demo\",
            \"symbol\": \"TEST.SZ\",
            \"base_freq\": \"5分钟\",
            \"signals_module\": \"czsc.signals\",
            \"signals_config\": [{\"name\":\"bar_triple_V230506\",\"freq\":\"5分钟\",\"params\":{\"di\":1}}],
            \"positions\": [{
                \"name\": \"p1\", \"symbol\": \"TEST.SZ\", \"opens\": [], \"exits\": [],
                \"interval\": 0, \"timeout\": 1, \"stop_loss\": 100.0, \"T0\": false
            }],
            \"market\": \"默认\", \"bg_max_count\": 5000
        }"#;
        let cfg: StrategyConfig = serde_json::from_str(s).expect("deserialize failed");
        assert_eq!(cfg.symbol, "TEST.SZ");
        assert_eq!(cfg.base_freq, "5分钟");
        assert_eq!(cfg.positions.len(), 1);
    }

    #[test]
    fn test_validate_strategy_rejects_empty_symbol() {
        let s = r#"{
            \"symbol\": \"\",
            \"base_freq\": \"5分钟\",
            \"signals_config\": [],
            \"positions\": [{
                \"name\": \"p1\", \"symbol\": \"TEST.SZ\", \"opens\": [], \"exits\": [],
                \"interval\": 0, \"timeout\": 1, \"stop_loss\": 100.0, \"T0\": false
            }]
        }"#;
        let cfg: StrategyConfig = serde_json::from_str(s).expect("deserialize failed");
        let r = validate_strategy(&cfg);
        assert!(r.is_err());
    }
}
