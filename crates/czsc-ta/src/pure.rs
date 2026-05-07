//! 纯 Rust 实现

/// Plain Simple Moving Average — talib.SMA-compatible.
///
/// Returns the rolling mean of `series` with window size `n`. Indices
/// 0..n-1 are filled with NaN to match the talib convention (so
/// `np.isfinite(out[n:])` is fully True). This is intentionally
/// distinct from `single_sma_positions`, which computes a double SMA
/// then derives a [-1, 0, 1] position signal — `sma` here is the raw
/// moving average needed by `czsc.ta.sma` per design doc §3.1.
pub fn sma(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    let mut out = vec![f64::NAN; len];
    if n > len {
        return out;
    }
    let mut sum: f64 = series.iter().take(n).sum();
    out[n - 1] = sum / n as f64;
    for i in n..len {
        sum += series[i] - series[i - n];
        out[i] = sum / n as f64;
    }
    out
}

// Ultimate Smoother 实现函数
pub fn ultimate_smoother(price: &[f64], period: f64) -> Vec<f64> {
    let len = price.len();
    if len == 0 {
        return vec![];
    }
    let a1 = (-1.414 * std::f64::consts::PI / period).exp();
    let b1 = 2.0 * a1 * (1.414 * 180.0 / period).to_radians().cos();
    let c2 = b1;
    let c3 = -a1 * a1;
    let c1 = (1.0 + c2 - c3) / 4.0;
    let mut us = vec![0.0; len];

    // 与 Python 实现完全一致，正确处理 NaN
    for i in 0..len {
        if i < 4 {
            us[i] = price[i];
        } else {
            // 检查输入值是否为 NaN，如果是则保持 NaN
            if price[i].is_nan() || price[i - 1].is_nan() || price[i - 2].is_nan() {
                us[i] = f64::NAN;
            } else {
                us[i] = (1.0 - c1) * price[i] + (2.0 * c1 - c2) * price[i - 1]
                    - (c1 + c3) * price[i - 2]
                    + c2 * us[i - 1]
                    + c3 * us[i - 2];
            }
        }
    }

    us
}

pub fn rolling_rank(series: &[f64], window: usize) -> Vec<Option<usize>> {
    let len = series.len();
    let mut ranks = Vec::with_capacity(len);
    for i in 0..len {
        if i + 1 < window {
            ranks.push(None);
            continue;
        }
        let start = i + 1 - window;
        let window_slice = &series[start..=i];
        let mut sorted = window_slice.to_vec();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        let value = series[i];
        let rank = sorted
            .iter()
            .position(|&x| (x - value).abs() < 1e-8)
            .map(|pos| pos + 1);
        ranks.push(rank);
    }
    ranks
}
/// 单均线多空
pub fn single_sma_positions(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        // 如果窗口大于序列长度，全部返回0
        return vec![0.0; len];
    }
    // 计算第一个移动平均
    let mut ms = vec![0.0; len];
    for i in 0..len {
        if i + 1 < n {
            ms[i] = 0.0; // 不足窗口长度的位置设为0
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            ms[i] = sum / n as f64;
        }
    }
    // 计算第二个移动平均（对第一个移动平均再次求移动平均）
    let mut ms_sma = vec![0.0; len];
    for i in 0..len {
        if i + 1 < n {
            ms_sma[i] = 0.0;
        } else {
            let sum: f64 = ms[i + 1 - n..=i].iter().sum();
            ms_sma[i] = sum / n as f64;
        }
    }
    // 计算差值并返回符号
    let mut result = vec![0.0; len];
    for i in 0..len {
        // 只有 i >= 2*n-2 时才有有效信号，与 Python pandas 的 fillna(0) 行为完全一致
        if i >= 2 * n - 2 && ms_sma[i] != 0.0 {
            result[i] = (series[i] - ms_sma[i]).signum();
        } else {
            result[i] = 0.0;
        }
    }
    result
}

/// 单指数移动平均多空信号
pub fn single_ema_positions(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        // 如果窗口大于序列长度，全部返回0
        return vec![0.0; len];
    }

    // 预分配所有向量，避免动态扩容
    let mut result = vec![0.0; len];
    let mut ms = vec![0.0; len];
    let mut ms_ema = vec![0.0; len];

    // 计算第一个移动平均
    for i in 0..len {
        if i + 1 < n {
            ms[i] = 0.0; // 不足窗口长度的位置设为0，对应 Python 的 NaN
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            ms[i] = sum / n as f64;
        }
    }

    // 计算指数移动平均，模拟 talib.EMA 的行为
    let alpha = 2.0 / (n as f64 + 1.0);

    // 找到第一个非零的 ms 值作为初始值
    let mut first_valid_idx = 0;
    for i in 0..len {
        if ms[i] != 0.0 {
            first_valid_idx = i;
            break;
        }
    }

    // 模拟 talib.EMA 的行为，需要 n 个有效数据才开始计算
    let start_idx = first_valid_idx + n - 1;

    // 一次性计算 EMA 和结果，减少循环次数
    for i in 0..len {
        if i < start_idx {
            ms_ema[i] = 0.0;
            result[i] = 0.0;
        } else if i == start_idx {
            // 用前 n 个有效值的简单平均作为初始值
            let sum: f64 = ms[first_valid_idx..=i].iter().sum();
            ms_ema[i] = sum / n as f64;
            result[i] = (series[i] - ms_ema[i]).signum();
        } else {
            ms_ema[i] = alpha * ms[i] + (1.0 - alpha) * ms_ema[i - 1];
            result[i] = (series[i] - ms_ema[i]).signum();
        }
    }

    result
}

