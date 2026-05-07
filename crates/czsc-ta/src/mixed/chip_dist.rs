use ordered_float::OrderedFloat;
use pyo3_stub_gen::derive::gen_stub_pyfunction;
use std::collections::HashMap;

use numpy::ndarray::Array1;
use numpy::{IntoPyArray, PyArray1, PyReadonlyArray2};
use pyo3::prelude::*;

/// 计算筹码分布（三角形分布 + 筹码沉淀机制）
///
/// 此函数用于估算基于历史K线的筹码分布情况，结合三角形分布模型和筹码沉淀（衰减）机制。
///
/// # Python 接口说明
///
/// 输入一个二维 numpy 数组，形状为 (N, 3)，每一行对应一根K线，列顺序为：
/// `[high, low, vol]`，类型必须为 `float64`。
///
/// 示例：
/// ```python
/// columns = ['high', 'low', 'vol']
/// arr2 = df[columns].to_numpy(dtype=np.float64)
/// price_centers, chip_dist = chip_distribution_triangle(arr2, 0.01, 0.9)
/// ```
///
/// # 参数
///
/// - `data`: 二维数组，形状为 (N, 3)，分别是每根K线的最高价、最低价和成交量。
/// - `price_step`: 分档间隔（如0.01表示以0.01为单位划分价格区间）。
/// - `decay_factor`: 筹码衰减因子，表示前一根K线上的筹码有多少比例沉淀保留到下一根K线上，范围为(0, 1)，例如0.98表示保留98%。
///
/// # 返回值
///
/// 返回一个元组 `(price_centers, chip_distribution)`:
/// - `price_centers`: 一维数组，表示价格分布区间的中心价位。
/// - `chip_distribution`: 一维数组，对应每个价格中心的筹码强度（权重/密度）。
///
/// 返回的两个数组长度相同，可用于绘制筹码分布图或进一步分析。
#[pyfunction]
#[gen_stub_pyfunction]
pub fn chip_distribution_triangle<'py>(
    py: Python<'py>,
    data: PyReadonlyArray2<'py, f64>,
    price_step: f64,
    decay_factor: f64,
) -> (Bound<'py, PyArray1<f64>>, Bound<'py, PyArray1<f64>>) {
    let data = data.as_array();
    let nrows = data.shape()[0];

    // 安全校验
    let ncols = data.shape()[1];
    if ncols < 3 {
        panic!("Input array must have at least 3 columns (high, low, vol)");
    }

    // 第2列是 low，第1列是 high
    let low_col = data.column(1);
    let high_col = data.column(0);

    // 取 min(low) 和 max(high)
    let min_low = low_col.fold(f64::INFINITY, |a, &b| a.min(b));
    let max_high = high_col.fold(f64::NEG_INFINITY, |a, &b| a.max(b));

    // 计算 price bins 区间
    let min_price = (min_low / price_step).floor() * price_step;
    let max_price = (max_high / price_step).ceil() * price_step;

    let nbins = ((max_price - min_price) / price_step).ceil() as usize;

    let mut chip_dist = Array1::<f64>::zeros(nbins);

    let price_centers =
        Array1::from_iter((0..nbins).map(|i| min_price + price_step * (i as f64 + 0.5)));

    // 缓存权重映射
    let mut weight_cache: HashMap<(OrderedFloat<f64>, OrderedFloat<f64>), Vec<f64>> =
        HashMap::new();

    for i in 0..nrows {
        let high = data[[i, 0]];
        let low = data[[i, 1]];
        let vol = data[[i, 2]];

        if high <= low || vol == 0.0 {
            continue;
        }

        let start_idx = ((low - min_price) / price_step).floor().max(0.0) as usize;
        let end_idx = ((high - min_price) / price_step).ceil().min(nbins as f64) as usize;

        if end_idx <= start_idx || end_idx > nbins {
            continue;
        }

        // 衰减之前的筹码分布
        for x in chip_dist.iter_mut() {
            *x *= decay_factor;
        }

        // 构造三角分布权重
        // 三角权重缓存查找
        let low_key = OrderedFloat(low);
        let high_key = OrderedFloat(high);

        let weights = weight_cache.entry((low_key, high_key)).or_insert_with(|| {
            let mid_price = (low + high) / 2.0;
            let mut w = Vec::with_capacity(end_idx - start_idx);
            for idx in start_idx..end_idx {
                let center_price = min_price + price_step * (idx as f64 + 0.5);
                let weight = 1.0 - ((center_price - mid_price).abs()) / ((high - low) / 2.0);
                w.push(weight.max(0.0));
            }
            w
        });

        let weight_sum: f64 = weights.iter().sum();
        if weight_sum == 0.0 {
            continue;
        }

        // 归一化权重并加权更新 chip_dist
        for (j, idx) in (start_idx..end_idx).enumerate() {
            chip_dist[idx] += vol * weights[j] / weight_sum;
        }
    }

    // 归一化 chip_dist
    let total: f64 = chip_dist.sum();
    if total > 0.0 {
        chip_dist.iter_mut().for_each(|x| *x /= total);
    }

    (price_centers.into_pyarray(py), chip_dist.into_pyarray(py))
}
