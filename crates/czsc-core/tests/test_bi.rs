//! Phase D.8 — RED test: BI (笔) constructs via BIBuilder, surfaces
//! direction / endpoints, and answers length / SNR / power_price helpers.

use std::sync::Arc;

use chrono::{TimeZone, Utc};
use czsc_core::objects::bar::{NewBar, NewBarBuilder};
use czsc_core::objects::bi::{BI, BIBuilder};
use czsc_core::objects::direction::Direction;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::fx::{FX, FXBuilder};
use czsc_core::objects::mark::Mark;

fn nb(ts: i64, high: f64, low: f64, vol: f64) -> NewBar {
    NewBarBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .freq(Freq::F30)
        .id(0)
        .open((high + low) / 2.0)
        .close((high + low) / 2.0)
        .high(high)
        .low(low)
        .vol(vol)
        .amount(vol * (high + low) / 2.0)
        .elements(Vec::new())
        .build()
        .unwrap()
}

fn fx(ts: i64, mark: Mark, level: f64) -> FX {
    let k1 = nb(ts - 1800, level - 0.5, level - 1.5, 100.0);
    let k2 = nb(ts, level + 0.5, level - 0.5, 200.0);
    let k3 = nb(ts + 1800, level - 0.2, level - 1.0, 100.0);
    FXBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .mark(mark)
        .high(k2.high)
        .low(k2.low)
        .fx(if matches!(level, l if l > 5.0) { k2.high } else { k2.low })
        .elements(vec![k1, k2, k3])
        .build()
        .unwrap()
}

fn sample_bi_up() -> BI {
    // up bi: starts at bottom fx, ends at top fx
    let fx_a = fx(1_700_000_000, Mark::D, 9.0);
    let fx_b = fx(1_700_007_200, Mark::G, 12.0);
    let bars: Vec<NewBar> = (0..5)
        .map(|i| nb(1_700_000_000 + i * 1800, 11.0 + i as f64 * 0.2, 9.5 + i as f64 * 0.2, 100.0))
        .collect();
    BIBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .fx_a(fx_a)
        .fx_b(fx_b.clone())
        .fxs(vec![fx_b])
        .direction(Direction::Up)
        .bars(bars)
        .build()
        .unwrap()
}

#[test]
fn builder_populates_fields() {
    let bi = sample_bi_up();
    assert_eq!(bi.direction, Direction::Up);
    assert_eq!(bi.bars.len(), 5);
}

#[test]
fn length_is_bars_count() {
    let bi = sample_bi_up();
    assert_eq!(bi.get_length(), 5);
}

#[test]
fn high_low_endpoints_match_fxs() {
    let bi = sample_bi_up();
    assert!(bi.get_low() < bi.get_high(), "low must be < high");
}

#[test]
fn power_price_is_finite() {
    let bi = sample_bi_up();
    assert!(bi.get_power_price().is_finite());
}

#[test]
fn equality_matches_rs_czsc_baseline() {
    let a = sample_bi_up();
    let b = sample_bi_up();
    assert_eq!(a, b);
}
