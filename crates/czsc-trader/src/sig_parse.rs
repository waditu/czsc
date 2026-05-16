use czsc_core::objects::freq::Freq;
use czsc_signals::registry::{SIGNAL_REGISTRY, TRADER_SIGNAL_REGISTRY};
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::Value;
use std::cmp::Ordering;
use std::collections::HashMap;
use tracing::error;

/// 单个信号函数配置。
///
/// 反序列化时同时支持两种 JSON 形态（PR-2 / PR-3 后下沉到 Rust 端）：
/// - 嵌套：`{"name": "...", "freq": "...", "params": {"di": 1}}`
/// - 展平：`{"name": "...", "freq": "...", "di": 1, "ma_type": "SMA"}`
///
/// 同时对 `name` 做模块前缀剥离：`"czsc.signals.tas.cci_V230402"` → `"cci_V230402"`。
#[derive(Debug, Clone, Serialize)]
pub struct SignalConfig {
    /// 函数名，如 "tas_ma_base_V221101"
    pub name: String,
    /// 关联的 K 线周期（若为 None，表示该函数接受 CzscSignals 而非单个 CZSC）
    pub freq: Option<String>,
    /// 函数参数（di/ma_type/timeperiod 等）
    pub params: HashMap<String, Value>,
}

impl<'de> Deserialize<'de> for SignalConfig {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        // 用 serde_json::Value 作为中间形态，避免手写 Visitor 维护两套字段集
        let value = serde_json::Value::deserialize(deserializer)?;
        let map = value
            .as_object()
            .ok_or_else(|| serde::de::Error::custom("SignalConfig 必须是 object"))?;

        let name_raw = map
            .get("name")
            .and_then(|v| v.as_str())
            .ok_or_else(|| serde::de::Error::missing_field("name"))?
            .to_string();
        // 剥离模块前缀：Rust 端按短名直接派发
        let name = name_raw
            .rsplit('.')
            .next()
            .unwrap_or(&name_raw)
            .to_string();

        let freq = map
            .get("freq")
            .and_then(|v| if v.is_null() { None } else { v.as_str() })
            .map(|s| s.to_string());

        // 风格 A：含 params 子字典；风格 B：参数平铺在顶层
        let mut params: HashMap<String, Value> = HashMap::new();
        if let Some(params_val) = map.get("params")
            && let Some(params_obj) = params_val.as_object()
        {
            for (k, v) in params_obj {
                params.insert(k.clone(), v.clone());
            }
        }
        for (k, v) in map.iter() {
            if matches!(k.as_str(), "name" | "freq" | "params" | "signals_module" | "module") {
                continue;
            }
            params.entry(k.clone()).or_insert_with(|| v.clone());
        }

        Ok(SignalConfig { name, freq, params })
    }
}

