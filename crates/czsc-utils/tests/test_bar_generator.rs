//! Phase C.2 — RED test: BarGenerator constructs, accepts seed bars via
//! init_freq_with_bars, refuses double init, and aggregates base-freq bars
//! into the higher freq via update_bar.

use std::sync::Arc;

use chrono::{NaiveDateTime, TimeZone, Utc};
use czsc_core::objects::bar::{RawBar, RawBarBuilder};
use czsc_core::objects::freq::Freq;
use czsc_core::objects::market::Market;
use czsc_utils::bar_generator::BarGenerator;

fn bar(ts: i64, open: f64, close: f64, high: f64, low: f64) -> RawBar {
    RawBarBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .freq(Freq::F1)
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

#[test]
fn new_constructs_with_freq_keys() {
    let bg = BarGenerator::new(Freq::F1, vec![Freq::F30], 100, Market::Default).unwrap();
    assert!(bg.freq_bars.contains_key(&Freq::F1));
    assert!(bg.freq_bars.contains_key(&Freq::F30));
}

#[test]
fn init_freq_with_bars_populates_seed_data() {
    let mut bg = BarGenerator::new(Freq::F1, vec![Freq::F30], 100, Market::Default).unwrap();
    let seed = vec![bar(1_700_000_000, 10.0, 11.0, 12.0, 9.0)];
    bg.init_freq_with_bars(Freq::F30, seed).unwrap();
    assert_eq!(bg.freq_bars.get(&Freq::F30).unwrap().read().len(), 1);
}

#[test]
fn init_freq_with_bars_rejects_unknown_freq() {
    let mut bg = BarGenerator::new(Freq::F1, vec![Freq::F30], 100, Market::Default).unwrap();
    let seed = vec![bar(1_700_000_000, 10.0, 11.0, 12.0, 9.0)];
    assert!(bg.init_freq_with_bars(Freq::F60, seed).is_err());
}

#[test]
fn init_freq_with_bars_rejects_double_init() {
    let mut bg = BarGenerator::new(Freq::F1, vec![Freq::F30], 100, Market::Default).unwrap();
    bg.init_freq_with_bars(Freq::F30, vec![bar(1_700_000_000, 10.0, 11.0, 12.0, 9.0)])
        .unwrap();
    let res = bg.init_freq_with_bars(Freq::F30, vec![bar(1_700_000_060, 11.0, 12.0, 13.0, 10.0)]);
    assert!(res.is_err());
}

#[test]
fn update_bar_appends_for_new_freq_window() {
    let bg = BarGenerator::new(Freq::F1, vec![Freq::F30], 100, Market::Default).unwrap();
    bg.update_bar(&bar(1_700_000_000, 10.0, 11.0, 12.0, 9.0))
        .unwrap();
    // Both freq queues received a bar
    assert!(!bg.freq_bars.get(&Freq::F1).unwrap().read().is_empty());
    assert!(!bg.freq_bars.get(&Freq::F30).unwrap().read().is_empty());
}

#[test]
fn symbol_returns_seed_symbol_after_update() {
    let bg = BarGenerator::new(Freq::F1, vec![Freq::F30], 100, Market::Default).unwrap();
    bg.update_bar(&bar(1_700_000_000, 10.0, 11.0, 12.0, 9.0))
        .unwrap();
    let sym = bg
        .symbol()
        .expect("symbol should be available after update");
    assert_eq!(&*sym, "000001");
}

// Natural QMT 605169.SH opening bars; prices/amount in yuan, volume in shares.
// The 09:30 auction label is distinct from the first continuous minute at 09:31.
fn opening_bars() -> Vec<RawBar> {
    include_str!("fixtures/qmt_opening_1m.csv")
        .lines()
        .skip(1)
        .enumerate()
        .map(|(i, line)| {
            let fields: Vec<_> = line.split(',').collect();
            let dt = NaiveDateTime::parse_from_str(fields[0], "%Y-%m-%dT%H:%M:%S").unwrap();
            let values: Vec<f64> = fields[1..].iter().map(|s| s.parse().unwrap()).collect();
            RawBarBuilder::default()
                .symbol(Arc::<str>::from("605169.SH"))
                .dt(Utc.from_utc_datetime(&dt))
                .freq(Freq::F1)
                .id(i as i32)
                .open(values[0])
                .high(values[1])
                .low(values[2])
                .close(values[3])
                .vol(values[4])
                .amount(values[5])
                .build()
                .unwrap()
        })
        .collect()
}

#[test]
fn opening_minutes_keep_identity_and_aggregate_once() {
    let bars = opening_bars();
    for market in [Market::AShare, Market::Default, Market::Futures] {
        let bg = BarGenerator::new(Freq::F1, vec![Freq::F5, Freq::F30], 100, market).unwrap();
        for input in &bars {
            bg.update_bar(input).unwrap();
            bg.update_bar(input).unwrap(); // Re-delivery must not count the auction twice.
        }
        let base: Vec<_> = bg.freq_bars[&Freq::F1].read().iter().cloned().collect();
        assert_eq!(base, bars, "base minute identity changed for {market:?}");
        for (freq, last_label) in [(Freq::F5, "09:35"), (Freq::F30, "10:00")] {
            let derived = bg.freq_bars[&freq].read();
            let all_in_one = market == Market::AShare;
            assert_eq!(derived.len(), if all_in_one { 1 } else { 2 });
            if !all_in_one {
                assert_eq!(derived[0].dt.format("%H:%M").to_string(), "09:30");
                assert_eq!(derived[0].vol, 11_700.0);
                assert_eq!(derived[0].amount, 153_270.0);
            }
            let last = derived.back().unwrap();
            assert_eq!(last.dt.format("%H:%M").to_string(), last_label);
            assert_eq!(
                (last.open, last.high, last.low, last.close),
                (13.10, 13.14, 12.98, 13.09)
            );
            assert_eq!(last.vol, if all_in_one { 474_500.0 } else { 462_800.0 });
            assert_eq!(
                last.amount,
                if all_in_one { 6_192_515.0 } else { 6_039_245.0 }
            );
        }
    }
}

#[test]
fn minute_base_keeps_supplied_label_without_changing_derived_calendar() {
    for (freq, stamp) in [
        (Freq::F1, "2026-09-29T09:31:20"),
        (Freq::F5, "2026-09-29T09:36:00"),
    ] {
        let mut input = opening_bars()[0].clone();
        input.freq = freq;
        input.dt = Utc
            .from_utc_datetime(&NaiveDateTime::parse_from_str(stamp, "%Y-%m-%dT%H:%M:%S").unwrap());
        let bg = BarGenerator::new(freq, vec![Freq::F30], 100, Market::AShare).unwrap();
        bg.update_bar(&input).unwrap();
        assert_eq!(bg.freq_bars[&freq].read()[0].dt, input.dt);
        assert_eq!(
            bg.freq_bars[&Freq::F30].read()[0]
                .dt
                .format("%H:%M:%S")
                .to_string(),
            "10:00:00"
        );
    }
}

#[test]
fn calendar_bases_keep_existing_date_normalization() {
    for (freq, expected_date) in [
        (Freq::D, "2026-09-29"),
        (Freq::W, "2026-10-02"),
        (Freq::M, "2026-09-30"),
    ] {
        let mut input = opening_bars()[0].clone();
        input.freq = freq;
        input.dt = Utc.with_ymd_and_hms(2026, 9, 29, 15, 0, 0).unwrap();
        let bg = BarGenerator::new(freq, vec![Freq::Y], 100, Market::AShare).unwrap();
        bg.update_bar(&input).unwrap();
        assert_eq!(
            bg.freq_bars[&freq].read()[0]
                .dt
                .format("%Y-%m-%d %H:%M:%S")
                .to_string(),
            format!("{expected_date} 00:00:00")
        );
        assert_eq!(
            bg.freq_bars[&Freq::Y].read()[0]
                .dt
                .format("%Y-%m-%d %H:%M:%S")
                .to_string(),
            "2026-12-31 00:00:00"
        );
    }
}
