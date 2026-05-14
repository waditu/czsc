use crate::engine_v2::scheduler::split_positions_into_chunks;
use crate::engine_v2::{ExecutionPlan, ExecutionPlanInput, UnifiedExecEngine};
use crate::sig_parse::{SignalConfig, get_signals_config};
use anyhow::{Context, Result};
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::event::Event;
use czsc_core::objects::operate::Operate;
use czsc_core::objects::position::{Position, load_position};
use czsc_core::objects::signal::Signal;
use log::{info, warn};
use md5;
use polars::prelude::*;
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

/// 获取一根信号配置的哈希值前8位（对齐 Python MD5 算法）
fn hash_str(val: &str) -> String {
    let digest = md5::compute(val.as_bytes());
    format!("{:x}", digest)[..8].to_uppercase()
}

/// Python `str(list[dict])` 风格，用于与 `hashlib.md5(f\"{obj}\")` 对齐
fn py_repr_signal_kv(sig_key: &str, sig_val: &str) -> String {
    let k = sig_key.replace('\'', "\\'");
    let v = sig_val.replace('\'', "\\'");
    format!("[{{'key': '{k}', 'value': '{v}'}}]")
}

fn py_repr_list_str(items: &[String]) -> String {
    if items.is_empty() {
        "[]".to_string()
    } else {
        let body = items
            .iter()
            .map(|x| format!("'{}'", x.replace('\'', "\\'")))
            .collect::<Vec<_>>()
            .join(", ");
        format!("[{body}]")
    }
}

fn py_repr_event_dump(event: &Event) -> String {
    let name = py_event_name(event).replace('\'', "\\'");
    let operate = event.operate.to_chinese().replace('\'', "\\'");
    let all = event
        .signals_all
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    let any = event
        .signals_any
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    let not = event
        .signals_not
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    format!(
        "{{'name': '{name}', 'operate': '{operate}', 'signals_all': {}, 'signals_any': {}, 'signals_not': {}}}",
        py_repr_list_str(&all),
        py_repr_list_str(&any),
        py_repr_list_str(&not),
    )
}

fn py_event_name(event: &Event) -> String {
    let operate = event.operate.to_chinese();
    let all = event
        .signals_all
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    let any = event
        .signals_any
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    let not = event
        .signals_not
        .iter()
        .map(|s| s.to_string())
        .collect::<Vec<_>>();
    let repr = format!(
        "{{'operate': '{}', 'signals_all': {}, 'signals_any': {}, 'signals_not': {}}}",
        operate.replace('\'', "\\'"),
        py_repr_list_str(&all),
        py_repr_list_str(&any),
        py_repr_list_str(&not),
    );
    let mut hasher = Sha256::new();
    hasher.update(repr.as_bytes());
    let hex = hex::encode(hasher.finalize()).to_uppercase();
    let sha4 = &hex[..4];
    let auto_name_prefix = matches!(
        event.operate,
        Operate::LE | Operate::SE | Operate::LO | Operate::SO
    ) && event
        .name
        .split('#')
        .next()
        .map(|x| matches!(x, "LE" | "SE" | "LO" | "SO"))
        .unwrap_or(false);
    let base = if event.name.is_empty() || auto_name_prefix {
        operate.to_string()
    } else {
        event.name.split('#').next().unwrap_or(operate).to_string()
    };
    format!("{base}#{sha4}")
}

/// 开仓优化：构建并返回新的候选策略集合
pub fn get_open_optim_positions(
    files_position: &[PathBuf],
    candidate_signals: &[String],
) -> Result<Vec<Position>> {
    let mut betas = Vec::new();
    for p in files_position {
        betas.push(load_position(p).with_context(|| format!("加载 {:?}", p))?);
    }

    let mut pos_list = betas.clone();
    for beta in betas {
        for sig_str in candidate_signals {
            let mut pos = beta.clone();
            if let Ok(sig) = sig_str.parse::<Signal>()
                && !pos.opens.is_empty()
            {
                let mut open_event = pos.opens[0].clone();
                open_event.signals_all.push(sig);
                open_event.name = py_event_name(&open_event);

                // 对齐 Python: str([{"key": ..., "value": ...}]) 格式
                let sig_key = open_event.signals_all.last().unwrap().key();
                let sig_val = open_event.signals_all.last().unwrap().value();
                let sigs_repr = py_repr_signal_kv(&sig_key, &sig_val);

                let hash = hash_str(&sigs_repr);
                pos.name = format!("{}#{}", beta.name, hash);
                pos.opens[0] = open_event;
                pos_list.push(pos);
            }
        }
    }

    Ok(pos_list)
}

