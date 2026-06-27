#[cfg(feature = "python")]
use crate::analyze::utils::format_standard_kline;
use crate::objects::{
    bar::{NewBar, RawBar, Symbol},
    bi::BI,
    direction::Direction,
    freq::Freq,
    fx::FX,
    mark::Mark,
};
use derive_builder::Builder;
#[cfg(feature = "python")]
use parking_lot::RwLock;
#[cfg(feature = "python")]
use polars::prelude::*;
#[cfg(feature = "python")]
use std::io::Cursor;
#[cfg(feature = "python")]
use std::sync::Arc;
use utils::{check_bi, check_fxs, remove_include};
pub mod errors;
pub mod utils;

#[cfg(feature = "python")]
use crate::utils::common::freq_to_chinese_string;
#[cfg(feature = "python")]
use crate::utils::common::{create_naive_pandas_timestamp, create_ordered_dict};
#[cfg(feature = "python")]
use pyo3::prelude::{PyAnyMethods, PyDictMethods};
#[cfg(feature = "python")]
use pyo3::types::{PyBytesMethods, PyDict};
#[cfg(feature = "python")]
use pyo3::{Py, PyAny, PyErr, PyResult, Python};
#[cfg(feature = "python")]
use pyo3::{pyclass, pymethods};
#[cfg(feature = "python")]
use pyo3_stub_gen::derive::{gen_stub_pyclass, gen_stub_pymethods};

#[cfg_attr(feature = "python", gen_stub_pyclass)]
#[cfg_attr(feature = "python", pyclass(from_py_object, module = "czsc._native"))]
#[derive(Debug, Clone, Builder, serde::Serialize, serde::Deserialize)]
pub struct CZSC {
    // verbose: bool,
    /// 最大允许保留的笔数量
    pub max_bi_num: usize,
    /// 笔的最小长度（去包含后的 K 线根数；默认 6，可由 CZSC_MIN_BI_LEN 覆盖）
    pub min_bi_len: usize,
    /// 原始K线序列
    pub bars_raw: Vec<RawBar>,
    pub bars_ubi: Vec<NewBar>,
    pub bi_list: Vec<BI>,
    pub symbol: Symbol,
    pub freq: Freq,
    // get_signals
    // signals
    #[cfg(feature = "python")]
    #[serde(skip)]
    #[builder(default = "Arc::new(RwLock::new(None))")]
    pub cache: Arc<RwLock<Option<Py<PyDict>>>>,
}

/// 解析"显式参数优先、否则环境变量、否则默认"的 usize 配置。
/// 显式参数 > 0 时直接采用；否则依次读 UPPER / lower 环境变量，
/// 解析失败或缺失时回落到 `default`。与 `czsc.envs` 大小写约定一致（spec §3.4）。
fn resolve_env_usize(explicit: usize, upper: &str, lower: &str, default: usize) -> usize {
    if explicit > 0 {
        return explicit;
    }
    if let Ok(v) = std::env::var(upper) {
        if let Ok(n) = v.trim().parse::<f64>() {
            return n as usize;
        }
    }
    if let Ok(v) = std::env::var(lower) {
        if let Ok(n) = v.trim().parse::<f64>() {
            return n as usize;
        }
    }
    default
}

/// 笔最小长度：显式参数 (>0) 优先，否则读 `CZSC_MIN_BI_LEN`（大小写不敏感），再否则 6。
pub fn resolve_min_bi_len(explicit: usize) -> usize {
    resolve_env_usize(explicit, "CZSC_MIN_BI_LEN", "czsc_min_bi_len", 6)
}

/// 最大笔数：显式参数 (>0) 优先，否则读 `CZSC_MAX_BI_NUM`，再否则 50。
pub fn resolve_max_bi_num(explicit: usize) -> usize {
    resolve_env_usize(explicit, "CZSC_MAX_BI_NUM", "czsc_max_bi_num", 50)
}

impl CZSC {
    /// 对齐 Python 同 dt 延伸时的对象共享语义：
    /// 仅同步“被 pop 出来的 last_ubi 对象”在已入笔结构中的镜像副本。
    fn sync_extended_last_ubi_in_bis(&mut self, last_ubi: &NewBar, bar: &RawBar) {
        #[inline]
        fn patch_new_bar_if_same(nb: &mut NewBar, target: &NewBar, bar: &RawBar) {
            if nb == target
                && let Some(last) = nb.elements.last_mut()
                && last.dt == bar.dt
            {
                *last = bar.clone();
            }
        }

        #[inline]
        fn patch_fx_if_same(fx: &mut FX, target: &NewBar, bar: &RawBar) {
            for nb in &mut fx.elements {
                patch_new_bar_if_same(nb, target, bar);
            }
        }

        for bi in &mut self.bi_list {
            for nb in &mut bi.bars {
                patch_new_bar_if_same(nb, last_ubi, bar);
            }
            patch_fx_if_same(&mut bi.fx_a, last_ubi, bar);
            patch_fx_if_same(&mut bi.fx_b, last_ubi, bar);
            for fx in &mut bi.fxs {
                patch_fx_if_same(fx, last_ubi, bar);
            }
        }
    }

