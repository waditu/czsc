//! Phase D.A — RED test：CZSC 分析器从 RawBar 流构造，
//! 暴露 bars_raw / bars_ubi / bi_list / fx_list，并能正确处理
//! 增量的 update_bar 输入。

use std::sync::Arc;

use chrono::{NaiveDateTime, TimeZone, Utc};
use czsc_core::analyze::{CZSC, CZSCBuilder};
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

fn seeded_bars(seed: u64, n: usize) -> Vec<RawBar> {
    let mut state = seed;
    let mut price = 100.0;
    (0..n)
        .map(|i| {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
            let delta = ((state >> 32) as i32 % 200) as f64 / 100.0;
            price += delta;
            let spread = 0.5 + ((state >> 48) % 100) as f64 / 100.0;
            rb(
                1_700_000_000 + (i as i64) * 1800,
                price - 0.1,
                price + 0.1,
                price + spread,
                price - spread,
            )
        })
        .collect()
}

#[test]
fn new_populates_symbol_and_freq() {
    let bars = synthetic_zigzag(50);
    let c = CZSC::new(bars, 50, 6);
    assert_eq!(&*c.symbol, "000001");
    assert_eq!(c.freq, Freq::F30);
    assert_eq!(c.max_bi_num, 50);
}

#[test]
fn new_consumes_all_bars_and_builds_ubi() {
    let bars = synthetic_zigzag(40);
    let c = CZSC::new(bars, 50, 6);
    // bars_ubi 是合并后 bar（NewBar）序列；对于 40 根原始 zigzag
    // bar，我们期望合并后的序列非空
    assert!(!c.bars_ubi.is_empty(), "bars_ubi should not be empty");
}

#[test]
fn fx_and_bi_lists_are_consistent_with_zigzag() {
    let bars = synthetic_zigzag(60);
    let c = CZSC::new(bars, 50, 6);
    let fxs = c.get_fx_list();
    // 60 根 zigzag bar 的正弦波形必须产出至少 2 个分型（顶底交替）
    assert!(
        fxs.len() >= 2,
        "60 根 zigzag 应至少产出 2 个分型，实际 {}",
        fxs.len()
    );
    assert!(fxs.len() <= 60, "分型数量不得超过 bar 数");
    // 有分型则必然有笔；max_bi_num=50 为上界
    assert!(
        !c.bi_list.is_empty(),
        "有分型时应至少识别出 1 笔，实际 {}",
        c.bi_list.len()
    );
    assert!(c.bi_list.len() <= 50, "笔数量不得超过 max_bi_num=50");
}

#[test]
fn update_bar_appends_incrementally() {
    let bars = synthetic_zigzag(30);
    let mut c = CZSC::new(bars, 50, 6);
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
    let c = CZSC::new(bars, 50, 6);
    let d = c.clone();
    assert_eq!(d.bi_list.len(), c.bi_list.len());
    assert_eq!(&*d.symbol, &*c.symbol);
}

#[test]
fn fx_list_deduplicates_shared_endpoint_between_finished_bis() {
    let c = CZSC::new(seeded_bars(1, 80), 50, 6);
    assert!(c.bi_list.len() >= 2);

    let shared = c.bi_list[0].fxs.last().unwrap();
    assert_eq!(shared, &c.bi_list[1].fxs[1]);

    let fxs = c.get_fx_list();
    assert_eq!(fxs.iter().filter(|fx| fx.dt == shared.dt).count(), 1);
    assert_eq!(fxs.iter().find(|fx| fx.dt == shared.dt).unwrap(), shared);
    assert!(fxs.windows(2).all(|pair| pair[0].dt < pair[1].dt));
    assert!(fxs.windows(2).all(|pair| pair[0].mark != pair[1].mark));
}

#[test]
fn fx_list_deduplicates_bi_to_ubi_boundary_and_keeps_later_ubi_fx() {
    let c = CZSC::new(seeded_bars(1, 26), 50, 6);
    let last_bi_fx = c.bi_list.last().unwrap().fxs.last().unwrap();
    let ubi_fxs = c.get_ubi_fxs().unwrap();
    assert_eq!(ubi_fxs.first().unwrap().dt, last_bi_fx.dt);
    let later_ubi_fx = ubi_fxs.iter().find(|fx| fx.dt > last_bi_fx.dt).unwrap();

    let fxs = c.get_fx_list();
    assert_eq!(fxs.iter().filter(|fx| fx.dt == last_bi_fx.dt).count(), 1);
    assert!(fxs.iter().any(|fx| fx == later_ubi_fx));
    assert_eq!(fxs.last().unwrap(), later_ubi_fx);
    assert!(fxs.windows(2).all(|pair| pair[0].dt < pair[1].dt));
}

