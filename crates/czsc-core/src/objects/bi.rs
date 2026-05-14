use super::{
    bar::{NewBar, RawBar, Symbol},
    direction::Direction,
    fake_bi::{FakeBI, create_fake_bis},
    fx::FX,
};
use crate::utils::{corr::LinearRegression, rounded::RoundToNthDigit};
use chrono::{DateTime, Utc};
use derive_builder::Builder;
#[cfg(feature = "python")]
use parking_lot::RwLock;
use std::sync::Arc;

#[cfg(feature = "python")]
use crate::utils::common::{create_naive_pandas_timestamp, create_ordered_dict};
#[cfg(feature = "python")]
use pyo3::basic::CompareOp;
#[cfg(feature = "python")]
use pyo3::types::{PyDict, PyDictMethods};
#[cfg(feature = "python")]
use pyo3::{Py, PyAny, PyResult, Python};
#[cfg(feature = "python")]
use pyo3::{pyclass, pymethods};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

/// 笔
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(Debug, Clone, Builder)]
#[builder(setter(into))]
pub struct BI {
    pub symbol: Symbol,
    /// 笔开始的分型
    pub fx_a: FX,
    /// 笔结束的分型
    pub fx_b: FX,
    /// 笔内部的分型列表
    pub fxs: Vec<FX>,
    pub direction: Direction,
    pub bars: Vec<NewBar>,
    #[cfg(feature = "python")]
    #[builder(default = "Arc::new(RwLock::new(None))")]
    pub cache: Arc<RwLock<Option<Py<PyDict>>>>,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl BI {
    #[new]
    fn new(
        symbol: String,
        direction: Direction,
        fx_a: FX,
        fx_b: FX,
        fxs: Vec<FX>,
        bars: Vec<NewBar>,
    ) -> Self {
        BI {
            symbol: symbol.into(),
            direction,
            fx_a,
            fx_b,
            fxs: fxs.into_iter().collect(),
            bars: bars.into_iter().collect(),
            cache: Arc::new(RwLock::new(None)),
        }
    }

    #[getter]
    fn symbol(&self) -> String {
        self.symbol.to_string()
    }

    #[getter]
    fn direction(&self) -> Direction {
        self.direction
    }

    #[getter]
    fn high(&self) -> f64 {
        self.get_high()
    }

    #[getter]
    fn low(&self) -> f64 {
        self.get_low()
    }
    #[getter]
    fn get_cache<'py>(&'py self, py: Python<'py>) -> Py<PyDict> {
        // 首先尝试读锁获取缓存
        {
            let cache_read = self.cache.read();
            if let Some(ref cached_dict) = *cache_read {
                return cached_dict.clone_ref(py);
            }
        }

        // 如果缓存为空，使用写锁初始化并填充所有属性
        let mut cache_write = self.cache.write();
        if cache_write.is_none() {
            let dict = PyDict::new(py);
            // 一次性填充所有属性，避免重复创建
            dict.set_item("symbol", self.symbol.as_ref()).unwrap();
            dict.set_item("direction", self.direction).unwrap();
            dict.set_item("high", self.get_high()).unwrap();
            dict.set_item("low", self.get_low()).unwrap();
            dict.set_item("fx_a", py.None()).unwrap(); // 复杂对象先设为None
            dict.set_item("fx_b", py.None()).unwrap(); // 复杂对象先设为None
            dict.set_item("bars", py.None()).unwrap(); // 复杂对象先设为None
            *cache_write = Some(dict.unbind());
        }
        cache_write.as_ref().unwrap().clone_ref(py)
    }

    #[setter]
    #[gen_stub(skip)] // 跳过为了防止和 get_cache重复
    fn set_cache(&self, dict: Py<PyDict>) {
        let mut cache_write = self.cache.write();
        *cache_write = Some(dict);
    }

    /// 直接支持 __dict__ 属性，让 pandas DataFrame() 能正确识别对象
    #[getter]
    pub fn __dict__(&self, py: Python) -> PyResult<Py<PyAny>> {
        // 直接返回缓存的字典，避免重复创建
        Ok(self.get_cache(py).into())
    }

    #[getter]
    fn sdt(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_naive_pandas_timestamp(py, self.start_dt())
    }

    #[getter]
    fn edt(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_naive_pandas_timestamp(py, self.end_dt())
    }

    #[getter]
    fn fx_a(&self) -> FX {
        self.fx_a.clone()
    }

    #[getter]
    fn fx_b(&self) -> FX {
        self.fx_b.clone()
    }

