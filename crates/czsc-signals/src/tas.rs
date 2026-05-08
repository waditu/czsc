use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{
    bar_index_map, cal_cross_num, count_last_same, cross_zero_axis, down_cross_count,
    fast_slow_cross, fast_slow_cross_ext, get_str_param, get_sub_elements, get_usize_param,
    linear_slope, make_kline_signal_v1, make_kline_signal_v2, make_kline_signal_v3,
    pd_cut_last_label, qcut_last_label, std_abs_series, values_from_fx,
};
use crate::utils::ta::{
    calc_sma, macd_snapshot_field_value, update_atr_cache, update_boll_cache, update_cci_cache,
    update_kdj_cache, update_ma_cache, update_macd_cache, update_sar_cache, MacdField,
};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::mark::Mark;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::zs::ZS;
use czsc_signal_macros::signal;
use serde_json::Value;
use std::collections::HashMap;

#[allow(clippy::too_many_arguments)]
fn snapshot_dif_values_from_raw_bars(
    czsc: &CZSC,
    mc: &crate::types::MacdSeries,
    id_to_idx: &HashMap<i32, usize>,
    raw_bars: &[RawBar],
    short: usize,
    long: usize,
    m: usize,
    snapshot_overrides: &mut HashMap<i32, (f64, f64, f64)>,
) -> Vec<f64> {
    raw_bars
        .iter()
        .filter_map(|rb| {
            macd_snapshot_field_value(
                czsc,
                mc,
                id_to_idx,
                rb,
                short,
                long,
                m,
                MacdField::Dif,
                snapshot_overrides,
            )
        })
        .filter(|x| x.is_finite())
        .collect()
}

#[allow(clippy::too_many_arguments)]
fn snapshot_dif_values_from_fx(
    czsc: &CZSC,
    mc: &crate::types::MacdSeries,
    id_to_idx: &HashMap<i32, usize>,
    fx: &czsc_core::objects::fx::FX,
    short: usize,
    long: usize,
    m: usize,
    snapshot_overrides: &mut HashMap<i32, (f64, f64, f64)>,
) -> Vec<f64> {
    let raw_bars: Vec<RawBar> = fx
        .elements
        .iter()
        .flat_map(|nb| nb.elements.iter().cloned())
        .collect();
    snapshot_dif_values_from_raw_bars(
        czsc,
        mc,
        id_to_idx,
        &raw_bars,
        short,
        long,
        m,
        snapshot_overrides,
    )
}

/// tas_ma_base_V221101：单均线多空与方向信号
///
/// 参数模板：`"{freq}_D{di}{ma_type}#{timeperiod}_分类V221101"`
///
/// 信号逻辑：
/// 1. 计算指定均线（`SMA/EMA`）；
/// 2. `close >= ma` 判定 `多头`，否则 `空头`；
/// 3. `ma_now >= ma_prev` 判定 `向上`，否则 `向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1SMA#5_分类V221101_多头_向上_任意_0')`
/// - `Signal('60分钟_D1EMA#12_分类V221101_空头_向下_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_ma_base_V221101",
    template = "{freq}_D{di}{ma_type}#{timeperiod}_分类V221101",
    opcode = "TasMaBaseV221101",
    param_kind = "TasMaBase"
)]
pub fn tas_ma_base_v221101(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let freq = czsc.freq;

    // 缓存 key 唯一标识这根线
    let cache_key = format!("{}_{}_{}", freq, ma_type, timeperiod);

    // 更新缓存
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);

    let mut signals_res = Vec::new();
    let ma = cache.series.get(&cache_key).unwrap();
    let close = &czsc.bars_raw;
    let bars = get_sub_elements(close, di, 3);
    if bars.len() < 2 {
        return signals_res;
    }

    let c = bars[bars.len() - 1].close;
    let m = ma[close.len() - di];
    let m_prev = ma[close.len() - di - 1];

    let v1 = if c >= m { "多头" } else { "空头" };

    // 判断方向：当前均线 >= 上一根均线为向上
    let v2 = if m >= m_prev { "向上" } else { "向下" };

    let k1 = freq.to_string();
    let k2 = format!("D{}{}#{}", di, ma_type, timeperiod);
    let k3 = "分类V221101";
    signals_res.extend(make_kline_signal_v2(&k1, &k2, k3, v1, v2));

    signals_res
}

/// tas_ma_base_V221203：单均线多空与距离分层信号
///
/// 参数模板：`"{freq}_D{di}{ma_type}#{timeperiod}T{th}_分类V221203"`
///
/// 信号逻辑：
/// 1. 计算指定均线（`SMA/EMA`）；
/// 2. `close >= ma` 判定 `多头`，否则 `空头`；
/// 3. `ma_now >= ma_prev` 判定 `向上`，否则 `向下`；
/// 4. `abs(close-ma)/ma * 10000 > th` 判定 `远离`，否则 `靠近`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1SMA#5T100_分类V221203_多头_向上_靠近_0')`
/// - `Signal('60分钟_D1EMA#12T80_分类V221203_空头_向下_远离_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`；
/// - `th`：距离阈值（BP），默认 `100`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_ma_base_V221203",
    template = "{freq}_D{di}{ma_type}#{timeperiod}T{th}_分类V221203",
    opcode = "TasMaBaseV221203",
    param_kind = "TasMaBaseV221203"
)]
pub fn tas_ma_base_v221203(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let th = get_usize_param(params, "th", 100) as f64;

    let cache_key = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod);
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);
    let ma = cache.series.get(&cache_key).unwrap();
    let bars = get_sub_elements(&czsc.bars_raw, di, 3);
    if bars.len() < 2 {
        return Vec::new();
    }

    let c = bars[bars.len() - 1].close;
    let m = ma[czsc.bars_raw.len() - di];
    let m_prev = ma[czsc.bars_raw.len() - di - 1];

    let v1 = if c >= m { "多头" } else { "空头" };
    let v2 = if m >= m_prev { "向上" } else { "向下" };
    let v3 = if ((c - m).abs() / m) * 10000.0 > th {
        "远离"
    } else {
        "靠近"
    };

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}{}#{}T{}", di, ma_type, timeperiod, th as usize);
    let k3 = "分类V221203";
    make_kline_signal_v3(&k1, &k2, k3, v1, v2, v3)
}

