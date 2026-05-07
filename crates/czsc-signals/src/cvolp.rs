use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

fn convolve_prefix(volume: &[f64], weights: &[f64]) -> Vec<f64> {
    let l = volume.len();
    let n = weights.len();
    let mut out = vec![0.0; l];
    for (k, out_k) in out.iter_mut().enumerate().take(l) {
        let i_start = (k + 1).saturating_sub(n);
        let mut acc = 0.0;
        for (i, value) in volume.iter().enumerate().take(k + 1).skip(i_start) {
            let j = k - i;
            acc += value * weights[j];
        }
        *out_k = acc;
    }
    out
}

/// cvolp_up_dw_line_V230612：CVOLP 动量变化率信号
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}UP{up}DW{dw}_CVOLP动量变化率V230612"`
///
/// 信号逻辑：
/// 1. 取最近 `n+m` 根成交量，构造长度为 `n` 的指数权重；
/// 2. 计算卷积平滑序列 `emap`，并将前 `n` 项置为 `emap[n]`；
/// 3. 计算 `sroc = (emap - roll(emap, m))[-1] / roll(emap, m)[-1]`；
/// 4. `sroc > up/100` 判 `看多`，`sroc < -dw/100` 判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N34M55UP5DW5_CVOLP动量变化率V230612_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N34M55UP5DW5_CVOLP动量变化率V230612_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：卷积平滑窗口，默认 `34`；
/// - `m`：滚动比较窗口，默认 `55`；
/// - `up`：看多阈值（百分比整数），默认 `5`；
/// - `dw`：看空阈值（百分比整数），默认 `5`。
/// 对齐说明：卷积平滑与 `roll` 口径对齐 Python `cvolp_up_dw_line_V230612`。
#[signal(
    category = "kline",
    name = "cvolp_up_dw_line_V230612",
    template = "{freq}_D{di}N{n}M{m}UP{up}DW{dw}_CVOLP动量变化率V230612",
    opcode = "CvolpUpDwLineV230612",
    param_kind = "CvolpUpDwLineV230612"
)]
pub fn cvolp_up_dw_line_v230612(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 34);
    let m = params.usize("m", 55);
    let up = params.usize("up", 5);
    let dw = params.usize("dw", 5);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}UP{}DW{}", di, n, m, up, dw);
    let k3 = "CVOLP动量变化率V230612";
    let mut v1 = "其他";

    if c.bars_raw.len() < di + n + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bars = get_sub_elements(&c.bars_raw, di, n + m);
    if bars.len() <= n || bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let volume: Vec<f64> = bars.iter().map(|x| x.vol).collect();
    let mut weights: Vec<f64> = (0..n)
        .map(|i| (-1.0 + i as f64 / (n.saturating_sub(1).max(1) as f64)).exp())
        .collect();
    let sum_w = weights.iter().sum::<f64>();
    if sum_w == 0.0 || !sum_w.is_finite() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    for w in &mut weights {
        *w /= sum_w;
    }

    let mut emap = convolve_prefix(&volume, &weights);
    let fill_v = emap[n];
    for x in emap.iter_mut().take(n) {
        *x = fill_v;
    }

    let l = emap.len();
    let ridx = (l - 1 + l - (m % l)) % l; // 对齐 np.roll(emap, m)[-1]
    let denom = emap[ridx];
    let numer = emap[l - 1] - denom;
    let sroc = if denom == 0.0 {
        if numer > 0.0 {
            f64::INFINITY
        } else if numer < 0.0 {
            f64::NEG_INFINITY
        } else {
            f64::NAN
        }
    } else {
        numer / denom
    };

    if sroc > up as f64 / 100.0 {
        v1 = "看多";
    }
    if sroc < -(dw as f64) / 100.0 {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
