use chrono::{Duration, TimeZone, Utc};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBarBuilder;
use czsc_core::objects::freq::Freq;
use czsc_signals::registry::{
    SIGNAL_REGISTRY, TRADER_SIGNAL_REGISTRY, list_generated_signal_descriptors,
};
use czsc_signals::types::{SignalFnRef, TaCache};
use czsc_trader::sig_parse::SignalConfig;
use serde_json::{Value, json};
use std::collections::{HashMap, HashSet};

fn context() -> CZSC {
    let bar = RawBarBuilder::default()
        .symbol("T")
        .id(1)
        .dt(Utc.with_ymd_and_hms(2026, 10, 14, 9, 35, 0).unwrap())
        .freq(Freq::F60)
        .open(1.0)
        .close(1.0)
        .high(1.0)
        .low(1.0)
        .vol(1.0)
        .amount(1.0)
        .build()
        .unwrap();
    CZSC::new(vec![bar], 50, 6)
}

fn price_change_context(di: usize, close: f64) -> CZSC {
    let mut closes = vec![100.0; 160];
    let target = closes.len() - di;
    closes[target] = close;
    let start = Utc.with_ymd_and_hms(2026, 10, 1, 9, 0, 0).unwrap();
    let bars = closes
        .into_iter()
        .enumerate()
        .map(|(index, close)| {
            RawBarBuilder::default()
                .symbol("T")
                .id(index as i32)
                .dt(start + Duration::hours(index as i64))
                .freq(Freq::F60)
                .open(close)
                .close(close)
                .high(close + 1.0)
                .low(close - 1.0)
                .vol(1.0)
                .amount(1.0)
                .build()
                .unwrap()
        })
        .collect();
    CZSC::new(bars, 50, 6)
}

#[test]
fn test_zdf_multi_digit_di_params_and_complete_signals_round_trip() {
    let name = "bar_zdf_V221203";
    let meta = &SIGNAL_REGISTRY[name];
    for di in [10, 11, 100] {
        for mode in ["ZF", "DF"] {
            for (change, expected_value) in [(4.5, "满足"), (1.0, "其他")] {
                let close = if mode == "ZF" {
                    100.0 + change
                } else {
                    100.0 - change
                };
                let context = price_change_context(di, close);
                assert_eq!(context.bars_raw.len(), 160);
                let params: HashMap<String, Value> =
                    serde_json::from_value(json!({"di": di, "mode": mode, "span": "300,600"}))
                        .unwrap();
                let original = (meta.func)(&context, &params, &mut TaCache::default());
                assert_eq!(original.len(), 1);
                assert_eq!(
                    original[0].key(),
                    format!("60分钟_D{di}{mode}_300至600V221203")
                );
                assert_eq!(original[0].value(), format!("{expected_value}_任意_任意_0"));
                let config = SignalConfig::from_signal_str(&original[0].to_string()).unwrap();
                assert_eq!(config.name, name);
                assert_eq!(config.freq.as_deref(), Some("60分钟"));
                let replayed = (meta.func)(&context, &config.params, &mut TaCache::default());
                assert_eq!(replayed.len(), 1);
                assert_eq!(replayed[0].to_string(), original[0].to_string());
                assert_eq!(config.params, params);
            }
        }
    }
}

#[test]
fn test_adjacent_ma_params_and_complete_signals_round_trip() {
    for name in [
        "tas_ma_base_V221101",
        "tas_ma_base_V221203",
        "tas_second_bs_V230303",
    ] {
        let meta = &SIGNAL_REGISTRY[name];
        for di in [10, 11, 100] {
            for ma_type in ["SMA", "EMA", "WMA"] {
                for (close, direction) in [(104.5, "多头_向上"), (95.5, "空头_向下")] {
                    let context = price_change_context(di, close);
                    let mut params: HashMap<String, Value> = serde_json::from_value(
                        json!({"di": di, "ma_type": ma_type, "timeperiod": 5}),
                    )
                    .unwrap();
                    if name == "tas_ma_base_V221203" {
                        params.insert("th".to_string(), json!(100));
                    }
                    let original = (meta.func)(&context, &params, &mut TaCache::default());
                    assert_eq!(original.len(), 1);
                    if name != "tas_second_bs_V230303" {
                        let distance = if name == "tas_ma_base_V221203" {
                            "远离"
                        } else {
                            "任意"
                        };
                        assert_eq!(original[0].value(), format!("{direction}_{distance}_0"));
                    }
                    let config = SignalConfig::from_signal_str(&original[0].to_string()).unwrap();
                    assert_eq!(config.name, name);
                    assert_eq!(config.freq.as_deref(), Some("60分钟"));
                    assert_eq!(config.params, params);
                    let replayed = (meta.func)(&context, &config.params, &mut TaCache::default());
                    assert_eq!(replayed.len(), 1);
                    assert_eq!(replayed[0].to_string(), original[0].to_string());
                }
            }
        }
    }
}