    #[getter]
    fn fxs(&self) -> Vec<FX> {
        self.fxs.to_vec()
    }

    /// 获取构成笔的NewBar列表
    #[getter]
    fn bars(&self) -> Vec<NewBar> {
        self.bars.to_vec()
    }

    /// 价差力度
    #[getter]
    fn power(&self) -> f64 {
        self.get_power()
    }

    /// 价差力度（别名）
    #[getter]
    fn power_price(&self) -> f64 {
        self.get_power_price()
    }

    /// 成交量力度
    #[getter]
    fn power_volume(&self) -> f64 {
        self.get_power_volume()
    }

    /// SNR 度量力度
    #[getter]
    fn power_snr(&self) -> f64 {
        self.get_power_snr()
    }

    /// 笔的涨跌幅
    #[getter]
    fn change(&self) -> f64 {
        self.get_change()
    }

    /// 笔内部的信噪比
    #[allow(non_snake_case)]
    #[getter]
    fn SNR(&self) -> f64 {
        self.get_snr()
    }

    /// 笔内部高低点之间的斜率
    #[getter]
    fn slope(&self) -> f64 {
        self.get_slope()
    }

    /// 笔内部价格的加速度
    #[getter]
    fn acceleration(&self) -> f64 {
        self.get_acceleration()
    }

    /// 笔的无包含关系K线数量
    #[getter]
    fn length(&self) -> usize {
        self.get_length()
    }

    /// 笔的原始K线close单变量线性回归拟合优度
    #[getter]
    fn rsq(&self) -> f64 {
        self.get_rsq()
    }

    /// 笔的斜边长度
    #[getter]
    fn hypotenuse(&self) -> f64 {
        self.get_hypotenuse()
    }

    /// 笔的斜边与竖直方向的夹角，角度越大，力度越大
    #[getter]
    fn angle(&self) -> f64 {
        self.get_angle()
    }

    /// 构成笔的原始K线序列，不包含首尾分型的首根K线
    #[getter]
    fn raw_bars(&self) -> Vec<RawBar> {
        self.get_raw_bars().into_iter().collect()
    }

    /// 笔的内部分型连接得到近似次级别笔列表
    #[getter]
    fn fake_bis(&self) -> Vec<FakeBI> {
        self.create_fake_bis().into_iter().collect()
    }

    /// 缓存字典（与 czsc 库兼容）
    #[getter]
    fn cache(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_ordered_dict(py)
    }

    /// 获取缓存值，如果不存在则返回默认值（与 czsc 库兼容）
    fn get_cache_with_default(&self, _key: &str, default_value: f64) -> f64 {
        default_value // 暂时返回默认值，因为我们的缓存是空的
    }

    /// 获取线性价格（与 czsc 库兼容）
    fn get_price_linear(&self, n: usize) -> f64 {
        // 简单实现：基于笔的高低点进行线性插值
        if n == 0 {
            if matches!(self.direction, Direction::Up) {
                self.low()
            } else {
                self.high()
            }
        } else if matches!(self.direction, Direction::Up) {
            self.high()
        } else {
            self.low()
        }
    }

    fn __repr__(&self) -> String {
        format!(
            "BI(symbol={}, sdt={}, edt={}, direction={:?}, high={}, low={})",
            self.symbol,
            self.start_dt().format("%Y-%m-%d %H:%M:%S"),
            self.end_dt().format("%Y-%m-%d %H:%M:%S"),
            self.direction,
            self.high(),
            self.low()
        )
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == other),
            CompareOp::Ne => Ok(self != other),
            _ => Ok(false),
        }
    }
}

impl PartialEq for BI {
    fn eq(&self, other: &Self) -> bool {
        self.symbol == other.symbol
            && self.fx_a == other.fx_a
            && self.fx_b == other.fx_b
            && self.fxs == other.fxs
            && self.direction == other.direction
            && self.bars == other.bars
    }
}

impl BI {
    pub fn start_dt(&self) -> DateTime<Utc> {
        self.fx_a.dt
    }

    pub fn end_dt(&self) -> DateTime<Utc> {
        self.fx_b.dt
    }

    /// 笔的内部分型连接得到近似次级别笔列表
    pub fn create_fake_bis(&self) -> Vec<FakeBI> {
        create_fake_bis(&self.fxs)
    }

    pub fn get_high(&self) -> f64 {
        self.fx_a.high.max(self.fx_b.high)
    }

