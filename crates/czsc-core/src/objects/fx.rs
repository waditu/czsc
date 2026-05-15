#[cfg(feature = "python")]
use crate::objects::bar::RawBar;
#[cfg(feature = "python")]
use parking_lot::RwLock;
use std::sync::Arc;

use super::{
    bar::{NewBar, Symbol},
    mark::Mark,
};
use chrono::{DateTime, Utc};
use derive_builder::Builder;

#[cfg(feature = "python")]
use crate::utils::common::{create_naive_pandas_timestamp, parse_python_datetime};
#[cfg(feature = "python")]
use pyo3::basic::CompareOp;
#[cfg(feature = "python")]
use pyo3::types::{PyDict, PyDictMethods};
#[cfg(feature = "python")]
use pyo3::{Bound, Python, pyclass, pymethods};
#[cfg(feature = "python")]
use pyo3::{Py, PyAny, PyResult};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

const POWER_STRONG: &str = "强";
const POWER_MEDIUM: &str = "中";
const POWER_WEAK: &str = "弱";

/// 分型
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(Debug, Clone, Builder)]
#[builder(setter(into))]
pub struct FX {
    pub symbol: Symbol,
    pub dt: DateTime<Utc>,
    pub mark: Mark,
    pub high: f64,
    pub low: f64,
    pub fx: f64,
    #[builder(default = "Vec::new()")]
    pub elements: Vec<NewBar>,
    #[cfg(feature = "python")]
    #[builder(default = "Arc::new(RwLock::new(None))")]
    pub cache: Arc<RwLock<Option<Py<PyDict>>>>,
}

impl FX {
    fn _power_str(&self) -> &str {
        assert_eq!(self.elements.len(), 3);

        let k1 = &self.elements[0];
        let k2 = &self.elements[1];
        let k3 = &self.elements[2];

        match self.mark {
            Mark::D => {
                if k3.close > k1.high {
                    POWER_STRONG
                } else if k3.close > k2.high {
                    POWER_MEDIUM
                } else {
                    POWER_WEAK
                }
            }
            Mark::G => {
                if k3.close < k1.low {
                    POWER_STRONG
                } else if k3.close < k2.low {
                    POWER_MEDIUM
                } else {
                    POWER_WEAK
                }
            }
        }
    }

    fn _power_volume(&self) -> f64 {
        assert_eq!(self.elements.len(), 3);
        self.elements.iter().map(|x| x.vol).sum()
    }

    fn _has_zs(&self) -> bool {
        assert_eq!(self.elements.len(), 3);

        let zd = self
            .elements
            .iter()
            .map(|x| x.low)
            .fold(f64::NEG_INFINITY, f64::max);
        let zg = self
            .elements
            .iter()
            .map(|x| x.high)
            .fold(f64::INFINITY, f64::min);

        zg >= zd
    }
}

impl FX {
    /// 判断分型强度
    pub fn power_str(&self) -> &str {
        self._power_str()
    }

    /// 计算成交量力度
    pub fn power_volume(&self) -> f64 {
        self._power_volume()
    }

