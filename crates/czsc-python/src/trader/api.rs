use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict, PyList};
use rust_xlsxwriter::Workbook;
use serde_json::{Value, json};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::utils::df_convert::pyarrow_to_df;
use chrono::{DateTime, FixedOffset, NaiveDate, NaiveDateTime, Utc};
use czsc_core::analyze::utils::format_standard_kline;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::position::Position;
use czsc_signals::registry::list_all_signals as list_all_registered_signals;
use czsc_trader::engine_v2::{ExecutionPlan, ExecutionPlanInput, UnifiedExecEngine};
use czsc_trader::optimize::{
    get_exit_optim_positions, get_open_optim_positions, symbols_optim_parallel,
};
use czsc_trader::signals::sig_parse::{SignalConfig, get_signals_config, get_signals_freqs};
use polars::prelude::*;

fn write_df_parquet(path: &Path, mut df: DataFrame) -> PyResult<()> {
    let mut file = fs::File::create(path)
        .map_err(|e| PyValueError::new_err(format!("创建输出文件失败: {e}")))?;
    ParquetWriter::new(&mut file)
        .finish(&mut df)
        .map_err(|e| PyRuntimeError::new_err(format!("写出 parquet 失败: {e}")))?;
    Ok(())
}

pub(crate) fn build_signals_dataframe(rows: &[HashMap<String, String>]) -> PyResult<DataFrame> {
    let mut keys: BTreeSet<String> = BTreeSet::new();
    for r in rows {
        keys.extend(r.keys().cloned());
    }
    if !keys.contains("cache") {
        keys.insert("cache".to_string());
    }

    let mut cols: Vec<Series> = Vec::new();
    for k in keys {
        let vals: Vec<Option<String>> = if k == "cache" {
            rows.iter().map(|_| Some("{}".to_string())).collect()
        } else {
            rows.iter().map(|r| r.get(&k).cloned()).collect()
        };
        cols.push(Series::new(k.as_str(), vals));
    }
    DataFrame::new(cols)
        .map_err(|e| PyRuntimeError::new_err(format!("构建 signals DataFrame 失败: {e}")))
}

fn align_signals_python_baseline(
    mut df: DataFrame,
    cutoff: Option<DateTime<Utc>>,
    cutoff_bar: Option<&RawBar>,
) -> PyResult<DataFrame> {
    if df.column("dt").is_ok() {
        df = df
            .lazy()
            .filter(col("dt").is_not_null())
            .collect()
            .map_err(|e| PyRuntimeError::new_err(format!("signals 过滤空 dt 失败: {e}")))?;
    }

    let Some(cutoff_bar) = cutoff_bar else {
        return Ok(df);
    };
    if cutoff.is_none() || df.height() == 0 || df.column("dt").is_err() {
        return Ok(df);
    }

    let cutoff_dt = cutoff_bar.dt.to_rfc3339();
    let dt_col = df
        .column("dt")
        .map_err(|e| PyRuntimeError::new_err(format!("读取 signals.dt 失败: {e}")))?;
    let has_cutoff = dt_col
        .str()
        .map_err(|e| PyRuntimeError::new_err(format!("signals.dt 类型错误: {e}")))?
        .into_iter()
        .any(|x| x == Some(cutoff_dt.as_str()));
    if has_cutoff {
        return Ok(df);
    }

    let mut head = df.slice(0, 1);
    let base_cols: Vec<(&str, String)> = vec![
        ("symbol", cutoff_bar.symbol.to_string()),
        ("id", cutoff_bar.id.to_string()),
        ("dt", cutoff_dt),
        ("freq", cutoff_bar.freq.to_string()),
        ("open", cutoff_bar.open.to_string()),
        ("close", cutoff_bar.close.to_string()),
        ("high", cutoff_bar.high.to_string()),
        ("low", cutoff_bar.low.to_string()),
        ("vol", cutoff_bar.vol.to_string()),
        ("amount", cutoff_bar.amount.to_string()),
        ("cache", "{}".to_string()),
    ];
    for (name, value) in base_cols {
        if head.column(name).is_ok() {
            head.with_column(Series::new(name, &[Some(value.as_str())]))
                .map_err(|e| {
                    PyRuntimeError::new_err(format!("补齐 signals 列 {name} 失败: {e}"))
                })?;
        }
    }
    head.vstack_mut(&df)
        .map_err(|e| PyRuntimeError::new_err(format!("拼接 signals 边界行失败: {e}")))?;
    Ok(head)
}

pub(crate) fn normalize_signals_dtypes(mut df: DataFrame) -> PyResult<DataFrame> {
    if df.column("dt").is_ok() {
        df = df
            .lazy()
            .with_column(
                col("dt")
                    .str()
                    .to_datetime(
                        Some(TimeUnit::Nanoseconds),
                        None,
                        StrptimeOptions {
                            format: Some("%Y-%m-%dT%H:%M:%S%.f%z".into()),
                            strict: false,
                            exact: false,
                            cache: true,
                        },
                        lit("raise"),
                    )
                    .dt()
                    .replace_time_zone(None, lit("raise"), NonExistent::Raise),
            )
            .collect()
            .map_err(|e| PyRuntimeError::new_err(format!("signals 列 dt 类型转换失败: {e}")))?;
    }
    let casts = [
        ("id", DataType::Int64),
        ("open", DataType::Float64),
        ("close", DataType::Float64),
        ("high", DataType::Float64),
        ("low", DataType::Float64),
        ("vol", DataType::Float64),
        ("amount", DataType::Float64),
    ];
    for (name, dtype) in casts {
        if df.column(name).is_ok() {
            let casted = df.column(name).and_then(|s| s.cast(&dtype)).map_err(|e| {
                PyRuntimeError::new_err(format!("signals 列 {name} 类型转换失败: {e}"))
            })?;
            df.with_column(casted)
                .map_err(|e| PyRuntimeError::new_err(format!("signals 写回列 {name} 失败: {e}")))?;
        }
    }
    Ok(df)
}