/// 平仓优化：构建并返回新的候选策略集合
pub fn get_exit_optim_positions(
    files_position: &[PathBuf],
    candidate_events: &[serde_json::Value],
) -> Result<Vec<Position>> {
    let mut betas = Vec::new();
    for p in files_position {
        betas.push(load_position(p).with_context(|| format!("加载 {:?}", p))?);
    }

    let mut pos_list = betas.clone();
    for beta in betas {
        let is_all_lo = beta.opens.iter().all(|x| x.operate == Operate::LO);
        let is_all_so = beta.opens.iter().all(|x| x.operate == Operate::SO);

        for event_val in candidate_events {
            if let Ok(mut event) = Event::load(event_val) {
                event.name = py_event_name(&event);
                if is_all_lo && event.operate != Operate::LE {
                    continue;
                }
                if is_all_so && event.operate != Operate::SE {
                    continue;
                }

                let event_str = py_repr_event_dump(&event);
                let hash = hash_str(&event_str);

                // mode = append（追加模式）
                let mut pos_append = beta.clone();
                pos_append.exits.push(event.clone());
                pos_append.name = format!("{}#追加{}", beta.name, hash);
                pos_list.push(pos_append);

                // mode = replace（替换模式）
                let mut pos_replace = beta.clone();
                pos_replace.exits = vec![event.clone()];
                pos_replace.name = format!("{}#替换{}", beta.name, hash);
                pos_list.push(pos_replace);
            }
        }
    }

    Ok(pos_list)
}

/// 提取所有需要的 unique signals 并转换为 SignalConfig
fn extract_signals_config(positions: &[Position]) -> Vec<SignalConfig> {
    let mut unique_sigs = HashSet::new();
    for pos in positions {
        for ev in &pos.opens {
            for s in ev.all_signals() {
                unique_sigs.insert(s.to_string());
            }
        }
        for ev in &pos.exits {
            for s in ev.all_signals() {
                unique_sigs.insert(s.to_string());
            }
        }
    }
    let sigs: Vec<&str> = unique_sigs.iter().map(|s| s.as_str()).collect();
    get_signals_config(&sigs)
}

