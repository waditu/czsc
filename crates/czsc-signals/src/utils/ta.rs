use crate::types::{BollSeries, KdjSeries, MacdSeries, TaCache};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use std::collections::HashMap;

#[derive(Debug, Clone, Copy)]
pub enum MacdField {
    Dif,
    Dea,
    Macd,
}

fn macd_field_at(series: &MacdSeries, idx: usize, field: MacdField) -> f64 {
    match field {
        MacdField::Dif => series.dif[idx],
        MacdField::Dea => series.dea[idx],
        MacdField::Macd => series.macd[idx],
    }
}

fn macd_field_from_tuple(values: (f64, f64, f64), field: MacdField) -> f64 {
    match field {
        MacdField::Dif => values.0,
        MacdField::Dea => values.1,
        MacdField::Macd => values.2,
    }
}

/// 读取指定 RawBar 的 MACD 字段值，并对齐 Python 的“RawBar 快照”语义：
///
/// - 若 `raw_bar.close` 与当前 `czsc.bars_raw[idx].close` 一致，直接返回缓存值；
/// - 若不一致（常见于同 dt 延伸阶段的历史快照），在“仅替换该 idx close”为快照值的条件下重算 MACD，
///   并返回该 idx 对应字段值。
///
/// `snapshot_overrides` 用于同一轮信号计算内复用同 id 的重算结果，避免重复全量计算。
#[allow(clippy::too_many_arguments)]
fn macd_snapshot_field_value_with_calc(
    czsc: &CZSC,
    series: &MacdSeries,
    id_to_idx: &HashMap<i32, usize>,
    raw_bar: &RawBar,
    short: usize,
    long: usize,
    m: usize,
    field: MacdField,
    snapshot_overrides: &mut HashMap<i32, (f64, f64, f64)>,
) -> Option<f64> {
    let &idx = id_to_idx.get(&raw_bar.id)?;
    let base = macd_field_at(series, idx, field);
    let current_close = czsc.bars_raw.get(idx)?.close;
    if (current_close - raw_bar.close).abs() <= f64::EPSILON {
        return Some(base);
    }

    if let Some(values) = snapshot_overrides.get(&raw_bar.id) {
        return Some(macd_field_from_tuple(*values, field));
    }

    let mut close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
    close[idx] = raw_bar.close;
    let snapshot = calc_macd_cache_style(&close, short, long, m);
    let values = (snapshot.dif[idx], snapshot.dea[idx], snapshot.macd[idx]);
    snapshot_overrides.insert(raw_bar.id, values);
    Some(macd_field_from_tuple(values, field))
}

#[allow(clippy::too_many_arguments)]
pub fn macd_snapshot_field_value(
    czsc: &CZSC,
    series: &MacdSeries,
    id_to_idx: &HashMap<i32, usize>,
    raw_bar: &RawBar,
    short: usize,
    long: usize,
    m: usize,
    field: MacdField,
    snapshot_overrides: &mut HashMap<i32, (f64, f64, f64)>,
) -> Option<f64> {
    macd_snapshot_field_value_with_calc(
        czsc,
        series,
        id_to_idx,
        raw_bar,
        short,
        long,
        m,
        field,
        snapshot_overrides,
    )
}

#[allow(clippy::too_many_arguments)]
pub fn macd_snapshot_field_value_py_style(
    czsc: &CZSC,
    series: &MacdSeries,
    id_to_idx: &HashMap<i32, usize>,
    raw_bar: &RawBar,
    short: usize,
    long: usize,
    m: usize,
    field: MacdField,
    snapshot_overrides: &mut HashMap<i32, (f64, f64, f64)>,
) -> Option<f64> {
    macd_snapshot_field_value(
        czsc,
        series,
        id_to_idx,
        raw_bar,
        short,
        long,
        m,
        field,
        snapshot_overrides,
    )
}

/// 读取指定 RawBar 的 MA 值，并对齐 Python 的“RawBar 快照”语义：
///
/// - 若 `raw_bar.close` 与当前 `czsc.bars_raw[idx].close` 一致，直接返回缓存值；
/// - 若不一致（常见于同 dt 延伸阶段的历史快照），在“仅替换该 idx close”为快照值的条件下重算 MA，
///   并返回该 idx 对应值。
///
/// `snapshot_overrides` 用于同一轮信号计算内复用同 id 的重算结果，避免重复全量计算。
pub fn ma_snapshot_value(
    czsc: &CZSC,
    series: &[f64],
    id_to_idx: &HashMap<i32, usize>,
    raw_bar: &RawBar,
    ma_type: &str,
    timeperiod: usize,
    snapshot_overrides: &mut HashMap<i32, f64>,
) -> Option<f64> {
    let &idx = id_to_idx.get(&raw_bar.id)?;
    let base = *series.get(idx)?;
    let current_close = czsc.bars_raw.get(idx)?.close;
    if (current_close - raw_bar.close).abs() <= f64::EPSILON {
        return Some(base);
    }

    if let Some(value) = snapshot_overrides.get(&raw_bar.id) {
        return Some(*value);
    }

    let mut close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
    close[idx] = raw_bar.close;
    let snapshot = match ma_type.to_uppercase().as_str() {
        "EMA" => calc_ema_cache_style(&close, timeperiod),
        "WMA" => calc_wma_cache_style(&close, timeperiod),
        _ => calc_sma_cache_style(&close, timeperiod),
    };
    let value = *snapshot.get(idx)?;
    snapshot_overrides.insert(raw_bar.id, value);
    Some(value)
}

/// 计算简单移动平均线 (SMA)，对齐 Python `czsc.utils.ta.SMA`
pub fn calc_sma(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut ms = vec![f64::NAN; len];
    if len == 0 || n == 0 {
        return ms;
    }
    for i in 0..len {
        let start = if i < n { 0 } else { i + 1 - n };
        let window = &series[start..=i];
        let mean = window.iter().sum::<f64>() / window.len() as f64;
        ms[i] = (mean * 10_000.0).round() / 10_000.0;
    }
    ms
}

/// 计算指数移动平均线 (EMA)，对齐 Python `czsc.utils.ta.EMA`
pub fn calc_ema(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut ms = vec![f64::NAN; len];
    if len == 0 || n == 0 {
        return ms;
    }
    ms[0] = series[0];
    for i in 1..len {
        let ema = (2.0 * series[i] + ms[i - 1] * (n as f64 - 1.0)) / (n as f64 + 1.0);
        ms[i] = ema;
    }
    for value in &mut ms {
        *value = (*value * 10_000.0).round() / 10_000.0;
    }
    ms
}