/// min_bi_len 必须真正作用于成笔逻辑：更大的阈值会过滤掉更短的笔，
/// 因此 bi_list 数量应单调不增。这是 issue #328 的回归保护——
/// 之前该值在 check_bi 里被硬编码为 6，外部传入完全失效。
#[test]
fn min_bi_len_affects_bi_count() {
    let bars = synthetic_zigzag(60);
    let small = CZSC::new(bars.clone(), 50, 6);
    let large = CZSC::new(bars, 50, 11);
    assert!(
        large.bi_list.len() <= small.bi_list.len(),
        "min_bi_len=11 不应比 min_bi_len=6 产出更多笔：{} > {}",
        large.bi_list.len(),
        small.bi_list.len()
    );
    // 所有成笔长度必须 >= 其 min_bi_len 阈值
    for bi in &small.bi_list {
        assert!(
            bi.bars.len() >= 6,
            "短阈值下出现 <6 的笔：{}",
            bi.bars.len()
        );
    }
    for bi in &large.bi_list {
        assert!(
            bi.bars.len() >= 11,
            "长阈值下出现 <11 的笔：{}",
            bi.bars.len()
        );
    }
}

fn natural_tail_fixture() -> (Vec<RawBar>, Vec<RawBar>) {
    let data: serde_json::Value =
        serde_json::from_str(include_str!("fixtures/tail_revision_605169_20260924.json")).unwrap();
    let bar = |row: &serde_json::Value, id: i32| {
        RawBarBuilder::default()
            .symbol(Arc::<str>::from(data["symbol"].as_str().unwrap()))
            .dt(
                NaiveDateTime::parse_from_str(row["dt"].as_str().unwrap(), "%Y-%m-%dT%H:%M:%S")
                    .unwrap()
                    .and_utc(),
            )
            .freq(Freq::F30)
            .id(id)
            .open(row["open"].as_f64().unwrap())
            .close(row["close"].as_f64().unwrap())
            .high(row["high"].as_f64().unwrap())
            .low(row["low"].as_f64().unwrap())
            .vol(row["volume"].as_f64().unwrap())
            .amount(row["amount"].as_f64().unwrap())
            .build()
            .unwrap()
    };
    let prefix: Vec<_> = data["prefix_30f"]
        .as_array()
        .unwrap()
        .iter()
        .enumerate()
        .map(|(i, row)| bar(row, i as i32))
        .collect();
    let parts = data["tail_native_5m"].as_array().unwrap();
    let end = bar(parts.last().unwrap(), prefix.len() as i32).dt;
    let mut versions: Vec<RawBar> = Vec::new();
    for row in parts {
        let mut next = bar(row, prefix.len() as i32);
        next.dt = end;
        if let Some(previous) = versions.last() {
            next.open = previous.open;
            next.high = previous.high.max(next.high);
            next.low = previous.low.min(next.low);
            next.vol += previous.vol;
            next.amount += previous.amount;
        }
        versions.push(next);
    }
    (prefix, versions)
}

fn assert_same_analysis(actual: &CZSC, expected: &CZSC) {
    // Compare complete structures, including nested OHLCV and FX elements.
    assert_eq!(actual.bars_raw, expected.bars_raw, "bars_raw");
    assert_eq!(actual.bars_ubi, expected.bars_ubi, "bars_ubi");
    assert_eq!(actual.bi_list, expected.bi_list, "bi_list");
    assert_eq!(actual.get_fx_list(), expected.get_fx_list(), "fx_list");
}

#[test]
fn tail_revision_retracts_a_bi_when_equal_high_changes_inclusion() {
    let (prefix, versions) = natural_tail_fixture();
    assert_eq!((versions[4].high, versions[5].high), (13.04, 13.05));
    for limit in [1, 50, 1000] {
        let mut c = CZSC::new(prefix.clone(), limit, 6);
        c.update_bar(versions[4].clone());
        assert_eq!(c.bi_list.len(), 1, "partial bar confirms a temporary BI");
        assert_eq!(c.bars_ubi.len(), 3);

        c.update_bar(versions[5].clone());
        let mut closed = prefix.clone();
        closed.push(versions[5].clone());
        let expected = CZSC::new(closed, limit, 6);
        assert!(
            expected.bi_list.is_empty(),
            "equal high retracts the top FX"
        );
        assert_same_analysis(&c, &expected);
    }
}

