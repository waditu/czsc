use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

fn std_pop(values: &[f64]) -> f64 {
    if values.is_empty() || values.iter().any(|x| !x.is_finite()) {
        return f64::NAN;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let var = values.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / values.len() as f64;
    var.sqrt()
}

/// pressure_support_V240222：高低点验证支撑压力位
///
/// 参数模板：`"{freq}_D{di}W{w}高低点验证_支撑压力V240222"`
///
/// 信号逻辑：
/// 1. 取最近 `w` 根K线，计算区间最高/最低与振幅标准差 `gap`；
/// 2. 若区间波动不足（`max_high-min_low < gap*0.3*w`）则返回 `其他`；
/// 3. 若窗口两端高点贴近全局高点，判 `压力位`；
/// 4. 若窗口两端低点贴近全局低点，判 `支撑位`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W20高低点验证_支撑压力V240222_压力位_任意_任意_0')`
/// - `Signal('60分钟_D1W20高低点验证_支撑压力V240222_支撑位_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `w`：观察窗口大小，默认 `20`，且必须大于 `10`。
/// 对齐说明：窗口切分与高低点验证条件对齐 Python `pressure_support_V240222`。
#[signal(
    category = "kline",
    name = "pressure_support_V240222",
    template = "{freq}_D{di}W{w}高低点验证_支撑压力V240222",
    opcode = "PressureSupportV240222",
    param_kind = "PressureSupportV240222"
)]
pub fn pressure_support_v240222(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 20);
    assert!(w > 10, "w must be > 10");

    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}高低点验证", di, w);
    let k3 = "支撑压力V240222";
    let mut v1 = "其他";

    if c.bars_raw.len() < w + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let max_high = bars.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let min_low = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let n = ((bars.len() as f64) * 0.2) as usize;
    if n == 0 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let left_bars = &bars[..n];
    let right_bars = &bars[bars.len() - n..];
    let gap = std_pop(
        &bars
            .iter()
            .map(|x| (x.high - x.low).abs())
            .collect::<Vec<f64>>(),
    );

    if max_high - min_low < gap * 0.3 * w as f64 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let left_high = left_bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let right_high = right_bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    if max_high == left_high.max(right_high) && max_high - left_high.min(right_high) < gap {
        v1 = "压力位";
    }

    let left_low = left_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let right_low = right_bars
        .iter()
        .map(|x| x.low)
        .fold(f64::INFINITY, f64::min);
    if min_low == left_low.min(right_low) && left_low.max(right_low) - min_low < gap {
        v1 = "支撑位";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// pressure_support_V240402：分型区间支撑压力位
///
/// 参数模板：`"{freq}_D{di}W{w}_支撑压力V240402"`
///
/// 信号逻辑：
/// 1. 统计最近 `50` 个分型中，包含当前收盘价的分型数量；
/// 2. 若命中分型少于 `5` 或窗口波动不足（`max_high-min_low < gap*3`）返回 `其他`；
/// 3. 当前收盘靠近窗口上沿（前20%）判 `压力位`；
/// 4. 当前收盘靠近窗口下沿（前30%）判 `支撑位`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W60_支撑压力V240402_压力位_任意_任意_0')`
/// - `Signal('60分钟_D1W60_支撑压力V240402_支撑位_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `w`：观察窗口大小，默认 `60`，且必须大于 `10`。
/// 对齐说明：分型筛选与收盘位置阈值对齐 Python `pressure_support_V240402`。
#[signal(
    category = "kline",
    name = "pressure_support_V240402",
    template = "{freq}_D{di}W{w}_支撑压力V240402",
    opcode = "PressureSupportV240402",
    param_kind = "PressureSupportV240402"
)]
pub fn pressure_support_v240402(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 60);
    assert!(w > 10, "w must be > 10");

    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}", di, w);
    let k3 = "支撑压力V240402";
    let mut v1 = "其他";

    if c.bars_raw.len() < w + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let fxs = c.get_fx_list();
    let fxs_tail = if fxs.len() > 50 {
        &fxs[fxs.len() - 50..]
    } else {
        &fxs[..]
    };
    let close = bars[bars.len() - 1].close;
    let near_fx_cnt = fxs_tail
        .iter()
        .filter(|fx| fx.low <= close && close <= fx.high)
        .count();

    let gap = std_pop(
        &bars
            .iter()
            .map(|x| (x.high - x.low).abs())
            .collect::<Vec<f64>>(),
    );
    let max_high = bars.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let min_low = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);

    if near_fx_cnt < 5 || max_high - min_low < gap * 3.0 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let hl_gap = max_high - min_low;
    if close > max_high - hl_gap * 0.2 {
        v1 = "压力位";
    }
    if close < min_low + hl_gap * 0.3 {
        v1 = "支撑位";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// pressure_support_V240406：分型密集支撑压力位
///
/// 参数模板：`"{freq}_D{di}W{w}_支撑压力V240406"`
///
/// 信号逻辑：
/// 1. 统计窗口最高/最低附近的分型数量（严格落在分型区间内）；
/// 2. 若窗口波动不足（`max_high-min_low < gap*3`）返回 `其他`；
/// 3. 若高点附近分型 `>=3` 且收盘靠近上沿，判 `压力位`；
/// 4. 若低点附近分型 `>=3` 且收盘靠近下沿，判 `支撑位`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W60_支撑压力V240406_压力位_任意_任意_0')`
/// - `Signal('60分钟_D1W60_支撑压力V240406_支撑位_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `w`：观察窗口大小，默认 `60`，且必须大于 `10`。
/// 对齐说明：分型密集阈值和价格区间判断对齐 Python `pressure_support_V240406`。
#[signal(
    category = "kline",
    name = "pressure_support_V240406",
    template = "{freq}_D{di}W{w}_支撑压力V240406",
    opcode = "PressureSupportV240406",
    param_kind = "PressureSupportV240406"
)]
pub fn pressure_support_v240406(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 60);
    assert!(w > 10, "w must be > 10");

    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}", di, w);
    let k3 = "支撑压力V240406";
    let mut v1 = "其他";

    if c.bars_raw.len() < w + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let fxs = c.get_fx_list();
    let fxs_tail = if fxs.len() > 50 {
        &fxs[fxs.len() - 50..]
    } else {
        &fxs[..]
    };

    let gap = std_pop(
        &bars
            .iter()
            .map(|x| (x.high - x.low).abs())
            .collect::<Vec<f64>>(),
    );
    let max_high = bars.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let min_low = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);

    if max_high - min_low < gap * 3.0 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let near_high_fx = fxs_tail
        .iter()
        .filter(|fx| fx.low < max_high && max_high < fx.high)
        .count();
    let near_low_fx = fxs_tail
        .iter()
        .filter(|fx| fx.low < min_low && min_low < fx.high)
        .count();
    let hl_gap = max_high - min_low;
    let close = bars[bars.len() - 1].close;

    if near_high_fx >= 3 && close > max_high - hl_gap * 0.2 {
        v1 = "压力位";
    }
    if near_low_fx >= 3 && close < min_low + hl_gap * 0.3 {
        v1 = "支撑位";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// pressure_support_V240530：关键重叠K线支撑压力位
///
/// 参数模板：`"{freq}_D{di}W{w}N{n}_支撑压力V240530"`
///
/// 信号逻辑：
/// 1. 在最近 `w` 根K线中寻找与其他K线重叠次数最多的关键K线；
/// 2. 若最大重叠次数小于 `0.5*w`，返回 `其他`；
/// 3. 以关键K线高低价在全局 `unique price` 列表上的 `±n` 档形成压力/支撑区间；
/// 4. 收盘落入高位区间判 `压力位`，落入低位区间判 `支撑位`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W20N5_支撑压力V240530_压力位_任意_任意_0')`
/// - `Signal('60分钟_D1W20N5_支撑压力V240530_支撑位_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `w`：观察窗口大小，默认 `20`，且必须大于 `10`；
/// - `n`：价格档位偏移，默认 `5`。
/// 对齐说明：关键K线重叠计数和 `unique price ±n` 区间判定对齐 Python `pressure_support_V240530`。
#[signal(
    category = "kline",
    name = "pressure_support_V240530",
    template = "{freq}_D{di}W{w}N{n}_支撑压力V240530",
    opcode = "PressureSupportV240530",
    param_kind = "PressureSupportV240530"
)]
pub fn pressure_support_v240530(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 20);
    let n = params.usize("n", 5);
    assert!(w > 10, "w must be > 10");

    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}N{}", di, w, n);
    let k3 = "支撑压力V240530";
    let mut v1 = "其他";

    if c.bars_raw.len() < w + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let mut overlap_counts = vec![0usize; bars.len()];
    for i in 0..bars.len() {
        let bi = &bars[i];
        let mut count = 0usize;
        for (j, bj) in bars.iter().enumerate() {
            if i == j {
                continue;
            }
            if bi.low.max(bj.low) < bi.high.min(bj.high) {
                count += 1;
            }
        }
        overlap_counts[i] = count;
    }

    // 对齐 Python: max(dict, key=dict.get) 在并列最大时返回“最先插入”的键（最小索引）
    let Some(max_cnt) = overlap_counts.iter().copied().max() else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(key_idx) = overlap_counts.iter().position(|x| *x == max_cnt) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    if (max_cnt as f64) < 0.5 * w as f64 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let key_bar = &bars[key_idx];
    let mut prices: Vec<f64> = c
        .bars_raw
        .iter()
        .flat_map(|x| [x.open, x.close, x.high, x.low])
        .collect();
    prices.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    prices.dedup_by(|a, b| *a == *b);

    let Some(high_idx) = prices.iter().position(|x| *x == key_bar.high) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(low_idx) = prices.iter().position(|x| *x == key_bar.low) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };

    if high_idx < n || low_idx < n {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    if high_idx + n >= prices.len() || low_idx + n >= prices.len() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let close = bars[bars.len() - 1].close;
    let pressure_h = prices[high_idx + n];
    let pressure_l = prices[high_idx - n];
    if pressure_h > close && close > pressure_l {
        v1 = "压力位";
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let support_h = prices[low_idx + n];
    let support_l = prices[low_idx - n];
    if support_h > close && close > support_l {
        v1 = "支撑位";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}
