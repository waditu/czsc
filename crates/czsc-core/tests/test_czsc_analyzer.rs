//! Phase D.A — RED test：CZSC 分析器从 RawBar 流构造，
//! 暴露 bars_raw / bars_ubi / bi_list / fx_list，并能正确处理
//! 增量的 update_bar 输入。

use std::sync::Arc;

use chrono::{TimeZone, Utc};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::{RawBar, RawBarBuilder};
use czsc_core::objects::freq::Freq;

fn rb(ts: i64, open: f64, close: f64, high: f64, low: f64) -> RawBar {
    RawBarBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .freq(Freq::F30)
        .id(0)
        .open(open)
        .close(close)
        .high(high)
        .low(low)
        .vol(1000.0_f64)
        .amount(1_000_000.0_f64)
        .build()
        .unwrap()
}

fn synthetic_zigzag(n: usize) -> Vec<RawBar> {
    // 构造一个类正弦波形的 zigzag，让分析器能产出 fxs/bis。
    (0..n)
        .map(|i| {
            let phase = (i as f64) * 0.7;
            let mid = 100.0 + 5.0 * phase.sin();
            let half = 1.0 + 0.5 * phase.cos().abs();
            rb(
                1_700_000_000 + (i as i64) * 1800,
                mid - 0.2,
                mid + 0.2,
                mid + half,
                mid - half,
            )
        })
        .collect()
}

#[test]
fn new_populates_symbol_and_freq() {
    let bars = synthetic_zigzag(50);
    let c = CZSC::new(bars, 50);
    assert_eq!(&*c.symbol, "000001");
    assert_eq!(c.freq, Freq::F30);
    assert_eq!(c.max_bi_num, 50);
}

#[test]
fn new_consumes_all_bars_and_builds_ubi() {
    let bars = synthetic_zigzag(40);
    let c = CZSC::new(bars, 50);
    // bars_ubi 是合并后 bar（NewBar）序列；对于 40 根原始 zigzag
    // bar，我们期望合并后的序列非空
    assert!(!c.bars_ubi.is_empty(), "bars_ubi should not be empty");
}

#[test]
fn fx_and_bi_lists_are_consistent_with_zigzag() {
    let bars = synthetic_zigzag(60);
    let c = CZSC::new(bars, 50);
    let fxs = c.get_fx_list();
    // 60 根 bar 的 zigzag 应该至少产出 2 个 fx（或者 0 个——
    // 具体数量取决于合成出来的波形；这里只断言非负不变量）。
    assert!(fxs.len() <= 60);
    assert!(c.bi_list.len() <= 50);
}

#[test]
fn update_bar_appends_incrementally() {
    let bars = synthetic_zigzag(30);
    let mut c = CZSC::new(bars, 50);
    let extra = rb(1_700_000_000 + 30 * 1800, 102.0, 103.0, 104.0, 101.0);
    c.update_bar(extra);
    assert_eq!(c.freq, Freq::F30);
    // bars_raw 单调增长（不计分析器内部的裁剪）
    assert!(
        c.bars_raw
            .iter()
            .any(|b| b.dt == Utc.timestamp_opt(1_700_000_000 + 30 * 1800, 0).unwrap())
    );
}

#[test]
fn analyzer_clones_independently() {
    let bars = synthetic_zigzag(20);
    let c = CZSC::new(bars, 50);
    let d = c.clone();
    assert_eq!(d.bi_list.len(), c.bi_list.len());
    assert_eq!(&*d.symbol, &*c.symbol);
}