/// 计算加权移动平均线 (WMA)，对齐 Python `czsc.utils.ta.WMA`
pub fn calc_wma(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut ms = vec![f64::NAN; len];
    if len == 0 || n == 0 {
        return ms;
    }
    let denom = (n * (n + 1) / 2) as f64;
    for i in n..len {
        let window = &series[i + 1 - n..=i];
        let weighted = window
            .iter()
            .enumerate()
            .map(|(idx, value)| *value * (idx + 1) as f64)
            .sum::<f64>();
        ms[i] = (weighted / denom * 10_000.0).round() / 10_000.0;
    }
    ms
}

fn calc_sma_cache_style(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut out = vec![f64::NAN; len];
    if len < n || n == 0 {
        return out;
    }
    let mut sum = series[..n].iter().sum::<f64>();
    out[n - 1] = sum / n as f64;
    for i in n..len {
        // 对齐 TA-Lib SMA 的累计顺序：先减旧值，再加新值。
        // 该顺序会影响极小浮点误差在边界位上的符号，进而影响分类信号。
        sum -= series[i - n];
        sum += series[i];
        out[i] = sum / n as f64;
    }
    out
}

fn calc_ema_cache_style(series: &[f64], n: usize) -> Vec<f64> {
    calc_ema_talib_style(series, n)
}

fn calc_wma_cache_style(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut out = vec![f64::NAN; len];
    if len < n || n == 0 {
        return out;
    }
    let denom = (n * (n + 1) / 2) as f64;
    for i in (n - 1)..len {
        let window = &series[i + 1 - n..=i];
        let weighted = window
            .iter()
            .enumerate()
            .map(|(idx, value)| *value * (idx + 1) as f64)
            .sum::<f64>();
        out[i] = weighted / denom;
    }
    out
}

/// 计算 MACD {dif, dea, macd}，对齐 TA-Lib 原始三元组语义：
/// - `dif` = MACD 线
/// - `dea` = 信号线
/// - `macd` = 柱状图
pub fn calc_macd(series: &[f64], short: usize, long: usize, m: usize) -> MacdSeries {
    let len = series.len();
    let mut dif = vec![f64::NAN; len];
    let mut dea = vec![f64::NAN; len];
    let mut macd = vec![f64::NAN; len];
    if len == 0 || short == 0 || long == 0 || m == 0 || len < long {
        return MacdSeries {
            ids: Vec::new(),
            dif,
            dea,
            macd,
        };
    }

    let fast_offset = long.saturating_sub(short);
    let ema_short_tail = calc_ema_talib_style(&series[fast_offset..], short);
    let ema_long = calc_ema_talib_style(series, long);
    let mut dif_input = vec![f64::NAN; len];
    let mut dif_raw = vec![f64::NAN; len];
    for i in 0..len {
        let ema_short_i = if i >= fast_offset {
            ema_short_tail[i - fast_offset]
        } else {
            f64::NAN
        };
        if ema_short_i.is_finite() && ema_long[i].is_finite() {
            dif_raw[i] = ema_short_i - ema_long[i];
            dif_input[i] = dif_raw[i];
        }
    }

    dea = calc_ema_talib_skip_leading_nan(&dif_input, m);

    for i in 0..len {
        if dif_raw[i].is_finite() && dea[i].is_finite() {
            dif[i] = dif_raw[i];
            macd[i] = dif_raw[i] - dea[i];
        }
    }

    MacdSeries {
        ids: Vec::new(),
        dif,
        dea,
        macd,
    }
}

fn calc_ema_talib_style(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut out = vec![f64::NAN; len];
    if len < n || n == 0 {
        return out;
    }
    let alpha = 2.0 / (n as f64 + 1.0);
    let seed = series[..n].iter().sum::<f64>() / n as f64;
    out[n - 1] = seed;
    for i in n..len {
        out[i] = alpha * series[i] + (1.0 - alpha) * out[i - 1];
    }
    out
}

fn calc_ema_talib_skip_leading_nan(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut out = vec![f64::NAN; len];
    let Some(start) = series.iter().position(|x| x.is_finite()) else {
        return out;
    };
    let tail = calc_ema_talib_style(&series[start..], n);
    for (i, value) in tail.into_iter().enumerate() {
        out[start + i] = value;
    }
    out
}

/// 计算用于信号缓存的 MACD，默认与 `calc_macd` 使用同一 TA-Lib 原始三元组契约。
pub fn calc_macd_cache_style(series: &[f64], short: usize, long: usize, m: usize) -> MacdSeries {
    calc_macd(series, short, long, m)
}

/// 与 `calc_macd` 完全同义，保留仅用于兼容迁移中的旧调用点。
pub fn calc_macd_py_style(series: &[f64], short: usize, long: usize, m: usize) -> MacdSeries {
    calc_macd(series, short, long, m)
}

/// 计算 ATR（Wilder 平滑），与 TA-Lib ATR 口径一致
pub fn calc_atr(high: &[f64], low: &[f64], close: &[f64], timeperiod: usize) -> Vec<f64> {
    let len = high.len().min(low.len()).min(close.len());
    let mut atr = vec![f64::NAN; len];
    if len == 0 || timeperiod == 0 || len <= timeperiod {
        return atr;
    }

    let mut tr = vec![0.0; len];
    for i in 0..len {
        let prev_close = if i == 0 { close[0] } else { close[i - 1] };
        let hl = high[i] - low[i];
        let hc = (high[i] - prev_close).abs();
        let lc = (low[i] - prev_close).abs();
        tr[i] = hl.max(hc).max(lc);
    }

    // 对齐 TA-Lib ATR: 首个有效值在索引 `timeperiod`，
    // 使用 TR[1..=timeperiod] 的均值作为种子（TR[0] 仅用于占位）。
    let first = tr[1..=timeperiod].iter().sum::<f64>() / timeperiod as f64;
    atr[timeperiod] = first;
    for i in (timeperiod + 1)..len {
        atr[i] = (atr[i - 1] * (timeperiod as f64 - 1.0) + tr[i]) / timeperiod as f64;
    }
    atr
}