/// 取窗口内的中间值作为中轴，中轴上方做多，下方做空
/// 中间值 = (最大值 + 最小值) / 2
pub fn mid_positions(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        return vec![0.0; len];
    }

    // 计算第一个移动平均
    let mut ms = vec![0.0; len];
    for i in 0..len {
        if i + 1 < n {
            ms[i] = 0.0; // 不足窗口长度的位置设为0
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            ms[i] = sum / n as f64;
        }
    }

    // 计算 ms 的滚动最大值和最小值
    let mut high = vec![0.0; len];
    let mut low = vec![0.0; len];

    for i in 0..len {
        if i + 1 < n {
            high[i] = 0.0;
            low[i] = 0.0;
        } else {
            let window = &ms[i + 1 - n..=i];
            high[i] = window.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
            low[i] = window.iter().fold(f64::INFINITY, |a, &b| a.min(b));
        }
    }

    // 计算中间值并返回符号
    let mut result = vec![0.0; len];
    for i in 0..len {
        if i + 1 < 2 * n - 1 {
            // 需要 2*n-1 个数据点才有有效信号
            result[i] = 0.0;
        } else if high[i] != 0.0 && low[i] != 0.0 {
            let mid = (high[i] + low[i]) / 2.0;
            result[i] = (ms[i] - mid).signum();
        } else {
            result[i] = 0.0;
        }
    }

    result
}

/// 双均线多空信号
/// 比较短周期和长周期的简单移动平均
pub fn double_sma_positions(series: &[f64], n: usize, m: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || n == 0 || m == 0 {
        return vec![];
    }
    if n >= m {
        panic!("短周期必须小于长周期");
    }
    if m > len {
        return vec![0.0; len];
    }

    let mut result = vec![0.0; len];

    // 使用增量计算优化性能
    let mut sma_n_sum = 0.0;
    let mut sma_m_sum = 0.0;
    let mut sma_n_count = 0;
    let mut sma_m_count = 0;

    for i in 0..len {
        // 更新短周期移动平均
        if i >= n - 1 {
            if sma_n_count == 0 {
                sma_n_sum = series[i + 1 - n..=i].iter().sum();
                sma_n_count = 1;
            } else {
                sma_n_sum = sma_n_sum + series[i] - series[i - n];
            }
        }

        // 更新长周期移动平均
        if i >= m - 1 {
            if sma_m_count == 0 {
                sma_m_sum = series[i + 1 - m..=i].iter().sum();
                sma_m_count = 1;
            } else {
                sma_m_sum = sma_m_sum + series[i] - series[i - m];
            }
        }

        if i >= m - 1 && sma_n_count > 0 && sma_m_count > 0 {
            let sma_n = sma_n_sum / n as f64;
            let sma_m = sma_m_sum / m as f64;
            result[i] = (sma_n - sma_m).signum();
        } else {
            result[i] = 0.0;
        }
    }

    result
}

/// 三均线系统持仓信号生成函数
/// 多头：factor > m3 的时候，m1 > m2
/// 空头：factor < m3 的时候，m1 < m2
pub fn triple_sma_positions(series: &[f64], m1: usize, m2: usize, m3: usize) -> Vec<i32> {
    let len = series.len();
    if len == 0 || m1 == 0 || m2 == 0 || m3 == 0 {
        return vec![];
    }
    if m3 > len {
        panic!("series 长度必须大于 m3");
    }
    if !(m3 > m2 && m2 > m1) {
        panic!("m3 必须大于 m2 大于 m1");
    }

    // 第一步：对原始序列计算 m1 期移动平均
    let mut smoothed_series = vec![None; len];
    for i in 0..len {
        if i + 1 < m1 {
            smoothed_series[i] = None;
        } else {
            let sum: f64 = series[i + 1 - m1..=i].iter().sum();
            smoothed_series[i] = Some(sum / m1 as f64);
        }
    }

    // 计算三个移动平均
    let mut ma1 = vec![None; len];
    let mut ma2 = vec![None; len];
    let mut ma3 = vec![None; len];

    // 计算 ma1 (对 smoothed_series 计算 m1 期移动平均)
    for i in 0..len {
        if i + 1 < m1 {
            ma1[i] = None;
        } else {
            let window: Vec<f64> = smoothed_series[i + 1 - m1..=i]
                .iter()
                .filter_map(|&x| x)
                .collect();
            if window.len() == m1 {
                let sum: f64 = window.iter().sum();
                ma1[i] = Some(sum / m1 as f64);
            } else {
                ma1[i] = None;
            }
        }
    }

    // 计算 ma2 (对 smoothed_series 计算 m2 期移动平均)
    for i in 0..len {
        if i + 1 < m2 {
            ma2[i] = None;
        } else {
            let window: Vec<f64> = smoothed_series[i + 1 - m2..=i]
                .iter()
                .filter_map(|&x| x)
                .collect();
            if window.len() == m2 {
                let sum: f64 = window.iter().sum();
                ma2[i] = Some(sum / m2 as f64);
            } else {
                ma2[i] = None;
            }
        }
    }

    // 计算 ma3 (对 smoothed_series 计算 m3 期移动平均)
    for i in 0..len {
        if i + 1 < m3 {
            ma3[i] = None;
        } else {
            let window: Vec<f64> = smoothed_series[i + 1 - m3..=i]
                .iter()
                .filter_map(|&x| x)
                .collect();
            if window.len() == m3 {
                let sum: f64 = window.iter().sum();
                ma3[i] = Some(sum / m3 as f64);
            } else {
                ma3[i] = None;
            }
        }
    }

    // 生成持仓信号
    let mut positions = vec![0i32; len];
    for i in 0..len {
        // 检查所有值是否都有效（非None）
        if let (Some(smoothed), Some(ma1_val), Some(ma2_val), Some(ma3_val)) =
            (smoothed_series[i], ma1[i], ma2[i], ma3[i])
        {
            if smoothed > ma3_val && ma1_val > ma2_val {
                positions[i] = 1; // 多头
            } else if smoothed < ma3_val && ma1_val < ma2_val {
                positions[i] = -1; // 空头
            } else {
                positions[i] = 0; // 空仓
            }
        } else {
            positions[i] = 0;
        }
    }

    positions
}

