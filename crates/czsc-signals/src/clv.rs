use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

/// clv_up_dw_line_V230605：CLV 多空信号
///
/// 参数模板：`"{freq}_D{di}N{n}_CLV多空V230605"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 根K线，计算每根 `(2*close-low-high)/(high-low)`；
/// 2. 计算该序列均值 `clv_ma`；
/// 3. `clv_ma > 0` 判 `看多`，否则判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N70_CLV多空V230605_看多_任意_任意_0')`
/// - `Signal('60分钟_D1N70_CLV多空V230605_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：统计窗口大小，默认 `70`。
/// 对齐说明：CLV 公式与阈值判断对齐 Python `clv_up_dw_line_V230605`。
#[signal(
    category = "kline",
    name = "clv_up_dw_line_V230605",
    template = "{freq}_D{di}N{n}_CLV多空V230605",
    opcode = "ClvUpDwLineV230605",
    param_kind = "ClvUpDwLineV230605"
)]
pub fn clv_up_dw_line_v230605(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 70);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}", di, n);
    let k3 = "CLV多空V230605";

    if c.bars_raw.len() < di + 100 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let mut vals = Vec::with_capacity(bars.len());
    for b in bars {
        let v = (2.0 * b.close - b.low - b.high) / (b.high - b.low);
        vals.push(v);
    }
    let clv_ma = vals.iter().sum::<f64>() / vals.len() as f64;
    let v1 = if clv_ma > 0.0 { "看多" } else { "看空" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
