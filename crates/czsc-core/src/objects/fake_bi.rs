use super::{bar::Symbol, direction::Direction, fx::FX};
#[cfg(feature = "python")]
use crate::utils::common::create_naive_pandas_timestamp;
use crate::{objects::mark::Mark, utils::rounded::RoundToNthDigit};
use chrono::{DateTime, Utc};
use derive_builder::Builder;
#[cfg(feature = "python")]
use parking_lot::Mutex;
#[cfg(feature = "python")]
use pyo3::types::{PyDict, PyDictMethods};
#[cfg(feature = "python")]
use pyo3::{Py, PyAny, PyResult, Python};
#[cfg(feature = "python")]
use pyo3::{pyclass, pymethods};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};
use std::sync::Arc;

/// 虚拟笔
/// 主要为笔的内部分析提供便利
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(Debug, Clone, Builder)]
#[builder(setter(into))]
pub struct FakeBI {
    pub symbol: Symbol,
    pub sdt: DateTime<Utc>,
    pub edt: DateTime<Utc>,
    pub direction: Direction,
    pub high: f64,
    pub low: f64,
    pub power: f64,
    #[cfg(feature = "python")]
    #[builder(default = "Arc::new(Mutex::new(None))")]
    pub cache: Arc<Mutex<Option<Py<PyDict>>>>,
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl FakeBI {
    #[getter]
    fn symbol(&self) -> String {
        self.symbol.to_string()
    }

    #[getter]
    fn sdt(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_naive_pandas_timestamp(py, self.sdt)
    }

    #[getter]
    fn edt(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_naive_pandas_timestamp(py, self.edt)
    }

    #[getter]
    fn direction(&self) -> Direction {
        self.direction
    }

    #[getter]
    fn high(&self) -> f64 {
        self.high
    }

    #[getter]
    fn low(&self) -> f64 {
        self.low
    }

    #[getter]
    fn power(&self) -> f64 {
        self.power
    }
    #[getter]
    fn get_cache<'py>(&'py mut self, py: Python<'py>) -> Py<PyDict> {
        let mut cache = self.cache.lock();
        if cache.is_none() {
            let dict = PyDict::new(py);
            // 一次性填充所有属性，避免重复创建
            dict.set_item("symbol", self.symbol.as_ref()).unwrap();
            dict.set_item("sdt", create_naive_pandas_timestamp(py, self.sdt).unwrap())
                .unwrap();
            dict.set_item("edt", create_naive_pandas_timestamp(py, self.edt).unwrap())
                .unwrap();
            dict.set_item("direction", self.direction).unwrap();
            dict.set_item("high", self.high).unwrap();
            dict.set_item("low", self.low).unwrap();
            dict.set_item("power", self.power).unwrap();
            *cache = Some(dict.unbind());
        }
        cache.as_ref().unwrap().clone_ref(py)
    }

    #[setter]
    #[gen_stub(skip)] // 跳过为了防止和 get_cache重复
    fn set_cache(&self, dict: Py<PyDict>) {
        *self.cache.lock() = Some(dict);
    }

    fn __repr__(&self) -> String {
        format!(
            "FakeBI(symbol={}, sdt={}, edt={}, direction={:?}, high={}, low={}, power={})",
            self.symbol,
            self.sdt.format("%Y-%m-%d %H:%M:%S"),
            self.edt.format("%Y-%m-%d %H:%M:%S"),
            self.direction,
            self.high,
            self.low,
            self.power
        )
    }
}

/// 创建 fake_bis 列表
///
/// # 参数
///
/// * `fxs` - 分型序列，必须顶底分型交替
///
/// # 返回值
///
/// * 返回 FakeBI 的 Vec
pub fn create_fake_bis(fxs: &[FX]) -> Vec<FakeBI> {
    // 如果长度为奇数，移除最后一个元素
    let len = if !fxs.len().is_multiple_of(2) {
        fxs.len() - 1
    } else {
        fxs.len()
    };

    let mut fake_bis = Vec::new();
    for window in fxs[..len].windows(2) {
        let fx1 = &window[0];
        let fx2 = &window[1];
        assert!(fx1.mark != fx2.mark, "相邻分型标记必须不同");

        let fake_bi = match fx1.mark {
            Mark::D => FakeBIBuilder::default()
                .symbol(fx1.symbol.clone())
                .sdt(fx1.dt)
                .edt(fx2.dt)
                .direction(Direction::Up)
                .high(fx2.high)
                .low(fx1.low)
                // 保留2位小数
                .power((fx2.high - fx1.low).round_to_2_digit())
                .build()
                .unwrap(),
            Mark::G => FakeBIBuilder::default()
                .symbol(fx1.symbol.clone())
                .sdt(fx1.dt)
                .edt(fx2.dt)
                .direction(Direction::Down)
                .high(fx1.high)
                .low(fx2.low)
                .power((fx1.high - fx2.low).round_to_2_digit())
                .build()
                .unwrap(),
        };
        fake_bis.push(fake_bi);
    }
    fake_bis
}