/// 计算 CCI，与 TA-Lib CCI 公式一致
pub fn calc_cci(high: &[f64], low: &[f64], close: &[f64], timeperiod: usize) -> Vec<f64> {
    let len = high.len().min(low.len()).min(close.len());
    let mut out = vec![f64::NAN; len];
    if len == 0 || timeperiod == 0 || len < timeperiod {
        return out;
    }

    let tp: Vec<f64> = (0..len)
        .map(|i| (high[i] + low[i] + close[i]) / 3.0)
        .collect();
    for i in (timeperiod - 1)..len {
        let w = &tp[i + 1 - timeperiod..=i];
        let ma = w.iter().sum::<f64>() / timeperiod as f64;
        let md = w.iter().map(|x| (x - ma).abs()).sum::<f64>() / timeperiod as f64;
        out[i] = if md == 0.0 {
            0.0
        } else {
            (tp[i] - ma) / (0.015 * md)
        };
    }
    out
}

/// 更新 MA 缓存
pub fn update_ma_cache(
    czsc: &CZSC,
    cache_key: &str,
    ma_type: &str,
    timeperiod: usize,
    cache: &mut TaCache,
) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let ma_type_u = ma_type.to_uppercase();
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();

    let mut need_init = !cache.series.contains_key(cache_key) || now_len < timeperiod + 15;
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

    let calc = |close: &[f64]| match ma_type_u.as_str() {
        "SMA" => calc_sma_cache_style(close, timeperiod),
        "EMA" => calc_ema_cache_style(close, timeperiod),
        "WMA" => calc_wma_cache_style(close, timeperiod),
        _ => calc_sma_cache_style(close, timeperiod),
    };

    if need_init {
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let res = calc(&close);
        cache.series.insert(cache_key.to_string(), res);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.series.get(cache_key).unwrap();
    let existing_ids = cache.series_ids.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, f64> = HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, existing[i]);
    }
    let mut res = Vec::with_capacity(now_len);
    for id in &bar_ids {
        res.push(*old_map.get(id).unwrap_or(&f64::NAN));
    }

    let window_size = (timeperiod + 10).min(now_len);
    let window_start = now_len - window_size;
    let close: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.close)
        .collect();
    let partial = calc(&close);
    for i in 1..=5.min(window_size) {
        let dst_idx = now_len - i;
        let src_idx = window_size - i;
        res[dst_idx] = partial[src_idx];
    }

    cache.series.insert(cache_key.to_string(), res);
    cache.series_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

/// 更新成交量 MA 缓存（对齐 Python `update_vol_ma_cache` 增量语义）
pub fn update_vol_ma_cache(
    czsc: &CZSC,
    cache_key: &str,
    ma_type: &str,
    timeperiod: usize,
    cache: &mut TaCache,
) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let ma_type_u = ma_type.to_uppercase();
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();

    let mut need_init = !cache.series.contains_key(cache_key) || now_len < timeperiod + 15;
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

    let calc = |vol: &[f64]| match ma_type_u.as_str() {
        "SMA" => calc_sma(vol, timeperiod),
        "EMA" => calc_ema(vol, timeperiod),
        "WMA" => calc_wma(vol, timeperiod),
        _ => calc_sma(vol, timeperiod),
    };

    if need_init {
        let vol: Vec<f64> = czsc.bars_raw.iter().map(|b| b.vol).collect();
        let res = calc(&vol);
        cache.series.insert(cache_key.to_string(), res);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.series.get(cache_key).unwrap();
    let existing_ids = cache.series_ids.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, f64> = HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, existing[i]);
    }
    let mut res = Vec::with_capacity(now_len);
    for id in &bar_ids {
        res.push(*old_map.get(id).unwrap_or(&f64::NAN));
    }

    let window_size = (timeperiod + 10).min(now_len);
    let window_start = now_len - window_size;
    let vol: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.vol)
        .collect();
    let partial = calc(&vol);
    for i in 1..=3.min(window_size) {
        let dst_idx = now_len - i;
        let src_idx = window_size - i;
        res[dst_idx] = partial[src_idx];
    }

    cache.series.insert(cache_key.to_string(), res);
    cache.series_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

/// 更新 MACD 缓存，对齐 Python `update_macd_cache` 的增量逻辑
pub fn update_macd_cache(
    czsc: &CZSC,
    cache_key: &str,
    short: usize,
    long: usize,
    m: usize,
    cache: &mut TaCache,
) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();
    let min_count = m + long + 168;

    let mut need_init = !cache.macd.contains_key(cache_key) || now_len < min_count + 15;
    if !need_init {
        if let Some(existing) = cache.macd.get(cache_key) {
            if now_len < 2 || existing.ids.is_empty() {
                need_init = true;
            } else {
                let penultimate_id = bar_ids[now_len - 2];
                need_init = !existing.ids.contains(&penultimate_id);
            }
        } else {
            need_init = true;
        }
    }

    if need_init {
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let mut res = calc_macd_cache_style(&close, short, long, m);
        res.ids = bar_ids;
        cache.macd.insert(cache_key.to_string(), res);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.macd.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, (f64, f64, f64)> = HashMap::with_capacity(existing.ids.len());
    for (i, id) in existing.ids.iter().enumerate() {
        old_map.insert(*id, (existing.dif[i], existing.dea[i], existing.macd[i]));
    }
    let mut dif = Vec::with_capacity(now_len);
    let mut dea = Vec::with_capacity(now_len);
    let mut macd = Vec::with_capacity(now_len);
    for id in &bar_ids {
        if let Some((d1, d2, d3)) = old_map.get(id) {
            dif.push(*d1);
            dea.push(*d2);
            macd.push(*d3);
        } else {
            dif.push(f64::NAN);
            dea.push(f64::NAN);
            macd.push(f64::NAN);
        }
    }

    let window_size = (min_count + 10).min(now_len);
    let window_start = now_len - window_size;
    let close: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.close)
        .collect();
    let partial = calc_macd_cache_style(&close, short, long, m);

    for i in 1..=5.min(window_size) {
        let dst_idx = now_len - i;
        let src_idx = window_size - i;
        dif[dst_idx] = partial.dif[src_idx];
        dea[dst_idx] = partial.dea[src_idx];
        macd[dst_idx] = partial.macd[src_idx];
    }

    cache.macd.insert(
        cache_key.to_string(),
        MacdSeries {
            ids: bar_ids,
            dif,
            dea,
            macd,
        },
    );
    cache.last_len = now_len;
}

/// 与 `update_macd_cache` 完全同义，保留仅用于兼容迁移中的旧调用点。
pub fn update_macd_cache_py_style(
    czsc: &CZSC,
    cache_key: &str,
    short: usize,
    long: usize,
    m: usize,
    cache: &mut TaCache,
) {
    update_macd_cache(czsc, cache_key, short, long, m, cache);
}

