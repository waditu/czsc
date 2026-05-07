use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::math::{median_abs, percentile_linear, std_pop};
use crate::utils::sig::{
    get_sub_elements, get_usize_param, make_kline_signal_v1, make_kline_signal_v2,
    make_kline_signal_v3,
};
use crate::utils::ta::{MacdField, macd_snapshot_field_value, update_macd_cache};
use crate::utils::zdy::{find_peaks_valleys, is_valid_zs, macd_cache_maps};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::mark::Mark;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::zs::ZS;
use czsc_signal_macros::signal;
use std::collections::HashMap;
#[allow(clippy::too_many_arguments)]
fn snapshot_macd_values_from_raw_bars(
    c: &CZSC,
    mc: &crate::types::MacdSeries,
    id_to_idx: &HashMap<i32, usize>,
    raw_bars: &[RawBar],
    short: usize,
    long: usize,
    signal: usize,
    field: MacdField,
    snapshot_overrides: &mut HashMap<i32, (f64, f64, f64)>,
) -> Vec<f64> {
    raw_bars
        .iter()
        .filter_map(|rb| {
            macd_snapshot_field_value(
                c,
                mc,
                id_to_idx,
                rb,
                short,
                long,
                signal,
                field,
                snapshot_overrides,
            )
        })
        .filter(|x| x.is_finite())
        .collect()
}

