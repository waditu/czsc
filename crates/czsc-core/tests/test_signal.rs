//! Phase D.10b —— RED 测试：Signal 类型（`SignalRef<'static>` 即 `Signal`）
//! 从规范的 k1_k2_k3_v1_v2_v3_score 字符串解析，并按 rs-czsc 的契约
//! 暴露 `key()` / `value()` / Display。

use std::str::FromStr;

use czsc_core::objects::signal::Signal;

#[test]
fn parses_canonical_signal_string() {
    let raw = "30分钟_D1_前高_看多_强_任意_0";
    let s = Signal::from_str(raw).unwrap();
    // key 会去掉 "任意" 段；这里 k1/k2/k3 全部是具体值
    assert_eq!(s.key(), "30分钟_D1_前高");
    // value 是 v1_v2_v3_score
    assert_eq!(s.value(), "看多_强_任意_0");
}

#[test]
fn display_round_trips_full_signal() {
    let raw = "30分钟_D1_前高_看多_强_任意_0";
    let s = Signal::from_str(raw).unwrap();
    assert_eq!(s.to_string(), raw);
}

#[test]
fn rejects_malformed_string() {
    assert!(Signal::from_str("only_three_fields").is_err());
}

#[test]
fn equality_is_full_signal_string() {
    let a = Signal::from_str("30分钟_D1_前高_看多_强_任意_0").unwrap();
    let b = Signal::from_str("30分钟_D1_前高_看多_强_任意_0").unwrap();
    assert_eq!(a, b);
    let c = Signal::from_str("30分钟_D1_前高_看空_强_任意_0").unwrap();
    assert_ne!(a, c);
}

#[test]
fn key_skips_wildcards() {
    let s = Signal::from_str("任意_D1_前高_看多_强_任意_0").unwrap();
    // k1 是「任意」→ 从 key 中剔除
    assert_eq!(s.key(), "D1_前高");
}

#[test]
fn is_match_obeys_score_and_wildcards() {
    use std::collections::HashMap;
    let s = Signal::from_str("30分钟_D1_前高_看多_强_任意_50").unwrap();
    let mut dict = HashMap::new();
    dict.insert("30分钟_D1_前高".to_string(), "看多_强_中_60".to_string());
    assert!(s.is_match(&dict), "score 60 >= 50 且 v3 是通配符，应当匹配");

    let mut low_score = HashMap::new();
    low_score.insert("30分钟_D1_前高".to_string(), "看多_强_中_40".to_string());
    assert!(!s.is_match(&low_score), "score 40 < 50 不应匹配");
}
