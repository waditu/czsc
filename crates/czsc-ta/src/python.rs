//! czsc-ta 的 PyO3 绑定注册表。
//!
//! 镜像 rs-czsc 原本放在其 python crate 里的 wrapper 层
//! （rs_czsc/python/src/utils/ta.rs）；我们把 `#[pyfunction]` 外壳
//! 搬到 czsc-ta 自身，这样 czsc-python 只负责编排 `register()`
//! 调用。除非启用 `python` feature（numpy-bound 条目则需要
//! `rust-numpy`），否则所有 wrapper 都处于休眠状态。

use pyo3::prelude::*;

use crate::{mixed, pure};

#[pyfunction]
fn ultimate_smoother(close: Vec<f64>, period: f64) -> Vec<f64> {
    pure::ultimate_smoother(&close, period)
}

#[pyfunction]
fn rolling_rank(series: Vec<f64>, window: usize) -> Vec<f64> {
    // 把 Option<usize> 转成 f64（None -> NaN），这样 `np.asarray(...)` 落到
    // float64 dtype，`np.isfinite(out[window:])` 也能按预期工作。
    // 消费 rank 位置的 Python 调用方可以用 `.dropna()` 代替对 None 的过滤。
    pure::rolling_rank(&series, window)
        .into_iter()
        .map(|opt| opt.map(|r| r as f64).unwrap_or(f64::NAN))
        .collect()
}

#[pyfunction]
#[pyo3(signature = (series, n=None, *, period=None, length=None))]
fn sma(
    series: Vec<f64>,
    n: Option<usize>,
    period: Option<usize>,
    length: Option<usize>,
) -> Vec<f64> {
    // 关键字参数情况和 `ema` 一样 —— talib 的关键字是 `timeperiod` /
    // pandas-ta 的是 `length`；rs-czsc 历史脚本传 `n` / `period`。
    // Phase A parity test 调用 `ta.sma(series, length=20)`。
    let p = n.or(period).or(length).unwrap_or(0);
    pure::sma(&series, p)
}

#[pyfunction]
fn single_sma_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::single_sma_positions(&series, n)
}

#[pyfunction]
fn single_ema_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::single_ema_positions(&series, n)
}

#[pyfunction]
fn mid_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::mid_positions(&series, n)
}

#[pyfunction]
fn double_sma_positions(series: Vec<f64>, n: usize, m: usize) -> Vec<f64> {
    pure::double_sma_positions(&series, n, m)
}

#[pyfunction]
fn triple_sma_positions(series: Vec<f64>, m1: usize, m2: usize, m3: usize) -> Vec<i32> {
    pure::triple_sma_positions(&series, m1, m2, m3)
}

#[pyfunction]
fn boll_positions(series: Vec<f64>, n: usize, k: f64) -> Vec<i32> {
    pure::boll_positions(&series, n, k)
}

#[pyfunction]
fn boll_reverse_positions(series: Vec<f64>, n: usize, k: f64) -> Vec<i32> {
    pure::boll_reverse_positions(&series, n, k)
}

#[pyfunction]
fn mms_positions(series: Vec<f64>, timeperiod: usize, window: usize) -> Vec<f64> {
    pure::mms_positions(&series, timeperiod, window)
}

#[pyfunction]
fn rsi_reverse_positions(
    series: Vec<f64>,
    n: usize,
    rsi_upper: f64,
    rsi_lower: f64,
    rsi_exit: f64,
) -> Vec<i32> {
    pure::rsi_reverse_positions(&series, n, rsi_upper, rsi_lower, rsi_exit)
}

#[pyfunction]
fn tanh_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::tanh_positions(&series, n)
}

#[pyfunction]
fn rank_positions(series: Vec<f64>, n: usize) -> Vec<f64> {
    pure::rank_positions(&series, n)
}

#[pyfunction]
#[pyo3(signature = (series, n=None, *, period=None, length=None))]
fn ema(
    series: Vec<f64>,
    n: Option<usize>,
    period: Option<usize>,
    length: Option<usize>,
) -> Vec<f64> {
    // 接受以下任一形式：位置参数 `n`、关键字参数 `period=`（rs-czsc 遗留）
    // 或 `length=`（talib / pandas-ta 惯例）。Phase A parity test
    // 中 `test/unit/test_ta_parity.py::test_ema_matches_talib` 调用
    // `ta.ema(series, length=14)`；rs-czsc 历史脚本传 `period=14`。
    // 解析顺序优先保留位置参数路径，让既有的位置参数调用方继续工作。
    let p = n.or(period).or(length).unwrap_or(0);
    pure::ema(&series, p)
}

