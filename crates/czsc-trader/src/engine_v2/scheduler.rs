use crate::engine_v2::compiler::ExecutionPlan;
use crate::engine_v2::compiler::optimize::build_candidate_chunks;
use crate::engine_v2::runtime::{RunOutput, UnifiedExecEngine};
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::position::Position;
use rayon::prelude::*;

pub struct SymbolTask {
    pub symbol: String,
    pub bars: Vec<RawBar>,
    pub plan: ExecutionPlan,
}

pub struct SymbolResult {
    pub symbol: String,
    pub output: Result<RunOutput, String>,
}

pub fn run_symbol_parallel(tasks: Vec<SymbolTask>, emit_signals: bool) -> Vec<SymbolResult> {
    let mut out: Vec<SymbolResult> = tasks
        .into_par_iter()
        .map(|task| SymbolResult {
            symbol: task.symbol,
            output: UnifiedExecEngine::run(&task.plan, task.bars, None, emit_signals, false),
        })
        .collect();
    out.sort_by(|a, b| a.symbol.cmp(&b.symbol));
    out
}

pub fn split_positions_into_chunks(
    positions: &[Position],
    chunk_size: usize,
) -> Vec<Vec<Position>> {
    let chunks = build_candidate_chunks(positions.len(), chunk_size);
    chunks
        .into_iter()
        .map(|c| positions[c.start..c.end].to_vec())
        .collect()
}
