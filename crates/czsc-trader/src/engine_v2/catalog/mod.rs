use crate::sig_parse::SignalConfig;
use czsc_signals::registry::{
    SIGNAL_REGISTRY, TRADER_SIGNAL_REGISTRY, list_generated_signal_descriptors,
};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SignalCategory {
    Kline,
    Trader,
}

#[derive(Debug, Clone)]
pub struct CatalogSignal {
    pub name: String,
    pub category: SignalCategory,
}

pub fn resolve_signal_category(sc: &SignalConfig) -> Result<CatalogSignal, String> {
    for d in list_generated_signal_descriptors() {
        if d.name.eq_ignore_ascii_case(sc.name.as_str()) {
            let category = match d.category {
                "kline" => SignalCategory::Kline,
                "trader" => SignalCategory::Trader,
                _ => continue,
            };
            return Ok(CatalogSignal {
                name: d.name.to_string(),
                category,
            });
        }
    }

    if sc.freq.is_some() {
        if SIGNAL_REGISTRY.contains_key(sc.name.as_str()) {
            return Ok(CatalogSignal {
                name: sc.name.clone(),
                category: SignalCategory::Kline,
            });
        }
        return Err(format!("未注册 K线信号: {}", sc.name));
    }

    if TRADER_SIGNAL_REGISTRY.contains_key(sc.name.as_str()) {
        Ok(CatalogSignal {
            name: sc.name.clone(),
            category: SignalCategory::Trader,
        })
    } else {
        Err(format!("未注册 Trader 信号: {}", sc.name))
    }
}

#[cfg(test)]
mod tests {
    use super::{SignalCategory, resolve_signal_category};
    use crate::sig_parse::SignalConfig;
    use std::collections::HashMap;

    #[test]
    fn resolve_uses_generated_descriptor_first() {
        let sc = SignalConfig {
            name: "tas_macd_base_V221028".to_string(),
            freq: Some("60分钟".to_string()),
            params: HashMap::new(),
        };
        let cs = resolve_signal_category(&sc).expect("must resolve");
        assert_eq!(cs.category, SignalCategory::Kline);
        assert_eq!(cs.name, "tas_macd_base_V221028");
    }
}