/// 布林线多空信号
/// series 大于 n 周期均线 + k * n周期标准差，做多；小于 n 周期均线 - k * n周期标准差，做空
pub fn boll_positions(series: &[f64], n: usize, k: f64) -> Vec<i32> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        return vec![0; len];
    }

    // 第一步：对原始序列计算 n 期移动平均
    let mut smoothed_series = vec![None; len];
    for i in 0..len {
        if i + 1 < n {
            smoothed_series[i] = None;
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            smoothed_series[i] = Some(sum / n as f64);
        }
    }

    // 计算移动平均 (sm)
    let mut sm = vec![None; len];
    for i in 0..len {
        if i + 1 < n {
            sm[i] = None;
        } else {
            let window: Vec<f64> = smoothed_series[i + 1 - n..=i]
                .iter()
                .filter_map(|&x| x)
                .collect();
            if window.len() == n {
                let sum: f64 = window.iter().sum();
                sm[i] = Some(sum / n as f64);
            } else {
                sm[i] = None;
            }
        }
    }

    // 计算移动标准差 (sd)
    let mut sd = vec![None; len];
    for i in 0..len {
        if i + 1 < n {
            sd[i] = None;
        } else {
            let window: Vec<f64> = smoothed_series[i + 1 - n..=i]
                .iter()
                .filter_map(|&x| x)
                .collect();
            if window.len() == n {
                let mean = window.iter().sum::<f64>() / n as f64;
                let variance =
                    window.iter().map(|&x| (x - mean).powi(2)).sum::<f64>() / (n - 1) as f64; // 使用 ddof=1 (样本标准差)
                sd[i] = Some(variance.sqrt());
            } else {
                sd[i] = None;
            }
        }
    }

    // 生成持仓信号
    let mut positions = vec![0i32; len];
    for i in 0..len {
        if let (Some(smoothed), Some(sm_val), Some(sd_val)) = (smoothed_series[i], sm[i], sd[i]) {
            let upper_band = sm_val + k * sd_val;
            let lower_band = sm_val - k * sd_val;

            // 使用更精确的比较，避免浮点数精度问题
            if smoothed > upper_band + 1e-10 {
                positions[i] = 1; // 做多
            } else if smoothed < lower_band - 1e-10 {
                positions[i] = -1; // 做空
            } else {
                positions[i] = 0; // 空仓
            }
        } else {
            positions[i] = 0;
        }
    }

    positions
}

/// 布林带反转策略的多空持仓信号生成函数
/// 策略逻辑：
///   1. 计算布林带：中轨为 MA(n), 上轨 = MA(n) + k*STD(n), 下轨 = MA(n) - k*STD(n)
///   2. 开多：当价格 < 下轨时，开多 (pos=+1)，一直持有至价格 > 中轨 => 平多 (pos=0)
///   3. 开空：当价格 > 上轨时，开空 (pos=-1)，一直持有至价格 < 中轨 => 平空 (pos=0)
pub fn boll_reverse_positions(series: &[f64], n: usize, k: f64) -> Vec<i32> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        return vec![0; len];
    }

    // 第一步：对原始序列计算 n 期移动平均
    let mut smoothed_series = vec![None; len];
    for i in 0..len {
        if i + 1 < n {
            smoothed_series[i] = None;
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            smoothed_series[i] = Some(sum / n as f64);
        }
    }

    // 计算布林带
    let mut upper = vec![None; len];
    let mut mid = vec![None; len];
    let mut lower = vec![None; len];

    for i in 0..len {
        if i + 1 < n {
            upper[i] = None;
            mid[i] = None;
            lower[i] = None;
        } else {
            let window: Vec<f64> = smoothed_series[i + 1 - n..=i]
                .iter()
                .filter_map(|&x| x)
                .collect();
            if window.len() == n {
                let mean = window.iter().sum::<f64>() / n as f64;
                let variance = window.iter().map(|&x| (x - mean).powi(2)).sum::<f64>() / n as f64;
                let std_dev = variance.sqrt();

                mid[i] = Some(mean);
                upper[i] = Some(mean + k * std_dev);
                lower[i] = Some(mean - k * std_dev);
            } else {
                upper[i] = None;
                mid[i] = None;
                lower[i] = None;
            }
        }
    }

    // 生成持仓信号
    let mut positions = vec![0i32; len];
    let mut current_pos = 0i32; // 当前持仓：0=空仓，+1=多头，-1=空头

    for i in 0..len {
        // 若尚未计算出 mid/upper/lower，跳过（最前面的 n-1 个数据点）
        if let (Some(upper_val), Some(mid_val), Some(lower_val)) = (upper[i], mid[i], lower[i]) {
            let price = smoothed_series[i].unwrap();

            // 若当前空仓
            if current_pos == 0 {
                // 价格 > 上轨 => 开空
                if price > upper_val {
                    current_pos = -1;
                }
                // 价格 < 下轨 => 开多
                else if price < lower_val {
                    current_pos = 1;
                }
            }
            // 若当前持有多头
            else if current_pos == 1 {
                // 当价格 > 中轨 => 平多
                if price > mid_val {
                    current_pos = 0;
                }
            }
            // 若当前持有空头
            else if current_pos == -1 {
                // 当价格 < 中轨 => 平空
                if price < mid_val {
                    current_pos = 0;
                }
            }
        } else {
            current_pos = 0;
        }

        positions[i] = current_pos;
    }

    positions
}

