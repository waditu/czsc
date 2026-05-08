use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{bar_index_map, get_sub_elements, make_kline_signal_v1, make_kline_signal_v2};
use crate::utils::ta::update_vol_ma_cache;
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

fn qcut_labels(values: &[f64], q: usize) -> Option<Vec<usize>> {
    if q == 0 || values.is_empty() || values.iter().any(|x| !x.is_finite()) {
        return None;
    }
    let mut sorted: Vec<f64> = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let quantile = |p: f64| -> f64 {
        if sorted.len() == 1 {
            return sorted[0];
        }
        let h = (sorted.len() - 1) as f64 * p;
        let i = h.floor() as usize;
        let j = h.ceil() as usize;
        if i == j {
            sorted[i]
        } else {
            sorted[i] + (h - i as f64) * (sorted[j] - sorted[i])
        }
    };

    let mut edges = Vec::with_capacity(q + 1);
    for i in 0..=q {
        edges.push(quantile(i as f64 / q as f64));
    }
    edges.dedup_by(|a, b| (*a - *b).abs() <= f64::EPSILON);
    if edges.len() <= 1 {
        return None;
    }
    let bins = edges.len() - 1;
    let mut labels = Vec::with_capacity(values.len());
    for &x in values {
        if x < edges[0] || x > edges[bins] {
            return None;
        }
        let mut found = None;
        for i in 0..bins {
            let left_ok = if i == 0 { x >= edges[i] } else { x > edges[i] };
            let right_ok = x <= edges[i + 1];
            if left_ok && right_ok {
                found = Some(i);
                break;
            }
        }
        labels.push(found.unwrap_or(bins - 1));
    }
    Some(labels)
}