/// tas_ma_base_V230313：单均线开平仓辅助信号（带重叠约束）
///
/// 参数模板：`"{freq}_D{di}#{ma_type}#{timeperiod}MO{max_overlap}_BS辅助V230313"`
///
/// 信号逻辑：
/// 1. 计算指定均线（`SMA/EMA`）；
/// 2. 取倒数 `di` 截止的 `max_overlap+1` 根K线；
/// 3. 若最新 `close >= ma` 且窗口内并非全部 `close > ma`，判 `看多`；
/// 4. 若最新 `close < ma` 且窗口内并非全部 `close < ma`，判 `看空`；
/// 5. 否则判 `其他`；并用 `ma_now >= ma_prev` 判方向 `向上/向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1#SMA#5MO5_BS辅助V230313_看多_向上_任意_0')`
/// - `Signal('60分钟_D1#EMA#12MO5_BS辅助V230313_看空_向下_任意_0')`
/// - `Signal('60分钟_D1#SMA#5MO5_BS辅助V230313_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`；
/// - `max_overlap`：相同方向最大重叠窗口，默认 `5`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_ma_base_V230313",
    template = "{freq}_D{di}#{ma_type}#{timeperiod}MO{max_overlap}_BS辅助V230313",
    opcode = "TasMaBaseV230313",
    param_kind = "TasMaBaseV230313"
)]
pub fn tas_ma_base_v230313(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let max_overlap = get_usize_param(params, "max_overlap", 5);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}#{}#{}MO{}", di, ma_type, timeperiod, max_overlap);
    let k3 = "BS辅助V230313";

    if max_overlap < 2 {
        return Vec::new();
    }

    let cache_key = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod);
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);
    let ma = cache.series.get(&cache_key).unwrap();

    let bars = get_sub_elements(&czsc.bars_raw, di, max_overlap + 1);
    if bars.len() < max_overlap + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let end = czsc.bars_raw.len() - di + 1;
    let start = end - (max_overlap + 1);
    let last_idx = end - 1;
    let last_close = bars[bars.len() - 1].close;
    let last_ma = ma[last_idx];

    let all_above = (start..end).all(|i| czsc.bars_raw[i].close > ma[i]);
    let all_below = (start..end).all(|i| czsc.bars_raw[i].close < ma[i]);

    let v1 = if last_close >= last_ma && !all_above {
        "看多"
    } else if last_close < last_ma && !all_below {
        "看空"
    } else {
        "其他"
    };

    if v1 == "其他" {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let v2 = if ma[last_idx] >= ma[last_idx - 1] {
        "向上"
    } else {
        "向下"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_ma_round_V221206：笔端点触碰均线信号
///
/// 参数模板：`"{freq}_D{di}TH{th}#碰{ma_type}#{timeperiod}_BE辅助V221206"`
///
/// 信号逻辑：
/// 1. 计算指定均线（`SMA/EMA`）；
/// 2. 取倒数第 `di` 笔，提取其结束分型中间 NewBar 的原始K线；
/// 3. 计算该批原始K线对应均线均值 `last_ma`；
/// 4. 若上笔且 `abs(high-last_ma)/power_price < th/100`，判 `上碰`；
/// 5. 若下笔且 `abs(low-last_ma)/power_price < th/100`，判 `下碰`；否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1TH10#碰SMA#60_BE辅助V221206_上碰_任意_任意_0')`
/// - `Signal('60分钟_D1TH10#碰SMA#60_BE辅助V221206_下碰_任意_任意_0')`
///
/// 参数说明：
/// - `di`：指定倒数第 `di` 笔，默认 `1`；
/// - `th`：端点触碰阈值（百分比），默认 `10`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_ma_round_V221206",
    template = "{freq}_D{di}TH{th}#碰{ma_type}#{timeperiod}_BE辅助V221206",
    opcode = "TasMaRoundV221206",
    param_kind = "TasMaRoundV221206"
)]
pub fn tas_ma_round_v221206(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 10) as f64;
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod = get_usize_param(params, "timeperiod", 5);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}TH{}#碰{}#{}", di, th as usize, ma_type, timeperiod);
    let k3 = "BE辅助V221206";
    let mut v1 = "其他";

    let cache_key = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod);
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);
    let ma = cache.series.get(&cache_key).unwrap();
    let bar_idx_map: HashMap<i32, usize> = czsc
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();

    if czsc.bi_list.len() > di + 3 {
        let last_bi = &czsc.bi_list[czsc.bi_list.len() - di];
        let mut ma_vals = Vec::new();
        if last_bi.fx_b.elements.len() > 1 {
            let nb = &last_bi.fx_b.elements[1];
            for rb in &nb.elements {
                if let Some(idx) = bar_idx_map.get(&rb.id) {
                    ma_vals.push(ma[*idx]);
                }
            }
        }

        if !ma_vals.is_empty() {
            let last_ma = ma_vals.iter().sum::<f64>() / ma_vals.len() as f64;
            let bi_change = last_bi.get_power_price();
            if bi_change > 0.0 {
                if last_bi.direction == Direction::Up
                    && (last_bi.get_high() - last_ma).abs() / bi_change < th / 100.0
                {
                    v1 = "上碰";
                } else if last_bi.direction == Direction::Down
                    && (last_bi.get_low() - last_ma).abs() / bi_change < th / 100.0
                {
                    v1 = "下碰";
                }
            }
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_double_ma_V230511：双均线反向信号
///
/// 参数模板：`"{freq}_D{di}#{ma_type}#{t1}#{t2}_BS辅助V230511"`
///
/// 信号逻辑：
/// 1. 计算 `t1/t2` 双均线，`t1 < t2`；
/// 2. 当前K线需为大实体（`solid >= max(upper, lower, mean_solid)`）；
/// 3. `ma1 > ma2` 且当前大实体阴线，判 `看多`；
/// 4. `ma1 < ma2` 且当前大实体阳线，判 `看空`；
/// 5. 在同侧连续区间内若仅出现一次对应大实体且区间长度 `< t2/2`，则 `v2=第一个`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1#SMA#5#20_BS辅助V230511_看多_第一个_任意_0')`
/// - `Signal('60分钟_D1#SMA#5#20_BS辅助V230511_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `t1`：快线周期，默认 `5`；
/// - `t2`：慢线周期，默认 `20`；
/// - `ma_type`：均线类型，默认 `SMA`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_double_ma_V230511",
    template = "{freq}_D{di}#{ma_type}#{t1}#{t2}_BS辅助V230511",
    opcode = "TasDoubleMaV230511",
    param_kind = "TasDoubleMaV230511"
)]
pub fn tas_double_ma_v230511(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let t1 = get_usize_param(params, "t1", 5);
    let t2 = get_usize_param(params, "t2", 20);
    let ma_type = get_str_param(params, "ma_type", "SMA");

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}#{}#{}#{}", di, ma_type, t1, t2);
    let k3 = "BS辅助V230511";
    let mut v1 = "其他";
    let mut v2 = "任意";

    if t1 >= t2 || czsc.bars_raw.len() < t2 + 10 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, v2);
    }

    let key1 = format!("{}_{}_{}", czsc.freq, ma_type, t1);
    let key2 = format!("{}_{}_{}", czsc.freq, ma_type, t2);
    update_ma_cache(czsc, &key1, ma_type, t1, cache);
    update_ma_cache(czsc, &key2, ma_type, t2, cache);
    let ma1 = cache.series.get(&key1).unwrap();
    let ma2 = cache.series.get(&key2).unwrap();
    let bar_idx_map: HashMap<i32, usize> = czsc
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();

    let bars = get_sub_elements(&czsc.bars_raw, di, t2 + 1);
    if bars.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, v2);
    }

    let mean_solid = bars.iter().map(|x| (x.open - x.close).abs()).sum::<f64>() / bars.len() as f64;
    let bar = &czsc.bars_raw[czsc.bars_raw.len() - di];
    let bar_upper = bar.high - bar.open.max(bar.close);
    let bar_lower = bar.open.min(bar.close) - bar.low;
    let bar_solid = (bar.open - bar.close).abs();
    let solid_th = mean_solid.max(bar_upper).max(bar_lower);
    if bar_solid < solid_th {
        return make_kline_signal_v2(&k1, &k2, k3, v1, v2);
    }

    let Some(&idx) = bar_idx_map.get(&bar.id) else {
        return make_kline_signal_v2(&k1, &k2, k3, v1, v2);
    };
    if ma1[idx] > ma2[idx] && bar.close < bar.open {
        v1 = "看多";
        let mut right_bars = Vec::new();
        for x in bars.iter().rev() {
            let Some(&xi) = bar_idx_map.get(&x.id) else {
                continue;
            };
            if ma1[xi] > ma2[xi] {
                right_bars.push((x.open - x.close).abs() > solid_th && x.close < x.open);
            } else {
                break;
            }
        }
        let cnt = right_bars.iter().filter(|x| **x).count();
        if (right_bars.len() as f64) < (t2 as f64 / 2.0) && cnt == 1 {
            v2 = "第一个";
        }
    } else if ma1[idx] < ma2[idx] && bar.close > bar.open {
        v1 = "看空";
        let mut right_bars = Vec::new();
        for x in bars.iter().rev() {
            let Some(&xi) = bar_idx_map.get(&x.id) else {
                continue;
            };
            if ma1[xi] < ma2[xi] {
                right_bars.push((x.open - x.close).abs() > solid_th && x.close > x.open);
            } else {
                break;
            }
        }
        let cnt = right_bars.iter().filter(|x| **x).count();
        if (right_bars.len() as f64) < (t2 as f64 / 2.0) && cnt == 1 {
            v2 = "第一个";
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_macd_base_V221028：MACD/DIF/DEA 多空与方向信号
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}#{key}_BS辅助V221028"`
///
/// 信号逻辑：
/// 1. 计算 MACD 三序列；
/// 2. 依据 `key` 选择 `MACD/DIF/DEA`；
/// 3. 当前值 `>=0` 判定 `多头`，否则 `空头`；
/// 4. 当前值 `>=` 前值判定 `向上`，否则 `向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9#MACD_BS辅助V221028_多头_向上_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9#DIF_BS辅助V221028_空头_向下_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`；
/// - `key`：`MACD`、`DIF` 或 `DEA`，默认 `MACD`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_base_V221028",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS辅助V221028",
    opcode = "TasMacdBaseV221028",
    param_kind = "TasMacdBaseV221028"
)]
pub fn tas_macd_base_v221028(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let key = get_str_param(params, "key", "MACD").to_uppercase();
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);

    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );

    let macd_cache = cache.macd.get(&cache_key).unwrap();
    let series = match key.as_str() {
        "DIF" => &macd_cache.dif,
        "DEA" => &macd_cache.dea,
        _ => &macd_cache.macd,
    };
    let sub = get_sub_elements(series, di, 2);
    if sub.len() < 2 {
        return Vec::new();
    }
    let prev = sub[sub.len() - 2];
    let curr = sub[sub.len() - 1];
    let v1 = if curr >= 0.0 { "多头" } else { "空头" };
    let v2 = if curr >= prev { "向上" } else { "向下" };

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}MACD{}#{}#{}#{}",
        di, fastperiod, slowperiod, signalperiod, key
    );
    let k3 = "BS辅助V221028";
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_macd_direct_V221106：MACD柱方向信号
///
/// 参数模板：`"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}方向_BS辅助V221106"`
///
/// 信号逻辑：
/// 1. 计算 MACD 柱序列；
/// 2. 取倒数 `di` 对齐的最近 3 根柱值；
/// 3. 严格递增判定 `向上`，严格递减判定 `向下`，否则 `模糊`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K#MACD12#26#9方向_BS辅助V221106_向上_任意_任意_0')`
/// - `Signal('60分钟_D1K#MACD12#26#9方向_BS辅助V221106_向下_任意_任意_0')`
/// - `Signal('60分钟_D1K#MACD12#26#9方向_BS辅助V221106_模糊_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_direct_V221106",
    template = "{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}方向_BS辅助V221106",
    opcode = "TasMacdDirectV221106",
    param_kind = "TasMacdDirectV221106"
)]
pub fn tas_macd_direct_v221106(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);

    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let macd_cache = cache.macd.get(&cache_key).unwrap();
    let macd = get_sub_elements(&macd_cache.macd, di, 3);

    let v1 = if macd.len() != 3 {
        "模糊"
    } else if macd[2] > macd[1] && macd[1] > macd[0] {
        "向上"
    } else if macd[2] < macd[1] && macd[1] < macd[0] {
        "向下"
    } else {
        "模糊"
    };

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}K#MACD{}#{}#{}方向",
        di, fastperiod, slowperiod, signalperiod
    );
    let k3 = "BS辅助V221106";
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_power_V221108：MACD强弱分层信号
///
/// 参数模板：`"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}强弱_BS辅助V221108"`
///
/// 信号逻辑：
/// 1. 计算当前 `DIF/DEA`；
/// 2. `dif >= dea >= 0` 判定 `超强`；
/// 3. `dif - dea > 0` 判定 `强势`；
/// 4. `dif <= dea <= 0` 判定 `超弱`；
/// 5. `dif - dea < 0` 判定 `弱势`，其余为 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K#MACD12#26#9强弱_BS辅助V221108_超强_任意_任意_0')`
/// - `Signal('60分钟_D1K#MACD12#26#9强弱_BS辅助V221108_弱势_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_power_V221108",
    template = "{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}强弱_BS辅助V221108",
    opcode = "TasMacdPowerV221108",
    param_kind = "TasMacdPowerV221108"
)]
pub fn tas_macd_power_v221108(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);

    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let macd_cache = cache.macd.get(&cache_key).unwrap();

    let mut v1 = "其他";
    if czsc.bars_raw.len() > di + 10 {
        let idx = czsc.bars_raw.len() - di;
        let dif = macd_cache.dif[idx];
        let dea = macd_cache.dea[idx];
        if dif >= dea && dea >= 0.0 {
            v1 = "超强";
        } else if dif - dea > 0.0 {
            v1 = "强势";
        } else if dif <= dea && dea <= 0.0 {
            v1 = "超弱";
        } else if dif - dea < 0.0 {
            v1 = "弱势";
        }
    }

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}K#MACD{}#{}#{}强弱",
        di, fastperiod, slowperiod, signalperiod
    );
    let k3 = "BS辅助V221108";
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_first_bs_V230217：均线结合K线形态的一买一卖辅助
///
/// 参数模板：`"{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS1辅助V230217"`
///
/// 信号逻辑：
/// 1. 在最近 `n` 根K线上计算均线并构造 `sma/low/high/open/close` 序列；
/// 2. 一买条件：
///    - `sma > low` 全满足；
///    - 阴线占比 `> 60%`；
///    - 最近3根出现新低；
///    - 最后一根收盘在均线上方；
/// 3. 一卖条件与上面对称；
/// 4. 满足则输出 `一买/一卖`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N10#SMA#5_BS1辅助V230217_一买_任意_任意_0')`
/// - `Signal('60分钟_D1N10#SMA#5_BS1辅助V230217_一卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：窗口大小，默认 `10`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_first_bs_V230217",
    template = "{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS1辅助V230217",
    opcode = "TasFirstBsV230217",
    param_kind = "TasFirstBsV230217"
)]
pub fn tas_first_bs_v230217(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 10);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod = get_usize_param(params, "timeperiod", 5);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}#{}#{}", di, n, ma_type, timeperiod);
    let k3 = "BS1辅助V230217";
    let mut v1 = "其他";

    if di == 0 || czsc.bars_raw.len() < n + 5 || n < 4 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod);
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);
    let ma = cache.series.get(&cache_key).unwrap();

    let end = czsc.bars_raw.len() - di + 1;
    let start = end - n;
    let bars = &czsc.bars_raw[start..end];
    let mut sma = Vec::with_capacity(n);
    let mut low = Vec::with_capacity(n);
    let mut high = Vec::with_capacity(n);
    let mut open = Vec::with_capacity(n);
    let mut close = Vec::with_capacity(n);
    for (i, b) in bars.iter().enumerate().take(n) {
        let idx = start + i;
        sma.push(ma[idx]);
        low.push(b.low);
        high.push(b.high);
        open.push(b.open);
        close.push(b.close);
    }

    let condition_1_down = sma.iter().zip(low.iter()).all(|(a, b)| *a > *b);
    let condition_1_up = sma.iter().zip(high.iter()).all(|(a, b)| *a < *b);

    let n1 = close
        .iter()
        .zip(open.iter())
        .filter(|(c, o)| **c < **o)
        .count();
    let m1 = close
        .iter()
        .zip(open.iter())
        .filter(|(c, o)| **c > **o)
        .count();
    let condition_2_down = (n1 as f64 / n as f64) > 0.6;
    let condition_2_up = (m1 as f64 / n as f64) > 0.6;

    let low_last3_min = low[n - 3..].iter().copied().fold(f64::INFINITY, f64::min);
    let low_prev_min = low[..n - 3].iter().copied().fold(f64::INFINITY, f64::min);
    let condition_3_down = low_last3_min < low_prev_min;
    let high_last3_max = high[n - 3..]
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, f64::max);
    let high_prev_max = high[..n - 3]
        .iter()
        .copied()
        .fold(f64::NEG_INFINITY, f64::max);
    let condition_3_up = high_last3_max > high_prev_max;

    let condition_4_down = close[n - 1] > sma[n - 1];
    let condition_4_up = close[n - 1] < sma[n - 1];

    if condition_1_down && condition_2_down && condition_3_down && condition_4_down {
        v1 = "一买";
    } else if condition_1_up && condition_2_up && condition_3_up && condition_4_up {
        v1 = "一卖";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_second_bs_V230228：均线结合K线形态的二买二卖辅助
///
/// 参数模板：`"{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS2辅助V230228"`
///
/// 信号逻辑：
/// 1. 在最近 `n` 根K线上计算均线；
/// 2. 二买条件：
///    - `sma[-1]` 为窗口新高且 `sma[-1] > sma[-2]`；
///    - 最新收盘 `close[-1] > sma[-1]`；
///    - 最近3根存在 `low < sma`；
/// 3. 二卖条件与上面对称；
/// 4. 满足则输出 `二买/二卖`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N21#SMA#20_BS2辅助V230228_二买_任意_任意_0')`
/// - `Signal('60分钟_D1N21#SMA#20_BS2辅助V230228_二卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：窗口大小，默认 `21`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `20`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_second_bs_V230228",
    template = "{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS2辅助V230228",
    opcode = "TasSecondBsV230228",
    param_kind = "TasSecondBsV230228"
)]
pub fn tas_second_bs_v230228(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 21);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod = get_usize_param(params, "timeperiod", 20);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}#{}#{}", di, n, ma_type, timeperiod);
    let k3 = "BS2辅助V230228";
    let mut v1 = "其他";

    if di == 0 || czsc.bars_raw.len() < n + 5 || n < 3 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod);
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);
    let ma = cache.series.get(&cache_key).unwrap();

    let end = czsc.bars_raw.len() - di + 1;
    let start = end - n;
    let bars = &czsc.bars_raw[start..end];
    let mut sma = Vec::with_capacity(n);
    for i in 0..n {
        sma.push(ma[start + i]);
    }

    let min_three = bars[n - 3..]
        .iter()
        .zip(sma[n - 3..].iter())
        .any(|(b, s)| *s > b.low);
    let max_three = bars[n - 3..]
        .iter()
        .zip(sma[n - 3..].iter())
        .any(|(b, s)| b.high > *s);

    let sma_max = sma.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let sma_min = sma.iter().copied().fold(f64::INFINITY, f64::min);
    let close_last = bars[n - 1].close;

    if sma_max == sma[n - 1] && sma[n - 1] > sma[n - 2] && close_last > sma[n - 1] && min_three {
        v1 = "二买";
    } else if sma_min == sma[n - 1]
        && sma[n - 1] < sma[n - 2]
        && close_last < sma[n - 1]
        && max_three
    {
        v1 = "二卖";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_second_bs_V230303：利用笔和均线辅助二买二卖
///
/// 参数模板：`"{freq}_D{di}{ma_type}#{timeperiod}_BS2辅助V230303"`
///
/// 信号逻辑：
/// 1. 取倒数 `di` 截止最近13笔，取最后一笔与其首尾原始K线；
/// 2. 二买条件：
///    - 最后一笔为向下；
///    - 最后一笔末K最低点跌破均线；
///    - 最近5笔最低点为13笔全局最低；
///    - 该笔首K均线值 < 末K均线值（均线向上）；
/// 3. 二卖条件与上面对称；
/// 4. 满足则输出 `二买/二卖`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1SMA#30_BS2辅助V230303_二买_任意_任意_0')`
/// - `Signal('60分钟_D1SMA#30_BS2辅助V230303_二卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：指定倒数第 `di` 笔，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `30`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_second_bs_V230303",
    template = "{freq}_D{di}{ma_type}#{timeperiod}_BS2辅助V230303",
    opcode = "TasSecondBsV230303",
    param_kind = "TasSecondBsV230303"
)]
pub fn tas_second_bs_v230303(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod = get_usize_param(params, "timeperiod", 30);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}{}#{}", di, ma_type, timeperiod);
    let k3 = "BS2辅助V230303";
    let mut v1 = "其他";

    if di == 0 || czsc.bi_list.len() < di + 13 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod);
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);
    let ma = cache.series.get(&cache_key).unwrap();
    let bar_idx_map: HashMap<i32, usize> = czsc
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();

    let bi_list = get_sub_elements(&czsc.bi_list, di, 13);
    if bi_list.len() < 13 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let last_bi = &bi_list[bi_list.len() - 1];
    let rb = last_bi.get_raw_bars();
    if rb.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let first_bar = &rb[0];
    let last_bar = &rb[rb.len() - 1];
    let Some(&first_idx) = bar_idx_map.get(&first_bar.id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(&last_idx) = bar_idx_map.get(&last_bar.id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };

    let min_low_5 = bi_list[bi_list.len() - 5..]
        .iter()
        .map(|x| x.get_low())
        .fold(f64::INFINITY, f64::min);
    let min_low_all = bi_list
        .iter()
        .map(|x| x.get_low())
        .fold(f64::INFINITY, f64::min);
    if last_bi.direction == Direction::Down
        && last_bar.low < ma[last_idx]
        && min_low_5 == min_low_all
        && ma[first_idx] < ma[last_idx]
    {
        v1 = "二买";
    }

    let max_high_5 = bi_list[bi_list.len() - 5..]
        .iter()
        .map(|x| x.get_high())
        .fold(f64::NEG_INFINITY, f64::max);
    let max_high_all = bi_list
        .iter()
        .map(|x| x.get_high())
        .fold(f64::NEG_INFINITY, f64::max);
    if last_bi.direction == Direction::Up
        && last_bar.high > ma[last_idx]
        && max_high_5 == max_high_all
        && ma[first_idx] > ma[last_idx]
    {
        v1 = "二卖";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_hlma_V230301：HMA/LMA 多空信号
///
/// 参数模板：`"{freq}_D{di}#{ma_type}#{timeperiod}HLMA_BS辅助V230301"`
///
/// 信号逻辑：
/// 1. 取最近 `timeperiod` 根K线，计算 `hma=high均值`、`lma=low均值`；
/// 2. 若 `close_now > hma` 且 `close_prev <= ma_prev`，判 `看多`；
/// 3. 若 `close_now < lma` 且 `close_prev >= ma_prev`，判 `看空`；
/// 4. 否则判 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1#SMA#3HLMA_BS辅助V230301_看多_任意_任意_0')`
/// - `Signal('60分钟_D1#SMA#3HLMA_BS辅助V230301_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：窗口周期，默认 `3`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_hlma_V230301",
    template = "{freq}_D{di}#{ma_type}#{timeperiod}HLMA_BS辅助V230301",
    opcode = "TasHlmaV230301",
    param_kind = "TasHlmaV230301"
)]
pub fn tas_hlma_v230301(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod = get_usize_param(params, "timeperiod", 3);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}#{}#{}HLMA", di, ma_type, timeperiod);
    let k3 = "BS辅助V230301";
    let mut v1 = "其他";

    if di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod);
    update_ma_cache(czsc, &cache_key, ma_type, timeperiod, cache);
    let ma = cache.series.get(&cache_key).unwrap();
    let bar_idx_map: HashMap<i32, usize> = czsc
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();

    let bars = get_sub_elements(&czsc.bars_raw, di, timeperiod);
    if bars.len() >= 2 {
        let hma = bars.iter().map(|x| x.high).sum::<f64>() / bars.len() as f64;
        let lma = bars.iter().map(|x| x.low).sum::<f64>() / bars.len() as f64;
        let b1 = &bars[bars.len() - 1];
        let b2 = &bars[bars.len() - 2];
        if let Some(&b2_idx) = bar_idx_map.get(&b2.id) {
            if b1.close > hma && b2.close <= ma[b2_idx] {
                v1 = "看多";
            } else if b1.close < lma && b2.close >= ma[b2_idx] {
                v1 = "看空";
            }
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_boll_cc_V230312：布林进出场信号
///
/// 参数模板：`"{freq}_D{di}BOLL{timeperiod}S{nbdev}SP{sp}_BS辅助V230312"`
///
/// 信号逻辑：
/// 1. 计算 BOLL 中轨与上下轨；
/// 2. 计算 `bias = (close / mid - 1) * 10000`；
/// 3. `close < upper 且 bias < -sp` 判 `看空`，`close > lower 且 bias > sp` 判 `看多`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1BOLL20S20SP400_BS辅助V230312_看空_任意_任意_0')`
/// - `Signal('60分钟_D1BOLL20S20SP400_BS辅助V230312_看多_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：BOLL 周期，默认 `20`；
/// - `nbdev`：标准差倍数 *10，默认 `20`；
/// - `sp`：偏离阈值（BP），默认 `400`。
/// 对齐说明：与 Python `tas_boll_cc_V230312` 的 bias 判定和阈值方向一致。
#[signal(
    category = "kline",
    name = "tas_boll_cc_V230312",
    template = "{freq}_D{di}BOLL{timeperiod}S{nbdev}SP{sp}_BS辅助V230312",
    opcode = "TasBollCcV230312",
    param_kind = "TasBollCcV230312"
)]
pub fn tas_boll_cc_v230312(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let sp = get_usize_param(params, "sp", 400) as f64;
    let timeperiod = get_usize_param(params, "timeperiod", 20);
    let nbdev = get_usize_param(params, "nbdev", 20);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}BOLL{}S{}SP{}", di, timeperiod, nbdev, sp as usize);
    let k3 = "BS辅助V230312";
    let mut v1 = "其他";
    if di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = format!("BOLL{}S{}", timeperiod, nbdev);
    update_boll_cache(czsc, &cache_key, timeperiod, nbdev as f64 / 10.0, cache);
    let boll = cache.boll.get(&cache_key).unwrap();
    let idx = czsc.bars_raw.len() - di;
    let close = czsc.bars_raw[idx].close;
    let mid = boll.mid[idx];
    let upper = boll.upper[idx];
    let lower = boll.lower[idx];
    if mid.is_finite() && upper.is_finite() && lower.is_finite() && mid.abs() > f64::EPSILON {
        let bias = (close / mid - 1.0) * 10000.0;
        if close < upper && bias < -sp {
            v1 = "看空";
        } else if close > lower && bias > sp {
            v1 = "看多";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_kdj_evc_V221201：KDJ 极值计数信号
///
/// 参数模板：`"{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{c1}#{c2}_KDJ极值V221201"`
///
/// 信号逻辑：
/// 1. 计算 `K/D/J` 序列并提取 `key`；
/// 2. 统计末端连续低于 `th` 或高于 `100-th` 的次数；
/// 3. 连续次数落入 `[c1, c2)` 时分别输出 `多头/空头`，并在 `v2` 标注计数。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_多头_C5_任意_0')`
/// - `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_空头_C6_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `key`：取值 `K/D/J`，默认 `K`；
/// - `th`：极值阈值，默认 `10`；
/// - `count_range`：连续计数区间，默认 `[5, 8]`。
/// 对齐说明：连续计数、`v2=Cx` 标注方式与 Python `tas_kdj_evc_V221201` 保持一致。
#[signal(
    category = "kline",
    name = "tas_kdj_evc_V221201",
    template = "{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{c1}#{c2}_KDJ极值V221201",
    opcode = "TasKdjEvcV221201",
    param_kind = "TasKdjEvcV221201"
)]
pub fn tas_kdj_evc_v221201(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let mut key = get_str_param(params, "key", "K").to_uppercase();
    let th = get_usize_param(params, "th", 10);
    let (c1, c2) = if let Some(Value::Array(arr)) = params.value("count_range") {
        if arr.len() >= 2 {
            let a = arr[0].as_u64().unwrap_or(5) as usize;
            let b = arr[1].as_u64().unwrap_or(8) as usize;
            (a, b)
        } else {
            (5, 8)
        }
    } else {
        (5, 8)
    };
    let fastk_period = get_usize_param(params, "fastk_period", 9);
    let slowk_period = get_usize_param(params, "slowk_period", 3);
    let slowd_period = get_usize_param(params, "slowd_period", 3);

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}T{}KDJ{}#{}#{}#{}值突破{}#{}",
        di, th, fastk_period, slowk_period, slowd_period, key, c1, c2
    );
    let k3 = "KDJ极值V221201";
    let mut v1 = "其他";
    let mut v2 = "任意".to_string();
    if c2 <= c1 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, &v2);
    }

    let cache_key = format!("KDJ{}#{}#{}", fastk_period, slowk_period, slowd_period);
    update_kdj_cache(
        czsc,
        &cache_key,
        fastk_period,
        slowk_period,
        slowd_period,
        cache,
    );
    let kd = cache.kdj.get(&cache_key).unwrap();
    let bars = get_sub_elements(&czsc.bars_raw, di, 3 + c2);
    if bars.len() == 3 + c2 {
        key = key.to_lowercase();
        let end = czsc.bars_raw.len() - di + 1;
        let start = end - bars.len();
        let mut vals = Vec::with_capacity(bars.len());
        for i in 0..bars.len() {
            let idx = start + i;
            let x = match key.as_str() {
                "d" => kd.d[idx],
                "j" => kd.j[idx],
                _ => kd.k[idx],
            };
            vals.push(x);
        }
        let long: Vec<bool> = vals.iter().map(|x| *x < th as f64).collect();
        let short: Vec<bool> = vals.iter().map(|x| *x > 100.0 - th as f64).collect();
        let lc = if *long.last().unwrap_or(&false) {
            count_last_same(&long)
        } else {
            0
        };
        let sc = if *short.last().unwrap_or(&false) {
            count_last_same(&short)
        } else {
            0
        };
        if c2 > lc && lc >= c1 {
            v1 = "多头";
            v2 = format!("C{}", lc);
        }
        if c2 > sc && sc >= c1 {
            v1 = "空头";
            v2 = format!("C{}", sc);
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}

/// tas_kdj_evc_V230401：KDJ 极值计数信号
///
/// 参数模板：`"{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{min_count}#{max_count}_BS辅助V230401"`
///
/// 信号逻辑：
/// 1. 计算 `K/D/J` 指标并提取目标序列；
/// 2. 末端连续低于阈值记多头计数，连续高于阈值记空头计数；
/// 3. 连续次数在 `[min_count, max_count)` 时输出 `多头/空头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_BS辅助V230401_多头_任意_任意_0')`
/// - `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_BS辅助V230401_空头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `key`：`K/D/J`，默认 `K`；
/// - `th`：极值阈值，默认 `10`；
/// - `min_count/max_count`：连续计数区间，默认 `5/8`。
/// 对齐说明：参数校验与计数边界严格对齐 Python `tas_kdj_evc_V230401`。
#[signal(
    category = "kline",
    name = "tas_kdj_evc_V230401",
    template = "{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{min_count}#{max_count}_BS辅助V230401",
    opcode = "TasKdjEvcV230401",
    param_kind = "TasKdjEvcV230401"
)]
pub fn tas_kdj_evc_v230401(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let key = get_str_param(params, "key", "K").to_uppercase();
    let th = get_usize_param(params, "th", 10);
    let min_count = get_usize_param(params, "min_count", 5);
    let max_count = get_usize_param(params, "max_count", min_count + 3);
    let fastk_period = get_usize_param(params, "fastk_period", 9);
    let slowk_period = get_usize_param(params, "slowk_period", 3);
    let slowd_period = get_usize_param(params, "slowd_period", 3);

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}T{}KDJ{}#{}#{}#{}值突破{}#{}",
        di, th, fastk_period, slowk_period, slowd_period, key, min_count, max_count
    );
    let k3 = "BS辅助V230401";
    let mut v1 = "其他";
    if min_count >= max_count
        || !(1..100).contains(&th)
        || !matches!(key.as_str(), "K" | "D" | "J")
        || czsc.bars_raw.len() < di + max_count + 2
    {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = format!("KDJ{}#{}#{}", fastk_period, slowk_period, slowd_period);
    update_kdj_cache(
        czsc,
        &cache_key,
        fastk_period,
        slowk_period,
        slowd_period,
        cache,
    );
    let kd = cache.kdj.get(&cache_key).unwrap();

    let bars = get_sub_elements(&czsc.bars_raw, di, 3 + max_count);
    let end = czsc.bars_raw.len() - di + 1;
    let start = end - bars.len();
    let vals: Vec<f64> = (0..bars.len())
        .map(|i| {
            let idx = start + i;
            match key.as_str() {
                "D" => kd.d[idx],
                "J" => kd.j[idx],
                _ => kd.k[idx],
            }
        })
        .collect();
    let long: Vec<bool> = vals.iter().map(|x| *x < th as f64).collect();
    let short: Vec<bool> = vals.iter().map(|x| *x > 100.0 - th as f64).collect();
    let lc = if *long.last().unwrap_or(&false) {
        count_last_same(&long)
    } else {
        0
    };
    let sc = if *short.last().unwrap_or(&false) {
        count_last_same(&short)
    } else {
        0
    };
    if max_count > lc && lc >= min_count {
        v1 = "多头";
    }
    if max_count > sc && sc >= min_count {
        v1 = "空头";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_atr_break_V230424：ATR 通道突破
///
/// 参数模板：`"{freq}_D{di}ATR{timeperiod}T{th}突破_BS辅助V230424"`
///
/// 信号逻辑：
/// 1. 取窗口 `HH/LL` 和当前 ATR；
/// 2. 若 `close` 落在 `HH-th*ATR` 与 `LL+th*ATR` 之间，输出 `其他`；
/// 3. 向上突破输出 `看多`，向下突破输出 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1ATR5T30突破_BS辅助V230424_看多_任意_任意_0')`
/// - `Signal('60分钟_D1ATR5T30突破_BS辅助V230424_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：ATR 周期，默认 `5`；
/// - `th`：ATR 倍数（除以10），默认 `30`。
/// 对齐说明：区间内返回 `其他` 的优先级与 Python `tas_atr_break_V230424` 一致。
#[signal(
    category = "kline",
    name = "tas_atr_break_V230424",
    template = "{freq}_D{di}ATR{timeperiod}T{th}突破_BS辅助V230424",
    opcode = "TasAtrBreakV230424",
    param_kind = "TasAtrBreakV230424"
)]
pub fn tas_atr_break_v230424(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 30);
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}ATR{}T{}突破", di, timeperiod, th);
    let k3 = "BS辅助V230424";

    if di == 0 || di > czsc.bars_raw.len() || czsc.bars_raw.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let cache_key = format!("ATR{}", timeperiod);
    update_atr_cache(czsc, &cache_key, timeperiod, cache);
    let atr_series = cache.series.get(&cache_key).unwrap();
    let bars = get_sub_elements(&czsc.bars_raw, di, timeperiod);
    let hh = bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let ll = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let idx = czsc.bars_raw.len() - di;
    let bar = &czsc.bars_raw[idx];
    let atr = atr_series[idx];
    let thf = th as f64 / 10.0;

    let v1 = if hh - thf * atr > bar.close && bar.close > ll + thf * atr {
        "其他"
    } else if bar.close > ll + thf * atr {
        "看多"
    } else if bar.close < hh - thf * atr {
        "看空"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_ma_system_V230513：均线系统多空排列
///
/// 参数模板：`"{freq}_D{di}SMA{ma_seq}_均线系统V230513"`
///
/// 信号逻辑：
/// 1. 计算 `ma_seq` 中各周期 SMA；
/// 2. 当前值严格递减判 `多头排列`；
/// 3. 当前值严格递增判 `空头排列`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1SMA5#10#20_均线系统V230513_多头排列_任意_任意_0')`
/// - `Signal('60分钟_D1SMA5#10#20_均线系统V230513_空头排列_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `ma_seq`：均线周期串，默认 `5#10#20`。
/// 对齐说明：排列判定方向与 Python `tas_ma_system_V230513` 完全一致。
#[signal(
    category = "kline",
    name = "tas_ma_system_V230513",
    template = "{freq}_D{di}SMA{ma_seq}_均线系统V230513",
    opcode = "TasMaSystemV230513",
    param_kind = "TasMaSystemV230513"
)]
pub fn tas_ma_system_v230513(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let ma_seq_str = get_str_param(params, "ma_seq", "5#10#20");
    let ma_seq: Vec<usize> = ma_seq_str
        .split('#')
        .filter_map(|x| x.parse::<usize>().ok())
        .collect();
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}SMA{}", di, ma_seq_str);
    let k3 = "均线系统V230513";
    let mut v1 = "其他";

    if ma_seq.is_empty() || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    for ma in &ma_seq {
        let key = format!("{}_SMA_{}", czsc.freq, ma);
        update_ma_cache(czsc, &key, "SMA", *ma, cache);
    }
    let max_ma = *ma_seq.iter().max().unwrap();
    if czsc.bars_raw.len() < max_ma + di + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let idx = czsc.bars_raw.len() - di;
    let ma_vals: Vec<f64> = ma_seq
        .iter()
        .map(|x| {
            let key = format!("{}_SMA_{}", czsc.freq, x);
            cache.series.get(&key).unwrap()[idx]
        })
        .collect();
    if ma_vals.windows(2).all(|w| w[0] > w[1]) {
        v1 = "多头排列";
    } else if ma_vals.windows(2).all(|w| w[0] < w[1]) {
        v1 = "空头排列";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_ma_cohere_V230512：均线系统粘合/扩散状态
///
/// 参数模板：`"{freq}_D{di}SMA{ma_seq}_均线系统V230512"`
///
/// 信号逻辑：
/// 1. 计算 `ma_seq` 各条 SMA，并构造最近 100 根“均线最大值/最小值 - 1”序列；
/// 2. 用前 80 根计算标准差 `ret_std`；
/// 3. 最近 20 根中，`ret < 0.5 * ret_std` 达到 16 次判 `粘合`；
/// 4. 最近 20 根中，`ret > 1.0 * ret_std` 达到 16 次判 `扩散`（覆盖前者）。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1SMA5#13#21#34#55_均线系统V230512_粘合_任意_任意_0')`
/// - `Signal('60分钟_D1SMA5#13#21#34#55_均线系统V230512_扩散_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `ma_seq`：均线周期序列（`#` 分隔），默认 `5#13#21#34#55`。
/// 对齐说明：阈值与覆盖顺序对齐 Python `tas_ma_cohere_V230512`。
#[signal(
    category = "kline",
    name = "tas_ma_cohere_V230512",
    template = "{freq}_D{di}SMA{ma_seq}_均线系统V230512",
    opcode = "TasMaCohereV230512",
    param_kind = "TasMaCohereV230512"
)]
pub fn tas_ma_cohere_v230512(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let ma_seq_str = get_str_param(params, "ma_seq", "5#13#21#34#55");
    let ma_seq: Vec<usize> = ma_seq_str
        .split('#')
        .filter_map(|x| x.parse::<usize>().ok())
        .collect();

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}SMA{}", di, ma_seq_str);
    let k3 = "均线系统V230512";
    let mut v1 = "其他";

    if ma_seq.is_empty() || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    for ma in &ma_seq {
        let key = format!("SMA#{}", ma);
        update_ma_cache(czsc, &key, "SMA", *ma, cache);
    }
    let max_ma = *ma_seq.iter().max().unwrap_or(&0);
    if czsc.bars_raw.len() < max_ma + di + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let bars = get_sub_elements(&czsc.bars_raw, di, 100);
    if bars.len() < 20 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let id_to_idx = bar_index_map(czsc);

    let mut ret_seq = Vec::with_capacity(bars.len());
    for bar in bars {
        let Some(idx) = id_to_idx.get(&bar.id).copied() else {
            continue;
        };
        let mut min_v = f64::INFINITY;
        let mut max_v = f64::NEG_INFINITY;
        for ma in &ma_seq {
            let key = format!("SMA#{}", ma);
            let val = cache
                .series
                .get(&key)
                .and_then(|s| s.get(idx))
                .copied()
                .unwrap_or(f64::NAN);
            min_v = min_v.min(val);
            max_v = max_v.max(val);
        }
        let ret = max_v / min_v - 1.0;
        ret_seq.push(ret);
    }

    if ret_seq.len() < 20 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let base = &ret_seq[..ret_seq.len() - 20];
    if base.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let mean = base.iter().sum::<f64>() / base.len() as f64;
    let var = base.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / base.len() as f64;
    let ret_std = var.sqrt();
    if !ret_std.is_finite() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let tail = &ret_seq[ret_seq.len() - 20..];
    let tight = tail.iter().filter(|x| **x < 0.5 * ret_std).count();
    if tight >= 16 {
        v1 = "粘合";
    }
    let spread = tail.iter().filter(|x| **x > ret_std).count();
    if spread >= 16 {
        v1 = "扩散";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_dif_layer_V241010：DIF 三层分类
///
/// 参数模板：`"{freq}_DIF分层W{w}T{t}_完全分类V241010"`
///
/// 信号逻辑：
/// 1. 取最近 `w` 根 DIF，计算绝对值最大幅度基准 `r`；
/// 2. `|dif_last| > r * t` 且符号为负，判 `空头远离`；
/// 3. `|dif_last| > r * t` 且符号为正，判 `多头远离`，否则 `零轴附近`。
///
/// 信号列表示例：
/// - `Signal('60分钟_DIF分层W100T30_完全分类V241010_空头远离_任意_任意_0')`
/// - `Signal('60分钟_DIF分层W100T30_完全分类V241010_零轴附近_任意_任意_0')`
///
/// 参数说明：
/// - `w`：观察窗口长度，默认 `100`；
/// - `t`：远离阈值倍率，默认 `30`。
/// 对齐说明：分层阈值口径与 Python `tas_dif_layer_V241010` 一致。
#[signal(
    category = "kline",
    name = "tas_dif_layer_V241010",
    template = "{freq}_DIF分层W{w}T{t}_完全分类V241010",
    opcode = "TasDifLayerV241010",
    param_kind = "TasDifLayerV241010"
)]
pub fn tas_dif_layer_v241010(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let w = get_usize_param(params, "w", 100);
    let t = get_usize_param(params, "t", 30);
    let k1 = czsc.freq.to_string();
    let k2 = format!("DIF分层W{}T{}", w, t);
    let k3 = "完全分类V241010";
    let mut v1 = "其他";
    if czsc.bars_raw.len() < w + 50 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let diffs = get_sub_elements(&mc.dif, 1, w);
    let r = diffs
        .iter()
        .map(|x| x.abs())
        .fold(f64::NEG_INFINITY, f64::max)
        / 100.0;
    let last = *diffs.last().unwrap();
    if last < 0.0 && last.abs() > r * t as f64 {
        v1 = "空头远离";
    } else if last > 0.0 && last.abs() > r * t as f64 {
        v1 = "多头远离";
    } else {
        v1 = "零轴附近";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_cross_status_V230619：0轴上下金死叉次数
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_金死叉V230619"`
///
/// 信号逻辑：
/// 1. 取近 100 根 DIF/DEA 并截取最近过零后的有效段；
/// 2. 在 0 轴上下分别统计金叉/死叉次数；
/// 3. 若当根形成有效交叉，输出 `0轴上/下金叉(死叉)第N次`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9_金死叉V230619_0轴下金叉第1次_任意_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9_金死叉V230619_0轴上死叉第2次_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。
/// 对齐说明：过零截取与交叉计次逻辑对齐 Python `tas_cross_status_V230619`。
#[signal(
    category = "kline",
    name = "tas_cross_status_V230619",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_金死叉V230619",
    opcode = "TasCrossStatusV230619",
    param_kind = "TasCrossStatusV230619"
)]
pub fn tas_cross_status_v230619(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MACD{}#{}#{}", di, fastperiod, slowperiod, signalperiod);
    let k3 = "金死叉V230619";
    let mut v1 = "其他".to_string();

    let mc = cache.macd.get(&cache_key).unwrap();
    let dif = get_sub_elements(&mc.dif, di, 100);
    let dea = get_sub_elements(&mc.dea, di, 100);
    if dif.len() >= 100 && dea.len() >= 100 {
        let num_k = cross_zero_axis(dif, dea);
        let dif_temp = get_sub_elements(dif, di, num_k);
        let dea_temp = get_sub_elements(dea, di, num_k);
        let dl = dif[dif.len() - 1];
        let d2 = dif[dif.len() - 2];
        let el = dea[dea.len() - 1];
        let e2 = dea[dea.len() - 2];
        if dl < 0.0 && el < 0.0 {
            let down_num_sc = down_cross_count(dif_temp, dea_temp);
            let down_num_jc = down_cross_count(dea_temp, dif_temp);
            if dl > el && d2 < e2 {
                v1 = format!("0轴下金叉第{}次", down_num_jc);
            } else if dl < el && d2 > e2 {
                v1 = format!("0轴下死叉第{}次", down_num_sc);
            }
        } else if dl > 0.0 && el > 0.0 {
            let up_num_sc = down_cross_count(dif_temp, dea_temp);
            let up_num_jc = down_cross_count(dea_temp, dif_temp);
            if dl > el && d2 < e2 {
                v1 = format!("0轴上金叉第{}次", up_num_jc);
            } else if dl < el && d2 > e2 {
                v1 = format!("0轴上死叉第{}次", up_num_sc);
            }
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// tas_cross_status_V230624：指定金死叉数值
///
/// 参数模板：`"{freq}_D{di}N{n}MD{md}_MACD交叉数量V230624"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 根 DIF/DEA 并过零截断；
/// 2. 按最小间隔 `md` 过滤交叉并统计 `jc/sc`；
/// 3. 根据当前所在零轴区域输出上下轴金叉/死叉次数。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N100MD1_MACD交叉数量V230624_0轴下金叉第2次_0轴下死叉第1次_任意_0')`
/// - `Signal('60分钟_D1N100MD1_MACD交叉数量V230624_0轴上金叉第1次_0轴上死叉第2次_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：统计窗口长度，默认 `100`；
/// - `md`：最小交叉间隔，默认 `1`。
/// 对齐说明：交叉过滤及计数口径与 Python `tas_cross_status_V230624` 保持一致。
#[signal(
    category = "kline",
    name = "tas_cross_status_V230624",
    template = "{freq}_D{di}N{n}MD{md}_MACD交叉数量V230624",
    opcode = "TasCrossStatusV230624",
    param_kind = "TasCrossStatusV230624"
)]
pub fn tas_cross_status_v230624(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 100);
    let md = get_usize_param(params, "md", 1).max(1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}MD{}", di, n, md);
    let k3 = "MACD交叉数量V230624";
    let mut v1 = "其他".to_string();
    let mut v2 = "其他".to_string();
    if czsc.bars_raw.len() < n + 1 {
        return make_kline_signal_v2(&k1, &k2, k3, &v1, &v2);
    }
    let mc = cache.macd.get(&cache_key).unwrap();
    let dif = get_sub_elements(&mc.dif, di, n);
    let dea = get_sub_elements(&mc.dea, di, n);
    let num_k = cross_zero_axis(dif, dea);
    let dif_temp = get_sub_elements(dif, 1, num_k);
    let dea_temp = get_sub_elements(dea, 1, num_k);
    let cross = fast_slow_cross(dif_temp, dea_temp);
    let (jc, sc) = cal_cross_num(&cross, md);
    let dl = dif[dif.len() - 1];
    let el = dea[dea.len() - 1];
    if dl < 0.0 && el < 0.0 {
        v1 = format!("0轴下金叉第{}次", jc);
        v2 = format!("0轴下死叉第{}次", sc);
    } else if dl > 0.0 && el > 0.0 {
        v1 = format!("0轴上金叉第{}次", jc);
        v2 = format!("0轴上死叉第{}次", sc);
    }
    make_kline_signal_v2(&k1, &k2, k3, &v1, &v2)
}

