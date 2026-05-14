use crate::{errors::UtilsError, freq_data::freq_end_time};
use anyhow::Context;
use chrono::{DateTime, Utc};
use czsc_core::czsc_bail;
use czsc_core::objects::{
    bar::{RawBar, RawBarBuilder, Symbol},
    freq::Freq,
    market::Market,
};
use parking_lot::{RwLock, RwLockWriteGuard};
use std::collections::{BTreeMap, VecDeque};

#[cfg(feature = "python")]
use pyo3::prelude::PyDictMethods;
#[cfg(feature = "python")]
use pyo3::types::{PyAnyMethods, PyDict, PyListMethods};
#[cfg(feature = "python")]
use pyo3::{IntoPyObject, PyResult, pyclass, pymethods};
#[cfg(feature = "python")]
use pyo3::{Py, PyAny, Python};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
pub struct BarGenerator {
    market: Market,
    /// 基准周期K线
    base_freq: Freq,
    /// 最大K线数量限制
    max_count: usize,
    /// 所有周期的K线数据，key是周期字符串，value是K线列表
    pub freq_bars: BTreeMap<Freq, RwLock<VecDeque<RawBar>>>,
}

impl Clone for BarGenerator {
    fn clone(&self) -> Self {
        let freq_bars = self
            .freq_bars
            .iter()
            .map(|(freq, bars_lock)| {
                let bars = bars_lock.read().clone();
                (*freq, RwLock::new(bars))
            })
            .collect();
        Self {
            market: self.market,
            base_freq: self.base_freq,
            max_count: self.max_count,
            freq_bars,
        }
    }
}

impl BarGenerator {
    pub fn new(
        base_freq: Freq,
        freqs: Vec<Freq>,
        max_count: usize,
        market: Market,
    ) -> Result<Self, UtilsError> {
        let bars = freqs
            .into_iter()
            .chain(std::iter::once(base_freq))
            .map(|f| (f, RwLock::new(VecDeque::with_capacity(max_count))))
            .collect();

        let bg = BarGenerator {
            market,
            base_freq,
            max_count,
            freq_bars: bars,
        };

        Ok(bg)
    }

    /// 初始化某个周期的K线序列
    ///
    /// # 函数计算逻辑
    ///
    /// 1. 检查输入的`freq`是否存在于`self.freq_bars`的键中。如果不存在，返回错误。
    /// 2. 检查`self.freq_bars[freq]`是否为空。如果不为空，返回错误，表示不允许重复初始化。
    /// 3. 如果以上检查都通过，将输入的`bars`存储到`self.freq_bars[freq]`中。
    /// 4. 从`bars`中获取最后一根K线的交易标的代码，更新`self.symbol`。
    ///
    /// # Arguments
    ///
    /// * `freq` - 周期名称
    /// * `bars` - K线序列
    ///
    /// # Returns
    ///
    /// * `Ok(())` - 初始化成功
    /// * `Err(String)` - 包含错误信息的字符串
    pub fn init_freq_with_bars<I>(&mut self, freq: Freq, bars: I) -> Result<(), UtilsError>
    where
        I: IntoIterator<Item = RawBar>,
    {
        if !self.freq_bars.contains_key(&freq) {
            czsc_bail!("周期 {} 不在self.bars", freq);
        }

        if let Some(existing_bars) = self.freq_bars.get(&freq)
            && !existing_bars.read().is_empty()
        {
            czsc_bail!("self.bars['{}'] 不为空，不允许执行初始化", freq);
        }

        let bars = bars
            .into_iter()
            .enumerate()
            .map(|(id, mut bar)| {
                bar.id = id as i32;
                bar
            })
            .collect();

        self.freq_bars.insert(freq, RwLock::new(bars));
        Ok(())
    }