#[test]
fn test_versioned_default_and_empty_keys_match_templates() {
    let contracts = [
        (
            "bar_operate_span_V221111",
            "T0935#1450_时间区间V221111",
            json!({"t1": "0935", "t2": "1450"}),
        ),
        (
            "bar_mean_amount_V221112",
            "D1K10B均额_1至4千万V221112",
            json!({"n": 10, "th1": 1, "th2": 4}),
        ),
        (
            "bar_zdf_V221203",
            "D1ZF_300至600V221203",
            json!({"mode": "ZF", "t1": 300, "t2": 600}),
        ),
        (
            "bar_amount_acc_V230214",
            "D2N5_累计超10千万V230214",
            json!({"di": 2, "n": 5, "t": 10}),
        ),
        ("bar_single_V230214", "D1T10_状态V230214", json!({"t": 10})),
        (
            "bar_big_solid_V230215",
            "D1N20_MIDV230215",
            json!({"n": 20}),
        ),
        (
            "bar_section_momentum_V221112",
            "D1K10B_阈值100BPV221112",
            json!({"n": 10, "th": 100}),
        ),
        (
            "bar_vol_bs1_V230224",
            "D1N20量价_BS1辅助V230224",
            json!({"n": 20}),
        ),
        (
            "bar_fake_break_V230204",
            "D1N20M5_假突破V230204",
            json!({"n": 20, "m": 5}),
        ),
        (
            "bar_channel_V230508",
            "D1M600_通道V230508",
            json!({"m": 600}),
        ),
        ("cxt_fx_power_V221107", "D1F_分型强弱V221107", json!({})),
        ("cxt_first_buy_V221126", "D1B_BUY1V221126", json!({})),
        ("cxt_first_sell_V221126", "D1B_SELL1V221126", json!({})),
        ("coo_td_V221110", "D1K_TDV221110", json!({})),
        ("byi_symmetry_zs_V221107", "D1B_对称中枢V221107", json!({})),
        (
            "jcc_san_xing_xian_V221023",
            "D1TH200_伞形线V221023",
            json!({"th": 200}),
        ),
        ("jcc_ten_mo_V221028", "D1_吞没形态V221028", json!({})),
        (
            "jcc_wu_yun_gai_ding_V221101",
            "D1Z500TH50_乌云盖顶V221101",
            json!({"z": 500, "th": 50}),
        ),
        (
            "jcc_ci_tou_V221101",
            "D1Z100TH50_刺透形态V221101",
            json!({"z": 100, "th": 50}),
        ),
        ("jcc_san_fa_V20221118", "D1K_三法AV20221118", json!({})),
        ("jcc_san_fa_V20221115", "D1K_三法V20221115", json!({})),
        (
            "jcc_xing_xian_V221118",
            "D2TH2_星形线V221118",
            json!({"di": 2, "th": 2}),
        ),
        (
            "jcc_fen_shou_xian_V20221113",
            "D1K_分手线V20221113",
            json!({}),
        ),
        (
            "jcc_zhu_huo_xian_V221027",
            "D1T2.0F500_烛火线V221027",
            json!({"th": "2.0", "zf": 500}),
        ),
        ("jcc_yun_xian_V221118", "D1_孕线V221118", json!({})),
        (
            "jcc_ping_tou_V221113",
            "D2TH100_平头形态V221113",
            json!({"di": 2, "th": 100}),
        ),
        ("jcc_two_crow_V221108", "D1K_两只乌鸦V221108", json!({})),
        ("jcc_three_crow_V221108", "D1_三只乌鸦V221108", json!({})),
        ("jcc_szx_V221111", "D1TH10_十字线V221111", json!({"th": 10})),
        (
            "jcc_san_szx_V221122",
            "D1T10_三星V221122",
            json!({"th": 10}),
        ),
        ("jcc_fan_ji_xian_V221121", "D1_反击线V221121", json!({})),
        ("jcc_shan_chun_V221121", "D1B_山川形态V221121", json!({})),
        ("jcc_gap_yin_yang_V221121", "D1K_并列阴阳V221121", json!({})),
        ("jcc_ta_xing_V221124", "D1K_塔形V221124", json!({})),
    ];
    assert_eq!(contracts.len(), 34);
    for (name, versioned_key, bindings) in contracts {
        let meta = &SIGNAL_REGISTRY[name];
        let expected_key = format!("60分钟_{versioned_key}");
        let mut values = json!({"freq": "60分钟", "di": 1});
        values
            .as_object_mut()
            .unwrap()
            .extend(bindings.as_object().unwrap().clone());
        let mut instantiated = meta.param_template.to_string();
        for (param, value) in values.as_object().unwrap() {
            let value = value
                .as_str()
                .map(str::to_string)
                .unwrap_or_else(|| value.to_string());
            instantiated = instantiated.replace(&format!("{{{param}}}"), &value);
        }
        assert_eq!(instantiated, expected_key, "{name} template");
        for empty in [false, true] {
            let mut context = context();
            if empty {
                context.bars_raw.clear();
            }
            let signals = (meta.func)(&context, &HashMap::new(), &mut TaCache::default());
            assert_eq!(signals.len(), 1, "{name}, empty={empty}");
            assert_eq!(signals[0].key(), expected_key, "{name}, empty={empty}");
            let config = SignalConfig::from_signal_str(&signals[0].to_string())
                .unwrap_or_else(|| panic!("{name}: {}", signals[0]));
            assert_eq!(config.name, name);
            assert_eq!(config.freq.as_deref(), Some("60分钟"));
            let restored = (meta.func)(&context, &config.params, &mut TaCache::default());
            assert_eq!(restored[0].key(), expected_key, "{name} round trip");
        }
    }
}