/// 更新 BOLL 缓存
pub fn update_boll_cache(
    czsc: &CZSC,
    cache_key: &str,
    timeperiod: usize,
    nbdev: f64,
    cache: &mut TaCache,
) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();

    let calc_full = |close: &[f64]| {
        let n = close.len();
        let mut upper = vec![f64::NAN; n];
        let mut mid = vec![f64::NAN; n];
        let mut lower = vec![f64::NAN; n];
        if n >= timeperiod {
            for i in (timeperiod - 1)..n {
                let window = &close[i + 1 - timeperiod..=i];
                let mean = window.iter().sum::<f64>() / timeperiod as f64;
                // numpy/talib 默认用的是总体标准差(ddof=0)
                let variance =
                    window.iter().map(|&x| (x - mean).powi(2)).sum::<f64>() / timeperiod as f64;
                let std_dev = variance.sqrt();
                mid[i] = mean;
                upper[i] = mean + nbdev * std_dev;
                lower[i] = mean - nbdev * std_dev;
            }
        }
        BollSeries { upper, mid, lower }
    };

    let mut need_init = !cache.boll.contains_key(cache_key)
        || !cache.boll_ids.contains_key(cache_key)
        || now_len < timeperiod + 15;
    if !need_init {
        if let Some(existing_ids) = cache.boll_ids.get(cache_key) {
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
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let res = calc_full(&close);
        cache.boll.insert(cache_key.to_string(), res);
        cache.boll_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.boll.get(cache_key).unwrap();
    let existing_ids = cache.boll_ids.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, (f64, f64, f64)> = HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, (existing.upper[i], existing.mid[i], existing.lower[i]));
    }

    let mut upper = Vec::with_capacity(now_len);
    let mut mid = Vec::with_capacity(now_len);
    let mut lower = Vec::with_capacity(now_len);
    for id in &bar_ids {
        if let Some((u, m, l)) = old_map.get(id) {
            upper.push(*u);
            mid.push(*m);
            lower.push(*l);
        } else {
            upper.push(f64::NAN);
            mid.push(f64::NAN);
            lower.push(f64::NAN);
        }
    }

    // 对齐 Python update_boll_cache：增量阶段重算尾窗并覆盖最近 5 根。
    let window_size = (timeperiod + 10).min(now_len);
    let window_start = now_len - window_size;
    let close: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.close)
        .collect();
    let partial = calc_full(&close);
    for i in 1..=5.min(window_size) {
        let dst_idx = now_len - i;
        let src_idx = window_size - i;
        upper[dst_idx] = partial.upper[src_idx];
        mid[dst_idx] = partial.mid[src_idx];
        lower[dst_idx] = partial.lower[src_idx];
    }

    cache
        .boll
        .insert(cache_key.to_string(), BollSeries { upper, mid, lower });
    cache.boll_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

/// 更新 ATR 缓存，对齐 Python `update_atr_cache` 的初始化/增量口径
pub fn update_atr_cache(czsc: &CZSC, cache_key: &str, timeperiod: usize, cache: &mut TaCache) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();

    let mut need_init = !cache.series.contains_key(cache_key) || now_len < timeperiod + 15;
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

    let calc_full = |h: &[f64], l: &[f64], c: &[f64]| calc_atr(h, l, c, timeperiod);

    if need_init {
        let high: Vec<f64> = czsc.bars_raw.iter().map(|b| b.high).collect();
        let low: Vec<f64> = czsc.bars_raw.iter().map(|b| b.low).collect();
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let res = calc_full(&high, &low, &close);
        cache.series.insert(cache_key.to_string(), res);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.series.get(cache_key).unwrap();
    let existing_ids = cache.series_ids.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, f64> = HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, existing[i]);
    }
    let mut res = Vec::with_capacity(now_len);
    for id in &bar_ids {
        res.push(*old_map.get(id).unwrap_or(&f64::NAN));
    }

    // 对齐 Python update_atr_cache: 增量阶段回看 timeperiod+80 窗口
    let window_size = (timeperiod + 80).min(now_len);
    let window_start = now_len - window_size;
    let high: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.high)
        .collect();
    let low: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.low)
        .collect();
    let close: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.close)
        .collect();
    let partial = calc_full(&high, &low, &close);

    // 对齐 Python: 历史 bar 仅补齐未写入过 cache_key 的值，不覆盖既有值。
    // 但最后一根未完成高周期 bar 在流式更新时会持续变化；Python 侧该对象的 cache
    // 会随新对象重建而刷新，Rust 侧需要显式重算末值避免把 ATR 冻结在更早时刻。
    for (i, partial_i) in partial.iter().enumerate().take(window_size) {
        let dst = window_start + i;
        if res[dst].is_nan() {
            res[dst] = *partial_i;
        }
    }
    let last_dst = now_len - 1;
    let last_src = window_size - 1;
    res[last_dst] = partial[last_src];

    cache.series.insert(cache_key.to_string(), res);
    cache.series_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

/// 更新 CCI 缓存，对齐 Python `update_cci_cache` 的初始化/增量口径
pub fn update_cci_cache(czsc: &CZSC, cache_key: &str, timeperiod: usize, cache: &mut TaCache) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();

    let mut need_init = !cache.series.contains_key(cache_key) || now_len < timeperiod + 15;
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

    let calc_full = |h: &[f64], l: &[f64], c: &[f64]| calc_cci(h, l, c, timeperiod);
    if need_init {
        let high: Vec<f64> = czsc.bars_raw.iter().map(|b| b.high).collect();
        let low: Vec<f64> = czsc.bars_raw.iter().map(|b| b.low).collect();
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let res = calc_full(&high, &low, &close);
        cache.series.insert(cache_key.to_string(), res);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.series.get(cache_key).unwrap();
    let existing_ids = cache.series_ids.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, f64> = HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, existing[i]);
    }
    let mut res = Vec::with_capacity(now_len);
    for id in &bar_ids {
        res.push(*old_map.get(id).unwrap_or(&f64::NAN));
    }

    // 对齐 Python update_cci_cache: 增量阶段回看 timeperiod + 10
    let window_size = (timeperiod + 10).min(now_len);
    let window_start = now_len - window_size;
    let high: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.high)
        .collect();
    let low: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.low)
        .collect();
    let close: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.close)
        .collect();
    let partial = calc_full(&high, &low, &close);

    // 对齐 Python: 历史 bar 仅补齐未写入过 cache_key 的值，不覆盖既有值。
    // 但流式场景下未完成高周期 bar 会复用同一 id；Rust 侧需要显式刷新末值，
    // 否则 CCI 会冻结在更早时刻，导致阈值类信号（如 CCI 决策区域）持续偏移。
    for (i, partial_i) in partial.iter().enumerate().take(window_size) {
        let dst = window_start + i;
        if res[dst].is_nan() {
            res[dst] = *partial_i;
        }
    }
    let last_dst = now_len - 1;
    let last_src = window_size - 1;
    res[last_dst] = partial[last_src];

    cache.series.insert(cache_key.to_string(), res);
    cache.series_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

