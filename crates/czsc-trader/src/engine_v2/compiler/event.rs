use czsc_core::objects::position::Position;
use std::collections::BTreeMap;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EventCondition {
    pub key_id: u32,
    pub value: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EventClause {
    pub all: Vec<EventCondition>,
    pub any: Vec<EventCondition>,
    pub not: Vec<EventCondition>,
}

#[derive(Debug, Clone, Default)]
pub struct CompiledEventPlan {
    pub key_ids: BTreeMap<String, u32>,
    pub by_position: BTreeMap<String, Vec<EventClause>>,
}

fn parse_condition(sig: &str, key_ids: &mut BTreeMap<String, u32>) -> Option<EventCondition> {
    let mut parts = sig.split('_');
    let k1 = parts.next()?;
    let k2 = parts.next()?;
    let k3 = parts.next()?;
    let v1 = parts.next().unwrap_or("其他");
    let key = format!("{k1}_{k2}_{k3}");
    let key_id = if let Some(x) = key_ids.get(key.as_str()) {
        *x
    } else {
        let x = key_ids.len() as u32;
        key_ids.insert(key.clone(), x);
        x
    };
    Some(EventCondition {
        key_id,
        value: v1.to_string(),
    })
}

pub fn compile_events(positions: &[Position]) -> CompiledEventPlan {
    let mut key_ids = BTreeMap::new();
    let mut by_position = BTreeMap::new();

    for p in positions {
        let mut clauses = Vec::new();
        for e in p.opens.iter().chain(p.exits.iter()) {
            let all = e
                .signals_all
                .iter()
                .filter_map(|x| parse_condition(x.to_string().as_str(), &mut key_ids))
                .collect();
            let any = e
                .signals_any
                .iter()
                .filter_map(|x| parse_condition(x.to_string().as_str(), &mut key_ids))
                .collect();
            let not = e
                .signals_not
                .iter()
                .filter_map(|x| parse_condition(x.to_string().as_str(), &mut key_ids))
                .collect();
            clauses.push(EventClause { all, any, not });
        }
        by_position.insert(p.name.clone(), clauses);
    }

    CompiledEventPlan {
        key_ids,
        by_position,
    }
}

#[cfg(test)]
mod tests {
    use super::compile_events;
    use czsc_core::objects::position::Position;

    #[test]
    fn compile_events_extracts_key_ids() {
        let p: Position = serde_json::from_value(serde_json::json!({
            "name": "P",
            "symbol": "000001.SZ",
            "opens": [{
                "name": "开多",
                "operate": "开多",
                "signals_all": ["30分钟_D1_表里关系V230101_向上_任意_任意_0"],
                "signals_any": [],
                "signals_not": []
            }],
            "exits": [],
            "interval": 0,
            "timeout": 10,
            "stop_loss": 100.0,
            "T0": false
        }))
        .expect("position from value");
        let plan = compile_events(&[p]);
        assert!(!plan.key_ids.is_empty());
        assert!(plan.by_position.contains_key("P"));
    }
}
