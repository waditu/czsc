use chrono::{Duration, TimeZone, Utc};
use czsc_core::objects::{
    bar::{RawBar, RawBarBuilder},
    freq::Freq,
    market::Market,
};
use czsc_trader::engine_v2::{
    compiler::{ExecutionPlan, ExecutionPlanInput},
    runtime::UnifiedExecEngine,
};
use czsc_trader::{sig_parse::SignalConfig, trader::CzscTrader};
use czsc_utils::bar_generator::BarGenerator;
use serde_json::json;

fn bars(freq: Freq, n: usize) -> Vec<RawBar> {
    let start = Utc.with_ymd_and_hms(2026, 1, 5, 0, 0, 0).unwrap();
    let minutes = if freq == Freq::F1 { 1 } else { 5 };
    let half_day = 120 / minutes;
    (0..n)
        .map(|i| {
            let slot = i % (2 * half_day);
            let minute = if slot < half_day {
                9 * 60 + 30 + (slot + 1) * minutes
            } else {
                13 * 60 + (slot - half_day + 1) * minutes
            };
            let close = 100.0 + (i as f64 * 0.19).sin() * 3.0 + (i as f64 * 0.013).cos() * 4.0;
            RawBarBuilder::default()
                .symbol("000001.SZ")
                .id(i as i32)
                .dt(start
                    + Duration::days((i / (2 * half_day)) as i64)
                    + Duration::minutes(minute as i64))
                .freq(freq)
                .open(close - 0.1)
                .close(close)
                .high(close + 0.3)
                .low(close - 0.3)
                .vol(1000.0)
                .amount(close * 1000.0)
                .build()
                .unwrap()
        })
        .collect()
}

fn configs() -> Vec<SignalConfig> {
    ["cat_macd_V230518", "cat_macd_V230520"]
        .into_iter()
        .map(|name| SignalConfig {
            name: name.to_string(),
            freq: None,
            params: [
                ("freq1".to_string(), json!("30分钟")),
                ("freq2".to_string(), json!("5分钟")),
            ]
            .into(),
        })
        .collect()
}

fn trader(input: &[RawBar]) -> CzscTrader {
    let base = input[0].freq;
    let bg = BarGenerator::new(
        base,
        vec![if base == Freq::F1 {
            Freq::F5
        } else {
            Freq::F30
        }],
        2000,
        Market::AShare,
    )
    .unwrap();
    for bar in &input[..299] {
        bg.update_bar(bar).unwrap();
    }
    CzscTrader::new("000001.SZ".to_string(), bg, vec![])
}

#[test]
fn cat_only_prepares_macd_in_the_frequency_owner() {
    let input = bars(Freq::F5, 500);
    let mut c = trader(&input);
    let cfg = configs();
    for bar in &input[299..] {
        c.update(bar, &cfg).unwrap();
    }
    for freq in ["30分钟", "5分钟"] {
        assert!(
            c.signals
                .ta_cache
                .get(freq)
                .and_then(|cache| cache.macd.get("MACD12#26#9"))
                .is_some(),
            "cat-only must use the {freq} owner cache"
        );
    }
}

fn assert_same_macd(left: &CzscTrader, right: &CzscTrader, freqs: &[&str]) {
    for freq in freqs {
        let left = &left.signals.ta_cache[*freq].macd["MACD12#26#9"];
        let right = &right.signals.ta_cache[*freq].macd["MACD12#26#9"];
        // MessagePack preserves f64 bits, including warmup NaNs.
        assert_eq!(
            rmp_serde::to_vec(left).unwrap(),
            rmp_serde::to_vec(right).unwrap(),
            "{freq}"
        );
    }
}

#[test]
fn joint_signals_preserve_kline_warmup_and_share_one_cache() {
    let input = bars(Freq::F5, 900);
    let kline: Vec<_> = ["30分钟", "5分钟"]
        .into_iter()
        .map(|freq| SignalConfig {
            name: "tas_macd_bc_V230804".to_string(),
            freq: Some(freq.to_string()),
            params: Default::default(),
        })
        .collect();
    let mut together = kline.clone();
    together.extend(configs());
    let joint = configs();
    let mut original = trader(&input);
    let mut combined = trader(&input);
    let mut cat_only = trader(&input);
    for bar in &input[299..] {
        original.update(bar, &kline).unwrap();
        combined.update(bar, &together).unwrap();
        cat_only.update(bar, &joint).unwrap();
        assert_same_macd(&original, &combined, &["30分钟", "5分钟"]);
        assert_same_macd(&original, &cat_only, &["30分钟", "5分钟"]);
        for (key, value) in &original.signals.s {
            assert_eq!(combined.signals.s.get(key), Some(value), "{key}");
        }
    }
}