    pub fn get_low(&self) -> f64 {
        self.fx_a.low.min(self.fx_b.low)
    }

    /// 价差力度
    pub fn get_power_price(&self) -> f64 {
        // 保留2位小数
        (self.fx_b.fx - self.fx_a.fx).abs().round_to_2_digit()
    }

    /// 价差力度
    pub fn get_power(&self) -> f64 {
        self.get_power_price()
    }

    /// 成交量力度
    pub fn get_power_volume(&self) -> f64 {
        if self.bars.len() <= 2 {
            return 0.0;
        }
        // sum([x.vol for x in self.bars[1:-1]])
        self.bars[1..self.bars.len() - 1]
            .iter()
            .map(|x| x.vol)
            .sum()
    }

    /// SNR 度量力度
    /// SNR越大，说明内部走势越顺畅，力度也就越大
    pub fn get_power_snr(&self) -> f64 {
        // return round(self.SNR, 4)
        (self.get_snr() * 10000.0).round() / 10000.0
    }

    /// 笔的涨跌幅
    pub fn get_change(&self) -> f64 {
        // 防止除以0
        if self.fx_a.fx == 0.0 {
            return 0.0;
        }
        // (结束分型 - 开始分型) / 开始分型，保留4位小数
        ((self.fx_b.fx - self.fx_a.fx) / self.fx_a.fx).round_to_4_digit()
    }

    /// 笔内部的信噪比
    pub fn get_snr(&self) -> f64 {
        let raw_bars = self.get_raw_bars();
        let n = raw_bars.len();

        match n {
            0 => 0.0,
            1 => {
                let bar = &raw_bars[0];
                (bar.close - bar.open).abs()
            }
            _ => {
                // 首尾变化的绝对值 - 按照Python版本逻辑
                let total_change = (raw_bars[n - 1].close - raw_bars[0].open).abs();
                // 每根K线开收价差的绝对值之和
                let diff_abs_change = raw_bars
                    .iter()
                    .fold(0.0, |sum, bar| sum + (bar.close - bar.open).abs());

                if diff_abs_change == 0.0 {
                    0.0
                } else {
                    total_change / diff_abs_change
                }
            }
        }
    }

    /// 笔内部高低点之间的斜率
    pub fn get_slope(&self) -> f64 {
        let raw_bars = self.get_raw_bars();
        let closes: Vec<f64> = raw_bars.iter().map(|bar| bar.close).collect();

        if closes.len() < 2 {
            return 0.0;
        }

        let n = closes.len() as f64;
        let x_mean = (n - 1.0) / 2.0;
        let y_mean = closes.iter().sum::<f64>() / n;

        let numerator: f64 = closes
            .iter()
            .enumerate()
            .map(|(i, y)| {
                let x = i as f64;
                (x - x_mean) * (y - y_mean)
            })
            .sum();

        let denominator: f64 = (0..closes.len())
            .map(|i| {
                let x = i as f64;
                (x - x_mean).powi(2)
            })
            .sum();

        if denominator == 0.0 {
            0.0
        } else {
            numerator / denominator
        }
    }

    /// 笔内部价格的加速度
    ///
    /// 负号表示开口向下；正号表示开口向上。数值越大，表示加速度越大。
    pub fn get_acceleration(&self) -> f64 {
        let raw_bars = self.get_raw_bars();
        let closes: Vec<f64> = raw_bars.iter().map(|bar| bar.close).collect();

        if closes.len() < 3 {
            return 0.0;
        }

        // 使用与Python numpy.polyfit(degree=2)兼容的二次多项式拟合
        // 返回二次项系数 (a in ax² + bx + c)
        self.numpy_compatible_quadratic_fit(&closes)
    }