#[pyfunction]
fn true_range(high: Vec<f64>, low: Vec<f64>, close_prev: Vec<f64>) -> Vec<f64> {
    pure::true_range(&high, &low, &close_prev)
}

#[pyfunction]
fn rsx_ss2(close: Vec<f64>, period: usize, smooth_period: usize) -> Vec<f64> {
    pure::rsx_ss2(&close, period, smooth_period)
}

#[pyfunction]
fn jurik_volty(close: Vec<f64>, period: usize, power: f64) -> Vec<f64> {
    pure::jurik_volty(&close, period, power)
}

#[pyfunction]
fn ultimate_channel(
    high: Vec<f64>,
    low: Vec<f64>,
    close: Vec<f64>,
    period: usize,
    multiplier: f64,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    pure::ultimate_channel(&high, &low, &close, period, multiplier)
}

#[pyfunction]
fn ultimate_bands(
    close: Vec<f64>,
    period: usize,
    std_multiplier: f64,
    smooth_period: usize,
) -> (Vec<f64>, Vec<f64>, Vec<f64>) {
    pure::ultimate_bands(&close, period, std_multiplier, smooth_period)
}

#[pyfunction]
fn ultimate_oscillator(
    high: Vec<f64>,
    low: Vec<f64>,
    close: Vec<f64>,
    short_period: usize,
    med_period: usize,
    long_period: usize,
) -> Vec<f64> {
    pure::ultimate_oscillator(&high, &low, &close, short_period, med_period, long_period)
}

#[pyfunction]
fn exponential_smoothing(series: Vec<f64>, alpha: f64) -> Vec<f64> {
    pure::exponential_smoothing(&series, alpha)
}

#[pyfunction]
fn holt_winters(
    series: Vec<f64>,
    season_length: usize,
    alpha: f64,
    beta: f64,
    gamma: f64,
) -> Vec<f64> {
    pure::holt_winters(&series, season_length, alpha, beta, gamma)
}

/// 把迁移过来的 czsc-ta 函数挂到 czsc-python 传入的父模块上。构建一个
/// `ta` 子模块，镜像 design doc §3.1 的命名空间映射（czsc.ta.* 以及在
/// 顶层重复暴露）。
pub fn register(py: Python<'_>, parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let ta = PyModule::new(py, "ta")?;
    // 设置全限定的 __name__，使 `czsc.ta`（通过 sys.modules 别名暴露）
    // 报告 `__name__ == "czsc._native.ta"`。检查命名空间来源的
    // public-API parity test 需要这个值；当该子模块里的类被
    // pickle 往返序列化时也需要这个值。
    ta.setattr("__name__", "czsc._native.ta")?;

    macro_rules! add {
        ($($name:ident),+ $(,)?) => {{
            $(
                ta.add_function(wrap_pyfunction!($name, &ta)?)?;
                parent.add_function(wrap_pyfunction!($name, parent)?)?;
            )+
        }};
    }

    add!(
        ultimate_smoother,
        rolling_rank,
        sma,
        single_sma_positions,
        single_ema_positions,
        mid_positions,
        double_sma_positions,
        triple_sma_positions,
        boll_positions,
        boll_reverse_positions,
        mms_positions,
        rsi_reverse_positions,
        tanh_positions,
        rank_positions,
        ema,
        true_range,
        rsx_ss2,
        jurik_volty,
        ultimate_channel,
        ultimate_bands,
        ultimate_oscillator,
        exponential_smoothing,
        holt_winters,
    );

    // numpy-bound 条目
    ta.add_function(wrap_pyfunction!(
        mixed::chip_dist::chip_distribution_triangle,
        &ta
    )?)?;
    parent.add_function(wrap_pyfunction!(
        mixed::chip_dist::chip_distribution_triangle,
        parent
    )?)?;

    // 把子模块注册到 sys.modules，这样 `from czsc._native.ta
    // import ema`（以及 `import czsc._native.ta`）就能像纯 Python
    // 包一样工作。`parent.add_submodule` 只是把它设置为父模块的
    // 一个属性 —— Python 的 import 机制在做嵌套模块解析时实际查询的
    // 是 sys.modules。
    let sys = py.import("sys")?;
    let py_modules = sys.getattr("modules")?;
    py_modules.set_item("czsc._native.ta", &ta)?;
    // 使用 `parent.add` 而不是 `add_submodule`，这样可以让属性 key
    // （`parent.ta`）与模块的全限定 __name__（`czsc._native.ta`）相互
    // 独立地受控。add_submodule 用全限定名作为属性，会把子模块
    // 暴露成 `parent.czsc._native.ta` 而不是 `parent.ta`。
    parent.add("ta", &ta)?;
    Ok(())
}
