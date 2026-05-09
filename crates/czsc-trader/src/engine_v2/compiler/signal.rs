use crate::engine_v2::catalog::{CatalogSignal, SignalCategory};
use crate::sig_parse::SignalConfig;
use serde_json::Value;
use std::collections::BTreeMap;

#[derive(Debug, Clone)]
pub struct CompiledSignal {
    pub signal_id: u32,
    pub name: String,
    pub freq: Option<String>,
    pub category: SignalCategory,
    pub params: Value,
}

#[derive(Debug, Clone, Default)]
pub struct CompiledSignalPlan {
    pub ops: Vec<CompiledSignal>,
    pub id_by_name: BTreeMap<String, u32>,
}

pub fn compile_signals(
    configs: &[SignalConfig],
    catalog: &[CatalogSignal],
) -> Result<CompiledSignalPlan, String> {
    if configs.len() != catalog.len() {
        return Err("signals_config 与 catalog_signals 数量不一致".to_string());
    }

    let mut id_by_name: BTreeMap<String, u32> = BTreeMap::new();
    for c in catalog {
        if !id_by_name.contains_key(c.name.as_str()) {
            let id = id_by_name.len() as u32;
            id_by_name.insert(c.name.clone(), id);
        }
    }

    let mut ops = Vec::with_capacity(configs.len());
    for (sc, cat) in configs.iter().zip(catalog.iter()) {
        let signal_id = *id_by_name
            .get(cat.name.as_str())
            .ok_or_else(|| format!("signal id 分配失败: {}", cat.name))?;
        let params = serde_json::to_value(&sc.params)
            .map_err(|e| format!("信号参数序列化失败 {}: {e}", sc.name))?;
        ops.push(CompiledSignal {
            signal_id,
            name: cat.name.clone(),
            freq: sc.freq.clone(),
            category: cat.category,
            params,
        });
    }

    Ok(CompiledSignalPlan { ops, id_by_name })
}
