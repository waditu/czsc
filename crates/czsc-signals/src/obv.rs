use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{bar_index_map, get_sub_elements, make_kline_signal_v1};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

fn signed_vol(bar: &czsc_core::objects::bar::RawBar) -> f64 {
    if bar.close > bar.open {
        bar.vol
    } else {
        -bar.vol
    }
}

/// 更新 OBV 缓存，保持与 Python `bar.cache["OBV"]` 的累计语义一致。
fn update_obv_cache(c: &CZSC, cache: &mut TaCache) {
    let cache_key = "OBV";
    let now_len = c.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let bar_ids: Vec<i32> = c.bars_raw.iter().map(|b| b.id).collect();

    let mut need_init = !cache.series.contains_key(cache_key);
    if !need_init {
        if let Some(existing_ids) = cache.series_ids.get(cache_key) {
            if now_len < 2 || existing_ids.is_empty() {
                need_init = true;
            } else {
                let penultimate_id = bar_ids[now_len - 2];
                need_init = !existing_ids.contains(&penultimate_id);
            }
        } else {
            need_init = true;
        }
    }

    if need_init {
        let mut obv = vec![0.0; now_len];
        obv[0] = signed_vol(&c.bars_raw[0]);
        for i in 1..now_len {
            obv[i] = obv[i - 1] + signed_vol(&c.bars_raw[i]);
        }
        cache.series.insert(cache_key.to_string(), obv);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.series.get(cache_key).unwrap();
    let existing_ids = cache.series_ids.get(cache_key).unwrap();
    let mut old_map = std::collections::HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, existing[i]);
    }

    let mut obv = Vec::with_capacity(now_len);
    for id in &bar_ids {
        obv.push(*old_map.get(id).unwrap_or(&f64::NAN));
    }

    if let Some(start) = obv.iter().position(|x| x.is_nan()) {
        if start == 0 {
            obv[0] = signed_vol(&c.bars_raw[0]);
            for i in 1..now_len {
                obv[i] = obv[i - 1] + signed_vol(&c.bars_raw[i]);
            }
        } else {
            for i in start..now_len {
                obv[i] = obv[i - 1] + signed_vol(&c.bars_raw[i]);
            }
        }
    }

    if now_len == 1 {
        obv[0] = signed_vol(&c.bars_raw[0]);
    } else {
        // 对齐 Python 多频流式语义：最后一根未完成 bar 的 open/close/vol 会持续更新，
        // 即使 bar id 不变，也必须基于前一根已确认 bar 的 OBV 重新计算当前值。
        obv[now_len - 1] = obv[now_len - 2] + signed_vol(&c.bars_raw[now_len - 1]);
    }

    cache.series.insert(cache_key.to_string(), obv);
    cache.series_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

/// 对齐 TA-Lib `EMA`：前 `n-1` 个位置为 NaN，第 `n` 个位置用前 `n` 个值的 SMA 初始化。
fn calc_ema_talib_style(series: &[f64], n: usize) -> Vec<f64> {
    let mut out = vec![f64::NAN; series.len()];
    if n == 0 || series.len() < n {
        return out;
    }
    let alpha = 2.0 / (n as f64 + 1.0);
    let seed = series[..n].iter().sum::<f64>() / n as f64;
    out[n - 1] = seed;
    for i in n..series.len() {
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1];
    }
    out
}

/// 对含“前导 NaN”的序列计算 TA-Lib 风格 EMA。
fn calc_ema_talib_skip_leading_nan(series: &[f64], n: usize) -> Vec<f64> {
    let mut out = vec![f64::NAN; series.len()];
    let Some(start) = series.iter().position(|x| x.is_finite()) else {
        return out;
    };
    let tail = &series[start..];
    let ema_tail = calc_ema_talib_style(tail, n);
    for (i, v) in ema_tail.iter().enumerate() {
        out[start + i] = *v;
    }
    out
}

