pub fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        0.0
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

pub fn std_pop(values: &[f64]) -> f64 {
    if values.is_empty() {
        return 0.0;
    }
    let m = mean(values);
    (values.iter().map(|x| (x - m).powi(2)).sum::<f64>() / values.len() as f64).sqrt()
}

pub fn percentile_linear(values: &[f64], p: f64) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    let mut x = values.to_vec();
    x.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    if x.len() == 1 {
        return Some(x[0]);
    }
    let rank = p.clamp(0.0, 100.0) / 100.0 * (x.len() as f64 - 1.0);
    let lo = rank.floor() as usize;
    let hi = rank.ceil() as usize;
    if lo == hi {
        Some(x[lo])
    } else {
        Some(x[lo] + (x[hi] - x[lo]) * (rank - lo as f64))
    }
}

pub fn median_abs(values: &[f64]) -> f64 {
    let mut x: Vec<f64> = values.iter().map(|v| v.abs()).collect();
    x.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    if x.is_empty() {
        0.0
    } else if x.len() % 2 == 1 {
        x[x.len() / 2]
    } else {
        (x[x.len() / 2 - 1] + x[x.len() / 2]) / 2.0
    }
}

pub fn max_amplitude_pct(prices: &[f64]) -> f64 {
    if prices.is_empty() {
        return 100.0;
    }
    let max_price = prices.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let min_price = prices.iter().copied().fold(f64::INFINITY, f64::min);
    if min_price == 0.0 {
        100.0
    } else {
        (max_price - min_price) / min_price * 100.0
    }
}

pub fn linreg_predict(xs: &[f64], ys: &[f64], x: f64) -> Option<f64> {
    if xs.len() != ys.len() || xs.is_empty() {
        return None;
    }
    let n = xs.len() as f64;
    let mean_x = xs.iter().sum::<f64>() / n;
    let mean_y = ys.iter().sum::<f64>() / n;
    let cov = xs
        .iter()
        .zip(ys.iter())
        .map(|(xv, yv)| (xv - mean_x) * (yv - mean_y))
        .sum::<f64>();
    let var_x = xs.iter().map(|xv| (xv - mean_x).powi(2)).sum::<f64>();
    if var_x == 0.0 {
        return Some(mean_y);
    }
    let slope = cov / var_x;
    let intercept = mean_y - slope * mean_x;
    Some(slope * x + intercept)
}

pub fn overlap(h1: f64, l1: f64, h2: f64, l2: f64) -> bool {
    l1.max(l2) < h1.min(h2)
}

#[cfg(test)]
mod tests {
    use super::linreg_predict;

    #[test]
    fn linreg_predict_returns_constant_for_single_sample() {
        let xs = [1.0];
        let ys = [10.0];
        let pred = linreg_predict(&xs, &ys, 99.0);
        assert_eq!(pred, Some(10.0));
    }
}