/// 更新 KDJ 缓存
pub fn update_kdj_cache(
    czsc: &CZSC,
    cache_key: &str,
    fastk_period: usize,
    slowk_period: usize,
    slowd_period: usize,
    cache: &mut TaCache,
) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 || fastk_period == 0 || slowk_period == 0 || slowd_period == 0 {
        return;
    }
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();
    let min_count = fastk_period + slowk_period;

    let mut need_init = !cache.kdj.contains_key(cache_key) || now_len < min_count + 15;
    if !need_init {
        if let Some(existing) = cache.kdj.get(cache_key) {
            if now_len < 2 || existing.ids.is_empty() {
                need_init = true;
            } else {
                let penultimate_id = bar_ids[now_len - 2];
                need_init = !existing.ids.contains(&penultimate_id);
            }
        } else {
            need_init = true;
        }
    }

    if need_init {
        let high: Vec<f64> = czsc.bars_raw.iter().map(|b| b.high).collect();
        let low: Vec<f64> = czsc.bars_raw.iter().map(|b| b.low).collect();
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let (k, d) = calc_stoch(
            &high,
            &low,
            &close,
            fastk_period,
            slowk_period,
            slowd_period,
        );
        let j: Vec<f64> = k
            .iter()
            .zip(d.iter())
            .map(|(x, y)| 3.0 * *x - 2.0 * *y)
            .collect();
        cache.kdj.insert(
            cache_key.to_string(),
            KdjSeries {
                ids: bar_ids,
                k,
                d,
                j,
            },
        );
        cache.last_len = now_len;
        return;
    }

    // 增量更新：先按 id 对齐旧缓存，再覆盖最近 5 根
    let existing = cache.kdj.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, (f64, f64, f64)> = HashMap::with_capacity(existing.ids.len());
    for (i, id) in existing.ids.iter().enumerate() {
        old_map.insert(*id, (existing.k[i], existing.d[i], existing.j[i]));
    }

    let mut k = Vec::with_capacity(now_len);
    let mut d = Vec::with_capacity(now_len);
    let mut j = Vec::with_capacity(now_len);
    for id in &bar_ids {
        if let Some((k0, d0, j0)) = old_map.get(id) {
            k.push(*k0);
            d.push(*d0);
            j.push(*j0);
        } else {
            k.push(f64::NAN);
            d.push(f64::NAN);
            j.push(f64::NAN);
        }
    }

    let window_size = (min_count + 10).min(now_len);
    let window_start = now_len - window_size;
    let high: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.high)
        .collect();
    let low: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.low)
        .collect();
    let close: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.close)
        .collect();
    let (partial_k, partial_d) = calc_stoch(
        &high,
        &low,
        &close,
        fastk_period,
        slowk_period,
        slowd_period,
    );
    for i in 1..=5.min(window_size) {
        let dst_idx = now_len - i;
        let src_idx = window_size - i;
        k[dst_idx] = partial_k[src_idx];
        d[dst_idx] = partial_d[src_idx];
        j[dst_idx] = 3.0 * k[dst_idx] - 2.0 * d[dst_idx];
    }

    cache.kdj.insert(
        cache_key.to_string(),
        KdjSeries {
            ids: bar_ids,
            k,
            d,
            j,
        },
    );
    cache.last_len = now_len;
}

/// 更新 RSI 缓存 (Wilder's Smoothing，严格对齐 TA-Lib)
pub fn update_rsi_cache(czsc: &CZSC, cache_key: &str, timeperiod: usize, cache: &mut TaCache) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();

    // 对齐 Python update_rsi_cache 的初始化/增量口径。
    // Rust 流式场景下同一高周期 bar 会在多次 update 中复用同一 id，
    // 这里不能因“最后一根 id 已存在”直接返回，否则 RSI 末值会被冻结。
    // 因此每次都重算窗口尾部，确保未完成 bar 的 RSI 随 close 更新。
    if !cache.series.contains_key(cache_key) || !cache.series_ids.contains_key(cache_key) {
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let rsi_res = calc_rsi(&close, timeperiod);
        cache.series.insert(cache_key.to_string(), rsi_res);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.series.get(cache_key).unwrap();
    let existing_ids = cache.series_ids.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, f64> = HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, existing[i]);
    }
    let use_full =
        now_len < timeperiod + 15 || now_len < 2 || !old_map.contains_key(&bar_ids[now_len - 2]);
    if use_full {
        let close: Vec<f64> = czsc.bars_raw.iter().map(|b| b.close).collect();
        let rsi_res = calc_rsi(&close, timeperiod);
        cache.series.insert(cache_key.to_string(), rsi_res);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let mut rsi_res = Vec::with_capacity(now_len);
    for id in &bar_ids {
        rsi_res.push(*old_map.get(id).unwrap_or(&f64::NAN));
    }

    let window_size = (timeperiod + 10).min(now_len);
    let window_start = now_len - window_size;
    let close: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.close)
        .collect();
    let partial = calc_rsi(&close, timeperiod);
    for i in 1..=5.min(window_size) {
        let dst_idx = now_len - i;
        let src_idx = window_size - i;
        rsi_res[dst_idx] = partial[src_idx];
    }

    cache.series.insert(cache_key.to_string(), rsi_res);
    cache.series_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