/// tas_cross_status_V230625：指定金叉/死叉次数后状态
///
/// 参数模板：`"{freq}_D{di}N{n}MD{md}J{j}S{s}_MACD交叉数量V230625"`
///
/// 信号逻辑：
/// 1. 在近 `n` 根内统计过滤后的金叉/死叉数量；
/// 2. 仅允许 `j` 或 `s` 之一生效；
/// 3. 达到目标次数后输出 `0轴上/下第N次金叉(死叉)以后`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N100MD1J2S0_MACD交叉数量V230625_0轴下第2次金叉以后_任意_任意_0')`
/// - `Signal('60分钟_D1N100MD1J0S2_MACD交叉数量V230625_0轴上第2次死叉以后_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：统计窗口长度，默认 `100`；
/// - `md`：交叉间隔阈值，默认 `1`；
/// - `j/s`：目标金叉或死叉次数，默认 `0/0`（二者不能同时非零）。
/// 对齐说明：参数约束与触发语义对齐 Python `tas_cross_status_V230625`。
#[signal(
    category = "kline",
    name = "tas_cross_status_V230625",
    template = "{freq}_D{di}N{n}MD{md}J{j}S{s}_MACD交叉数量V230625",
    opcode = "TasCrossStatusV230625",
    param_kind = "TasCrossStatusV230625"
)]
pub fn tas_cross_status_v230625(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let j = get_usize_param(params, "j", 0);
    let s = get_usize_param(params, "s", 0);
    let n = get_usize_param(params, "n", 100);
    let md = get_usize_param(params, "md", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}MD{}J{}S{}", di, n, md, j, s);
    let k3 = "MACD交叉数量V230625";
    let mut v1 = "其他".to_string();
    if j * s != 0 || czsc.bars_raw.len() < di + n + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, &v1);
    }
    let mc = cache.macd.get(&cache_key).unwrap();
    let dif = get_sub_elements(&mc.dif, di, n);
    let dea = get_sub_elements(&mc.dea, di, n);
    let num_k = cross_zero_axis(dif, dea);
    let dif_temp = get_sub_elements(dif, 1, num_k);
    let dea_temp = get_sub_elements(dea, 1, num_k);
    let cross = fast_slow_cross(dif_temp, dea_temp);
    let (jc, sc) = cal_cross_num(&cross, md);
    let dl = dif[dif.len() - 1];
    let el = dea[dea.len() - 1];
    if dl < 0.0 && el < 0.0 {
        if jc >= j && s == 0 {
            v1 = format!("0轴下第{}次金叉以后", j);
        } else if j == 0 && sc >= s {
            v1 = format!("0轴下第{}次死叉以后", s);
        }
    } else if dl > 0.0 && el > 0.0 {
        if jc >= j && s == 0 {
            v1 = format!("0轴上第{}次金叉以后", j);
        } else if j == 0 && sc >= s {
            v1 = format!("0轴上第{}次死叉以后", s);
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// tas_slope_V231019：DIF 斜率分位多空
///
/// 参数模板：`"{freq}_D{di}DIF{n}斜率T{th}_BS辅助V231019"`
///
/// 信号逻辑：
/// 1. 计算最近区间内 DIF 线性回归斜率序列；
/// 2. 计算当前斜率在历史区间中的归一化分位；
/// 3. 分位 `> th/100` 判 `看多`，`< 1-th/100` 判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1DIF10斜率T80_BS辅助V231019_看多_任意_任意_0')`
/// - `Signal('60分钟_D1DIF10斜率T80_BS辅助V231019_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：斜率回看长度，默认 `10`；
/// - `th`：分位阈值（50-100），默认 `80`。
/// 对齐说明：分位判定区间和阈值方向与 Python `tas_slope_V231019` 一致。
#[signal(
    category = "kline",
    name = "tas_slope_V231019",
    template = "{freq}_D{di}DIF{n}斜率T{th}_BS辅助V231019",
    opcode = "TasSlopeV231019",
    param_kind = "TasSlopeV231019"
)]
pub fn tas_slope_v231019(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 10);
    let th = get_usize_param(params, "th", 80);
    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}DIF{}斜率T{}", di, n, th);
    let k3 = "BS辅助V231019";
    let mut v1 = "其他";
    if !(51..100).contains(&th) || czsc.bars_raw.len() < 50 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let mc = cache.macd.get(cache_key).unwrap();
    let dif = &mc.dif;
    let end = czsc.bars_raw.len() - di + 1;
    let start = end.saturating_sub(n * 10);
    let mut slopes = Vec::new();
    for i in start..end {
        if i < n {
            slopes.push(0.0);
        } else {
            slopes.push(linear_slope(&dif[i - n..i]));
        }
    }
    if slopes.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let last = *slopes.last().unwrap();
    let min_v = slopes.iter().copied().fold(f64::INFINITY, f64::min);
    let max_v = slopes.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    if (max_v - min_v).abs() > f64::EPSILON {
        let q = (last - min_v) / (max_v - min_v);
        if q > th as f64 / 100.0 {
            v1 = "看多";
        } else if q < 1.0 - th as f64 / 100.0 {
            v1 = "看空";
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_boll_vt_V230212：BOLL 通道突破进出场信号
///
/// 参数模板：`"{freq}_D{di}BOLL{timeperiod}S{nbdev}MO{max_overlap}_BS辅助V230212"`
///
/// 信号逻辑：
/// 1. 计算指定参数的 BOLL 上下轨（`nbdev / 10` 为标准差倍数）；
/// 2. 最新收盘价在上轨上方，且窗口内曾有收盘价在上轨下方，判 `看多`；
/// 3. 最新收盘价在下轨下方，且窗口内曾有收盘价在下轨上方，判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1BOLL20S20MO5_BS辅助V230212_看多_任意_任意_0')`
/// - `Signal('60分钟_D1BOLL20S20MO5_BS辅助V230212_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：BOLL 周期，默认 `20`；
/// - `nbdev`：标准差倍数 *10，默认 `20`；
/// - `max_overlap`：窗口重叠长度，默认 `5`。
/// 对齐说明：严格按 Python `tas_boll_vt_V230212` 判定分支实现。
#[signal(
    category = "kline",
    name = "tas_boll_vt_V230212",
    template = "{freq}_D{di}BOLL{timeperiod}S{nbdev}MO{max_overlap}_BS辅助V230212",
    opcode = "TasBollVtV230212",
    param_kind = "TasBollVtV230212"
)]
pub fn tas_boll_vt_v230212(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 20);
    let nbdev = get_usize_param(params, "nbdev", 20);
    let max_overlap = get_usize_param(params, "max_overlap", 5);
    let nbdev_f = nbdev as f64 / 10.0;
    let cache_key = format!("BOLL{}#{:.1}", timeperiod, nbdev_f);
    update_boll_cache(czsc, &cache_key, timeperiod, nbdev_f, cache);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}BOLL{}S{}MO{}", di, timeperiod, nbdev, max_overlap);
    let k3 = "BS辅助V230212";
    let mut v1 = "其他";

    let bars = get_sub_elements(&czsc.bars_raw, di, max_overlap + 1);
    if bars.len() < max_overlap + 1 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let boll = cache.boll.get(&cache_key).unwrap();
    let end = czsc.bars_raw.len() - di + 1;
    let start = end - bars.len();
    let last_i = end - 1;
    let last_bar = &bars[bars.len() - 1];
    if last_bar.close > boll.upper[last_i]
        && bars
            .iter()
            .enumerate()
            .any(|(i, b)| b.close < boll.upper[start + i])
    {
        v1 = "看多";
    } else if last_bar.close < boll.lower[last_i]
        && bars
            .iter()
            .enumerate()
            .any(|(i, b)| b.close > boll.lower[start + i])
    {
        v1 = "看空";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_cci_base_V230402：CCI 极值连续计数信号
///
/// 参数模板：`"{freq}_D{di}CCI{timeperiod}#{min_count}#{max_count}_BS辅助V230402"`
///
/// 信号逻辑：
/// 1. 计算 CCI 序列；
/// 2. 若末尾连续 `CCI > 100` 次数落在 `[min_count, max_count)`，判 `多头`；
/// 3. 若末尾连续 `CCI < -100` 次数落在 `[min_count, max_count)`，判 `空头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1CCI14#3#6_BS辅助V230402_多头_任意_任意_0')`
/// - `Signal('60分钟_D1CCI14#3#6_BS辅助V230402_空头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：CCI 周期，默认 `14`；
/// - `min_count`：最小连续次数，默认 `3`；
/// - `max_count`：最大连续次数上界（开区间），默认 `min_count + 3`。
/// 对齐说明：连续计数和覆盖顺序与 Python `tas_cci_base_V230402` 一致。
#[signal(
    category = "kline",
    name = "tas_cci_base_V230402",
    template = "{freq}_D{di}CCI{timeperiod}#{min_count}#{max_count}_BS辅助V230402",
    opcode = "TasCciBaseV230402",
    param_kind = "TasCciBaseV230402"
)]
pub fn tas_cci_base_v230402(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 14);
    let min_count = get_usize_param(params, "min_count", 3);
    let max_count = get_usize_param(params, "max_count", min_count + 3);
    assert!(min_count < max_count, "min_count 必须小于 max_count");

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}CCI{}#{}#{}", di, timeperiod, min_count, max_count);
    let k3 = "BS辅助V230402";
    let mut v1 = "其他";

    let cache_key = format!("CCI{}", timeperiod);
    update_cci_cache(czsc, &cache_key, timeperiod, cache);
    let cci_series = cache.series.get(&cache_key).unwrap();
    let bars = get_sub_elements(&czsc.bars_raw, di, max_count + 1);
    if bars.len() != max_count + 1 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let end = czsc.bars_raw.len() - di + 1;
    let start = end - bars.len();
    let cci: Vec<f64> = (start..end).map(|i| cci_series[i]).collect();
    let long: Vec<bool> = cci.iter().map(|x| *x > 100.0).collect();
    let short: Vec<bool> = cci.iter().map(|x| *x < -100.0).collect();
    let lc = if *long.last().unwrap_or(&false) {
        count_last_same(&long)
    } else {
        0
    };
    let sc = if *short.last().unwrap_or(&false) {
        count_last_same(&short)
    } else {
        0
    };

    if max_count > lc && lc >= min_count {
        v1 = "多头";
    }
    if max_count > sc && sc >= min_count {
        v1 = "空头";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cci_decision_V240620：CCI 逆势决策区域
///
/// 参数模板：`"{freq}_N{n}CCI_决策区域V240620"`
///
/// 信号逻辑：
/// 1. 固定计算 `CCI(14)`；
/// 2. 取最近 `n` 根 CCI：若最小值 `< -100` 判 `开多`，`v2` 为 `< -100` 的出现次数；
/// 3. 若最大值 `> 100` 判 `开空`，`v2` 为 `> 100` 的出现次数（覆盖开多分支）。
///
/// 信号列表示例：
/// - `Signal('15分钟_N4CCI_决策区域V240620_开多_2次_任意_0')`
/// - `Signal('15分钟_N4CCI_决策区域V240620_开空_1次_任意_0')`
///
/// 参数说明：
/// - `n`：统计窗口长度，默认 `2`。
/// 对齐说明：分支顺序与 Python `cci_decision_V240620` 保持一致（后判空头覆盖前判多头）。
#[signal(
    category = "kline",
    name = "cci_decision_V240620",
    template = "{freq}_N{n}CCI_决策区域V240620",
    opcode = "CciDecisionV240620",
    param_kind = "CciDecisionV240620"
)]
pub fn cci_decision_v240620(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 2);
    let k1 = czsc.freq.to_string();
    let k2 = format!("N{}CCI", n);
    let k3 = "决策区域V240620";
    let mut v1 = "其他";
    let mut v2 = "任意".to_string();

    if czsc.bars_raw.len() < 100 {
        return make_kline_signal_v2(&k1, &k2, k3, v1, &v2);
    }

    let cache_key = "CCI14";
    update_cci_cache(czsc, cache_key, 14, cache);
    let cci = match cache.series.get(cache_key) {
        Some(v) if !v.is_empty() => v,
        _ => return make_kline_signal_v2(&k1, &k2, k3, v1, &v2),
    };
    let start = if n == 0 {
        0
    } else {
        cci.len().saturating_sub(n)
    };
    let cci_seq = &cci[start..];
    if cci_seq.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, &v2);
    }

    let short_count = cci_seq.iter().filter(|x| **x > 100.0).count();
    let long_count = cci_seq.iter().filter(|x| **x < -100.0).count();

    if cci_seq.iter().copied().fold(f64::INFINITY, f64::min) < -100.0 {
        v1 = "开多";
        v2 = format!("{}次", long_count);
    }
    if cci_seq.iter().copied().fold(f64::NEG_INFINITY, f64::max) > 100.0 {
        v1 = "开空";
        v2 = format!("{}次", short_count);
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}

