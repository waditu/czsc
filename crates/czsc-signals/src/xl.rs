use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1, make_kline_signal_v2};
use crate::utils::ta::update_ma_cache;
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        f64::NAN
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

fn std_pop(values: &[f64]) -> f64 {
    let m = mean(values);
    if !m.is_finite() || values.is_empty() {
        return f64::NAN;
    }
    let var = values.iter().map(|x| (x - m).powi(2)).sum::<f64>() / values.len() as f64;
    var.sqrt()
}

fn quantile_midpoint(values: &[f64], q: f64) -> f64 {
    if values.is_empty() {
        return f64::NAN;
    }
    let mut v = values.to_vec();
    v.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let n = v.len();
    let pos = q * (n.saturating_sub(1)) as f64;
    let lo = pos.floor() as usize;
    let hi = pos.ceil() as usize;
    if lo == hi {
        v[lo]
    } else {
        (v[lo] + v[hi]) / 2.0
    }
}

fn check_szx(bar: &RawBar, th: i32) -> bool {
    if bar.close == bar.open && bar.high != bar.low {
        return true;
    }
    bar.close != bar.open && (bar.high - bar.low) / (bar.close - bar.open).abs() > th as f64
}

fn trend_count(cache1: &[f64], cache2: &[f64]) -> i32 {
    let mut num = 0;
    if cache1.len() != cache2.len() || cache1.len() < 2 {
        return num;
    }
    for i in 0..cache1.len() - 1 {
        let b1 = cache1[i] < cache2[i];
        let b2 = cache1[i + 1] < cache2[i + 1];
        if b2 && b1 != b2 {
            num = 1;
        } else if b2 && b1 == b2 {
            num += 1;
        }

        let b3 = cache1[i] > cache2[i];
        let b4 = cache1[i + 1] > cache2[i + 1];
        if b4 && b3 != b4 {
            num = 1;
        } else if b4 && b3 == b4 {
            num += 1;
        }
        if num >= 10 {
            num = 10;
        }
    }
    num
}