    pub fn new(bars_raw: Vec<RawBar>, max_bi_num: usize, min_bi_len: usize) -> Self {
        // todo check length of bars_raw

        let mut c = Self {
            max_bi_num,
            min_bi_len,
            bars_raw: Vec::with_capacity(bars_raw.len()), // 预分配容量
            bars_ubi: Vec::with_capacity(bars_raw.len() / 2), // 预估容量
            bi_list: Vec::with_capacity(max_bi_num.min(bars_raw.len() / 10)), // 预估笔数量
            symbol: bars_raw[0].symbol.clone(),
            freq: bars_raw[0].freq,
            #[cfg(feature = "python")]
            cache: Arc::new(RwLock::new(None)),
        };

        for b in bars_raw {
            c.update_bar(b);
        }

        c
    }

    /// 分型列表，包括 bars_ubi 中的分型
    pub fn get_fx_list(&self) -> Vec<FX> {
        let mut fxs = Vec::new();
        for bi_ in self.bi_list.iter() {
            fxs.extend_from_slice(&bi_.fxs[1..]);
        }

        if let Some(ubi_fxs) = self.get_ubi_fxs() {
            for x in ubi_fxs {
                if fxs.is_empty() || x.dt > fxs.last().unwrap().dt {
                    fxs.push(x);
                }
            }
        }
        fxs
    }

    /// 更新分析结果
    ///
    /// :param bar: 单根K线对象
    pub fn update_bar(&mut self, bar: RawBar) {
        // 更新K线序列
        let last_bars = if self.bars_raw.is_empty() || bar.dt != self.bars_raw.last().unwrap().dt {
            self.bars_raw.push(bar.clone());
            vec![bar]
        } else {
            // 当前 bar 是上一根 bar 的时间延伸
            *self.bars_raw.last_mut().unwrap() = bar.clone();
            let last_ubi = self.bars_ubi.pop().unwrap();
            self.sync_extended_last_ubi_in_bis(&last_ubi, &bar);
            let mut last_bars = last_ubi.elements.to_vec();
            assert_eq!(
                bar.dt,
                last_bars.last().unwrap().dt,
                "时间错位: {} != {}",
                bar.dt,
                last_bars.last().unwrap().dt
            );

            *last_bars.last_mut().unwrap() = bar;
            last_bars
        };

        // 去除包含关系
        for bar in last_bars.iter() {
            if self.bars_ubi.len() < 2 {
                self.bars_ubi.push(NewBar::new_from_raw(bar));
            } else {
                let (has_include, k3) = {
                    // 安全获取两个相邻元素的引用
                    let idx = self.bars_ubi.len() - 2;
                    let (_, last_two) = self.bars_ubi.split_at_mut(idx);
                    let k1 = &last_two[0]; // 倒数第二个元素
                    let k2 = &last_two[1]; // 最后一个元素
                    remove_include(k1, k2, bar.clone()).unwrap()
                };
                if has_include {
                    *self.bars_ubi.last_mut().unwrap() = k3;
                } else {
                    self.bars_ubi.push(k3);
                }
            }
        }

        // 更新笔
        self.__update_bi();
        // 根据最大笔数量限制完成 bi_list, bars_raw 序列的数量控制
        if self.bi_list.len() > self.max_bi_num {
            let start_idx = self.bi_list.len() - self.max_bi_num;
            self.bi_list.drain(0..start_idx);
        }

        if !self.bi_list.is_empty() {
            let sdt = self.bi_list.first().unwrap().fx_a.elements[0].dt;
            // 对齐 Python: 取第一个 dt >= sdt 的位置（重复 dt 时必须取最左侧）
            let drain_to = self.bars_raw.partition_point(|bar| bar.dt < sdt);
            self.bars_raw.drain(0..drain_to);
        }

        // 如果有信号计算函数，则进行信号计算
        // todo self.get_signals
    }

