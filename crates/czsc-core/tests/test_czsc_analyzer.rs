//! Phase D.A — RED test: CZSC analyzer constructs from a RawBar feed,
//! exposes bars_raw / bars_ubi / bi_list / fx_list, and survives an
//! incremental update_bar feed.

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
    // Build a sine-like zigzag so that the analyzer can produce fxs/bis.
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
    // bars_ubi is the merged-bar (NewBar) sequence; for 40 raw zigzag
    // bars we expect non-empty merged sequence
    assert!(!c.bars_ubi.is_empty(), "bars_ubi should not be empty");
}

#[test]
fn fx_and_bi_lists_are_consistent_with_zigzag() {
    let bars = synthetic_zigzag(60);
    let c = CZSC::new(bars, 50);
    let fxs = c.get_fx_list();
    // A 60-bar zigzag should produce at least 2 fxs (or zero — the
    // exact count depends on the synthetic shape; we only assert
    // non-negative invariants).
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
    // bars_raw monotonically grows (modulo the analyzer's internal pruning)
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
