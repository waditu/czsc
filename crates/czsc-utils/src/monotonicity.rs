//! Spearman 单调性系数（对齐 `scipy.stats.spearmanr` 的 Spearman 相关）。
//!
//! 历史上 Python 端 [`czsc.eda.monotonicity`] 调用 `scipy.stats.spearmanr(seq,
//! range(len(seq)))` 计算"序列与自然数序列的秩相关"。2026-05-17 PR-D 起，
//! 同样的语义改为 Rust 实现，并通过 PyO3 暴露成 `czsc._native.monotonicity`。
//!
//! 关键的等价点（[`scipy.stats.spearmanr` 默认行为对齐]）：
//!
//! - 长度 ≤ 1 时返回 `NaN`（无法计算相关）；
//! - 含 NaN 时返回 `NaN`（对应 `nan_policy="propagate"`）；
//! - 平均秩（average rank）处理 tied values（对应 `scipy.stats.rankdata`
//!   `method="average"`）；
//! - 全相等序列（std=0）返回 `NaN`（分母为 0 的退化情形）。
//!
//! 性能：O(n log n) 排序 + O(n) 单遍累加，无堆分配热点；对 N=10000 的序列
//! 实测比 `scipy.stats.spearmanr` 快 5× 以上，详见
//! `tests/perf/test_monotonicity_perf.py`。

/// 计算 `sequence` 与自然数序列 `[0, 1, ..., len-1]` 之间的 Spearman 秩相关。
///
/// 返回值在 `[-1.0, 1.0]` 之间，越接近 1 表示单调递增，越接近 -1 表示单调
/// 递减，接近 0 表示无序。退化情形返回 `f64::NAN`，与 scipy 行为一致。
pub fn monotonicity(sequence: &[f64]) -> f64 {
    let n = sequence.len();
    if n < 2 {
        return f64::NAN;
    }
    // 含 NaN 时 scipy 默认（`nan_policy="propagate"`）返回 NaN，逐元素短路即可。
    if sequence.iter().any(|x| x.is_nan()) {
        return f64::NAN;
    }

    let ranks = average_ranks(sequence);
    // 对照变量 x = 1..=n 的秩就是其值本身（自然数序列无 tie），直接走 Pearson。
    pearson_with_naturals(&ranks)
}

/// 计算 `values` 的平均秩。tied values 共享 `(low + high) / 2` 的秩号，
/// 与 `scipy.stats.rankdata(values, method="average")` 等价。
///
/// 实现细节：
/// - 先 `enumerate + sort` 得到 (原下标, 值) 的有序序列；
/// - 一趟扫描中识别 tie 区间 `[i, j]`（区间内值相等），把同一个平均秩号写回
///   原位置。
fn average_ranks(values: &[f64]) -> Vec<f64> {
    let n = values.len();
    let mut indexed: Vec<(usize, f64)> = values.iter().copied().enumerate().collect();
    // 用 partial_cmp + unwrap_or(Equal)：sequence 已无 NaN（调用方短路过），
    // 这里 unwrap 不会 fallback；保留 Equal fallback 是为了防御性。
    indexed.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

    let mut ranks = vec![0.0; n];
    let mut i = 0;
    while i < n {
        let mut j = i;
        // 推进到 tie 区间末尾（值相等的最后一个位置）
        while j + 1 < n && indexed[j + 1].1 == indexed[i].1 {
            j += 1;
        }
        // 1-based 平均秩：(low+1 + high+1) / 2
        let avg_rank = (i + 1 + j + 1) as f64 / 2.0;
        for k in i..=j {
            ranks[indexed[k].0] = avg_rank;
        }
        i = j + 1;
    }
    ranks
}

/// 计算 `ranks` 与对照向量 `[1, 2, ..., n]` 的 Pearson 相关系数。
///
/// 对照向量 sum / sum² 用闭式公式（避免重复构造 Vec）：
/// - `Σ i = n(n+1)/2`；
/// - `Σ i² = n(n+1)(2n+1)/6`。
fn pearson_with_naturals(ranks: &[f64]) -> f64 {
    let n = ranks.len();
    let n_f = n as f64;
    let sum_y: f64 = ranks.iter().sum();
    let sum_y2: f64 = ranks.iter().map(|v| v * v).sum();
    let sum_xy: f64 = ranks
        .iter()
        .enumerate()
        .map(|(i, &y)| (i + 1) as f64 * y)
        .sum();
    let sum_x = n_f * (n_f + 1.0) / 2.0;
    let sum_x2 = n_f * (n_f + 1.0) * (2.0 * n_f + 1.0) / 6.0;

    let numerator = n_f * sum_xy - sum_x * sum_y;
    let var_x = n_f * sum_x2 - sum_x * sum_x;
    let var_y = n_f * sum_y2 - sum_y * sum_y;
    let denominator = (var_x * var_y).sqrt();
    if denominator == 0.0 {
        return f64::NAN;
    }
    numerator / denominator
}

#[cfg(test)]
mod tests {
    use super::*;

    fn approx_eq(a: f64, b: f64, tol: f64) -> bool {
        (a.is_nan() && b.is_nan()) || (a - b).abs() <= tol
    }

    #[test]
    fn strictly_increasing_returns_one() {
        let seq: Vec<f64> = (0..50).map(|i| i as f64).collect();
        assert!(approx_eq(monotonicity(&seq), 1.0, 1e-12));
    }

    #[test]
    fn strictly_decreasing_returns_minus_one() {
        let seq: Vec<f64> = (0..50).map(|i| -(i as f64)).collect();
        assert!(approx_eq(monotonicity(&seq), -1.0, 1e-12));
    }

    #[test]
    fn empty_or_single_returns_nan() {
        assert!(monotonicity(&[]).is_nan());
        assert!(monotonicity(&[3.14]).is_nan());
    }

    #[test]
    fn constant_returns_nan() {
        // 全相等 → ranks 全为 (1+n)/2，std=0 → NaN
        assert!(monotonicity(&[1.0, 1.0, 1.0, 1.0]).is_nan());
    }

    #[test]
    fn nan_propagates() {
        assert!(monotonicity(&[1.0, f64::NAN, 2.0]).is_nan());
    }

    #[test]
    fn duplicates_use_average_rank() {
        // [10, 20, 20, 30] 对应 1-based 秩 [1, 2.5, 2.5, 4]
        // 与 [1, 2, 3, 4] 的 Pearson 相关接近 1（单调递增带 tie）
        let r = monotonicity(&[10.0, 20.0, 20.0, 30.0]);
        // scipy.stats.spearmanr([10,20,20,30], [0,1,2,3]).statistic ≈ 0.9486832980505138
        assert!(approx_eq(r, 0.948_683_298_050_513_8, 1e-12));
    }

    #[test]
    fn random_sample_matches_known_value() {
        // 与 scipy 在 Python 端预先计算的参考值对比，确保实现等价
        // scipy.stats.spearmanr([3,1,4,1,5,9,2,6,5,3,5], range(11)).statistic
        // = 0.43782986108274397
        let seq = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.0, 5.0];
        let r = monotonicity(&seq);
        assert!(approx_eq(r, 0.437_829_861_082_743_97, 1e-12));
    }

    #[test]
    fn two_element_distinct() {
        // 两个不同元素：单调，应为 ±1
        assert!(approx_eq(monotonicity(&[1.0, 2.0]), 1.0, 1e-12));
        assert!(approx_eq(monotonicity(&[2.0, 1.0]), -1.0, 1e-12));
    }
}
