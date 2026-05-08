use super::czsc_signals::parse_signals_config;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::market::Market;
use czsc_trader::signals::czsc_signals::CzscSignals;
use czsc_trader::signals::sig_parse::get_signals_freqs;
use czsc_utils::bar_generator::BarGenerator;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use std::str::FromStr;

/// 批量生成 CZSC 信号
///
/// 参数:
///   bars: 基础周期 K 线列表
///   signals_config: 信号配置列表
///   sdt: 信号开始计算日期，格式 "YYYYMMDD" 或 "YYYY-MM-DD"
///   init_n: 预热 K 线数量
///   df: 是否返回 DataFrame（默认 False 返回 list[dict]）
#[pyfunction]
#[pyo3(signature = (bars, signals_config, sdt="20170101", init_n=500, df=false))]
pub fn generate_czsc_signals(
    py: Python,
    bars: Vec<RawBar>,
    signals_config: &Bound<PyList>,
    sdt: &str,
    init_n: usize,
    df: bool,
) -> PyResult<PyObject> {
    if bars.is_empty() {
        return Err(PyValueError::new_err("bars 不能为空"));
    }

    let configs = parse_signals_config(signals_config)?;

    // 提取所有信号需要的周期
    let freq_strs = get_signals_freqs(&configs);
    let freqs: Vec<Freq> = freq_strs
        .iter()
        .filter_map(|s| Freq::from_str(s).ok())
        .collect();

    // 获取基准周期
    let base_freq = bars[0].freq;

    // 创建 BarGenerator
    let bg = BarGenerator::new(base_freq, freqs, 1000, Market::Default)
        .map_err(|e| PyValueError::new_err(format!("创建 BarGenerator 失败: {e}")))?;

    // 计算分割点：取 sdt 日期和 init_n 的较大者
    let sdt_normalized = normalize_sdt(sdt);
    let mut split_idx = init_n.min(bars.len());

    // 按 sdt 日期查找分割点
    for (i, bar) in bars.iter().enumerate() {
        let bar_date = bar.dt.format("%Y%m%d").to_string();
        if bar_date >= sdt_normalized && i >= init_n {
            split_idx = i;
            break;
        }
    }
    // 确保不超出范围
    if split_idx >= bars.len() {
        split_idx = bars.len().saturating_sub(1);
    }

    let (bars_left, bars_right) = bars.split_at(split_idx);

    // 创建 CzscSignals 并预热
    let symbol = bars[0].symbol.to_string();
    let mut signals = CzscSignals::new(symbol, bg);

    // 预热
    for bar in bars_left {
        signals.bg.update_bar(bar).ok();
    }

    // prime_signals 用最后一根预热 bar
    if let Some(last_warmup) = bars_left.last() {
        signals.prime_signals(last_warmup, &configs);
    }

    // 计算信号
    let mut records: Vec<PyObject> = Vec::with_capacity(bars_right.len());
    for bar in bars_right {
        signals.update_signals(bar, &configs);
        let dict = PyDict::new(py);
        for (k, v) in &signals.s {
            dict.set_item(k, v)?;
        }
        records.push(dict.into_any().unbind());
    }

    if df {
        // 返回 DataFrame
        let pandas = py.import("pandas")?;
        let df_obj = pandas.call_method1("DataFrame", (records,))?;
        Ok(df_obj.into_any().unbind())
    } else {
        let list = PyList::new(py, &records)?;
        Ok(list.into_any().unbind())
    }
}

/// 将 sdt 标准化为 "YYYYMMDD" 格式
fn normalize_sdt(sdt: &str) -> String {
    sdt.replace('-', "")
}