    /// 更新指定周期K线
    ///
    /// # 函数计算逻辑
    ///
    /// 1. 计算目标周期的结束时间`freq_edt`
    /// 2. 检查`self.bars`中是否已经有目标周期的K线：
    ///    - 如果没有，创建一个新的`RawBar`对象并添加到`self.bars`中，然后返回
    /// 3. 如果已有K线，获取最后一根K线`last`
    /// 4. 检查`freq_edt`与最后一根K线的日期时间的关系：
    ///    - 如果不相等，创建新的`RawBar`对象并添加到序列末尾
    ///    - 如果相等，创建新的`RawBar`对象并更新最后一根K线，其中：
    ///      * 开盘价使用最后一根K线的开盘价
    ///      * 收盘价使用当前K线的收盘价
    ///      * 最高价取最后一根K线和当前K线的最高价的最大值
    ///      * 最低价取最后一根K线和当前K线的最低价的最小值
    ///      * 成交量和成交金额为两根K线的累加值
    ///
    /// # Arguments
    ///
    /// * `bar` - 基础周期已完成K线的引用
    /// * `freq` - 目标周期的引用
    ///
    fn update_freq(
        &self,
        bar: &RawBar,
        freq: Freq,
        mut bars: RwLockWriteGuard<'_, VecDeque<RawBar>>,
    ) -> Result<(), UtilsError> {
        // 1. 计算目标周期的结束时间
        let freq_edt = freq_end_time(bar.dt, freq, self.market)?;

        // 如果是第一根K线
        if bars.is_empty() {
            let new_bar = RawBarBuilder::default()
                .symbol(bar.symbol.clone())
                .id(0)
                .dt(freq_edt)
                .freq(freq)
                .open(bar.open)
                .close(bar.close)
                .high(bar.high)
                .low(bar.low)
                .vol(bar.vol)
                .amount(bar.amount)
                .build()
                .context("Failed to create the first rawbar")?;
            // 限制K线数量
            // 如果超出最大容量，先移除最旧的元素
            if bars.len() == self.max_count {
                bars.pop_front();
            }
            bars.push_back(new_bar);
            return Ok(());
        }

        // 3. 获取最后一根K线的引用
        let last = bars.back().unwrap();

        // 4. 创建新的K线
        let new_bar = if freq_edt != last.dt {
            // 如果时间不同，创建新的K线
            RawBarBuilder::default()
                .symbol(bar.symbol.clone())
                .id(last.id + 1)
                .dt(freq_edt)
                .freq(freq)
                .open(bar.open)
                .close(bar.close)
                .high(bar.high)
                .low(bar.low)
                .vol(bar.vol)
                .amount(bar.amount)
                .build()
                .context("Failed to create a new rawbar")?
        } else {
            // 如果时间相同，更新现有K线
            RawBarBuilder::default()
                .symbol(bar.symbol.clone())
                .id(last.id)
                .dt(freq_edt)
                .freq(freq)
                // 保持原有开盘价
                .open(last.open)
                // 更新收盘价
                .close(bar.close)
                // 取最大值
                .high(last.high.max(bar.high))
                // 取最小值
                .low(last.low.min(bar.low))
                // 累加成交量
                .vol(last.vol + bar.vol)
                // 累加成交额
                .amount(last.amount + bar.amount)
                .build()
                .context("Failed to create a new rawbar")?
        };

        // 更新或添加K线
        if freq_edt != last.dt {
            // 限制K线数量
            // 如果超出最大容量，先移除最旧的元素
            if bars.len() == self.max_count {
                bars.pop_front();
            }
            bars.push_back(new_bar);
        } else {
            let last_index = bars.len() - 1;
            bars[last_index] = new_bar;
        }

        Ok(())
    }

    /// 获取最新K线日期
    pub fn latest_date(&self) -> Option<DateTime<Utc>> {
        self.freq_bars
            .values()
            .next()
            .and_then(|v| v.read().back().cloned())
            .map(|b| b.dt)
    }

    /// 获取所属品种
    pub fn symbol(&self) -> Option<Symbol> {
        self.freq_bars
            .values()
            .next()
            .and_then(|v| v.read().back().cloned())
            .map(|b| b.symbol)
    }

