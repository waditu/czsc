use super::freq::Freq;
use chrono::{DateTime, Utc};
use derive_builder::Builder;
#[cfg(feature = "python")]
use parking_lot::RwLock;
#[cfg(feature = "python")]
use pyo3::types::PyDict;

use std::sync::Arc;

use crate::utils::common::freq_to_chinese_string;
#[cfg(feature = "python")]
use crate::utils::common::{create_naive_pandas_timestamp, parse_python_datetime};
#[cfg(feature = "python")]
use pyo3::IntoPyObject;
#[cfg(feature = "python")]
use pyo3::basic::CompareOp;
#[cfg(feature = "python")]
use pyo3::types::PyDictMethods;
#[cfg(feature = "python")]
use pyo3::{Bound, Py, PyAny, PyResult, Python, pyclass, pymethods};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

// 数据不会被修改，只需要共享一个只读视图
pub type Symbol = Arc<str>;

/// 原始K线元素
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(Debug, Clone, Builder, serde::Serialize, serde::Deserialize)]
#[builder(setter(into), pattern = "owned")]
pub struct RawBar {
    pub symbol: Symbol,
    pub dt: DateTime<Utc>,
    #[builder(default = "Freq::Tick")]
    pub freq: Freq,
    /// id 必须是升序
    pub id: i32,
    pub open: f64,
    pub close: f64,
    pub high: f64,
    pub low: f64,
    pub vol: f64,
    pub amount: f64,

    #[cfg(feature = "python")]
    #[serde(skip)]
    #[builder(default = "Arc::new(RwLock::new(None))")]
    pub cache: Arc<RwLock<Option<Py<PyDict>>>>,
}

impl RawBar {
    /// 上影
    pub fn upper(&self) -> f64 {
        self.high - self.open.max(self.close)
    }

    /// 下影
    pub fn lower(&self) -> f64 {
        self.open.min(self.close) - self.low
    }