    /// numpy兼容的二次多项式拟合
    /// 返回二次项系数，与Python的numpy.polyfit(range(len(c)), c, 2)[0]保持一致
    fn numpy_compatible_quadratic_fit(&self, y_values: &[f64]) -> f64 {
        let n = y_values.len() as f64;

        // 构建设计矩阵 X 和目标向量 y
        // 对于二次拟合: y = a*x² + b*x + c
        // 矩阵形式: [x²  x  1] * [a; b; c] = y

        let mut sum_x4 = 0.0;
        let mut sum_x3 = 0.0;
        let mut sum_x2 = 0.0;
        let mut sum_x = 0.0;
        let sum_1 = n;
        let mut sum_x2_y = 0.0;
        let mut sum_x_y = 0.0;
        let mut sum_y = 0.0;

        for (i, &y) in y_values.iter().enumerate() {
            let x = i as f64;
            let x2 = x * x;
            let x3 = x2 * x;
            let x4 = x3 * x;

            sum_x4 += x4;
            sum_x3 += x3;
            sum_x2 += x2;
            sum_x += x;
            sum_x2_y += x2 * y;
            sum_x_y += x * y;
            sum_y += y;
        }

        // 正规方程组:
        // [sum_x4  sum_x3  sum_x2] [a]   [sum_x2_y]
        // [sum_x3  sum_x2  sum_x ] [b] = [sum_x_y ]
        // [sum_x2  sum_x   sum_1 ] [c]   [sum_y   ]

        // 使用克莱默法则求解 a (二次项系数)
        let det = sum_x4 * (sum_x2 * sum_1 - sum_x * sum_x)
            - sum_x3 * (sum_x3 * sum_1 - sum_x * sum_x2)
            + sum_x2 * (sum_x3 * sum_x - sum_x2 * sum_x2);

        if det.abs() < 1e-10 {
            return 0.0;
        }

        let det_a = sum_x2_y * (sum_x2 * sum_1 - sum_x * sum_x)
            - sum_x_y * (sum_x3 * sum_1 - sum_x * sum_x2)
            + sum_y * (sum_x3 * sum_x - sum_x2 * sum_x2);

        det_a / det
    }

    /// 笔的无包含关系K线数量
    pub fn get_length(&self) -> usize {
        self.bars.len()
    }

    /// 笔的原始K线close单变量线性回归 拟合优度
    pub fn get_rsq(&self) -> f64 {
        let raw_bars = self.get_raw_bars();
        let closes: Vec<f64> = raw_bars.iter().map(|bar| bar.close).collect();

        if closes.is_empty() {
            return 0.0;
        }

        let res = closes.single_linear();
        // 保留4位小数
        (res.r2 * 10000.0).round() / 10000.0
    }

    /// 构成笔的原始K线序列，不包含首尾分型的首根K线
    pub fn get_raw_bars(&self) -> Vec<RawBar> {
        if self.bars.len() > 2 {
            let capacity = self.bars[1..self.bars.len() - 1]
                .iter()
                .map(|bar| bar.elements.len())
                .sum();

            let mut value = Vec::with_capacity(capacity);
            for bar in &self.bars[1..self.bars.len() - 1] {
                value.extend_from_slice(&bar.elements);
            }
            value
        } else {
            Vec::new()
        }
    }

    /// 笔的斜边长度
    pub fn get_hypotenuse(&self) -> f64 {
        (self.get_power_price().powi(2) + (self.get_raw_bars().len() as f64).powi(2)).sqrt()
    }

    /// 笔的斜边与竖直方向的夹角，角度越大，力度越大
    pub fn get_angle(&self) -> f64 {
        let angle_rad = (self.get_power_price() / self.get_hypotenuse()).asin();
        let angle_deg = angle_rad * 180.0 / std::f64::consts::PI;
        (angle_deg * 100.0).round() / 100.0
    }
}

pub fn print_bi(bis: &Vec<BI>) {
    println!(
        "{:<10} {:<12} {:<12} {:>6} {:<8}",
        "Direction", "FX_A (Mark)", "FX_B (Mark)", "FXs", "Bars"
    );

    println!("{:-<10} {:-<12} {:-<12} {:-<6} {:-<8}", "", "", "", "", "");

    // 数据行
    for bi in bis {
        let dir_icon = match bi.direction {
            Direction::Up => "↑",
            Direction::Down => "↓",
        };

        println!(
            "{:<10} {:<12} {:<12} {:>6} {:>4} bars",
            dir_icon,
            bi.fx_a.mark,
            bi.fx_b.mark,
            bi.fxs.len(),
            bi.bars.len()
        );
    }
}

#[cfg(test)]
pub mod tests {
    use super::*;
    use crate::objects::fx::tests::create_d_fx;
    use std::sync::Arc;

    /// 创建一个测试用的笔
    pub fn create_bi() -> BI {
        let fx_a = create_d_fx();
        let fx_b = create_d_fx();

        BIBuilder::default()
            .symbol(Arc::from("TEST".to_string()))
            .fx_a(fx_a.clone())
            .fx_b(fx_b.clone())
            .fxs(vec![fx_a.clone(), fx_b])
            .direction(Direction::Up)
            .bars(fx_a.elements)
            .build()
            .unwrap()
    }

    #[test]
    fn test_new_bi() {
        create_bi();
    }
}