/// 均线的最大最小值归一化
/// 返回归一化后的值，范围在 [-1, 1] 之间
pub fn mms_positions(series: &[f64], timeperiod: usize, window: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || timeperiod == 0 || window == 0 {
        return vec![];
    }
    if timeperiod > len || window > len {
        return vec![0.0; len];
    }

    // 计算移动平均 (sm)
    let mut sm = vec![None; len];
    for i in 0..len {
        if i + 1 < timeperiod {
            sm[i] = None;
        } else {
            let sum: f64 = series[i + 1 - timeperiod..=i].iter().sum();
            sm[i] = Some(sum / timeperiod as f64);
        }
    }

    // 计算移动平均的最小值 (sm_min)
    let mut sm_min = vec![None; len];
    for i in 0..len {
        if i + 1 < window {
            sm_min[i] = None;
        } else {
            let window_values: Vec<f64> =
                sm[i + 1 - window..=i].iter().filter_map(|&x| x).collect();
            if window_values.len() == window {
                sm_min[i] = Some(window_values.iter().fold(f64::INFINITY, |a, &b| a.min(b)));
            } else {
                sm_min[i] = None;
            }
        }
    }

    // 计算移动平均的最大值 (sm_max)
    let mut sm_max = vec![None; len];
    for i in 0..len {
        if i + 1 < window {
            sm_max[i] = None;
        } else {
            let window_values: Vec<f64> =
                sm[i + 1 - window..=i].iter().filter_map(|&x| x).collect();
            if window_values.len() == window {
                sm_max[i] = Some(
                    window_values
                        .iter()
                        .fold(f64::NEG_INFINITY, |a, &b| a.max(b)),
                );
            } else {
                sm_max[i] = None;
            }
        }
    }

    // 计算归一化结果
    let mut result = vec![0.0; len];
    for i in 0..len {
        if let (Some(sm_val), Some(sm_min_val), Some(sm_max_val)) = (sm[i], sm_min[i], sm_max[i]) {
            let denominator = sm_max_val - sm_min_val;
            if denominator.abs() > 1e-10 {
                // 归一化到 [0, 1]，然后转换到 [-1, 1]
                let normalized = (sm_val - sm_min_val) / denominator;
                result[i] = normalized * 2.0 - 1.0;
            } else {
                // 如果最大值和最小值相等，设为0
                result[i] = 0.0;
            }
        } else {
            result[i] = 0.0;
        }
    }

    result
}

/// RSI 反转策略的多空持仓信号
/// 返回每个点的持仓信号（-1: 空头, 0: 空仓, 1: 多头）
pub fn rsi_reverse_positions(
    series: &[f64],
    n: usize,
    rsi_upper: f64,
    rsi_lower: f64,
    rsi_exit: f64,
) -> Vec<i32> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        return vec![0; len];
    }

    // 第一步：对原始序列计算 n 期移动平均（与 Python 一致）
    let mut smoothed_series = vec![None; len];
    for i in 0..len {
        if i + 1 < n {
            smoothed_series[i] = None;
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            smoothed_series[i] = Some(sum / n as f64);
        }
    }

    // 第二步：对移动平均后的数据计算 RSI（与 Python 一致）
    let mut rsi = vec![None; len];
    for i in 0..len {
        // 检查是否有足够的有效数据来计算 RSI
        let mut valid_count = 0;
        let mut gains = 0.0;
        let mut losses = 0.0;

        // 计算前 n 个周期的涨跌幅（使用移动平均后的数据）
        let start = if i >= n { i.saturating_sub(n) } else { 0 };
        for j in start..i {
            if j > 0
                && let (Some(current), Some(prev)) = (smoothed_series[j], smoothed_series[j - 1])
            {
                let change = current - prev;
                if change > 0.0 {
                    gains += change;
                } else {
                    losses += change.abs();
                }
                valid_count += 1;
            }
        }

        // 只有当有足够的有效数据时才计算 RSI
        if valid_count >= n - 1 {
            // 允许一个缺失值
            if losses == 0.0 {
                rsi[i] = Some(100.0);
            } else {
                let avg_gain = gains / valid_count as f64;
                let avg_loss = losses / valid_count as f64;
                let rs = avg_gain / avg_loss;
                rsi[i] = Some(100.0 - (100.0 / (1.0 + rs)));
            }
        } else {
            rsi[i] = None;
        }
    }

    // 第三步：生成持仓信号
    let mut positions = vec![0; len];
    let mut current_pos = 0; // 当前持仓：0=空仓，+1=多头，-1=空头

    for i in 0..len {
        if let Some(rsi_val) = rsi[i] {
            // 若当前空仓
            if current_pos == 0 {
                // 如果 RSI < rsi_lower，则开多
                if rsi_val < rsi_lower {
                    current_pos = 1;
                }
                // 如果 RSI > rsi_upper，则开空
                else if rsi_val > rsi_upper {
                    current_pos = -1;
                }
            }
            // 若当前持有多头
            else if current_pos == 1 {
                // 当 RSI > rsi_exit，则平多 (回到空仓)
                if rsi_val > rsi_exit {
                    current_pos = 0;
                }
            }
            // 若当前持有空头
            else if current_pos == -1 {
                // 当 RSI < rsi_exit，则平空 (回到空仓)
                if rsi_val < rsi_exit {
                    current_pos = 0;
                }
            }
        }
        // 如果无法计算出 RSI，保持空仓
        positions[i] = current_pos;
    }

    positions
}