#[test]
fn multiple_kline_consumers_do_not_advance_macd_warmup_twice() {
    let input = bars(Freq::F5, 305);
    let config = |name: &str| SignalConfig {
        name: name.to_string(),
        freq: Some("5分钟".to_string()),
        params: Default::default(),
    };
    let single = vec![config("tas_macd_bc_V230804")];
    let multiple = vec![
        config("tas_macd_bc_V230804"),
        config("tas_macd_base_V221028"),
    ];
    let reverse: Vec<_> = multiple.iter().rev().cloned().collect();
    let mut reference = trader(&input);
    let mut forward = trader(&input);
    let mut backward = trader(&input);
    for bar in &input[299..] {
        reference.update(bar, &single).unwrap();
        forward.update(bar, &multiple).unwrap();
        backward.update(bar, &reverse).unwrap();
        assert_same_macd(&reference, &forward, &["5分钟"]);
        assert_same_macd(&reference, &backward, &["5分钟"]);
        assert_eq!(forward.signals.s, backward.signals.s);
    }
}

#[test]
fn standalone_macd_cache_still_updates_across_bars() {
    let input = bars(Freq::F5, 301);
    let mut analysis = czsc_core::analyze::CZSC::new(input[..300].to_vec(), 50, 6);
    let mut cache = czsc_signals::types::TaCache::new();
    let key = "MACD12#26#9";
    czsc_signals::utils::ta::update_macd_cache(&analysis, key, 12, 26, 9, &mut cache);
    let before = cache.macd[key].macd.last().unwrap().to_bits();
    analysis.update_bar(input[300].clone());
    czsc_signals::utils::ta::update_macd_cache(&analysis, key, 12, 26, 9, &mut cache);
    assert_eq!(cache.macd[key].ids.last(), Some(&input[300].id));
    assert_ne!(cache.macd[key].macd.last().unwrap().to_bits(), before);
}

#[test]
fn restored_cat_only_cache_survives_repeated_tail_updates() {
    let input = bars(Freq::F5, 810);
    let cfg = configs();
    let mut original = trader(&input);
    for bar in &input[299..799] {
        original.update(bar, &cfg).unwrap();
    }
    let mut restored =
        CzscTrader::restore_state(&original.dump_state(&cfg, "mean").unwrap()).unwrap();
    assert!(
        restored
            .trader
            .signals
            .ta_cache
            .values()
            .all(|cache| cache.updated_macd_keys.is_none())
    );
    assert_same_macd(&original, &restored.trader, &["30分钟", "5分钟"]);
    for bar in &input[798..] {
        // Subsequent 5m inputs revise the same 30m tail; duplicate inputs must not refresh it.
        for _ in 0..2 {
            original.update(bar, &cfg).unwrap();
            restored
                .trader
                .update(bar, &restored.signals_config)
                .unwrap();
            assert_same_macd(&original, &restored.trader, &["30分钟", "5分钟"]);
            assert_eq!(original.signals.s, restored.trader.signals.s);
        }
    }
}

#[test]
fn compiled_and_dynamic_joint_signals_agree_with_explicit_and_default_frequencies() {
    for (base, use_defaults) in [(Freq::F5, false), (Freq::F1, true)] {
        let input = bars(base, 900);
        let mut cfg = configs();
        if use_defaults {
            for config in &mut cfg {
                config.params.clear();
            }
        }
        let position = serde_json::from_value(json!({
            "opens": [], "exits": [], "interval": 0, "timeout": 1,
            "stop_loss": 0.0, "T0": false, "name": "inactive", "symbol": "000001.SZ"
        }))
        .unwrap();
        let plan = ExecutionPlan::compile(ExecutionPlanInput {
            symbol: "000001.SZ".to_string(),
            base_freq: base.to_string(),
            signals_config: cfg.clone(),
            positions: vec![position],
            market: Some("A股".to_string()),
            bg_max_count: Some(2000),
            sdt: Some(input[298].dt.to_rfc3339()),
            include_sdt_bar: Some(false),
        })
        .unwrap();
        let compiled = UnifiedExecEngine::run(&plan, input.clone(), None, true, false).unwrap();
        let mut dynamic = trader(&input);
        dynamic.signals.prime_signals(&input[298], &cfg);
        let mut non_neutral = 0;
        for (bar, row) in input[299..].iter().zip(&compiled.signal_rows) {
            dynamic.update(bar, &cfg).unwrap();
            assert_eq!(
                &dynamic.signals.s, row,
                "default={use_defaults}, dt={}",
                bar.dt
            );
            non_neutral += row
                .iter()
                .filter(|(key, value)| key.contains("联立") && !value.starts_with("其他_"))
                .count();
        }
        assert_eq!(compiled.signal_rows.len(), input.len() - 299);
        assert!(
            non_neutral > 0,
            "must exercise actual joint MACD decisions, defaults={use_defaults}"
        );
        let freqs = if use_defaults {
            ["5分钟", "1分钟"]
        } else {
            ["30分钟", "5分钟"]
        };
        for freq in freqs {
            assert!(
                dynamic.signals.ta_cache[freq]
                    .macd
                    .contains_key("MACD12#26#9")
            );
        }
    }
}