fn combine_pairs_holds_for_backtest(positions: &[Position]) -> PyResult<(DataFrame, DataFrame)> {
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

            let keep_cols: Vec<String> = ["dt", "pos", "price", "pos_name"]
                .iter()
                .filter(|c| df.column(c).is_ok())
                .map(|x| x.to_string())
                .collect();
            let refs: Vec<&str> = keep_cols.iter().map(|x| x.as_str()).collect();
            let df = df
                .select(refs)
                .map_err(|e| PyRuntimeError::new_err(format!("筛选 holds 列失败: {e}")))?;
            all_holds.push(df.lazy());
        }
    }

    let mut pairs_df = if all_pairs.is_empty() {
        DataFrame::default()
    } else {
        let mut df = concat(all_pairs, UnionArgs::default())
            .and_then(|lf| lf.collect())
            .map_err(|e| PyRuntimeError::new_err(format!("合并 pairs 失败: {e}")))?;
        let mut sort_cols = Vec::new();
        for c in ["pos_name", "开仓时间", "平仓时间"] {
            if df.column(c).is_ok() {
                sort_cols.push(c);
            }
        }
        if !sort_cols.is_empty() {
            let lf = df.lazy();
            df = lf
                .sort(sort_cols, SortMultipleOptions::default())
                .collect()
                .map_err(|e| PyRuntimeError::new_err(format!("pairs 排序失败: {e}")))?;
        }
        df
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
        let mut df = concat(all_holds, UnionArgs::default())
            .and_then(|lf| lf.collect())
            .map_err(|e| PyRuntimeError::new_err(format!("合并 holds 失败: {e}")))?;
        let mut sort_cols = Vec::new();
        for c in ["pos_name", "dt"] {
            if df.column(c).is_ok() {
                sort_cols.push(c);
            }
        }
        if !sort_cols.is_empty() {
            let lf = df.lazy();
            df = lf
                .sort(sort_cols, SortMultipleOptions::default())
                .collect()
                .map_err(|e| PyRuntimeError::new_err(format!("holds 排序失败: {e}")))?;
        }
        df
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

/// 内部从 parquet 文件读取 bars
fn read_bars_from_file(path: &Path, base_freq: Freq) -> PyResult<Vec<RawBar>> {
    let file = fs::File::open(path).map_err(|e| {
        PyValueError::new_err(format!("读取 bars 文件失败 {}: {e}", path.display()))
    })?;
    let df = ParquetReader::new(file)
        .finish()
        .map_err(|e| PyValueError::new_err(format!("解析 parquet 失败 {}: {e}", path.display())))?;
    format_standard_kline(df, base_freq).map_err(|e| {
        PyValueError::new_err(format!(
            "标准化 K 线失败 {} (freq={base_freq}): {e}",
            path.display()
        ))
    })
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

fn py_escape_str(s: &str) -> String {
    s.replace('\\', "\\\\").replace('\'', "\\'")
}

fn py_repr_list_str(items: &[String]) -> String {
    if items.is_empty() {
        return "[]".to_string();
    }
    let body = items
        .iter()
        .map(|x| format!("'{}'", py_escape_str(x)))
        .collect::<Vec<_>>()
        .join(", ");
    format!("[{body}]")
}

fn py_repr_json(v: &Value) -> String {
    match v {
        Value::Null => "None".to_string(),
        Value::Bool(b) => {
            if *b {
                "True".to_string()
            } else {
                "False".to_string()
            }
        }
        Value::Number(n) => n.to_string(),
        Value::String(s) => format!("'{}'", py_escape_str(s)),
        Value::Array(arr) => {
            let body = arr.iter().map(py_repr_json).collect::<Vec<_>>().join(", ");
            format!("[{body}]")
        }
        Value::Object(map) => {
            let body = map
                .iter()
                .map(|(k, val)| format!("'{}': {}", py_escape_str(k), py_repr_json(val)))
                .collect::<Vec<_>>()
                .join(", ");
            format!("{{{body}}}")
        }
    }
}

fn md5_upper8(s: &str) -> String {
    let digest = md5::compute(s.as_bytes());
    format!("{:x}", digest)[..8].to_uppercase()
}

fn sanitize_file_stem(name: &str) -> String {
    name.chars()
        .map(|c| match c {
            '/' | '\\' | ':' | '*' | '?' | '"' | '<' | '>' | '|' => '_',
            _ => c,
        })
        .collect()
}

fn event_to_position_file_dump(e: &czsc_core::objects::event::Event) -> Value {
    let all = e
        .signals_all
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    let any = e
        .signals_any
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    let not = e
        .signals_not
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    json!({
        "name": e.name,
        "operate": e.operate.to_chinese(),
        "signals_all": all,
        "signals_any": any,
        "signals_not": not,
    })
}

fn position_to_position_file_dump(p: &Position) -> Value {
    json!({
        "name": p.name,
        "opens": p.opens.iter().map(event_to_position_file_dump).collect::<Vec<_>>(),
        "exits": p.exits.iter().map(event_to_position_file_dump).collect::<Vec<_>>(),
        "interval": p.interval,
        "timeout": p.timeout,
        "stop_loss": p.stop_loss,
        "T0": p.t0,
    })
}

fn position_to_position_file_repr_for_md5(p: &Position) -> String {
    let event_repr = |e: &czsc_core::objects::event::Event| {
        let all = e
            .signals_all
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>();
        let any = e
            .signals_any
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>();
        let not = e
            .signals_not
            .iter()
            .map(|s| s.to_string())
            .collect::<Vec<_>>();
        format!(
            "{{'name': '{}', 'operate': '{}', 'signals_all': {}, 'signals_any': {}, 'signals_not': {}}}",
            py_escape_str(&e.name),
            py_escape_str(e.operate.to_chinese()),
            py_repr_list_str(&all),
            py_repr_list_str(&any),
            py_repr_list_str(&not),
        )
    };
    let opens = p
        .opens
        .iter()
        .map(event_repr)
        .collect::<Vec<_>>()
        .join(", ");
    let exits = p
        .exits
        .iter()
        .map(event_repr)
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "{{'name': '{}', 'opens': [{}], 'exits': [{}], 'interval': {}, 'timeout': {}, 'stop_loss': {}, 'T0': {}}}",
        py_escape_str(&p.name),
        opens,
        exits,
        p.interval,
        p.timeout,
        py_float_repr(p.stop_loss),
        if p.t0 { "True" } else { "False" },
    )
}

fn write_positions_json(positions: &[Position], out_dir: &Path) -> PyResult<()> {
    fs::create_dir_all(out_dir).map_err(|e| {
        PyValueError::new_err(format!(
            "创建 positions 目录失败 {}: {e}",
            out_dir.display()
        ))
    })?;
    for pos in positions {
        let stem = sanitize_file_stem(&pos.name);
        let file = out_dir.join(format!("{stem}.json"));
        let mut dump = position_to_position_file_dump(pos);
        let md5_repr = position_to_position_file_repr_for_md5(pos);
        let md5_val = format!("{:x}", md5::compute(md5_repr.as_bytes()));
        if let Value::Object(ref mut map) = dump {
            map.insert("md5".to_string(), Value::String(md5_val));
        }
        let content = serde_json::to_string_pretty(&dump)
            .map_err(|e| PyRuntimeError::new_err(format!("序列化 Position 失败: {e}")))?;
        fs::write(&file, content).map_err(|e| {
            PyRuntimeError::new_err(format!("写入 Position 失败 {}: {e}", file.display()))
        })?;
    }
    Ok(())
}

fn read_parquet_if_exists(path: &Path) -> PyResult<Option<DataFrame>> {
    if !path.exists() {
        return Ok(None);
    }
    let file = fs::File::open(path)
        .map_err(|e| PyValueError::new_err(format!("读取 parquet 失败 {}: {e}", path.display())))?;
    let df = ParquetReader::new(file).finish().map_err(|e| {
        PyRuntimeError::new_err(format!("解析 parquet 失败 {}: {e}", path.display()))
    })?;
    Ok(Some(df))
}

fn df_first_f64(df: &DataFrame, col_name: &str) -> Option<f64> {
    let series = df.column(col_name).ok()?;
    let casted = series.cast(&DataType::Float64).ok()?;
    let ca = casted.f64().ok()?;
    ca.get(0)
}

fn round_to(v: f64, digits: i32) -> f64 {
    if !v.is_finite() {
        return v;
    }
    let p = 10_f64.powi(digits);
    (v * p).round_ties_even() / p
}

fn mean(vals: &[f64]) -> f64 {
    if vals.is_empty() {
        return f64::NAN;
    }
    vals.iter().sum::<f64>() / vals.len() as f64
}

fn sample_std(vals: &[f64]) -> f64 {
    if vals.len() <= 1 {
        return f64::NAN;
    }
    let m = mean(vals);
    let var = vals.iter().map(|x| (x - m).powi(2)).sum::<f64>() / (vals.len() as f64 - 1.0);
    var.sqrt()
}

fn py_cap_max(v: f64, cap: f64) -> f64 {
    if v.is_nan() { f64::NAN } else { v.min(cap) }
}

fn cal_break_even_point(seq: &[f64]) -> f64 {
    if seq.is_empty() {
        return 0.0;
    }
    if seq.iter().sum::<f64>() < 0.0 {
        return 1.0;
    }
    let mut sorted = seq.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let mut csum = 0.0;
    let mut neg_cnt = 0usize;
    for v in sorted {
        csum += v;
        if csum < 0.0 {
            neg_cnt += 1;
        }
    }
    (neg_cnt as f64 + 1.0) / seq.len() as f64
}

fn py_float_repr(v: f64) -> String {
    if !v.is_finite() {
        return "0.0".to_string();
    }
    if v.fract().abs() < 1e-12 {
        format!("{v:.1}")
    } else {
        format!("{v}")
    }
}

fn event_to_opt_dump_repr(e: &czsc_core::objects::event::Event) -> String {
    let signal_kv_repr = |s: &czsc_core::objects::signal::Signal| {
        format!(
            "{{'key': '{}', 'value': '{}'}}",
            py_escape_str(&s.key()),
            py_escape_str(&s.value())
        )
    };
    let all = format!(
        "[{}]",
        e.signals_all
            .iter()
            .map(signal_kv_repr)
            .collect::<Vec<_>>()
            .join(", ")
    );
    let any = format!(
        "[{}]",
        e.signals_any
            .iter()
            .map(signal_kv_repr)
            .collect::<Vec<_>>()
            .join(", ")
    );
    let not = format!(
        "[{}]",
        e.signals_not
            .iter()
            .map(signal_kv_repr)
            .collect::<Vec<_>>()
            .join(", ")
    );
    format!(
        "{{'name': '{}', 'operate': '{}', 'signals_all': {}, 'signals_any': {}, 'signals_not': {}}}",
        py_escape_str(&e.name),
        py_escape_str(e.operate.to_chinese()),
        all,
        any,
        not,
    )
}

fn position_to_opt_dump_repr(p: &Position) -> String {
    let opens = p
        .opens
        .iter()
        .map(event_to_opt_dump_repr)
        .collect::<Vec<_>>()
        .join(", ");
    let exits = p
        .exits
        .iter()
        .map(event_to_opt_dump_repr)
        .collect::<Vec<_>>()
        .join(", ");
    format!(
        "{{'symbol': 'symbol', 'name': '{}', 'opens': [{}], 'exits': [{}], 'interval': {}, 'timeout': {}, 'stop_loss': {}, 'T0': {}, 'pairs': [], 'holds': []}}",
        py_escape_str(&p.name),
        opens,
        exits,
        p.interval,
        p.timeout,
        py_float_repr(p.stop_loss),
        if p.t0 { "True" } else { "False" },
    )
}

fn collect_optimize_report_rows(
    positions: &[Position],
    symbols: &[String],
    poss_dir: &Path,
) -> PyResult<Vec<Value>> {
    let mut rows: Vec<Value> = Vec::new();

    for pos in positions {
        let mut pair_lfs = Vec::new();
        let mut hold_lfs = Vec::new();

        for sym in symbols {
            let sym_dir = poss_dir.join(sym);
            let pairs_path = sym_dir.join(format!("{}.pairs.parquet", pos.name));
            let holds_path = sym_dir.join(format!("{}.holds.parquet", pos.name));

            if let Some(df) = read_parquet_if_exists(&pairs_path)? {
                pair_lfs.push(df.lazy());
            }
            if let Some(df) = read_parquet_if_exists(&holds_path)? {
                hold_lfs.push(df.lazy());
            }
        }

        if pair_lfs.is_empty() || hold_lfs.is_empty() {
            continue;
        }

        let pairs = concat(pair_lfs, UnionArgs::default())
            .and_then(|lf| lf.collect())
            .map_err(|e| PyRuntimeError::new_err(format!("合并 pairs 失败: {e}")))?;
        let holds = concat(hold_lfs, UnionArgs::default())
            .and_then(|lf| lf.collect())
            .map_err(|e| PyRuntimeError::new_err(format!("合并 holds 失败: {e}")))?;

        if pairs.height() == 0 || holds.height() == 0 {
            continue;
        }
        if holds.column("dt").is_err()
            || holds.column("n1b").is_err()
            || holds.column("pos").is_err()
        {
            continue;
        }

        let cross_df = holds
            .lazy()
            .group_by([col("dt")])
            .agg([
                ((col("n1b").cast(DataType::Float64) * col("pos").cast(DataType::Float64)).sum()
                    / (col("pos").neq(lit(0)).cast(DataType::Float64).sum() + lit(1.0)))
                .alias("cross_ret"),
                (col("n1b").cast(DataType::Float64) * col("pos").cast(DataType::Float64))
                    .mean()
                    .alias("cross1_ret"),
            ])
            .select([
                col("cross_ret").sum().alias("截面等权收益"),
                col("cross1_ret").sum().alias("截面品种等权"),
            ])
            .collect()
            .map_err(|e| PyRuntimeError::new_err(format!("计算截面统计失败: {e}")))?;

        let cross = df_first_f64(&cross_df, "截面等权收益").unwrap_or(0.0);
        let cross1 = df_first_f64(&cross_df, "截面品种等权").unwrap_or(0.0);
        let total_trades = pairs.height() as i64;

        let pairs_enhanced = pairs
            .lazy()
            .with_columns([
                col("开仓时间").dt().strftime("%Y-%m-%d").alias("开仓日"),
                col("开仓时间")
                    .dt()
                    .strftime("%Y-%m-%d %H:%M:%S")
                    .alias("开仓时间文本"),
                col("平仓时间")
                    .dt()
                    .strftime("%Y-%m-%d %H:%M:%S")
                    .alias("平仓时间文本"),
            ])
            .collect()
            .map_err(|e| PyRuntimeError::new_err(format!("增强 pairs 字段失败: {e}")))?;

        let profit_casted = pairs_enhanced
            .column("盈亏比例")
            .and_then(|s| s.cast(&DataType::Float64))
            .map_err(|e| PyRuntimeError::new_err(format!("读取盈亏比例失败: {e}")))?;
        let profit_ca = profit_casted
            .f64()
            .map_err(|e| PyRuntimeError::new_err(format!("盈亏比例类型错误: {e}")))?;
        let profits: Vec<f64> = profit_ca.into_iter().flatten().collect();
        if profits.is_empty() {
            continue;
        }

        let hold_days_casted = pairs_enhanced
            .column("持仓天数")
            .and_then(|s| s.cast(&DataType::Float64))
            .map_err(|e| PyRuntimeError::new_err(format!("读取持仓天数失败: {e}")))?;
        let hold_days_ca = hold_days_casted
            .f64()
            .map_err(|e| PyRuntimeError::new_err(format!("持仓天数类型错误: {e}")))?;
        let hold_days: Vec<f64> = hold_days_ca.into_iter().flatten().collect();

        let hold_bars_casted = pairs_enhanced
            .column("持仓K线数")
            .and_then(|s| s.cast(&DataType::Float64))
            .map_err(|e| PyRuntimeError::new_err(format!("读取持仓K线数失败: {e}")))?;
        let hold_bars_ca = hold_bars_casted
            .f64()
            .map_err(|e| PyRuntimeError::new_err(format!("持仓K线数类型错误: {e}")))?;
        let hold_bars: Vec<f64> = hold_bars_ca.into_iter().flatten().collect();

        let start_time = pairs_enhanced
            .column("开仓时间文本")
            .ok()
            .and_then(|s| s.str().ok())
            .and_then(|ca| ca.into_iter().flatten().map(|x| x.to_string()).min());
        let end_time = pairs_enhanced
            .column("平仓时间文本")
            .ok()
            .and_then(|s| s.str().ok())
            .and_then(|ca| ca.into_iter().flatten().map(|x| x.to_string()).max());

        let symbol_count = pairs_enhanced
            .column("标的代码")
            .ok()
            .and_then(|s| s.str().ok())
            .map(|ca| {
                let mut ss = HashSet::new();
                for x in ca.into_iter().flatten() {
                    ss.insert(x.to_string());
                }
                ss.len() as i64
            })
            .unwrap_or(0);

        let mut open_day_profit: HashMap<String, Vec<f64>> = HashMap::new();
        let open_day_ca = pairs_enhanced
            .column("开仓日")
            .and_then(|s| s.str())
            .map_err(|e| PyRuntimeError::new_err(format!("读取开仓日失败: {e}")))?;
        for i in 0..pairs_enhanced.height() {
            if let (Some(day), Some(p)) = (open_day_ca.get(i), profit_ca.get(i)) {
                open_day_profit.entry(day.to_string()).or_default().push(p);
            }
        }
        let open_day_be = if open_day_profit.is_empty() {
            0.0
        } else {
            let x = open_day_profit
                .values()
                .map(|v| cal_break_even_point(v))
                .sum::<f64>()
                / open_day_profit.len() as f64;
            round_to(x, 4)
        };

        let avg_profit = round_to(mean(&profits), 4);
        let std_profit = round_to(sample_std(&profits), 4);
        let max_profit = round_to(
            profits
                .iter()
                .copied()
                .fold(f64::NEG_INFINITY, |a, b| if a > b { a } else { b }),
            4,
        );
        let min_profit = round_to(
            profits
                .iter()
                .copied()
                .fold(f64::INFINITY, |a, b| if a < b { a } else { b }),
            4,
        );
        let win_n = profits.iter().filter(|x| **x > 0.0).count() as f64;
        let total_n = profits.len() as f64;
        let win_pct = round_to(win_n / total_n, 4);

        let gain_vals: Vec<f64> = profits.iter().copied().filter(|x| *x > 0.0).collect();
        let loss_vals: Vec<f64> = profits.iter().copied().filter(|x| *x <= 0.0).collect();
        let gain_mean = mean(&gain_vals);
        let loss_mean = mean(&loss_vals);
        let gain_sum: f64 = gain_vals.iter().sum();
        let loss_sum: f64 = loss_vals.iter().sum();
        let single_gain_loss_rate = {
            let raw = gain_mean / (loss_mean.abs() + 1e-8);
            py_cap_max(round_to(raw, 2), 5.0)
        };
        let total_gain_loss_rate = {
            let raw = gain_sum / (loss_sum.abs() + 1e-8);
            py_cap_max(round_to(raw, 2), 5.0)
        };
        let trade_score = round_to(total_gain_loss_rate * win_pct, 4);
        let edge = round_to(single_gain_loss_rate * win_pct - (1.0 - win_pct), 4);
        let break_even = round_to(cal_break_even_point(&profits), 4);
        let avg_hold_days = round_to(mean(&hold_days), 2);
        let avg_hold_bars = round_to(mean(&hold_bars), 2);
        let per_natural_day = round_to(avg_profit / avg_hold_days, 2);
        let per_bar = round_to(avg_profit / avg_hold_bars, 2);

        let pos_dump = position_to_opt_dump_repr(pos);

        rows.push(json!({
            "开始时间": start_time,
            "结束时间": end_time,
            "交易标的数量": symbol_count,
            "总体交易次数": total_trades,
            "平均持仓天数": avg_hold_days,
            "平均持仓K线数": avg_hold_bars,
            "平均单笔收益": avg_profit,
            "单笔收益标准差": std_profit,
            "最大单笔收益": max_profit,
            "最小单笔收益": min_profit,
            "交易胜率": win_pct,
            "单笔盈亏比": single_gain_loss_rate,
            "累计盈亏比": total_gain_loss_rate,
            "交易得分": trade_score,
            "赢面": edge,
            "盈亏平衡点": break_even,
            "开仓日盈亏平衡点": open_day_be,
            "每自然日收益": per_natural_day,
            "每根K线收益": per_bar,
            "截面等权收益": cross,
            "截面品种等权": cross1,
            "pos_name": pos.name,
            "pos_dump": pos_dump,
        }));
    }

    rows.sort_by(|a, b| {
        let av = a
            .get("截面等权收益")
            .and_then(Value::as_f64)
            .unwrap_or(f64::NEG_INFINITY);
        let bv = b
            .get("截面等权收益")
            .and_then(Value::as_f64)
            .unwrap_or(f64::NEG_INFINITY);
        bv.partial_cmp(&av).unwrap_or(std::cmp::Ordering::Equal)
    });

    Ok(rows)
}

fn write_optimize_report_xlsx(rows: &[Value], out_path: &Path) -> PyResult<()> {
    let mut workbook = Workbook::new();
    let worksheet = workbook.add_worksheet();

    let headers = [
        "开始时间",
        "结束时间",
        "交易标的数量",
        "总体交易次数",
        "平均持仓天数",
        "平均持仓K线数",
        "平均单笔收益",
        "单笔收益标准差",
        "最大单笔收益",
        "最小单笔收益",
        "交易胜率",
        "单笔盈亏比",
        "累计盈亏比",
        "交易得分",
        "赢面",
        "盈亏平衡点",
        "开仓日盈亏平衡点",
        "每自然日收益",
        "每根K线收益",
        "截面等权收益",
        "截面品种等权",
        "pos_name",
        "pos_dump",
    ];

    for (c, h) in headers.iter().enumerate() {
        worksheet
            .write_string(0, c as u16, *h)
            .map_err(|e| PyRuntimeError::new_err(format!("写入 xlsx 表头失败: {e}")))?;
    }

    for (r, row) in rows.iter().enumerate() {
        let rr = (r + 1) as u32;
        for (c, h) in headers.iter().enumerate() {
            let cc = c as u16;
            let v = row.get(*h).unwrap_or(&Value::Null);
            match v {
                Value::Null => {}
                Value::Bool(b) => {
                    worksheet.write_boolean(rr, cc, *b).map_err(|e| {
                        PyRuntimeError::new_err(format!("写入 xlsx 布尔值失败: {e}"))
                    })?;
                }
                Value::Number(n) => {
                    if let Some(f) = n.as_f64() {
                        worksheet.write_number(rr, cc, f).map_err(|e| {
                            PyRuntimeError::new_err(format!("写入 xlsx 数值失败: {e}"))
                        })?;
                    } else {
                        worksheet.write_string(rr, cc, n.to_string()).map_err(|e| {
                            PyRuntimeError::new_err(format!("写入 xlsx 字符串数值失败: {e}"))
                        })?;
                    }
                }
                Value::String(s) => {
                    worksheet.write_string(rr, cc, s).map_err(|e| {
                        PyRuntimeError::new_err(format!("写入 xlsx 字符串失败: {e}"))
                    })?;
                }
                _ => {
                    let s = serde_json::to_string(v).map_err(|e| {
                        PyRuntimeError::new_err(format!("序列化 xlsx 单元格失败: {e}"))
                    })?;
                    worksheet.write_string(rr, cc, s).map_err(|e| {
                        PyRuntimeError::new_err(format!("写入 xlsx JSON 字符串失败: {e}"))
                    })?;
                }
            }
        }
    }

    workbook
        .save(out_path)
        .map_err(|e| PyRuntimeError::new_err(format!("写入 xlsx 失败: {e}")))
}

/// 运行批量优化任务。
///
/// Python 侧通常不会直接构造 Rust `ExecutionPlan`，而是先准备：
/// - `bars_dir`: 每个 symbol 一个 parquet 文件的目录，文件名形如 `{symbol}.parquet`
/// - `config_path`: 优化任务 JSON 配置文件，包含 `optim_type / symbols / files_position`
/// - `res_path`: 输出根目录，函数内部会按 task hash 创建子目录
///
/// 返回值是简短的文本摘要，包含任务目录和报表路径；详细产物会落到磁盘。
#[pyfunction]
#[pyo3(text_signature = "(bars_dir, config_path, res_path, n_threads=1)")]
#[pyo3(signature = (bars_dir, config_path, res_path, n_threads=1))]
pub fn run_optimize(
    bars_dir: &str,
    config_path: &str,
    res_path: &str,
    n_threads: usize,
) -> PyResult<String> {
    let config_content = fs::read_to_string(config_path)
        .map_err(|e| PyValueError::new_err(format!("读取 config 错误: {e}")))?;

    let config: Value = serde_json::from_str(&config_content)
        .map_err(|e| PyValueError::new_err(format!("解析 config 错误: {e}")))?;

    let optim_type = config["optim_type"].as_str().unwrap_or("open");
    let base_freq_str = config["base_freq"].as_str().unwrap_or("日线");
    let base_freq = base_freq_str
        .parse::<Freq>()
        .map_err(|_| PyValueError::new_err("解析 base_freq 失败"))?;
    let market = config["market"].as_str();
    let bg_max_count = config["bg_max_count"].as_u64().map(|x| x as usize);
    let symbols_val = config["symbols"]
        .as_array()
        .ok_or_else(|| PyValueError::new_err("缺少 symbols 参数"))?;

    let mut symbols = Vec::new();
    for s in symbols_val {
        symbols.push(s.as_str().unwrap().to_string());
    }

    let task_name = config["task_name"]
        .as_str()
        .map(|s| s.to_string())
        .unwrap_or_else(|| {
            if optim_type == "open" {
                "入场优化".to_string()
            } else {
                "出场优化".to_string()
            }
        });

    let files_position: Vec<PathBuf> = config["files_position"]
        .as_array()
        .unwrap_or(&vec![])
        .iter()
        .map(|v| PathBuf::from(v.as_str().unwrap()))
        .collect();

    let (positions, task_hash) = if optim_type == "open" {
        let mut candidate_sigs: Vec<String> = config["candidate_signals"]
            .as_array()
            .unwrap_or(&vec![])
            .iter()
            .map(|v| v.as_str().unwrap().to_string())
            .collect();
        candidate_sigs.sort();
        let mut sorted_symbols = symbols.clone();
        sorted_symbols.sort();
        let digest = md5_upper8(&format!(
            "{}_{}",
            py_repr_list_str(&candidate_sigs),
            py_repr_list_str(&sorted_symbols)
        ));
        (
            get_open_optim_positions(&files_position, &candidate_sigs)
                .map_err(|e| PyValueError::new_err(format!("生成开仓策略错误: {:?}", e)))?,
            digest,
        )
    } else {
        let candidate_events = config["candidate_events"]
            .as_array()
            .unwrap_or(&vec![])
            .clone();
        let digest = md5_upper8(&format!(
            "{}_{}",
            py_repr_json(&Value::Array(candidate_events.clone())),
            py_repr_list_str(&symbols)
        ));
        (
            get_exit_optim_positions(&files_position, &candidate_events)
                .map_err(|e| PyValueError::new_err(format!("生成平仓策略错误: {:?}", e)))?,
            digest,
        )
    };

    let task_dir = Path::new(res_path).join(format!("{task_name}_{task_hash}"));
    let poss_dir = task_dir.join("poss");
    let positions_dir = task_dir.join("positions");
    fs::create_dir_all(&poss_dir).map_err(|e| {
        PyValueError::new_err(format!("创建结果目录失败 {}: {e}", poss_dir.display()))
    })?;
    write_positions_json(&positions, &positions_dir)?;

    let mut bars_map = HashMap::new();
    for sym in &symbols {
        let file_path = Path::new(bars_dir).join(format!("{}.parquet", sym));
        if file_path.exists() {
            let bars = read_bars_from_file(&file_path, base_freq)?;
            bars_map.insert(sym.clone(), bars);
        }
    }

    let sdt_cutoff = config["sdt"]
        .as_str()
        .and_then(parse_sdt_utc)
        .and_then(|dt| FixedOffset::east_opt(0).map(|tz| dt.with_timezone(&tz)));

    symbols_optim_parallel(
        symbols.clone(),
        bars_map,
        positions.clone(),
        &poss_dir,
        base_freq_str,
        market,
        bg_max_count,
        sdt_cutoff,
        n_threads,
    );

    let report_rows = collect_optimize_report_rows(&positions, &symbols, &poss_dir)?;
    let report_prefix = if optim_type == "open" {
        "入场优化"
    } else {
        "出场优化"
    };
    let report_path = task_dir.join(format!("{report_prefix}_{task_name}_{task_hash}.xlsx"));
    if !report_rows.is_empty() {
        write_optimize_report_xlsx(&report_rows, &report_path)?;
    }

    Ok(format!(
        "跑批完成: task_dir={}, report={}",
        task_dir.display(),
        if report_rows.is_empty() {
            "NONE".to_string()
        } else {
            report_path.display().to_string()
        }
    ))
}

#[allow(unused_variables)]
/// 执行一次单标的回测并将 `signals / pairs / holds` 落盘到指定目录。
///
/// 参数约定：
/// - `bars_bytes`: Python `pyarrow` 序列化后的 Arrow bytes
/// - `config_path`: 与 Python `czsc` 风格兼容的策略 JSON 文件
/// - `res_path`: 结果目录，函数会写出三个 parquet 文件
/// - `opts`: 兼容保留字段，当前未使用
///
/// 这个入口适合“本地一次性回测并保留产物”的场景；如果只想拿内存结果，
/// 优先使用 `run_research` / `run_replay`。
#[pyfunction]
#[pyo3(text_signature = "(bars_bytes, config_path, res_path, opts='')")]
#[pyo3(signature = (bars_bytes, config_path, res_path, opts=""))]
pub fn run_backtest(
    py: Python,
    bars_bytes: &Bound<PyBytes>,
    config_path: &str,
    res_path: &str,
    opts: &str,
) -> PyResult<String> {
    // 1. 加载配置
    let config_content = fs::read_to_string(config_path)
        .map_err(|e| PyValueError::new_err(format!("读取 config 错误: {e}")))?;
    let config: Value = serde_json::from_str(&config_content)
        .map_err(|e| PyValueError::new_err(format!("解析 config 错误: {e}")))?;

    let base_freq = config["base_freq"]
        .as_str()
        .unwrap_or("日线")
        .parse::<Freq>()
        .map_err(|_| PyValueError::new_err("解析 base_freq 失败"))?;

    // 2. 解析 DataFrame 拿到 bars
    let raw_data = bars_bytes.as_bytes();
    let df = pyarrow_to_df(raw_data)
        .map_err(|e| PyValueError::new_err(format!("Arrow bytes 转 DataFrame 失败: {e}")))?;

    let bars = format_standard_kline(df, base_freq)
        .map_err(|e| PyValueError::new_err(format!("K线标准化格式错误: {e}")))?;

    // 3. 读取策略与信号配置
    let signals_config: Vec<SignalConfig> = if let Some(cfgs) = config["signals_config"].as_array()
    {
        let s = serde_json::to_string(cfgs).unwrap();
        serde_json::from_str(&s).unwrap()
    } else {
        vec![]
    };

    let positions_val = config["positions"]
        .as_array()
        .ok_or_else(|| PyValueError::new_err("缺少 positions 配置"))?;

    let mut positions: Vec<Position> = Vec::new();
    for p_val in positions_val {
        let p_str = serde_json::to_string(p_val).unwrap();
        let pos: Position = serde_json::from_str(&p_str)
            .map_err(|e| PyValueError::new_err(format!("Position 解析错误: {e}")))?;
        positions.push(pos);
    }

    // 4. 构建统一执行计划
    let symbol = config["symbols"]
        .as_array()
        .and_then(|arr| arr.first())
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN")
        .to_string();
    let market = config["market"].as_str().map(|x| x.to_string());
    let sdt = config["sdt"].as_str().map(|x| x.to_string());
    let bg_max_count = config["bg_max_count"].as_u64().map(|x| x as usize);
    let plan_input = ExecutionPlanInput {
        symbol: symbol.clone(),
        base_freq: base_freq.to_string(),
        signals_config,
        positions,
        market,
        bg_max_count,
        sdt,
        include_sdt_bar: config["include_sdt_bar"].as_bool(),
    };
    let plan = ExecutionPlan::compile(plan_input)
        .map_err(|e| PyValueError::new_err(format!("ExecutionPlan 编译失败: {e}")))?;
    let cutoff = plan.sdt.as_deref().and_then(parse_sdt_utc);
    let cutoff_bar = cutoff.and_then(|c| bars.iter().find(|b| b.dt == c).cloned());
    let output = UnifiedExecEngine::run(&plan, bars, None, true, false)
        .map_err(|e| PyValueError::new_err(format!("UnifiedExecEngine 执行失败: {e}")))?;
    let rows = output.signal_rows;
    let positions = output.positions;

    // 5. 执行结果统计
    let mut total_pairs = 0;
    for pos in &positions {
        if let Ok(df) = pos.pairs() {
            total_pairs += df.height();
        }
    }
    println!(
        ">>> (RUST) 回放结束。最终所有仓位共产生完毕交易流水 Pairs 的条数为: {}",
        total_pairs
    );

    // 6. 存储结果
    let res_dir = Path::new(res_path);
    if !res_dir.exists() {
        fs::create_dir_all(res_dir).map_err(|e| PyValueError::new_err(e.to_string()))?;
    }

    let mut signals_df = build_signals_dataframe(&rows)?;
    signals_df = align_signals_python_baseline(signals_df, cutoff, cutoff_bar.as_ref())?;
    if signals_df.column("dt").is_ok() {
        signals_df = signals_df
            .lazy()
            .sort(["dt"], SortMultipleOptions::default())
            .collect()
            .map_err(|e| PyRuntimeError::new_err(format!("signals 排序失败: {e}")))?;
    }
    signals_df = normalize_signals_dtypes(signals_df)?;
    let (pairs_df, holds_df) = combine_pairs_holds_for_backtest(&positions)?;

    write_df_parquet(&res_dir.join("signals.parquet"), signals_df)?;
    write_df_parquet(&res_dir.join("pairs.parquet"), pairs_df)?;
    write_df_parquet(&res_dir.join("holds.parquet"), holds_df)?;

    Ok("单次回测完成".to_string())
}

#[allow(unused_variables)]
/// 仅生成信号明细，不执行完整交易统计。
///
/// 这个入口对应 Python `generate_czsc_signals` 风格用法：
/// - 从 Arrow bytes 读取 bars
/// - 根据 `signals_config` 构建统一执行计划
/// - 输出 `signals.parquet`
///
/// 当 `positions` 为空时，内部会注入 `__signals_only__` 占位仓位，以复用统一执行引擎。
/// `sdt` 参数会覆盖配置中的 `sdt`，常用于信号矩阵或基准对比。
#[pyfunction]
#[pyo3(text_signature = "(bars_bytes, config_path, out_path, sdt='')")]
#[pyo3(signature = (bars_bytes, config_path, out_path, sdt=""))]
pub fn generate_signals(
    py: Python,
    bars_bytes: &Bound<PyBytes>,
    config_path: &str,
    out_path: &str,
    sdt: &str,
) -> PyResult<()> {
    // 1) 读取配置
    let config_content = fs::read_to_string(config_path)
        .map_err(|e| PyValueError::new_err(format!("读取 config 错误: {e}")))?;
    let config: Value = serde_json::from_str(&config_content)
        .map_err(|e| PyValueError::new_err(format!("解析 config 错误: {e}")))?;

    let base_freq = config["base_freq"]
        .as_str()
        .unwrap_or("日线")
        .parse::<Freq>()
        .map_err(|_| PyValueError::new_err("解析 base_freq 失败"))?;

    let signals_config: Vec<SignalConfig> = if let Some(cfgs) = config["signals_config"].as_array()
    {
        let s = serde_json::to_string(cfgs).unwrap();
        serde_json::from_str(&s).unwrap_or_default()
    } else {
        vec![]
    };

    // 2) Arrow bytes -> bars
    let raw_data = bars_bytes.as_bytes();
    let df = pyarrow_to_df(raw_data)
        .map_err(|e| PyValueError::new_err(format!("Arrow bytes 转 DataFrame 失败: {e}")))?;
    let bars = format_standard_kline(df, base_freq)
        .map_err(|e| PyValueError::new_err(format!("K线标准化格式错误: {e}")))?;

    // 3) 构建执行计划并执行
    let symbol = config["symbols"]
        .as_array()
        .and_then(|arr| arr.first())
        .and_then(|v| v.as_str())
        .unwrap_or("UNKNOWN")
        .to_string();
    let mut positions: Vec<Position> = if let Some(arr) = config["positions"].as_array() {
        let mut out = Vec::with_capacity(arr.len());
        for p_val in arr {
            let p_str = serde_json::to_string(p_val).unwrap();
            let pos: Position = serde_json::from_str(&p_str)
                .map_err(|e| PyValueError::new_err(format!("Position 解析错误: {e}")))?;
            out.push(pos);
        }
        out
    } else {
        vec![]
    };
    // generate_signals 允许无仓位场景：注入一个无事件占位仓位以复用统一执行引擎
    if positions.is_empty() {
        let stub: Position = serde_json::from_value(serde_json::json!({
            "name": "__signals_only__",
            "symbol": symbol,
            "opens": [],
            "exits": [],
            "interval": 0,
            "timeout": 1,
            "stop_loss": 1000.0,
            "T0": false
        }))
        .map_err(|e| PyValueError::new_err(format!("构建 signals-only 占位 Position 失败: {e}")))?;
        positions.push(stub);
    }
    let plan = ExecutionPlan::compile(ExecutionPlanInput {
        symbol,
        base_freq: base_freq.to_string(),
        signals_config,
        positions,
        market: config["market"].as_str().map(|x| x.to_string()),
        bg_max_count: config["bg_max_count"].as_u64().map(|x| x as usize),
        sdt: config["sdt"].as_str().map(|x| x.to_string()),
        include_sdt_bar: config["include_sdt_bar"].as_bool(),
    })
    .map_err(|e| PyValueError::new_err(format!("ExecutionPlan 编译失败: {e}")))?;
    let sdt_override = if sdt.is_empty() { None } else { Some(sdt) };
    let output = UnifiedExecEngine::run(&plan, bars, sdt_override, true, false)
        .map_err(|e| PyRuntimeError::new_err(format!("UnifiedExecEngine 执行失败: {e}")))?;
    let rows = output.signal_rows;

    // 4) 行转列，写 parquet
    let mut out_df = build_signals_dataframe(&rows)?;
    out_df = normalize_signals_dtypes(out_df)?;

    let out = Path::new(out_path);
    let file_path = if out.extension().is_some() {
        out.to_path_buf()
    } else {
        if !out.exists() {
            fs::create_dir_all(out).map_err(|e| PyValueError::new_err(e.to_string()))?;
        }
        out.join("signals.parquet")
    };
    let mut file = fs::File::create(&file_path)
        .map_err(|e| PyValueError::new_err(format!("创建输出文件失败: {e}")))?;
    ParquetWriter::new(&mut file)
        .finish(&mut out_df)
        .map_err(|e| PyValueError::new_err(format!("写出 parquet 失败: {e}")))?;

    Ok(())
}

/// 返回所有已注册信号函数的只读元信息。
///
/// 每个元素都是一个 `dict`，包含：
/// - `name`: 信号函数名
/// - `param_template`: 参数模板
/// - `category`: `kline` 或 `trader`
/// - `namespace`: 命名空间前缀，如 `bar / tas / cxt / pos`
///
/// 常用于：
/// - 构建 parity 覆盖矩阵
/// - 生成文档或自动补全
/// - 检查 Rust / Python 共享信号交集
#[pyfunction]
#[pyo3(text_signature = "(include_kline=True, include_trader=True)")]
#[pyo3(signature = (include_kline=true, include_trader=true))]
pub fn list_all_signals(
    py: Python<'_>,
    include_kline: bool,
    include_trader: bool,
) -> PyResult<Py<PyList>> {
    let infos = list_all_registered_signals(include_kline, include_trader);
    let list = PyList::empty(py);
    for it in infos {
        let d = PyDict::new(py);
        d.set_item("name", it.name)?;
        d.set_item("param_template", it.param_template)?;
        d.set_item("category", it.category)?;
        d.set_item("namespace", it.namespace)?;
        list.append(d)?;
    }
    Ok(list.unbind())
}

/// 从 `unique_signals` 反推出 Rust 运行时 `signals_config`。
///
/// 这是 PyO3 暴露给 Python 兼容层的核心反解析入口：
/// - 输入：信号字符串列表，例如 `['60分钟_D1SMA#5_分类V221101_多头_向上_任意_0']`
/// - 输出：可直接放入策略 JSON 的 `list[dict]`
///
/// 这个函数依赖 Rust 注册表中的 `param_template` 做反解析，因此适合：
/// - `CzscStrategyBase.unique_signals -> signals_config`
/// - parity benchmark 中的 same-source import-swap 场景
#[pyfunction]
#[pyo3(text_signature = "(unique_signals)")]
#[pyo3(signature = (unique_signals))]
pub fn derive_signals_config(py: Python<'_>, unique_signals: Vec<String>) -> PyResult<PyObject> {
    let refs: Vec<&str> = unique_signals.iter().map(String::as_str).collect();
    let configs = get_signals_config(&refs);
    let json_str = serde_json::to_string(&configs)
        .map_err(|e| PyRuntimeError::new_err(format!("序列化 signals_config 失败: {e}")))?;
    let json_mod = py.import("json")?;
    Ok(json_mod.call_method1("loads", (json_str,))?.unbind())
}

/// 从 `signals_config` 中提取执行所需的全部周期列表。
///
/// 返回结果已经按 `czsc` 习惯的中文周期顺序排序，而不是字典序。
/// 这个入口通常给 Python 兼容层用于自动填充：
/// - `freqs`
/// - `sorted_freqs`
/// - `base_freq` 推导前的候选周期集合
#[pyfunction]
#[pyo3(text_signature = "(signals_config)")]
#[pyo3(signature = (signals_config))]
pub fn derive_signals_freqs(py: Python<'_>, signals_config: PyObject) -> PyResult<Vec<String>> {
    let json_mod = py.import("json")?;
    let json_str = json_mod
        .call_method1("dumps", (signals_config,))?
        .extract::<String>()?;
    let configs: Vec<SignalConfig> = serde_json::from_str(&json_str)
        .map_err(|e| PyValueError::new_err(format!("signals_config 解析失败: {e}")))?;
    Ok(get_signals_freqs(&configs))
}

#[cfg(test)]
mod tests {
    use super::parse_sdt_utc;

    #[test]
    fn test_parse_sdt_utc_supports_iso_t_without_tz() {
        let dt = parse_sdt_utc("2023-02-28T12:00:00");
        assert!(dt.is_some());
    }

    #[test]
    fn test_parse_sdt_utc_supports_iso_t_with_fractional() {
        let dt = parse_sdt_utc("2023-02-28T12:00:00.123456");
        assert!(dt.is_some());
    }
}
