use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

/// ntmdk_V230824：M 日前收盘价对比多空
///
/// 参数模板：`"{freq}_D{di}M{m}_NTMDK多空V230824"`
///
/// 信号逻辑：
/// 1. 取截止倒数第 `di` 根的最近 `m` 根K线；
/// 2. 若末根收盘价大于首根收盘价，判 `看多`；
/// 3. 否则判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1M10_NTMDK多空V230824_看多_任意_任意_0')`
/// - `Signal('60分钟_D1M10_NTMDK多空V230824_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `m`：回看比较窗口，默认 `10`。
/// 对齐说明：比较口径对齐 Python `ntmdk_V230824`。
#[signal(
    category = "kline",
    name = "ntmdk_V230824",
    template = "{freq}_D{di}M{m}_NTMDK多空V230824",
    opcode = "NtmdkV230824",
    param_kind = "NtmdkV230824"
)]
pub fn ntmdk_v230824(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let m = params.usize("m", 10);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}M{}", di, m);
    let k3 = "NTMDK多空V230824";
    let v1_default = "其他";

    if c.bars_raw.len() < di + m + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }
    let bars = get_sub_elements(&c.bars_raw, di, m);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, v1_default);
    }
    let v1 = if bars[bars.len() - 1].close > bars[0].close {
        "看多"
    } else {
        "看空"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
