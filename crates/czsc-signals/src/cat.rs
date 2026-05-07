use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_str_param, get_sub_elements, make_signal, make_signal_v1};
use crate::utils::ta::update_macd_cache;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::state::TraderState;
use czsc_signal_macros::signal;
use std::collections::HashMap;

fn macd_map(cache: &TaCache, cache_key: &str) -> HashMap<i32, f64> {
    let mut out = HashMap::new();
    if let Some(series) = cache.macd.get(cache_key) {
        for (i, id) in series.ids.iter().enumerate() {
            if let Some(v) = series.macd.get(i) {
                out.insert(*id, *v);
            }
        }
    }
    out
}

fn dea_map(cache: &TaCache, cache_key: &str) -> HashMap<i32, f64> {
    let mut out = HashMap::new();
    if let Some(series) = cache.macd.get(cache_key) {
        for (i, id) in series.ids.iter().enumerate() {
            if let Some(v) = series.dea.get(i) {
                out.insert(*id, *v);
            }
        }
    }
    out
}

fn cross_up_bars<'a>(bars: &[&'a RawBar], macd: &HashMap<i32, f64>) -> Vec<&'a RawBar> {
    let mut out = Vec::new();
    for w in bars.windows(2) {
        let m1 = *macd.get(&w[0].id).unwrap_or(&f64::NAN);
        let m2 = *macd.get(&w[1].id).unwrap_or(&f64::NAN);
        if m1 < 0.0 && m2 > 0.0 {
            out.push(w[1]);
        }
    }
    out
}

fn cross_down_bars<'a>(bars: &[&'a RawBar], macd: &HashMap<i32, f64>) -> Vec<&'a RawBar> {
    let mut out = Vec::new();
    for w in bars.windows(2) {
        let m1 = *macd.get(&w[0].id).unwrap_or(&f64::NAN);
        let m2 = *macd.get(&w[1].id).unwrap_or(&f64::NAN);
        if m1 > 0.0 && m2 < 0.0 {
            out.push(w[1]);
        }
    }
    out
}

/// cat_macd_V230518：高低级别 MACD 交叉联立信号
///
/// 参数模板：`"{freq1}#{freq2}_MACD交叉_联立V230518"`
///
/// 信号逻辑：
/// 1. 当 `freq1` 最近一次由负翻正（MACD 金叉）后，检查 `freq2` 是否仅出现 1 次金叉，满足判 `看多`；
/// 2. 当 `freq1` 最近一次由正翻负（MACD 死叉）后，检查 `freq2` 是否仅出现 1 次死叉，满足判 `看空`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线#60分钟_MACD交叉_联立V230518_看多_任意_任意_0')`
/// - `Signal('日线#60分钟_MACD交叉_联立V230518_看空_任意_任意_0')`
///
/// 参数说明：
/// - `freq1`：高一级别周期，默认 `5分钟`；
/// - `freq2`：低一级别周期，默认 `1分钟`。
/// 对齐说明：触发窗口、首次交叉判定与 Python `cat_macd_V230518` 保持一致。
#[signal(
    category = "trader",
    name = "cat_macd_V230518",
    template = "{freq1}#{freq2}_MACD交叉_联立V230518",
    opcode = "CatMacdV230518",
    param_kind = "CatMacdV230518"
)]
pub fn cat_macd_v230518(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let freq1 = get_str_param(params, "freq1", "5分钟");
    let freq2 = get_str_param(params, "freq2", "1分钟");

    let k1 = format!("{}#{}", freq1, freq2);
    let k2 = "MACD交叉";
    let k3 = "联立V230518";

    let Some(c1) = cat.get_czsc(freq1) else {
        return make_signal_v1(&k1, k2, k3, "其他");
    };
    let Some(c2) = cat.get_czsc(freq2) else {
        return make_signal_v1(&k1, k2, k3, "其他");
    };
    if c1.bars_raw.len() < 50 || c2.bars_raw.len() < 50 {
        return make_signal_v1(&k1, k2, k3, "其他");
    }

    let cache_key = "MACD12#26#9";
    let mut c1_cache = TaCache::new();
    let mut c2_cache = TaCache::new();
    update_macd_cache(c1, cache_key, 12, 26, 9, &mut c1_cache);
    update_macd_cache(c2, cache_key, 12, 26, 9, &mut c2_cache);
    let c1_macd_map = macd_map(&c1_cache, cache_key);
    let c2_macd_map = macd_map(&c2_cache, cache_key);

    let c1_bars: Vec<&RawBar> = get_sub_elements(&c1.bars_raw, 1, 8).iter().collect();
    let c2_bars: Vec<&RawBar> = get_sub_elements(&c2.bars_raw, 1, 50).iter().collect();
    if c1_bars.len() < 2 || c2_bars.len() < 2 {
        return make_signal_v1(&k1, k2, k3, "其他");
    }

    let c1_macd: Vec<f64> = c1_bars
        .iter()
        .filter_map(|b| c1_macd_map.get(&b.id).copied())
        .collect();
    if c1_macd.len() != c1_bars.len() {
        return make_signal_v1(&k1, k2, k3, "其他");
    }

    if c1_macd.last().copied().unwrap_or(0.0) > 0.0
        && c1_macd.iter().filter(|x| **x > 0.0).count() != c1_macd.len()
    {
        let c1_gold = cross_up_bars(&c1_bars, &c1_macd_map);
        if let Some(last_gold) = c1_gold.last() {
            let c2_after: Vec<&RawBar> = c2_bars
                .iter()
                .copied()
                .filter(|x| x.dt > last_gold.dt)
                .collect();
            if c2_after.len() > 3 {
                let c2_gold = cross_up_bars(&c2_after, &c2_macd_map);
                if c2_gold.len() == 1 {
                    return make_signal_v1(&k1, k2, k3, "看多");
                }
            }
        }
    }

    if c1_macd.last().copied().unwrap_or(0.0) < 0.0
        && c1_macd.iter().filter(|x| **x < 0.0).count() != c1_macd.len()
    {
        let c1_dead = cross_down_bars(&c1_bars, &c1_macd_map);
        if let Some(last_dead) = c1_dead.last() {
            let c2_after: Vec<&RawBar> = c2_bars
                .iter()
                .copied()
                .filter(|x| x.dt > last_dead.dt)
                .collect();
            if c2_after.len() > 3 {
                let c2_dead = cross_down_bars(&c2_after, &c2_macd_map);
                if c2_dead.len() == 1 {
                    return make_signal_v1(&k1, k2, k3, "看空");
                }
            }
        }
    }

    make_signal_v1(&k1, k2, k3, "其他")
}