    /// 更新各周期K线
    ///
    /// # 函数计算逻辑
    ///
    /// 1. 获取基准周期`base_freq`，并验证输入`bar`的周期值是否与之匹配
    /// 2. 更新`self.symbol`和`self.end_dt`为当前K线的对应值
    /// 3. 检查重复性：
    ///    - 检查`self.bars[base_freq]`中是否已存在相同时间的K线
    ///    - 如果存在重复K线，返回错误，不进行更新
    /// 4. 如果无重复，遍历所有周期：
    ///    - 对每个周期调用`update_freq`方法更新K线数据
    /// 5. 维护数据量：
    ///    - 遍历所有周期的K线数据
    ///    - 确保每个周期的K线数量不超过`max_count`
    ///    - 如果超过限制，保留最新的`max_count`条数据
    ///
    /// # Arguments
    ///
    /// * `bar` - 已完成的基准周期K线的引用
    ///
    /// # Returns
    ///
    /// * `Ok(())` - 更新成功
    /// * `Err(String)` - 包含错误信息的字符串
    pub fn update_bar(&self, bar: &RawBar) -> Result<(), UtilsError> {
        // 1. 验证基准周期是否匹配
        if bar.freq != self.base_freq {
            czsc_bail!(
                "输入周期和基准周期不匹配. Expected {}, got {}",
                self.base_freq,
                bar.freq.to_string()
            );
        }

        // 3. 检查是否存在重复的K线
        if let Some(base_bars) = self.freq_bars.get(&self.base_freq)
            && let Some(last_bar) = base_bars.read().back()
            && last_bar.dt == bar.dt
        {
            return Ok(());
        }

        for (freq, bars) in self.freq_bars.iter() {
            // 更新每个周期的K线
            self.update_freq(bar, *freq, bars.write())?;
        }

        Ok(())
    }
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl BarGenerator {
    #[new]
    #[pyo3(signature = (base_freq, freqs, max_count = 2000, market = None))]
    fn new_py(
        base_freq: Py<PyAny>,
        freqs: Py<PyAny>,
        max_count: usize,
        market: Option<Py<PyAny>>,
    ) -> PyResult<Self> {
        use std::str::FromStr;

        Python::attach(|py| {
            // 转换base_freq - 支持字符串和枚举
            let base_freq =
                if let Ok(py_str) = base_freq.cast_bound::<pyo3::types::PyString>(py) {
                    let py_str = py_str.to_string();
                    Freq::from_str(&py_str).map_err(|e| {
                        pyo3::exceptions::PyValueError::new_err(format!("解析base_freq失败: {e}"))
                    })?
                } else if let Ok(freq) = base_freq.extract::<Freq>(py) {
                    freq
                } else {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "base_freq必须是字符串或Freq枚举",
                    ));
                };

            // 转换freqs - 支持字符串列表和枚举列表
            let freqs_list = freqs
                .cast_bound::<pyo3::types::PyList>(py)
                .map_err(|_| pyo3::exceptions::PyValueError::new_err("freqs必须是列表"))?;

            let mut converted_freqs = Vec::new();
            for freq_item in freqs_list.iter() {
                let freq = if let Ok(py_str) = freq_item.cast::<pyo3::types::PyString>() {
                    let py_str = py_str.to_string();
                    Freq::from_str(&py_str).map_err(|e| {
                        pyo3::exceptions::PyValueError::new_err(format!("解析freqs失败: {e}"))
                    })?
                } else if let Ok(freq) = freq_item.extract::<Freq>() {
                    freq
                } else {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "freqs中的每个元素必须是字符串或Freq枚举",
                    ));
                };
                converted_freqs.push(freq);
            }

            // 转换market - 支持字符串、枚举和None（默认为A股）
            let market = if let Some(market_obj) = market {
                if let Ok(py_str) = market_obj.cast_bound::<pyo3::types::PyString>(py) {
                    let py_str = py_str.to_string();
                    Market::from_str(&py_str).map_err(|e| {
                        pyo3::exceptions::PyValueError::new_err(format!("解析market失败: {e}"))
                    })?
                } else if let Ok(market) = market_obj.extract::<Market>(py) {
                    market
                } else {
                    return Err(pyo3::exceptions::PyValueError::new_err(
                        "market必须是字符串或Market枚举",
                    ));
                }
            } else {
                Market::Default // 默认为默认市场，与历史版本保持一致
            };

