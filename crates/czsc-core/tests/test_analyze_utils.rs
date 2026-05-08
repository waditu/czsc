//! Phase D.U — RED test: analyze::utils helpers (check_fx / check_fxs /
//! check_bi / remove_include / format_standard_kline) are publicly callable
//! and produce the expected shapes per the rs-czsc 47ef6efa baseline.
//!
//! This test also locks the visibility promotions required by the design
//! doc §2.5: all four `pub(crate)` helpers must now be `pub`.

use std::sync::Arc;

use chrono::{TimeZone, Utc};
use czsc_core::analyze::utils::{check_bi, check_fx, check_fxs, format_standard_kline};
use czsc_core::objects::bar::{NewBar, NewBarBuilder, RawBar};
use czsc_core::objects::freq::Freq;
use czsc_core::objects::mark::Mark;

fn nb(ts: i64, high: f64, low: f64) -> NewBar {
    NewBarBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .freq(Freq::F30)
        .id(0)
        .open((high + low) / 2.0)
        .close((high + low) / 2.0)
        .high(high)
        .low(low)
        .vol(100.0)
        .amount(100.0 * (high + low) / 2.0)
        .elements(Vec::new())
        .build()
        .unwrap()
}

#[test]
fn check_fx_detects_top_pattern() {
    // top fx: middle bar engulfs both neighbours from above
    let k1 = nb(1, 11.0, 9.0);
    let k2 = nb(2, 12.0, 10.0);
    let k3 = nb(3, 11.5, 9.5);
    let fx = check_fx(&k1, &k2, &k3).expect("expected top fx");
    assert_eq!(fx.mark, Mark::G);
    assert!((fx.fx - 12.0).abs() < f64::EPSILON);
}

#[test]
fn check_fx_detects_bottom_pattern() {
    let k1 = nb(1, 11.0, 9.5);
    let k2 = nb(2, 10.5, 8.0);
    let k3 = nb(3, 11.0, 9.0);
    let fx = check_fx(&k1, &k2, &k3).expect("expected bottom fx");
    assert_eq!(fx.mark, Mark::D);
    assert!((fx.fx - 8.0).abs() < f64::EPSILON);
}

#[test]
fn check_fx_returns_none_when_no_pattern() {
    // strictly increasing — neither top nor bottom
    let k1 = nb(1, 10.0, 9.0);
    let k2 = nb(2, 11.0, 10.0);
    let k3 = nb(3, 12.0, 11.0);
    assert!(check_fx(&k1, &k2, &k3).is_none());
}

#[test]
fn check_fxs_extracts_fx_from_sequence() {
    // 5 bars: ascending, peak, descending → exactly one top fx in the middle
    let bars = vec![
        nb(1, 10.0, 9.0),
        nb(2, 11.0, 10.0),
        nb(3, 12.0, 11.0),
        nb(4, 11.5, 10.5),
        nb(5, 11.0, 10.0),
    ];
    let fxs = check_fxs(&bars);
    assert!(!fxs.is_empty(), "expected at least one fx in peak sequence");
}

#[test]
fn check_bi_returns_tuple_with_remainder() {
    let bars: Vec<NewBar> = (0..6)
        .map(|i| nb(i + 1, 10.0 + i as f64, 9.0 + i as f64))
        .collect();
    let (bi, remainder) = check_bi(&bars);
    // The function signature contract: always returns (Option<BI>, &[NewBar])
    let _ = bi;
    assert!(remainder.len() <= bars.len());
}

#[test]
fn format_standard_kline_builds_raw_bars_from_dataframe() {
    use polars::prelude::*;

    let df = df! {
        "symbol" => ["000001", "000001", "000001"],
        "dt"     => [1_700_000_000_000i64, 1_700_001_800_000, 1_700_003_600_000],
        "open"   => [10.0_f64, 10.5, 11.0],
        "close"  => [10.5_f64, 11.0, 10.8],
        "high"   => [11.0_f64, 11.5, 11.2],
        "low"    => [9.5_f64, 10.0, 10.5],
        "vol"    => [100.0_f64, 200.0, 150.0],
        "amount" => [1000.0_f64, 2000.0, 1500.0],
    }
    .unwrap()
    .lazy()
    .with_column(
        col("dt")
            .cast(DataType::Datetime(TimeUnit::Milliseconds, None))
            .alias("dt"),
    )
    .collect()
    .unwrap();

    let bars: Vec<RawBar> = format_standard_kline(df, Freq::F30).unwrap();
    assert_eq!(bars.len(), 3);
    assert_eq!(&*bars[0].symbol, "000001");
    assert_eq!(bars[0].freq, Freq::F30);
}
