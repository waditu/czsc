use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

/// kcatr_up_dw_line_V230823：ATR 通道突破多空
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}T{th}_KCATR多空V230823"`
///
/// 信号逻辑：
/// 1. 在最近 `n` 根上计算平均真实波幅 `ATR`；
/// 2. 在最近 `m` 根上计算收盘均值 `middle`；
/// 3. 最新收盘价大于 `middle + ATR * th` 判 `看多`；
/// 4. 最新收盘价小于 `middle - ATR * th` 判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N30M16T2_KCATR多空V230823_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N30M16T2_KCATR多空V230823_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：ATR 计算窗口，默认 `30`；
/// - `m`：中轨均值窗口，默认 `16`；
/// - `th`：ATR 倍数阈值，默认 `2`。
/// 对齐说明：ATR 取样与突破阈值口径对齐 Python `kcatr_up_dw_line_V230823`。
#[signal(
    category = "kline",
    name = "kcatr_up_dw_line_V230823",
    template = "{freq}_D{di}N{n}M{m}T{th}_KCATR多空V230823",
    opcode = "KcatrUpDwLineV230823",
    param_kind = "KcatrUpDwLineV230823"
)]
pub fn kcatr_up_dw_line_v230823(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 30);
    let m = params.usize("m", 16);
    let th = params.usize("th", 2);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}T{}", di, n, m, th);
    let k3 = "KCATR多空V230823";
    let mut v1 = "其他";

    if c.bars_raw.len() < di + n.max(m) + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let n_bars = get_sub_elements(&c.bars_raw, di, n);
    let m_bars = get_sub_elements(&c.bars_raw, di, m);
    if n_bars.len() < 2 || m_bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let mut tr_sum = 0.0;
    for i in 1..n_bars.len() {
        let b = &n_bars[i];
        let p = &n_bars[i - 1];
        let tr1 = (b.high - b.low).abs();
        let tr2 = (b.high - p.close).abs();
        let tr3 = (b.low - p.close).abs();
        tr_sum += tr1.max(tr2).max(tr3);
    }
    let atr = tr_sum / (n_bars.len() - 1) as f64;
    let middle = m_bars.iter().map(|x| x.close).sum::<f64>() / m_bars.len() as f64;
    let close = m_bars[m_bars.len() - 1].close;

    if close > middle + atr * th as f64 {
        v1 = "看多";
    } else if close < middle - atr * th as f64 {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