/// tas_accelerate_V230531：BOLL 通道加速信号
///
/// 参数模板：`"{freq}_D{di}N{n}T{t}_BOLL加速V230531"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 根，计算中线/上轨/下轨涨跌幅；
/// 2. 全部在中线上方且 `上轨涨幅 > t/10 * 中线涨幅 > 0`，判 `多头加速`；
/// 3. 全部在中线下方且 `下轨涨幅 < t/10 * 中线涨幅 < 0`，判 `空头加速`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N20T20_BOLL加速V230531_多头加速_升破上轨_任意_0')`
/// - `Signal('60分钟_D1N20T20_BOLL加速V230531_空头加速_跌破下轨_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：观察窗口，默认 `20`；
/// - `t`：轨道/中线倍率阈值（除以10），默认 `20`。
/// 对齐说明：按 Python `tas_accelerate_V230531` 双分支覆盖语义实现。
#[signal(
    category = "kline",
    name = "tas_accelerate_V230531",
    template = "{freq}_D{di}N{n}T{t}_BOLL加速V230531",
    opcode = "TasAccelerateV230531",
    param_kind = "TasAccelerateV230531"
)]
pub fn tas_accelerate_v230531(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 20);
    let t = get_usize_param(params, "t", 20);
    let cache_key = "BOLL20#2.0";
    update_boll_cache(czsc, cache_key, 20, 2.0, cache);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}T{}", di, n, t);
    let k3 = "BOLL加速V230531";
    let mut v1 = "其他";
    let mut v2 = "其他";

    if czsc.bars_raw.len() < 40 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, v2);
    }
    let bars = get_sub_elements(&czsc.bars_raw, di, n);
    if bars.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, v2);
    }

    let boll = cache.boll.get(cache_key).unwrap();
    let end = czsc.bars_raw.len() - di + 1;
    let start = end - bars.len();
    let first_i = start;
    let last_i = end - 1;
    let mid_zdf = boll.mid[last_i] / boll.mid[first_i] - 1.0;
    let up_zdf = boll.upper[last_i] / boll.upper[first_i] - 1.0;
    let down_zdf = boll.lower[last_i] / boll.lower[first_i] - 1.0;
    let all_above_mid = bars
        .iter()
        .enumerate()
        .all(|(i, b)| b.close > boll.mid[start + i]);
    let all_below_mid = bars
        .iter()
        .enumerate()
        .all(|(i, b)| b.close < boll.mid[start + i]);
    let last_bar = &bars[bars.len() - 1];

    if all_above_mid && up_zdf > (t as f64 / 10.0) * mid_zdf && mid_zdf > 0.0 {
        v1 = "多头加速";
        v2 = if boll.upper[last_i] < last_bar.high {
            "升破上轨"
        } else {
            "未破上轨"
        };
    }
    if all_below_mid && down_zdf < (t as f64 / 10.0) * mid_zdf && mid_zdf < 0.0 {
        v1 = "空头加速";
        v2 = if boll.lower[last_i] > last_bar.low {
            "跌破下轨"
        } else {
            "未破下轨"
        };
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_low_trend_V230627：阴跌/小阳趋势信号
///
/// 参数模板：`"{freq}_D{di}N{n}TH{th}_趋势230627"`
///
/// 信号逻辑：
/// 1. 对窗口内实体振幅做阈值过滤，剔除波动过大的场景；
/// 2. 统计 `low <= 历史收盘最小值` 次数，超过 `0.8*n` 判 `阴跌趋势`；
/// 3. 统计 `high >= 历史收盘最大值` 次数，超过 `0.8*n` 判 `小阳趋势`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N13TH300_趋势230627_阴跌趋势_任意_任意_0')`
/// - `Signal('60分钟_D1N13TH300_趋势230627_小阳趋势_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：统计窗口，默认 `13`；
/// - `th`：实体振幅阈值（BP），默认 `300`。
/// 对齐说明：循环窗口与阈值比较口径对齐 Python `tas_low_trend_V230627`。
#[signal(
    category = "kline",
    name = "tas_low_trend_V230627",
    template = "{freq}_D{di}N{n}TH{th}_趋势230627",
    opcode = "TasLowTrendV230627",
    param_kind = "TasLowTrendV230627"
)]
pub fn tas_low_trend_v230627(czsc: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 13);
    let th = get_usize_param(params, "th", 300);
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}TH{}", di, n, th);
    let k3 = "趋势230627";
    let mut v1 = "其他";

    if czsc.bars_raw.len() < di + n + 8 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let bars = get_sub_elements(&czsc.bars_raw, di, n + 5);
    if bars.len() < n + 5 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let solid_zf: Vec<f64> = bars[5..]
        .iter()
        .map(|x| (x.close / x.open - 1.0).abs() * 10000.0)
        .collect();
    let violent = solid_zf.iter().filter(|x| **x > th as f64).count();
    if violent as f64 > (0.2 * n as f64).max(3.0) {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let mut min_count = 0usize;
    let mut max_count = 0usize;
    for i in 5..bars.len() {
        let bar = &bars[i];
        let w5 = &bars[..i];
        let min_close = w5.iter().map(|x| x.close).fold(f64::INFINITY, f64::min);
        let max_close = w5.iter().map(|x| x.close).fold(f64::NEG_INFINITY, f64::max);
        if bar.low <= min_close {
            min_count += 1;
        }
        if bar.high >= max_close {
            max_count += 1;
        }
    }

    if min_count as f64 >= 0.8 * n as f64 {
        v1 = "阴跌趋势";
    }
    if max_count as f64 >= 0.8 * n as f64 {
        v1 = "小阳趋势";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_atr_V230630：ATR 波动分层信号
///
/// 参数模板：`"{freq}_D{di}ATR{timeperiod}_波动V230630"`
///
/// 信号逻辑：
/// 1. 计算 `ATR / close` 波动率；
/// 2. 对最近 100 根波动率做 `qcut(10)` 分层；
/// 3. 输出末值所在层级 `第{n}层`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1ATR14_波动V230630_第3层_任意_任意_0')`
/// - `Signal('60分钟_D1ATR14_波动V230630_第9层_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：ATR 周期，默认 `14`。
/// 对齐说明：ATR 预热与分层边界对齐 Python `tas_atr_V230630`。
#[signal(
    category = "kline",
    name = "tas_atr_V230630",
    template = "{freq}_D{di}ATR{timeperiod}_波动V230630",
    opcode = "TasAtrV230630",
    param_kind = "TasAtrV230630"
)]
pub fn tas_atr_v230630(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 14);
    let cache_key = format!("ATR{}", timeperiod);
    update_atr_cache(czsc, &cache_key, timeperiod, cache);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}ATR{}", di, timeperiod);
    let k3 = "波动V230630";
    let mut v1 = "其他".to_string();

    if czsc.bars_raw.len() < di + timeperiod + 8 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, &v1);
    }

    let bars = get_sub_elements(&czsc.bars_raw, di, 100);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, &v1);
    }
    let atr = cache.series.get(&cache_key).unwrap();
    let end = czsc.bars_raw.len() - di + 1;
    let start = end - bars.len();
    let lev: Vec<f64> = bars
        .iter()
        .enumerate()
        .map(|(i, b)| atr[start + i] / b.close)
        .collect();
    if let Some(q) = qcut_last_label(&lev, 10) {
        v1 = format!("第{}层", q + 1);
    }

    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// tas_macd_base_V230320：MACD/DIF/DEA 多空与方向信号（含重叠约束）
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}MO{max_overlap}#{key}_BS辅助V230320"`
///
/// 信号逻辑：
/// 1. 计算 `MACD/DIF/DEA` 序列；
/// 2. 取倒数 `di` 截止的最近 `max_overlap+1` 根值；
/// 3. 若 `last > 0` 且前序存在 `< 0` 判 `多头`；
/// 4. 若 `last < 0` 且前序存在 `> 0` 判 `空头`；
/// 5. 否则判 `其他`；方向由 `last >= prev` 判 `向上/向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9MO3#MACD_BS辅助V230320_多头_向上_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9MO3#DIF_BS辅助V230320_空头_向下_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `key`：指标键，`MACD/DIF/DEA`，默认 `MACD`；
/// - `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`；
/// - `max_overlap`：最大重叠窗口，默认 `3`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_base_V230320",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}MO{max_overlap}#{key}_BS辅助V230320",
    opcode = "TasMacdBaseV230320",
    param_kind = "TasMacdBaseV230320"
)]
pub fn tas_macd_base_v230320(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let key = get_str_param(params, "key", "MACD").to_uppercase();
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let max_overlap = get_usize_param(params, "max_overlap", 3);

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}MACD{}#{}#{}MO{}#{}",
        di, fastperiod, slowperiod, signalperiod, max_overlap, key
    );
    let k3 = "BS辅助V230320";

    if !matches!(key.as_str(), "MACD" | "DIF" | "DEA") || czsc.bars_raw.len() < 5 + di + max_overlap
    {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );

    let mc = cache.macd.get(&cache_key).unwrap();
    let series = match key.as_str() {
        "DIF" => &mc.dif,
        "DEA" => &mc.dea,
        _ => &mc.macd,
    };
    let values = get_sub_elements(series, di, max_overlap + 1);
    if values.len() < max_overlap + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let last = *values.last().unwrap();
    let prev = values[values.len() - 2];
    let has_neg = values[..values.len() - 1].iter().any(|x| *x < 0.0);
    let has_pos = values[..values.len() - 1].iter().any(|x| *x > 0.0);
    let v1 = if last > 0.0 && has_neg {
        "多头"
    } else if last < 0.0 && has_pos {
        "空头"
    } else {
        "其他"
    };

    if v1 == "其他" {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let v2 = if last >= prev { "向上" } else { "向下" };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_macd_change_V221105：MACD变色次数信号
///
/// 参数模板：`"{freq}_D{di}K{n}#MACD{fastperiod}#{slowperiod}#{signalperiod}变色次数_BS辅助V221105"`
///
/// 信号逻辑：
/// 1. 在最近 `n` 根上计算 DIF/DEA 金叉死叉序列；
/// 2. 过滤 `距离<2` 的抖动交叉；
/// 3. 同类型连续交叉按 Python 语义合并；
/// 4. 输出合并后次数 `"{num}次"`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_0次_任意_任意_0')`
/// - `Signal('60分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_3次_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：统计窗口长度，默认 `55`；
/// - `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_change_V221105",
    template = "{freq}_D{di}K{n}#MACD{fastperiod}#{slowperiod}#{signalperiod}变色次数_BS辅助V221105",
    opcode = "TasMacdChangeV221105",
    param_kind = "TasMacdChangeV221105"
)]
pub fn tas_macd_change_v221105(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 55);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);

    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let macd_cache = cache.macd.get(&cache_key).unwrap();
    let dif = get_sub_elements(&macd_cache.dif, di, n);
    let dea = get_sub_elements(&macd_cache.dea, di, n);

    let cross = fast_slow_cross(dif, dea);
    let re_cross: Vec<_> = cross
        .into_iter()
        .filter(|x| x.get("距离").copied().unwrap_or(0.0) >= 2.0)
        .collect();

    let num = if re_cross.is_empty() {
        0
    } else {
        let mut merged: Vec<HashMap<&'static str, f64>> = Vec::new();
        for c in re_cross {
            if !merged.is_empty()
                && c.get("类型").copied().unwrap_or(0.0)
                    == merged
                        .last()
                        .and_then(|x| x.get("类型"))
                        .copied()
                        .unwrap_or(0.0)
            {
                merged.pop();
            }
            merged.push(c);
        }
        merged.len()
    };

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}K{}#MACD{}#{}#{}变色次数",
        di, n, fastperiod, slowperiod, signalperiod
    );
    let k3 = "BS辅助V221105";
    let v1 = format!("{}次", num);
    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// tas_dif_zero_V240614：DIF靠近零轴买卖点信号