/// 更新 SAR 缓存（对齐 Python `update_sar_cache`）
pub fn update_sar_cache(czsc: &CZSC, cache_key: &str, cache: &mut TaCache) {
    let now_len = czsc.bars_raw.len();
    if now_len == 0 {
        return;
    }
    let bar_ids: Vec<i32> = czsc.bars_raw.iter().map(|b| b.id).collect();
    let calc_full = |h: &[f64], l: &[f64]| calc_sar(h, l, 0.02, 0.2);

    if !cache.series.contains_key(cache_key) || !cache.series_ids.contains_key(cache_key) {
        let high: Vec<f64> = czsc.bars_raw.iter().map(|b| b.high).collect();
        let low: Vec<f64> = czsc.bars_raw.iter().map(|b| b.low).collect();
        let res = calc_full(&high, &low);
        cache.series.insert(cache_key.to_string(), res);
        cache.series_ids.insert(cache_key.to_string(), bar_ids);
        cache.last_len = now_len;
        return;
    }

    let existing = cache.series.get(cache_key).unwrap();
    let existing_ids = cache.series_ids.get(cache_key).unwrap();
    let mut old_map: HashMap<i32, f64> = HashMap::with_capacity(existing_ids.len());
    for (i, id) in existing_ids.iter().enumerate() {
        old_map.insert(*id, existing[i]);
    }

    let use_full = now_len < 50 || now_len < 2 || !old_map.contains_key(&bar_ids[now_len - 2]);
    let (window_start, window_size) = if use_full {
        (0usize, now_len)
    } else {
        let size = 120.min(now_len);
        (now_len - size, size)
    };

    let high: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.high)
        .collect();
    let low: Vec<f64> = czsc.bars_raw[window_start..]
        .iter()
        .map(|b| b.low)
        .collect();
    let partial = calc_full(&high, &low);

    let mut res = Vec::with_capacity(now_len);
    for id in &bar_ids {
        res.push(*old_map.get(id).unwrap_or(&f64::NAN));
    }

    for (i, partial_i) in partial.iter().enumerate().take(window_size) {
        let dst = window_start + i;
        if !old_map.contains_key(&bar_ids[dst]) {
            res[dst] = *partial_i;
        }
    }
    // 与 ATR/RSI 的流式处理一致：无论 id 是否已存在，都刷新最后一根。
    // 这样才能对齐 Python 中“最后一根 bar 对象被重建后重新写 cache”的效果。
    let last_dst = now_len - 1;
    let last_src = window_size - 1;
    res[last_dst] = partial[last_src];

    cache.series.insert(cache_key.to_string(), res);
    cache.series_ids.insert(cache_key.to_string(), bar_ids);
    cache.last_len = now_len;
}

fn calc_sar(high: &[f64], low: &[f64], acceleration: f64, max_acceleration: f64) -> Vec<f64> {
    let len = high.len().min(low.len());
    let mut out = vec![f64::NAN; len];
    if len < 2 {
        return out;
    }

    let up_move = high[1] - high[0];
    let down_move = low[0] - low[1];
    let plus_dm = if up_move > down_move && up_move > 0.0 {
        up_move
    } else {
        0.0
    };
    let minus_dm = if down_move > up_move && down_move > 0.0 {
        down_move
    } else {
        0.0
    };
    let mut is_long = minus_dm == 0.0 || plus_dm > minus_dm;

    let accel = acceleration.min(max_acceleration);
    let mut af = accel;
    let mut today_idx = 1usize;
    let mut out_idx = 1usize;
    let mut new_high = high[today_idx - 1];
    let mut new_low = low[today_idx - 1];

    let mut ep;
    let mut sar;
    if is_long {
        ep = high[today_idx];
        sar = new_low;
    } else {
        ep = low[today_idx];
        sar = new_high;
    }

    new_low = low[today_idx];
    new_high = high[today_idx];

    while today_idx < len {
        let prev_low = new_low;
        let prev_high = new_high;
        new_low = low[today_idx];
        new_high = high[today_idx];
        today_idx += 1;

        if is_long {
            if new_low <= sar {
                is_long = false;
                sar = ep;
                if sar < prev_high {
                    sar = prev_high;
                }
                if sar < new_high {
                    sar = new_high;
                }
                out[out_idx] = sar;
                af = accel;
                ep = new_low;
                sar = sar + af * (ep - sar);
                if sar < prev_high {
                    sar = prev_high;
                }
                if sar < new_high {
                    sar = new_high;
                }
            } else {
                out[out_idx] = sar;
                if new_high > ep {
                    ep = new_high;
                    af = (af + accel).min(max_acceleration);
                }
                sar = sar + af * (ep - sar);
                if sar > prev_low {
                    sar = prev_low;
                }
                if sar > new_low {
                    sar = new_low;
                }
            }
        } else if new_high >= sar {
            is_long = true;
            sar = ep;
            if sar > prev_low {
                sar = prev_low;
            }
            if sar > new_low {
                sar = new_low;
            }
            out[out_idx] = sar;
            af = accel;
            ep = new_high;
            sar = sar + af * (ep - sar);
            if sar > prev_low {
                sar = prev_low;
            }
            if sar > new_low {
                sar = new_low;
            }
        } else {
            out[out_idx] = sar;
            if new_low < ep {
                ep = new_low;
                af = (af + accel).min(max_acceleration);
            }
            sar = sar + af * (ep - sar);
            if sar < prev_high {
                sar = prev_high;
            }
            if sar < new_high {
                sar = new_high;
            }
        }
        out_idx += 1;
    }
    out
}

fn calc_rsi(close: &[f64], timeperiod: usize) -> Vec<f64> {
    let now_len = close.len();
    let mut rsi_res = vec![f64::NAN; now_len];
    if now_len <= timeperiod || timeperiod == 0 {
        return rsi_res;
    }

    let mut avg_gain = 0.0;
    let mut avg_loss = 0.0;
    for i in 1..=timeperiod {
        let change = close[i] - close[i - 1];
        if change > 0.0 {
            avg_gain += change;
        } else {
            avg_loss += -change;
        }
    }
    avg_gain /= timeperiod as f64;
    avg_loss /= timeperiod as f64;

    rsi_res[timeperiod] = {
        let sum = avg_gain + avg_loss;
        if sum != 0.0 {
            100.0 * (avg_gain / sum)
        } else {
            0.0
        }
    };

    for i in (timeperiod + 1)..now_len {
        let delta = close[i] - close[i - 1];

        // 逐步对齐 TA-Lib: 先乘 period-1，再加今日涨跌，最后除以 period。
        avg_gain *= timeperiod as f64 - 1.0;
        avg_loss *= timeperiod as f64 - 1.0;
        if delta < 0.0 {
            avg_loss -= delta;
        } else {
            avg_gain += delta;
        }
        avg_gain /= timeperiod as f64;
        avg_loss /= timeperiod as f64;

        let sum = avg_gain + avg_loss;
        rsi_res[i] = if sum != 0.0 {
            100.0 * (avg_gain / sum)
        } else {
            0.0
        };
    }

    rsi_res
}

