//! Phase D.9 —— RED 测试：ZS（中枢）从非空 BI 列表构造，
//! 计算 zg / zd / zz / gg / dd 边界，并暴露 is_valid()。

use std::sync::Arc;

use chrono::{TimeZone, Utc};
use czsc_core::objects::bar::{NewBar, NewBarBuilder};
use czsc_core::objects::bi::{BI, BIBuilder};
use czsc_core::objects::direction::Direction;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::fx::{FX, FXBuilder};
use czsc_core::objects::mark::Mark;
use czsc_core::objects::zs::ZS;

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

fn fx(ts: i64, mark: Mark, level: f64) -> FX {
    let k1 = nb(ts - 1800, level - 0.5, level - 1.5);
    let k2 = nb(ts, level + 0.5, level - 0.5);
    let k3 = nb(ts + 1800, level - 0.2, level - 1.0);
    let mark_clone = mark.clone();
    FXBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .mark(mark_clone)
        .high(k2.high)
        .low(k2.low)
        .fx(if matches!(mark, Mark::G) {
            k2.high
        } else {
            k2.low
        })
        .elements(vec![k1, k2, k3])
        .build()
        .unwrap()
}

fn make_bi(
    ts_a: i64,
    mark_a: Mark,
    level_a: f64,
    ts_b: i64,
    mark_b: Mark,
    level_b: f64,
    direction: Direction,
) -> BI {
    let fx_a = fx(ts_a, mark_a, level_a);
    let fx_b = fx(ts_b, mark_b, level_b);
    // bars 跨度 —— 端点决定 high/low
    let bars = vec![
        nb(ts_a, level_a + 0.5, level_a - 0.5),
        nb(
            (ts_a + ts_b) / 2,
            (level_a + level_b) / 2.0 + 0.5,
            (level_a + level_b) / 2.0 - 0.5,
        ),
        nb(ts_b, level_b + 0.5, level_b - 0.5),
    ];
    BIBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .fx_a(fx_a)
        .fx_b(fx_b.clone())
        .fxs(vec![fx_b])
        .direction(direction)
        .bars(bars)
        .build()
        .unwrap()
}

fn sample_zs() -> ZS {
    // 由 3 笔构成的中枢：向下 12 -> 9，向上 9 -> 11，向下 11 -> 9.5
    let bi1 = make_bi(
        1_700_000_000,
        Mark::G,
        12.0,
        1_700_001_800,
        Mark::D,
        9.0,
        Direction::Down,
    );
    let bi2 = make_bi(
        1_700_001_800,
        Mark::D,
        9.0,
        1_700_003_600,
        Mark::G,
        11.0,
        Direction::Up,
    );
    let bi3 = make_bi(
        1_700_003_600,
        Mark::G,
        11.0,
        1_700_005_400,
        Mark::D,
        9.5,
        Direction::Down,
    );
    ZS::new(vec![bi1, bi2, bi3])
}

#[test]
fn new_populates_endpoints() {
    let zs = sample_zs();
    assert_eq!(zs.bis.len(), 3);
    assert_eq!(zs.sdir, Direction::Down);
    assert_eq!(zs.edir, Direction::Down);
}

#[test]
fn zg_zd_within_first_three_bis() {
    let zs = sample_zs();
    // zg = 前 3 笔 high 的最小值；zd = 前 3 笔 low 的最大值
    assert!(zs.zg >= zs.zd, "zg={} must be >= zd={}", zs.zg, zs.zd);
}

#[test]
fn zz_is_midpoint_of_zg_zd() {
    let zs = sample_zs();
    let mid = (zs.zg + zs.zd) / 2.0;
    assert!(
        (zs.zz - mid).abs() < 1e-9,
        "zz {} should equal mid {}",
        zs.zz,
        mid
    );
}

#[test]
fn gg_dd_envelope_zg_zd() {
    let zs = sample_zs();
    assert!(zs.gg >= zs.zg, "gg {} must be >= zg {}", zs.gg, zs.zg);
    assert!(zs.dd <= zs.zd, "dd {} must be <= zd {}", zs.dd, zs.zd);
}

#[test]
fn is_valid_returns_true_for_standard_zs() {
    // sample_zs() 由 3 笔组成、zg > zd 的标准中枢，must be valid
    let zs = sample_zs();
    assert!(zs.is_valid(), "标准 3 笔中枢（zg={} > zd={}）应通过有效性检查", zs.zg, zs.zd);
}