#[test]
fn test_dynamic_k3_params_round_trip() {
    for (name, key, params) in [
        (
            "bar_mean_amount_V221112",
            "D1K10B均额_1至4千万V221112",
            json!({"di": 1, "n": 10, "th1": 1, "th2": 4}),
        ),
        (
            "bar_mean_amount_V221112",
            "D2K7B均额_2至8千万V221112",
            json!({"di": 2, "n": 7, "th1": 2, "th2": 8}),
        ),
        (
            "bar_zdf_V221203",
            "D1ZF_300至600V221203",
            json!({"di": 1, "mode": "ZF", "span": "300,600"}),
        ),
        (
            "bar_zdf_V221203",
            "D3DF_125至875V221203",
            json!({"di": 3, "mode": "DF", "span": "125,875"}),
        ),
        (
            "bar_amount_acc_V230214",
            "D2N5_累计超10千万V230214",
            json!({"di": 2, "n": 5, "t": 10}),
        ),
        (
            "bar_amount_acc_V230214",
            "D1N7_累计超25千万V230214",
            json!({"di": 1, "n": 7, "t": 25}),
        ),
        (
            "bar_section_momentum_V221112",
            "D1K10B_阈值100BPV221112",
            json!({"di": 1, "n": 10, "th": 100}),
        ),
        (
            "bar_section_momentum_V221112",
            "D2K7B_阈值250BPV221112",
            json!({"di": 2, "n": 7, "th": 250}),
        ),
    ] {
        let key = format!("60分钟_{key}");
        let config = SignalConfig::from_signal_str(&format!("{key}_其他_任意_任意_0"))
            .unwrap_or_else(|| panic!("{name}: {key}"));
        assert_eq!(config.name, name);
        assert_eq!(config.freq.as_deref(), Some("60分钟"));
        let expected_params: HashMap<String, Value> = serde_json::from_value(params).unwrap();
        assert_eq!(config.params, expected_params, "{name}");
        let signals =
            (SIGNAL_REGISTRY[name].func)(&context(), &config.params, &mut TaCache::default());
        assert_eq!(signals.len(), 1);
        assert_eq!(signals[0].key(), key, "{name} round trip");
    }
}

#[test]
fn test_time_span_params_keep_hhmm_strings() {
    for (start, end) in [("0935", "1450"), ("1000", "1100"), ("0000", "0030")] {
        let key = format!("60分钟_T{start}#{end}_时间区间V221111");
        let config = SignalConfig::from_signal_str(&format!("{key}_是_任意_任意_0")).unwrap();
        assert_eq!(config.name, "bar_operate_span_V221111");
        assert_eq!(config.params["t1"], json!(start));
        assert_eq!(config.params["t2"], json!(end));
        let signals = (SIGNAL_REGISTRY[config.name.as_str()].func)(
            &context(),
            &config.params,
            &mut TaCache::default(),
        );
        assert_eq!(signals[0].key(), key);
    }
}

#[test]
fn test_san_xing_xian_threshold_round_trip() {
    for (encoded, threshold) in [
        (200, 2.0),
        (250, 2.5),
        (150, 1.5),
        (115, 1.15),
        (-115, -1.15),
    ] {
        let key = format!("60分钟_D1TH{encoded}_伞形线V221023");
        let config = SignalConfig::from_signal_str(&format!("{key}_满足_任意_任意_0")).unwrap();
        assert_eq!(config.name, "jcc_san_xing_xian_V221023");
        assert!((config.params["th"].as_f64().unwrap() - threshold).abs() < 1e-12);
        let signals = (SIGNAL_REGISTRY[config.name.as_str()].func)(
            &context(),
            &config.params,
            &mut TaCache::default(),
        );
        assert_eq!(signals[0].key(), key);
    }
}