    fn __update_bi(&mut self) -> Option<()> {
        if self.bars_ubi.len() < 3 {
            return None;
        }

        // 查找笔
        if self.bi_list.is_empty() {
            // 第一笔的查找
            let fxs = check_fxs(&self.bars_ubi);

            let first = fxs.first()?;
            let fx_a = fxs
                .iter()
                .filter(|x| x.mark == first.mark)
                .reduce(|acc, x| match first.mark {
                    Mark::D if x.low <= acc.low => x,
                    Mark::G if x.high >= acc.high => x,
                    _ => acc,
                })
                .unwrap_or(first);

            let bars_ubi = self
                .bars_ubi
                .iter()
                .filter(|x| x.dt >= fx_a.elements[0].dt)
                .collect::<Vec<_>>();

            let (bi, bars_ubi_) = check_bi(&bars_ubi, self.min_bi_len);
            if let Some(bi) = bi {
                self.bi_list.push(bi);
            }

            self.bars_ubi = bars_ubi_.iter().map(|&bar| bar.clone()).collect::<Vec<_>>();
            return None;
        }

        // todo log

        // println!(
        //     "dt: {}, 未完成笔延伸数量: {}",
        //     self.bars_ubi.last().unwrap().dt,
        //     self.bars_ubi.len()
        // );
        let (bi, bars_ubi_) = check_bi(&self.bars_ubi, self.min_bi_len);
        if let Some(bi) = bi {
            self.bi_list.push(bi);
        }

        self.bars_ubi = bars_ubi_.to_vec();

        // 后处理：如果当前笔被破坏，将当前笔的bars与bars_ubi进行合并，并丢弃
        let last_bi = self.bi_list.last().unwrap(); // 获取最后一个笔
        let bars_ubi = &self.bars_ubi;

        if bars_ubi.last().is_some()
            && ((last_bi.direction == Direction::Up
                && bars_ubi.last().unwrap().high > last_bi.get_high())
                || (last_bi.direction == Direction::Down
                    && bars_ubi.last().unwrap().low < last_bi.get_low()))
        {
            // 当前笔被破坏，将当前笔的bars与bars_ubi进行合并
            // 使用除了最后两根K线之外的所有K线
            let merge_point = last_bi.bars[last_bi.bars.len() - 2].dt;

            // 创建新的合并后的bars序列
            self.bars_ubi = last_bi.bars[..last_bi.bars.len() - 2]
                .iter()
                .chain(bars_ubi.iter().filter(|x| x.dt >= merge_point))
                .cloned()
                .collect();

            // 移除最后一个笔
            self.bi_list.pop();
        }
        None
    }

    /// 获取 bars_ubi 中的分型
    pub fn get_ubi_fxs(&self) -> Option<Vec<FX>> {
        if self.bars_ubi.is_empty() {
            return None;
        }
        Some(check_fxs(&self.bars_ubi))
    }

    #[allow(unused)]
    /// Unfinished Bi，未完成的笔
    fn get_ubi(&self) -> Option<UBI> {
        if self.bars_ubi.is_empty() || self.bi_list.is_empty() {
            return None;
        }

        let ubi_fxs = self.get_ubi_fxs()?;

        let bars_raw = self
            .bars_ubi
            .iter()
            .flat_map(|x| &x.elements)
            .collect::<Vec<_>>();

        // 获取最高点和最低点，以及对应的时间
        let high_bar = bars_raw
            .iter()
            .max_by(|a, b| {
                a.high
                    .partial_cmp(&b.high)
                    .unwrap_or(std::cmp::Ordering::Less)
            })
            .unwrap()
            .to_owned()
            .to_owned();

        let low_bar = bars_raw
            .iter()
            .min_by(|a, b| {
                a.low
                    .partial_cmp(&b.low)
                    .unwrap_or(std::cmp::Ordering::Greater)
            })
            .unwrap()
            .to_owned()
            .to_owned();

        let direction = if self.bi_list.last().unwrap().direction == Direction::Down {
            Direction::Up
        } else {
            Direction::Down
        };
        let fx_a = ubi_fxs.first().unwrap().to_owned();
        Some(UBI {
            symbol: self.symbol.clone(),
            direction,
            high: high_bar.high,
            low: low_bar.low,
            high_bar,
            low_bar,
            bars: self.bars_ubi.to_owned(),
            raw_bars: self.bars_raw.to_owned(),
            fxs: ubi_fxs,
            fx_a,
        })
    }
}

#[cfg(feature = "python")]
#[cfg_attr(feature = "python", gen_stub_pymethods)]
#[cfg_attr(feature = "python", pymethods)]
impl CZSC {
    #[new]
    #[pyo3(signature = (bars_raw, max_bi_num=0, min_bi_len=0))]
    pub fn new_py(bars_raw: Vec<RawBar>, max_bi_num: usize, min_bi_len: usize) -> PyResult<Self> {
        Ok(CZSC::new(
            bars_raw,
            resolve_max_bi_num(max_bi_num),
            resolve_min_bi_len(min_bi_len),
        ))
    }