/// tanh 多空策略
/// 返回每个点的持仓信号（-1 到 1 之间的值）
pub fn tanh_positions(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        return vec![0.0; len];
    }

    // 计算移动平均
    let mut ms = vec![None; len];
    for i in 0..len {
        if i + 1 < n {
            ms[i] = None;
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            ms[i] = Some(sum / n as f64);
        }
    }

    // 计算移动平均的均值和标准差
    let mut mean = vec![None; len];
    let mut std = vec![None; len];

    for i in 0..len {
        if i + 1 < n {
            mean[i] = None;
            std[i] = None;
        } else {
            let mut values = Vec::new();
            for j in i + 1 - n..=i {
                if let Some(val) = ms[j] {
                    values.push(val);
                }
            }

            if values.len() == n {
                let sum: f64 = values.iter().sum();
                let mean_val = sum / n as f64;
                mean[i] = Some(mean_val);

                // 使用 pandas 的 ddof=1 默认行为（n-1 自由度）
                let variance =
                    values.iter().map(|&x| (x - mean_val).powi(2)).sum::<f64>() / (n - 1) as f64;
                std[i] = Some(variance.sqrt());
            }
        }
    }

    // 计算 tanh 值
    let mut result = vec![0.0; len];
    for i in 0..len {
        if let (Some(ms_val), Some(mean_val), Some(std_val)) = (ms[i], mean[i], std[i])
            && std_val > 0.0
        {
            let z_score = (ms_val - mean_val) / std_val;
            result[i] = z_score.tanh();
        }
    }

    // 四舍五入到两位小数
    for val in &mut result {
        *val = (*val * 100.0).round() / 100.0;
    }

    result
}

/// rank 多空策略
/// 返回每个点的持仓信号（-1 到 1 之间的值）
pub fn rank_positions(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    if len == 0 || n == 0 {
        return vec![];
    }
    if n > len {
        return vec![0.0; len];
    }

    // 计算移动平均
    let mut ms = vec![None; len];
    for i in 0..len {
        if i + 1 < n {
            ms[i] = None;
        } else {
            let sum: f64 = series[i + 1 - n..=i].iter().sum();
            ms[i] = Some(sum / n as f64);
        }
    }

    // 计算 rank
    let mut result = vec![0.0; len];
    for i in 0..len {
        if i + 1 < n {
            result[i] = 0.0;
        } else {
            let mut values = Vec::new();
            for j in i + 1 - n..=i {
                if let Some(val) = ms[j] {
                    values.push(val);
                }
            }

            if values.len() == n {
                // 计算当前值在窗口中的排名
                let current_val = values[n - 1];
                let mut rank = 1;
                for &val in &values[..n - 1] {
                    if val < current_val {
                        rank += 1;
                    }
                }

                // 计算归一化的 rank
                let normalized_rank = (rank - 1) as f64 / (n - 1) as f64;
                let x = (normalized_rank - 0.5) * 2.0;
                result[i] = x;
            }
        }
    }

    // 四舍五入到两位小数
    for val in &mut result {
        *val = (*val * 100.0).round() / 100.0;
    }

    result
}

/// 计算指数移动平均 (EMA)
/// 返回每个点的 EMA 值
pub fn ema(series: &[f64], period: usize) -> Vec<f64> {
    // talib-compatible EMA: warmup [0, period-1) is NaN, position
    // (period-1) is seeded with the simple mean of the first `period`
    // samples, then the standard recurrence runs forward. This matches
    // talib.EMA's output bit-for-bit (verified by Phase A's
    // `test_ema_matches_talib`). The previous rs-czsc implementation
    // seeded with `series[0]`, which produced visible divergence in
    // the first ~30 bars.
    let len = series.len();
    if len == 0 || period == 0 {
        return vec![];
    }
    if period > len {
        return vec![f64::NAN; len];
    }

    let mut result = vec![f64::NAN; len];
    let alpha = 2.0 / (period + 1) as f64;

    let seed: f64 = series.iter().take(period).sum::<f64>() / period as f64;
    result[period - 1] = seed;
    for i in period..len {
        result[i] = alpha * series[i] + (1.0 - alpha) * result[i - 1];
    }

    result
}

/// 计算真实波幅 (True Range)
/// 返回每个点的真实波幅值
pub fn true_range(high: &[f64], low: &[f64], close_prev: &[f64]) -> Vec<f64> {
    let len = high.len();
    if len == 0 {
        return vec![];
    }

    let mut result = vec![0.0; len];

    for i in 0..len {
        let tr1 = high[i] - low[i];

        // 与Python的close.shift(1)行为一致
        // 第一个位置使用NaN，其他位置使用close_prev
        let prev_close = if i == 0 { f64::NAN } else { close_prev[i] };

        let tr2 = if prev_close.is_nan() {
            f64::NAN
        } else {
            (high[i] - prev_close).abs()
        };
        let tr3 = if prev_close.is_nan() {
            f64::NAN
        } else {
            (low[i] - prev_close).abs()
        };

        // 取三个值中的最大值，处理NaN
        if tr2.is_nan() || tr3.is_nan() {
            // 如果有NaN，只使用tr1
            result[i] = tr1;
        } else {
            result[i] = tr1.max(tr2).max(tr3);
        }
    }

    result
}