#[test]
fn repeated_tail_revisions_clone_and_serde_match_each_closed_snapshot() {
    let (prefix, versions) = natural_tail_fixture();
    let mut partial = prefix.clone();
    partial.push(versions[4].clone());
    let original = CZSC::new(partial, 1, 6);
    let encoded = serde_json::to_vec(&original).unwrap();
    let restored: CZSC = serde_json::from_slice(&encoded).unwrap();
    assert_same_analysis(&restored, &original);

    for mut c in [original.clone(), restored] {
        // Replacements may repeat, retract a provisional bar, and extend again.
        for index in [4, 5, 5, 0, 1, 2, 3, 4, 5] {
            c.update_bar(versions[index].clone());
            let mut closed = prefix.clone();
            closed.push(versions[index].clone());
            assert_same_analysis(&c, &CZSC::new(closed, 1, 6));
        }
    }
    assert_eq!(
        original.bi_list.len(),
        1,
        "clones must not mutate their source"
    );
}

#[test]
fn tail_revision_restores_pruned_bars_and_bis() {
    let bars = seeded_bars(1, 200);
    let mut c = CZSC::new(bars[..1].to_vec(), 1, 6);
    let mut pruning_count = 0;
    let mut removed_bi_count = 0;
    for i in 1..bars.len() {
        let previous_first = c.bars_raw[0].dt;
        c.update_bar(bars[i].clone());
        if c.bars_raw[0].dt > previous_first {
            pruning_count += 1;
        }
        let mut revised = bars[i].clone();
        // A wider version can destroy a new or previous BI and change inclusion.
        revised.high = bars[i - 1].high.max(revised.high) + 3.0;
        revised.low = bars[i - 1].low.min(revised.low) - 3.0;
        let mut expected_bars = bars[..i].to_vec();
        expected_bars.push(revised.clone());
        let expected = CZSC::new(expected_bars, 1, 6);
        if expected.bi_list.len() < c.bi_list.len() {
            removed_bi_count += 1;
        }

        let mut restored: CZSC = serde_json::from_slice(&serde_json::to_vec(&c).unwrap()).unwrap();
        for analyzer in [&mut c, &mut restored] {
            analyzer.update_bar(revised.clone());
            assert_same_analysis(analyzer, &expected);
            analyzer.update_bar(bars[i].clone());
            assert_same_analysis(analyzer, &CZSC::new(bars[..=i].to_vec(), 1, 6));
        }
    }
    assert!(pruning_count > 3, "exercise repeated retention pruning");
    assert!(removed_bi_count > 0, "exercise retraction after pruning");
}

#[test]
fn closed_bar_updates_match_constructor() {
    let (prefix, versions) = natural_tail_fixture();
    let bars: Vec<_> = prefix.into_iter().chain([versions[5].clone()]).collect();
    let mut c = CZSC::new(bars[..1].to_vec(), 1, 6);
    for bar in &bars[1..] {
        c.update_bar(bar.clone());
    }
    assert_same_analysis(&c, &CZSC::new(bars, 1, 6));
}

#[test]
fn snapshots_require_tail_state_and_builder_starts_empty() {
    let (prefix, versions) = natural_tail_fixture();
    let c = CZSC::new(prefix, 1, 6);
    let mut missing = serde_json::to_value(&c).unwrap();
    missing.as_object_mut().unwrap().remove("tail_update");
    let error = serde_json::from_value::<CZSC>(missing).unwrap_err();
    assert!(error.to_string().contains("tail_update"));

    let mut builder = CZSCBuilder::default();
    builder
        .symbol(Arc::<str>::from("605169.SH"))
        .freq(Freq::F30)
        .max_bi_num(1)
        .min_bi_len(6)
        .bars_raw(vec![])
        .bars_ubi(vec![])
        .bi_list(vec![]);
    let empty = builder.build().unwrap();
    let mut restored: CZSC = serde_json::from_slice(&serde_json::to_vec(&empty).unwrap()).unwrap();
    for bar in versions {
        restored.update_bar(bar.clone());
        assert_same_analysis(&restored, &CZSC::new(vec![bar], 1, 6));
    }
    builder.bars_raw(c.bars_raw);
    assert!(
        builder
            .build()
            .unwrap_err()
            .to_string()
            .contains("CZSC::new")
    );
}
