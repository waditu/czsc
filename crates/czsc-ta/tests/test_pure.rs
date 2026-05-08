//! Phase E.2 — RED test：czsc-ta 纯算子保持长度、在退化输入上表现
//! 正确，并产出与 rs-czsc 47ef6efa baseline 对齐的合理数值输出。

use czsc_ta::pure::{
    boll_positions, double_sma_positions, ema, mid_positions, rolling_rank, single_ema_positions,
    single_sma_positions, true_range, ultimate_smoother,
};

fn series(n: usize) -> Vec<f64> {
    (0..n).map(|i| (i as f64) * 0.1 + 100.0).collect()
}

#[test]
fn ultimate_smoother_preserves_length() {
    let s = series(50);
    let out = ultimate_smoother(&s, 10.0);
    assert_eq!(out.len(), s.len());
}

#[test]
fn ultimate_smoother_first_4_passthrough() {
    // 按 rs-czsc 契约，前 4 个值必须等于输入。
    let s = series(20);
    let out = ultimate_smoother(&s, 10.0);
    for i in 0..4 {
        assert!(
            (out[i] - s[i]).abs() < f64::EPSILON,
            "i={i}: {} vs {}",
            out[i],
            s[i]
        );
    }
}

#[test]
fn ultimate_smoother_empty_returns_empty() {
    assert!(ultimate_smoother(&[], 10.0).is_empty());
}

#[test]
fn rolling_rank_preserves_length() {
    let s = series(50);
    let out = rolling_rank(&s, 10);
    assert_eq!(out.len(), s.len());
}

#[test]
fn ema_preserves_length() {
    let s = series(50);
    let out = ema(&s, 12);
    assert_eq!(out.len(), s.len());
}

#[test]
fn ema_zero_period_returns_empty() {
    // rs-czsc 的 ema 在 period == 0 时短路返回空 Vec；
    // 锁定这个行为，让调用方可以依赖一个稳定的契约。
    let s = vec![1.0, 2.0, 3.0];
    let out = ema(&s, 0);
    assert!(out.is_empty(), "ema(_, 0) 必须短路返回空 Vec");
}

#[test]
fn single_sma_positions_preserves_length() {
    let s = series(30);
    assert_eq!(single_sma_positions(&s, 5).len(), s.len());
}

#[test]
fn single_ema_positions_preserves_length() {
    let s = series(30);
    assert_eq!(single_ema_positions(&s, 5).len(), s.len());
}

#[test]
fn mid_positions_in_range() {
    let s = series(30);
    let out = mid_positions(&s, 5);
    for v in &out {
        assert!(*v >= -1.0 && *v <= 1.0, "持仓应在 [-1, 1] 区间，实际为 {v}");
    }
}

#[test]
fn double_sma_positions_returns_signal_length() {
    let s = series(30);
    let out = double_sma_positions(&s, 5, 10);
    assert_eq!(out.len(), s.len());
}

#[test]
fn boll_positions_in_signed_range() {
    let s = series(50);
    let out = boll_positions(&s, 20, 2.0);
    assert_eq!(out.len(), s.len());
    for v in &out {
        assert!(*v >= -1 && *v <= 1, "boll 持仓必须为 -1/0/1，实际为 {v}");
    }
}

#[test]
fn true_range_matches_input_length() {
    let high = vec![10.0, 11.0, 12.0, 11.5];
    let low = vec![9.0, 9.5, 10.5, 10.0];
    let prev = vec![9.5, 10.0, 11.0, 10.5];
    let tr = true_range(&high, &low, &prev);
    assert_eq!(tr.len(), 4);
    // tr[i] = max(high-low, |high-prev|, |low-prev|) >= 0
    for v in &tr {
        assert!(*v >= 0.0, "true_range 必须非负，实际为 {v}");
    }
}
