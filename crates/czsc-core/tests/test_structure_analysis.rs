use std::sync::Arc;

use chrono::{TimeZone, Utc};
use czsc_core::analyze::utils::{
    check_gap_info, get_zs_seq, is_bis_down, is_bis_up, is_symmetry_zs,
};
use czsc_core::objects::bar::{NewBar, NewBarBuilder, RawBar, RawBarBuilder};
use czsc_core::objects::bi::{BI, BIBuilder};
use czsc_core::objects::direction::Direction;
use czsc_core::objects::fake_bi::create_fake_bis;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::fx::{FX, FXBuilder};
use czsc_core::objects::mark::Mark;

fn new_bar(ts: i64, high: f64, low: f64) -> NewBar {
    NewBarBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .freq(Freq::F30)
        .id(ts as i32)
        .open((high + low) / 2.0)
        .close((high + low) / 2.0)
        .high(high)
        .low(low)
        .vol(100.0)
        .amount(1000.0)
        .elements(Vec::new())
        .build()
        .unwrap()
}

fn fx(ts: i64, mark: Mark, price: f64) -> FX {
    let (high, low) = match mark {
        Mark::G => (price, price - 1.0),
        Mark::D => (price + 1.0, price),
    };
    FXBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(ts, 0).unwrap())
        .mark(mark)
        .high(high)
        .low(low)
        .fx(price)
        .elements(vec![
            new_bar(ts - 1, high, low),
            new_bar(ts, high, low),
            new_bar(ts + 1, high, low),
        ])
        .build()
        .unwrap()
}

fn bi(ts: i64, start: f64, end: f64) -> BI {
    let (direction, mark_a, mark_b) = if end > start {
        (Direction::Up, Mark::D, Mark::G)
    } else {
        (Direction::Down, Mark::G, Mark::D)
    };
    let fx_a = fx(ts, mark_a, start);
    let fx_b = fx(ts + 10, mark_b, end);
    BIBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .fx_a(fx_a.clone())
        .fx_b(fx_b.clone())
        .fxs(vec![fx_a, fx_b])
        .direction(direction)
        .bars(vec![new_bar(ts, start.max(end), start.min(end))])
        .build()
        .unwrap()
}

fn raw_bar(id: i32, high: f64, low: f64) -> RawBar {
    RawBarBuilder::default()
        .symbol(Arc::<str>::from("000001"))
        .dt(Utc.timestamp_opt(id as i64, 0).unwrap())
        .freq(Freq::F30)
        .id(id)
        .open((high + low) / 2.0)
        .close((high + low) / 2.0)
        .high(high)
        .low(low)
        .vol(100.0)
        .amount(1000.0)
        .build()
        .unwrap()
}

#[test]
fn structure_helpers_handle_empty_and_short_inputs() {
    assert!(get_zs_seq(&[]).is_empty());
    assert!(!is_symmetry_zs(&[], 0.3));
    assert!(!is_bis_up(&[]));
    assert!(!is_bis_down(&[]));
    assert!(check_gap_info(&[]).is_empty());
}

#[test]
fn create_fake_bis_builds_expected_up_bi_and_trims_odd_tail() {
    let fxs = vec![
        fx(0, Mark::D, 9.0),
        fx(10, Mark::G, 12.0),
        fx(20, Mark::D, 10.0),
    ];
    let fake_bis = create_fake_bis(&fxs);
    assert_eq!(fake_bis.len(), 1);
    assert_eq!(fake_bis[0].direction, Direction::Up);
    assert_eq!(
        (fake_bis[0].high, fake_bis[0].low, fake_bis[0].power),
        (12.0, 9.0, 3.0)
    );
}

#[test]
#[should_panic(expected = "相邻分型标记必须不同")]
fn create_fake_bis_rejects_non_alternating_fxs() {
    create_fake_bis(&[fx(0, Mark::G, 10.0), fx(10, Mark::G, 11.0)]);
}

#[test]
fn get_zs_seq_groups_overlapping_bis_and_splits_separated_bis() {
    let bis = vec![bi(0, 12.0, 9.0), bi(20, 9.0, 11.0), bi(40, 11.0, 9.5)];
    let grouped = get_zs_seq(&bis);
    assert_eq!(grouped.len(), 1);
    assert_eq!(grouped[0].bis.len(), 3);

    let separated = get_zs_seq(&[bis[0].clone(), bi(20, 5.0, 7.0)]);
    assert_eq!(separated.len(), 2);
}

#[test]
fn symmetry_and_trend_helpers_identify_valid_structures() {
    let symmetric = vec![bi(0, 12.0, 9.0), bi(20, 9.0, 12.0), bi(40, 12.0, 9.0)];
    assert!(is_symmetry_zs(&symmetric, 0.01));

    let up = vec![bi(0, 9.0, 12.0), bi(20, 12.0, 10.0), bi(40, 10.0, 14.0)];
    assert!(is_bis_up(&up));
    assert!(!is_bis_down(&up));

    let down = vec![bi(0, 14.0, 10.0), bi(20, 10.0, 12.0), bi(40, 12.0, 8.0)];
    assert!(is_bis_down(&down));
    assert!(!is_bis_up(&down));
}

#[test]
fn symmetry_and_trend_helpers_reject_invalid_shapes() {
    let asymmetric = vec![bi(0, 12.0, 9.0), bi(20, 9.0, 11.0), bi(40, 11.0, 8.0)];
    assert!(!is_symmetry_zs(&asymmetric, 0.1));
    assert!(!is_symmetry_zs(&asymmetric[..2], 0.3));
    assert!(!is_symmetry_zs(&asymmetric, -0.1));

    let even = vec![bi(0, 9.0, 12.0), bi(20, 12.0, 10.0)];
    assert!(!is_bis_up(&even));
    assert!(!is_bis_down(&even));

    let unordered = vec![bi(40, 9.0, 12.0), bi(0, 12.0, 10.0), bi(20, 10.0, 14.0)];
    assert!(!is_bis_up(&unordered));
}

#[test]
fn check_gap_info_reports_direction_range_and_cover() {
    let bars = vec![
        raw_bar(1, 10.0, 9.0),
        raw_bar(2, 12.0, 11.0),
        raw_bar(3, 11.5, 9.5),
        raw_bar(4, 8.5, 8.0),
    ];
    let gaps = check_gap_info(&bars);
    assert_eq!(gaps.len(), 2);
    assert_eq!(gaps[0].kind, "向上缺口");
    assert_eq!(gaps[0].cover, "已补");
    assert_eq!((gaps[0].high, gaps[0].low), (11.0, 10.0));
    assert_eq!(gaps[1].kind, "向下缺口");
    assert_eq!(gaps[1].cover, "未补");
    assert_eq!((gaps[1].high, gaps[1].low), (9.5, 8.5));
}

#[test]
fn check_gap_info_handles_no_gap_and_covered_down_gap() {
    let no_gap = vec![raw_bar(1, 10.0, 9.0), raw_bar(2, 10.5, 9.5)];
    assert!(check_gap_info(&no_gap).is_empty());

    let down_gap = vec![
        raw_bar(1, 12.0, 11.0),
        raw_bar(2, 10.0, 9.0),
        raw_bar(3, 11.5, 9.5),
    ];
    let gaps = check_gap_info(&down_gap);
    assert_eq!(gaps.len(), 1);
    assert_eq!(gaps[0].kind, "向下缺口");
    assert_eq!(gaps[0].cover, "已补");
    assert_eq!((gaps[0].high, gaps[0].low), (11.0, 10.0));
}