///
/// 参数模板：`"{freq}_DIF靠近零轴W{w}T{t}_BS辅助V240614"`
///
/// 信号逻辑：
/// 1. 取最近 `w` 根K线的 `DIF` 序列；
/// 2. 计算 `delta = std(diffs) * t / 100`；
/// 3. 若 `diffs` 全部大于0，且 `diffs[-1]` 靠近零轴，同时 `max(diffs)` 显著高于均值+标准差，判 `买点`；
/// 4. 若 `diffs` 全部小于0，且 `diffs[-1]` 靠近零轴，同时 `min(diffs)` 显著低于-(均值+标准差)，判 `卖点`。
///
/// 信号列表示例：
/// - `Signal('60分钟_DIF靠近零轴W20T50_BS辅助V240614_买点_任意_任意_0')`
/// - `Signal('60分钟_DIF靠近零轴W20T50_BS辅助V240614_卖点_任意_任意_0')`
/// - `Signal('60分钟_DIF靠近零轴W20T50_BS辅助V240614_其他_任意_任意_0')`
///
/// 参数说明：
/// - `w`：K线窗口长度，默认 `20`；
/// - `t`：波动率倍数（除以100），默认 `50`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_dif_zero_V240614",
    template = "{freq}_DIF靠近零轴W{w}T{t}_BS辅助V240614",
    opcode = "TasDifZeroV240614",
    param_kind = "TasDifZeroV240614"
)]
pub fn tas_dif_zero_v240614(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let w = get_usize_param(params, "w", 20);
    let t = get_usize_param(params, "t", 50) as f64;

    let k1 = czsc.freq.to_string();
    let k2 = format!("DIF靠近零轴W{}T{}", w, t as usize);
    let k3 = "BS辅助V240614";
    let mut v1 = "其他";

    if czsc.bars_raw.len() < 110 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let macd_cache = cache.macd.get(cache_key).unwrap();
    let diffs = get_sub_elements(&macd_cache.dif, 1, w);
    if diffs.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let mean = diffs.iter().sum::<f64>() / diffs.len() as f64;
    let variance = diffs.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / diffs.len() as f64;
    let std_diff = variance.sqrt();
    let delta = std_diff * t / 100.0;
    let max_diff = diffs.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let min_diff = diffs.iter().copied().fold(f64::INFINITY, f64::min);
    let abs_mean_diff = mean.abs();
    let last = *diffs.last().unwrap();

    let all_pos = diffs.iter().all(|&x| x > 0.0);
    let all_neg = diffs.iter().all(|&x| x < 0.0);
    if all_pos && delta > last && last > -delta && max_diff > abs_mean_diff + std_diff {
        v1 = "买点";
    }
    if all_neg && -delta < last && last < delta && min_diff < -(abs_mean_diff + std_diff) {
        v1 = "卖点";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_dif_zero_V240612：DIF靠近零轴买卖点信号（基于最近一笔）
///
/// 参数模板：`"{freq}_DIF靠近零轴T{t}_BS辅助V240612"`
///
/// 信号逻辑：
/// 1. 取最近一笔内部原始K线的 `DIF` 序列；
/// 2. 计算 `delta = std(diffs) * t / 100`；
/// 3. 若最后一笔为向下笔，且末端 `DIF` 靠近零轴，同时 `max(diffs)` 显著高于均值+标准差，判 `买点`；
/// 4. 若最后一笔为向上笔，且末端 `DIF` 靠近零轴，同时 `min(diffs)` 显著低于-(均值+标准差)，判 `卖点`。
///
/// 信号列表示例：
/// - `Signal('60分钟_DIF靠近零轴T50_BS辅助V240612_买点_任意_任意_0')`
/// - `Signal('60分钟_DIF靠近零轴T50_BS辅助V240612_卖点_任意_任意_0')`
/// - `Signal('60分钟_DIF靠近零轴T50_BS辅助V240612_其他_任意_任意_0')`
///
/// 参数说明：
/// - `t`：波动率倍数（除以100），默认 `50`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_dif_zero_V240612",
    template = "{freq}_DIF靠近零轴T{t}_BS辅助V240612",
    opcode = "TasDifZeroV240612",
    param_kind = "TasDifZeroV240612"
)]
pub fn tas_dif_zero_v240612(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let t = get_usize_param(params, "t", 50) as f64;
    let k1 = czsc.freq.to_string();
    let k2 = format!("DIF靠近零轴T{}", t as usize);
    let k3 = "BS辅助V240612";
    let mut v1 = "其他";

    if czsc.bars_raw.len() < 110 || czsc.bars_ubi.len() > 7 || czsc.bi_list.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let macd_cache = cache.macd.get(cache_key).unwrap();
    let last_bi = czsc.bi_list.last().unwrap();
    let raw_bars = last_bi.get_raw_bars();
    if raw_bars.len() < 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let id_to_idx: HashMap<i32, usize> = czsc
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();
    let mut diffs = Vec::with_capacity(raw_bars.len());
    for b in &raw_bars {
        if let Some(&idx) = id_to_idx.get(&b.id) {
            diffs.push(macd_cache.dif[idx]);
        }
    }
    if diffs.len() < 7 || diffs.iter().any(|x| !x.is_finite()) {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let mean = diffs.iter().sum::<f64>() / diffs.len() as f64;
    let variance = diffs.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / diffs.len() as f64;
    let std_diff = variance.sqrt();
    let delta = std_diff * t / 100.0;
    let max_diff = diffs.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let min_diff = diffs.iter().copied().fold(f64::INFINITY, f64::min);
    let abs_mean_diff = mean.abs();
    let last = *diffs.last().unwrap();

    if matches!(last_bi.direction, Direction::Down)
        && delta > last
        && last > -delta
        && max_diff > abs_mean_diff + std_diff
    {
        v1 = "买点";
    }
    if matches!(last_bi.direction, Direction::Up)
        && -delta < last
        && last < delta
        && min_diff < -(abs_mean_diff + std_diff)
    {
        v1 = "卖点";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bc_V221201：MACD背驰辅助信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}#MACD{fastperiod}#{slowperiod}#{signalperiod}_BCV221201"`
///
/// 信号逻辑：
/// 1. 取最近 `m+n` 根K线，前 `m` 为对照窗口，后 `n` 为近端窗口；
/// 2. 若近端价格创新低且MACD低点抬高，判 `底部` 背驰；
/// 3. 若近端价格创新高且MACD高点走低，判 `顶部` 背驰；
/// 4. 并给出当前柱体颜色 `红柱/绿柱`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N3M50#MACD12#26#9_BCV221201_底部_绿柱_任意_0')`
/// - `Signal('60分钟_D1N3M50#MACD12#26#9_BCV221201_顶部_红柱_任意_0')`
/// - `Signal('60分钟_D1N3M50#MACD12#26#9_BCV221201_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n/m`：近端窗口与对照窗口长度，默认 `3/50`；
/// - `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_bc_V221201",
    template = "{freq}_D{di}N{n}M{m}#MACD{fastperiod}#{slowperiod}#{signalperiod}_BCV221201",
    opcode = "TasMacdBcV221201",
    param_kind = "TasMacdBcV221201"
)]
pub fn tas_macd_bc_v221201(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 3);
    let m = get_usize_param(params, "m", 50);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);

    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    crate::utils::ta::update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}N{}M{}#MACD{}#{}#{}",
        di, n, m, fastperiod, slowperiod, signalperiod
    );
    let k3 = "BCV221201";
    let mut v1 = "其他";
    let mut v2 = "任意";

    let macd_cache = cache.macd.get(&cache_key).unwrap();
    let bars = get_sub_elements(&czsc.bars_raw, di, n + m);
    let macd_sub = get_sub_elements(&macd_cache.macd, di, n + m);
    if bars.len() == n + m && macd_sub.len() == n + m {
        let m_close: Vec<f64> = bars[..m].iter().map(|x| x.close).collect();
        let m_macd = macd_sub[..m].to_vec();
        let n_close: Vec<f64> = bars[m..].iter().map(|x| x.close).collect();
        let n_macd = macd_sub[m..].to_vec();

        let n_macd_last = n_macd.last().unwrap();
        let n_macd_prev = n_macd.get(n_macd.len() - 2).unwrap_or(&0.0);

        // 对齐 Python 内建 min/max 的 NaN 语义（首元素为 NaN 时结果保持 NaN）
        let py_min = |xs: &[f64]| -> f64 {
            let mut it = xs.iter();
            let mut best = *it.next().unwrap_or(&f64::NAN);
            for &x in it {
                if x < best {
                    best = x;
                }
            }
            best
        };
        let py_max = |xs: &[f64]| -> f64 {
            let mut it = xs.iter();
            let mut best = *it.next().unwrap_or(&f64::NAN);
            for &x in it {
                if x > best {
                    best = x;
                }
            }
            best
        };

        if n_macd_last > n_macd_prev {
            let min_n_close = py_min(&n_close);
            let min_m_close = py_min(&m_close);
            let min_n_macd = py_min(&n_macd);
            let min_m_macd = py_min(&m_macd);
            if min_n_close < min_m_close && min_n_macd > min_m_macd {
                v1 = "底部";
            }
        } else if n_macd_last < n_macd_prev {
            let max_n_close = py_max(&n_close);
            let max_m_close = py_max(&m_close);
            let max_n_macd = py_max(&n_macd);
            let max_m_macd = py_max(&m_macd);
            if max_n_close > max_m_close && max_n_macd < max_m_macd {
                v1 = "顶部";
            }
        }

        v2 = if *n_macd_last > 0.0 {
            "红柱"
        } else {
            "绿柱"
        };
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_angle_V230802：笔角度偏离信号
///
/// 参数模板：`"{freq}_D{di}N{n}T{th}_笔角度V230802"`
///
/// 信号逻辑：
/// 1. 定义角度为 `power_price / length`；
/// 2. 取同向历史 `n` 笔角度均值作为基线；
/// 3. 当前角度低于 `th%` 时输出反向信号。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N9T50_笔角度V230802_空头_任意_任意_0')`
/// - `Signal('60分钟_D1N9T50_笔角度V230802_多头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 笔，默认 `1`；
/// - `n`：同向样本数，默认 `9`；
/// - `th`：角度阈值百分比，默认 `50`。
/// 对齐说明：`length` 口径使用 `BI.length`（无包含K数量）与 Python 对齐。
#[signal(
    category = "kline",
    name = "tas_angle_V230802",
    template = "{freq}_D{di}N{n}T{th}_笔角度V230802",
    opcode = "TasAngleV230802",
    param_kind = "TasAngleV230802"
)]
pub fn tas_angle_v230802(czsc: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 9);
    let th = get_usize_param(params, "th", 50);
    assert!(th > 30 && th < 300, "th 取值范围为 30 ~ 300");

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}T{}", di, n, th);
    let k3 = "笔角度V230802";
    let mut v1 = "其他";

    if czsc.bi_list.len() < di + 2 * n + 2 || czsc.bars_ubi.len() >= 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let bis = get_sub_elements(&czsc.bi_list, di, n * 2 + 1);
    if bis.len() < n * 2 + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let b1 = bis.last().unwrap();
    let b1_len = b1.bars.len();
    if b1_len == 0 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let b1_angle = b1.get_power_price() / b1_len as f64;
    let same_dir_ang: Vec<f64> = bis[..bis.len() - 1]
        .iter()
        .filter(|bi| bi.direction == b1.direction)
        .filter_map(|bi| {
            let l = bi.bars.len();
            if l > 0 {
                Some(bi.get_power_price() / l as f64)
            } else {
                None
            }
        })
        .rev()
        .take(n)
        .collect::<Vec<f64>>()
        .into_iter()
        .rev()
        .collect();
    if !same_dir_ang.is_empty() {
        let mean = same_dir_ang.iter().sum::<f64>() / same_dir_ang.len() as f64;
        if b1_angle < mean * th as f64 / 100.0 {
            v1 = if b1.direction == Direction::Up {
                "空头"
            } else {
                "多头"
            };
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_double_ma_V240208：双均线交叉结构信号
///
/// 参数模板：`"{freq}_D{di}N{N}M{M}双均线_BS辅助V240208"`
///
/// 信号逻辑：
/// 1. 计算 `N/M` 双均线并识别交叉序列；
/// 2. 最近三次交叉记作 `X1/X2/X3`；
/// 3. `X3` 金叉且 `X2` 快线最高判 `多头`，死叉镜像判 `空头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N20M60双均线_BS辅助V240208_多头_任意_任意_0')`
/// - `Signal('60分钟_D1N20M60双均线_BS辅助V240208_空头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `N`：快线周期，默认 `20`；
/// - `M`：慢线周期，默认 `60`。
/// 对齐说明：交叉类型与快线比较逻辑对齐 Python `tas_double_ma_V240208`。
#[signal(
    category = "kline",
    name = "tas_double_ma_V240208",
    template = "{freq}_D{di}N{N}M{M}双均线_BS辅助V240208",
    opcode = "TasDoubleMaV240208",
    param_kind = "TasDoubleMaV240208"
)]
pub fn tas_double_ma_v240208(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "N", 20);
    let m = get_usize_param(params, "M", 60);
    assert!(n < m, "N 必须小于 M");

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}M{}双均线", di, n, m);
    let k3 = "BS辅助V240208";
    let mut v1 = "其他";

    let key_fast = format!("{}_{}_{}", czsc.freq, "SMA", n);
    let key_slow = format!("{}_{}_{}", czsc.freq, "SMA", m);
    update_ma_cache(czsc, &key_fast, "SMA", n, cache);
    update_ma_cache(czsc, &key_slow, "SMA", m, cache);
    let fast_all = cache.series.get(&key_fast).unwrap();
    let slow_all = cache.series.get(&key_slow).unwrap();
    let bars = get_sub_elements(&czsc.bars_raw, di, m * 30);
    if bars.is_empty() || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let end = czsc.bars_raw.len() - di + 1;
    let start = end - bars.len();
    let fast_ma: Vec<f64> = (start..end).map(|i| fast_all[i]).collect();
    let slow_ma: Vec<f64> = (start..end).map(|i| slow_all[i]).collect();
    let cross_info = fast_slow_cross(&fast_ma, &slow_ma);
    if cross_info.len() >= 3 {
        let x1 = &cross_info[cross_info.len() - 3];
        let x2 = &cross_info[cross_info.len() - 2];
        let x3 = &cross_info[cross_info.len() - 1];
        if x3.get("类型").copied().unwrap_or(0.0) > 0.0
            && x2.get("快线").copied().unwrap_or(f64::NEG_INFINITY)
                > x1.get("快线")
                    .copied()
                    .unwrap_or(f64::NEG_INFINITY)
                    .max(x3.get("快线").copied().unwrap_or(f64::NEG_INFINITY))
        {
            v1 = "多头";
        } else if x3.get("类型").copied().unwrap_or(0.0) < 0.0
            && x2.get("快线").copied().unwrap_or(f64::INFINITY)
                < x1.get("快线")
                    .copied()
                    .unwrap_or(f64::INFINITY)
                    .min(x3.get("快线").copied().unwrap_or(f64::INFINITY))
        {
            v1 = "空头";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_dma_bs_V240608：双均线顺势回调买卖点
///
/// 参数模板：`"{freq}_N{n}双均线{t1}#{t2}顺势_BS辅助V240608"`
///
/// 信号逻辑：
/// 1. 以 `t1/t2` 均线顺势方向做过滤；
/// 2. 在 `ma2` 附近按离散价格序号选取回踩/反抽位；
/// 3. 满足穿越与收盘条件时给出 `买点/卖点`。
///
/// 信号列表示例：
/// - `Signal('60分钟_N5双均线5#10顺势_BS辅助V240608_买点_任意_任意_0')`
/// - `Signal('60分钟_N5双均线5#10顺势_BS辅助V240608_卖点_任意_任意_0')`
///
/// 参数说明：
/// - `n`：价格序号偏移，默认 `5`；
/// - `t1`：快线周期，默认 `5`；
/// - `t2`：慢线周期，默认 `10`。
/// 对齐说明：价格位选取（含负索引语义）与 Python `tas_dma_bs_V240608` 一致。
#[signal(
    category = "kline",
    name = "tas_dma_bs_V240608",
    template = "{freq}_N{n}双均线{t1}#{t2}顺势_BS辅助V240608",
    opcode = "TasDmaBsV240608",
    param_kind = "TasDmaBsV240608"
)]
pub fn tas_dma_bs_v240608(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 5);
    let t1 = get_usize_param(params, "t1", 5);
    let t2 = get_usize_param(params, "t2", 10);
    assert!(t1 < t2, "均线1的周期必须小于均线2的周期");

    let k1 = czsc.freq.to_string();
    let k2 = format!("N{}双均线{}#{}顺势", n, t1, t2);
    let k3 = "BS辅助V240608";
    let mut v1 = "其他";

    let ma1_key = format!("{}_{}_{}", czsc.freq, "SMA", t1);
    let ma2_key = format!("{}_{}_{}", czsc.freq, "SMA", t2);
    update_ma_cache(czsc, &ma1_key, "SMA", t1, cache);
    update_ma_cache(czsc, &ma2_key, "SMA", t2, cache);
    let ma1 = cache.series.get(&ma1_key).unwrap();
    let ma2 = cache.series.get(&ma2_key).unwrap();

    if czsc.bars_raw.len() < 110 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let bars = &czsc.bars_raw[czsc.bars_raw.len() - 100..];
    let mut unique_prices: Vec<f64> = bars
        .iter()
        .flat_map(|x| [x.close, x.high, x.low, x.open])
        .collect();
    unique_prices.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    unique_prices.dedup_by(|a, b| (*a - *b).abs() <= f64::EPSILON);

    let idx2 = czsc.bars_raw.len() - 1;
    let idx1 = czsc.bars_raw.len() - 2;
    let bar1 = &czsc.bars_raw[idx1];
    let bar2 = &czsc.bars_raw[idx2];
    let ma1_value = ma1[idx2];
    let ma2_value = ma2[idx2];
    let lower_prices: Vec<f64> = unique_prices
        .iter()
        .copied()
        .filter(|x| *x < ma2_value)
        .collect();
    let upper_prices: Vec<f64> = unique_prices
        .iter()
        .copied()
        .filter(|x| *x > ma2_value)
        .collect();

    if !upper_prices.is_empty() && ma1_value > ma2_value && ma2[idx2] > ma2[idx1] {
        let ma2_round_high = if upper_prices.len() > n {
            upper_prices[n]
        } else {
            *upper_prices.last().unwrap()
        };
        if bar1.low < ma2_round_high && ma2_round_high < bar2.high && bar2.close < ma2_round_high {
            v1 = "买点";
        }
    } else if !lower_prices.is_empty() && ma1_value < ma2_value && ma2[idx2] < ma2[idx1] {
        let ma2_round_low = if lower_prices.len() > n {
            lower_prices[lower_prices.len() - n]
        } else {
            lower_prices[0]
        };
        if bar1.high > ma2_round_low && ma2_round_low > bar2.low && bar2.close > ma2_round_low {
            v1 = "卖点";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bc_V230803：双分型 MACD 背驰信号
///
/// 参数模板：`"{freq}_MACD双分型背驰_BS辅助V230803"`
///
/// 信号逻辑：
/// 1. 提取最近分型列表中的同类顶/底分型；
/// 2. 对比两个分型中间K线的 MACD 柱值；
/// 3. 向上笔出现 `macd1 > macd2 > 0` 判 `空头`，向下笔镜像判 `多头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_MACD双分型背驰_BS辅助V230803_空头_任意_任意_0')`
/// - `Signal('60分钟_MACD双分型背驰_BS辅助V230803_多头_任意_任意_0')`
///
/// 参数说明：
/// - 无额外参数。
/// 对齐说明：分型来源改为 `get_fx_list()`，与 Python `c.fx_list` 语义对齐。
#[signal(
    category = "kline",
    name = "tas_macd_bc_V230803",
    template = "{freq}_MACD双分型背驰_BS辅助V230803",
    opcode = "TasMacdBcV230803",
    param_kind = "TasMacdBcV230803"
)]
pub fn tas_macd_bc_v230803(czsc: &CZSC, _params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let k1 = czsc.freq.to_string();
    let k2 = "MACD双分型背驰";
    let k3 = "BS辅助V230803";
    let mut v1 = "其他";

    if czsc.bi_list.len() < 3 || czsc.bars_ubi.len() >= 7 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    let mc = cache.macd.get(cache_key).unwrap();
    let bar_idx: HashMap<i32, usize> = czsc
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();
    let get_macd = |bar_id: i32| -> Option<f64> { bar_idx.get(&bar_id).map(|i| mc.macd[*i]) };

    let fx_list = czsc.get_fx_list();
    let b1 = czsc.bi_list.last().unwrap();
    if b1.direction == Direction::Up {
        let tops: Vec<_> = fx_list
            .iter()
            .rev()
            .take(10)
            .filter(|fx| fx.mark == Mark::G)
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect();
        if tops.len() >= 2 {
            let fx1 = tops[tops.len() - 2];
            let fx2 = tops[tops.len() - 1];
            let id1 = fx1
                .elements
                .iter()
                .flat_map(|nb| nb.elements.iter())
                .nth(1)
                .map(|x| x.id);
            let id2 = fx2
                .elements
                .iter()
                .flat_map(|nb| nb.elements.iter())
                .nth(1)
                .map(|x| x.id);
            if let (Some(i1), Some(i2)) = (id1, id2)
                && let (Some(macd1), Some(macd2)) = (get_macd(i1), get_macd(i2))
                    && macd1 > macd2 && macd2 > 0.0 {
                        v1 = "空头";
                    }
        }
    } else {
        let bottoms: Vec<_> = fx_list
            .iter()
            .rev()
            .take(10)
            .filter(|fx| fx.mark == Mark::D)
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect();
        if bottoms.len() >= 2 {
            let fx1 = bottoms[bottoms.len() - 2];
            let fx2 = bottoms[bottoms.len() - 1];
            let id1 = fx1
                .elements
                .iter()
                .flat_map(|nb| nb.elements.iter())
                .nth(1)
                .map(|x| x.id);
            let id2 = fx2
                .elements
                .iter()
                .flat_map(|nb| nb.elements.iter())
                .nth(1)
                .map(|x| x.id);
            if let (Some(i1), Some(i2)) = (id1, id2)
                && let (Some(macd1), Some(macd2)) = (get_macd(i1), get_macd(i2))
                    && macd1 < macd2 && macd2 < 0.0 {
                        v1 = "多头";
                    }
        }
    }

    make_kline_signal_v1(&k1, k2, k3, v1)
}

