//! Phase C.2 — RED test: BarGenerator constructs, accepts seed bars via
//! init_freq_with_bars, refuses double init, and aggregates base-freq bars
//! into the higher freq via update_bar.

use std::sync::Arc;

use chrono::{TimeZone, Utc};
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
    assert!(bg.freq_bars.get(&Freq::F1).unwrap().read().len() >= 1);
    assert!(bg.freq_bars.get(&Freq::F30).unwrap().read().len() >= 1);
}

#[test]
fn symbol_returns_seed_symbol_after_update() {
    let bg = BarGenerator::new(Freq::F1, vec![Freq::F30], 100, Market::Default).unwrap();
    bg.update_bar(&bar(1_700_000_000, 10.0, 11.0, 12.0, 9.0))
        .unwrap();
    let sym = bg.symbol().expect("symbol should be available after update");
    assert_eq!(&*sym, "000001");
}