/// RSX-SS2 - 自适应平滑的RSI变体
/// 返回每个点的 RSX-SS2 值
pub fn rsx_ss2(close: &[f64], period: usize, smooth_period: usize) -> Vec<f64> {
    let len = close.len();
    if len == 0 || period == 0 || smooth_period == 0 {
        return vec![];
    }

    // 计算价格变化
    let mut delta = vec![f64::NAN; len];
    for i in 1..len {
        delta[i] = close[i] - close[i - 1];
    }

    // 计算增益和损失
    let mut gain = vec![f64::NAN; len];
    let mut loss = vec![f64::NAN; len];
    for i in 0..len {
        if i == 0 {
            gain[i] = 0.0;
            loss[i] = 0.0;
        } else if delta[i] > 0.0 {
            gain[i] = delta[i];
            loss[i] = 0.0;
        } else {
            gain[i] = 0.0;
            loss[i] = -delta[i];
        }
    }

    // 计算平均增益和平均损失 (使用 EMA)
    let alpha = 1.0 / period as f64;
    let mut avg_gain = vec![f64::NAN; len];
    let mut avg_loss = vec![f64::NAN; len];

    // 找到第一个非 NaN 的值来初始化
    let mut first_valid_idx = None;
    for i in 0..len {
        if !gain[i].is_nan() && !loss[i].is_nan() {
            first_valid_idx = Some(i);
            break;
        }
    }

    if let Some(idx) = first_valid_idx {
        // 使用第一个有效值作为初始值，与 pandas ewm 行为一致
        avg_gain[idx] = gain[idx];
        avg_loss[idx] = loss[idx];

        // 计算 EMA，与 pandas ewm(adjust=False) 行为一致
        for i in idx + 1..len {
            if !gain[i].is_nan() && !loss[i].is_nan() {
                avg_gain[i] = alpha * gain[i] + (1.0 - alpha) * avg_gain[i - 1];
                avg_loss[i] = alpha * loss[i] + (1.0 - alpha) * avg_loss[i - 1];
            } else {
                avg_gain[i] = f64::NAN;
                avg_loss[i] = f64::NAN;
            }
        }
    }

    // 计算 RSI
    let mut rsi = vec![f64::NAN; len];
    for i in 0..len {
        if avg_gain[i].is_nan() || avg_loss[i].is_nan() {
            rsi[i] = f64::NAN;
        } else if avg_loss[i] == 0.0 {
            rsi[i] = 100.0;
        } else {
            let rs = avg_gain[i] / avg_loss[i];
            rsi[i] = 100.0 - (100.0 / (1.0 + rs));
        }
    }

    // 第一个值设为 NaN，与 Python 行为一致
    if len > 0 {
        rsi[0] = f64::NAN;
    }

    // 使用终极平滑器进行平滑
    ultimate_smoother(&rsi, smooth_period as f64)
}

/// Jurik波动平滑器 - 低噪声波动指标
/// 返回平滑波动率值
pub fn jurik_volty(close: &[f64], period: usize, power: f64) -> Vec<f64> {
    let len = close.len();
    if len == 0 || period == 0 {
        return vec![];
    }

    // 计算价格变化
    let mut price_change = vec![f64::NAN; len];
    for i in 1..len {
        price_change[i] = (close[i] - close[i - 1]).abs();
    }

    // 初步平滑 - 第一次 EMA
    let span1 = period / 2;
    let alpha1 = 2.0 / (span1 + 1) as f64;
    let mut smooth1 = vec![f64::NAN; len];

    // 找到第一个非 NaN 的值来初始化
    let mut first_valid_idx = None;
    for i in 0..len {
        if !price_change[i].is_nan() {
            first_valid_idx = Some(i);
            break;
        }
    }

    if let Some(idx) = first_valid_idx {
        // 检查是否所有非 NaN 值都相同（pandas ewm 的特殊处理）
        let first_value = price_change[idx];
        let mut all_same = true;
        for i in idx..len {
            if !price_change[i].is_nan() && price_change[i] != first_value {
                all_same = false;
                break;
            }
        }

        if all_same {
            // 如果所有值都相同，直接返回原始值（pandas ewm 行为）
            for i in idx..len {
                if !price_change[i].is_nan() {
                    smooth1[i] = price_change[i];
                }
            }
        } else {
            // 正常 EMA 计算
            smooth1[idx] = price_change[idx];
            for i in idx + 1..len {
                if !price_change[i].is_nan() {
                    smooth1[i] = alpha1 * price_change[i] + (1.0 - alpha1) * smooth1[i - 1];
                } else {
                    smooth1[i] = f64::NAN;
                }
            }
        }
    }

    // 第二次 EMA
    let mut smooth2 = vec![f64::NAN; len];

    // 找到第一个非 NaN 的值来初始化
    let mut first_valid_idx2 = None;
    for i in 0..len {
        if !smooth1[i].is_nan() {
            first_valid_idx2 = Some(i);
            break;
        }
    }

    if let Some(idx) = first_valid_idx2 {
        // 检查是否所有非 NaN 值都相同（pandas ewm 的特殊处理）
        let first_value = smooth1[idx];
        let mut all_same = true;
        for i in idx..len {
            if !smooth1[i].is_nan() && smooth1[i] != first_value {
                all_same = false;
                break;
            }
        }

        if all_same {
            // 如果所有值都相同，直接返回原始值（pandas ewm 行为）
            for i in idx..len {
                if !smooth1[i].is_nan() {
                    smooth2[i] = smooth1[i];
                }
            }
        } else {
            // 正常 EMA 计算
            smooth2[idx] = smooth1[idx];
            for i in idx + 1..len {
                if !smooth1[i].is_nan() {
                    smooth2[i] = alpha1 * smooth1[i] + (1.0 - alpha1) * smooth2[i - 1];
                } else {
                    smooth2[i] = f64::NAN;
                }
            }
        }
    }

    // Jurik特定平滑公式
    let mut jv = vec![0.0; len];
    for i in 2..len {
        if !smooth2[i].is_nan() && !smooth2[i - 1].is_nan() {
            jv[i] = (smooth2[i] + (smooth2[i] - smooth2[i - 1]) * 0.5) * power;
        } else {
            jv[i] = 0.0;
        }
    }

    // 最终平滑 - 第三次 EMA，与Pandas ewm(span=period/3, adjust=False).mean()行为完全一致
    let span3 = period / 3;
    let alpha3 = 2.0 / (span3 + 1) as f64;
    let mut result = vec![0.0; len];

    // 找到第一个非零的 jv 值来初始化
    let mut first_valid_idx3 = None;
    for i in 0..len {
        if jv[i] != 0.0 {
            first_valid_idx3 = Some(i);
            break;
        }
    }

    if let Some(idx) = first_valid_idx3 {
        // 检查是否所有非零值都相同（pandas ewm 的特殊处理）
        let first_value = jv[idx];
        let mut all_same = true;
        for i in idx..len {
            if jv[i] != 0.0 && jv[i] != first_value {
                all_same = false;
                break;
            }
        }

        if all_same {
            // 如果所有值都相同，直接返回原始值（pandas ewm 行为）
            for i in idx..len {
                if jv[i] != 0.0 {
                    result[i] = jv[i];
                }
            }
        } else {
            // 正常 EMA 计算 - 与Pandas ewm(adjust=False)行为完全一致
            result[idx] = jv[idx];
            for i in idx + 1..len {
                result[i] = alpha3 * jv[i] + (1.0 - alpha3) * result[i - 1];
            }
        }
    }

    result
}