/// tas_macd_bc_V240307：MACD 柱背驰计次信号
///
/// 参数模板：`"{freq}_D{di}N{n}柱子背驰_BS辅助V240307"`
///
/// 信号逻辑：
/// 1. 在窗口内识别 MACD 柱局部顶/底；
/// 2. 顶部减弱并满足间隔条件判 `顶背驰`，底部抬高镜像判 `底背驰`；
/// 3. 输出距离最近顶/底的计次数 `第k次`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N20柱子背驰_BS辅助V240307_顶背驰_第2次_任意_0')`
/// - `Signal('60分钟_D1N20柱子背驰_BS辅助V240307_底背驰_第1次_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：观察窗口，默认 `20`。
/// 对齐说明：峰谷识别、间隔阈值与统计口径对齐 Python `tas_macd_bc_V240307`。
#[signal(
    category = "kline",
    name = "tas_macd_bc_V240307",
    template = "{freq}_D{di}N{n}柱子背驰_BS辅助V240307",
    opcode = "TasMacdBcV240307",
    param_kind = "TasMacdBcV240307"
)]
pub fn tas_macd_bc_v240307(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 20);
    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}柱子背驰", di, n);
    let k3 = "BS辅助V240307";
    let mut v1 = "其他";
    let mut v2 = "其他".to_string();

    if czsc.bars_raw.len() < 7 + n || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, &v2);
    }
    let bars = get_sub_elements(&czsc.bars_raw, di, n);
    let mc = cache.macd.get(cache_key).unwrap();
    let end = czsc.bars_raw.len() - di + 1;
    let start = end - bars.len();
    let macd: Vec<f64> = (start..end).map(|i| mc.macd[i]).collect();
    let m_len = macd.len();

    let gs: Vec<usize> = (1..m_len.saturating_sub(1))
        .filter(|&i| macd[i - 1] < macd[i] && macd[i] > macd[i + 1] && macd[i] > 0.0)
        .collect();
    let ds: Vec<usize> = (1..m_len.saturating_sub(1))
        .filter(|&i| macd[i - 1] > macd[i] && macd[i] < macd[i + 1] && macd[i] < 0.0)
        .collect();

    if macd.last().copied().unwrap_or(0.0) > 0.0
        && gs.len() >= 2
        && macd[*gs.last().unwrap()] < macd[gs[gs.len() - 2]]
        && gs[gs.len() - 1] - gs[gs.len() - 2] > 2
    {
        let macd_sub = &macd[gs[gs.len() - 2]..];
        let neg_sum: f64 = macd_sub.iter().filter(|x| **x < 0.0).sum::<f64>().abs();
        let std_abs = std_abs_series(macd_sub);
        if neg_sum < std_abs {
            v1 = "顶背驰";
            v2 = format!("第{}次", m_len - gs[gs.len() - 1] - 1);
        }
    }
    if macd.last().copied().unwrap_or(0.0) < 0.0
        && ds.len() >= 2
        && macd[*ds.last().unwrap()] > macd[ds[ds.len() - 2]]
        && ds[ds.len() - 1] - ds[ds.len() - 2] > 2
    {
        let macd_sub = &macd[ds[ds.len() - 2]..];
        let pos_sum: f64 = macd_sub.iter().filter(|x| **x > 0.0).sum::<f64>().abs();
        let std_abs = std_abs_series(macd_sub);
        if pos_sum < std_abs {
            v1 = "底背驰";
            v2 = format!("第{}次", m_len - ds[ds.len() - 1] - 1);
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}

/// tas_macd_dist_V230408：DIF/DEA/MACD等宽分层信号
///
/// 参数模板：`"{freq}_{key}分层W{w}N{n}_BS辅助V230408"`
///
/// 信号逻辑：
/// 1. 获取最近 `w` 根K线的 `DIF/DEA/MACD` 序列；
/// 2. 按等宽区间切分为 `n` 层；
/// 3. 返回最后一个值所在层级 `第{q}层`。
///
/// 信号列表示例：
/// - `Signal('60分钟_DIF分层W100N10_BS辅助V230408_第3层_任意_任意_0')`
/// - `Signal('60分钟_MACD分层W100N10_BS辅助V230408_第8层_任意_任意_0')`
///
/// 参数说明：
/// - `key`：`DIF/DEA/MACD`，默认 `DIF`；
/// - `w`：窗口长度，默认 `100`；
/// - `n`：分层数量，默认 `10`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_dist_V230408",
    template = "{freq}_{key}分层W{w}N{n}_BS辅助V230408",
    opcode = "TasMacdDistV230408",
    param_kind = "TasMacdDistV230408"
)]
pub fn tas_macd_dist_v230408(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 10);
    let w = get_usize_param(params, "w", 100);
    let key = get_str_param(params, "key", "dif").to_uppercase();
    let k1 = czsc.freq.to_string();
    let k2 = format!("{}分层W{}N{}", key, w, n);
    let k3 = "BS辅助V230408";
    if !matches!(key.as_str(), "DIF" | "DEA" | "MACD") || czsc.bi_list.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let series = match key.as_str() {
        "DIF" => &mc.dif,
        "DEA" => &mc.dea,
        _ => &mc.macd,
    };
    let factors = get_sub_elements(series, 1, w);
    let v1 = pd_cut_last_label(factors, n)
        .map(|q| format!("第{}层", q))
        .unwrap_or_else(|| "其他".to_string());
    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// tas_macd_dist_V230409：DIF/DEA/MACD远离零轴信号
///
/// 参数模板：`"{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230409"`
///
/// 信号逻辑：
/// 1. 获取最近 `w` 根K线指标值并计算绝对值均值；
/// 2. 若最近 `n` 根中绝对值最大者超过 `mean * t/10`，判定远离零轴；
/// 3. 按最后一个值符号输出 `多头远离/空头远离`。
///
/// 信号列表示例：
/// - `Signal('60分钟_DIF远离W100N10T20_BS辅助V230409_多头远离_任意_任意_0')`
/// - `Signal('60分钟_DIF远离W100N10T20_BS辅助V230409_空头远离_任意_任意_0')`
///
/// 参数说明：
/// - `key`：`DIF/DEA/MACD`，默认 `DIF`；
/// - `w`：窗口长度，默认 `100`；
/// - `n`：最近判定窗口，默认 `10`；
/// - `t`：远离阈值倍率（除以10），默认 `20`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_dist_V230409",
    template = "{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230409",
    opcode = "TasMacdDistV230409",
    param_kind = "TasMacdDistV230409"
)]
pub fn tas_macd_dist_v230409(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 10);
    let w = get_usize_param(params, "w", 100);
    let t = get_usize_param(params, "t", 20) as f64;
    let key = get_str_param(params, "key", "dif").to_uppercase();
    let k1 = czsc.freq.to_string();
    let k2 = format!("{}远离W{}N{}T{}", key, w, n, t as usize);
    let k3 = "BS辅助V230409";
    let mut v1 = "其他".to_string();
    if !matches!(key.as_str(), "DIF" | "DEA" | "MACD") || czsc.bi_list.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, &v1);
    }

    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let series = match key.as_str() {
        "DIF" => &mc.dif,
        "DEA" => &mc.dea,
        _ => &mc.macd,
    };
    let factors = get_sub_elements(series, 1, w);
    if !factors.is_empty() && factors.iter().all(|x| x.is_finite()) {
        let mean_abs = factors.iter().map(|x| x.abs()).sum::<f64>() / factors.len() as f64;
        let recent = get_sub_elements(factors, 1, n);
        let recent_abs_max = recent.iter().map(|x| x.abs()).fold(0.0f64, f64::max);
        if recent_abs_max > mean_abs * t / 10.0 {
            let last = *factors.last().unwrap();
            v1 = if last > 0.0 {
                "多头远离".to_string()
            } else {
                "空头远离".to_string()
            };
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// tas_macd_dist_V230410：DIF/DEA/MACD多空分层信号
///
/// 参数模板：`"{freq}_{key}多空分层W{w}N{n}_BS辅助V230410"`
///
/// 信号逻辑：
/// 1. 取最近 `w` 根指标序列，按最后一值符号判 `多头/空头`；
/// 2. 仅保留同符号样本并等宽分层为 `n` 层；
/// 3. 输出 `多头/空头` 与 `第{q}层`。
///
/// 信号列表示例：
/// - `Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_多头_第2层_任意_0')`
/// - `Signal('60分钟_DIF多空分层W200N5_BS辅助V230410_空头_第4层_任意_0')`
///
/// 参数说明：
/// - `key`：`DIF/DEA/MACD`，默认 `DIF`；
/// - `w`：窗口长度，默认 `200`；
/// - `n`：分层数量，默认 `5`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_dist_V230410",
    template = "{freq}_{key}多空分层W{w}N{n}_BS辅助V230410",
    opcode = "TasMacdDistV230410",
    param_kind = "TasMacdDistV230410"
)]
pub fn tas_macd_dist_v230410(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 5);
    let w = get_usize_param(params, "w", 200);
    let key = get_str_param(params, "key", "dif").to_uppercase();
    let k1 = czsc.freq.to_string();
    let k2 = format!("{}多空分层W{}N{}", key, w, n);
    let k3 = "BS辅助V230410";
    if !matches!(key.as_str(), "DIF" | "DEA" | "MACD") || czsc.bi_list.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let series = match key.as_str() {
        "DIF" => &mc.dif,
        "DEA" => &mc.dea,
        _ => &mc.macd,
    };
    let factors_all = get_sub_elements(series, 1, w);
    if factors_all.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let last = *factors_all.last().unwrap();
    let v1 = if last > 0.0 { "多头" } else { "空头" };
    let factors: Vec<f64> = if v1 == "多头" {
        factors_all.iter().copied().filter(|x| *x > 0.0).collect()
    } else {
        factors_all.iter().copied().filter(|x| *x < 0.0).collect()
    };
    let v2 = pd_cut_last_label(&factors, n)
        .map(|q| format!("第{}层", q))
        .unwrap_or_else(|| "任意".to_string());
    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}