/// vol_single_ma_V230214：单成交量均线多空与方向信号
///
/// 参数模板：`"{freq}_D{di}VOL#{ma_type}#{timeperiod}_分类V230214"`
///
/// 信号逻辑：
/// 1. 计算指定成交量均线（`SMA/EMA/WMA`）；
/// 2. `vol_now >= vol_ma_now` 判定 `多头`，否则 `空头`；
/// 3. `vol_ma_now >= vol_ma_prev` 判定 `向上`，否则 `向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1VOL#SMA#5_分类V230214_多头_向上_任意_0')`
/// - `Signal('60分钟_D1VOL#EMA#12_分类V230214_空头_向下_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`。
/// 对齐说明：成交量均线缓存与判定口径对齐 Python `vol_single_ma_V230214`。
#[signal(
    category = "kline",
    name = "vol_single_ma_V230214",
    template = "{freq}_D{di}VOL#{ma_type}#{timeperiod}_分类V230214",
    opcode = "VolSingleMaV230214",
    param_kind = "VolSingleMaV230214"
)]
pub fn vol_single_ma_v230214(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let timeperiod = params.usize("timeperiod", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}VOL#{}#{}", di, ma_type, timeperiod);
    let k3 = "分类V230214";

    let cache_key = format!("VOL#{}#{}", ma_type, timeperiod);
    update_vol_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);

    let bars = get_sub_elements(&c.bars_raw, di, 3);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let idx_map = bar_index_map(c);
    let idx_prev = bars.len() - 2;
    let idx_last = bars.len() - 1;
    let Some(i_prev) = idx_map.get(&bars[idx_prev].id).copied() else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(i_last) = idx_map.get(&bars[idx_last].id).copied() else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    if i_prev >= ma.len() || i_last >= ma.len() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let v1 = if bars[idx_last].vol >= ma[i_last] {
        "多头"
    } else {
        "空头"
    };
    let v2 = if ma[i_last] >= ma[i_prev] {
        "向上"
    } else {
        "向下"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// vol_double_ma_V230214：成交量双均线多空信号
///
/// 参数模板：`"{freq}_D{di}VOL双均线{ma_type}#{t1}#{t2}_BS辅助V230214"`
///
/// 信号逻辑：
/// 1. 分别计算成交量短均线 `t1` 与长均线 `t2`；
/// 2. `vol_ma_short >= vol_ma_long` 判定 `看多`，否则 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1VOL双均线SMA#5#20_BS辅助V230214_看多_任意_任意_0')`
/// - `Signal('60分钟_D1VOL双均线EMA#5#20_BS辅助V230214_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `t1`：短均线周期，默认 `5`；
/// - `t2`：长均线周期，默认 `20`；
/// - `ma_type`：均线类型，默认 `SMA`。
/// 对齐说明：短长成交量均线关系判定与 Python `vol_double_ma_V230214` 一致。
#[signal(
    category = "kline",
    name = "vol_double_ma_V230214",
    template = "{freq}_D{di}VOL双均线{ma_type}#{t1}#{t2}_BS辅助V230214",
    opcode = "VolDoubleMaV230214",
    param_kind = "VolDoubleMaV230214"
)]
pub fn vol_double_ma_v230214(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let t1 = params.usize("t1", 5);
    let t2 = params.usize("t2", 20);
    assert!(t2 > t1, "t2 must be greater than t1");
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let k1 = c.freq.to_string();
    let k2 = format!("D{}VOL双均线{}#{}#{}", di, ma_type, t1, t2);
    let k3 = "BS辅助V230214";

    let cache_key1 = format!("VOL#{}#{}", ma_type, t1);
    let cache_key2 = format!("VOL#{}#{}", ma_type, t2);
    update_vol_ma_cache(c, &cache_key1, &ma_type, t1, cache);
    update_vol_ma_cache(c, &cache_key2, &ma_type, t2, cache);

    let bars = get_sub_elements(&c.bars_raw, di, 3);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let Some(ma1) = cache.series.get(&cache_key1) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(ma2) = cache.series.get(&cache_key2) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let idx_map = bar_index_map(c);
    let Some(i_last) = idx_map.get(&bars[bars.len() - 1].id).copied() else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    if i_last >= ma1.len() || i_last >= ma2.len() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let v1 = if ma1[i_last] >= ma2[i_last] {
        "看多"
    } else {
        "看空"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// vol_ti_suo_V221216：梯量与缩量柱信号
///
/// 参数模板：`"{freq}_D{di}K_量柱V221216"`
///
/// 信号逻辑：
/// 1. 连续三根成交量递增判定 `梯量`，递减判定 `缩量`；
/// 2. 在 `梯量/缩量` 前提下，以当前收盘与前两根收盘区间比较得到 `价升/价跌/价平`；
/// 3. 不满足量柱条件时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K_量柱V221216_梯量_价升_任意_0')`
/// - `Signal('60分钟_D1K_量柱V221216_缩量_价跌_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：量柱与价位分类规则对齐 Python `vol_ti_suo_V221216`。
#[signal(
    category = "kline",
    name = "vol_ti_suo_V221216",
    template = "{freq}_D{di}K_量柱V221216",
    opcode = "VolTiSuoV221216",
    param_kind = "VolTiSuoV221216"
)]
pub fn vol_ti_suo_v221216(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "量柱V221216";
    if c.bars_raw.len() < di + 5 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let bar1 = &c.bars_raw[c.bars_raw.len() - di];
    let bar2 = &c.bars_raw[c.bars_raw.len() - di - 1];
    let bar3 = &c.bars_raw[c.bars_raw.len() - di - 2];
    let close_max = bar2.close.max(bar3.close);
    let close_min = bar2.close.min(bar3.close);

    let v1 = if bar1.vol > bar2.vol && bar2.vol > bar3.vol {
        "梯量"
    } else if bar1.vol < bar2.vol && bar2.vol < bar3.vol {
        "缩量"
    } else {
        "其他"
    };
    if v1 == "其他" {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let v2 = if bar1.close < close_min && bar1.close < bar1.open {
        "价跌"
    } else if bar1.close > close_max && bar1.close > bar1.open {
        "价升"
    } else {
        "价平"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// vol_gao_di_V221218：高量柱与低量柱信号
///
/// 参数模板：`"{freq}_D{di}K_量柱V221218"`
///
/// 信号逻辑：
/// 1. 依次检查 `10/9/8/7/6` 根窗口；
/// 2. 若末根成交量为窗口最大值，判 `高量柱`；
/// 3. 若次末根为窗口最大且末根不足其 50%，判 `高量黄金柱`；
/// 4. 若末根成交量为窗口最小值，判 `低量柱`；
/// 5. 命中后输出对应窗口长度（如 `10K`）。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K_量柱V221218_高量柱_10K_任意_0')`
/// - `Signal('60分钟_D1K_量柱V221218_低量柱_7K_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：窗口递减检查顺序与高/低量柱定义对齐 Python `vol_gao_di_V221218`。
#[signal(
    category = "kline",
    name = "vol_gao_di_V221218",
    template = "{freq}_D{di}K_量柱V221218",
    opcode = "VolGaoDiV221218",
    param_kind = "VolGaoDiV221218"
)]
pub fn vol_gao_di_v221218(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "量柱V221218";
    let mut v1 = "其他";
    let mut v2 = "任意".to_string();

    for n in [10usize, 9, 8, 7, 6] {
        let bars = get_sub_elements(&c.bars_raw, di, n);
        if bars.len() != n || bars.len() <= 5 {
            continue;
        }
        let max_vol = bars.iter().map(|x| x.vol).fold(f64::NEG_INFINITY, f64::max);
        let min_vol = bars.iter().map(|x| x.vol).fold(f64::INFINITY, f64::min);
        let last = &bars[bars.len() - 1];
        let prev = &bars[bars.len() - 2];
        let cur = if (last.vol - max_vol).abs() <= f64::EPSILON {
            "高量柱"
        } else if (prev.vol - max_vol).abs() <= f64::EPSILON && last.vol < prev.vol * 0.5 {
            "高量黄金柱"
        } else if (last.vol - min_vol).abs() <= f64::EPSILON {
            "低量柱"
        } else {
            "其他"
        };
        if cur != "其他" {
            v1 = cur;
            v2 = format!("{}K", n);
            break;
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}

/// vol_window_V230731：窗口成交量分层特征
///
/// 参数模板：`"{freq}_D{di}W{w}M{m}N{n}_窗口能量V230731"`
///
/// 信号逻辑：
/// 1. 取最近 `m` 根成交量并按 `qcut` 分成 `n` 层；
/// 2. 统计最近 `w` 根中的最高层与最低层；
/// 3. 输出 `高量N{max}` 与 `低量N{min}`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D2W5M100N10_窗口能量V230731_高量N9_低量N4_任意_0')`
/// - `Signal('60分钟_D1W5M30N10_窗口能量V230731_高量N10_低量N3_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `w`：观察窗口大小，默认 `5`；
/// - `m`：分层样本长度，默认 `30`；
/// - `n`：分层数量，默认 `10`。
/// 对齐说明：分层采用与 Python `pd.qcut(..., duplicates='drop')` 等价的去重分位边界。
#[signal(
    category = "kline",
    name = "vol_window_V230731",
    template = "{freq}_D{di}W{w}M{m}N{n}_窗口能量V230731",
    opcode = "VolWindowV230731",
    param_kind = "VolWindowV230731"
)]
pub fn vol_window_v230731(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 5);
    let m = params.usize("m", 30);
    let n = params.usize("n", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}M{}N{}", di, w, m, n);
    let k3 = "窗口能量V230731";

    if c.bars_raw.len() < di + m {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let vols: Vec<f64> = get_sub_elements(&c.bars_raw, di, m)
        .iter()
        .map(|x| x.vol)
        .collect();
    let Some(labels) = qcut_labels(&vols, n) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    if labels.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let tail = if w >= labels.len() {
        &labels[..]
    } else {
        &labels[labels.len() - w..]
    };
    let max_layer = tail.iter().copied().max().unwrap_or(0) + 1;
    let min_layer = tail.iter().copied().min().unwrap_or(0) + 1;
    let v1 = format!("高量N{}", max_layer);
    let v2 = format!("低量N{}", min_layer);
    make_kline_signal_v2(&k1, &k2, k3, &v1, &v2)
}

/// vol_window_V230801：窗口成交量先后顺序特征
///
/// 参数模板：`"{freq}_D{di}W{w}_窗口能量V230801"`
///
/// 信号逻辑：
/// 1. 取最近 `w` 根成交量；
/// 2. 若最小量索引在最大量索引之后，判 `先放后缩`；
/// 3. 否则判 `先缩后放`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W5_窗口能量V230801_先放后缩_任意_任意_0')`
/// - `Signal('60分钟_D1W5_窗口能量V230801_先缩后放_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `w`：观察窗口大小，默认 `5`。
/// 对齐说明：最大/最小成交量首次出现位置比较逻辑对齐 Python `vol_window_V230801`。
#[signal(
    category = "kline",
    name = "vol_window_V230801",
    template = "{freq}_D{di}W{w}_窗口能量V230801",
    opcode = "VolWindowV230801",
    param_kind = "VolWindowV230801"
)]
pub fn vol_window_v230801(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}", di, w);
    let k3 = "窗口能量V230801";

    if c.bars_raw.len() < di + w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let vols: Vec<f64> = get_sub_elements(&c.bars_raw, di, w)
        .iter()
        .map(|x| x.vol)
        .collect();
    if vols.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let min_i = vols
        .iter()
        .enumerate()
        .min_by(|a, b| a.1.partial_cmp(b.1).unwrap_or(std::cmp::Ordering::Equal))
        .map(|(i, _)| i)
        .unwrap_or(0);
    let max_i = vols
        .iter()
        .enumerate()
        .max_by(|a, b| a.1.partial_cmp(b.1).unwrap_or(std::cmp::Ordering::Equal))
        .map(|(i, _)| i)
        .unwrap_or(0);
    let v1 = if min_i > max_i {
        "先放后缩"
    } else {
        "先缩后放"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