fn calc_sma_nan(series: &[f64], n: usize) -> Vec<f64> {
    let len = series.len();
    let mut out = vec![f64::NAN; len];
    if n == 0 || len < n {
        return out;
    }
    for i in (n - 1)..len {
        let w = &series[i + 1 - n..=i];
        if w.iter().any(|x| x.is_nan()) {
            continue;
        }
        out[i] = w.iter().sum::<f64>() / n as f64;
    }
    out
}

fn calc_stoch(
    high: &[f64],
    low: &[f64],
    close: &[f64],
    fastk_period: usize,
    slowk_period: usize,
    slowd_period: usize,
) -> (Vec<f64>, Vec<f64>) {
    let len = close.len();
    let mut fastk = vec![f64::NAN; len];
    if len == 0
        || high.len() != len
        || low.len() != len
        || fastk_period == 0
        || slowk_period == 0
        || slowd_period == 0
        || len < fastk_period
    {
        return (vec![f64::NAN; len], vec![f64::NAN; len]);
    }

    for i in (fastk_period - 1)..len {
        let start = i + 1 - fastk_period;
        let hh = high[start..=i]
            .iter()
            .fold(f64::NEG_INFINITY, |a, &b| a.max(b));
        let ll = low[start..=i].iter().fold(f64::INFINITY, |a, &b| a.min(b));
        if hh > ll {
            fastk[i] = (close[i] - ll) / (hh - ll) * 100.0;
        }
    }

    let mut slowk = calc_sma_nan(&fastk, slowk_period);
    let mut slowd = calc_sma_nan(&slowk, slowd_period);

    // 与 TA-Lib STOCH lookback 对齐：fastk-1 + slowk-1 + slowd-1。
    // TA-Lib 在该索引之前的 slowk/slowd 都返回 NaN。
    let lookback = (fastk_period - 1) + (slowk_period - 1) + (slowd_period - 1);
    let warmup = lookback.min(len);
    for i in 0..warmup {
        slowk[i] = f64::NAN;
        slowd[i] = f64::NAN;
    }
    (slowk, slowd)
}

#[cfg(test)]
mod tests {
    use super::{
        calc_ema, calc_macd, calc_macd_cache_style, calc_macd_py_style, calc_rsi, calc_sma,
        calc_stoch, calc_wma,
    };

    #[test]
    fn test_calc_sma_matches_python_expanding_mean_before_window() {
        let series = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let res = calc_sma(&series, 3);
        assert_eq!(res, vec![1.0, 1.5, 2.0, 3.0, 4.0]);
    }

    #[test]
    fn test_calc_ema_matches_python_seed_from_first_value() {
        let series = vec![10.1234, 14.9812, 9.3345, 11.7789];
        let res = calc_ema(&series, 3);
        assert_eq!(res, vec![10.1234, 12.5523, 10.9434, 11.3612]);
    }

    #[test]
    fn test_calc_wma_matches_python_validity_window() {
        let series = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        let res = calc_wma(&series, 3);
        assert!(res[0].is_nan());
        assert!(res[1].is_nan());
        assert!(res[2].is_nan());
        assert!((res[3] - 3.3333).abs() < 1e-4);
        assert!((res[4] - 4.3333).abs() < 1e-4);
    }

    #[test]
    fn test_calc_macd_uses_talib_warmup_and_histogram_contract() {
        let series = vec![
            10.1234, 14.9812, 9.3345, 11.7789, 13.5521, 12.0044, 15.3311, 14.2088, 13.8877,
            16.2355, 15.0222, 17.1188, 16.0044, 18.4455, 17.9933, 19.2244, 18.1102, 17.8891,
            20.0033, 19.7721, 21.1144, 20.8842, 22.3355, 21.6622, 23.1188, 22.7744, 24.3355,
            23.9911, 22.8877, 21.4455, 20.8844, 19.7733, 21.1188, 22.5522, 23.8877, 22.6644,
            24.1188, 25.2244, 24.0033, 26.1188,
        ];
        let res = calc_macd(&series, 12, 26, 9);
        assert_eq!(res.dif.len(), series.len());
        assert!(res.dif[..33].iter().all(|x| x.is_nan()));
        assert!(res.dea[..33].iter().all(|x| x.is_nan()));
        assert!(res.macd[..33].iter().all(|x| x.is_nan()));

        let exp_dif = [
            2.1423805846933526,
            2.178795717541078,
            2.084911326267463,
            2.103616018844914,
            2.1824938717891307,
            2.122011347779168,
            2.219200124149946,
        ];
        let exp_dea = [
            2.8872106434589506,
            2.745527658275376,
            2.6134043918737935,
            2.5114467172680177,
            2.4456561481722403,
            2.380927188093626,
            2.34858177530489,
        ];
        let exp_macd = [
            -0.744830058765598,
            -0.5667319407342979,
            -0.5284930656063307,
            -0.40783069842310393,
            -0.26316227638310963,
            -0.258915840314458,
            -0.1293816511549437,
        ];
        for (offset, idx) in (33..40).enumerate() {
            assert!((res.dif[idx] - exp_dif[offset]).abs() < 1e-12);
            assert!((res.dea[idx] - exp_dea[offset]).abs() < 1e-12);
            assert!((res.macd[idx] - exp_macd[offset]).abs() < 1e-12);
        }
    }

    #[test]
    fn test_calc_macd_cache_style_matches_talib_contract() {
        let series = vec![
            10.1234, 14.9812, 9.3345, 11.7789, 13.5521, 12.0044, 15.3311, 14.2088, 13.8877,
            16.2355, 15.0222, 17.1188, 16.0044, 18.4455, 17.9933, 19.2244, 18.1102, 17.8891,
            20.0033, 19.7721, 21.1144, 20.8842, 22.3355, 21.6622, 23.1188, 22.7744, 24.3355,
            23.9911, 22.8877, 21.4455, 20.8844, 19.7733, 21.1188, 22.5522, 23.8877, 22.6644,
            24.1188, 25.2244, 24.0033, 26.1188,
        ];
        let base = calc_macd(&series, 12, 26, 9);
        let cache = calc_macd_cache_style(&series, 12, 26, 9);
        assert_eq!(base.dif.len(), cache.dif.len());
        for idx in 0..series.len() {
            if base.dif[idx].is_nan() {
                assert!(cache.dif[idx].is_nan());
                assert!(cache.dea[idx].is_nan());
                assert!(cache.macd[idx].is_nan());
            } else {
                assert!((base.dif[idx] - cache.dif[idx]).abs() < 1e-12);
                assert!((base.dea[idx] - cache.dea[idx]).abs() < 1e-12);
                assert!((base.macd[idx] - cache.macd[idx]).abs() < 1e-12);
            }
        }
    }

