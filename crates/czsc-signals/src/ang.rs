use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1, make_kline_signal_v2, pd_cut_last_label};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;
use std::collections::HashMap;

fn mean_or_nan(values: &[f64]) -> f64 {
    if values.is_empty() {
        f64::NAN
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

fn sma_valid(values: &[f64], n: usize) -> Vec<f64> {
    if n == 0 || values.len() < n {
        return vec![];
    }
    let mut out = Vec::with_capacity(values.len() - n + 1);
    let mut acc: f64 = values[..n].iter().sum();
    out.push(acc / n as f64);
    for i in n..values.len() {
        acc += values[i] - values[i - n];
        out.push(acc / n as f64);
    }
    out
}

/// adtm_up_dw_line_V230603：ADTM 能量异动多空信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}TH{th}_ADTMV230603"`
///
/// 信号逻辑：
/// 1. 计算 `N` 窗口 `up_sum` 与 `M` 窗口 `dw_sum`；
/// 2. 计算 `adtm = (up_sum - dw_sum) / max(up_sum, dw_sum)`；
/// 3. `up_sum > dw_sum` 或 `adtm > th/10` 判 `看多`；
/// 4. `up_sum < dw_sum` 或 `adtm < th/10` 判 `看空`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N30M20TH5_ADTMV230603_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N30M20TH5_ADTMV230603_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：`up_sum` 窗口，默认 `30`；
/// - `m`：`dw_sum` 窗口，默认 `20`；
/// - `th`：阈值（除以 10 使用），默认 `5`。
/// 对齐说明：与 Python `adtm_up_dw_line_V230603` 的条件优先级与阈值口径一致。
#[signal(
    category = "kline",
    name = "adtm_up_dw_line_V230603",
    template = "{freq}_D{di}N{n}M{m}TH{th}_ADTMV230603",
    opcode = "AdtmUpDwLineV230603",
    param_kind = "AdtmUpDwLineV230603"
)]
pub fn adtm_up_dw_line_v230603(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 30);
    let m = params.usize("m", 20);
    let th = params.usize("th", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}TH{}", di, n, m, th);
    let k3 = "ADTMV230603";

    if c.bars_raw.len() < di + n.max(m) + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let n_bars = get_sub_elements(&c.bars_raw, di, n);
    let m_bars = get_sub_elements(&c.bars_raw, di, m);
    if n_bars.len() < 2 || m_bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut up_sum = 0.0;
    for i in 1..n_bars.len() {
        if n_bars[i].open > n_bars[i - 1].open {
            up_sum += (n_bars[i].high - n_bars[i].open).max(n_bars[i].open - n_bars[i - 1].open);
        }
    }

    let mut dw_sum = 0.0;
    for i in 1..m_bars.len() {
        if m_bars[i].open < m_bars[i - 1].open {
            dw_sum += (m_bars[i].open - m_bars[i].low).max(m_bars[i - 1].open - m_bars[i].open);
        }
    }

    let denom = up_sum.max(dw_sum);
    let adtm = if denom > 0.0 {
        (up_sum - dw_sum) / denom
    } else {
        f64::NAN
    };

    let mut v1 = "其他";
    if up_sum > dw_sum || adtm > th as f64 / 10.0 {
        v1 = "看多";
    }
    if up_sum < dw_sum || adtm < th as f64 / 10.0 {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// amv_up_dw_line_V230603：AMV 能量多空信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}_AMV能量V230603"`
///
/// 信号逻辑：
/// 1. 计算 `N` 与 `M` 窗口成交额加权均价；
/// 2. 形成 `amv1` 与 `amv2`；
/// 3. `amv1 > amv2` 判 `看多`，否则 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N30M120_AMV能量V230603_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N30M120_AMV能量V230603_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：短窗口，默认 `30`；
/// - `m`：长窗口，默认 `120`。
/// 对齐说明：与 Python `amv_up_dw_line_V230603` 的加权均价公式一致。
#[signal(
    category = "kline",
    name = "amv_up_dw_line_V230603",
    template = "{freq}_D{di}N{n}M{m}_AMV能量V230603",
    opcode = "AmvUpDwLineV230603",
    param_kind = "AmvUpDwLineV230603"
)]
pub fn amv_up_dw_line_v230603(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 30);
    let m = params.usize("m", 120);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}", di, n, m);
    let k3 = "AMV能量V230603";
    if n > m || c.bars_raw.len() < di + m + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let n_bars = get_sub_elements(&c.bars_raw, di, n);
    let m_bars = get_sub_elements(&c.bars_raw, di, m);
    if n_bars.is_empty() || m_bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let amov1: f64 = n_bars
        .iter()
        .map(|b| b.amount * (b.open + b.close) / 2.0)
        .sum();
    let amov2: f64 = m_bars
        .iter()
        .map(|b| b.amount * (b.open + b.close) / 2.0)
        .sum();
    let vol_sum1: f64 = n_bars.iter().map(|b| b.amount).sum();
    let vol_sum2: f64 = m_bars.iter().map(|b| b.amount).sum();
    let amv1 = amov1 / vol_sum1;
    let amv2 = amov2 / vol_sum2;
    let v1 = if amv1 > amv2 { "看多" } else { "看空" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// asi_up_dw_line_V230603：ASI 多空信号
///
/// 参数模板：`"{freq}_D{di}N{n}P{p}_ASI多空V230603"`
///
/// 信号逻辑：
/// 1. 基于最近 `p` 根K线计算 SI 序列并累加得 ASI；
/// 2. 将最新 ASI 与 `p` 窗口 ASI 均值比较；
/// 3. `asi_last > asi_mean` 判 `看多`，否则 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N30P120_ASI多空V230603_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N30P120_ASI多空V230603_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：SI 公式中的常数项，默认 `30`；
/// - `p`：窗口长度，默认 `120`。
/// 对齐说明：按 Python `asi_up_dw_line_V230603` 的原始向量公式逐项对齐实现。
#[signal(
    category = "kline",
    name = "asi_up_dw_line_V230603",
    template = "{freq}_D{di}N{n}P{p}_ASI多空V230603",
    opcode = "AsiUpDwLineV230603",
    param_kind = "AsiUpDwLineV230603"
)]
pub fn asi_up_dw_line_v230603(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 30);
    let p = params.usize("p", 120);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}P{}", di, n, p);
    let k3 = "ASI多空V230603";
    if c.bars_raw.len() < di + p + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let bars = get_sub_elements(&c.bars_raw, di, p);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let len = bars.len();
    let mut close = Vec::with_capacity(len);
    let mut open = Vec::with_capacity(len);
    let mut high = Vec::with_capacity(len);
    let mut low = Vec::with_capacity(len);
    for b in bars {
        close.push(b.close);
        open.push(b.open);
        high.push(b.high);
        low.push(b.low);
    }

    let mut prev_close = Vec::with_capacity(len);
    let mut prev_low = Vec::with_capacity(len);
    let mut prev_open = Vec::with_capacity(len);
    prev_close.push(close[0]);
    prev_low.push(low[0]);
    prev_open.push(open[0]);
    for i in 1..len {
        prev_close.push(close[i - 1]);
        prev_low.push(low[i - 1]);
        prev_open.push(open[i - 1]);
    }

    let mut si = Vec::with_capacity(len);
    for i in 0..len {
        let a = (high[i] - prev_close[i]).abs();
        let b = (low[i] - prev_close[i]).abs();
        let c1 = (high[i] - prev_low[i]).abs();
        let d = (prev_close[i] - prev_open[i]).abs();
        let k = a.max(b);
        let m = (high[i] - low[i]).max(n as f64);
        let r1 = a + 0.5 * b + 0.25 * d;
        let r2 = b + 0.5 * a + 0.25 * d;
        let r3 = c1 + 0.25 * d;
        let r4 = if a >= b && a >= c1 { r1 } else { r2 };
        let r = if c1 >= a && c1 >= b { r3 } else { r4 };
        let den = r * k / m;
        if den == 0.0 {
            return make_kline_signal_v1(&k1, &k2, k3, "其他");
        }
        let si_i = 50.0 * (close[i] - c1 + (c1 - open[i]) + 0.5 * (close[i] - open[i])) / den;
        si.push(si_i);
    }

    let mut acc = 0.0;
    let mut asi = Vec::with_capacity(si.len());
    for x in si {
        acc += x;
        asi.push(acc);
    }
    let asi_last = *asi.last().unwrap_or(&f64::NAN);
    let asi_mean = mean_or_nan(&asi);
    let v1 = if asi_last > asi_mean { "看多" } else { "看空" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cmo_up_dw_line_V230605：CMO 能量阈值信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}_CMO能量V230605"`
