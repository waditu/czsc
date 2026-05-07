//! Phase D.7 — RED test: FX (分型) constructs via FXBuilder, exposes
//! power_str / power_volume / has_zs (non-python build), and compares
//! by structural equality.

use std::sync::Arc;

use chrono::{TimeZone, Utc};
use czsc_core::objects::bar::{NewBar, NewBarBuilder};
use czsc_core::objects::fx::{FX, FXBuilder};
use czsc_core::objects::freq::Freq;
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

fn sample_top_fx() -> FX {
    // top fx (顶分型): middle bar's high is the highest
    let k1 = nb(1_700_000_000, 11.0, 9.0, 100.0);
    let k2 = nb(1_700_001_800, 12.0, 10.0, 200.0); // top
    let k3 = nb(1_700_003_600, 11.5, 9.5, 100.0);
    FXBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(k2.dt)
        .mark(Mark::G)
        .high(k2.high)
        .low(k2.low)
        .fx(k2.high)
        .elements(vec![k1, k2, k3])
        .build()
        .unwrap()
}

#[test]
fn builder_populates_fields() {
    let fx = sample_top_fx();
    assert_eq!(fx.mark, Mark::G);
    assert_eq!(fx.elements.len(), 3);
    assert!((fx.high - 12.0).abs() < f64::EPSILON);
}

#[test]
fn power_str_returns_one_of_strong_medium_weak() {
    let fx = sample_top_fx();
    let p = fx.power_str();
    assert!(matches!(p, "强" | "中" | "弱"), "got {p}");
}

#[test]
fn power_volume_is_finite() {
    let fx = sample_top_fx();
    assert!(fx.power_volume().is_finite());
}

#[test]
fn equality_matches_rs_czsc_baseline() {
    let a = sample_top_fx();
    let b = sample_top_fx();
    assert_eq!(a, b);
}