    #[test]
    fn test_calc_macd_plain_and_py_style_share_canonical_contract() {
        let series: Vec<f64> = (1..=200).map(|x| x as f64 / 3.7).collect();
        let res = calc_macd(&series, 12, 26, 9);
        let alias = calc_macd_py_style(&series, 12, 26, 9);
        assert_eq!(res.dif.len(), alias.dif.len());
        for idx in 0..res.dif.len() {
            if res.dif[idx].is_nan() {
                assert!(alias.dif[idx].is_nan());
                assert!(alias.dea[idx].is_nan());
                assert!(alias.macd[idx].is_nan());
            } else {
                assert!((res.dif[idx] - alias.dif[idx]).abs() < 1e-12);
                assert!((res.dea[idx] - alias.dea[idx]).abs() < 1e-12);
                assert!((res.macd[idx] - alias.macd[idx]).abs() < 1e-12);
                let expect = res.dif[idx] - res.dea[idx];
                assert!((res.macd[idx] - expect).abs() < 1e-12);
            }
        }
    }

    #[test]
    fn test_calc_macd_talib_histogram_is_not_doubled() {
        let series = vec![
            10.1234, 14.9812, 9.3345, 11.7789, 13.5521, 12.0044, 15.3311, 14.2088, 13.8877,
            16.2355, 15.0222, 17.1188, 16.0044, 18.4455, 17.9933, 19.2244, 18.1102, 17.8891,
            20.0033, 19.7721, 21.1144, 20.8842, 22.3355, 21.6622, 23.1188, 22.7744, 24.3355,
            23.9911, 22.8877, 21.4455, 20.8844, 19.7733, 21.1188, 22.5522, 23.8877, 22.6644,
            24.1188, 25.2244, 24.0033, 26.1188,
        ];
        let res = calc_macd(&series, 12, 26, 9);
        let idx = 39;
        let hist = res.macd[idx];
        let doubled = (res.dif[idx] - res.dea[idx]) * 2.0;
        assert!((hist - (res.dif[idx] - res.dea[idx])).abs() < 1e-12);
        assert!((hist - doubled).abs() > 1e-6);
    }

    #[test]
    fn test_calc_rsi_flat_tail_aligns_talib_direction_case1() {
        let close = vec![
            22763.8, 22769.4, 22671.5, 22864.0, 22941.1, 22778.9, 22763.9, 23276.7, 23126.7,
            23062.3, 23230.6, 23115.5, 22916.9, 22962.4, 22974.4, 22974.4,
        ];
        let rsi = calc_rsi(&close, 6);
        let prev = rsi[14];
        let curr = rsi[15];
        assert!(prev.is_finite() && curr.is_finite());
        assert!(
            curr < prev,
            "expected talib direction down, prev={prev}, curr={curr}"
        );
    }

    #[test]
    fn test_calc_rsi_flat_tail_aligns_talib_direction_case2() {
        let close = vec![
            67887.5, 67935.1, 68395.2, 68305.0, 68548.2, 68600.9, 68731.1, 68881.0, 68788.3,
            68808.5, 68459.1, 68673.0, 68949.0, 69173.0, 69566.1, 69566.1,
        ];
        let rsi = calc_rsi(&close, 6);
        let prev = rsi[14];
        let curr = rsi[15];
        assert!(prev.is_finite() && curr.is_finite());
        assert!(
            curr < prev,
            "expected talib direction down, prev={prev}, curr={curr}"
        );
    }

    #[test]
    fn test_calc_stoch_all_nan_when_range_zero() {
        let high = vec![1.0; 11];
        let low = vec![1.0; 11];
        let close = vec![1.0; 11];
        let (k, d) = calc_stoch(&high, &low, &close, 9, 3, 3);
        assert!(k.iter().all(|x| x.is_nan()));
        assert!(d.iter().all(|x| x.is_nan()));
    }

    #[test]
    fn test_calc_stoch_matches_talib_reference_sequence() {
        let high = vec![
            10.0, 11.0, 12.0, 11.0, 13.0, 14.0, 15.0, 14.0, 16.0, 17.0, 18.0, 17.0, 19.0, 20.0,
            21.0, 20.0, 22.0, 23.0, 22.0, 24.0,
        ];
        let low = vec![
            9.0, 10.0, 11.0, 10.0, 12.0, 13.0, 14.0, 13.0, 15.0, 16.0, 17.0, 16.0, 18.0, 19.0,
            20.0, 19.0, 21.0, 22.0, 21.0, 23.0,
        ];
        let close = vec![
            9.5, 10.5, 11.5, 10.8, 12.6, 13.2, 14.7, 13.5, 15.4, 16.8, 17.1, 16.4, 18.6, 19.4,
            20.9, 19.7, 21.3, 22.7, 21.8, 23.4,
        ];
        let (k, d) = calc_stoch(&high, &low, &close, 9, 3, 3);

        let exp_k = [
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            87.67857142857143,
            88.57142857142856,
            94.82142857142856,
            91.3095238095238,
            90.83333333333333,
            89.82142857142856,
            89.52380952380952,
            90.35714285714285,
        ];
        let exp_d = [
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            f64::NAN,
            89.58333333333333,
            88.29365079365078,
            90.35714285714285,
            91.5674603174603,
            92.32142857142856,
            90.65476190476188,
            90.0595238095238,
            89.90079365079363,
        ];

        for i in 0..k.len() {
            if exp_k[i].is_nan() {
                assert!(k[i].is_nan(), "k[{i}] should be NaN but got {}", k[i]);
            } else {
                assert!(
                    (k[i] - exp_k[i]).abs() < 1e-12,
                    "k[{i}] = {}, expect {}",
                    k[i],
                    exp_k[i]
                );
            }
            if exp_d[i].is_nan() {
                assert!(d[i].is_nan(), "d[{i}] should be NaN but got {}", d[i]);
            } else {
                assert!(
                    (d[i] - exp_d[i]).abs() < 1e-12,
                    "d[{i}] = {}, expect {}",
                    d[i],
                    exp_d[i]
                );
            }
        }
    }
}