///
/// 信号逻辑：
/// 1. 统计窗口内上涨/下跌收盘差值总和；
/// 2. 计算 `cmo = (up-dw)/(up+dw)*100`；
/// 3. `cmo > m` 判 `看多`；`cmo < -m` 判 `看空`；否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N70M30_CMO能量V230605_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N70M30_CMO能量V230605_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：统计窗口，默认 `70`；
/// - `m`：阈值，默认 `30`。
/// 对齐说明：与 Python `cmo_up_dw_line_V230605` 保持同一阈值与分支顺序。
#[signal(
    category = "kline",
    name = "cmo_up_dw_line_V230605",
    template = "{freq}_D{di}N{n}M{m}_CMO能量V230605",
    opcode = "CmoUpDwLineV230605",
    param_kind = "CmoUpDwLineV230605"
)]
pub fn cmo_up_dw_line_v230605(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 70);
    let m = params.usize("m", 30);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}", di, n, m);
    let k3 = "CMO能量V230605";
    if c.bars_raw.len() < di + n + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut up_sum = 0.0;
    let mut dw_sum = 0.0;
    for i in 1..bars.len() {
        let d = bars[i].close - bars[i - 1].close;
        if d > 0.0 {
            up_sum += d;
        } else if d < 0.0 {
            dw_sum += -d;
        }
    }
    let cmo = (up_sum - dw_sum) / (up_sum + dw_sum) * 100.0;
    let mut v1 = "其他";
    if cmo > m as f64 {
        v1 = "看多";
    }
    if cmo < -(m as f64) {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// skdj_up_dw_line_V230611：SKDJ 随机波动信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}UP{up}DW{dw}_SKDJ随机波动V230611"`
///
/// 信号逻辑：
/// 1. 先计算 `RSV(n)` 序列；
/// 2. 对 RSV 做两次 `m` 周期均值平滑；
/// 3. `dw < D < K_last` 判 `看多`；`K_last < D 且 D > up` 判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N233M89UP60DW40_SKDJ随机波动V230611_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N233M89UP60DW40_SKDJ随机波动V230611_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：RSV 窗口，默认 `233`；
/// - `m`：平滑窗口，默认 `89`；
/// - `up`：超买阈值，默认 `60`；
/// - `dw`：超卖阈值，默认 `40`。
/// 对齐说明：与 Python `skdj_up_dw_line_V230611` 的双平滑与阈值判定一致。
#[signal(
    category = "kline",
    name = "skdj_up_dw_line_V230611",
    template = "{freq}_D{di}N{n}M{m}UP{up}DW{dw}_SKDJ随机波动V230611",
    opcode = "SkdjUpDwLineV230611",
    param_kind = "SkdjUpDwLineV230611"
)]
pub fn skdj_up_dw_line_v230611(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 233);
    let m = params.usize("m", 89);
    let up = params.usize("up", 60);
    let dw = params.usize("dw", 40);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}UP{}DW{}", di, n, m, up, dw);
    let k3 = "SKDJ随机波动V230611";

    if c.bars_raw.len() < di + m * 3 + 20 || n < m {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let cache_key = format!("RSV{}", n);
    let mut old_map: HashMap<i32, f64> = HashMap::new();
    if let (Some(ids), Some(vals)) = (cache.series_ids.get(&cache_key), cache.series.get(&cache_key))
    {
        for (id, v) in ids.iter().zip(vals.iter()) {
            old_map.insert(*id, *v);
        }
    }

    let mut rsv_series = Vec::with_capacity(c.bars_raw.len());
    let mut rsv_ids = Vec::with_capacity(c.bars_raw.len());
    for (i, bar) in c.bars_raw.iter().enumerate() {
        rsv_ids.push(bar.id);
        // 对齐 Python：历史 bar 的 RSV 只计算一次；同 dt 延伸时仅最后一根会重算。
        if i + 1 < c.bars_raw.len()
            && let Some(v) = old_map.get(&bar.id) {
                rsv_series.push(*v);
                continue;
            }
        let win = if i < n {
            &c.bars_raw[..=i]
        } else {
            // 对齐 Python 原始实现：i>=n 分支直接使用 di=i 取子序列（保留其历史行为）
            get_sub_elements(&c.bars_raw, i, n)
        };
        let v = if win.is_empty() {
            f64::NAN
        } else {
            let min_low = win.iter().fold(f64::INFINITY, |acc, b| acc.min(b.low));
            let max_high = win.iter().fold(f64::NEG_INFINITY, |acc, b| acc.max(b.high));
            let den = max_high - min_low;
            if den == 0.0 {
                f64::NAN
            } else {
                (bar.close - min_low) / den * 100.0
            }
        };
        rsv_series.push(v);
    }
    cache.series.insert(cache_key.clone(), rsv_series.clone());
    cache.series_ids.insert(cache_key, rsv_ids);

    let bars = get_sub_elements(&c.bars_raw, di, m * 3 + 20);
    if bars.len() < m * 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let start = c.bars_raw.len() - di + 1 - bars.len();
    let end = start + bars.len();
    let rsv = &rsv_series[start..end];
    let ma_rsv = sma_valid(rsv, m);
    let k = sma_valid(&ma_rsv, m);
    if k.len() < m {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let d = mean_or_nan(&k[k.len() - m..]);
    let k_last = *k.last().unwrap_or(&f64::NAN);

    let mut v1 = "其他";
    if (dw as f64) < d && d < k_last {
        v1 = "看多";
    }
    if k_last < d && d > up as f64 {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bias_up_dw_line_V230618：BIAS 三周期共振信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}P{p}TH1{th1}TH2{th2}TH3{th3}_BIAS乖离率V230618"`
///
/// 信号逻辑：
/// 1. 分别计算 `n/m/p` 三个窗口的均线乖离率；
/// 2. 三个乖离率同时超过正阈值判 `看多`；
/// 3. 三个乖离率同时低于负阈值判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N6M12P24TH11TH23TH35_BIAS乖离率V230618_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N6M12P24TH11TH23TH35_BIAS乖离率V230618_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n/m/p`：三组均线窗口，默认 `6/12/24`；
/// - `th1/th2/th3`：对应窗口阈值，默认 `1/3/5`。
/// 对齐说明：与 Python `bias_up_dw_line_V230618` 的三阈值共振条件一致。
#[signal(
    category = "kline",
    name = "bias_up_dw_line_V230618",
    template = "{freq}_D{di}N{n}M{m}P{p}TH1{th1}TH2{th2}TH3{th3}_BIAS乖离率V230618",
    opcode = "BiasUpDwLineV230618",
    param_kind = "BiasUpDwLineV230618"
)]
pub fn bias_up_dw_line_v230618(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 6);
    let m = params.usize("m", 12);
    let p = params.usize("p", 24);
    let th1 = params.usize("th1", 1);
    let th2 = params.usize("th2", 3);
    let th3 = params.usize("th3", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}P{}TH1{}TH2{}TH3{}", di, n, m, p, th1, th2, th3);
    let k3 = "BIAS乖离率V230618";
    if c.bars_raw.len() < di + n.max(m).max(p) {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let b1 = get_sub_elements(&c.bars_raw, di, n);
    let b2 = get_sub_elements(&c.bars_raw, di, m);
    let b3 = get_sub_elements(&c.bars_raw, di, p);
    if b1.is_empty() || b2.is_empty() || b3.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let ma1 = mean_or_nan(&b1.iter().map(|x| x.close).collect::<Vec<_>>());
    let ma2 = mean_or_nan(&b2.iter().map(|x| x.close).collect::<Vec<_>>());
    let ma3 = mean_or_nan(&b3.iter().map(|x| x.close).collect::<Vec<_>>());
    let bias1 = (b1[b1.len() - 1].close - ma1) / ma1 * 100.0;
    let bias2 = (b2[b2.len() - 1].close - ma2) / ma2 * 100.0;
    let bias3 = (b3[b3.len() - 1].close - ma3) / ma3 * 100.0;

    let mut v1 = "其他";
    if bias1 > th1 as f64 && bias2 > th2 as f64 && bias3 > th3 as f64 {
        v1 = "看多";
    }
    if bias1 < -(th1 as f64) && bias2 < -(th2 as f64) && bias3 < -(th3 as f64) {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// dema_up_dw_line_V230605：DEMA 短线趋势信号
///
/// 参数模板：`"{freq}_D{di}N{n}_DEMA短线趋势V230605"`
///
/// 信号逻辑：
/// 1. 用 `n` 与 `2n` 窗口均值构造 `dema = 2*MA(n)-MA(2n)`；
/// 2. 最新收盘价高于 dema 判 `看多`，否则判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N5_DEMA短线趋势V230605_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N5_DEMA短线趋势V230605_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：短窗口，默认 `5`。
/// 对齐说明：按 Python `dema_up_dw_line_V230605` 的近似 DEMA 口径实现。
#[signal(
    category = "kline",
    name = "dema_up_dw_line_V230605",
    template = "{freq}_D{di}N{n}_DEMA短线趋势V230605",
    opcode = "DemaUpDwLineV230605",
    param_kind = "DemaUpDwLineV230605"
)]
pub fn dema_up_dw_line_v230605(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}", di, n);
    let k3 = "DEMA短线趋势V230605";
    if c.bars_raw.len() < di + 2 * n + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let short_bars = get_sub_elements(&c.bars_raw, di, n);
    let long_bars = get_sub_elements(&c.bars_raw, di, n * 2);
    if short_bars.is_empty() || long_bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let dema = 2.0 * mean_or_nan(&short_bars.iter().map(|x| x.close).collect::<Vec<_>>())
        - mean_or_nan(&long_bars.iter().map(|x| x.close).collect::<Vec<_>>());
    let v1 = if short_bars[short_bars.len() - 1].close > dema {
        "看多"
    } else {
        "看空"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// demakder_up_dw_line_V230605：DEMAKER 价格趋势信号
///
/// 参数模板：`"{freq}_D{di}N{n}TH{th}TL{tl}_DEMAKER价格趋势V230605"`
///
/// 信号逻辑：
/// 1. 统计窗口内上涨高点均值 `demax` 与下跌低点均值 `demin`；
/// 2. 计算 `demaker = demax / (demax + demin)`；
/// 3. `demaker > th/10` 判 `看多`，`demaker < tl/10` 判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N105TH5TL5_DEMAKER价格趋势V230605_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N105TH5TL5_DEMAKER价格趋势V230605_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：统计窗口，默认 `105`；
/// - `th/tl`：上下阈值（除以 10 使用），默认 `5/5`。
/// 对齐说明：保持 Python `demakder_up_dw_line_V230605` 对空样本返回 NaN 的行为。
#[signal(
    category = "kline",
    name = "demakder_up_dw_line_V230605",
    template = "{freq}_D{di}N{n}TH{th}TL{tl}_DEMAKER价格趋势V230605",
    opcode = "DemakderUpDwLineV230605",
    param_kind = "DemakderUpDwLineV230605"
)]
pub fn demakder_up_dw_line_v230605(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 105);
    let th = params.usize("th", 5);
    let tl = params.usize("tl", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}TH{}TL{}", di, n, th, tl);
    let k3 = "DEMAKER价格趋势V230605";
    if c.bars_raw.len() < di + n + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut demax_items = Vec::new();
    let mut demin_items = Vec::new();
    for i in 1..bars.len() {
        let dh = bars[i].high - bars[i - 1].high;
        if dh > 0.0 {
            demax_items.push(dh);
        }
        let dl = bars[i - 1].low - bars[i].low;
        if dl > 0.0 {
            demin_items.push(dl);
        }
    }
    let demax = mean_or_nan(&demax_items);
    let demin = mean_or_nan(&demin_items);
    let demaker = demax / (demax + demin);

    let mut v1 = "其他";
    if demaker > th as f64 / 10.0 {
        v1 = "看多";
    }
    if demaker < tl as f64 / 10.0 {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// emv_up_dw_line_V230605：EMV 简易波动多空信号
///
/// 参数模板：`"{freq}_D{di}_EMV简易波动V230605"`
///
/// 信号逻辑：
/// 1. 取最近两根K线计算中点位移；
/// 2. 以成交量/振幅形成箱体比率；
/// 3. `emv > 0` 判 `看多`，否则判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1_EMV简易波动V230605_看多_任意_任意_0')`
/// - `Signal('60分钟_D1_EMV简易波动V230605_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `emv_up_dw_line_V230605` 的两根K线近似 EMV 计算一致。
#[signal(
    category = "kline",
    name = "emv_up_dw_line_V230605",
    template = "{freq}_D{di}_EMV简易波动V230605",
    opcode = "EmvUpDwLineV230605",
    param_kind = "EmvUpDwLineV230605"
)]
pub fn emv_up_dw_line_v230605(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}", di);
    let k3 = "EMV简易波动V230605";
    if c.bars_raw.len() < di + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, 2);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let mid_pt_move = (bars[1].high + bars[1].low) / 2.0 - (bars[0].high + bars[0].low) / 2.0;
    let box_ratio = bars[1].vol / (bars[1].high - bars[1].low + 1e-9);
    let emv = mid_pt_move / box_ratio;
    let v1 = if emv > 0.0 { "看多" } else { "看空" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// er_up_dw_line_V230604：ER 价格动量分层信号
///
/// 参数模板：`"{freq}_D{di}W{w}N{n}_ER价格动量V230604"`
///
/// 信号逻辑：
/// 1. 以 `W` 窗口均价构造 bull/bear power 因子；
/// 2. 仅保留与末值同号的因子子序列；
/// 3. 末值正负给出 `均线上方/均线下方`；
/// 4. 对同号子序列做 `N` 分箱输出 `第x层`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W60N10_ER价格动量V230604_均线上方_第3层_任意_0')`
/// - `Signal('60分钟_D1W60N10_ER价格动量V230604_均线下方_第8层_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `w`：均价窗口，默认 `60`；
/// - `n`：分层数量，默认 `10`。
/// 对齐说明：与 Python `er_up_dw_line_V230604` 的同号过滤与分层规则一致。
#[signal(
    category = "kline",
    name = "er_up_dw_line_V230604",
    template = "{freq}_D{di}W{w}N{n}_ER价格动量V230604",
    opcode = "ErUpDwLineV230604",
    param_kind = "ErUpDwLineV230604"
)]
pub fn er_up_dw_line_v230604(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 60);
    let n = params.usize("n", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}N{}", di, w, n);
    let k3 = "ER价格动量V230604";

    let cache_key = format!("ER{}", w);
    let mut old_map: HashMap<i32, f64> = HashMap::new();
    if let (Some(ids), Some(vals)) = (
        cache.series_ids.get(&cache_key),
        cache.series.get(&cache_key),
    ) {
        for (id, v) in ids.iter().zip(vals.iter()) {
            old_map.insert(*id, *v);
        }
    }

    let mut out = Vec::with_capacity(c.bars_raw.len());
    let mut out_ids = Vec::with_capacity(c.bars_raw.len());
    for (i, bar) in c.bars_raw.iter().enumerate() {
        out_ids.push(bar.id);
        let is_last_bar = i + 1 == c.bars_raw.len();
        if is_last_bar {
            // 对齐 Python 流式语义：最后一根未完成高周期 bar 在基准级别持续推进时，
            // high/low 会变化，ER 末值需要随之刷新，不能仅按 bar id 复用旧缓存。
        } else if let Some(v) = old_map.get(&bar.id) {
            out.push(*v);
            continue;
        }
        // 对齐 Python: _bars = c.bars_raw[i-w:i]（i 为 1-based）
        // 注意这里必须保留 Python 负索引切片语义：
        // - 当 len(c.bars_raw) < w 时，会返回一个递增前缀而不是空窗口；
        // - 当 len(c.bars_raw) > w 且 start > end 时，结果为空切片。
        let i1 = i + 1;
        let len = c.bars_raw.len();
        let raw_start = i1 as isize - w as isize;
        let start = if raw_start < 0 {
            (len as isize + raw_start).max(0) as usize
        } else {
            raw_start as usize
        };
        let win = if start >= i1 {
            &c.bars_raw[0..0]
        } else {
            &c.bars_raw[start..i1]
        };
        let ma = mean_or_nan(&win.iter().map(|x| x.close).collect::<Vec<_>>());
        let v = if bar.high > ma {
            bar.high - ma
        } else {
            bar.low - ma
        };
        out.push(v);
    }
    cache.series.insert(cache_key.clone(), out.clone());
    cache.series_ids.insert(cache_key, out_ids);

    // 对齐 Python：即使样本不足返回“其他”，也要先完成历史 bar 的 ER 缓存写入。
    if c.bars_raw.len() < di + w + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let bars = get_sub_elements(&c.bars_raw, di, w * 10);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let start = c.bars_raw.len() - di + 1 - bars.len();
    let end = start + bars.len();
    let mut factors = out[start..end].to_vec();
    let last = *factors.last().unwrap_or(&f64::NAN);
    if !last.is_finite() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    factors.retain(|x| x.is_finite() && x * last > 0.0);
    if factors.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let v1 = if last > 0.0 { "均线上方" } else { "均线下方" };
    let v2 = match pd_cut_last_label(&factors, n) {
        Some(q) => format!("第{}层", q),
        None => "其他".to_string(),
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}
