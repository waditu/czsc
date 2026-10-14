use chrono::{TimeZone, Utc};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBarBuilder;
use czsc_core::objects::freq::Freq;
use czsc_signals::registry::SIGNAL_REGISTRY;
use czsc_signals::types::TaCache;
use serde_json::json;
use std::collections::HashMap;

#[test]
fn test_bar_operate_span_key_matches_template() {
    let meta = &SIGNAL_REGISTRY["bar_operate_span_V221111"];
    for (start, end, cases) in [
        (
            "0935",
            "1450",
            [
                (9, 34, "否"),
                (9, 35, "是"),
                (12, 0, "是"),
                (14, 50, "是"),
                (14, 51, "否"),
            ],
        ),
        (
            "1000",
            "1100",
            [
                (9, 59, "否"),
                (10, 0, "是"),
                (10, 30, "是"),
                (11, 0, "是"),
                (11, 1, "否"),
            ],
        ),
    ] {
        let params = if start == "0935" {
            HashMap::new()
        } else {
            HashMap::from([
                ("t1".to_string(), json!(start)),
                ("t2".to_string(), json!(end)),
            ])
        };
        let expected_key = meta
            .param_template
            .replace("{freq}", "60分钟")
            .replace("{t1}", start)
            .replace("{t2}", end);
        assert_eq!(
            expected_key,
            format!("60分钟_T{start}#{end}_时间区间V221111")
        );
        for (hour, minute, expected_value) in cases {
            let bar = RawBarBuilder::default()
                .symbol("T")
                .id(1)
                .dt(Utc.with_ymd_and_hms(2026, 10, 14, hour, minute, 0).unwrap())
                .freq(Freq::F60)
                .open(1.0)
                .close(1.0)
                .high(1.0)
                .low(1.0)
                .vol(1.0)
                .amount(1.0)
                .build()
                .unwrap();
            let mut context = CZSC::new(vec![bar], 50, 6);
            let mut cache = TaCache::default();
            let signals = (meta.func)(&context, &params, &mut cache);
            assert_eq!(signals.len(), 1);
            assert_eq!(signals[0].key(), expected_key);
            assert_eq!(signals[0].value(), format!("{expected_value}_任意_任意_0"));
            context.bars_raw.clear();
            let signals = (meta.func)(&context, &params, &mut cache);
            assert_eq!(signals.len(), 1);
            assert_eq!(signals[0].key(), expected_key);
            assert_eq!(signals[0].value(), "其他_任意_任意_0");
        }
    }
}
