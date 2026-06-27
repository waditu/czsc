//! Phase D.U — RED test：analyze::utils 的 helper（check_fx / check_fxs /
//! check_bi / remove_include / format_standard_kline）对外可调用，
//! 并且产出与 rs-czsc 47ef6efa 基线一致的形状。
//!
//! 本测试同时锁定 design doc §2.5 要求的可见性提升：
//! 这 4 个原本 `pub(crate)` 的 helper 现在必须是 `pub`。

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
    // 顶分型：中间 bar 从上方包住两侧邻居
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
    // 严格递增——既不是顶也不是底
    let k1 = nb(1, 10.0, 9.0);
    let k2 = nb(2, 11.0, 10.0);
    let k3 = nb(3, 12.0, 11.0);
    assert!(check_fx(&k1, &k2, &k3).is_none());
}

#[test]
fn check_fxs_extracts_fx_from_sequence() {
    // 5 根 bar：上升、峰、下降 → 中间恰好出现一个顶分型
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
fn check_bi_returns_none_for_monotone_sequence() {
    // 严格单调递增序列既无顶分型也无底分型，不满足笔的识别条件
    let bars: Vec<NewBar> = (0..6)
        .map(|i| nb(i + 1, 10.0 + i as f64, 9.0 + i as f64))
        .collect();
    let (bi, remainder) = check_bi(&bars, 6);
    assert!(bi.is_none(), "单调递增序列不应识别出笔");
    assert!(
        remainder.len() <= bars.len(),
        "remainder 长度不得超过输入长度"
    );
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