    /// 实体
    pub fn solid(&self) -> f64 {
        (self.open - self.close).abs()
    }
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl RawBar {
    #[new]
    #[pyo3(signature = (symbol, dt, freq, open, close, high, low, vol, amount, id=0))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        _py: Python,
        symbol: &str,
        dt: &Bound<PyAny>,
        freq: Freq,
        open: f64,
        close: f64,
        high: f64,
        low: f64,
        vol: f64,
        amount: f64,
        id: i32,
    ) -> PyResult<Self> {
        // 使用通用的日期时间解析函数
        let datetime_utc = parse_python_datetime(dt)?;

        Ok(RawBar {
            symbol: symbol.into(),
            dt: datetime_utc,
            freq,
            id,
            open,
            close,
            high,
            low,
            vol,
            amount,
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
    fn freq(&self) -> Freq {
        self.freq
    }

    #[getter]
    fn id(&self) -> i32 {
        self.id
    }

    #[getter]
    fn open(&self) -> f64 {
        self.open
    }

    #[getter]
    fn close(&self) -> f64 {
        self.close
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
    fn vol(&self) -> f64 {
        self.vol
    }

    #[getter]
    fn amount(&self) -> f64 {
        self.amount
    }

    /// 实体部分（与原版CZSC兼容）
    #[getter(solid)]
    fn solid_py(&self) -> f64 {
        self.solid()
    }

    /// 上影线长度（与原版CZSC兼容）
    #[getter(upper)]
    fn upper_py(&self) -> f64 {
        self.upper()
    }

    /// 下影线长度（与原版CZSC兼容）
    #[getter(lower)]
    fn lower_py(&self) -> f64 {
        self.lower()
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
            dict.set_item("dt", create_naive_pandas_timestamp(py, self.dt).unwrap())
                .unwrap();
            dict.set_item("freq", freq_to_chinese_string(self.freq))
                .unwrap();
            dict.set_item("id", self.id).unwrap();
            dict.set_item("open", self.open).unwrap();
            dict.set_item("close", self.close).unwrap();
            dict.set_item("high", self.high).unwrap();
            dict.set_item("low", self.low).unwrap();
            dict.set_item("vol", self.vol).unwrap();
            dict.set_item("amount", self.amount).unwrap();
            dict.set_item("solid", self.solid()).unwrap();
            dict.set_item("upper", self.upper()).unwrap();
            dict.set_item("lower", self.lower()).unwrap();
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

    /// 让对象表现得像记录，pandas DataFrame构造器会调用这个
    fn _asdict(&self, py: Python) -> PyResult<Py<PyAny>> {
        self.__dict__(py)
    }

    /// 转换为字典，便于创建 pandas DataFrame
    fn to_dict(&self, py: Python) -> PyResult<Py<PyAny>> {
        self.__dict__(py)
    }

    /// 支持pickle序列化
    fn __reduce__(&self, py: Python) -> PyResult<Py<PyAny>> {
        // RawBar.new 接收 `freq: Freq`（PyO3 枚举），而不是字符串 ——
        // 通过 pickle 直接传递枚举，这样 unpickle 路径
        // （`RawBar(*args)`）才会成功。如果在这里用
        // `freq_to_chinese_string` 字符串化，会迫使构造函数同时
        // 接受 str|Freq，并悄悄地改动公共 API。
        let cls = py.get_type::<Self>();
        let args = (
            self.symbol.as_ref(),
            create_naive_pandas_timestamp(py, self.dt)?,
            self.freq,
            self.open,
            self.close,
            self.high,
            self.low,
            self.vol,
            self.amount,
            self.id,
        );
        Ok((
            cls.into_any().unbind(),
            args.into_pyobject(py)?.into_any().unbind(),
        )
            .into_pyobject(py)?
            .into_any()
            .unbind())
    }

    /// 支持深拷贝
    fn __deepcopy__(&self, _memo: &Bound<PyAny>) -> PyResult<Self> {
        Ok(self.clone())
    }

    fn __repr__(&self) -> String {
        format!(
            "RawBar(symbol={}, dt={}, freq={:?}, id={}, open={}, close={}, high={}, low={}, vol={}, amount={})",
            self.symbol,
            self.dt.format("%Y-%m-%d %H:%M:%S"),
            self.freq,
            self.id,
            self.open,
            self.close,
            self.high,
            self.low,
            self.vol,
            self.amount
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

impl PartialEq for RawBar {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
            && self.symbol == other.symbol
            && self.dt == other.dt
            && self.freq == other.freq
            && self.open == other.open
            && self.close == other.close
            && self.high == other.high
            && self.low == other.low
            && self.vol == other.vol
            && self.amount == other.amount
    }
}

/// 去除包含关系后的K线元素
#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(Debug, Clone, Builder, serde::Serialize, serde::Deserialize)]
#[builder(setter(into), pattern = "owned")]
pub struct NewBar {
    pub symbol: Symbol,
    pub dt: DateTime<Utc>,
    #[builder(default = "Freq::Tick")]
    pub freq: Freq,
    /// id 必须是升序
    pub id: i32,
    pub open: f64,
    pub close: f64,
    pub high: f64,
    pub low: f64,
    pub vol: f64,
    pub amount: f64,
    /// 存入具有包含关系的原始K线
    #[builder(default = "Vec::new()")]
    pub elements: Vec<RawBar>,

    #[cfg(feature = "python")]
    #[serde(skip)]
    #[builder(default = "Arc::new(RwLock::new(None))")]
    pub cache: Arc<RwLock<Option<Py<PyDict>>>>,
}

impl AsRef<NewBar> for NewBar {
    fn as_ref(&self) -> &NewBar {
        self
    }
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl NewBar {
    #[new]
    #[pyo3(signature = (symbol, dt, freq, open, close, high, low, vol, amount, id=0, elements=None))]
    #[allow(clippy::too_many_arguments)]
    fn new(
        _py: Python,
        symbol: &str,
        dt: &Bound<PyAny>,
        freq: Freq,
        open: f64,
        close: f64,
        high: f64,
        low: f64,
        vol: f64,
        amount: f64,
        id: i32,
        elements: Option<Vec<RawBar>>,
    ) -> PyResult<Self> {
        // 使用通用的日期时间解析函数
        let datetime_utc = parse_python_datetime(dt)?;

        Ok(NewBar {
            symbol: symbol.into(),
            dt: datetime_utc,
            freq,
            id,
            open,
            close,
            high,
            low,
            vol,
            amount,
            elements: elements.unwrap_or_default(),
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
    fn freq(&self) -> Freq {
        self.freq
    }

    #[getter]
    fn id(&self) -> i32 {
        self.id
    }

    #[getter]
    fn open(&self) -> f64 {
        self.open
    }

    #[getter]
    fn close(&self) -> f64 {
        self.close
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
    fn vol(&self) -> f64 {
        self.vol
    }

    #[getter]
    fn amount(&self) -> f64 {
        self.amount
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
            dict.set_item("dt", create_naive_pandas_timestamp(py, self.dt).unwrap())
                .unwrap();
            dict.set_item("freq", freq_to_chinese_string(self.freq))
                .unwrap();
            dict.set_item("id", self.id).unwrap();
            dict.set_item("open", self.open).unwrap();
            dict.set_item("close", self.close).unwrap();
            dict.set_item("high", self.high).unwrap();
            dict.set_item("low", self.low).unwrap();
            dict.set_item("vol", self.vol).unwrap();
            dict.set_item("amount", self.amount).unwrap();
            // 计算solid/upper/lower而不是调用方法
            dict.set_item("solid", (self.open - self.close).abs())
                .unwrap();
            dict.set_item("upper", self.high - self.open.max(self.close))
                .unwrap();
            dict.set_item("lower", self.open.min(self.close) - self.low)
                .unwrap();
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
    #[getter]
    fn elements(&self) -> Vec<RawBar> {
        self.elements.to_vec()
    }

    /// 获取构成NewBar的原始K线列表（与elements相同，为兼容czsc库）
    #[getter]
    fn raw_bars(&self) -> Vec<RawBar> {
        self.elements()
    }

    fn __repr__(&self) -> String {
        format!(
            "NewBar(symbol={}, dt={}, freq={:?}, id={}, open={}, close={}, high={}, low={}, vol={}, amount={})",
            self.symbol,
            self.dt.format("%Y-%m-%d %H:%M:%S"),
            self.freq,
            self.id,
            self.open,
            self.close,
            self.high,
            self.low,
            self.vol,
            self.amount
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

impl PartialEq for NewBar {
    fn eq(&self, other: &Self) -> bool {
        self.id == other.id
            && self.symbol == other.symbol
            && self.dt == other.dt
            && self.freq == other.freq
            && self.open == other.open
            && self.close == other.close
            && self.high == other.high
            && self.low == other.low
            && self.vol == other.vol
            && self.amount == other.amount
            && self.elements == other.elements
    }
}

impl NewBar {
    /// 创建新K线的辅助函数
    ///
    /// 出现error的可能性比较小
    pub fn new_from_raw(bar: &RawBar) -> Self {
        #[cfg(feature = "python")]
        {
            NewBarBuilder::default()
                .symbol(bar.symbol.clone())
                .id(bar.id)
                .freq(bar.freq)
                .dt(bar.dt)
                .open(bar.open)
                .close(bar.close)
                .high(bar.high)
                .low(bar.low)
                .vol(bar.vol)
                .amount(bar.amount)
                .elements(vec![bar.clone()])
                .cache(Arc::new(RwLock::new(None)))
                .build()
                .unwrap()
        }
        #[cfg(not(feature = "python"))]
        {
            NewBarBuilder::default()
                .symbol(bar.symbol.clone())
                .id(bar.id)
                .freq(bar.freq)
                .dt(bar.dt)
                .open(bar.open)
                .close(bar.close)
                .high(bar.high)
                .low(bar.low)
                .vol(bar.vol)
                .amount(bar.amount)
                .elements(vec![bar.clone()])
                .build()
                .unwrap()
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const TEST: &str = "test";

    #[test]
    fn test_raw_bar_new() {
        let bar = RawBarBuilder::default()
            .symbol(Arc::from(TEST))
            .dt(Utc::now())
            .id(0)
            .open(0)
            .close(0)
            .high(0)
            .low(0)
            .vol(0)
            .amount(0)
            .build()
            .unwrap();
        assert_eq!(bar.freq, Freq::Tick);
    }

    #[test]
    fn test_raw_bar_calculations() {
        // 测试上涨的情况
        let bar = RawBarBuilder::default()
            .symbol(Arc::from(TEST))
            .dt(Utc::now())
            .id(0)
            .open(10)
            .close(12)
            .high(15)
            .low(8)
            .vol(0)
            .amount(0)
            .build()
            .unwrap();

        // 15 - 12 = 3
        assert_eq!(bar.upper(), 3.0);
        // 10 - 8 = 2
        assert_eq!(bar.lower(), 2.0);
        // 10 - 12 = 2
        assert_eq!(bar.solid(), 2.0);

        // 测试下跌的情况
        let bar = RawBarBuilder::default()
            .symbol(Arc::from(TEST))
            .dt(Utc::now())
            .id(0)
            .open(12)
            .close(10)
            .high(15)
            .low(8)
            .vol(0)
            .amount(0)
            .build()
            .unwrap();

        // 15 - 12 = 3
        assert_eq!(bar.upper(), 3.0);
        // 10 - 8 = 2
        assert_eq!(bar.lower(), 2.0);

        // |12 - 10| = 2
        assert_eq!(bar.solid(), 2.0);
    }

    #[test]
    fn test_new_bar() {
        let bar = NewBarBuilder::default()
            .symbol(Arc::from(TEST))
            .dt(Utc::now())
            .id(0)
            .open(0)
            .close(0)
            .high(0)
            .low(0)
            .vol(0)
            .amount(0)
            .build()
            .unwrap();
        assert_eq!(bar.freq, Freq::Tick);
    }

    #[test]
    fn test_new_bar_with_elements() {
        let mut new_bar = NewBarBuilder::default()
            .symbol(Arc::from(TEST))
            .dt(Utc::now())
            .id(0)
            .open(0)
            .close(0)
            .high(0)
            .low(0)
            .vol(0)
            .amount(0)
            .build()
            .unwrap();

        let raw_bar1 = RawBarBuilder::default()
            .symbol(Arc::from(TEST))
            .id(1)
            .dt(Utc::now())
            .freq(Freq::Tick)
            .open(10)
            .close(12)
            .high(15)
            .low(8)
            .vol(100)
            .amount(1000)
            .build()
            .unwrap();

        new_bar.elements.push(raw_bar1.clone());
        assert_eq!(new_bar.elements.len(), 1);
        assert_eq!(new_bar.elements[0].id, 1);
    }
}