            let bg = Self::new(base_freq, converted_freqs, max_count, market)?;
            Ok(bg)
        })
    }

    /// 初始化某个周期的K线序列
    ///
    /// # 函数计算逻辑
    ///
    /// 1. 检查输入的`freq`是否存在于`self.freq_bars`的键中。如果不存在，返回错误。
    /// 2. 检查`self.freq_bars[freq]`是否为空。如果不为空，返回错误，表示不允许重复初始化。
    /// 3. 如果以上检查都通过，将输入的`bars`存储到`self.freq_bars[freq]`中。
    /// 4. 从`bars`中获取最后一根K线的交易标的代码，更新`self.symbol`。
    ///
    /// # Arguments
    ///
    /// * `freq` - 周期名称 (支持字符串或Freq枚举)
    /// * `bars` - K线序列
    fn init_freq_bars(&mut self, freq: Py<PyAny>, bars: Vec<RawBar>) -> PyResult<()> {
        use std::str::FromStr;

        Python::attach(|py| {
            // 转换freq - 支持字符串和枚举
            let freq = if let Ok(py_str) = freq.cast_bound::<pyo3::types::PyString>(py) {
                let py_str = py_str.to_string();
                Freq::from_str(&py_str).map_err(|e| {
                    pyo3::exceptions::PyValueError::new_err(format!("解析freq失败: {e}"))
                })?
            } else if let Ok(freq) = freq.extract::<Freq>(py) {
                freq
            } else {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "freq必须是字符串或Freq枚举",
                ));
            };

            self.init_freq_with_bars(freq, bars)?;
            Ok(())
        })
    }

    /// 获取最新K线日期
    pub fn get_latest_date(&self) -> Option<String> {
        self.latest_date().map(|dt| dt.to_string())
    }

    /// 获取所属品种 - Python 属性
    #[getter]
    #[pyo3(name = "symbol")]
    fn get_symbol_py(&self) -> Option<String> {
        self.freq_bars
            .values()
            .next()
            .and_then(|v| v.read().back().cloned())
            .map(|b| b.symbol.to_string())
    }

    /// 获取基准频率
    #[getter]
    fn base_freq(&self) -> String {
        match self.base_freq {
            Freq::F1 => "1分钟",
            Freq::F2 => "2分钟",
            Freq::F3 => "3分钟",
            Freq::F4 => "4分钟",
            Freq::F5 => "5分钟",
            Freq::F6 => "6分钟",
            Freq::F10 => "10分钟",
            Freq::F12 => "12分钟",
            Freq::F15 => "15分钟",
            Freq::F20 => "20分钟",
            Freq::F30 => "30分钟",
            Freq::F60 => "60分钟",
            Freq::F120 => "120分钟",
            Freq::F240 => "240分钟",
            Freq::F360 => "360分钟",
            Freq::D => "日线",
            Freq::W => "周线",
            Freq::M => "月线",
            Freq::S => "季线",
            Freq::Y => "年线",
            Freq::Tick => "Tick",
        }
        .to_string()
    }

    /// 获取end_dt属性（Python兼容）
    #[getter]
    fn end_dt(&self, py: Python) -> PyResult<Option<Py<PyAny>>> {
        match self.latest_date() {
            Some(dt) => {
                let timestamp = czsc_core::utils::common::create_naive_pandas_timestamp(py, dt)?;
                Ok(Some(timestamp))
            }
            None => Ok(None),
        }
    }

    /// 获取各周期K线数据 - 返回字典，键为频率字符串，值为K线列表
    #[getter]
    fn bars(&self, py: Python) -> PyResult<Py<PyAny>> {
        let dict = PyDict::new(py);

        // 遍历 BarGenerator 的所有周期数据
        for (freq, bars_lock) in &self.freq_bars {
            let bars = bars_lock.read();
            let freq_str = match freq {
                Freq::Tick => "Tick",
                Freq::F1 => "1分钟",
                Freq::F2 => "2分钟",
                Freq::F3 => "3分钟",
                Freq::F4 => "4分钟",
                Freq::F5 => "5分钟",
                Freq::F6 => "6分钟",
                Freq::F10 => "10分钟",
                Freq::F12 => "12分钟",
                Freq::F15 => "15分钟",
                Freq::F20 => "20分钟",
                Freq::F30 => "30分钟",
                Freq::F60 => "60分钟",
                Freq::F120 => "120分钟",
                Freq::F240 => "240分钟",
                Freq::F360 => "360分钟",
                Freq::D => "日线",
                Freq::W => "周线",
                Freq::M => "月线",
                Freq::S => "季线",
                Freq::Y => "年线",
            };

            // 将 RawBar 转换为 PyRawBar
            let py_bars: Vec<RawBar> = bars.iter().cloned().collect();

            dict.set_item(freq_str, py_bars)?;
        }

        Ok(dict.into())
    }

    /// 从Python RawBar对象更新K线数据 - 支持直接自动转换
    #[pyo3(signature = (bar))]
    fn update(&self, bar: &RawBar) -> PyResult<()> {
        self.update_bar(bar)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))
    }

    /// 支持 pickle 序列化 - 使用 __reduce__ 方法
    fn __reduce__(&self, py: Python) -> PyResult<Py<PyAny>> {
        // 构造函数参数
        let freqs: Vec<String> = self
            .freq_bars
            .keys()
            .filter(|&freq| *freq != self.base_freq) // 排除基准频率
            .map(|freq| freq.to_string())
            .collect();

        let args = (self.base_freq.to_string(), freqs, self.max_count).into_pyobject(py)?;

        // 状态数据
        let state = PyDict::new(py);
        state.set_item("market", self.market.to_string())?;

        // 保存所有周期的K线数据
        let freq_bars_dict = PyDict::new(py);
        for (freq, bars_lock) in &self.freq_bars {
            let bars = bars_lock.read();
            let bars_list: Vec<_> = bars.iter().cloned().collect();
            freq_bars_dict.set_item(freq.to_string(), bars_list)?;
        }
        state.set_item("freq_bars", freq_bars_dict)?;

        // 返回 (constructor, args, state)
        let constructor = py.get_type::<Self>();
        let result = (constructor, args, state).into_pyobject(py)?;
        Ok(result.into())
    }

    /// 支持 pickle 反序列化
    fn __setstate__(&mut self, py: Python, state: Py<PyAny>) -> PyResult<()> {
        use std::str::FromStr;

        let state_dict = state.cast_bound::<PyDict>(py)?;

        // 恢复市场属性
        if let Some(market_item) = state_dict.get_item("market")? {
            let market_str: String = market_item.extract()?;
            self.market = Market::from_str(&market_str).map_err(|e| {
                pyo3::exceptions::PyValueError::new_err(format!("Failed to parse market: {e}"))
            })?;
        }

        // 恢复K线数据
        if let Some(freq_bars_item) = state_dict.get_item("freq_bars")? {
            let freq_bars_dict = freq_bars_item.cast::<PyDict>()?;
            self.freq_bars.clear();

            for (freq_str, bars_obj) in freq_bars_dict.iter() {
                let freq_str: String = freq_str.extract()?;
                let freq = Freq::from_str(&freq_str).map_err(|e| {
                    pyo3::exceptions::PyValueError::new_err(format!("Failed to parse freq: {e}"))
                })?;

                let bars_list: Vec<RawBar> = bars_obj.extract()?;
                let bars_deque: VecDeque<RawBar> = bars_list.into_iter().collect();
                self.freq_bars.insert(freq, RwLock::new(bars_deque));
            }
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use chrono::{NaiveDateTime, TimeZone};

    use super::*;
    use std::sync::Arc;

    #[test]
    fn test_init_freq_bars() {
        let mut bg =
            BarGenerator::new(Freq::F1, vec![Freq::F5, Freq::F15], 5, Market::Default).unwrap();

        // 创建测试用的K线数据
        let test_bars = vec![
            RawBarBuilder::default()
                .symbol("000016.SH".to_string())
                .id(1)
                .dt(Utc.from_utc_datetime(
                    &NaiveDateTime::parse_from_str("2024-1-1 0:0:0", "%Y-%m-%d %H:%M:%S").unwrap(),
                ))
                .freq(Freq::F5)
                .open(4000.0)
                .close(4010.0)
                .high(4020.0)
                .low(3990.0)
                .vol(1000.0)
                .amount(4000.0)
                .build()
                .unwrap(),
            RawBarBuilder::default()
                .symbol("000016.SH".to_string())
                .id(2)
                .dt(Utc.from_utc_datetime(
                    &NaiveDateTime::parse_from_str("2024-1-1 0:6:0", "%Y-%m-%d %H:%M:%S").unwrap(),
                ))
                .freq(Freq::F5)
                .open(4010.0)
                .close(4020.0)
                .high(4030.0)
                .low(4000.0)
                .vol(1200.0)
                .amount(4800.0)
                .build()
                .unwrap(),
        ];

        // 成功初始化
        let result = bg.init_freq_with_bars(Freq::F5, test_bars.clone());
        assert!(result.is_ok());

        // 验证数据是否正确存储
        let bars = bg.freq_bars.get(&Freq::F5).unwrap().read();
        assert_eq!(bars.len(), 2);
        assert_eq!(bars[0].open, 4000.0);
        assert_eq!(bars[1].close, 4020.0);

        // 重复初始化错误
        drop(bars);
        let result = bg.init_freq_with_bars(Freq::F5, test_bars);
        assert!(result.is_err());

        // 空K线列表初始化
        let result = bg.init_freq_with_bars(Freq::F15, vec![]);
        assert!(result.is_ok());
        let bars = bg.freq_bars.get(&Freq::F15).unwrap().read();
        assert!(bars.is_empty());
    }

    #[test]
    fn test_update_freq_new_bar() {
        let bg = BarGenerator::new(Freq::F1, vec![Freq::F5, Freq::F15], 5, Market::AShare).unwrap();

        // 第一根K线的更新
        let bar1 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str("2024-1-1 2:1:0", "%Y-%m-%d %H:%M:%S").unwrap(),
            ))
            .freq(Freq::F1)
            .open(4000.0)
            .close(4010.0)
            .high(4020.0)
            .low(3990.0)
            .vol(1000.0)
            .amount(4000.0)
            .build()
            .unwrap();

        let result = bg.update_bar(&bar1);
        assert!(result.is_ok());

        let five_min_bars = bg.freq_bars.get(&Freq::F5).unwrap().read();
        assert_eq!(five_min_bars.len(), 1, "K线柱数量应该为1");
        assert_eq!(five_min_bars[0].open, 4000.0, "开盘价应该为4000.0");
        assert_eq!(five_min_bars[0].close, 4010.0, "收盘价应该为4010.0");
        assert_eq!(five_min_bars[0].high, 4020.0, "最高价应该为4020.0");
        assert_eq!(five_min_bars[0].low, 3990.0, "最低价应该为3990.0");
        assert_eq!(five_min_bars[0].vol, 1000.0, "成交量应该为1000.0");
    }

    #[test]
    fn test_update_freq_same_bar() {
        let bg = BarGenerator::new(Freq::F1, vec![Freq::F5, Freq::F15], 5, Market::AShare).unwrap();

        let bar1 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str("2024-1-1 2:1:0", "%Y-%m-%d %H:%M:%S").unwrap(),
            ))
            .freq(Freq::F1)
            .open(4000.0)
            .close(4010.0)
            .high(4020.0)
            .low(3990.0)
            .vol(10.0)
            .amount(40.0)
            .build()
            .unwrap();
        bg.update_bar(&bar1).unwrap();

        // 在同一个5分钟周期内更新
        let bar2 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str("2024-1-1 2:2:0", "%Y-%m-%d %H:%M:%S").unwrap(),
            ))
            .freq(Freq::F1)
            .open(4006.0)
            .high(4020.0)
            .low(4000.0)
            .close(4015.0)
            .vol(15.0)
            .amount(60.0)
            .build()
            .unwrap();

        bg.update_bar(&bar2).unwrap();

        let five_min_bars = bg.freq_bars.get(&Freq::F5).unwrap().read();
        assert_eq!(five_min_bars.len(), 1);
        assert_eq!(five_min_bars[0].open, 4000.0, "开盘价应该保持不变");
        assert_eq!(five_min_bars[0].close, 4015.0, "收盘价应该更新");
        assert_eq!(five_min_bars[0].high, 4020.0, "最高价应该取两者的最大值");
        assert_eq!(five_min_bars[0].low, 3990.0, "最低价应该取两者的最小值");
        assert_eq!(five_min_bars[0].vol, 25.0, "成交量应该累加");
        assert_eq!(five_min_bars[0].amount, 100.0, "检查成交额应该累加");
    }

    #[test]
    fn test_update_freq_new_period() {
        let bg = BarGenerator::new(Freq::F1, vec![Freq::F5, Freq::F15], 5, Market::AShare).unwrap();

        let bar1 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str("2024-1-2 09:31:00", "%Y-%m-%d %H:%M:%S").unwrap(),
            ))
            .freq(Freq::F1)
            .open(4000.0)
            .high(4010.0)
            .low(3990.0)
            .close(4005.0)
            .vol(10.0)
            .amount(40.0)
            .build()
            .unwrap();

        bg.update_bar(&bar1).unwrap();

        // 新的5分钟周期（09:36 属于下一个 F5 周期）
        let bar2 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str("2024-1-2 09:36:00", "%Y-%m-%d %H:%M:%S").unwrap(),
            ))
            .freq(Freq::F1)
            .open(4010.0)
            .high(4030.0)
            .low(4000.0)
            .close(4020.0)
            .vol(20.0)
            .amount(60.0)
            .build()
            .unwrap();
        bg.update_bar(&bar2).unwrap();

        let five_min_bars = bg.freq_bars.get(&Freq::F5).unwrap().read();
        assert_eq!(five_min_bars.len(), 2, "K线柱数量应该为2");
        // 检查新K线的数据
        assert_eq!(five_min_bars[1].open, 4010.0, "开盘价应该保持不变");
        assert_eq!(five_min_bars[1].close, 4020.0, "收盘价应该为4020.0");
        assert_eq!(five_min_bars[1].high, 4030.0, "最高价应该为4030.0");
        assert_eq!(five_min_bars[1].low, 4000.0, "最低价应该为4000.0");
        assert_eq!(five_min_bars[1].vol, 20.0, "成交量应该为20.0");
        assert_eq!(five_min_bars[1].amount, 60.0, "成交额应该为60.0");
    }

    #[test]
    fn test_update_freq_edge_cases() {
        let bg = BarGenerator::new(Freq::F1, vec![Freq::F5, Freq::F15], 5, Market::AShare).unwrap();

        let bar1 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str("2024-1-1 2:6:0", "%Y-%m-%d %H:%M:%S").unwrap(),
            ))
            .freq(Freq::F1)
            .open(4000.0)
            .high(4010.0)
            .low(3990.0)
            .close(4005.0)
            .vol(10.0)
            .amount(40.0)
            .build()
            .unwrap();
        bg.update_bar(&bar1).unwrap();

        // 跨天的情况
        let bar2 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(Utc.from_utc_datetime(
                &NaiveDateTime::parse_from_str("2024-1-2 2:6:0", "%Y-%m-%d %H:%M:%S").unwrap(),
            ))
            .freq(Freq::F1)
            .open(4010.0)
            .high(4030.0)
            .low(4000.0)
            .close(4020.0)
            .vol(20.0)
            .amount(60.0)
            .build()
            .unwrap();
        bg.update_bar(&bar2).unwrap();

        let five_min_bars = bg.freq_bars.get(&Freq::F5).unwrap().read();
        assert_eq!(five_min_bars.len(), 2, "K线柱数量应该为2");
        // 检查ID的连续性
        assert_eq!(
            five_min_bars[1].id,
            five_min_bars[0].id + 1,
            "K线柱ID应该连续，第二个K线柱的ID应该比第一个多1"
        );
    }

    #[test]
    fn test_update() {
        // 系统内部以 UTC 存储 CST 交易时间
        let dt = Utc.from_utc_datetime(
            &NaiveDateTime::parse_from_str("2024-12-12 10:01:00", "%Y-%m-%d %H:%M:%S").unwrap(),
        );

        // 基本设置：创建一个同时处理1分钟、5分钟和15分钟周期的BarGenerator
        let bg = BarGenerator::new(Freq::F1, vec![Freq::F5, Freq::F15], 5, Market::AShare).unwrap();

        // 测试周期不匹配的情况
        let invalid_freq_bar = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(dt)
            .freq(Freq::F5)
            .open(4000.0)
            .high(4010.0)
            .low(3990.0)
            .close(4005.0)
            .vol(1000.0)
            .amount(4000.0)
            .build()
            .unwrap();

        assert!(
            bg.update_bar(&invalid_freq_bar).is_err(),
            "更新函数应该返回错误，因为传入的K线柱频率无效"
        );

        // 测试正常更新流程
        let bar1 = RawBarBuilder::default()
            .symbol("000016.SH".to_string())
            .id(1)
            .dt(dt)
            .freq(Freq::F1)
            .open(4000.0)
            .high(4010.0)
            .low(3990.0)
            .close(4005.0)
            .vol(1000.0)
            .amount(4000.0)
            .build()
            .unwrap();
        assert!(
            bg.update_bar(&bar1).is_ok(),
            "更新函数应该成功处理有效的K线柱"
        );
        // 检查更新后的状态
        assert_eq!(
            bg.symbol(),
            Some(Arc::from("000016.SH".to_string())),
            "更新后的符号应该与K线柱的符号匹配"
        );
        assert_eq!(
            bg.latest_date(),
            Some(bar1.dt),
            "更新后的结束时间应该与K线柱的时间匹配"
        );
        // 测试重复数据的处理
        assert!(
            bg.update_bar(&bar1).is_ok(),
            "重复数据应该被成功处理，即更新函数应该返回成功，但重复数据不应影响状态"
        );

        // 检查各周期数据是否正确
        assert_eq!(
            bg.freq_bars.get(&Freq::F1).unwrap().read().len(),
            1,
            "1分钟周期的K线柱数量应该为1"
        );
        assert_eq!(
            bg.freq_bars.get(&Freq::F5).unwrap().read().len(),
            1,
            "5分钟周期的K线柱数量应该为1"
        );
        assert_eq!(
            bg.freq_bars.get(&Freq::F15).unwrap().read().len(),
            1,
            "15分钟周期的K线柱数量应该为1"
        );

        // 测试数据量限制
        // 添加足够多的数据以触发max_count限制
        for i in 2..8 {
            let bar = RawBarBuilder::default()
                .symbol(Arc::from("000016.SH".to_string()))
                .id(i)
                .dt(Utc.from_utc_datetime(
                    &NaiveDateTime::parse_from_str(
                        format!("2024-1-2 9:3{i}:0").as_str(),
                        "%Y-%m-%d %H:%M:%S",
                    )
                    .unwrap(),
                ))
                .freq(Freq::F1)
                .open(4000.0 + i as f64)
                .high(4010.0 + i as f64)
                .low(3990.0 + i as f64)
                .close(4005.0 + i as f64)
                .vol(1000.0)
                .amount(4000.0)
                .build()
                .unwrap();

            assert!(bg.update_bar(&bar).is_ok(), "更新数据失败");
        }

        // 验证数据量限制是否生效（max_count = 5）
        for (_, bars) in bg.freq_bars.iter() {
            assert!(bars.read().len() <= 5, "K线数量超过了max_count限制");
        }

        // 测试跨周期数据的正确性
        let bars_5min = bg.freq_bars.get(&Freq::F5).unwrap().read();
        let last_5min = bars_5min.back().unwrap();
        assert_eq!(
            last_5min.freq,
            Freq::F5,
            "最后一个5分钟周期的K线柱频率应该为F5"
        );

        let bars_15min = bg.freq_bars.get(&Freq::F15).unwrap().read();
        let last_15min = bars_15min.back().unwrap();
        assert_eq!(
            last_15min.freq,
            Freq::F15,
            "最后一个15分钟周期的K线柱频率应该为F15"
        );

        // 测试不同市场时间

        let bg_other_market =
            BarGenerator::new(Freq::F1, vec![Freq::F15], 5, Market::Futures).unwrap();

        let bar_futures = RawBarBuilder::default()
            .symbol("IF2403".to_string())
            .id(1)
            .dt(dt)
            .freq(Freq::F1)
            .open(5180.0)
            .high(5185.0)
            .low(5178.0)
            .close(5182.0)
            .vol(100.0)
            .amount(518200.0)
            .build()
            .unwrap();

        assert!(
            bg_other_market.update_bar(&bar_futures).is_ok(),
            "更新其他市场数据失败"
        );

        // 断言其他市场的符号是否正确更新
        assert_eq!(
            bg_other_market.symbol(),
            Some(Arc::from("IF2403".to_string())),
            "市场符号应该更新为IF2403"
        );
    }
}