impl SignalConfig {
    /// 从单独的信号字符串推导配置（对应 Python get_signals_config 中的反解析逻辑）
    /// 例如: "日线_D1SMA#5_分类V221101_多头_向上_任意_0" -> freq="日线", name="tas_ma_base_V221101", params={di=1, ma_type="SMA", timeperiod=5}
    pub fn from_signal_str(signal: &str) -> Option<Self> {
        let parts: Vec<&str> = signal.split('_').collect();
        if parts.len() != 7 {
            error!("非标准信号格式: {}", signal);
            return None;
        }

        let k3 = parts[2];
        let key = parts[..3].join("_");

        for (func_name, meta) in SIGNAL_REGISTRY.iter() {
            let Some(tpl_parts) = split_template_parts(meta.param_template) else {
                continue;
            };
            if tpl_parts.len() != 3 {
                continue;
            }
            if tpl_parts[2] == k3
                && let Some((freq, params)) = parse_template_into_config(meta.param_template, &key)
            {
                return Some(Self {
                    name: func_name.to_string(),
                    freq,
                    params,
                });
            }
        }
        for (func_name, meta) in TRADER_SIGNAL_REGISTRY.iter() {
            let Some(tpl_parts) = split_template_parts(meta.param_template) else {
                continue;
            };
            if tpl_parts.len() != 3 {
                continue;
            }
            if tpl_parts[2] == k3
                && let Some((freq, params)) = parse_template_into_config(meta.param_template, &key)
            {
                return Some(Self {
                    name: func_name.to_string(),
                    freq,
                    params,
                });
            }
        }
        None
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
enum TemplateToken {
    Lit(String),
    Placeholder(String),
}

fn tokenize_template_segment(segment: &str) -> Option<Vec<TemplateToken>> {
    let mut tokens = Vec::new();
    let chars: Vec<char> = segment.chars().collect();
    let mut i = 0;
    let mut lit = String::new();

    while i < chars.len() {
        if chars[i] == '{' {
            if !lit.is_empty() {
                tokens.push(TemplateToken::Lit(std::mem::take(&mut lit)));
            }
            let mut j = i + 1;
            while j < chars.len() && chars[j] != '}' {
                j += 1;
            }
            if j >= chars.len() {
                return None;
            }
            let name: String = chars[i + 1..j].iter().collect();
            if name.is_empty() {
                return None;
            }
            tokens.push(TemplateToken::Placeholder(name));
            i = j + 1;
        } else {
            lit.push(chars[i]);
            i += 1;
        }
    }

    if !lit.is_empty() {
        tokens.push(TemplateToken::Lit(lit));
    }
    Some(tokens)
}

fn parse_scalar_value(raw: &str) -> Value {
    if let Ok(v) = raw.parse::<i64>() {
        return Value::from(v);
    }
    if raw.eq_ignore_ascii_case("true") {
        return Value::from(true);
    }
    if raw.eq_ignore_ascii_case("false") {
        return Value::from(false);
    }
    Value::String(raw.to_string())
}

fn parse_template_segment(segment: &str, raw: &str) -> Option<HashMap<String, Value>> {
    let tokens = tokenize_template_segment(segment)?;
    parse_template_tokens(&tokens, raw, 0, 0, HashMap::new())
}

fn parse_template_into_config(
    template: &str,
    key: &str,
) -> Option<(Option<String>, HashMap<String, Value>)> {
    let tpl_parts = split_template_parts(template)?;
    let key_parts: Vec<&str> = key.splitn(3, '_').collect();
    if tpl_parts.len() != key_parts.len() {
        return None;
    }

    let mut freq = None;
    let mut params = HashMap::new();
    for (tpl_part, key_part) in tpl_parts.iter().zip(key_parts.iter()) {
        for (name, value) in parse_template_segment(tpl_part, key_part)? {
            if name == "freq" {
                let v = value.as_str()?.to_string();
                freq = Some(v);
            } else {
                params.insert(name, value);
            }
        }
    }
    Some((freq, params))
}

fn split_template_parts(template: &str) -> Option<Vec<&str>> {
    let mut parts = Vec::new();
    let mut depth = 0usize;
    let mut start = 0usize;

    for (idx, ch) in template.char_indices() {
        match ch {
            '{' => depth += 1,
            '}' => {
                if depth == 0 {
                    return None;
                }
                depth -= 1;
            }
            '_' if depth == 0 => {
                parts.push(template.get(start..idx)?);
                start = idx + ch.len_utf8();
            }
            _ => {}
        }
    }

    if depth != 0 {
        return None;
    }
    parts.push(template.get(start..)?);
    Some(parts)
}

fn parse_template_tokens(
    tokens: &[TemplateToken],
    raw: &str,
    token_idx: usize,
    raw_idx: usize,
    params: HashMap<String, Value>,
) -> Option<HashMap<String, Value>> {
    if token_idx == tokens.len() {
        return (raw_idx == raw.len()).then_some(params);
    }

    match tokens.get(token_idx)? {
        TemplateToken::Lit(lit) => {
            let rest = raw.get(raw_idx..)?;
            if !rest.starts_with(lit) {
                return None;
            }
            parse_template_tokens(tokens, raw, token_idx + 1, raw_idx + lit.len(), params)
        }
        TemplateToken::Placeholder(name) => {
            if token_idx + 1 == tokens.len() {
                let captured = raw.get(raw_idx..)?;
                if captured.is_empty() {
                    return None;
                }
                let mut next_params = params;
                next_params.insert(name.clone(), parse_scalar_value(captured));
                return Some(next_params);
            }

            let rest = raw.get(raw_idx..)?;
            match tokens.get(token_idx + 1)? {
                TemplateToken::Lit(lit) => {
                    for (pos, _) in rest.match_indices(lit) {
                        if pos == 0 {
                            continue;
                        }
                        let Some(captured) = rest.get(..pos) else {
                            continue;
                        };
                        let mut next_params = params.clone();
                        next_params.insert(name.clone(), parse_scalar_value(captured));
                        if let Some(parsed) = parse_template_tokens(
                            tokens,
                            raw,
                            token_idx + 1,
                            raw_idx + pos,
                            next_params,
                        ) {
                            return Some(parsed);
                        }
                    }
                    None
                }
                TemplateToken::Placeholder(_) => {
                    let mut end_points = Vec::new();
                    for (offset, _) in rest.char_indices() {
                        if offset > 0 {
                            end_points.push(raw_idx + offset);
                        }
                    }
                    end_points.push(raw.len());

                    for end in end_points {
                        if end <= raw_idx {
                            continue;
                        }
                        let Some(captured) = raw.get(raw_idx..end) else {
                            continue;
                        };
                        let mut next_params = params.clone();
                        next_params.insert(name.clone(), parse_scalar_value(captured));
                        if let Some(parsed) =
                            parse_template_tokens(tokens, raw, token_idx + 1, end, next_params)
                        {
                            return Some(parsed);
                        }
                    }
                    None
                }
            }
        }
    }
}

/// 从 unique_signals 中获取去重的 SignalConfig 列表
pub fn get_signals_config(unique_signals: &[&str]) -> Vec<SignalConfig> {
    let mut configs = Vec::new();
    let mut seen = std::collections::HashSet::new();

    for sig in unique_signals {
        if let Some(cfg) = SignalConfig::from_signal_str(sig) {
            let key = format!("{:?}", cfg);
            if seen.insert(key) {
                configs.push(cfg);
            }
        }
    }
    configs
}

/// 获取信号中所有不同的周期（freq）
pub fn get_signals_freqs(signals_config: &[SignalConfig]) -> Vec<String> {
    let mut freqs = std::collections::HashSet::new();
    for cfg in signals_config {
        if let Some(f) = &cfg.freq {
            freqs.insert(f.clone());
        }
        for (k, v) in &cfg.params {
            if !k.starts_with("freq") {
                continue;
            }
            if let Some(f) = v.as_str() {
                freqs.insert(f.to_string());
            }
        }
    }

    let mut result: Vec<String> = freqs.into_iter().collect();
    result.sort_by(|a, b| match (a.parse::<Freq>(), b.parse::<Freq>()) {
        (Ok(fa), Ok(fb)) => fa.cmp(&fb),
        (Ok(_), Err(_)) => Ordering::Less,
        (Err(_), Ok(_)) => Ordering::Greater,
        (Err(_), Err(_)) => a.cmp(b),
    });
    result
}

#[cfg(test)]
mod tests {
    use super::{
        SignalConfig, get_signals_freqs, parse_template_into_config, parse_template_segment,
        split_template_parts,
    };
    use serde_json::Value;
    use std::collections::HashMap;

    #[test]
    fn test_from_signal_str_parses_bar_single_di_n() {
        let sig = "5分钟_D2单K趋势N20_BS辅助V230506_第6层_任意_任意_0";
        let cfg = SignalConfig::from_signal_str(sig).expect("should parse signal config");
        assert_eq!(cfg.name, "bar_single_V230506");
        assert_eq!(cfg.freq.as_deref(), Some("5分钟"));
        assert_eq!(cfg.params.get("di"), Some(&Value::from(2)));
        assert_eq!(cfg.params.get("n"), Some(&Value::from(20)));
    }

    #[test]
    fn test_from_signal_str_parses_kline_template_params_without_k2_fallback() {
        let sig = "60分钟_D1SMA#5_分类V221101_多头_向上_任意_0";
        let cfg = SignalConfig::from_signal_str(sig).expect("should parse signal config");
        assert_eq!(cfg.name, "tas_ma_base_V221101");
        assert_eq!(cfg.freq.as_deref(), Some("60分钟"));
        assert_eq!(cfg.params.get("di"), Some(&Value::from(1)));
        assert_eq!(cfg.params.get("ma_type"), Some(&Value::from("SMA")));
        assert_eq!(cfg.params.get("timeperiod"), Some(&Value::from(5)));
        assert!(!cfg.params.contains_key("k2"));
    }

    #[test]
    fn test_from_signal_str_parses_trader_multi_freq_template_params() {
        let sig = "日线#60分钟_MACD交叉_联立V230518_其他_任意_任意_0";
        let cfg = SignalConfig::from_signal_str(sig).expect("should parse signal config");
        assert_eq!(cfg.name, "cat_macd_V230518");
        assert_eq!(cfg.freq, None);
        assert_eq!(cfg.params.get("freq1"), Some(&Value::from("日线")));
        assert_eq!(cfg.params.get("freq2"), Some(&Value::from("60分钟")));
        assert!(!cfg.params.contains_key("k2"));
    }

    #[test]
    fn test_parse_template_into_config_handles_adjacent_placeholders() {
        let tpl_parts = split_template_parts("{freq}_D{di}{ma_type}#{timeperiod}_分类V221101")
            .expect("template should split");
        let key_parts: Vec<&str> = "60分钟_D1SMA#5_分类V221101".split('_').collect();
        assert_eq!(
            tpl_parts,
            vec!["{freq}", "D{di}{ma_type}#{timeperiod}", "分类V221101"]
        );
        assert_eq!(key_parts, vec!["60分钟", "D1SMA#5", "分类V221101"]);
        assert_eq!(
            parse_template_segment("{freq}", "60分钟")
                .expect("freq segment should parse")
                .get("freq"),
            Some(&Value::from("60分钟"))
        );
        assert!(
            parse_template_segment("分类V221101", "分类V221101").is_some(),
            "literal segment should parse"
        );
        let parsed = parse_template_into_config(
            "{freq}_D{di}{ma_type}#{timeperiod}_分类V221101",
            "60分钟_D1SMA#5_分类V221101",
        )
        .expect("should parse template");
        assert_eq!(parsed.0.as_deref(), Some("60分钟"));
        assert_eq!(parsed.1.get("di"), Some(&Value::from(1)));
        assert_eq!(parsed.1.get("ma_type"), Some(&Value::from("SMA")));
        assert_eq!(parsed.1.get("timeperiod"), Some(&Value::from(5)));
    }

    #[test]
    fn test_parse_template_segment_handles_adjacent_placeholders() {
        let params = parse_template_segment("D{di}{ma_type}#{timeperiod}", "D1SMA#5")
            .expect("segment should parse");
        assert_eq!(params.get("di"), Some(&Value::from(1)));
        assert_eq!(params.get("ma_type"), Some(&Value::from("SMA")));
        assert_eq!(params.get("timeperiod"), Some(&Value::from(5)));
    }

    #[test]
    fn test_parse_template_segment_handles_adjacent_numeric_and_string_placeholders_without_name_hints()
     {
        let params = parse_template_segment("D{di}{mode}", "D1ZF").expect("segment should parse");
        assert_eq!(params.get("di"), Some(&Value::from(1)));
        assert_eq!(params.get("mode"), Some(&Value::from("ZF")));
    }

    #[test]
    fn test_split_template_parts_ignores_underscores_inside_placeholders() {
        let parts = split_template_parts("{freq}_D{di}{ma_type}#{timeperiod}_分类V221101")
            .expect("template should split");
        assert_eq!(
            parts,
            vec!["{freq}", "D{di}{ma_type}#{timeperiod}", "分类V221101"]
        );
    }

    #[test]
    fn test_get_signals_freqs_collects_freq_params() {
        let mut params = HashMap::new();
        params.insert("freq1".to_string(), Value::from("日线"));
        params.insert("freq2".to_string(), Value::from("60分钟"));
        let cfgs = vec![
            SignalConfig {
                name: "cat_macd_V230518".to_string(),
                freq: None,
                params,
            },
            SignalConfig {
                name: "tas_ma_base_V221101".to_string(),
                freq: Some("15分钟".to_string()),
                params: HashMap::new(),
            },
        ];
        let freqs = get_signals_freqs(&cfgs);
        assert!(freqs.contains(&"15分钟".to_string()));
        assert!(freqs.contains(&"日线".to_string()));
        assert!(freqs.contains(&"60分钟".to_string()));
    }

    #[test]
    fn test_get_signals_freqs_uses_builtin_freq_order() {
        let cfgs = vec![
            SignalConfig {
                name: "demo_a".to_string(),
                freq: Some("日线".to_string()),
                params: HashMap::new(),
            },
            SignalConfig {
                name: "demo_b".to_string(),
                freq: Some("30分钟".to_string()),
                params: HashMap::new(),
            },
            SignalConfig {
                name: "demo_c".to_string(),
                freq: Some("60分钟".to_string()),
                params: HashMap::new(),
            },
        ];

        let freqs = get_signals_freqs(&cfgs);
        assert_eq!(freqs, vec!["30分钟", "60分钟", "日线"]);
    }
}
