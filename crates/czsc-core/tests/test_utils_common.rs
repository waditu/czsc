//! Phase D.4 — RED test: freq_to_chinese_string returns the canonical
//! Chinese label for each Freq variant; this is the helper bar.rs and
//! various PyO3 bindings rely on to build display strings.

use czsc_core::objects::freq::Freq;
use czsc_core::utils::common::freq_to_chinese_string;

#[test]
fn covers_minute_freqs() {
    assert_eq!(freq_to_chinese_string(Freq::F1), "1分钟");
    assert_eq!(freq_to_chinese_string(Freq::F30), "30分钟");
    assert_eq!(freq_to_chinese_string(Freq::F360), "360分钟");
}

#[test]
fn covers_higher_timeframes() {
    assert_eq!(freq_to_chinese_string(Freq::D), "日线");
    assert_eq!(freq_to_chinese_string(Freq::W), "周线");
    assert_eq!(freq_to_chinese_string(Freq::M), "月线");
    assert_eq!(freq_to_chinese_string(Freq::Y), "年线");
}

#[test]
fn tick_returns_english_marker() {
    assert_eq!(freq_to_chinese_string(Freq::Tick), "Tick");
}