/// zdy_bi_end_V230406：停顿分型辅助判断笔结束
///
/// 参数模板：`"{freq}_D0停顿分型_BE辅助V230406"`
///
/// 信号逻辑：
/// 1. 要求最后一笔已完成、UBI 处于 4 到 6 根之间，且最后一笔长度不少于 7；
/// 2. 向下笔后若 UBI 后段收盘价上破底分型高点判定 `看多`，向上笔后若 UBI 后段收盘价下破顶分型低点判定 `看空`；
/// 3. 再补充内部停顿与是否仍处于分型区间，输出 `v2/v3`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0停顿分型_BE辅助V230406_看多_内部底停顿_底分区间_0')`
/// - `Signal('60分钟_D0停顿分型_BE辅助V230406_看空_内部顶停顿_顶分区间_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 仅在最后一笔结束后、未完成笔较短时评估停顿分型。
/// 对齐说明：与 Python `czsc.signals.zdy_bi_end_V230406` 保持一致。
#[signal(category = "kline", name = "zdy_bi_end_V230406", template = "{freq}_D0停顿分型_BE辅助V230406", opcode = "ZdyBiEndV230406", param_kind = "ZdyBiEndV230406")]
pub fn zdy_bi_end_v230406(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "D0停顿分型";
    let k3 = "BE辅助V230406";
    if c.bi_list.len() < 3 || c.bars_ubi.len() > 6 || c.bars_ubi.len() < 4 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_bi = c.bi_list.last().unwrap();
    let last_fx_raw = last_bi
        .fx_b
        .elements
        .last()
        .map(|x| x.elements.clone())
        .unwrap_or_default();
    if last_fx_raw.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_high = last_fx_raw.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let last_low = last_fx_raw.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let last_bar = c.bars_raw.last().unwrap();
    if last_bi.fx_b.elements.last().unwrap().dt >= last_bar.dt || last_bi.get_length() < 7 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_bars: Vec<RawBar> = c.bars_ubi[3..]
        .iter()
        .flat_map(|x| x.elements.iter().cloned())
        .collect::<Vec<_>>();
    let max_close = last_bars.iter().map(|x| x.close).fold(f64::NEG_INFINITY, f64::max);
    let min_close = last_bars.iter().map(|x| x.close).fold(f64::INFINITY, f64::min);
    let v1 = if last_bi.direction == Direction::Down && max_close > last_high {
        "看多"
    } else if last_bi.direction == Direction::Up && min_close < last_low {
        "看空"
    } else {
        "其他"
    };
    if v1 == "其他" {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let mut v2 = "任意";
    if v1 == "看多" && last_bi.fxs.len() >= 4 {
        for i in 0..last_bi.fxs.len() - 1 {
            let fx1 = &last_bi.fxs[i];
            let fx2 = &last_bi.fxs[i + 1];
            let fx2_raw: Vec<RawBar> = fx2
                .elements
                .iter()
                .flat_map(|x| x.elements.iter().cloned())
                .collect::<Vec<_>>();
            if fx1.mark == Mark::D && fx2.mark == Mark::G && fx2_raw.iter().map(|x| x.close).fold(f64::NEG_INFINITY, f64::max) > fx1.elements.last().unwrap().high {
                v2 = "内部底停顿";
            }
        }
    }
    if v1 == "看空" && last_bi.fxs.len() >= 4 {
        for i in 0..last_bi.fxs.len() - 1 {
            let fx1 = &last_bi.fxs[i];
            let fx2 = &last_bi.fxs[i + 1];
            let fx2_raw: Vec<RawBar> = fx2
                .elements
                .iter()
                .flat_map(|x| x.elements.iter().cloned())
                .collect::<Vec<_>>();
            if fx1.mark == Mark::G && fx2.mark == Mark::D && fx2_raw.iter().map(|x| x.close).fold(f64::INFINITY, f64::min) < fx1.elements.last().unwrap().low {
                v2 = "内部顶停顿";
            }
        }
    }
    let mut v3 = "任意";
    if v1 == "看多" && last_bar.close < last_bi.fx_b.high {
        v3 = "底分区间";
    }
    if v1 == "看空" && last_bar.close > last_bi.fx_b.low {
        v3 = "顶分区间";
    }
    make_kline_signal_v3(&k1, k2, k3, v1, v2, v3)
}

/// zdy_bi_end_V230407：连续停顿分型辅助判断笔结束
///
/// 参数模板：`"{freq}_D0停顿分型_BE辅助V230407"`
///
/// 信号逻辑：
/// 1. 与 `V230406` 共用边界条件，但要求突破发生在最后分型之后的连续收盘序列上；
/// 2. 向下笔后若连续收盘上破底分型高点判定 `看多`，向上笔后若连续收盘下破顶分型低点判定 `看空`；
/// 3. 再检查笔内相邻分型是否形成内部停顿，补充 `v2`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0停顿分型_BE辅助V230407_看多_内部底停顿_任意_0')`
/// - `Signal('60分钟_D0停顿分型_BE辅助V230407_看空_内部顶停顿_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 连续突破要求突破 K 线在时间上连续，不接受中途回落后再次突破。
/// 对齐说明：与 Python `czsc.signals.zdy_bi_end_V230407` 保持一致。
#[signal(category = "kline", name = "zdy_bi_end_V230407", template = "{freq}_D0停顿分型_BE辅助V230407", opcode = "ZdyBiEndV230407", param_kind = "ZdyBiEndV230407")]
pub fn zdy_bi_end_v230407(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "D0停顿分型";
    let k3 = "BE辅助V230407";
    if c.bi_list.len() < 3 || c.bars_ubi.len() > 6 || c.bars_ubi.len() < 4 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_bi = c.bi_list.last().unwrap();
    let last_fx_raw = last_bi
        .fx_b
        .elements
        .last()
        .map(|x| x.elements.clone())
        .unwrap_or_default();
    if last_fx_raw.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_high = last_fx_raw.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let last_low = last_fx_raw.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let last_bar = c.bars_raw.last().unwrap();
    if last_bi.fx_b.elements.last().unwrap().dt >= last_bar.dt || last_bi.get_length() < 7 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_bars: Vec<RawBar> = c.bars_ubi
        .iter()
        .flat_map(|x| x.elements.iter().cloned())
        .filter(|x| x.dt >= last_bi.fx_b.elements.last().unwrap().dt)
        .collect::<Vec<_>>();
    let mut v1 = "其他";
    if last_bi.direction == Direction::Down && last_bars.last().unwrap().close > last_high {
        let idx: Vec<usize> = last_bars.iter().enumerate().filter(|(_, x)| x.close > last_high).map(|(i, _)| i).collect();
        if idx.len() == 1 || (idx.len() > 1 && idx[idx.len() - 1] - idx[0] == idx.len() - 1) {
            v1 = "看多";
        }
    } else if last_bi.direction == Direction::Up && last_bars.last().unwrap().close < last_low {
        let idx: Vec<usize> = last_bars.iter().enumerate().filter(|(_, x)| x.close < last_low).map(|(i, _)| i).collect();
        if idx.len() == 1 || (idx.len() > 1 && idx[idx.len() - 1] - idx[0] == idx.len() - 1) {
            v1 = "看空";
        }
    }
    if v1 == "其他" {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let mut v2 = "任意";
    if v1 == "看多" && last_bi.fxs.len() >= 4 {
        for i in 0..last_bi.fxs.len() - 1 {
            let fx1 = &last_bi.fxs[i];
            let fx2 = &last_bi.fxs[i + 1];
            let fx2_raw: Vec<RawBar> = fx2
                .elements
                .iter()
                .flat_map(|x| x.elements.iter().cloned())
                .collect::<Vec<_>>();
            if fx1.mark == Mark::D && fx2.mark == Mark::G && fx2_raw.iter().map(|x| x.close).fold(f64::NEG_INFINITY, f64::max) > fx1.elements.last().unwrap().high {
                v2 = "内部底停顿";
            }
        }
    }
    if v1 == "看空" && last_bi.fxs.len() >= 4 {
        for i in 0..last_bi.fxs.len() - 1 {
            let fx1 = &last_bi.fxs[i];
            let fx2 = &last_bi.fxs[i + 1];
            let fx2_raw: Vec<RawBar> = fx2
                .elements
                .iter()
                .flat_map(|x| x.elements.iter().cloned())
                .collect::<Vec<_>>();
            if fx1.mark == Mark::G && fx2.mark == Mark::D && fx2_raw.iter().map(|x| x.close).fold(f64::INFINITY, f64::min) < fx1.elements.last().unwrap().low {
                v2 = "内部顶停顿";
            }
        }
    }
    make_kline_signal_v2(&k1, k2, k3, v1, v2)
}

/// zdy_zs_V230423：中枢形态辅助识别上涨下跌结构
///
/// 参数模板：`"{freq}_D{di}中枢形态_BS辅助V230423"`
///
/// 信号逻辑：
/// 1. 依次尝试最近 `9/7/5` 笔，取首尾笔之外的中间笔构造中枢；
/// 2. 要求中枢有效，且中枢高度至少达到首笔波动的三分之一；
/// 3. 若首笔与末笔分别对应区间最低点和最高点，则判定 `上涨/下跌` 并输出笔数。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1中枢形态_BS辅助V230423_上涨_5笔_任意_0')`
/// - `Signal('60分钟_D1中枢形态_BS辅助V230423_下跌_7笔_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 仅在未完成笔不超过 7 根时评估，避免把延伸中的 UBI 当成已确认结构。
/// 对齐说明：与 Python `czsc.signals.zdy_zs_V230423` 保持一致。
#[signal(category = "kline", name = "zdy_zs_V230423", template = "{freq}_D{di}中枢形态_BS辅助V230423", opcode = "ZdyZsV230423", param_kind = "ZdyZsV230423")]
pub fn zdy_zs_v230423(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}中枢形态", di);
    let k3 = "BS辅助V230423";
    if c.bi_list.len() < 7 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    for n in [9, 7, 5] {
        let bis = get_sub_elements(&c.bi_list, di, n);
        if bis.len() != n {
            continue;
        }
        let bi1 = &bis[0];
        let zs = ZS::new(bis[1..n - 1].to_vec());
        if !(zs.is_valid() && zs.zg - zs.zd > (bi1.get_high() - bi1.get_low()) / 3.0) {
            continue;
        }
        let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
        let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
        if bi1.direction == Direction::Up && bi1.get_low() == min_low && bis.last().unwrap().get_high() == max_high {
            return make_kline_signal_v2(&k1, &k2, k3, "上涨", &format!("{}笔", n));
        }
        if bi1.direction == Direction::Down && bi1.get_high() == max_high && bis.last().unwrap().get_low() == min_low {
            return make_kline_signal_v2(&k1, &k2, k3, "下跌", &format!("{}笔", n));
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_zs_space_V230421：中枢空间辅助识别上涨下跌结构
///
/// 参数模板：`"{freq}_D{di}中枢空间_BS辅助V230421"`
///
/// 信号逻辑：
/// 1. 依次尝试最近 `9/7/5` 笔，取中间笔构造有效中枢；
/// 2. 对上涨结构，要求末笔离开中枢上沿的空间不小于首笔进入中枢前的空间；下跌结构反向判断；
/// 3. 满足空间对称性后输出 `上涨/下跌 + 笔数`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1中枢空间_BS辅助V230421_上涨_5笔_任意_0')`
/// - `Signal('60分钟_D1中枢空间_BS辅助V230421_下跌_9笔_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 仅对有效中枢做空间比较，无中枢时直接返回 `其他`。
/// 对齐说明：与 Python `czsc.signals.zdy_zs_space_V230421` 保持一致。
#[signal(category = "kline", name = "zdy_zs_space_V230421", template = "{freq}_D{di}中枢空间_BS辅助V230421", opcode = "ZdyZsSpaceV230421", param_kind = "ZdyZsSpaceV230421")]
pub fn zdy_zs_space_v230421(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}中枢空间", di);
    let k3 = "BS辅助V230421";
    if c.bi_list.len() < 7 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    for n in [9, 7, 5] {
        let bis = get_sub_elements(&c.bi_list, di, n);
        if bis.len() != n {
            continue;
        }
        let zs = ZS::new(bis[1..n - 1].to_vec());
        if !zs.is_valid() {
            continue;
        }
        let bi1 = &bis[0];
        let bi2 = &bis[n - 1];
        let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
        let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
        if bi1.direction == Direction::Up && bi1.get_low() == min_low && bi2.get_high() == max_high && bi2.get_high() - zs.zg >= zs.zd - bi1.get_low() {
            return make_kline_signal_v2(&k1, &k2, k3, "上涨", &format!("{}笔", n));
        }
        if bi1.direction == Direction::Down && bi1.get_high() == max_high && bi2.get_low() == min_low && zs.zd - bi2.get_low() >= bi1.get_high() - zs.zg {
            return make_kline_signal_v2(&k1, &k2, k3, "下跌", &format!("{}笔", n));
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_macd_bc_V230422：MACD 面积背驰辅助信号
///
/// 参数模板：`"{freq}_D{di}T{th}MACD面积背驰_BS辅助V230422"`
///
/// 信号逻辑：
/// 1. 依次尝试最近 `9/7/5` 笔，要求中间结构可构成有效中枢；
/// 2. 比较首笔与末笔内部 MACD 柱面积，并用 `th` 控制末笔面积相对首笔的阈值；
/// 3. 结合 DIF 零轴位置与首末笔高低点，判定 `上涨/下跌` 背驰并输出笔数。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T50MACD面积背驰_BS辅助V230422_上涨_5笔_任意_0')`
/// - `Signal('60分钟_D1T50MACD面积背驰_BS辅助V230422_下跌_7笔_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `th`：末笔面积相对首笔面积的百分比阈值，默认 `50`。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_bc_V230422` 保持一致。
#[signal(category = "kline", name = "zdy_macd_bc_V230422", template = "{freq}_D{di}T{th}MACD面积背驰_BS辅助V230422", opcode = "ZdyMacdBcV230422", param_kind = "ZdyMacdBcV230422")]
pub fn zdy_macd_bc_v230422(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 50) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}T{}MACD面积背驰", di, th as i32);
    let k3 = "BS辅助V230422";
    if c.bi_list.len() < 7 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let cache_key = "MACD12#26#9";
    update_macd_cache(c, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let id_to_idx: HashMap<i32, usize> = c
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();
    let mut snapshot_overrides = HashMap::new();
    for n in [9, 7, 5] {
        let bis = get_sub_elements(&c.bi_list, di, n);
        if bis.len() != n || !is_valid_zs(&bis[1..n - 1]) {
            continue;
        }
        let zs = ZS::new(bis[1..n - 1].to_vec());
        let bi1 = &bis[0];
        let bi2 = &bis[n - 1];
        let bi1_raw = bi1.get_raw_bars();
        let bi2_raw = bi2.get_raw_bars();
        let bi1_macd = snapshot_macd_values_from_raw_bars(
            c,
            mc,
            &id_to_idx,
            &bi1_raw[1..bi1_raw.len().saturating_sub(1)],
            12,
            26,
            9,
            MacdField::Macd,
            &mut snapshot_overrides,
        );
        let bi2_macd = snapshot_macd_values_from_raw_bars(
            c,
            mc,
            &id_to_idx,
            &bi2_raw[1..bi2_raw.len().saturating_sub(1)],
            12,
            26,
            9,
            MacdField::Macd,
            &mut snapshot_overrides,
        );
        if bi1_macd.is_empty() || bi2_macd.is_empty() {
            continue;
        }
        let bi1_dif = macd_snapshot_field_value(
            c,
            mc,
            &id_to_idx,
            &bi1_raw[bi1_raw.len() - 2],
            12,
            26,
            9,
            MacdField::Dif,
            &mut snapshot_overrides,
        )
        .unwrap_or(0.0);
        let bi2_dif = macd_snapshot_field_value(
            c,
            mc,
            &id_to_idx,
            &bi2_raw[bi2_raw.len() - 2],
            12,
            26,
            9,
            MacdField::Dif,
            &mut snapshot_overrides,
        )
        .unwrap_or(0.0);
        let zs_fxb_raw: Vec<RawBar> = zs.bis.iter().flat_map(|x| x.fx_b.elements.iter().flat_map(|nb| nb.elements.iter().cloned())).collect();
        let (bi1_area, bi2_area, dif_zero) = if bi1.direction == Direction::Up {
            (
                bi1_macd.iter().copied().filter(|x| *x > 0.0).sum::<f64>(),
                bi2_macd.iter().copied().filter(|x| *x > 0.0).sum::<f64>(),
                snapshot_macd_values_from_raw_bars(
                    c,
                    mc,
                    &id_to_idx,
                    &zs_fxb_raw,
                    12,
                    26,
                    9,
                    MacdField::Dif,
                    &mut snapshot_overrides,
                )
                .into_iter()
                .fold(f64::INFINITY, f64::min),
            )
        } else {
            (
                bi1_macd.iter().copied().filter(|x| *x < 0.0).sum::<f64>(),
                bi2_macd.iter().copied().filter(|x| *x < 0.0).sum::<f64>(),
                snapshot_macd_values_from_raw_bars(
                    c,
                    mc,
                    &id_to_idx,
                    &zs_fxb_raw,
                    12,
                    26,
                    9,
                    MacdField::Dif,
                    &mut snapshot_overrides,
                )
                .into_iter()
                .fold(f64::NEG_INFINITY, f64::max),
            )
        };
        if bi2_area > bi1_area * th / 100.0 {
            continue;
        }
        let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
        let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
        if bi1.direction == Direction::Up && bi1.get_low() == min_low && bi2.get_high() == max_high && dif_zero < 0.0 && bi1_dif > bi2_dif && bi2_dif > 0.0 {
            return make_kline_signal_v2(&k1, &k2, k3, "上涨", &format!("{}笔", n));
        }
        if bi1.direction == Direction::Down && bi1.get_high() == max_high && bi2.get_low() == min_low && dif_zero > 0.0 && bi1_dif < bi2_dif && bi2_dif < 0.0 {
            return make_kline_signal_v2(&k1, &k2, k3, "下跌", &format!("{}笔", n));
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_macd_bs1_V230422：MACD 一买一卖辅助信号
///
/// 参数模板：`"{freq}_D{di}T{th}MACD_BS1辅助V230422"`
///
/// 信号逻辑：
/// 1. 依次尝试最近 `13/11/9/7/5` 笔，要求中间结构构成有效中枢；
/// 2. 比较首笔与末笔的 MACD 柱面积、末笔起点 DIF 与中枢 DIF 极值；
/// 3. 满足首末笔方向、极值位置和 DIF 强弱关系时输出 `看多/看空 + 上涨/下跌N笔`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T50MACD_BS1辅助V230422_看空_上涨5笔_任意_0')`
/// - `Signal('60分钟_D1T50MACD_BS1辅助V230422_看多_下跌7笔_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `th`：末笔 MACD 面积占首笔面积的最大百分比，默认 `50`。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_bs1_V230422` 保持一致。
#[signal(category = "kline", name = "zdy_macd_bs1_V230422", template = "{freq}_D{di}T{th}MACD_BS1辅助V230422", opcode = "ZdyMacdBs1V230422", param_kind = "ZdyMacdBs1V230422")]
pub fn zdy_macd_bs1_v230422(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 50) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}T{}MACD", di, th as i32);
    let k3 = "BS1辅助V230422";
    if c.bi_list.len() < 7 || c.bars_ubi.len() > 9 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let (dif_map, _, macd_map) = macd_cache_maps(c, 26, 12, 9, cache);
    for n in [13, 11, 9, 7, 5] {
        let bis = get_sub_elements(&c.bi_list, di, n);
        if bis.len() != n || !is_valid_zs(&bis[1..n - 1]) {
            continue;
        }
        let zs = ZS::new(bis[1..n - 1].to_vec());
        let bi1 = &bis[0];
        let bi2 = &bis[n - 1];
        let bi1_raw = bi1.get_raw_bars();
        let bi2_raw = bi2.get_raw_bars();
        if bi1_raw.len() < 3 || bi2_raw.len() < 3 {
            continue;
        }
        let bi1_area = bi1_raw[1..bi1_raw.len() - 1].iter().filter_map(|x| macd_map.get(&x.id).copied()).map(f64::abs).sum::<f64>();
        let bi2_area = bi2_raw[1..bi2_raw.len() - 1].iter().filter_map(|x| macd_map.get(&x.id).copied()).map(f64::abs).sum::<f64>();
        let bi1_dif = *dif_map.get(&bi1_raw[bi1_raw.len() - 2].id).unwrap_or(&0.0);
        let bi2_dif = *dif_map.get(&bi2_raw[bi2_raw.len() - 2].id).unwrap_or(&0.0);
        let bi2_start_dif = *dif_map.get(&bi2_raw[1].id).unwrap_or(&0.0);
        let zs_dif = if bi1.direction == Direction::Up {
            zs.bis
                .iter()
                .filter(|x| x.direction == Direction::Up)
                .flat_map(|x| x.fx_b.elements.iter().flat_map(|nb| nb.elements.iter()))
                .filter_map(|x| dif_map.get(&x.id).copied())
                .fold(f64::NEG_INFINITY, f64::max)
        } else {
            zs.bis
                .iter()
                .filter(|x| x.direction == Direction::Down)
                .flat_map(|x| x.fx_b.elements.iter().flat_map(|nb| nb.elements.iter()))
                .filter_map(|x| dif_map.get(&x.id).copied())
                .fold(f64::INFINITY, f64::min)
        };
        if bi2_area > bi1_area * th / 100.0 {
            continue;
        }
        let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
        let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
        if bi1.direction == Direction::Up
            && bi1.get_low() == min_low
            && bi2.get_high() == max_high
            && bi2_start_dif < zs_dif.abs() * 0.5
            && bi1_dif > bi2_dif
            && bi2_dif > zs_dif
            && zs_dif > 0.0
        {
            return make_kline_signal_v2(&k1, &k2, k3, "看空", &format!("上涨{}笔", n));
        }
        if bi1.direction == Direction::Down
            && bi1.get_high() == max_high
            && bi2.get_low() == min_low
            && bi2_start_dif > zs_dif.abs() * 0.5
            && 0.0 > zs_dif
            && zs_dif > bi2_dif
            && bi2_dif > bi1_dif
        {
            return make_kline_signal_v2(&k1, &k2, k3, "看多", &format!("下跌{}笔", n));
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_macd_dif_V230516：DIF 走平后的反向观察信号
///
/// 参数模板：`"{freq}_D{di}DIF走平_BS辅助V230516"`
///
/// 信号逻辑：
/// 1. 取最近 10 根 K 线的 DIF 变化，计算相邻差分的平均波动阈值；
/// 2. 若最新 DIF 相对前一根不再继续大幅下行，结合 MACD 绿柱位置判定 `看多`；反向同理判定 `看空`；
/// 3. 用 `绿柱远离/红柱远离/柱子否定` 说明当前柱体是否支持反转观察。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1DIF走平_BS辅助V230516_看多_绿柱远离_任意_0')`
/// - `Signal('60分钟_D1DIF走平_BS辅助V230516_看空_红柱远离_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根 K 线，默认 `1`；
/// - 固定使用 `12,26,9` MACD 参数，并观察最近 10 根 K 线。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_dif_V230516` 保持一致。
#[signal(category = "kline", name = "zdy_macd_dif_V230516", template = "{freq}_D{di}DIF走平_BS辅助V230516", opcode = "ZdyMacdDifV230516", param_kind = "ZdyMacdDifV230516")]
pub fn zdy_macd_dif_v230516(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}DIF走平", di);
    let k3 = "BS辅助V230516";
    if c.bars_raw.len() < 12 + di {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let (dif_map, _, macd_map) = macd_cache_maps(c, 12, 26, 9, cache);
    let bars = get_sub_elements(&c.bars_raw, di, 10);
    let dif: Vec<f64> = bars.iter().filter_map(|x| dif_map.get(&x.id).copied()).collect();
    if dif.len() < 2 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let dif_th = dif.windows(2).map(|w| (w[0] - w[1]).abs()).sum::<f64>() / dif.len() as f64 * 0.2;
    let mut v1 = "其他";
    let mut v2 = "其他";
    if dif[dif.len() - 1] - dif[dif.len() - 2] > -dif_th {
        let min_macd = bars.iter().filter_map(|x| macd_map.get(&x.id).copied()).fold(f64::INFINITY, f64::min);
        v1 = "看多";
        v2 = if dif[dif.len() - 1] < min_macd * 2.5 { "绿柱远离" } else { "柱子否定" };
    }
    if dif[dif.len() - 1] - dif[dif.len() - 2] < dif_th {
        let max_macd = bars.iter().filter_map(|x| macd_map.get(&x.id).copied()).fold(f64::NEG_INFINITY, f64::max);
        v1 = "看空";
        v2 = if dif[dif.len() - 1] > max_macd * 2.5 { "红柱远离" } else { "柱子否定" };
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// zdy_macd_dif_V230517：MACD 开仓辅助信号
///
/// 参数模板：`"{freq}_D{di}MACD开仓_BS辅助V230517"`
///
/// 信号逻辑：
/// 1. 取最近 20 根 K 线的 DIF 与 MACD 柱体；
/// 2. 若最新 DIF 重新站上零轴或 MACD 柱发生金叉/死叉/飞吻形态，则分别判定 `看多/看空`；
/// 3. 未出现明确开仓形态时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD开仓_BS辅助V230517_看多_MACD金叉_任意_0')`
/// - `Signal('60分钟_D1MACD开仓_BS辅助V230517_看空_DIF破零轴_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根 K 线，默认 `1`；
/// - 固定使用 `12,26,9` MACD 参数，至少要求 50 根原始 K 线预热。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_dif_V230517` 保持一致。
#[signal(category = "kline", name = "zdy_macd_dif_V230517", template = "{freq}_D{di}MACD开仓_BS辅助V230517", opcode = "ZdyMacdDifV230517", param_kind = "ZdyMacdDifV230517")]
pub fn zdy_macd_dif_v230517(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}MACD开仓", di);
    let k3 = "BS辅助V230517";
    if c.bars_raw.len() < 50 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let (dif_map, _, macd_map) = macd_cache_maps(c, 12, 26, 9, cache);
    let bars = get_sub_elements(&c.bars_raw, di, 20);
    let macd: Vec<f64> = bars.iter().filter_map(|x| macd_map.get(&x.id).copied()).collect();
    let dif: Vec<f64> = bars.iter().filter_map(|x| dif_map.get(&x.id).copied()).collect();
    if dif.last().copied().unwrap_or(0.0) > 0.0 {
        let mut v2 = None;
        if dif[..dif.len() - 1].iter().all(|x| *x < 0.0) {
            v2 = Some("DIF破零轴");
        }
        if macd[macd.len() - 1] > 0.0 && macd[macd.len() - 2] < 0.0 {
            v2 = Some("MACD金叉");
        }
        if macd[macd.len() - 5] > macd[macd.len() - 4] && macd[macd.len() - 4] > macd[macd.len() - 3] && macd[macd.len() - 3] > macd[macd.len() - 2] && macd[macd.len() - 2] < macd[macd.len() - 1] && macd[macd.len() - 2] > 0.0 {
            v2 = Some("MACD飞吻");
        }
        if let Some(v2) = v2 {
            return make_kline_signal_v2(&k1, &k2, k3, "看多", v2);
        }
    }
    if dif.last().copied().unwrap_or(0.0) < 0.0 {
        let mut v2 = None;
        if dif[..dif.len() - 1].iter().all(|x| *x > 0.0) {
            v2 = Some("DIF破零轴");
        }
        if macd[macd.len() - 1] < 0.0 && macd[macd.len() - 2] > 0.0 {
            v2 = Some("MACD死叉");
        }
        if macd[macd.len() - 5] < macd[macd.len() - 4] && macd[macd.len() - 4] < macd[macd.len() - 3] && macd[macd.len() - 3] < macd[macd.len() - 2] && macd[macd.len() - 2] > macd[macd.len() - 1] && macd[macd.len() - 2] < 0.0 {
            v2 = Some("MACD飞吻");
        }
        if let Some(v2) = v2 {
            return make_kline_signal_v2(&k1, &k2, k3, "看空", v2);
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_macd_V230518：MACD 交叉计数信号
///
/// 参数模板：`"{freq}_D{di}MACD交叉N{n}_BS辅助V230518"`
///
/// 信号逻辑：
/// 1. 取最近 `n + 1` 根 K 线的 MACD 柱值；
/// 2. 根据最新柱体正负判定 `金叉/死叉` 方向；
/// 3. 从最新柱开始逆序统计同号连续根数，输出 `第N次` 或 `超计数范围`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD交叉N9_BS辅助V230518_金叉_第3次_任意_0')`
/// - `Signal('60分钟_D1MACD交叉N9_BS辅助V230518_死叉_超计数范围_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根 K 线，默认 `1`；
/// - `n`：最大统计窗口，默认 `9`。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_V230518` 保持一致。
#[signal(category = "kline", name = "zdy_macd_V230518", template = "{freq}_D{di}MACD交叉N{n}_BS辅助V230518", opcode = "ZdyMacdV230518", param_kind = "ZdyMacdV230518")]
pub fn zdy_macd_v230518(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 9);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}MACD交叉N{}", di, n);
    let k3 = "BS辅助V230518";
    if c.bars_raw.len() < 50 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let (_, _, macd_map) = macd_cache_maps(c, 12, 26, 9, cache);
    let bars = get_sub_elements(&c.bars_raw, di, n + 1);
    let macd: Vec<f64> = bars.iter().filter_map(|x| macd_map.get(&x.id).copied()).collect();
    let v1 = if macd.last().copied().unwrap_or(0.0) > 0.0 { "金叉" } else { "死叉" };
    let mut count = 0usize;
    for m in macd.iter().rev() {
        if (*m > 0.0 && macd[macd.len() - 1] > 0.0) || (*m < 0.0 && macd[macd.len() - 1] < 0.0) {
            count += 1;
        } else {
            break;
        }
    }
    if count == n + 1 {
        return make_kline_signal_v2(&k1, &k2, k3, v1, "超计数范围");
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, &format!("第{}次", count))
}

/// zdy_macd_V230519：MACD 连续缩柱信号
///
/// 参数模板：`"{freq}_D{di}N{n}MACD缩柱_BS辅助V230519"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 根 K 线的 MACD 柱值；
/// 2. 若全部为正且柱体连续缩短，判定 `多头连续缩柱`；
/// 3. 若全部为负且绝对值连续缩短，判定 `空头连续缩柱`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N3MACD缩柱_BS辅助V230519_多头连续缩柱_任意_任意_0')`
/// - `Signal('60分钟_D1N3MACD缩柱_BS辅助V230519_空头连续缩柱_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根 K 线，默认 `1`；
/// - `n`：连续缩柱的观察窗口，默认 `3`。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_V230519` 保持一致。
#[signal(category = "kline", name = "zdy_macd_V230519", template = "{freq}_D{di}N{n}MACD缩柱_BS辅助V230519", opcode = "ZdyMacdV230519", param_kind = "ZdyMacdV230519")]
pub fn zdy_macd_v230519(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 3);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}MACD缩柱", di, n);
    let k3 = "BS辅助V230519";
    if c.bars_raw.len() < 50 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let (_, _, macd_map) = macd_cache_maps(c, 12, 26, 9, cache);
    let bars = get_sub_elements(&c.bars_raw, di, n);
    let macd: Vec<f64> = bars.iter().filter_map(|x| macd_map.get(&x.id).copied()).collect();
    if macd.iter().all(|x| *x > 0.0) && macd.windows(2).all(|w| w[1] < w[0]) {
        return make_kline_signal_v1(&k1, &k2, k3, "多头连续缩柱");
    }
    if macd.iter().all(|x| *x < 0.0) && macd.windows(2).all(|w| w[1] > w[0]) {
        return make_kline_signal_v1(&k1, &k2, k3, "空头连续缩柱");
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_macd_dif_iqr_V230521：DIF 走平 IQR 版本辅助信号
///
/// 参数模板：`"{freq}_D{di}DIF走平IQR_BS辅助V230521"`
///
/// 信号逻辑：
/// 1. 取最近 100 根 K 线的 DIF 序列，计算四分位距 `IQR`；
/// 2. 若最近 3 根 DIF 振幅小于 `IQR`，视为 DIF 走平；
/// 3. 再结合最新 MACD 柱正负和 DIF 与柱体距离，输出 `看多/看空 + 远离/否定`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1DIF走平IQR_BS辅助V230521_看多_绿柱远离_任意_0')`
/// - `Signal('60分钟_D1DIF走平IQR_BS辅助V230521_看空_红柱远离_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根 K 线，默认 `1`；
/// - 固定使用最近 100 根 K 线做 IQR 估计，至少要求 50 根原始 K 线预热。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_dif_iqr_V230521` 保持一致。
#[signal(category = "kline", name = "zdy_macd_dif_iqr_V230521", template = "{freq}_D{di}DIF走平IQR_BS辅助V230521", opcode = "ZdyMacdDifIqrV230521", param_kind = "ZdyMacdDifIqrV230521")]
pub fn zdy_macd_dif_iqr_v230521(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}DIF走平IQR", di);
    let k3 = "BS辅助V230521";
    if c.bars_raw.len() < 50 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let (dif_map, _, macd_map) = macd_cache_maps(c, 12, 26, 9, cache);
    let bars = get_sub_elements(&c.bars_raw, di, 100);
    let macd = macd_map.get(&bars.last().unwrap().id).copied().unwrap_or(0.0) * 2.0;
    let dif: Vec<f64> = bars.iter().filter_map(|x| dif_map.get(&x.id).copied()).collect();
    let q3 = percentile_linear(&dif, 75.0).unwrap_or(0.0);
    let q1 = percentile_linear(&dif, 25.0).unwrap_or(0.0);
    let iqr = q3 - q1;
    if dif[dif.len() - 3..].iter().copied().fold(f64::NEG_INFINITY, f64::max) - dif[dif.len() - 3..].iter().copied().fold(f64::INFINITY, f64::min) < iqr && macd < 0.0 {
        return make_kline_signal_v2(&k1, &k2, k3, "看多", if dif[dif.len() - 1] < macd { "绿柱远离" } else { "柱子否定" });
    }
    if dif[dif.len() - 3..].iter().copied().fold(f64::NEG_INFINITY, f64::max) - dif[dif.len() - 3..].iter().copied().fold(f64::INFINITY, f64::min) < iqr && macd > 0.0 {
        return make_kline_signal_v2(&k1, &k2, k3, "看空", if dif[dif.len() - 1] > macd { "红柱远离" } else { "柱子否定" });
    }
    make_kline_signal_v2(&k1, &k2, k3, "其他", "其他")
}

/// zdy_macd_V230527：MACD 因子远离统计信号
///
/// 参数模板：`"{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230527"`
///
/// 信号逻辑：
/// 1. 在最近 `w` 根 K 线内提取 `DIF/DEA/MACD` 之一作为统计因子；
/// 2. 用绝对值中位数与总体标准差构造远离阈值；
/// 3. 若最近 `n` 根中的最大绝对值超过阈值，则输出 `多头远离/空头远离`。
///
/// 信号列表示例：
/// - `Signal('60分钟_DIF远离W100N10T20_BS辅助V230527_多头远离_任意_任意_0')`
/// - `Signal('60分钟_MACD远离W200N20T30_BS辅助V230527_空头远离_任意_任意_0')`
///
/// 参数说明：
/// - `key`：参与统计的 MACD 因子，支持 `DIF/DEA/MACD`，默认 `DIF`；
/// - `w`：统计窗口长度，默认 `100`；
/// - `n`：最近观察窗口长度，默认 `10`；
/// - `t`：标准差放大系数，默认 `20`。
/// 对齐说明：与 Python `czsc.signals.zdy_macd_V230527` 保持一致。
#[signal(category = "kline", name = "zdy_macd_V230527", template = "{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230527", opcode = "ZdyMacdV230527", param_kind = "ZdyMacdV230527")]
pub fn zdy_macd_v230527(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 10);
    let w = get_usize_param(params, "w", 100);
    let t = get_usize_param(params, "t", 20) as f64;
    let key = params.str("key", "DIF").to_uppercase();
    let k1 = c.freq.to_string();
    let k2 = format!("{}远离W{}N{}T{}", key, w, n, t as i32);
    let k3 = "BS辅助V230527";
    if c.bi_list.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let (dif_map, dea_map, macd_map) = macd_cache_maps(c, 12, 26, 9, cache);
    let bars = get_sub_elements(&c.bars_raw, 1, w);
    let factors: Vec<f64> = bars
        .iter()
        .filter_map(|x| match key.as_str() {
            "DIF" => dif_map.get(&x.id).copied(),
            "DEA" => dea_map.get(&x.id).copied(),
            _ => macd_map.get(&x.id).copied(),
        })
        .collect();
    let median = median_abs(&factors);
    let std = std_pop(&factors.iter().map(|x| x.abs()).collect::<Vec<_>>());
    let last_n = &factors[factors.len().saturating_sub(n)..];
    let max_abs = *last_n.iter().max_by(|a, b| a.abs().partial_cmp(&b.abs()).unwrap_or(std::cmp::Ordering::Equal)).unwrap_or(&0.0);
    if max_abs.abs() > median + t / 10.0 * std {
        return make_kline_signal_v1(&k1, &k2, k3, if max_abs > 0.0 { "多头远离" } else { "空头远离" });
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_dif_V230527：DIF 相对 MACD 柱的远离信号
///
/// 参数模板：`"{freq}_N{n}T{t}_DIF远离V230527"`
///
/// 信号逻辑：
/// 1. 在最近 `n * 8` 根 K 线中找到最近 `n` 根内绝对值最大的 DIF；
/// 2. 若该 DIF 为正，则与历史正 MACD 柱峰值比较；为负则与历史负 MACD 柱绝对值比较；
/// 3. 超过阈值后输出 `多头远离/空头远离`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N10T30_DIF远离V230527_多头远离_任意_任意_0')`
/// - `Signal('60分钟_N20T40_DIF远离V230527_空头远离_任意_任意_0')`
///
/// 参数说明：
/// - `n`：最近观察窗口长度，默认 `10`；
/// - `t`：与历史柱峰值比较的放大系数，默认 `30`。
/// 对齐说明：与 Python `czsc.signals.zdy_dif_V230527` 保持一致。
#[signal(category = "kline", name = "zdy_dif_V230527", template = "{freq}_N{n}T{t}_DIF远离V230527", opcode = "ZdyDifV230527", param_kind = "ZdyDifV230527")]
pub fn zdy_dif_v230527(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 10);
    let t = get_usize_param(params, "t", 30) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("N{}T{}", n, t as i32);
    let k3 = "DIF远离V230527";
    if c.bars_raw.len() < 30 + n * 8 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let (dif_map, _, macd_map) = macd_cache_maps(c, 12, 26, 9, cache);
    let bars = get_sub_elements(&c.bars_raw, 1, n * 8);
    let tail = &bars[bars.len() - n..];
    let max_abs_dif_bar = tail.iter().max_by(|a, b| dif_map.get(&a.id).unwrap_or(&0.0).abs().partial_cmp(&dif_map.get(&b.id).unwrap_or(&0.0).abs()).unwrap_or(std::cmp::Ordering::Equal)).unwrap();
    let max_abs_dif = *dif_map.get(&max_abs_dif_bar.id).unwrap_or(&0.0);
    if max_abs_dif > 0.0 {
        let seq: Vec<f64> = bars.iter().filter_map(|x| macd_map.get(&x.id).copied()).filter(|x| *x > 0.0).collect();
        if seq.len() > n && max_abs_dif.abs() > seq.iter().copied().fold(f64::NEG_INFINITY, f64::max) * t / 10.0 {
            return make_kline_signal_v1(&k1, &k2, k3, "多头远离");
        }
    } else if max_abs_dif < 0.0 {
        let seq: Vec<f64> = bars.iter().filter_map(|x| macd_map.get(&x.id).copied()).filter(|x| *x < 0.0).map(f64::abs).collect();
        if seq.len() > n && max_abs_dif.abs() > seq.iter().copied().fold(f64::NEG_INFINITY, f64::max) * t / 10.0 {
            return make_kline_signal_v1(&k1, &k2, k3, "空头远离");
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// zdy_dif_V230528：DIF 峰谷分位远离信号
///
/// 参数模板：`"{freq}_N{n}T{t}_DIF远离V230528"`
///
/// 信号逻辑：
/// 1. 提取最近最多 1000 根 K 线的 DIF 序列，并识别局部峰值与谷值；
/// 2. 用峰值上分位和谷值下分位构造多空远离阈值；
/// 3. 若最近一次峰值或谷值超过对应分位阈值，且最新 DIF 同向，则输出 `多头远离/空头远离`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N20T80_DIF远离V230528_多头远离_任意_任意_0')`
/// - `Signal('60分钟_N20T80_DIF远离V230528_空头远离_任意_任意_0')`
///
/// 参数说明：
/// - `n`：参与比较的峰谷样本数量下限，默认 `20`；
/// - `t`：峰值分位数阈值，默认 `80`，谷值侧使用 `100 - t`。
/// 对齐说明：与 Python `czsc.signals.zdy_dif_V230528` 保持一致。
#[signal(category = "kline", name = "zdy_dif_V230528", template = "{freq}_N{n}T{t}_DIF远离V230528", opcode = "ZdyDifV230528", param_kind = "ZdyDifV230528")]
pub fn zdy_dif_v230528(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 20);
    let t = get_usize_param(params, "t", 80) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("N{}T{}", n, t as i32);
    let k3 = "DIF远离V230528";
    let (dif_map, _, _) = macd_cache_maps(c, 12, 26, 9, cache);
    let dif_values: Vec<f64> = c.bars_raw.iter().rev().take(1000).collect::<Vec<_>>().into_iter().rev().filter_map(|x| dif_map.get(&x.id).copied()).collect();
    let (peaks, valleys) = find_peaks_valleys(&dif_values);
    if peaks.len() < n || valleys.len() < n {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let peaks_n = percentile_linear(&peaks.values().copied().collect::<Vec<_>>(), t).unwrap_or(f64::INFINITY);
    let valleys_n = percentile_linear(&valleys.values().copied().collect::<Vec<_>>(), 100.0 - t).unwrap_or(f64::NEG_INFINITY);

    if peaks.keys().max() > valleys.keys().max() && *peaks.get(peaks.keys().max().unwrap()).unwrap() > peaks_n && *dif_values.last().unwrap_or(&0.0) > 0.0 {
        return make_kline_signal_v1(&k1, &k2, k3, "多头远离");
    }
    if valleys.keys().max() > peaks.keys().max() && *valleys.get(valleys.keys().max().unwrap()).unwrap() < valleys_n && *dif_values.last().unwrap_or(&0.0) < 0.0 {
        return make_kline_signal_v1(&k1, &k2, k3, "空头远离");
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}