    /// 直接从Arrow格式的DataFrame创建CZSC对象，避免中间转换
    /// 这是高性能的批量创建接口，适用于大量数据的初始化
    ///
    /// :param df_bytes: Arrow IPC格式的DataFrame字节数据
    /// :param freq: K线频率
    /// :param max_bi_num: 最大笔数量限制
    /// :return: CZSC对象
    #[staticmethod]
    #[pyo3(signature = (df_bytes, freq, max_bi_num=0, min_bi_len=0))]
    pub fn from_dataframe(
        df_bytes: pyo3::Bound<'_, pyo3::types::PyBytes>,
        freq: Freq,
        max_bi_num: usize,
        min_bi_len: usize,
    ) -> PyResult<Self> {
        // 直接从Arrow字节数据创建DataFrame
        let bytes_data = df_bytes.as_bytes();
        let cursor = Cursor::new(bytes_data);
        let df = IpcReader::new(cursor).finish().map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to read Arrow data: {e}"
            ))
        })?;

        // 数据验证：确保DataFrame包含必需的列
        let required_columns = [
            "symbol", "dt", "open", "close", "high", "low", "vol", "amount",
        ];
        let column_names = df.get_column_names();
        for col in &required_columns {
            if !column_names.iter().any(|name| name.as_str() == *col) {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                    "Missing required column: {col}"
                )));
            }
        }

        // 验证数据不为空
        if df.height() == 0 {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "DataFrame is empty",
            ));
        }

        // 直接格式化为RawBar - 这是性能关键路径
        let bars = format_standard_kline(df, freq).map_err(|e| {
            PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Failed to format kline data: {e}"
            ))
        })?;

        // 批量创建CZSC对象
        Ok(CZSC::new(
            bars,
            resolve_max_bi_num(max_bi_num),
            resolve_min_bi_len(min_bi_len),
        ))
    }

    #[getter]
    fn symbol(&self) -> String {
        self.symbol.to_string()
    }

    #[getter]
    fn freq(&self) -> Freq {
        self.freq
    }

    #[getter]
    fn max_bi_num(&self) -> usize {
        self.max_bi_num
    }

    #[getter]
    fn min_bi_len(&self) -> usize {
        self.min_bi_len
    }

    #[getter]
    fn bi_list(&self) -> Vec<BI> {
        self.bi_list.to_vec()
    }

    /// 获取原始K线序列 - 返回PyRawBar对象列表
    #[getter]
    fn bars_raw(&self) -> Vec<RawBar> {
        self.bars_raw.to_vec()
    }

    /// 获取原始K线序列的DataFrame格式，便于绘图和分析
    #[getter]
    fn bars_raw_df(&self, py: Python) -> PyResult<Py<PyAny>> {
        let pandas = py.import("pandas")?;
        let df_class = pandas.getattr("DataFrame")?;

        let data: Vec<Py<PyAny>> = self
            .bars_raw
            .iter()
            .map(|bar| -> PyResult<Py<PyAny>> {
                let dict = PyDict::new(py);
                dict.set_item("symbol", bar.symbol.as_ref())?;
                dict.set_item("dt", create_naive_pandas_timestamp(py, bar.dt)?)?;
                dict.set_item("freq", freq_to_chinese_string(bar.freq))?;
                dict.set_item("id", bar.id)?;
                dict.set_item("open", bar.open)?;
                dict.set_item("close", bar.close)?;
                dict.set_item("high", bar.high)?;
                dict.set_item("low", bar.low)?;
                dict.set_item("vol", bar.vol)?;
                dict.set_item("amount", bar.amount)?;
                Ok(dict.into())
            })
            .collect::<PyResult<Vec<_>>>()?;

        let df = df_class.call1((data,))?;
        Ok(df.into())
    }

    /// 获取无包含关系K线序列
    #[getter]
    fn bars_ubi(&self) -> Vec<NewBar> {
        self.bars_ubi.to_vec()
    }

    /// 获取已完成的笔列表（与 bi_list 相同，为兼容 czsc 库）
    #[getter]
    fn finished_bis(&self) -> Vec<BI> {
        if self.bi_list.is_empty() {
            return vec![];
        }
        if self.bars_ubi.len() < 5 {
            return self.bi_list[..self.bi_list.len().saturating_sub(1)].to_vec();
        }
        self.bi_list.to_vec()
    }

    /// 获取分型列表（属性，与 czsc 库兼容）
    #[getter]
    fn fx_list(&self) -> Vec<FX> {
        self.get_fx_list().into_iter().collect()
    }

    /// 缓存字典（与 czsc 库兼容）
    #[getter]
    fn cache(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_ordered_dict(py)
    }

    /// 信号字典（与 czsc 库兼容）
    #[getter]
    fn signals(&self, py: Python) -> PyResult<Py<PyAny>> {
        create_ordered_dict(py)
    }

    /// 无包含关系K线分型列表（与 czsc 库兼容）
    #[getter]
    fn ubi_fxs(&self) -> Vec<FX> {
        self.get_ubi_fxs().unwrap_or_default()
    }

    /// 无包含关系K线（与 czsc 库兼容）
    /// 返回未完成的笔信息，格式与 Python 版本保持一致
    #[getter]
    fn ubi(&self, py: Python) -> PyResult<Py<PyAny>> {
        let ubi_fxs = self.get_ubi_fxs().unwrap_or_default();

        if self.bars_ubi.is_empty() || self.bi_list.is_empty() || ubi_fxs.is_empty() {
            return Ok(py.None());
        }

        // 获取所有原始K线
        let bars_raw: Vec<RawBar> = self
            .bars_ubi
            .iter()
            .flat_map(|x| &x.elements)
            .cloned()
            .collect();

        if bars_raw.is_empty() {
            return Ok(py.None());
        }

        // 获取最高点和最低点
        let high_bar = bars_raw
            .iter()
            .max_by(|a, b| a.high.partial_cmp(&b.high).unwrap())
            .unwrap()
            .clone();

        let low_bar = bars_raw
            .iter()
            .min_by(|a, b| a.low.partial_cmp(&b.low).unwrap())
            .unwrap()
            .clone();

        // 确定方向：与最后一笔相反
        let direction = if self.bi_list.last().unwrap().direction == Direction::Down {
            Direction::Up
        } else {
            Direction::Down
        };

        // 创建字典，按照原版 czsc 的字段顺序
        let dict = PyDict::new(py);
        dict.set_item("symbol", self.symbol.as_ref())?;
        dict.set_item("direction", direction)?;
        dict.set_item("high", high_bar.high)?;
        dict.set_item("low", low_bar.low)?;
        dict.set_item("high_bar", high_bar)?;
        dict.set_item("low_bar", low_bar)?;
        dict.set_item("bars", self.bars_ubi())?;
        dict.set_item("raw_bars", bars_raw)?;
        dict.set_item("fxs", ubi_fxs.clone())?;
        dict.set_item("fx_a", ubi_fxs.first().unwrap().clone())?;

        // 直接返回字典
        Ok(dict.into())
    }

    /// 是否显示详细信息（与 czsc 库兼容）
    #[getter]
    fn verbose(&self) -> bool {
        false // 默认不显示详细信息
    }

    /// 最后一笔延伸情况（与 czsc 库兼容）
    /// 判断最后一笔是否在延伸中，True 表示延伸中
    #[getter]
    fn last_bi_extend(&self) -> bool {
        // 如果没有笔，返回 false
        if self.bi_list.is_empty() {
            return false;
        }

        // 如果没有无包含关系K线，返回 false
        if self.bars_ubi.is_empty() {
            return false;
        }

        let last_bi = &self.bi_list[self.bi_list.len() - 1];

        match last_bi.direction {
            Direction::Up => {
                // 向上笔：检查当前所有无包含K线的最高价是否 > 最后一笔的高点
                let max_high = self
                    .bars_ubi
                    .iter()
                    .map(|bar| bar.high)
                    .max_by(|a, b| a.partial_cmp(b).unwrap())
                    .unwrap_or(0.0);

                max_high > last_bi.get_high()
            }
            Direction::Down => {
                // 向下笔：检查当前所有无包含K线的最低价是否 < 最后一笔的低点
                let min_low = self
                    .bars_ubi
                    .iter()
                    .map(|bar| bar.low)
                    .min_by(|a, b| a.partial_cmp(b).unwrap())
                    .unwrap_or(f64::MAX);

                min_low < last_bi.get_low()
            }
        }
    }

    /// 在浏览器中打开（与 czsc 库兼容）
    #[pyo3(signature = (_renderer=None))]
    fn open_in_browser(&self, _renderer: Option<&str>) -> PyResult<String> {
        Ok("Browser opening not implemented in Rust version".to_string())
    }

    /// 转换为 ECharts 格式（与 czsc 库兼容）
    fn to_echarts(&self) -> PyResult<String> {
        Ok("ECharts export not implemented in Rust version".to_string())
    }

    /// 转换为 Plotly 格式（与 czsc 库兼容）
    fn to_plotly(&self) -> PyResult<String> {
        Ok("Plotly export not implemented in Rust version".to_string())
    }

    /// 更新K线数据
    fn update(&mut self, bar: RawBar) -> PyResult<()> {
        self.update_bar(bar);
        Ok(())
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

        // 如果缓存为空，使用写锁初始化
        let mut cache_write = self.cache.write();
        if cache_write.is_none() {
            *cache_write = Some(PyDict::new(py).unbind());
        }
        cache_write.as_ref().unwrap().clone_ref(py)
    }

    #[setter]
    #[gen_stub(skip)] // 跳过为了防止和 get_cache重复
    fn set_cache(&self, dict: Py<PyDict>) {
        let mut cache_write = self.cache.write();
        *cache_write = Some(dict);
    }
    fn __repr__(&self) -> String {
        format!(
            "CZSC(symbol={}, freq={:?}, max_bi_num={}, bi_count={})",
            self.symbol,
            self.freq,
            self.max_bi_num,
            self.bi_list.len()
        )
    }

    /// Pickle 支持 —— `__reduce__` 返回 ``(CZSC, (fixed_point_bars, max_bi_num))``。
    ///
    /// `update_bar` 会丢弃 dt 小于当前 first-BI 起始时间的旧 bar
    /// （参见上面的 `bars_raw.drain` 块），因此刚构造出来的 CZSC 的
    /// `bars_raw` 可能仍然和「再分析一次后到达的不动点」不同。这里多
    /// 跑一次 `CZSC::new`，让其在序列化前收敛 —— 保证即使 CzscSignals
    /// 在 `kas[freq]` 里嵌套了 CZSC，`pickle.dumps(restored) ==
    /// pickle.dumps(obj)` 也是逐字节相等的（Phase A 的
    /// `restored.__getstate__() == obj.__getstate__()` 断言依赖这一点）。
    fn __reduce__(&self, py: Python) -> PyResult<Py<PyAny>> {
        use pyo3::IntoPyObject;
        let trimmed = CZSC::new(self.bars_raw.clone(), self.max_bi_num, self.min_bi_len);
        let args = (trimmed.bars_raw, self.max_bi_num, self.min_bi_len).into_pyobject(py)?;
        let constructor = py.get_type::<Self>();
        let result = (constructor, args).into_pyobject(py)?;
        Ok(result.into())
    }
}