/// tas_macd_first_bs_V221201：MACD一买一卖辅助信号
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221201"`
///
/// 信号逻辑：
/// 1. 在近 300 根内统计 DIF/DEA 金叉死叉序列；
/// 2. 满足特定零轴位置与节奏条件时，给出 `一买` 或 `一卖`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V221201_一买_任意_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V221201_一卖_任意_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V221201_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_first_bs_V221201",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221201",
    opcode = "TasMacdFirstBsV221201",
    param_kind = "TasMacdFirstBsV221201"
)]
pub fn tas_macd_first_bs_v221201(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);

    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    crate::utils::ta::update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );

    let macd_cache = cache.macd.get(&cache_key).unwrap();

    // 对齐 Python: bars = get_sub_elements(c.bars_raw, di=di, n=300)
    // Python 条件: if len(bars) >= 100
    let mut v1 = "其他";
    let bars = get_sub_elements(&czsc.bars_raw, di, 300);
    if bars.len() >= 100 {
        let dif = get_sub_elements(&macd_cache.dif, di, 300);
        let dea = get_sub_elements(&macd_cache.dea, di, 300);
        let macd = get_sub_elements(&macd_cache.macd, di, 300);

        let cross = fast_slow_cross(dif, dea);
        let up: Vec<_> = cross
            .iter()
            .filter(|x| x["类型"] == 1.0 && x["距离"] > 5.0)
            .collect();
        let dn: Vec<_> = cross
            .iter()
            .filter(|x| x["类型"] == -1.0 && x["距离"] > 5.0)
            .collect();

        // 对齐 Python: 各条件独立检查长度
        let b1_con1 = cross.len() > 3
            && cross.last().unwrap()["类型"] == -1.0
            && cross.last().unwrap()["慢线"] < 0.0;
        let b1_con2 =
            dn.len() > 3 && dn[dn.len() - 2]["慢线"] < 0.0 && dn[dn.len() - 3]["慢线"] < 0.0;
        let b1_con3 = macd.len() > 10 && macd[macd.len() - 1] > macd[macd.len() - 2];

        if b1_con1 && b1_con2 && b1_con3 {
            v1 = "一买";
        }

        let s1_con1 = cross.len() > 3
            && cross.last().unwrap()["类型"] == 1.0
            && cross.last().unwrap()["慢线"] > 0.0;
        let s1_con2 =
            up.len() > 3 && up[up.len() - 2]["慢线"] > 0.0 && up[up.len() - 3]["慢线"] > 0.0;
        let s1_con3 = macd.len() > 10 && macd[macd.len() - 1] < macd[macd.len() - 2];

        if s1_con1 && s1_con2 && s1_con3 {
            v1 = "一卖";
        }
    }

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MACD{}#{}#{}", di, fastperiod, slowperiod, signalperiod);
    let k3 = "BS1辅助V221201";

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_first_bs_V221216：MACD 第一买卖点（扩展版）
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221216"`
///
/// 信号逻辑：
/// 1. 以最近 10 根与前 90 根做高低点对比（新高/新低）；
/// 2. 结合最近交叉类型、零轴位置与 MACD 方向判断 `一买/一卖`；
/// 3. `v2` 输出最后一次交叉类型（`金叉/死叉`）。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V221216_一买_死叉_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V221216_一卖_金叉_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。
/// 对齐说明：分支条件、`or` 组合与 `v2` 输出语义对齐 Python `tas_macd_first_bs_V221216`。
#[signal(
    category = "kline",
    name = "tas_macd_first_bs_V221216",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221216",
    opcode = "TasMacdFirstBsV221216",
    param_kind = "TasMacdFirstBsV221216"
)]
pub fn tas_macd_first_bs_v221216(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MACD{}#{}#{}", di, fastperiod, slowperiod, signalperiod);
    let k3 = "BS1辅助V221216";
    let mut v1 = "其他";
    let mut v2 = "任意";

    let bars = get_sub_elements(&czsc.bars_raw, di, 300);
    if bars.len() >= 100 {
        let mc = cache.macd.get(&cache_key).unwrap();
        let dif = get_sub_elements(&mc.dif, di, 300);
        let dea = get_sub_elements(&mc.dea, di, 300);
        let macd = get_sub_elements(&mc.macd, di, 300);
        let n_bars = &bars[bars.len() - 10..];
        let m_bars = &bars[bars.len() - 100..bars.len() - 10];
        let high_n = n_bars
            .iter()
            .map(|x| x.high)
            .fold(f64::NEG_INFINITY, f64::max);
        let low_n = n_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
        let high_m = m_bars
            .iter()
            .map(|x| x.high)
            .fold(f64::NEG_INFINITY, f64::max);
        let low_m = m_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);

        let cross = fast_slow_cross_ext(dif, dea);
        let up: Vec<_> = cross
            .iter()
            .filter(|x| x.kind > 0 && x.distance > 5)
            .collect();
        let dn: Vec<_> = cross
            .iter()
            .filter(|x| x.kind < 0 && x.distance > 5)
            .collect();
        if let Some(last) = cross.last() {
            let b1_con1a = cross.len() > 3 && last.kind < 0 && last.slow < 0.0;
            let b1_con1b =
                cross.len() > 3 && last.kind > 0 && !dn.is_empty() && dn[dn.len() - 1].slow < 0.0;
            let b1_con2 =
                dn.len() > 3 && dn[dn.len() - 2].slow < 0.0 && dn[dn.len() - 3].slow < 0.0;
            let b1_con3 = macd.len() > 10 && macd[macd.len() - 1] > macd[macd.len() - 2];
            if low_n < low_m && (b1_con1a || b1_con1b) && b1_con2 && b1_con3 {
                v1 = "一买";
            }

            let s1_con1a = cross.len() > 3 && last.kind > 0 && last.slow > 0.0;
            let s1_con1b =
                cross.len() > 3 && last.kind < 0 && !up.is_empty() && up[up.len() - 1].slow > 0.0;
            let s1_con2 =
                up.len() > 3 && up[up.len() - 2].slow > 0.0 && up[up.len() - 3].slow > 0.0;
            let s1_con3 = macd.len() > 10 && macd[macd.len() - 1] < macd[macd.len() - 2];
            if high_n > high_m && (s1_con1a || s1_con1b) && s1_con2 && s1_con3 {
                v1 = "一卖";
            }
            v2 = if last.kind > 0 { "金叉" } else { "死叉" };
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_macd_second_bs_V221201：MACD 第二买卖点
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS2辅助V221201"`
///
/// 信号逻辑：
/// 1. 在近 350 根（去掉最早 50 根）统计交叉序列；
/// 2. 结合最近交叉距今、零轴位置与 MACD 方向判 `二买/二卖`；
/// 3. `v2` 返回最后交叉类型。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9_BS2辅助V221201_二买_死叉_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9_BS2辅助V221201_二卖_金叉_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。
/// 对齐说明：`距今` 条件与零轴判定对齐 Python `tas_macd_second_bs_V221201`。
#[signal(
    category = "kline",
    name = "tas_macd_second_bs_V221201",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS2辅助V221201",
    opcode = "TasMacdSecondBsV221201",
    param_kind = "TasMacdSecondBsV221201"
)]
pub fn tas_macd_second_bs_v221201(
    czsc: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MACD{}#{}#{}", di, fastperiod, slowperiod, signalperiod);
    let k3 = "BS2辅助V221201";
    let mut v1 = "其他";
    let mut v2 = "任意";

    let raw = get_sub_elements(&czsc.bars_raw, di, 350);
    let bars: Vec<_> = if raw.len() > 50 {
        raw[50..].to_vec()
    } else {
        Vec::new()
    };
    if bars.len() >= 100 {
        let mc = cache.macd.get(&cache_key).unwrap();
        let end = czsc.bars_raw.len() - di + 1;
        let start = end - get_sub_elements(&czsc.bars_raw, di, 350).len() + 50;
        let dif: Vec<f64> = (0..bars.len()).map(|i| mc.dif[start + i]).collect();
        let dea: Vec<f64> = (0..bars.len()).map(|i| mc.dea[start + i]).collect();
        let macd: Vec<f64> = (0..bars.len()).map(|i| mc.macd[start + i]).collect();

        let cross = fast_slow_cross_ext(&dif, &dea);
        let up: Vec<_> = cross
            .iter()
            .filter(|x| x.kind > 0 && x.distance > 5)
            .collect();
        let dn: Vec<_> = cross
            .iter()
            .filter(|x| x.kind < 0 && x.distance > 5)
            .collect();
        if let Some(last) = cross.last() {
            let b2_con1a = cross.len() > 3 && last.kind < 0 && last.slow > 0.0 && last.to_now > 5;
            let b2_con1b = cross.len() > 3
                && last.kind > 0
                && !dn.is_empty()
                && dn[dn.len() - 1].slow > 0.0
                && last.to_now < 5;
            let b2_con2 =
                dn.len() > 4 && dn[dn.len() - 3].slow < 0.0 && dn[dn.len() - 2].slow < 0.0;
            let b2_con3 = macd.len() > 10 && macd[macd.len() - 1] > macd[macd.len() - 2];
            if (b2_con1a || b2_con1b) && b2_con2 && b2_con3 {
                v1 = "二买";
            }

            let s2_con1a = cross.len() > 3 && last.kind > 0 && last.slow < 0.0 && last.to_now > 5;
            let s2_con1b = cross.len() > 3
                && last.kind < 0
                && !up.is_empty()
                && up[up.len() - 1].slow < 0.0
                && last.to_now < 5;
            let s2_con2 =
                up.len() > 4 && up[up.len() - 3].slow > 0.0 && up[up.len() - 2].slow > 0.0;
            let s2_con3 = macd.len() > 10 && macd[macd.len() - 1] < macd[macd.len() - 2];
            if (s2_con1a || s2_con1b) && s2_con2 && s2_con3 {
                v1 = "二卖";
            }
            v2 = if last.kind > 0 { "金叉" } else { "死叉" };
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_macd_xt_V221208：MACD 柱形态信号
///
/// 参数模板：`"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}形态_BS辅助V221208"`
///
/// 信号逻辑：
/// 1. 读取最近 5 根 MACD 柱；
/// 2. 按柱子相对大小关系判定 `逼空棒/杀多棒/绿抽脚/红缩头`；
/// 3. 按跨零关系判定 `空翻多/多翻空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K#MACD12#26#9形态_BS辅助V221208_逼空棒_任意_任意_0')`
/// - `Signal('60分钟_D1K#MACD12#26#9形态_BS辅助V221208_多翻空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。
/// 对齐说明：形态分支顺序与 Python `tas_macd_xt_V221208` 保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_xt_V221208",
    template = "{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}形态_BS辅助V221208",
    opcode = "TasMacdXtV221208",
    param_kind = "TasMacdXtV221208"
)]
pub fn tas_macd_xt_v221208(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}K#MACD{}#{}#{}形态",
        di, fastperiod, slowperiod, signalperiod
    );
    let k3 = "BS辅助V221208";
    let mut v1 = "其他";

    let mc = cache.macd.get(&cache_key).unwrap();
    let macd = get_sub_elements(&mc.macd, di, 5);
    if macd.len() == 5 {
        let min_m = macd.iter().copied().fold(f64::INFINITY, f64::min);
        let max_m = macd.iter().copied().fold(f64::NEG_INFINITY, f64::max);
        if min_m > 0.0 && macd[4] > macd[3] && macd[3] < macd[1] {
            v1 = "逼空棒";
        } else if max_m < 0.0 && macd[4] < macd[3] && macd[3] > macd[1] {
            v1 = "杀多棒";
        } else if max_m < 0.0 && macd[4] > macd[3] && macd[3] < macd[1] {
            v1 = "绿抽脚";
        } else if min_m > 0.0 && macd[4] < macd[3] && macd[3] > macd[1] {
            v1 = "红缩头";
        } else if macd[4] > 0.0 && macd[2] < 0.0 {
            v1 = "空翻多";
        } else if macd[2] > 0.0 && macd[4] < 0.0 {
            v1 = "多翻空";
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bs1_V230312：MACD 辅助一买一卖（笔结构）
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230312"`
///
/// 信号逻辑：
/// 1. 最近 7 笔内，末笔创新低并满足三卖结构且末分型 MACD 抬升，判 `看多`；
/// 2. 镜像条件（创新高 + 三买结构 + MACD 走弱）判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V230312_看多_任意_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V230312_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 笔，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。
/// 对齐说明：笔结构约束与末分型 MACD 比较逻辑对齐 Python `tas_macd_bs1_V230312`。
#[signal(
    category = "kline",
    name = "tas_macd_bs1_V230312",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230312",
    opcode = "TasMacdBs1V230312",
    param_kind = "TasMacdBs1V230312"
)]
pub fn tas_macd_bs1_v230312(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MACD{}#{}#{}", di, fastperiod, slowperiod, signalperiod);
    let k3 = "BS1辅助V230312";
    let mut v1 = "其他";

    let bis = get_sub_elements(&czsc.bi_list, di, 7);
    if bis.len() >= 7 {
        let mc = cache.macd.get(&cache_key).unwrap();
        let id_to_idx = bar_index_map(czsc);
        let mut snapshot_overrides: HashMap<i32, (f64, f64, f64)> = HashMap::new();
        let last_bi = &bis[bis.len() - 1];
        let last_fx = &last_bi.fx_b;
        let last_raw: Vec<_> = last_fx
            .elements
            .iter()
            .flat_map(|nb| nb.elements.iter())
            .collect();
        if !last_raw.is_empty() {
            let first_macd = macd_snapshot_field_value(
                czsc,
                mc,
                &id_to_idx,
                last_raw.first().unwrap(),
                fastperiod,
                slowperiod,
                signalperiod,
                MacdField::Macd,
                &mut snapshot_overrides,
            )
            .unwrap_or(f64::NAN);
            let last_macd = macd_snapshot_field_value(
                czsc,
                mc,
                &id_to_idx,
                last_raw.last().unwrap(),
                fastperiod,
                slowperiod,
                signalperiod,
                MacdField::Macd,
                &mut snapshot_overrides,
            )
            .unwrap_or(f64::NAN);

            let up_lows: Vec<f64> = bis[..bis.len() - 1]
                .iter()
                .filter(|x| x.direction == Direction::Up)
                .map(|x| x.get_low())
                .collect();
            let down_highs: Vec<f64> = bis[..bis.len() - 1]
                .iter()
                .filter(|x| x.direction == Direction::Down)
                .map(|x| x.get_high())
                .collect();
            let min_low = bis
                .iter()
                .map(|x| x.get_low())
                .fold(f64::INFINITY, f64::min);
            let max_high = bis
                .iter()
                .map(|x| x.get_high())
                .fold(f64::NEG_INFINITY, f64::max);
            if !up_lows.is_empty()
                && last_bi.direction == Direction::Down
                && last_bi.get_low() == min_low
                && last_bi.get_high() < up_lows.iter().copied().fold(f64::NEG_INFINITY, f64::max)
                && last_macd > first_macd
            {
                v1 = "看多";
            }
            if !down_highs.is_empty()
                && last_bi.direction == Direction::Up
                && last_bi.get_high() == max_high
                && last_bi.get_low() > down_highs.iter().copied().fold(f64::INFINITY, f64::min)
                && last_macd < first_macd
            {
                v1 = "看空";
            }
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bs1_V230313：MACD 红绿柱第一买卖点
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230313"`
///
/// 信号逻辑：
/// 1. 近 10 与前 90 根对比新高新低；
/// 2. 用交叉面积递减/递增与 MACD 方向判 `一买/一卖`；
/// 3. `v2` 返回最后交叉类型。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V230313_一买_死叉_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9_BS1辅助V230313_一卖_金叉_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。
/// 对齐说明：面积比较与条件优先级（`and/or`）按 Python `tas_macd_bs1_V230313` 对齐。
#[signal(
    category = "kline",
    name = "tas_macd_bs1_V230313",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230313",
    opcode = "TasMacdBs1V230313",
    param_kind = "TasMacdBs1V230313"
)]
pub fn tas_macd_bs1_v230313(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(
        czsc,
        &cache_key,
        fastperiod,
        slowperiod,
        signalperiod,
        cache,
    );
    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MACD{}#{}#{}", di, fastperiod, slowperiod, signalperiod);
    let k3 = "BS1辅助V230313";
    let mut v1 = "其他";
    let mut v2 = "任意";

    let bars = get_sub_elements(&czsc.bars_raw, di, 300);
    if bars.len() > 100 {
        let mc = cache.macd.get(&cache_key).unwrap();
        let dif = get_sub_elements(&mc.dif, di, 300);
        let dea = get_sub_elements(&mc.dea, di, 300);
        let macd = get_sub_elements(&mc.macd, di, 300);

        let n_bars = &bars[bars.len() - 10..];
        let m_bars = &bars[bars.len() - 100..bars.len() - 10];
        let high_n = n_bars
            .iter()
            .map(|x| x.high)
            .fold(f64::NEG_INFINITY, f64::max);
        let low_n = n_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
        let high_m = m_bars
            .iter()
            .map(|x| x.high)
            .fold(f64::NEG_INFINITY, f64::max);
        let low_m = m_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);

        let cross = fast_slow_cross_ext(dif, dea);
        let up: Vec<_> = cross.iter().filter(|x| x.kind > 0).collect();
        let dn: Vec<_> = cross.iter().filter(|x| x.kind < 0).collect();
        if cross.len() >= 3 {
            let last = cross.last().unwrap();
            let c2 = &cross[cross.len() - 2];
            let c3 = &cross[cross.len() - 3];
            let b1_con1a = (cross.len() > 3 && last.kind < 0 && last.area < c2.area)
                || (cross.len() > 3 && last.area < c3.area);
            let b1_con1b = (cross.len() > 3 && last.kind > 0 && last.area > c2.area)
                || (cross.len() > 3 && last.area < c3.area);
            let b1_con2 = dn.len() > 3 && dn[dn.len() - 2].area < dn[dn.len() - 3].area;
            let b1_con3 = macd.len() > 10 && macd[macd.len() - 1] > macd[macd.len() - 2];
            if low_n < low_m && (b1_con1a || b1_con1b) && b1_con2 && b1_con3 {
                v1 = "一买";
            }

            let s1_con1a = (cross.len() > 3 && last.kind > 0 && last.area > c2.area)
                || (cross.len() > 3 && last.area > c3.area);
            let s1_con1b = (cross.len() > 3 && last.kind < 0 && last.area < c2.area)
                || (cross.len() > 3 && last.area < c3.area);
            let s1_con2 = up.len() > 3 && up[up.len() - 2].area > up[up.len() - 3].area;
            let s1_con3 = macd.len() > 10 && macd[macd.len() - 1] < macd[macd.len() - 2];
            if high_n > high_m && (s1_con1a || s1_con1b) && s1_con2 && s1_con3 {
                v1 = "一卖";
            }
            v2 = if last.kind > 0 { "金叉" } else { "死叉" };
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_boll_power_V221112：BOLL强弱分层信号
///
/// 参数模板：`"{freq}_D{di}BOLL{timeperiod}_强弱V221112"`
///
/// 信号逻辑：
/// 1. 计算 BOLL 中线与标准差；
/// 2. 先以 `close` 相对中线判断 `多头/空头`；
/// 3. 再按偏离程度分层 `弱势/强势/超强/极强`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1BOLL20_强弱V221112_多头_强势_任意_0')`
/// - `Signal('60分钟_D1BOLL20_强弱V221112_空头_超强_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：BOLL周期，默认 `20`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_boll_power_V221112",
    template = "{freq}_D{di}BOLL{timeperiod}_强弱V221112",
    opcode = "TasBollPowerV221112",
    param_kind = "TasBollPowerV221112"
)]
pub fn tas_boll_power_v221112(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 20);

    // Python 使用 dev_seq = (1.382, 2, 2.764) 计算 BOLL 上下轨
    // 我们需要用 2 倍标准差的缓存来推导 std_dev，然后乘以正确的系数
    let cache_key = format!("BOLL{}#2.0", timeperiod);
    update_boll_cache(czsc, &cache_key, timeperiod, 2.0, cache);

    let boll_cache = cache.boll.get(&cache_key).unwrap();
    let bars = &czsc.bars_raw;
    let mut v1 = "其他";
    let mut v2 = "其他";

    if bars.len() >= di + 20 {
        let latest = get_sub_elements(bars, di, 1);
        if !latest.is_empty() {
            let idx = bars.len() - di;
            let latest_c = latest[0].close;
            let m = boll_cache.mid[idx];
            // upper = mid + 2*std_dev → std_dev = (upper - mid) / 2.0
            let std_dev = (boll_cache.upper[idx] - m) / 2.0;

            // 对齐 Python: dev_seq = (1.382, 2, 2.764)
            let u1 = m + 1.382 * std_dev;
            let u2 = m + 2.0 * std_dev;
            let u3 = m + 2.764 * std_dev;

            let l1 = m - 1.382 * std_dev;
            let l2 = m - 2.0 * std_dev;
            let l3 = m - 2.764 * std_dev;

            v1 = if latest_c >= m { "多头" } else { "空头" };
            v2 = if latest_c >= u3 || latest_c <= l3 {
                "极强"
            } else if latest_c >= u2 || latest_c <= l2 {
                "超强"
            } else if latest_c >= u1 || latest_c <= l1 {
                "强势"
            } else {
                "弱势"
            };
        }
    }

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}BOLL{}", di, timeperiod);
    let k3 = "强弱V221112";

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_boll_bc_V221118：BOLL背驰辅助信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}L{line}#BOLL{timeperiod}_背驰V221118"`
///
/// 信号逻辑：
/// 1. 对比近端 `n` 根与参考段 `m` 根的价格极值；
/// 2. 结合 BOLL 指定轨道 `line` 的上下突破次数；
/// 3. 满足低点背驰给 `一买`，满足高点背驰给 `一卖`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N3M10L3#BOLL20_背驰V221118_一买_任意_任意_0')`
/// - `Signal('60分钟_D1N3M10L3#BOLL20_背驰V221118_一卖_任意_任意_0')`
/// - `Signal('60分钟_D1N3M10L3#BOLL20_背驰V221118_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n/m`：近端与参考窗口长度，默认 `3/10`；
/// - `line`：轨道层级，默认 `3`；
/// - `timeperiod`：BOLL周期，默认 `20`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_boll_bc_V221118",
    template = "{freq}_D{di}N{n}M{m}L{line}#BOLL{timeperiod}_背驰V221118",
    opcode = "TasBollBcV221118",
    param_kind = "TasBollBcV221118"
)]
pub fn tas_boll_bc_v221118(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 3);
    let m = get_usize_param(params, "m", 10);
    let line = get_usize_param(params, "line", 3);
    let timeperiod = get_usize_param(params, "timeperiod", 20);

    let cache_key = format!("BOLL{}#2.0", timeperiod);
    update_boll_cache(czsc, &cache_key, timeperiod, 2.0, cache);

    let boll_cache = cache.boll.get(&cache_key).unwrap();
    let bn_bars = get_sub_elements(&czsc.bars_raw, di, n);
    let bm_bars = get_sub_elements(&czsc.bars_raw, di, m);
    let mut v1 = "其他";

    let dev = match line {
        1 => 1.382,
        2 => 2.0,
        3 => 2.764,
        _ => line as f64,
    };
    let get_line_val = |idx: usize, is_upper: bool| -> f64 {
        let mid = boll_cache.mid[idx];
        let std_dev = (boll_cache.upper[idx] - mid) / 2.0;
        if is_upper {
            mid + dev * std_dev
        } else {
            mid - dev * std_dev
        }
    };

    if !bn_bars.is_empty() && !bm_bars.is_empty() && czsc.bars_raw.len() >= di {
        let min_low_n = bn_bars.iter().map(|b| b.low).fold(f64::INFINITY, f64::min);
        let min_low_m = bm_bars.iter().map(|b| b.low).fold(f64::INFINITY, f64::min);

        let total_len = czsc.bars_raw.len();
        let bm_start_idx = total_len - di + 1 - bm_bars.len();
        let bn_start_idx = total_len - di + 1 - bn_bars.len();

        let mut d_c2_count = 0;
        for (offset, bar) in bm_bars.iter().enumerate() {
            let idx = bm_start_idx + offset;
            if bar.close < get_line_val(idx, false) {
                d_c2_count += 1;
            }
        }
        let mut d_c3_count = 0;
        for (offset, bar) in bn_bars.iter().enumerate() {
            let idx = bn_start_idx + offset;
            if bar.close < get_line_val(idx, false) {
                d_c3_count += 1;
            }
        }

        let d_c1 = min_low_n <= min_low_m;
        let d_c2 = d_c2_count > 1;
        let d_c3 = d_c3_count == 0;

        let max_high_n = bn_bars
            .iter()
            .map(|b| b.high)
            .fold(f64::NEG_INFINITY, f64::max);
        let max_high_m = bm_bars
            .iter()
            .map(|b| b.high)
            .fold(f64::NEG_INFINITY, f64::max);

        let mut g_c2_count = 0;
        for (offset, bar) in bm_bars.iter().enumerate() {
            let idx = bm_start_idx + offset;
            if bar.close > get_line_val(idx, true) {
                g_c2_count += 1;
            }
        }
        let mut g_c3_count = 0;
        for (offset, bar) in bn_bars.iter().enumerate() {
            let idx = bn_start_idx + offset;
            if bar.close > get_line_val(idx, true) {
                g_c3_count += 1;
            }
        }

        let g_c1 = max_high_n == max_high_m;
        let g_c2 = g_c2_count > 1;
        let g_c3 = g_c3_count == 0;

        v1 = if d_c1 && d_c2 && d_c3 {
            "一买"
        } else if g_c1 && g_c2 && g_c3 {
            "一卖"
        } else {
            "其他"
        };
    }

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}N{}M{}L{}#BOLL{}", di, n, m, line, timeperiod);
    let k3 = "背驰V221118";

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_kdj_base_V221101：KDJ基础辅助信号
///
/// 参数模板：`"{freq}_D{di}K#KDJ{fastk_period}#{slowk_period}#{slowd_period}_KDJ辅助V221101"`
///
/// 信号逻辑：
/// 1. 计算 K、D、J 三序列；
/// 2. `J > K > D` 判定 `多头`，`J < K < D` 判定 `空头`，否则 `其他`；
/// 3. `J_now >= J_prev` 判定 `向上`，否则 `向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K#KDJ9#3#3_KDJ辅助V221101_多头_向上_任意_0')`
/// - `Signal('60分钟_D1K#KDJ9#3#3_KDJ辅助V221101_空头_向下_任意_0')`
/// - `Signal('60分钟_D1K#KDJ9#3#3_KDJ辅助V221101_其他_向下_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `fastk_period/slowk_period/slowd_period`：KDJ参数，默认 `9/3/3`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_kdj_base_V221101",
    template = "{freq}_D{di}K#KDJ{fastk_period}#{slowk_period}#{slowd_period}_KDJ辅助V221101",
    opcode = "TasKdjBaseV221101",
    param_kind = "TasKdjBaseV221101"
)]
pub fn tas_kdj_base_v221101(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let fastk_period = get_usize_param(params, "fastk_period", 9);
    let slowk_period = get_usize_param(params, "slowk_period", 3);
    let slowd_period = get_usize_param(params, "slowd_period", 3);

    let cache_key = format!("KDJ{}#{}#{}", fastk_period, slowk_period, slowd_period);
    crate::utils::ta::update_kdj_cache(
        czsc,
        &cache_key,
        fastk_period,
        slowk_period,
        slowd_period,
        cache,
    );

    let kdj_cache = cache.kdj.get(&cache_key).unwrap();

    let k = get_sub_elements(&kdj_cache.k, di, 3);
    let d = get_sub_elements(&kdj_cache.d, di, 3);
    let j = get_sub_elements(&kdj_cache.j, di, 3);
    if k.len() < 2 || d.len() < 2 || j.len() < 2 {
        return Vec::new();
    }

    let k_last = *k.last().unwrap();
    let d_last = *d.last().unwrap();
    let j_last = *j.last().unwrap();
    let j_prev = j[j.len() - 2];

    let v1 = if j_last > k_last && k_last > d_last {
        "多头"
    } else if j_last < k_last && k_last < d_last {
        "空头"
    } else {
        "其他"
    };

    let v2 = if j_last >= j_prev { "向上" } else { "向下" };

    let k1 = czsc.freq.to_string();
    let k2 = format!(
        "D{}K#KDJ{}#{}#{}",
        di, fastk_period, slowk_period, slowd_period
    );
    let k3 = "KDJ辅助V221101";

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_rsi_base_V230227：RSI超买超卖与方向信号
///
/// 参数模板：`"{freq}_D{di}T{th}RSI{timeperiod}_RSI辅助V230227"`
///
/// 信号逻辑：
/// 1. 使用 `n` 计算 RSI（与 Python 保持一致）；
/// 2. `rsi <= th` 判 `超卖`，`rsi >= 100-th` 判 `超买`，否则 `其他`；
/// 3. `rsi_now >= rsi_prev` 判 `向上`，否则 `向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T20RSI6_RSI辅助V230227_超卖_向上_任意_0')`
/// - `Signal('60分钟_D1T20RSI6_RSI辅助V230227_超买_向下_任意_0')`
/// - `Signal('60分钟_D1T20RSI6_RSI辅助V230227_其他_向上_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：RSI 实际计算周期，默认 `6`；
/// - `timeperiod`：仅用于信号键展示，默认 `6`；
/// - `th`：超买超卖阈值，默认 `20`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_rsi_base_V230227",
    template = "{freq}_D{di}T{th}RSI{timeperiod}_RSI辅助V230227",
    opcode = "TasRsiBaseV230227",
    param_kind = "TasRsiBaseV230227"
)]
pub fn tas_rsi_base_v230227(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    // 对齐 Python: n 用于实际 RSI 计算，timeperiod 仅用于信号 key
    let n = get_usize_param(params, "n", 6);
    let timeperiod = get_usize_param(params, "timeperiod", 6);
    let th = get_usize_param(params, "th", 20);

    // 实际 RSI 计算用 n
    let cache_key = format!("RSI{}", n);
    crate::utils::ta::update_rsi_cache(czsc, &cache_key, n, cache);

    let series = cache.series.get(&cache_key).unwrap();
    let sub = get_sub_elements(series, di, 2);
    if sub.len() < 2 {
        return Vec::new();
    }

    let rsi_prev = sub[sub.len() - 2];
    let rsi = sub[sub.len() - 1];

    let v1 = if rsi <= th as f64 {
        "超卖"
    } else if rsi >= 100.0 - th as f64 {
        "超买"
    } else {
        "其他"
    };

    // 与 Python 保持一致：方向比较不加额外浮点容差
    let v2 = if rsi >= rsi_prev { "向上" } else { "向下" };

    let k1 = czsc.freq.to_string();
    // 信号 key 用 timeperiod（对齐 Python 标签行为）
    let k2 = format!("D{}T{}RSI{}", di, th, timeperiod);
    let k3 = "RSI辅助V230227";
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_double_ma_V221203：双均线多空强弱信号
///
/// 参数模板：`"{freq}_D{di}T{th}#{ma_type}#{timeperiod1}#{timeperiod2}_JX辅助V221203"`
///
/// 信号逻辑：
/// 1. 计算两条均线 `ma1/ma2`；
/// 2. `ma1 >= ma2` 判定 `多头`，否则 `空头`；
/// 3. 两线相对距离（BP）超过 `th` 判 `强势`，否则 `弱势`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T100#SMA#5#10_JX辅助V221203_多头_强势_任意_0')`
/// - `Signal('60分钟_D1T80#EMA#12#26_JX辅助V221203_空头_弱势_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `th`：强弱阈值（BP），默认 `100`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod1/timeperiod2`：两条均线周期，默认 `5/10`。
/// 对齐说明：与 Python 同名函数逻辑与边界条件保持一致。
#[signal(
    category = "kline",
    name = "tas_double_ma_V221203",
    template = "{freq}_D{di}T{th}#{ma_type}#{timeperiod1}#{timeperiod2}_JX辅助V221203",
    opcode = "TasDoubleMaV221203",
    param_kind = "TasDoubleMaV221203"
)]
pub fn tas_double_ma_v221203(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 100);
    let ma_type = get_str_param(params, "ma_type", "SMA");
    let timeperiod1 = get_usize_param(params, "timeperiod1", 5);
    let timeperiod2 = get_usize_param(params, "timeperiod2", 10);

    let cache_key1 = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod1);
    let cache_key2 = format!("{}_{}_{}", czsc.freq, ma_type, timeperiod2);

    crate::utils::ta::update_ma_cache(czsc, &cache_key1, ma_type, timeperiod1, cache);
    crate::utils::ta::update_ma_cache(czsc, &cache_key2, ma_type, timeperiod2, cache);

    let ma1_series = cache.series.get(&cache_key1).unwrap();
    let ma2_series = cache.series.get(&cache_key2).unwrap();

    let ma1_sub = get_sub_elements(ma1_series, di, 1);
    let ma2_sub = get_sub_elements(ma2_series, di, 1);
    if ma1_sub.is_empty() || ma2_sub.is_empty() {
        return Vec::new();
    }

    let ma1v = ma1_sub[ma1_sub.len() - 1];
    let ma2v = ma2_sub[ma2_sub.len() - 1];

    let v1 = if ma1v >= ma2v { "多头" } else { "空头" };
    let v2 = if (ma1v - ma2v).abs() / ma2v * 10000.0 >= th as f64 {
        "强势"
    } else {
        "弱势"
    };

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}T{}#{}#{}#{}", di, th, ma_type, timeperiod1, timeperiod2);
    let k3 = "JX辅助V221203";

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// tas_sar_base_V230425：SAR 基础多空信号
///
/// 参数模板：`"{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425"`
///
/// 信号逻辑：
/// 1. 计算 SAR 序列；
/// 2. 若当前 `close > sar` 且窗口内存在任意 `close < sar`，判定 `看多`；
/// 3. 若当前 `close < sar` 且窗口内存在任意 `close > sar`，判定 `看空`；
/// 4. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MO5SAR_BS辅助V230425_看多_任意_任意_0')`
/// - `Signal('60分钟_D1MO5SAR_BS辅助V230425_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `max_overlap`：重叠窗口，默认 `5`。
/// 对齐说明：突破与重叠窗口判定逻辑对齐 Python `tas_sar_base_V230425`。
#[signal(
    category = "kline",
    name = "tas_sar_base_V230425",
    template = "{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425",
    opcode = "TasSarBaseV230425",
    param_kind = "TasSarBaseV230425"
)]
pub fn tas_sar_base_v230425(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let max_overlap = get_usize_param(params, "max_overlap", 5);
    let cache_key = "SAR";
    update_sar_cache(czsc, cache_key, cache);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MO{}SAR", di, max_overlap);
    let k3 = "BS辅助V230425";
    let mut v1 = "其他";

    if czsc.bars_raw.len() < 3 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let sar = cache.series.get(cache_key).unwrap();
    let id_to_idx = bar_index_map(czsc);
    let bars = get_sub_elements(&czsc.bars_raw, di, max_overlap);
    let bar = &czsc.bars_raw[czsc.bars_raw.len() - di];
    let idx = czsc.bars_raw.len() - di;
    let bar_sar = sar[idx];
    if bar_sar.is_finite() {
        if bar.close > bar_sar
            && bars.iter().any(|x| {
                id_to_idx
                    .get(&x.id)
                    .map(|i| sar[*i].is_finite() && x.close < sar[*i])
                    .unwrap_or(false)
            })
        {
            v1 = "看多";
        } else if bar.close < bar_sar
            && bars.iter().any(|x| {
                id_to_idx
                    .get(&x.id)
                    .map(|i| sar[*i].is_finite() && x.close > sar[*i])
                    .unwrap_or(false)
            })
        {
            v1 = "看空";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bs1_V230411：MACD DIF 五笔背驰信号
///
/// 参数模板：`"{freq}_D{di}T{tha}#{thb}#{thc}_BS1辅助V230411"`
///
/// 信号逻辑：
/// 1. 取最近 5 笔并要求当前未完成笔长度约束；
/// 2. 上笔场景：涨幅、DIF 结构、末笔涨幅与 DIF 衰减同时满足，判定 `顶背驰`；
/// 3. 下笔场景镜像：跌幅、DIF 结构与 DIF 回升满足，判定 `底背驰`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T30#5#30_BS1辅助V230411_顶背驰_任意_任意_0')`
/// - `Signal('60分钟_D1T30#5#30_BS1辅助V230411_底背驰_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 笔，默认 `1`；
/// - `tha`：前三笔累计涨跌阈值（BP），默认 `30`；
/// - `thb`：第5笔相对第3笔价格阈值（BP），默认 `5`；
/// - `thc`：第5笔相对第3笔 DIF 变化阈值（BP），默认 `30`。
/// 对齐说明：五笔条件组合与 Python `tas_macd_bs1_V230411` 一致。
#[signal(
    category = "kline",
    name = "tas_macd_bs1_V230411",
    template = "{freq}_D{di}T{tha}#{thb}#{thc}_BS1辅助V230411",
    opcode = "TasMacdBs1V230411",
    param_kind = "TasMacdBs1V230411"
)]
pub fn tas_macd_bs1_v230411(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let tha = get_usize_param(params, "tha", 30) as f64;
    let thb = get_usize_param(params, "thb", 5) as f64;
    let thc = get_usize_param(params, "thc", 30) as f64;
    assert!(tha > 0.0 && tha < 10000.0);
    assert!(thb > 0.0 && thb < 10000.0);
    assert!(thc > 0.0 && thc < 10000.0);

    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let dif = &mc.dif;
    let id_to_idx = bar_index_map(czsc);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}T{}#{}#{}", di, tha as usize, thb as usize, thc as usize);
    let k3 = "BS1辅助V230411";
    let mut v1 = "其他";

    if czsc.bi_list.len() <= di + 7 || czsc.bars_ubi.len() > 9 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let bis = get_sub_elements(&czsc.bi_list, di, 5);
    if bis.len() < 5 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bi1 = &bis[0];
    let bi3 = &bis[2];
    let bi5 = &bis[4];

    let bi1_raw = bi1.get_raw_bars();
    if bi1_raw.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let first_dif = id_to_idx
        .get(&bi1_raw[0].id)
        .map(|i| dif[*i])
        .unwrap_or(f64::NAN);
    if first_dif.is_nan() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    if bi5.direction == Direction::Up {
        let bi1_dif = values_from_fx(&bi1.fx_b, &id_to_idx, dif)
            .into_iter()
            .fold(f64::NEG_INFINITY, f64::max);
        let bi3_dif = values_from_fx(&bi3.fx_b, &id_to_idx, dif)
            .into_iter()
            .fold(f64::NEG_INFINITY, f64::max);
        let bi5_dif = values_from_fx(&bi5.fx_b, &id_to_idx, dif)
            .into_iter()
            .fold(f64::NEG_INFINITY, f64::max);
        let cond1 = ((bi3.get_high() - bi1.get_low()) / bi1.get_low()) * 10000.0 > tha;
        let cond2 = bi3_dif > bi1_dif;
        let cond3 = ((bi5.get_high() - bi3.get_high()) / bi3.get_high()) * 10000.0 > -thb;
        let cond4 = ((bi5_dif - bi3_dif) / bi3_dif) * 10000.0 < -thc;
        if cond1 && cond2 && cond3 && cond4 {
            v1 = "顶背驰";
        }
    } else if bi5.direction == Direction::Down {
        let bi1_dif = values_from_fx(&bi1.fx_b, &id_to_idx, dif)
            .into_iter()
            .fold(f64::INFINITY, f64::min);
        let bi3_dif = values_from_fx(&bi3.fx_b, &id_to_idx, dif)
            .into_iter()
            .fold(f64::INFINITY, f64::min);
        let bi5_dif = values_from_fx(&bi5.fx_b, &id_to_idx, dif)
            .into_iter()
            .fold(f64::INFINITY, f64::min);
        let cond1 = ((bi3.get_low() - bi1.get_high()) / bi1.get_high()) * 10000.0 < -tha;
        let cond2 = bi3_dif < bi1_dif;
        let cond3 = ((bi5.get_low() - bi3.get_low()) / bi3.get_low()) * 10000.0 < thb;
        let cond4 = ((bi5_dif - bi3_dif) / bi3_dif) * 10000.0 > thc;
        if cond1 && cond2 && cond3 && cond4 {
            v1 = "底背驰";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bs1_V230412：MACD DIF 五笔背驰简化信号
///
/// 参数模板：`"{freq}_D{di}T{tha}#{thb}_BS1辅助V230412"`
///
/// 信号逻辑：
/// 1. 取最近 5 笔并校验未完成笔长度；
/// 2. 上笔场景：前三笔涨幅过阈值，且 `DIF(3)` 为局部最大，末笔价格不弱，判 `顶背驰`；
/// 3. 下笔场景镜像：`DIF(3)` 为局部最小，判 `底背驰`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T100#10_BS1辅助V230412_顶背驰_任意_任意_0')`
/// - `Signal('60分钟_D1T100#10_BS1辅助V230412_底背驰_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 笔，默认 `1`；
/// - `tha`：前三笔累计涨跌阈值（BP），默认 `100`；
/// - `thb`：第5笔相对第3笔价格阈值（BP），默认 `10`。
/// 对齐说明：条件组合与 Python `tas_macd_bs1_V230412` 保持一致。
#[signal(
    category = "kline",
    name = "tas_macd_bs1_V230412",
    template = "{freq}_D{di}T{tha}#{thb}_BS1辅助V230412",
    opcode = "TasMacdBs1V230412",
    param_kind = "TasMacdBs1V230412"
)]
pub fn tas_macd_bs1_v230412(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let tha = get_usize_param(params, "tha", 100) as f64;
    let thb = get_usize_param(params, "thb", 10) as f64;
    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let dif = &mc.dif;
    let id_to_idx = bar_index_map(czsc);
    let mut snapshot_overrides = HashMap::new();

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}T{}#{}", di, tha as usize, thb as usize);
    let k3 = "BS1辅助V230412";
    let mut v1 = "其他";

    if czsc.bi_list.len() <= di + 7 || czsc.bars_ubi.len() > 9 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis = get_sub_elements(&czsc.bi_list, di, 5);
    if bis.len() < 5 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bi1 = &bis[0];
    let bi3 = &bis[2];
    let bi5 = &bis[4];
    let bi1_raw = bi1.get_raw_bars();
    if bi1_raw.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let first_dif = id_to_idx
        .get(&bi1_raw[0].id)
        .map(|i| dif[*i])
        .unwrap_or(f64::NAN);
    if first_dif.is_nan() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    if bi5.direction == Direction::Up {
        let bi1_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &bi1.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
            .into_iter()
            .fold(f64::NEG_INFINITY, f64::max);
        let bi3_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &bi3.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
            .into_iter()
            .fold(f64::NEG_INFINITY, f64::max);
        let bi5_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &bi5.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
            .into_iter()
            .fold(f64::NEG_INFINITY, f64::max);
        let cond1 = ((bi3.get_high() - bi1.get_low()) / bi1.get_low()) * 10000.0 > tha;
        let cond2 = bi5_dif < bi3_dif && bi3_dif > bi1_dif;
        let cond3 = ((bi5.get_high() - bi3.get_high()) / bi3.get_high()) * 10000.0 > -thb;
        if cond1 && cond2 && cond3 {
            v1 = "顶背驰";
        }
    } else if bi5.direction == Direction::Down {
        let bi1_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &bi1.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
            .into_iter()
            .fold(f64::INFINITY, f64::min);
        let bi3_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &bi3.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
            .into_iter()
            .fold(f64::INFINITY, f64::min);
        let bi5_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &bi5.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
            .into_iter()
            .fold(f64::INFINITY, f64::min);
        let cond1 = ((bi3.get_low() - bi1.get_high()) / bi1.get_high()) * 10000.0 < -tha;
        let cond2 = bi5_dif > bi3_dif && bi3_dif < bi1_dif;
        let cond3 = ((bi5.get_low() - bi3.get_low()) / bi3.get_low()) * 10000.0 < thb;
        if cond1 && cond2 && cond3 {
            v1 = "底背驰";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_rumi_V230704：RUMI 零轴切换信号
///
/// 参数模板：`"{freq}_D{di}F{timeperiod1}S{timeperiod2}R{rumi_window}_BS辅助V230704"`
///
/// 信号逻辑：
/// 1. 计算 `SMA(timeperiod1)` 与 `WMA(timeperiod2)`，得到 `diff = fast - slow`；
/// 2. 对 `diff` 做 `SMA(rumi_window)` 平滑，得到 `rumi`；
/// 3. `rumi` 上穿 0 轴判 `多头`，下穿 0 轴判 `空头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1F3S50R30_BS辅助V230704_多头_任意_任意_0')`
/// - `Signal('60分钟_D1F3S50R30_BS辅助V230704_空头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod1`：快线均线周期，默认 `3`；
/// - `timeperiod2`：慢线均线周期，默认 `50`；
/// - `rumi_window`：RUMI 平滑周期，默认 `30`。
/// 对齐说明：快慢线选型与零轴交叉判定对齐 Python `tas_rumi_V230704`。
#[signal(
    category = "kline",
    name = "tas_rumi_V230704",
    template = "{freq}_D{di}F{timeperiod1}S{timeperiod2}R{rumi_window}_BS辅助V230704",
    opcode = "TasRumiV230704",
    param_kind = "TasRumiV230704"
)]
pub fn tas_rumi_v230704(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let rumi_window = get_usize_param(params, "rumi_window", 30);
    let timeperiod1 = get_usize_param(params, "timeperiod1", 3);
    let timeperiod2 = get_usize_param(params, "timeperiod2", 50);
    assert!(
        rumi_window < timeperiod2,
        "rumi_window 必须小于 timeperiod2"
    );

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}F{}S{}R{}", di, timeperiod1, timeperiod2, rumi_window);
    let k3 = "BS辅助V230704";
    let mut v1 = "其他";

    if czsc.bars_raw.len() < di + timeperiod2 || di == 0 || di > czsc.bars_raw.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let key1 = format!("{}_{}_{}", czsc.freq, "SMA", timeperiod1);
    let key2 = format!("{}_{}_{}", czsc.freq, "WMA", timeperiod2);
    update_ma_cache(czsc, &key1, "SMA", timeperiod1, cache);
    update_ma_cache(czsc, &key2, "WMA", timeperiod2, cache);
    let fast = cache.series.get(&key1).unwrap();
    let slow = cache.series.get(&key2).unwrap();
    let id_to_idx = bar_index_map(czsc);

    let bars = get_sub_elements(&czsc.bars_raw, di, timeperiod2);
    if bars.len() == timeperiod2 {
        let fast_arr: Vec<f64> = bars
            .iter()
            .filter_map(|x| id_to_idx.get(&x.id).map(|i| fast[*i]))
            .collect();
        let slow_arr: Vec<f64> = bars
            .iter()
            .filter_map(|x| id_to_idx.get(&x.id).map(|i| slow[*i]))
            .collect();
        if fast_arr.len() == timeperiod2 && slow_arr.len() == timeperiod2 {
            let diff: Vec<f64> = fast_arr
                .iter()
                .zip(slow_arr.iter())
                .map(|(a, b)| *a - *b)
                .collect();
            let rumi = calc_sma(&diff, rumi_window);
            if rumi.len() >= 2 {
                let r1 = rumi[rumi.len() - 2];
                let r2 = rumi[rumi.len() - 1];
                if r2 > 0.0 && r1 < 0.0 {
                    v1 = "多头";
                } else if r2 < 0.0 && r1 > 0.0 {
                    v1 = "空头";
                }
            }
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bc_V230804：MACD 黄白线背驰信号
///
/// 参数模板：`"{freq}_D{di}MACD背驰_BS辅助V230804"`
///
/// 信号逻辑：
/// 1. 取最近 7 笔，并在末 5 笔构建中枢；
/// 2. 上笔场景：末笔位于高位区且 DIF 峰值弱于前两上笔，判 `空头`；
/// 3. 下笔场景镜像：末笔位于低位区且 DIF 谷值抬升，判 `多头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD背驰_BS辅助V230804_空头_任意_任意_0')`
/// - `Signal('60分钟_D1MACD背驰_BS辅助V230804_多头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 笔，默认 `1`。
/// 对齐说明：中枢有效性与 DIF 对比口径与 Python `tas_macd_bc_V230804` 一致。
#[signal(
    category = "kline",
    name = "tas_macd_bc_V230804",
    template = "{freq}_D{di}MACD背驰_BS辅助V230804",
    opcode = "TasMacdBcV230804",
    param_kind = "TasMacdBcV230804"
)]
pub fn tas_macd_bc_v230804(czsc: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let id_to_idx = bar_index_map(czsc);
    let mut snapshot_overrides: HashMap<i32, (f64, f64, f64)> = HashMap::new();

    let k1 = czsc.freq.to_string();
    let k2 = format!("D{}MACD背驰", di);
    let k3 = "BS辅助V230804";
    let mut v1 = "其他";

    if czsc.bi_list.len() < 7 || czsc.bars_ubi.len() >= 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis = get_sub_elements(&czsc.bi_list, di, 7);
    if bis.len() < 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let zs = ZS::new(bis[bis.len() - 5..].to_vec());
    if !zs.is_valid() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let dd = bis
        .iter()
        .map(|bi| bi.get_low())
        .fold(f64::INFINITY, f64::min);
    let gg = bis
        .iter()
        .map(|bi| bi.get_high())
        .fold(f64::NEG_INFINITY, f64::max);
    let b1 = &bis[bis.len() - 5];
    let b3 = &bis[bis.len() - 3];
    let b5 = &bis[bis.len() - 1];

    if b5.direction == Direction::Up && b5.get_high() > (gg - (gg - dd) / 4.0) {
        let b5_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b5.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
        .into_iter()
        .fold(f64::NEG_INFINITY, f64::max);
        let mut od = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b1.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        );
        od.extend(snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b3.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        ));
        let od_dif = od.into_iter().fold(f64::NEG_INFINITY, f64::max);
        if 0.0 < b5_dif && b5_dif < od_dif {
            v1 = "空头";
        }
    }
    if b5.direction == Direction::Down && b5.get_low() < (dd + (gg - dd) / 4.0) {
        let b5_dif = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b5.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
        .into_iter()
        .fold(f64::INFINITY, f64::min);
        let mut od = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b1.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        );
        od.extend(snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b3.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        ));
        let od_dif = od.into_iter().fold(f64::INFINITY, f64::min);
        if 0.0 > b5_dif && b5_dif > od_dif {
            v1 = "多头";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// tas_macd_bc_ubi_V230804：未完成笔 MACD 背驰观察
///
/// 参数模板：`"{freq}_MACD背驰_UBI观察V230804"`
///
/// 信号逻辑：
/// 1. 使用未完成笔（UBI）方向与极值位置；
/// 2. 在最近 6 笔中构造中枢并比较 UBI 末段 DIF 与历史对应笔 DIF；
/// 3. 上行 UBI DIF 走弱判 `空头`，下行 UBI DIF 抬升判 `多头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_MACD背驰_UBI观察V230804_空头_任意_任意_0')`
/// - `Signal('60分钟_MACD背驰_UBI观察V230804_多头_任意_任意_0')`
///
/// 参数说明：
/// - 无额外参数。
/// 对齐说明：UBI 原始K线口径与 Python `tas_macd_bc_ubi_V230804` 一致。
#[signal(
    category = "kline",
    name = "tas_macd_bc_ubi_V230804",
    template = "{freq}_MACD背驰_UBI观察V230804",
    opcode = "TasMacdBcUbiV230804",
    param_kind = "TasMacdBcUbiV230804"
)]
pub fn tas_macd_bc_ubi_v230804(
    czsc: &CZSC,
    _params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let cache_key = "MACD12#26#9";
    update_macd_cache(czsc, cache_key, 12, 26, 9, cache);
    let mc = cache.macd.get(cache_key).unwrap();
    let id_to_idx = bar_index_map(czsc);
    let mut snapshot_overrides: HashMap<i32, (f64, f64, f64)> = HashMap::new();

    let k1 = czsc.freq.to_string();
    let k2 = "MACD背驰";
    let k3 = "UBI观察V230804";
    let mut v1 = "其他";

    // 对齐 Python `not ubi` 语义：ubi_fxs 为空视为 ubi 不可用。
    let Some(ubi_fxs) = czsc.get_ubi_fxs() else {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    };
    if ubi_fxs.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    let ubi_raw_bars: Vec<RawBar> = czsc
        .bars_ubi
        .iter()
        .flat_map(|nb| nb.elements.iter().cloned())
        .collect();
    if czsc.bi_list.len() < 7 || ubi_raw_bars.len() < 7 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    let bis = get_sub_elements(&czsc.bi_list, 1, 6);
    if bis.len() < 6 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let zs = ZS::new(bis[bis.len() - 5..].to_vec());
    if !zs.is_valid() {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    let dd = bis
        .iter()
        .map(|bi| bi.get_low())
        .fold(f64::INFINITY, f64::min);
    let gg = bis
        .iter()
        .map(|bi| bi.get_high())
        .fold(f64::NEG_INFINITY, f64::max);
    let ubi_high = ubi_raw_bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let ubi_low = ubi_raw_bars
        .iter()
        .map(|x| x.low)
        .fold(f64::INFINITY, f64::min);
    let ubi_direction = if czsc.bi_list.last().unwrap().direction == Direction::Down {
        Direction::Up
    } else {
        Direction::Down
    };

    let b2 = &bis[bis.len() - 4];
    let b4 = &bis[bis.len() - 2];
    if ubi_direction == Direction::Up && ubi_high > (gg - (gg - dd) / 4.0) {
        let b5_dif = snapshot_dif_values_from_raw_bars(
            czsc,
            mc,
            &id_to_idx,
            &ubi_raw_bars[ubi_raw_bars.len() - 5..],
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
        .into_iter()
        .fold(f64::NEG_INFINITY, f64::max);
        let mut od = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b2.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        );
        od.extend(snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b4.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        ));
        let od_dif = od.into_iter().fold(f64::NEG_INFINITY, f64::max);
        if 0.0 < b5_dif && b5_dif < od_dif {
            v1 = "空头";
        }
    }
    if ubi_direction == Direction::Down && ubi_low < (dd + (gg - dd) / 4.0) {
        let b5_dif = snapshot_dif_values_from_raw_bars(
            czsc,
            mc,
            &id_to_idx,
            &ubi_raw_bars[ubi_raw_bars.len() - 5..],
            12,
            26,
            9,
            &mut snapshot_overrides,
        )
        .into_iter()
        .fold(f64::INFINITY, f64::min);
        let mut od = snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b2.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        );
        od.extend(snapshot_dif_values_from_fx(
            czsc,
            mc,
            &id_to_idx,
            &b4.fx_b,
            12,
            26,
            9,
            &mut snapshot_overrides,
        ));
        let od_dif = od.into_iter().fold(f64::INFINITY, f64::min);
        if 0.0 > b5_dif && b5_dif > od_dif {
            v1 = "多头";
        }
    }

    make_kline_signal_v1(&k1, k2, k3, v1)
}