    /// 判断构成分型的三根无包含K线是否有重叠中枢
    pub fn has_zs(&self) -> bool {
        self._has_zs()
    }
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl FX {
    #[new]
    fn new(
        symbol: String,
        dt: &Bound<PyAny>,
        mark: Mark,
        high: f64,
        low: f64,
        fx: f64,
        elements: Vec<NewBar>,
    ) -> PyResult<Self> {
        // 使用通用的日期时间解析函数
        let datetime_utc = parse_python_datetime(dt)?;

        Ok(FX {
            symbol: symbol.into(),
            dt: datetime_utc,
            mark,
            high,
            low,
            fx,
            elements: elements.into_iter().collect(),
            cache: Arc::new(RwLock::new(None)),
        })
    }

    #[getter]
    fn symbol(&self) -> String {
        self.symbol.to_string()
    }

    #[getter]
    fn dt(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_naive_pandas_timestamp(py, self.dt)
    }

    #[getter]
    fn mark(&self) -> Mark {
        self.mark.clone()
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
    fn fx(&self) -> f64 {
        self.fx
    }

    /// 获取构成分型的NewBar列表
    #[getter]
    fn new_bars(&self) -> Vec<NewBar> {
        self.elements.to_vec()
    }

    /// 获取原始K线列表（从NewBar的elements中提取）
    #[getter]
    fn raw_bars(&self) -> Vec<RawBar> {
        self.elements
            .iter()
            .flat_map(|new_bar| new_bar.elements.clone())
            .collect()
    }

    /// 获取分型强度字符串
    #[getter(power_str)]
    fn power_str_py(&self) -> String {
        self._power_str().to_string()
    }

    /// 获取成交量力度
    #[getter(power_volume)]
    fn power_volume_py(&self) -> f64 {
        self._power_volume()
    }

    /// 判断是否有重叠中枢
    #[getter(has_zs)]
    fn has_zs_py(&self) -> bool {
        self._has_zs()
    }

    /// 获取构成分型的NewBar列表（与new_bars相同，为兼容czsc库）
    #[getter]
    fn elements(&self) -> Vec<NewBar> {
        self.new_bars()
    }

    /// 缓存字典（与 czsc 库兼容）
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
            dict.set_item("dt", create_naive_pandas_timestamp(py, self.dt).unwrap())
                .unwrap();
            dict.set_item("mark", self.mark.clone()).unwrap();
            dict.set_item("high", self.high).unwrap();
            dict.set_item("low", self.low).unwrap();
            dict.set_item("fx", self.fx).unwrap();
            dict.set_item("elements", py.None()).unwrap(); // 复杂对象先设为None
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

    fn __repr__(&self) -> String {
        format!(
            "FX(symbol={}, dt={}, mark={:?}, fx={})",
            self.symbol,
            self.dt.format("%Y-%m-%d %H:%M:%S"),
            self.mark,
            self.fx
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

impl PartialEq for FX {
    fn eq(&self, other: &Self) -> bool {
        self.symbol == other.symbol
            && self.dt == other.dt
            && self.mark == other.mark
            && self.high == other.high
            && self.low == other.low
            && self.fx == other.fx
            && self.elements == other.elements
    }
}

pub fn print_fx_list(fxs: &[FX]) {
    println!("{:<12} {:>12} {:>12} {:>12}", "Mark", "High", "Low", "FX");
    println!("{:-<12} {:-^12} {:-^12} {:-^12}", "", "", "", "");

    for fx in fxs {
        println!(
            "{:<12} {:>12.4} {:>12.4} {:>12.4}",
            fx.mark, fx.high, fx.low, fx.fx
        );
    }
}

#[cfg(test)]
pub mod tests {
    use std::sync::Arc;

    use chrono::Utc;

    use crate::objects::bar::NewBarBuilder;

    use super::*;

    #[test]
    fn test_fx_new() {
        let fx1 = FXBuilder::default()
            .symbol(Arc::from("TEST".to_string()))
            .dt(Utc::now())
            .mark(Mark::D)
            .high(0)
            .low(0)
            .fx(0)
            .build()
            .unwrap();
        assert_eq!(fx1.high, 0.0);
    }

    /// 创建一个测试用的底分型
    pub fn create_d_fx() -> FX {
        // 创建测试用的K线数据
        let k1 = NewBarBuilder::default()
            .symbol(Arc::from("TEST".to_string()))
            .dt(Utc::now())
            .id(1)
            .open(8.5)
            .high(9.0)
            .low(8.0)
            .close(8.2)
            .vol(90.0)
            .amount(900.0)
            .build()
            .unwrap();

        let k2 = NewBarBuilder::default()
            .symbol(Arc::from("TEST".to_string()))
            .dt(Utc::now())
            .id(2)
            .open(8)
            .high(8.5)
            .low(7.5)
            .close(8.0)
            .vol(100.0)
            .amount(1000.0)
            .build()
            .unwrap();

        let k3 = NewBarBuilder::default()
            .symbol(Arc::from("TEST".to_string()))
            .dt(Utc::now())
            .id(3)
            .open(8.5)
            .high(9.0)
            .low(8.0)
            .close(8.8)
            .vol(110.0)
            .amount(1100.0)
            .build()
            .unwrap();

        FXBuilder::default()
            .symbol(k1.symbol.clone())
            .dt(k2.dt)
            .mark(Mark::D)
            .high(k2.high)
            .low(k2.low)
            .fx(k2.low)
            .elements(vec![k1.clone(), k2.clone(), k3.clone()])
            .build()
            .unwrap()
    }

    #[test]
    fn test_power_str() {
        let fx_d = create_d_fx();
        assert_eq!(fx_d.power_str(), POWER_MEDIUM);
    }

    #[test]
    fn test_power_volume() {
        let fx_d = create_d_fx();
        assert_eq!(fx_d.power_volume(), 300.0);
    }

    #[test]
    fn test_has_zs() {
        let fx_d = create_d_fx();
        assert!(fx_d.has_zs());
    }
}