/// obvm_line_V230610：OBV 双 EMA 能量信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}_OBV能量V230610"`
///
/// 信号逻辑：
/// 1. 计算 OBV 累计量序列（阳线加量、阴线减量）；
/// 2. 分别计算 OBV 的短期 EMA(`n`) 与长期 EMA(`m`)；
/// 3. 短期 EMA 大于长期 EMA 判 `看多`，否则判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N10M30_OBV能量V230610_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N10M30_OBV能量V230610_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：短期 EMA 周期，默认 `10`；
/// - `m`：长期 EMA 周期，默认 `30`。
/// 对齐说明：OBV 构造方式与 Python `obvm_line_V230610` 一致（按 K 线涨跌符号加减成交量）。
#[signal(
    category = "kline",
    name = "obvm_line_V230610",
    template = "{freq}_D{di}N{n}M{m}_OBV能量V230610",
    opcode = "ObvmLineV230610",
    param_kind = "ObvmLineV230610"
)]
pub fn obvm_line_v230610(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 10);
    let m = params.usize("m", 30);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}", di, n, m);
    let k3 = "OBV能量V230610";
    let v1_default = "其他";

    if c.bars_raw.len() < di + n.max(m) + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }

    update_obv_cache(c, cache);
    let Some(obv_series) = cache.series.get("OBV") else {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    };
    let id_map = bar_index_map(c);
    let bars = get_sub_elements(&c.bars_raw, di, n.max(m) + 10);
    let mut obv_seq = Vec::with_capacity(bars.len());
    for b in bars {
        if let Some(i) = id_map.get(&b.id).copied()
            && i < obv_series.len() {
                obv_seq.push(obv_series[i]);
            }
    }
    if obv_seq.len() < n.max(m) {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }

    let ema_n = calc_ema_talib_style(&obv_seq, n);
    let ema_m = calc_ema_talib_style(&obv_seq, m);
    let e1 = *ema_n.last().unwrap_or(&f64::NAN);
    let e2 = *ema_m.last().unwrap_or(&f64::NAN);
    if !e1.is_finite() || !e2.is_finite() {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }
    let v1 = if e1 > e2 { "看多" } else { "看空" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// obv_up_dw_line_V230719：OBV 交叉信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}MO{max_overlap}_OBV能量V230719"`
///
/// 信号逻辑：
/// 1. 先计算 OBV 累计量序列；
/// 2. 计算 `obvm = EMA(OBV, n)`，再计算 `sig = EMA(obvm, m)`；
/// 3. 若当前 `obvm > sig` 且 `max_overlap` 根前 `obvm < sig`，判 `看多`；
/// 4. 若当前 `obvm < sig` 且 `max_overlap` 根前 `obvm > sig`，判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N7M10MO3_OBV能量V230719_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N7M10MO3_OBV能量V230719_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：OBVM EMA 周期，默认 `7`；
/// - `m`：信号线 EMA 周期，默认 `10`；
/// - `max_overlap`：交叉回看根数，默认 `3`。
/// 对齐说明：交叉判定时点与 Python `obv_up_dw_line_V230719` 完全一致（使用 `-max_overlap`）。
#[signal(
    category = "kline",
    name = "obv_up_dw_line_V230719",
    template = "{freq}_D{di}N{n}M{m}MO{max_overlap}_OBV能量V230719",
    opcode = "ObvUpDwLineV230719",
    param_kind = "ObvUpDwLineV230719"
)]
pub fn obv_up_dw_line_v230719(
    c: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 7);
    let m = params.usize("m", 10);
    let max_overlap = params.usize("max_overlap", 3);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}MO{}", di, n, m, max_overlap);
    let k3 = "OBV能量V230719";
    let v1_default = "其他";

    let min_k_num = di + n.max(m) + max_overlap + 10;
    if c.bars_raw.len() < min_k_num {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }

    update_obv_cache(c, cache);
    let Some(obv_series) = cache.series.get("OBV") else {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    };
    let id_map = bar_index_map(c);
    let bars = get_sub_elements(&c.bars_raw, di, min_k_num);
    let mut obv_seq = Vec::with_capacity(bars.len());
    for b in bars {
        if let Some(i) = id_map.get(&b.id).copied()
            && i < obv_series.len() {
                obv_seq.push(obv_series[i]);
            }
    }
    if obv_seq.len() < min_k_num {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }

    let obvm = calc_ema_talib_style(&obv_seq, n);
    let sig = calc_ema_talib_skip_leading_nan(&obvm, m);
    let l = obvm.len();
    if l <= max_overlap {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }
    let obvm_last = obvm[l - 1];
    let sig_last = sig[l - 1];
    let obvm_ref = obvm[l - max_overlap];
    let sig_ref = sig[l - max_overlap];
    if !obvm_last.is_finite()
        || !sig_last.is_finite()
        || !obvm_ref.is_finite()
        || !sig_ref.is_finite()
    {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }

    let v1 = if obvm_last > sig_last && obvm_ref < sig_ref {
        "看多"
    } else if obvm_last < sig_last && obvm_ref > sig_ref {
        "看空"
    } else {
        v1_default
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
