use super::{bi::BI, direction::Direction};
#[cfg(feature = "python")]
use crate::utils::common::create_naive_pandas_timestamp;
use chrono::{DateTime, Utc};
use core::f64;
use derive_builder::Builder;
#[cfg(feature = "python")]
use parking_lot::RwLock;
#[cfg(feature = "python")]
use pyo3::types::{PyDict, PyDictMethods};
#[cfg(feature = "python")]
use pyo3::{Py, PyAny, PyResult, Python, pyclass, pymethods};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};
use std::sync::Arc;

#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(Debug, Clone, Builder)]
pub struct ZS {
    pub bis: Vec<BI>,
    /// 中枢开始时间
    pub sdt: DateTime<Utc>,
    /// 中枢结束时间
    pub edt: DateTime<Utc>,
    /// 中枢第一笔方向，sdir 是 start direction 的缩写
    pub sdir: Direction,
    /// 中枢倒一笔方向，edir 是 end direction 的缩写
    pub edir: Direction,
    /// 中枢上沿
    pub zg: f64,
    /// 中枢下沿
    pub zd: f64,
    /// 中枢中轴
    pub zz: f64,
    /// 中枢最高点
    pub gg: f64,
    /// 中枢最低点
    pub dd: f64,
    #[cfg(feature = "python")]
    #[builder(default = "Arc::new(RwLock::new(None))")]
    pub cache: Arc<RwLock<Option<Py<PyDict>>>>,
}

impl ZS {
    pub fn new(bis: Vec<BI>) -> Self {
        let sdt = bis.first().unwrap().start_dt();
        let edt = bis.last().unwrap().end_dt();
        let sdir = bis.first().unwrap().direction;
        let edir = bis.last().unwrap().direction;
        let zg = bis
            .iter()
            .take(3)
            .map(|x| x.get_high())
            .fold(f64::INFINITY, f64::min);
        let zd = bis
            .iter()
            .take(3)
            .map(|x| x.get_low())
            .fold(f64::NEG_INFINITY, f64::max);
        let gg = bis
            .iter()
            .map(|x| x.get_high())
            .fold(f64::NEG_INFINITY, f64::max);
        let dd = bis
            .iter()
            .map(|x| x.get_low())
            .fold(f64::INFINITY, f64::min);

        let zz = zd + (zg - zd) * 0.5;

        ZS {
            bis,
            sdt,
            edt,
            sdir,
            edir,
            zg,
            zd,
            zz,
            gg,
            dd,
            #[cfg(feature = "python")]
            cache: Arc::new(RwLock::new(None)),
        }
    }

    /// 中枢是否有效
    pub fn is_valid(&self) -> bool {
        let zg = self.zg;
        let zd = self.zd;
        if zg < zd {
            return false;
        }

        self.bis.iter().all(|bi| {
            // 情况1: 笔的高点在中枢区间内
            let high_in_range = (bi.get_high() <= zg) && (bi.get_high() >= zd);
            // 情况2: 笔的低点在中枢区间内
            let low_in_range = (bi.get_low() <= zg) && (bi.get_low() >= zd);
            // 情况3: 笔完全包含中枢区间
            let contains_range = (bi.get_high() >= zg) && (bi.get_low() <= zd);
            high_in_range || low_in_range || contains_range
        })
    }
}
#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl ZS {
    #[new]
    fn new_py(bis: Vec<BI>) -> Self {
        Self::new(bis)
    }

    /// 获取构成中枢的笔列表
    #[getter]
    fn bis(&self) -> Vec<BI> {
        self.bis.clone()
    }

    /// 中枢开始时间
    #[getter]
    fn sdt(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_naive_pandas_timestamp(py, self.sdt)
    }

    /// 中枢结束时间
    #[getter]
    fn edt(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_naive_pandas_timestamp(py, self.edt)
    }

    /// 中枢第一笔方向
    #[getter]
    fn sdir(&self) -> Direction {
        self.sdir
    }

    /// 中枢倒一笔方向
    #[getter]
    fn edir(&self) -> Direction {
        self.edir
    }

    /// 中枢上沿
    #[getter]
    fn zg(&self) -> f64 {
        self.zg
    }

    /// 中枢下沿
    #[getter]
    fn zd(&self) -> f64 {
        self.zd
    }

    /// 中枢中轴
    #[getter]
    fn zz(&self) -> f64 {
        self.zz
    }

    /// 中枢最高点
    #[getter]
    fn gg(&self) -> f64 {
        self.gg
    }

    /// 中枢最低点
    #[getter]
    fn dd(&self) -> f64 {
        self.dd
    }

    /// 中枢是否有效
    #[pyo3(name = "is_valid")]
    fn is_valid_py(&self) -> bool {
        self.is_valid()
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
            dict.set_item("sdt", create_naive_pandas_timestamp(py, self.sdt).unwrap())
                .unwrap();
            dict.set_item("edt", create_naive_pandas_timestamp(py, self.edt).unwrap())
                .unwrap();
            dict.set_item("sdir", self.sdir).unwrap();
            dict.set_item("edir", self.edir).unwrap();
            dict.set_item("zg", self.zg).unwrap();
            dict.set_item("zd", self.zd).unwrap();
            dict.set_item("zz", self.zz).unwrap();
            dict.set_item("gg", self.gg).unwrap();
            dict.set_item("dd", self.dd).unwrap();
            dict.set_item("bis", py.None()).unwrap(); // 复杂对象先设为None
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
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::objects::bi::tests::create_bi;

    #[test]
    fn test_new_zs() {
        let bi1 = create_bi();

        let zs1 = ZS::new(vec![bi1.clone(), bi1.clone(), bi1]);

        println!("{:?}", zs1.sdt);
    }
}