/// 终极通道 - 基于终极平滑器的通道指标
/// 返回 (中线, 上轨, 下轨)
pub fn ultimate_channel(
    high: &[f64],
    low: &[f64],
    close: &[f64],
    period: usize,
    multiplier: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let len = high.len();
    if len == 0 || period == 0 {
        return (vec![], vec![], vec![]);
    }

    // 计算终极平滑中线
    let midline = ultimate_smoother(close, period as f64);

    // 计算平滑真实波幅 (STR)
    let mut close_prev = vec![0.0; len];
    for i in 1..len {
        close_prev[i] = close[i - 1];
    }

    let tr = true_range(high, low, &close_prev);

    // 计算 ATR (平均真实波幅)
    let mut atr = vec![0.0; len];
    // 前 period-1 个值设为 NaN (与 Pandas rolling().mean() 行为一致)
    for i in 0..period - 1 {
        atr[i] = f64::NAN;
    }

    if len >= period {
        // 计算第一个 ATR 值
        let mut sum = 0.0;
        for i in 0..period {
            sum += tr[i];
        }
        atr[period - 1] = sum / period as f64;

        // 计算后续 ATR 值
        for i in period..len {
            atr[i] = (atr[i - 1] * (period - 1) as f64 + tr[i]) / period as f64;
        }
    }

    // 使用终极平滑器平滑 ATR
    let str = ultimate_smoother(&atr, (period / 2) as f64);

    // 计算通道
    let mut upper = vec![0.0; len];
    let mut lower = vec![0.0; len];
    for i in 0..len {
        upper[i] = midline[i] + multiplier * str[i];
        lower[i] = midline[i] - multiplier * str[i];
    }

    (midline, upper, lower)
}

/// 终极带 - 基于终极平滑器的布林带变体
/// 返回 (中线, 上轨, 下轨)
pub fn ultimate_bands(
    close: &[f64],
    period: usize,
    std_multiplier: f64,
    smooth_period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    let len = close.len();
    if len == 0 || period == 0 || smooth_period == 0 {
        return (vec![], vec![], vec![]);
    }

    // 如果数据长度小于 period，返回空结果
    if len < period {
        return (vec![], vec![], vec![]);
    }

    // 计算终极平滑中线
    let midline = ultimate_smoother(close, period as f64);

    // 计算标准差并平滑
    let mut std = vec![0.0; len];

    // 前 period-1 个值设为 NaN (与 Pandas rolling().std() 行为一致)
    if period > 1 {
        for i in 0..(period - 1) {
            std[i] = f64::NAN;
        }
    }

    // 计算滚动标准差
    for i in (period - 1)..len {
        let start = if i >= (period - 1) {
            i.saturating_sub(period - 1)
        } else {
            0
        };
        let end = i + 1;

        // 确保索引有效
        if start >= len || end > len || start >= end {
            std[i] = f64::NAN;
            continue;
        }

        // 计算均值
        let mut sum = 0.0;
        for j in start..end {
            sum += close[j];
        }
        let mean = sum / period as f64;

        // 计算方差
        let mut variance = 0.0;
        for j in start..end {
            let diff = close[j] - mean;
            variance += diff * diff;
        }

        // 使用 ddof=1 (与 Pandas 默认行为一致)
        if period > 1 {
            std[i] = (variance / (period - 1) as f64).sqrt();
        } else {
            std[i] = 0.0;
        }
    }

    // 使用终极平滑器平滑标准差
    let smooth_std = ultimate_smoother(&std, smooth_period as f64);

    // 计算通道
    let mut upper = vec![0.0; len];
    let mut lower = vec![0.0; len];
    for i in 0..len {
        upper[i] = midline[i] + std_multiplier * smooth_std[i];
        lower[i] = midline[i] - std_multiplier * smooth_std[i];
    }

    (midline, upper, lower)
}

