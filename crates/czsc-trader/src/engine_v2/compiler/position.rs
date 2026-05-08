use czsc_core::objects::position::Position;

#[derive(Debug, Clone)]
pub struct CompiledPosition {
    pub name: String,
    pub interval: i64,
    pub timeout: i32,
    pub stop_loss: f64,
    pub event_count: usize,
}

#[derive(Debug, Clone, Default)]
pub struct CompiledPositionPlan {
    pub positions: Vec<CompiledPosition>,
}

pub fn compile_positions(positions: &[Position]) -> CompiledPositionPlan {
    let positions = positions
        .iter()
        .map(|p| CompiledPosition {
            name: p.name.clone(),
            interval: p.interval,
            timeout: p.timeout,
            stop_loss: p.stop_loss,
            event_count: p.opens.len() + p.exits.len(),
        })
        .collect();
    CompiledPositionPlan { positions }
}