/// 针对单个标的运行批量并行策略优化
#[allow(clippy::too_many_arguments)]
pub fn one_symbol_optim(
    symbol: &str,
    bars: &[RawBar],
    positions: Vec<Position>,
    out_dir: &Path,
    base_freq: &str,
    market: Option<&str>,
    bg_max_count: Option<usize>,
    sdt_cutoff: Option<chrono::DateTime<chrono::FixedOffset>>,
) -> Result<()> {
    let symbol_dir = out_dir.join(symbol);
    fs::create_dir_all(&symbol_dir)?;

    if bars.len() < 100 {
        warn!("{} K线数量不足，无法跑批", symbol);
        return Ok(());
    }

    let config = extract_signals_config(&positions);

    let start_time = std::time::Instant::now();
    let sdt_override = sdt_cutoff.map(|x| x.to_rfc3339());
    let plan = ExecutionPlan::compile(ExecutionPlanInput {
        symbol: symbol.to_string(),
        base_freq: base_freq.to_string(),
        signals_config: config,
        positions: positions.clone(),
        market: market.map(|x| x.to_string()),
        bg_max_count,
        sdt: sdt_override.clone(),
        include_sdt_bar: None,
    })
    .map_err(anyhow::Error::msg)?;
    let output =
        UnifiedExecEngine::run(&plan, bars.to_vec(), sdt_override.as_deref(), false, false)
            .map_err(anyhow::Error::msg)?;
    let optimized_positions = output.positions;

    // 落盘
    for pos in &optimized_positions {
        let name = &pos.name;
        if let Ok(mut df) = pos.pairs() {
            let file_path = symbol_dir.join(format!("{}.pairs.parquet", name));
            let mut file = fs::File::create(&file_path)?;
            ParquetWriter::new(&mut file).finish(&mut df)?;
        }
        if let Ok(mut df) = pos.holds() {
            if df.height() > 0 {
                // 对齐 Python: n1b 最后一行 NaN/Null 填充为 0.0
                if let Ok(n1b_col) = df.column("n1b") {
                    let n1b = n1b_col.cast(&DataType::Float64)?;
                    let n1b = n1b.fill_null(FillNullStrategy::Zero)?;
                    let _ = df.with_column(n1b);
                }
                let s_sym = Series::new("symbol".into(), vec![symbol; df.height()]);
                let _ = df.with_column(s_sym);
            }

            let file_path = symbol_dir.join(format!("{}.holds.parquet", name));
            let mut file = fs::File::create(&file_path)?;
            ParquetWriter::new(&mut file).finish(&mut df)?;
        }
    }

    info!("{} 跑批完成，耗时 {:?}", symbol, start_time.elapsed());

    Ok(())
}

/// 并行计算所有 symbol
#[allow(clippy::too_many_arguments)]
pub fn symbols_optim_parallel(
    symbols: Vec<String>,
    bars_map: HashMap<String, Vec<RawBar>>, // memory 传入全量 K线 (或者传入回调自己读取)
    positions: Vec<Position>,
    out_dir: &Path,
    base_freq: &str,
    market: Option<&str>,
    bg_max_count: Option<usize>,
    sdt_cutoff: Option<chrono::DateTime<chrono::FixedOffset>>,
    n_threads: usize,
) {
    let chunks = split_positions_into_chunks(&positions, 16);

    // 单线程下避免 rayon 嵌套并行，防止在某些环境出现卡住
    if n_threads == 1 {
        for sym in symbols {
            if let Some(bars) = bars_map.get(&sym) {
                if chunks.len() <= 1 {
                    let _ = one_symbol_optim(
                        &sym,
                        bars.as_slice(),
                        positions.clone(),
                        out_dir,
                        base_freq,
                        market,
                        bg_max_count,
                        sdt_cutoff,
                    );
                } else {
                    for chunk_pos in &chunks {
                        let _ = one_symbol_optim(
                            &sym,
                            bars.as_slice(),
                            chunk_pos.clone(),
                            out_dir,
                            base_freq,
                            market,
                            bg_max_count,
                            sdt_cutoff,
                        );
                    }
                }
            }
        }
        return;
    }

    let run = || {
        symbols.into_par_iter().for_each(|sym| {
            if let Some(bars) = bars_map.get(&sym) {
                if chunks.len() <= 1 {
                    let _ = one_symbol_optim(
                        &sym,
                        bars.as_slice(),
                        positions.clone(),
                        out_dir,
                        base_freq,
                        market,
                        bg_max_count,
                        sdt_cutoff,
                    );
                } else {
                    chunks.par_iter().for_each(|chunk_pos| {
                        let _ = one_symbol_optim(
                            &sym,
                            bars.as_slice(),
                            chunk_pos.clone(),
                            out_dir,
                            base_freq,
                            market,
                            bg_max_count,
                            sdt_cutoff,
                        );
                    });
                }
            }
        })
    };

    if n_threads > 0 {
        match rayon::ThreadPoolBuilder::new()
            .num_threads(n_threads)
            .build()
        {
            Ok(pool) => pool.install(run),
            Err(err) => {
                warn!("构建 rayon 线程池失败，回退默认线程池: {err}");
                run();
            }
        }
    } else {
        run();
    }
}