/// Unfinished Bi，未完成的笔
#[derive(Debug, Clone)]
pub struct UBI {
    pub symbol: Symbol,
    pub direction: Direction,
    pub high: f64,
    pub low: f64,
    pub high_bar: RawBar,
    pub low_bar: RawBar,
    pub bars: Vec<NewBar>,
    pub raw_bars: Vec<RawBar>,
    pub fxs: Vec<FX>,
    pub fx_a: FX,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::analyze::utils::format_standard_kline;
    use crate::objects::freq::Freq;
    use chrono::NaiveDateTime;
    use chrono::{DateTime, Utc};
    use polars::prelude::SerReader;
    use polars::prelude::{CsvReader, StringChunked, StringMethods};
    use std::io::Cursor;

    fn example_data() -> &'static str {
        const CSV_DATA: &str = r#"
dt,symbol,open,close,high,low,vol,amount
2025-01-02,002515.SZ,50.73,51.29,52.97,50.62,32900684.0,152798823.0
2025-01-03,002515.SZ,51.4,48.72,51.85,48.6,33224687.0,147184323.0
2025-01-06,002515.SZ,48.83,48.6,49.39,47.48,17419634.0,75608391.0
2025-01-07,002515.SZ,48.6,48.94,49.05,48.27,13929982.0,60500438.0
2025-01-08,002515.SZ,48.27,48.04,48.94,47.26,17697397.0,75973887.0
2025-01-09,002515.SZ,48.27,48.16,48.83,47.6,14284260.0,61391856.0
2025-01-10,002515.SZ,48.04,46.92,48.94,46.81,16080374.0,68834125.0
2025-01-13,002515.SZ,46.59,46.92,47.26,45.47,12508818.0,52037636.0
2025-01-14,002515.SZ,46.92,48.16,48.27,46.92,16407679.0,69944802.0
2025-01-15,002515.SZ,49.5,49.5,50.73,49.05,29140842.0,129502353.0
2025-01-16,002515.SZ,49.5,49.72,50.28,48.94,19124511.0,84774186.0
2025-01-17,002515.SZ,49.28,50.28,51.74,49.05,22228511.0,99754272.0
2025-01-20,002515.SZ,50.4,50.4,50.73,49.61,14908933.0,66989586.0
2025-01-21,002515.SZ,50.62,50.06,50.73,49.61,11565100.0,51612511.0
2025-01-22,002515.SZ,50.06,49.16,50.06,48.83,10889797.0,47963340.0
2025-01-23,002515.SZ,49.39,48.72,49.95,48.72,13050206.0,57522568.0
2025-01-24,002515.SZ,48.49,48.83,48.94,48.27,12042388.0,52334558.0
2025-01-27,002515.SZ,49.05,49.39,51.74,49.05,22813802.0,102357601.0
2025-02-05,002515.SZ,49.39,49.16,49.95,48.72,13525075.0,59524887.0
2025-02-06,002515.SZ,48.83,49.05,49.28,48.16,17429613.0,75782611.0
2025-02-07,002515.SZ,48.94,49.5,49.95,48.72,17447114.0,76989329.0
2025-02-10,002515.SZ,49.39,50.4,50.51,49.16,18733821.0,83810683.0
2025-02-11,002515.SZ,50.4,49.84,50.73,49.61,13189816.0,58803966.0
2025-02-12,002515.SZ,50.06,50.06,50.4,49.5,15881392.0,70692291.0
2025-02-13,002515.SZ,49.84,49.84,50.51,49.61,18048669.0,80671035.0
2025-02-14,002515.SZ,49.72,49.05,49.95,48.94,17455299.0,76786904.0
2025-02-17,002515.SZ,49.16,49.39,49.61,48.6,15791678.0,69303481.0
2025-02-18,002515.SZ,49.16,47.71,49.39,47.48,20599809.0,88885983.0
2025-02-19,002515.SZ,47.48,48.04,48.16,47.37,12911258.0,55064600.0
2025-02-20,002515.SZ,48.04,48.27,48.83,47.71,12823411.0,55267260.0
2025-02-21,002515.SZ,48.27,47.6,48.72,47.48,16547084.0,70527761.0
2025-02-24,002515.SZ,47.71,52.41,52.41,47.71,93355060.0,426873493.0
2025-02-25,002515.SZ,51.96,50.51,51.96,50.17,54431026.0,246916111.0
2025-02-26,002515.SZ,50.62,52.52,52.86,50.17,50584995.0,232883144.0
2025-02-27,002515.SZ,52.41,53.64,53.98,51.96,47142936.0,224200231.0
2025-02-28,002515.SZ,53.2,52.52,53.53,52.41,29058781.0,137329596.0
"#;
        CSV_DATA
    }

    fn get_bars() -> Vec<RawBar> {
        let cursor = Cursor::new(example_data().as_bytes());
        let mut df = CsvReader::new(cursor).finish().unwrap();

        let dt_col = df
            .column("dt")
            .unwrap()
            .str()
            .unwrap()
            .as_datetime(
                Some("%Y-%m-%d"),
                polars::prelude::TimeUnit::Milliseconds,
                false,
                false,
                None,
                &StringChunked::from_iter(std::iter::once("raise")),
            )
            .unwrap();
        df.with_column(dt_col).unwrap();

        format_standard_kline(df, Freq::D).unwrap()
    }

    fn parse_dt(s: &str) -> DateTime<Utc> {
        NaiveDateTime::parse_from_str(s, "%Y-%m-%d %H:%M:%S")
            .unwrap()
            .and_local_timezone(Utc)
            .unwrap() // 保证时间有效性
    }

    /// ## 数据来源
    ///
    ///
    /// ```
    /// from czsc.connectors import cooperation as coo
    /// df = coo.stocks_daily_klines(sdt="20250101", edt="20250302")
    /// df = df[df["symbol"]=="002515.SZ"][['dt', 'symbol','open', 'close', 'high', 'low', 'vol', 'amount']]
    /// df.reset_index(drop=True, inplace=True)
    /// bars = czsc.format_standard_kline(df, "日线")
    /// c = czsc.CZSC(bars)
    /// for b in c.bi_list:
    ///     print(b)
    /// ```
    ///
    /// ```
    /// BI(symbol=002515.SZ, sdt=2025-01-13 00:00:00, edt=2025-01-17 00:00:00, direction=向上, high=51.74, low=45.47)
    /// BI(symbol=002515.SZ, sdt=2025-01-17 00:00:00, edt=2025-02-06 00:00:00, direction=向下, high=51.74, low=48.16)
    /// BI(symbol=002515.SZ, sdt=2025-02-06 00:00:00, edt=2025-02-11 00:00:00, direction=向上, high=50.73, low=48.16)
    /// BI(symbol=002515.SZ, sdt=2025-02-11 00:00:00, edt=2025-02-19 00:00:00, direction=向下, high=50.73, low=47.37)
    /// ```
    #[test]
    fn test_czsc_bi_list() {
        let bars = get_bars();
        let c = CZSC::new(bars, 50, 6);

        let expected = [
            (
                "2025-01-13 00:00:00",
                "2025-01-17 00:00:00",
                Direction::Up,
                51.74,
                45.47,
            ),
            (
                "2025-01-17 00:00:00",
                "2025-02-06 00:00:00",
                Direction::Down,
                51.74,
                48.16,
            ),
            (
                "2025-02-06 00:00:00",
                "2025-02-11 00:00:00",
                Direction::Up,
                50.73,
                48.16,
            ),
            (
                "2025-02-11 00:00:00",
                "2025-02-19 00:00:00",
                Direction::Down,
                50.73,
                47.37,
            ),
        ];

        assert_eq!(c.bi_list.len(), expected.len());

        for (i, (bi, exp)) in c.bi_list.iter().zip(expected.iter()).enumerate() {
            assert_eq!(bi.start_dt(), parse_dt(exp.0), "Index {i} sdt mismatch");
            assert_eq!(bi.end_dt(), parse_dt(exp.1), "Index {i} edt mismatch");
            assert_eq!(bi.direction, exp.2, "Index {i} direction mismatch");
            assert!(
                (bi.get_high() - exp.3).abs() < 1e-4,
                "Index {i} high mismatch"
            );
            assert!(
                (bi.get_low() - exp.4).abs() < 1e-4,
                "Index {i} low mismatch"
            );
        }
    }

    /// ## 数据来源
    ///
    ///
    /// ```
    /// from czsc.connectors import cooperation as coo
    /// df = coo.stocks_daily_klines(sdt="20250101", edt="20250302")
    /// df = df[df["symbol"]=="002515.SZ"][['dt', 'symbol','open', 'close', 'high', 'low', 'vol', 'amount']]
    /// df.reset_index(drop=True, inplace=True)
    /// bars = czsc.format_standard_kline(df, "日线")
    /// c = czsc.CZSC(bars)
    /// for b in c.fx_list:
    ///     print(f"dt={fx.dt}, fx={fx.fx}")
    /// ```
    ///
    /// ```
    /// dt: 2025-01-15 00:00:00, fx: 50.73
    /// dt: 2025-01-16 00:00:00, fx: 48.94
    /// dt: 2025-01-17 00:00:00, fx: 51.74
    /// dt: 2025-01-24 00:00:00, fx: 48.27
    /// dt: 2025-01-27 00:00:00, fx: 51.74
    /// dt: 2025-02-06 00:00:00, fx: 48.16
    /// dt: 2025-02-11 00:00:00, fx: 50.73
    /// dt: 2025-02-12 00:00:00, fx: 49.5
    /// dt: 2025-02-13 00:00:00, fx: 50.51
    /// dt: 2025-02-19 00:00:00, fx: 47.37
    /// dt: 2025-02-20 00:00:00, fx: 48.83
    /// dt: 2025-02-21 00:00:00, fx: 47.48
    /// ```
    #[test]
    fn test_czsc_fx_list() {
        let bars = get_bars();
        let c = CZSC::new(bars, 50, 6);

        let expected = [
            ("2025-01-15 00:00:00", 50.73),
            ("2025-01-16 00:00:00", 48.94),
            ("2025-01-17 00:00:00", 51.74),
            ("2025-01-24 00:00:00", 48.27),
            ("2025-01-27 00:00:00", 51.74),
            ("2025-02-06 00:00:00", 48.16),
            ("2025-02-11 00:00:00", 50.73),
            ("2025-02-12 00:00:00", 49.5),
            ("2025-02-13 00:00:00", 50.51),
            ("2025-02-19 00:00:00", 47.37),
            ("2025-02-20 00:00:00", 48.83),
            ("2025-02-21 00:00:00", 47.48),
        ];

        // for fx in c.get_fx_list() {
        //     println!("dt={dt}, fx={fx}", dt = fx.dt, fx = fx.fx)
        // }

        for (i, (fx, exp)) in c.get_fx_list().iter().zip(expected.iter()).enumerate() {
            assert_eq!(fx.dt, parse_dt(exp.0), "Index {i} dt mismatch");
            assert!((fx.fx - exp.1).abs() < 1e-4, "Index {i} fx mismatch");
        }
    }
}