#[test]
fn test_parser_rejects_mismatched_contracts() {
    for signal in [
        "60分钟_T0935#1450_时间区间_是_任意_任意_0",
        "60分钟_D1M600_通道V230507_其他_任意_任意_0",
        "60分钟_D1K10B均额_1至4亿_其他_任意_任意_0",
        "60分钟_D1错误_累计超10千万_其他_任意_任意_0",
        "60分钟_D1K10B_阈值100BP_其他_任意_0",
    ] {
        assert!(SignalConfig::from_signal_str(signal).is_none(), "{signal}");
    }
}

#[test]
fn test_all_descriptors_are_unique_and_registered() {
    let descriptors = list_generated_signal_descriptors();
    assert!(descriptors.len() >= 246);
    assert_eq!(
        descriptors.len(),
        SIGNAL_REGISTRY.len() + TRADER_SIGNAL_REGISTRY.len()
    );
    let mut names = HashSet::new();
    let mut opcodes = HashSet::new();
    for descriptor in descriptors {
        let version = descriptor.name.rsplit_once("_V").unwrap().1;
        let k3 = descriptor.template.rsplit('_').next().unwrap();
        let digits_start = k3
            .trim_end_matches(|character: char| character.is_ascii_digit())
            .len();
        assert_eq!(&k3[digits_start..], version, "{}", descriptor.name);
        assert!(names.insert(descriptor.name), "{}", descriptor.name);
        assert!(opcodes.insert(descriptor.opcode), "{}", descriptor.opcode);
        match descriptor.func_ref {
            SignalFnRef::Kline(_) => {
                assert_eq!(descriptor.category, "kline");
                assert_eq!(
                    SIGNAL_REGISTRY[descriptor.name].param_template,
                    descriptor.template
                );
            }
            SignalFnRef::Trader(_) => {
                assert_eq!(descriptor.category, "trader");
                assert_eq!(
                    TRADER_SIGNAL_REGISTRY[descriptor.name].param_template,
                    descriptor.template
                );
            }
        }
    }
}

#[test]
fn test_strategy_conditions_require_versioned_keys() {
    let context = context();
    let output = (SIGNAL_REGISTRY["bar_operate_span_V221111"].func)(
        &context,
        &HashMap::new(),
        &mut TaCache::default(),
    );
    let signals = HashMap::from([(output[0].key(), output[0].value())]);
    let updated: czsc_core::objects::signal::Signal = output[0].to_string().parse().unwrap();
    let legacy: czsc_core::objects::signal::Signal = output[0]
        .to_string()
        .replace("时间区间V221111", "时间区间")
        .parse()
        .unwrap();
    assert!(updated.is_match(&signals));
    assert!(!legacy.is_match(&signals));
}

#[test]
fn test_normal_doji_preserves_classification_and_migrated_condition() {
    let start = Utc.with_ymd_and_hms(2026, 10, 1, 9, 0, 0).unwrap();
    let bars = (0..12)
        .map(|index| {
            let (open, close, high, low) = if index == 11 {
                (100.0, 100.0, 101.0, 99.0)
            } else {
                (90.0, 100.0, 100.0, 90.0)
            };
            RawBarBuilder::default()
                .symbol("T")
                .id(index)
                .dt(start + Duration::hours(index as i64))
                .freq(Freq::F60)
                .open(open)
                .close(close)
                .high(high)
                .low(low)
                .vol(1.0)
                .amount(1.0)
                .build()
                .unwrap()
        })
        .collect();
    let context = CZSC::new(bars, 50, 6);
    assert_eq!(context.bars_raw.len(), 12);
    let meta = &SIGNAL_REGISTRY["jcc_szx_V221111"];
    let output = (meta.func)(&context, &HashMap::new(), &mut TaCache::default());
    assert_eq!(output.len(), 1);
    let expected = "60分钟_D1TH10_十字线V221111_十字线_北方_任意_0";
    assert_eq!(output[0].to_string(), expected);
    let config = SignalConfig::from_signal_str(expected).unwrap();
    let replayed = (meta.func)(&context, &config.params, &mut TaCache::default());
    assert_eq!(replayed[0].to_string(), expected);
    let signals = HashMap::from([(output[0].key(), output[0].value())]);
    let migrated: czsc_core::objects::signal::Signal = expected.parse().unwrap();
    let legacy: czsc_core::objects::signal::Signal = expected
        .replacen("十字线V221111", "十字线", 1)
        .parse()
        .unwrap();
    assert!(migrated.is_match(&signals));
    assert!(!legacy.is_match(&signals));
}