/// xl_bar_position_V240328：相对高低位置识别信号
///
/// 参数模板：`"{freq}_N{n}_BS辅助V240328"`
///
/// 信号逻辑：
/// 1. 计算最近 `3n` 根 `(close-EMA(n))/EMA(n)` 偏离度；
/// 2. 若最新值低于 30% 分位数判 `相对低点`；
/// 3. 若最新值高于 70% 分位数判 `相对高点`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N10_BS辅助V240328_相对低点_任意_任意_0')`
/// - `Signal('60分钟_N10_BS辅助V240328_相对高点_任意_任意_0')`
///
/// 参数说明：
/// - `n`：EMA 周期，默认 `10`。
/// 对齐说明：与 Python `xl_bar_position_V240328` 的分位口径一致（midpoint）。
#[signal(
    category = "kline",
    name = "xl_bar_position_V240328",
    template = "{freq}_N{n}_BS辅助V240328",
    opcode = "XlBarPositionV240328",
    param_kind = "XlBarPositionV240328"
)]
pub fn xl_bar_position_v240328(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("N{}", n);
    let k3 = "BS辅助V240328";
    if c.bars_raw.len() < n + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, n + 2 * n);
    let ema_key = format!("EMA#{}", n);
    update_ma_cache(c, &ema_key, "EMA", n, cache);
    let ema = match cache.series.get(&ema_key) {
        Some(v) => v,
        None => return make_kline_signal_v1(&k1, &k2, k3, "其他"),
    };
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let start = c.bars_raw.len() - bars.len();
    let mut nor = Vec::with_capacity(bars.len());
    for (i, b) in bars.iter().enumerate() {
        let e = ema[start + i];
        nor.push((b.close - e) / e);
    }
    let q30 = quantile_midpoint(&nor, 0.3);
    let q70 = quantile_midpoint(&nor, 0.7);
    let last = *nor.last().unwrap_or(&f64::NAN);
    let v1 = if last < q30 {
        "相对低点"
    } else if last > q70 {
        "相对高点"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// xl_bar_trend_V240329：十字孕线反转信号
///
/// 参数模板：`"{freq}_N{n}M{m}_十字线反转V240329"`
///
/// 信号逻辑：
/// 1. 判断最新K线是否十字线（`check_szx`）；
/// 2. 前一根为长阴线且满足阈值判 `底部十字孕线`；
/// 3. 前一根为长阳线且满足阈值判 `顶部十字孕线`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N10M5_十字线反转V240329_底部十字孕线_其他_任意_0')`
/// - `Signal('60分钟_N10M5_十字线反转V240329_顶部十字孕线_其他_任意_0')`
///
/// 参数说明：
/// - `n`：十字线阈值参数，默认 `10`；
/// - `m`：实体比例阈值，默认 `5`。
/// 对齐说明：与 Python `xl_bar_trend_V240329` 的 `check_szx` 口径一致。
#[signal(
    category = "kline",
    name = "xl_bar_trend_V240329",
    template = "{freq}_N{n}M{m}_十字线反转V240329",
    opcode = "XlBarTrendV240329",
    param_kind = "XlBarTrendV240329"
)]
pub fn xl_bar_trend_v240329(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 10) as i32;
    let m = params.usize("m", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("N{}M{}", n, m);
    let k3 = "十字线反转V240329";
    if c.bars_raw.len() < n as usize + 1 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, 2);
    if bars.len() < 2 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let bar1 = &bars[0];
    let bar2 = &bars[1];
    let mut v1 = "其他";
    if check_szx(bar2, n)
        && bar1.close < bar1.open
        && (bar1.open - bar1.close) / (bar1.high - bar1.low) * 10.0 >= m as f64
    {
        v1 = "底部十字孕线";
    }
    if check_szx(bar2, n)
        && bar1.close > bar1.open
        && (bar1.close - bar1.open) / (bar1.high - bar1.low) * 10.0 >= m as f64
    {
        v1 = "顶部十字孕线";
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, "其他")
}

/// xl_bar_trend_V240330：双均线过滤信号
///
/// 参数模板：`"{freq}_N{n}M{m}#{ma_type}_双均线过滤V240330"`
///
/// 信号逻辑：
/// 1. 计算 `MA(n)` 与 `MA(m)`；
/// 2. 根据两线相对位置输出 `看多/看空`；
/// 3. 统计连续状态次数并输出 `第xx次`（最大 10）。
///
/// 信号列表示例：
/// - `Signal('60分钟_N5M21#SMA_双均线过滤V240330_看多_第03次_任意_0')`
/// - `Signal('60分钟_N5M21#SMA_双均线过滤V240330_看空_第06次_任意_0')`
///
/// 参数说明：
/// - `n/m`：短长均线周期，默认 `5/21`；
/// - `ma_type`：均线类型，默认 `SMA`。
/// 对齐说明：与 Python `xl_bar_trend_V240330` 的次数计数逻辑一致。
#[signal(
    category = "kline",
    name = "xl_bar_trend_V240330",
    template = "{freq}_N{n}M{m}#{ma_type}_双均线过滤V240330",
    opcode = "XlBarTrendV240330",
    param_kind = "XlBarTrendV240330"
)]
pub fn xl_bar_trend_v240330(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 5);
    let m = params.usize("m", 21);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let k1 = c.freq.to_string();
    let k2 = format!("N{}M{}#{}", n, m, ma_type);
    let k3 = "双均线过滤V240330";
    if c.bars_raw.len() < m + 1 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let key1 = format!("{}#{}", ma_type, n);
    let key2 = format!("{}#{}", ma_type, m);
    update_ma_cache(c, &key1, &ma_type, n, cache);
    update_ma_cache(c, &key2, &ma_type, m, cache);
    let bars = get_sub_elements(&c.bars_raw, 1, m + 1);
    let start = c.bars_raw.len() - bars.len();
    let ma1 = match cache.series.get(&key1) {
        Some(v) => v,
        None => return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他"),
    };
    let ma2 = match cache.series.get(&key2) {
        Some(v) => v,
        None => return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他"),
    };
    let mut cache1 = Vec::with_capacity(bars.len());
    let mut cache2 = Vec::with_capacity(bars.len());
    for i in 0..bars.len() {
        cache1.push(ma1[start + i]);
        cache2.push(ma2[start + i]);
    }
    let num = trend_count(&cache1, &cache2).min(10);
    let v2 = format!("第{:02}次", num);
    let v1 = if cache1[cache1.len() - 1] > cache2[cache2.len() - 1] {
        "看多"
    } else if cache1[cache1.len() - 1] < cache2[cache2.len() - 1] {
        "看空"
    } else {
        "其他"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}

