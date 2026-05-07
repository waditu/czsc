use super::rounded::RoundToNthDigit;

#[derive(Debug)]
pub struct LinearResult {
    /// 标识斜率
    pub slope: f64,
    /// 截距
    pub intercept: f64,
    /// 拟合优度
    pub r2: f64,
}

/// 单变量线性拟合
pub trait LinearRegression {
    fn single_linear(&self) -> LinearResult;
}

impl LinearRegression for [f64] {
    /// 单变量线性拟合
    /// https://en.wikipedia.org/wiki/Linear_regression
    fn single_linear(&self) -> LinearResult {
        if self.is_empty() {
            return LinearResult {
                slope: 0.0,
                intercept: 0.0,
                r2: 0.0,
            };
        }

        // 数据点的数量
        let sample_size = self.len() as f64;

        // x 值的总和, 隐式生成的索引序列 [0, 1, 2, ..., n-1]，其和为等差数列公式 (n-1)*n/2
        let sum_x = (sample_size - 1.0) * sample_size / 2.0;
        // x 值的平方和，使用公式 (n-1)*n*(2n-1)/6，对应索引序列的平方和
        let sum_x_squared = (sample_size - 1.0) * sample_size * (2.0 * sample_size - 1.0) / 6.0;

        // sum_xy: x 和 y 的乘积之和（Σ(x*y)）
        let (sum_xy, sum_y) = self.iter().enumerate().fold((0.0, 0.0), |acc, (i, &y1)| {
            (acc.0 + (i as f64) * y1, acc.1 + y1)
        });

        // 线性回归斜率公式的分母部分: n*Σx² - (Σx)^2
        let denominator = sample_size * sum_x_squared - sum_x * sum_x;
        if denominator == 0.0 {
            return LinearResult {
                slope: 0.0,
                intercept: 0.0,
                r2: 0.0,
            };
        }

        let y_intercept = (1.0 / denominator) * (sum_x_squared * sum_y - sum_x * sum_xy);
        let slope = (1.0 / denominator) * (sample_size * sum_xy - sum_x * sum_y);

        let y_mean = sum_y / sample_size;
        let (ss_tot, ss_err) = self.iter().enumerate().fold((0.0, 0.0), |acc, (i, &y1)| {
            let y_diff = y1 - y_mean;
            let predicted = slope * (i as f64) + y_intercept;
            let err = y1 - predicted;
            (acc.0 + y_diff * y_diff, acc.1 + err * err)
        });

        let rsq = 1.0 - ss_err / (ss_tot + 0.00001);

        LinearResult {
            slope: slope.round_to_4_digit(),
            intercept: y_intercept.round_to_4_digit(),
            r2: rsq.round_to_4_digit(),
        }
    }
}

/// ## 计算两个向量的Pearson Corr
///
/// [wiki](https://en.wikipedia.org/wiki/Pearson_correlation_coefficient)
///
/// - 当数据为空或长度不一致时返回 None。
///
/// - 分母为0时返回 None避免除0错误
pub fn pearson_corr(x: &[f64], y: &[f64]) -> Option<f64> {
    if x.len() != y.len() || x.is_empty() {
        return None;
    }

    let n = x.len();
    // x̄ = (Σxᵢ) / n
    let mean_x = x.iter().sum::<f64>() / n as f64;
    // ȳ = (Σyᵢ) / n
    let mean_y = y.iter().sum::<f64>() / n as f64;

    // cov(X, Y): Σ(xᵢ - x̄)(yᵢ - ȳ)
    let mut cov = 0.0;
    // Σ(xᵢ - x̄)²
    let mut sum_x_sq = 0.0;
    // Σ(yᵢ - ȳ)²
    let mut sum_y_sq = 0.0;

    for i in 0..n {
        let diff_x = x[i] - mean_x;
        let diff_y = y[i] - mean_y;
        cov += diff_x * diff_y;

        sum_x_sq += diff_x * diff_x;
        sum_y_sq += diff_y * diff_y;
    }

    let denominator = (sum_x_sq * sum_y_sq).sqrt();
    if denominator == 0.0 {
        // 防止分母为0
        return None;
    }

    // cov(X, Y) / (σXσY)
    Some(cov / denominator)
}

/// 计算两个向量的Spearman Rank Corr
///
/// [wiki](https://en.wikipedia.org/wiki/Spearman%27s_rank_correlation_coefficient)
///
/// > Spearman's coefficient is appropriate for both continuous and discrete ordinal variables.
///
/// - 当数据为空或长度不一致时返回 None。
pub fn spearman_rank_corr(x: &[f64], y: &[f64]) -> Option<f64> {
    if x.len() != y.len() || x.is_empty() {
        return None;
    }

    fn compute_ranks(data: &[f64]) -> Vec<f64> {
        // 将数据与原始索引绑定：[(值, 原始索引)]
        let mut indexed_data: Vec<(f64, usize)> =
            data.iter().enumerate().map(|(i, &val)| (val, i)).collect();

        // 按值排序（从小到大）
        indexed_data.sort_by(|a, b| a.0.partial_cmp(&b.0).unwrap());

        let n = data.len();
        let mut ranks = vec![0.0; n];
        let mut i = 0;

        // 遍历排序后的数据，处理重复值
        while i < n {
            let current_val = indexed_data[i].0;
            let mut j = i;

            // 找到所有与当前值相同的元素（重复值的结束位置）
            while j < n && indexed_data[j].0 == current_val {
                j += 1;
            }

            // 计算平均排名（从1开始）
            let avg_rank = (i + 1 + j) as f64 / 2.0;

            // 将平均Rank赋给所有重复值的原始索引
            for item in &indexed_data[i..j] {
                let original_index = item.1;
                ranks[original_index] = avg_rank;
            }

            // 跳过已处理的重复值
            i = j;
        }

        ranks
    }

    // R[X]
    let x_ranks = compute_ranks(x);
    // R[Y]
    let y_ranks = compute_ranks(y);

    // cov(R[X], R[Y]) / (σR[X]σR[Y])
    pearson_corr(&x_ranks, &y_ranks)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_linear() {
        let y = [1.0, 2.0, 3.0, 4.0, 5.0];

        let res2 = y.single_linear();

        println!("{res2:?}");
    }

    ///```
    /// import pandas as pd
    /// a = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, 6.0, 16.0]
    /// b = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, -6.0, 16.0]
    /// df = pd.DataFrame({'col_a': a, 'col_b': b})
    /// df['col_a'].corr(df['col_b'])
    ///```
    /// np.float64(0.8214654924226573)
    #[test]
    fn test_pearson_corr() {
        let a = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, 6.0, 16.0];
        let b = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, -6.0, 16.0];
        assert_eq!(
            pearson_corr(&a, &b).map(|x| x.round_to_4_digit()),
            Some(0.8215)
        )
    }

    ///```
    /// import pandas as pd
    /// a = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, 6.0, 16.0]
    /// b = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, -6.0, 16.0]
    /// df = pd.DataFrame({'col_a': a, 'col_b': b})
    /// df['col_a'].corr(df['col_b'], method="spearman")
    ///```
    /// np.float64(0.6470588235294119)
    #[test]
    fn test_spearman_rank_corr() {
        let a = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, 6.0, 16.0];
        let b = [1.0, 2.0, -3.0, -1.0, 5.0, 1.0, -7.0, -6.0, 16.0];
        assert_eq!(
            spearman_rank_corr(&a, &b).map(|x| x.round_to_4_digit()),
            Some(0.6471)
        )
    }
}