/// 终极波动指标 (UOS) - 多周期融合振荡器
/// 返回 UOS 值
pub fn ultimate_oscillator(
    high: &[f64],
    low: &[f64],
    close: &[f64],
    short_period: usize,
    med_period: usize,
    long_period: usize,
) -> Vec<f64> {
    let len = high.len();
    if len == 0 || short_period == 0 || med_period == 0 || long_period == 0 {
        return vec![];
    }

    // 计算买方压力 - 与Python实现完全一致
    let mut buying_pressure = vec![0.0; len];
    for i in 0..len {
        let prev_close = if i > 0 { close[i - 1] } else { close[i] };
        // 使用 min(low[i], prev_close) 与Python的pd.concat([low, close.shift(1)], axis=1).min(axis=1)一致
        let min_val = low[i].min(prev_close);
        buying_pressure[i] = close[i] - min_val;
    }

    // 计算真实波幅 - 与Python实现完全一致
    let mut close_prev = vec![0.0; len];
    for i in 1..len {
        close_prev[i] = close[i - 1];
    }
    let true_range = true_range(high, low, &close_prev);

    // 计算不同周期的平均值 - 与Pandas rolling().sum()行为完全一致
    let mut avg7 = vec![f64::NAN; len];
    let mut avg14 = vec![f64::NAN; len];
    let mut avg28 = vec![f64::NAN; len];

    // 计算 avg7 - 与Pandas rolling().sum()行为完全一致
    for i in (short_period - 1)..len {
        let mut bp_sum = 0.0;
        let mut tr_sum = 0.0;
        // 检查是否有NaN值，如果有则结果也为NaN
        let mut has_nan = false;
        for j in (i + 1 - short_period)..=i {
            if buying_pressure[j].is_nan() || true_range[j].is_nan() {
                has_nan = true;
                break;
            }
            bp_sum += buying_pressure[j];
            tr_sum += true_range[j];
        }
        if has_nan {
            avg7[i] = f64::NAN;
        } else if tr_sum != 0.0 {
            avg7[i] = bp_sum / tr_sum;
        } else {
            avg7[i] = 0.0;
        }
    }

    // 计算 avg14 - 与Pandas rolling().sum()行为完全一致
    for i in (med_period - 1)..len {
        let mut bp_sum = 0.0;
        let mut tr_sum = 0.0;
        // 检查是否有NaN值，如果有则结果也为NaN
        let mut has_nan = false;
        for j in (i + 1 - med_period)..=i {
            if buying_pressure[j].is_nan() || true_range[j].is_nan() {
                has_nan = true;
                break;
            }
            bp_sum += buying_pressure[j];
            tr_sum += true_range[j];
        }
        if has_nan {
            avg14[i] = f64::NAN;
        } else if tr_sum != 0.0 {
            avg14[i] = bp_sum / tr_sum;
        } else {
            avg14[i] = 0.0;
        }
    }

    // 计算 avg28 - 与Pandas rolling().sum()行为完全一致
    for i in (long_period - 1)..len {
        let mut bp_sum = 0.0;
        let mut tr_sum = 0.0;
        // 检查是否有NaN值，如果有则结果也为NaN
        let mut has_nan = false;
        for j in (i + 1 - long_period)..=i {
            if buying_pressure[j].is_nan() || true_range[j].is_nan() {
                has_nan = true;
                break;
            }
            bp_sum += buying_pressure[j];
            tr_sum += true_range[j];
        }
        if has_nan {
            avg28[i] = f64::NAN;
        } else if tr_sum != 0.0 {
            avg28[i] = bp_sum / tr_sum;
        } else {
            avg28[i] = 0.0;
        }
    }

    // 计算 UOS - 与Python实现完全一致
    let mut uos = vec![f64::NAN; len];
    for i in 0..len {
        // 检查是否有 NaN 值
        if avg7[i].is_nan() || avg14[i].is_nan() || avg28[i].is_nan() {
            uos[i] = f64::NAN;
        } else {
            uos[i] = 100.0 * ((4.0 * avg7[i]) + (2.0 * avg14[i]) + avg28[i]) / (4.0 + 2.0 + 1.0);
        }
    }

    uos
}

/// 指数平滑 - 基础时间序列平滑技术
/// 返回平滑后的序列
pub fn exponential_smoothing(series: &[f64], alpha: f64) -> Vec<f64> {
    let len = series.len();
    if len == 0 {
        return vec![];
    }

    let mut result = vec![0.0; len];

    // 第一个值保持不变
    result[0] = series[0];

    // 应用指数平滑公式
    for i in 1..len {
        result[i] = alpha * series[i] + (1.0 - alpha) * result[i - 1];
    }

    result
}

/// Holt-Winters三参数平滑 - 支持趋势和季节性的平滑方法
/// 返回平滑后的序列
pub fn holt_winters(
    series: &[f64],
    season_length: usize,
    alpha: f64,
    beta: f64,
    gamma: f64,
) -> Vec<f64> {
    let n = series.len();
    if n == 0 || season_length == 0 || season_length > n {
        return vec![];
    }

    let mut level = vec![0.0; n];
    let mut trend = vec![0.0; n];
    let mut season = vec![0.0; n];
    let mut forecast = vec![0.0; n];

    // 初始化
    let initial_level = series[..season_length].iter().sum::<f64>() / season_length as f64;
    for i in 0..season_length {
        level[i] = initial_level;
        trend[i] = 0.0;
        season[i] = series[i] - level[i];
    }

    // 三重指数平滑
    for i in season_length..n {
        level[i] = alpha * (series[i] - season[i - season_length])
            + (1.0 - alpha) * (level[i - 1] + trend[i - 1]);
        trend[i] = beta * (level[i] - level[i - 1]) + (1.0 - beta) * trend[i - 1];
        season[i] = gamma * (series[i] - level[i]) + (1.0 - gamma) * season[i - season_length];
        forecast[i] = level[i] + trend[i] + season[i];
    }

    // 前 season_length 个值设为原始值
    for i in 0..season_length {
        forecast[i] = series[i];
    }

    forecast
}