/// xl_bar_trend_V240331：通道突破信号
///
/// 参数模板：`"{freq}_N{n}_突破信号V240331"`
///
/// 信号逻辑：
/// 1. 若最新高点突破前 `n` 根最高价，判 `做多`；
/// 2. 若最新低点跌破前 `n` 根最低价，判 `做空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N20_突破信号V240331_做多_任意_任意_0')`
/// - `Signal('60分钟_N20_突破信号V240331_做空_任意_任意_0')`
///
/// 参数说明：
/// - `n`：通道窗口，默认 `20`。
/// 对齐说明：与 Python `xl_bar_trend_V240331` 的突破判定一致。
#[signal(
    category = "kline",
    name = "xl_bar_trend_V240331",
    template = "{freq}_N{n}_突破信号V240331",
    opcode = "XlBarTrendV240331",
    param_kind = "XlBarTrendV240331"
)]
pub fn xl_bar_trend_v240331(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 20);
    let k1 = c.freq.to_string();
    let k2 = format!("N{}", n);
    let k3 = "突破信号V240331";
    if c.bars_raw.len() < n + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, n + 1);
    let hh = bars[..bars.len() - 1]
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let ll = bars[..bars.len() - 1]
        .iter()
        .map(|x| x.low)
        .fold(f64::INFINITY, f64::min);
    let last = &bars[bars.len() - 1];
    let v1 = if last.high >= hh {
        "做多"
    } else if last.low <= ll {
        "做空"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// xl_bar_basis_V240412：长蜡烛形态信号
///
/// 参数模板：`"{freq}_N{n}#TH{th}_形态V240412"`
///
/// 信号逻辑：
/// 1. 统计前 `n` 根实体长度均值与标准差；
/// 2. 当前实体超过 `mean + th*std` 时识别长蜡烛；
/// 3. 按实体方向输出 `看涨长蜡烛/看跌长蜡烛`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N10#TH3_形态V240412_看涨长蜡烛_任意_任意_0')`
/// - `Signal('60分钟_N10#TH3_形态V240412_看跌长蜡烛_任意_任意_0')`
///
/// 参数说明：
/// - `n`：统计窗口，默认 `10`；
/// - `th`：标准差倍数，默认 `3`。
/// 对齐说明：与 Python `xl_bar_basis_V240412` 的阈值公式一致。
#[signal(
    category = "kline",
    name = "xl_bar_basis_V240412",
    template = "{freq}_N{n}#TH{th}_形态V240412",
    opcode = "XlBarBasisV240412",
    param_kind = "XlBarBasisV240412"
)]
pub fn xl_bar_basis_v240412(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 10);
    let th = params.usize("th", 3);
    let k1 = c.freq.to_string();
    let k2 = format!("N{}#TH{}", n, th);
    let k3 = "形态V240412";
    if c.bars_raw.len() < n + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, n + 1);
    let lens: Vec<f64> = bars[..bars.len() - 1]
        .iter()
        .map(|x| (x.close - x.open).abs())
        .collect();
    let bar_solid_th = mean(&lens) + th as f64 * std_pop(&lens);
    let bar_solid = bars[bars.len() - 1].close - bars[bars.len() - 1].open;
    let v1 = if bar_solid > 0.0 && bar_solid > bar_solid_th {
        "看涨长蜡烛"
    } else if bar_solid < 0.0 && bar_solid.abs() > bar_solid_th {
        "看跌长蜡烛"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// xl_bar_basis_V240411：吞没形态信号
///
/// 参数模板：`"{freq}_N{n}_形态V240411"`
///
/// 信号逻辑：
/// 1. 最近两根K线构成看涨吞没时输出 `看涨吞没`；
/// 2. 构成看跌吞没时输出 `看跌吞没`；
/// 3. 否则输出 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N2_形态V240411_看涨吞没_任意_任意_0')`
/// - `Signal('60分钟_N2_形态V240411_看跌吞没_任意_任意_0')`
///
/// 参数说明：
/// - `n`：最小窗口参数，默认 `2`。
/// 对齐说明：与 Python `xl_bar_basis_V240411` 的吞没条件一致。
#[signal(
    category = "kline",
    name = "xl_bar_basis_V240411",
    template = "{freq}_N{n}_形态V240411",
    opcode = "XlBarBasisV240411",
    param_kind = "XlBarBasisV240411"
)]
pub fn xl_bar_basis_v240411(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 2);
    let k1 = c.freq.to_string();
    let k2 = format!("N{}", n);
    let k3 = "形态V240411";
    if c.bars_raw.len() < n + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, 2);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bar1 = &bars[0];
    let bar2 = &bars[1];
    let v1 = if (bar1.open > bar1.close) && (bar2.close > bar1.high) && (bar2.open <= bar1.low) {
        "看涨吞没"
    } else if (bar1.open < bar1.close) && (bar2.open >= bar1.high) && (bar2.close < bar1.low) {
        "看跌吞没"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// xl_bar_trend_V240623：通道突破连续信号
///
/// 参数模板：`"{freq}_N{n}通道_突破信号V240623"`
///
/// 信号逻辑：
/// 1. 使用倒数第二根K线判断是否突破前 `n` 通道；
/// 2. 突破上轨给 `做多`，且最新再创新高给 `连续2次上涨`；
/// 3. 跌破下轨给 `做空`，且最新再创新低给 `连续2次下跌`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N20通道_突破信号V240623_做多_连续2次上涨_任意_0')`
/// - `Signal('60分钟_N20通道_突破信号V240623_做空_连续2次下跌_任意_0')`
///
/// 参数说明：
/// - `n`：通道窗口，默认 `20`。
/// 对齐说明：与 Python `xl_bar_trend_V240623` 的“倒二突破 + 最新确认”口径一致。
#[signal(
    category = "kline",
    name = "xl_bar_trend_V240623",
    template = "{freq}_N{n}通道_突破信号V240623",
    opcode = "XlBarTrendV240623",
    param_kind = "XlBarTrendV240623"
)]
pub fn xl_bar_trend_v240623(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 20);
    let k1 = c.freq.to_string();
    let k2 = format!("N{}通道", n);
    let k3 = "突破信号V240623";
    let bars = get_sub_elements(&c.bars_raw, 1, n + 1);
    if bars.len() < n + 1 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }
    let hh = bars[..bars.len() - 2]
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let ll = bars[..bars.len() - 2]
        .iter()
        .map(|x| x.low)
        .fold(f64::INFINITY, f64::min);
    let prev = &bars[bars.len() - 2];
    let last = &bars[bars.len() - 1];
    let mut v1 = "其他";
    let mut v2 = "任意";
    if prev.high >= hh {
        v1 = "做多";
        if last.high > prev.high {
            v2 = "连续2次上涨";
        }
    } else if prev.low <= ll {
        v1 = "做空";
        if last.low < prev.low {
            v2 = "连续2次下跌";
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}