/// cat_macd_V230520：高低级别 MACD 缩柱联立信号
///
/// 参数模板：`"{freq1}#{freq2}_MACD交叉_联立V230520"`
///
/// 信号逻辑：
/// 1. `freq1` 最近三根 MACD 连续抬升且历史出现负值时，检查 `freq2` 的金死叉结构，满足判 `看多`；
/// 2. `freq1` 最近三根 MACD 连续下压且历史出现正值时，检查 `freq2` 的死金叉结构，满足判 `看空`；
/// 3. 同时给出触发时 `DEA` 在零轴上下的位置 `v2`。
///
/// 信号列表示例：
/// - `Signal('日线#60分钟_MACD交叉_联立V230520_看多_零轴上方_任意_0')`
/// - `Signal('日线#60分钟_MACD交叉_联立V230520_看空_零轴下方_任意_0')`
///
/// 参数说明：
/// - `freq1`：高一级别周期，默认 `5分钟`；
/// - `freq2`：低一级别周期，默认 `1分钟`。
/// 对齐说明：交叉次数、顺序和阈值条件与 Python `cat_macd_V230520` 一致。
#[signal(
    category = "trader",
    name = "cat_macd_V230520",
    template = "{freq1}#{freq2}_MACD交叉_联立V230520",
    opcode = "CatMacdV230520",
    param_kind = "CatMacdV230520"
)]
pub fn cat_macd_v230520(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let freq1 = get_str_param(params, "freq1", "5分钟");
    let freq2 = get_str_param(params, "freq2", "1分钟");

    let k1 = format!("{}#{}", freq1, freq2);
    let k2 = "MACD交叉";
    let k3 = "联立V230520";

    let Some(c1) = cat.get_czsc(freq1) else {
        return make_signal_v1(&k1, k2, k3, "其他");
    };
    let Some(c2) = cat.get_czsc(freq2) else {
        return make_signal_v1(&k1, k2, k3, "其他");
    };
    if c1.bars_raw.len() < 50 || c2.bars_raw.len() < 50 {
        return make_signal_v1(&k1, k2, k3, "其他");
    }

    let cache_key = "MACD12#26#9";
    let mut c1_cache = TaCache::new();
    let mut c2_cache = TaCache::new();
    update_macd_cache(c1, cache_key, 12, 26, 9, &mut c1_cache);
    update_macd_cache(c2, cache_key, 12, 26, 9, &mut c2_cache);
    let c1_macd_map = macd_map(&c1_cache, cache_key);
    let c2_macd_map = macd_map(&c2_cache, cache_key);
    let c2_dea_map = dea_map(&c2_cache, cache_key);

    let c1_bars: Vec<&RawBar> = get_sub_elements(&c1.bars_raw, 1, 8).iter().collect();
    let c2_bars: Vec<&RawBar> = get_sub_elements(&c2.bars_raw, 1, 50).iter().collect();
    if c1_bars.len() < 3 || c2_bars.len() < 2 {
        return make_signal_v1(&k1, k2, k3, "其他");
    }

    let c1_macd: Vec<f64> = c1_bars
        .iter()
        .filter_map(|b| c1_macd_map.get(&b.id).copied())
        .collect();
    if c1_macd.len() != c1_bars.len() {
        return make_signal_v1(&k1, k2, k3, "其他");
    }

    let li = c1_macd.len() - 1;
    let up3 = c1_macd[li - 2] < c1_macd[li - 1] && c1_macd[li - 1] < c1_macd[li];
    let down3 = c1_macd[li - 2] > c1_macd[li - 1] && c1_macd[li - 1] > c1_macd[li];

    if up3
        && c1_macd
            .iter()
            .copied()
            .fold(f64::INFINITY, f64::min)
            < 0.0
    {
        let min_bar = c1_bars
            .iter()
            .min_by(|a, b| a.low.partial_cmp(&b.low).unwrap_or(std::cmp::Ordering::Equal))
            .copied();
        if let Some(min_bar) = min_bar {
            let c2_after: Vec<&RawBar> = c2_bars
                .iter()
                .copied()
                .filter(|x| x.dt > min_bar.dt)
                .collect();
            if c2_after.len() > 3 {
                let last_bar = *c2_after.last().unwrap();
                let c2_vals: Vec<f64> = c2_after
                    .iter()
                    .filter_map(|b| c2_macd_map.get(&b.id).copied())
                    .collect();
                if !c2_vals.is_empty() {
                    let min_macd = c2_vals.iter().copied().fold(f64::INFINITY, f64::min);
                    let max_macd = c2_vals.iter().copied().fold(f64::NEG_INFINITY, f64::max);
                    let c2_gold = cross_up_bars(&c2_after, &c2_macd_map);
                    let c2_dead = cross_down_bars(&c2_after, &c2_macd_map);
                    if c2_gold.len() == 1
                        && c2_dead.len() == 1
                        && c2_gold[0].id - c2_dead[0].id >= 5
                        && last_bar.dt == c2_gold[0].dt
                        && c2_gold[0].dt > c2_dead[0].dt
                        && min_macd.abs() > max_macd.abs() * 0.3
                    {
                        let dea = *c2_dea_map.get(&c2_gold[0].id).unwrap_or(&0.0);
                        let v2 = if dea > 0.0 { "零轴上方" } else { "零轴下方" };
                        return make_signal(&k1, k2, k3, "看多", v2);
                    }
                }
            }
        }
    }

    if down3
        && c1_macd
            .iter()
            .copied()
            .fold(f64::NEG_INFINITY, f64::max)
            > 0.0
    {
        let max_bar = c1_bars
            .iter()
            .max_by(|a, b| a.high.partial_cmp(&b.high).unwrap_or(std::cmp::Ordering::Equal))
            .copied();
        if let Some(max_bar) = max_bar {
            let c2_after: Vec<&RawBar> = c2_bars
                .iter()
                .copied()
                .filter(|x| x.dt > max_bar.dt)
                .collect();
            if c2_after.len() > 3 {
                let last_bar = *c2_after.last().unwrap();
                let c2_vals: Vec<f64> = c2_after
                    .iter()
                    .filter_map(|b| c2_macd_map.get(&b.id).copied())
                    .collect();
                if !c2_vals.is_empty() {
                    let min_macd = c2_vals.iter().copied().fold(f64::INFINITY, f64::min);
                    let max_macd = c2_vals.iter().copied().fold(f64::NEG_INFINITY, f64::max);
                    let c2_gold = cross_up_bars(&c2_after, &c2_macd_map);
                    let c2_dead = cross_down_bars(&c2_after, &c2_macd_map);
                    if c2_dead.len() == 1
                        && c2_gold.len() == 1
                        && c2_dead[0].id - c2_gold[0].id >= 5
                        && last_bar.dt == c2_dead[0].dt
                        && c2_dead[0].dt > c2_gold[0].dt
                        && max_macd.abs() > min_macd.abs() * 0.3
                    {
                        let dea = *c2_dea_map.get(&c2_dead[0].id).unwrap_or(&0.0);
                        let v2 = if dea > 0.0 { "零轴上方" } else { "零轴下方" };
                        return make_signal(&k1, k2, k3, "看空", v2);
                    }
                }
            }
        }
    }

    make_signal_v1(&k1, k2, k3, "其他")
}
