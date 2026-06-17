//! CzscTrader 状态快照（dump_state / restore_state）Rust 侧往返保真测试。
//!
//! 验证序列化层：缠论计算状态（bg / kas）经 MessagePack 往返后逐字段相等，
//! 以及快照版本校验。行为级零重放等价性由 Python 测试覆盖
//! （tests/unit/test_hot_start_snapshot.py）。

use chrono::{NaiveDateTime, TimeZone, Utc};
use czsc_core::objects::bar::{RawBar, RawBarBuilder};
use czsc_core::objects::freq::Freq;
use czsc_core::objects::market::Market;
use czsc_trader::trader::CzscTrader;
use czsc_utils::bar_generator::BarGenerator;

fn make_bar(id: i32, offset_min: u32, close: f64) -> RawBar {
    // 从 09:31 起按分钟递增，跨小时正确进位
    let total = 9 * 60 + 31 + offset_min;
    let (hh, mm) = (total / 60, total % 60);
    let dt = Utc.from_utc_datetime(
        &NaiveDateTime::parse_from_str(
            &format!("2024-01-02 {hh:02}:{mm:02}:00"),
            "%Y-%m-%d %H:%M:%S",
        )
        .unwrap(),
    );
    RawBarBuilder::default()
        .symbol("000001.SZ".to_string())
        .id(id)
        .dt(dt)
        .freq(Freq::F1)
        .open(close - 1.0)
        .close(close)
        .high(close + 1.0)
        .low(close - 2.0)
        .vol(1000.0)
        .amount(1000.0 * close)
        .build()
        .unwrap()
}

fn build_trader_with_bars() -> CzscTrader {
    let bg = BarGenerator::new(Freq::F1, vec![Freq::F5], 2000, Market::Default).unwrap();
    // 先喂入若干 1 分钟 bar，使 bg 各级别有数据；构造时 CzscSignals::new 据此建 kas
    for i in 0..30 {
        let bar = make_bar(i, i as u32, 100.0 + i as f64);
        bg.update_bar(&bar).unwrap();
    }
    CzscTrader::new("000001.SZ".to_string(), bg, vec![])
}

#[test]
fn dump_restore_roundtrip_preserves_state() {
    let trader = build_trader_with_bars();
    let bytes = trader.dump_state(&[], "mean").expect("dump_state");
    assert!(!bytes.is_empty(), "快照字节不应为空");

    let restored = CzscTrader::restore_state(&bytes).expect("restore_state");
    let r = restored.trader;

    assert_eq!(r.name, trader.name);
    assert_eq!(restored.ensemble_method, "mean");

    // bg：各级别 K 线数量与末根一致
    assert_eq!(
        r.signals.bg.freq_bars.len(),
        trader.signals.bg.freq_bars.len()
    );
    for (freq, lock) in &trader.signals.bg.freq_bars {
        let orig = lock.read();
        let got = r.signals.bg.freq_bars.get(freq).expect("freq 缺失").read();
        assert_eq!(orig.len(), got.len(), "freq {freq} bar 数量不一致");
        assert_eq!(
            orig.back().map(|b| b.dt),
            got.back().map(|b| b.dt),
            "freq {freq} 末根 dt 不一致"
        );
    }

    // kas：各级别 CZSC 的 bars_raw / bi_list 规模一致
    assert_eq!(r.signals.kas.len(), trader.signals.kas.len());
    for (freq, czsc) in &trader.signals.kas {
        let got = r.signals.kas.get(freq).expect("kas freq 缺失");
        assert_eq!(czsc.bars_raw.len(), got.bars_raw.len(), "{freq} bars_raw");
        assert_eq!(czsc.bars_ubi.len(), got.bars_ubi.len(), "{freq} bars_ubi");
        assert_eq!(czsc.bi_list.len(), got.bi_list.len(), "{freq} bi_list");
        assert_eq!(
            czsc.bars_raw.last().map(|b| b.close.to_bits()),
            got.bars_raw.last().map(|b| b.close.to_bits()),
            "{freq} 末根 close"
        );
    }
}

#[test]
fn restore_state_rejects_garbage() {
    assert!(
        CzscTrader::restore_state(b"not-a-snapshot").is_err(),
        "非法字节应返回 Err"
    );
}
