use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, get_usize_param, make_kline_signal_v1, make_kline_signal_v2};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

fn get_f64_param(params: &ParamView, key: &str, default: f64) -> f64 {
    if let Some(v) = params.value(key) {
        if let Some(x) = v.as_f64() {
            return x;
        }
        if let Some(s) = v.as_str()
            && let Ok(x) = s.parse::<f64>() {
                return x;
            }
    }
    default
}

#[inline]
fn py_float_str(v: f64) -> String {
    let mut s = v.to_string();
    if !s.contains('.') && !s.contains('e') && !s.contains('E') {
        s.push_str(".0");
    }
    s
}

#[inline]
fn solid(bar: &RawBar) -> f64 {
    (bar.open - bar.close).abs()
}

#[inline]
fn upper(bar: &RawBar) -> f64 {
    bar.high - bar.open.max(bar.close)
}

#[inline]
fn lower(bar: &RawBar) -> f64 {
    bar.open.min(bar.close) - bar.low
}

fn variance(values: &[f64]) -> f64 {
    if values.is_empty() {
        return f64::NAN;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    values.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / values.len() as f64
}

fn check_szx(bar: &RawBar, th: i32) -> bool {
    if bar.close == bar.open && bar.high != bar.low {
        return true;
    }
    if bar.close != bar.open && (bar.high - bar.low) / (bar.close - bar.open).abs() > th as f64 {
        return true;
    }
    false
}

/// jcc_san_xing_xian_V221023：伞形线形态信号
///
/// 参数模板：`"{freq}_D{di}TH{th}_伞形线"`
///
/// 信号逻辑：
/// 1. 判断当前K线是否满足长下影短上影（下影 > 实体 * th，且上影 < 0.2 * 实体）；
/// 2. 若满足，再结合左侧20根区间位置，判定 `锤子/上吊`；
/// 3. 不满足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1TH200_伞形线_满足_锤子_任意_0')`
/// - `Signal('15分钟_D1TH200_伞形线_满足_上吊_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `th`：下影线与实体倍数阈值，默认 `2`（内部按 100 倍整数编码）。
/// 对齐说明：与 Python `jcc_san_xing_xian_V221023` 判定顺序一致。
#[signal(
    category = "kline",
    name = "jcc_san_xing_xian_V221023",
    template = "{freq}_D{di}TH{th}_伞形线V221023",
    opcode = "JccSanXingXianV221023",
    param_kind = "JccSanXingXianV221023"
)]
pub fn jcc_san_xing_xian_v221023(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_f64_param(params, "th", 2.0);
    let th_i = (th * 100.0) as i32;

    let k1 = c.freq.to_string();
    let k2 = format!("D{}TH{}", di, th_i);
    let k3 = "伞形线";

    if di == 0 || di > c.bars_raw.len() {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }

    let bar = &c.bars_raw[c.bars_raw.len() - di];
    let x1 = bar.high - bar.open.max(bar.close);
    let x2 = (bar.close - bar.open).abs();
    let x3 = bar.open.min(bar.close) - bar.low;
    let v1 = if x3 > x2 * th_i as f64 / 100.0 && x1 < 0.2 * x2 {
        "满足"
    } else {
        "其他"
    };

    let mut v2 = "其他";
    if c.bars_raw.len() > 20 + di {
        let left_bars = get_sub_elements(&c.bars_raw, di, 20);
        if !left_bars.is_empty() {
            let left_max = left_bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max);
            let left_min = left_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
            let gap = left_max - left_min;
            if bar.low <= left_min + 0.25 * gap {
                v2 = "锤子";
            } else if bar.high >= left_max - 0.25 * gap {
                v2 = "上吊";
            }
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_ten_mo_V221028：吞没形态
///
/// 参数模板：`"{freq}_D{di}_吞没形态"`
///
/// 信号逻辑：
/// 1. 当前K线高低点完全包住前一根K线，记 `满足`；
/// 2. 结合左侧20根位置与实体方向，区分 `看涨吞没/看跌吞没`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1_吞没形态_满足_看涨吞没_任意_0')`
/// - `Signal('15分钟_D1_吞没形态_满足_看跌吞没_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `jcc_ten_mo_V221028` 判定条件一致。
#[signal(
    category = "kline",
    name = "jcc_ten_mo_V221028",
    template = "{freq}_D{di}_吞没形态V221028",
    opcode = "JccTenMoV221028",
    param_kind = "JccTenMoV221028"
)]
pub fn jcc_ten_mo_v221028(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}", di);
    let k3 = "吞没形态";

    if c.bars_raw.len() < di + 1 || di == 0 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }

    let bar1 = &c.bars_raw[c.bars_raw.len() - di];
    let bar2 = &c.bars_raw[c.bars_raw.len() - di - 1];
    let v1 = if bar1.high > bar2.high && bar1.low < bar2.low {
        "满足"
    } else {
        "其他"
    };

    let mut v2 = "其他";
    if c.bars_raw.len() > 20 + di {
        let left_bars = get_sub_elements(&c.bars_raw, di, 20);
        if !left_bars.is_empty() {
            let left_max = left_bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max);
            let left_min = left_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
            let gap = left_max - left_min;

            if bar1.low <= left_min + 0.25 * gap
                && bar1.close > bar1.open
                && bar1.close > bar2.high
                && bar1.open < bar2.low
            {
                v2 = "看涨吞没";
            } else if bar1.high >= left_max - 0.25 * gap
                && bar1.close < bar1.open
                && bar1.close < bar2.low
                && bar1.open > bar2.high
            {
                v2 = "看跌吞没";
            }
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_wu_yun_gai_ding_V221101：乌云盖顶
///
/// 参数模板：`"{freq}_D{di}Z{z}TH{th}_乌云盖顶"`
///
/// 信号逻辑：
/// 1. 前一根阳线实体涨幅需大于 `z`；
/// 2. 当前K线跳空高开，且收盘回落到前一根实体内部；
/// 3. 前一根收盘位于左侧10根收盘高位，判定 `满足`。
///
/// 信号列表示例：
/// - `Signal('日线_D1Z500TH50_乌云盖顶_满足_任意_任意_0')`
/// - `Signal('日线_D1Z500TH50_乌云盖顶_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `z`：前一根阳线最小涨幅（BP），默认 `500`；
/// - `th`：当前收盘扎入前一根实体比例，默认 `50`。
/// 对齐说明：与 Python `jcc_wu_yun_gai_ding_V221101` 一致。
#[signal(
    category = "kline",
    name = "jcc_wu_yun_gai_ding_V221101",
    template = "{freq}_D{di}Z{z}TH{th}_乌云盖顶V221101",
    opcode = "JccWuYunGaiDingV221101",
    param_kind = "JccWuYunGaiDingV221101"
)]
pub fn jcc_wu_yun_gai_ding_v221101(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let z = get_usize_param(params, "z", 500) as f64;
    let th = get_usize_param(params, "th", 50) as f64;

    let k1 = c.freq.to_string();
    let k2 = format!("D{}Z{}TH{}", di, z as i32, th as i32);
    let k3 = "乌云盖顶";
    let mut v1 = "其他";

    if c.bars_raw.len() > di + 10 && di > 0 {
        let pre_bar = &c.bars_raw[c.bars_raw.len() - di - 1];
        let bar = &c.bars_raw[c.bars_raw.len() - di];
        let z0 = (pre_bar.close - pre_bar.open) / pre_bar.open * 10000.0;
        let flag_z = z0 > z;
        let flag_ho = bar.open > pre_bar.high;
        let flag_th = bar.close < (pre_bar.close + pre_bar.open) * (th / 100.0);

        let left_bars = get_sub_elements(&c.bars_raw, di + 2, 10);
        if !left_bars.is_empty() {
            let left_max_close = left_bars
                .iter()
                .map(|x| x.close)
                .fold(f64::NEG_INFINITY, f64::max);
            let flag_up = pre_bar.close >= left_max_close;
            if flag_z && flag_ho && flag_th && flag_up {
                v1 = "满足";
            }
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// jcc_ci_tou_V221101：刺透形态
///
/// 参数模板：`"{freq}_D{di}Z{z}TH{th}_刺透形态"`
///
/// 信号逻辑：
/// 1. 前一根为大阴线且跌幅超过 `z`；
/// 2. 当前低开并收盘刺入前一根实体 `th` 比例以上；
/// 3. 满足则返回 `满足`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1Z100TH50_刺透形态_满足_任意_任意_0')`
/// - `Signal('15分钟_D1Z100TH50_刺透形态_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `z`：前一根最小跌幅（BP），默认 `100`；
/// - `th`：刺入比例阈值，默认 `50`。
/// 对齐说明：与 Python `jcc_ci_tou_V221101` 一致。
#[signal(
    category = "kline",
    name = "jcc_ci_tou_V221101",
    template = "{freq}_D{di}Z{z}TH{th}_刺透形态V221101",
    opcode = "JccCiTouV221101",
    param_kind = "JccCiTouV221101"
)]
pub fn jcc_ci_tou_v221101(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let z = get_usize_param(params, "z", 100) as f64;
    let th = get_usize_param(params, "th", 50) as f64;

    let k1 = c.freq.to_string();
    let k2 = format!("D{}Z{}TH{}", di, z as i32, th as i32);
    let k3 = "刺透形态";

    if c.bars_raw.len() < di + 15 || di == 0 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let bars = get_sub_elements(&c.bars_raw, di, 2);
    if bars.len() != 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bar2 = &bars[0];
    let bar1 = &bars[1];

    let c1 = bar2.close < bar2.open && (1.0 - bar2.close / bar2.open) > z / 10000.0;
    let c2 =
        bar1.open < bar2.low && bar1.close > bar2.close + (bar2.open - bar2.close) * (th / 100.0);
    let v1 = if c1 && c2 { "满足" } else { "其他" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// jcc_san_fa_V20221118：三法形态A
///
/// 参数模板：`"{freq}_D{di}K_三法A"`
///
/// 信号逻辑：
/// 1. 在 5~8 根窗口内扫描三法形态；
/// 2. 满足上升三法或下降三法时输出方向；
/// 3. `v2` 记录触发窗口长度 `nK`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K_三法A_上升三法_6K_任意_0')`
/// - `Signal('60分钟_D1K_三法A_下降三法_8K_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：窗口遍历与条件组合对齐 Python `jcc_san_fa_V20221118`。
#[signal(
    category = "kline",
    name = "jcc_san_fa_V20221118",
    template = "{freq}_D{di}K_三法AV20221118",
    opcode = "JccSanFaV20221118",
    param_kind = "JccSanFaV20221118"
)]
pub fn jcc_san_fa_v20221118(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "三法A";

    let check = |bars: &[RawBar]| -> &'static str {
        if bars.len() < 5 {
            return "其他";
        }
        let last = bars.last().unwrap();
        let first = &bars[0];
        let c1 = if last.close > last.open && first.close > first.open && last.close > first.high {
            "上升"
        } else if last.close < last.open && first.close < first.open && last.close < first.low {
            "下降"
        } else {
            "其他"
        };

        let mid = &bars[1..bars.len() - 1];
        let hhc = mid.iter().map(|x| x.close).fold(f64::NEG_INFINITY, f64::max);
        let llc = mid.iter().map(|x| x.close).fold(f64::INFINITY, f64::min);
        let hhv = mid.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
        let llv = mid.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);

        if c1 == "上升" && last.close > hhv && hhv > first.high && llv > first.open && first.close > hhc {
            "上升三法"
        } else if c1 == "下降"
            && first.low > llv
            && llv > last.close
            && hhv < first.open
            && first.close < llc
        {
            "下降三法"
        } else {
            "其他"
        }
    };

    let mut v1 = "其他";
    let mut v2 = "其他";
    for n in [5usize, 6, 7, 8] {
        let bars = get_sub_elements(&c.bars_raw, di, n);
        let t = check(bars);
        if t != "其他" {
            v1 = t;
            v2 = if n == 5 {
                "5K"
            } else if n == 6 {
                "6K"
            } else if n == 7 {
                "7K"
            } else {
                "8K"
            };
            break;
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_san_fa_V20221115：三法形态
///
/// 参数模板：`"{freq}_D{di}K_三法"`
///
/// 信号逻辑：
/// 1. 固定观察 6 根K线，比较首尾与中间三根位置关系；
/// 2. 满足基础强度阈值时，判定 `上升三法/下降三法`；
/// 3. 不满足返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K_三法_满足_上升三法_任意_0')`
/// - `Signal('60分钟_D1K_三法_满足_下降三法_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `zdf`：首尾涨跌幅阈值（BP），默认 `500`。
/// 对齐说明：与 Python `jcc_san_fa_V20221115` 判定一致。
#[signal(
    category = "kline",
    name = "jcc_san_fa_V20221115",
    template = "{freq}_D{di}K_三法V20221115",
    opcode = "JccSanFaV20221115",
    param_kind = "JccSanFaV20221115"
)]
pub fn jcc_san_fa_v20221115(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let zdf = get_usize_param(params, "zdf", 500) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "三法";

    let bars = get_sub_elements(&c.bars_raw, di, 6);
    if bars.len() != 6 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let bar6 = &bars[0];
    let bar5 = &bars[1];
    let bar4 = &bars[2];
    let bar3 = &bars[3];
    let bar2 = &bars[4];
    let bar1 = &bars[5];

    let bar1_zdf = ((bar2.close - bar1.close) / bar2.close).abs() * 10000.0;
    let bar5_zdf = ((bar6.close - bar5.close) / bar6.close).abs() * 10000.0;
    let max_high = bar2.high.max(bar3.high).max(bar4.high);
    let min_low = bar2.low.min(bar3.low).min(bar4.low);

    let v1 = if bar1_zdf >= zdf && bar5_zdf > zdf && bar5.high > max_high {
        "满足"
    } else {
        "其他"
    };

    let v2 = if bar5.close > bar5.open
        && bar1.close > bar1.open
        && bar1.close > bar5.high
        && bar1.close > max_high
        && bar1.open > bar2.close
    {
        "上升三法"
    } else if bar5.close < bar5.open
        && bar1.close < bar1.open
        && bar1.close < bar5.low
        && bar1.close < min_low
        && bar1.open < bar2.close
    {
        "下降三法"
    } else {
        "其他"
    };

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_xing_xian_V221118：星形线
///
/// 参数模板：`"{freq}_D{di}TH{th}_星形线"`
///
/// 信号逻辑：
/// 1. 取三根K线，按高低点结构区分启明星/黄昏星候选；
/// 2. 再结合实体强弱关系做最终确认；
/// 3. 中间K线开收相等时输出 `中间十字`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D2TH2_星形线_启明星_中间十字_任意_0')`
/// - `Signal('60分钟_D2TH2_星形线_黄昏星_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `2`；
/// - `th`：左侧实体与中间实体的倍率阈值，默认 `2`。
/// 对齐说明：与 Python `jcc_xing_xian_V221118` 条件一致。
#[signal(
    category = "kline",
    name = "jcc_xing_xian_V221118",
    template = "{freq}_D{di}TH{th}_星形线V221118",
    opcode = "JccXingXianV221118",
    param_kind = "JccXingXianV221118"
)]
pub fn jcc_xing_xian_v221118(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 2);
    let th = get_usize_param(params, "th", 2) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TH{}", di, th as i32);
    let k3 = "星形线";

    let bars = get_sub_elements(&c.bars_raw, di, 3);
    if bars.len() != 3 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }
    let bar3 = &bars[0];
    let bar2 = &bars[1];
    let bar1 = &bars[2];

    let x3 = (bar3.close - bar3.open).abs();
    let x2 = (bar2.close - bar2.open).abs();
    let x1 = (bar1.close - bar1.open).abs();

    let mut v1 = "其他";
    if bar3.high > bar2.high
        && bar2.high < bar1.high
        && bar3.low > bar2.low
        && bar2.low < bar1.low
        && bar3.close < bar3.open
        && x2 * th < x3
        && x3 < x2 + x1
        && bar1.close > bar1.open
        && bar1.open > bar2.close.max(bar2.open)
    {
        v1 = "启明星";
    } else if bar3.high < bar2.high
        && bar2.high > bar1.high
        && bar3.low < bar2.low
        && bar2.low > bar1.low
        && bar3.close > bar3.open
        && x2 * th < x3
        && x3 < x2 + x1
        && bar1.close < bar1.open
        && bar1.open < bar2.close.min(bar2.open)
    {
        v1 = "黄昏星";
    }

    let v2 = if bar2.close == bar2.open { "中间十字" } else { "任意" };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_fen_shou_xian_V20221113：分手线
///
/// 参数模板：`"{freq}_D{di}K_分手线"`
///
/// 信号逻辑：
/// 1. 两根K线同开盘，且第二根收盘突破第一根高低点，判 `满足`；
/// 2. 结合区间位置与实体方向，细分 `上升分手/下跌分手`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K_分手线_满足_上升分手_任意_0')`
/// - `Signal('60分钟_D1K_分手线_满足_下跌分手_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `zdf`：分手强度阈值（BP），默认 `300`。
/// 对齐说明：与 Python `jcc_fen_shou_xian_V20221113` 一致。
#[signal(
    category = "kline",
    name = "jcc_fen_shou_xian_V20221113",
    template = "{freq}_D{di}K_分手线V20221113",
    opcode = "JccFenShouXianV20221113",
    param_kind = "JccFenShouXianV20221113"
)]
pub fn jcc_fen_shou_xian_v20221113(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let zdf = get_usize_param(params, "zdf", 300) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "分手线";

    if c.bars_raw.len() < di + 1 || di == 0 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }

    let bar1 = &c.bars_raw[c.bars_raw.len() - di];
    let bar2 = &c.bars_raw[c.bars_raw.len() - di - 1];
    let v1 = if (bar1.open == bar2.open && bar1.close < bar2.low) || bar1.close > bar2.high {
        "满足"
    } else {
        "其他"
    };

    let mut v2 = "其他";
    if c.bars_raw.len() > 20 + di {
        let left_bars = get_sub_elements(&c.bars_raw, di, 20);
        if !left_bars.is_empty() {
            let left_max = left_bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max);
            let left_min = left_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
            let gap = left_max - left_min;

            if bar1.low <= left_min + 0.25 * gap
                && bar1.open == bar2.open
                && bar1.close < bar2.low
                && bar2.close > bar2.open
                && (bar2.close - bar1.close) / bar2.close * 10000.0 > zdf
            {
                v2 = "下跌分手";
            } else if bar1.high >= left_max - 0.25 * gap
                && bar1.open == bar2.open
                && bar1.close > bar2.high
                && bar2.close < bar2.open
                && (bar1.close - bar2.close) / bar2.close * 10000.0 > zdf
            {
                v2 = "上升分手";
            }
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_zhu_huo_xian_V221027：烛火线
///
/// 参数模板：`"{freq}_D{di}T{th}F{zf}_烛火线"`
///
/// 信号逻辑：
/// 1. 以影线、实体和振幅阈值判断是否 `满足`；
/// 2. 结合左侧20根区间位置判定 `箭在弦/风中烛`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1T200F500_烛火线_满足_箭在弦_任意_0')`
/// - `Signal('60分钟_D1T200F500_烛火线_满足_风中烛_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `th`：上影线与实体倍数阈值，默认 `2`；
/// - `zf`：最小振幅阈值（BP），默认 `500`。
/// 对齐说明：按 Python `jcc_zhu_huo_xian_V221027` 原始公式实现。
#[signal(
    category = "kline",
    name = "jcc_zhu_huo_xian_V221027",
    template = "{freq}_D{di}T{th}F{zf}_烛火线V221027",
    opcode = "JccZhuHuoXianV221027",
    param_kind = "JccZhuHuoXianV221027"
)]
pub fn jcc_zhu_huo_xian_v221027(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_f64_param(params, "th", 2.0);
    let zf = get_usize_param(params, "zf", 500) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}T{}F{}", di, py_float_str(th), zf as i32);
    let k3 = "烛火线";

    if di == 0 || di > c.bars_raw.len() {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }

    let bar = &c.bars_raw[c.bars_raw.len() - di];
    let x1 = bar.high - bar.open.max(bar.close);
    let x2 = (bar.close - bar.open).abs();
    let x3 = bar.open.min(bar.close) - bar.low;
    let zf_min = if bar.low != 0.0 {
        (bar.high - bar.low) / bar.low * 10000.0 >= zf
    } else {
        false
    };

    let v1 = if x1 > x2 * th / 100.0 && x3 < 0.2 * x2 && x3 < 0.5 * x1 && zf_min {
        "满足"
    } else {
        "其他"
    };

    let mut v2 = "其他";
    if c.bars_raw.len() > 20 + di {
        let left_bars = get_sub_elements(&c.bars_raw, di, 20);
        if !left_bars.is_empty() {
            let left_max = left_bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max);
            let left_min = left_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
            let gap = left_max - left_min;
            if bar.low <= left_min + 0.25 * gap {
                v2 = "箭在弦";
            } else if bar.high >= left_max - 0.25 * gap {
                v2 = "风中烛";
            }
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_yun_xian_V221118：孕线形态
///
/// 参数模板：`"{freq}_D{di}_孕线"`
///
/// 信号逻辑：
/// 1. 前一根为长实体，当前为小实体；
/// 2. 当前开收位于前一根实体区间内；
/// 3. 方向反转判 `看多/看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1_孕线_看多_任意_任意_0')`
/// - `Signal('60分钟_D1_孕线_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `jcc_yun_xian_V221118` 一致。
#[signal(
    category = "kline",
    name = "jcc_yun_xian_V221118",
    template = "{freq}_D{di}_孕线V221118",
    opcode = "JccYunXianV221118",
    param_kind = "JccYunXianV221118"
)]
pub fn jcc_yun_xian_v221118(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}", di);
    let k3 = "孕线";

    let bars = get_sub_elements(&c.bars_raw, di, 2);
    if bars.len() != 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bar2 = &bars[0];
    let bar1 = &bars[1];

    let mut v1 = "其他";
    if solid(bar2) > upper(bar2).max(lower(bar2)) && solid(bar1) < upper(bar1).max(lower(bar1)) {
        if bar2.close > bar1.close
            && bar1.close > bar2.open
            && bar2.close > bar1.open
            && bar1.open > bar2.open
        {
            v1 = "看空";
        }
        if bar2.close < bar1.close
            && bar1.close < bar2.open
            && bar2.close < bar1.open
            && bar1.open < bar2.open
        {
            v1 = "看多";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// jcc_ping_tou_V221113：平头形态
///
/// 参数模板：`"{freq}_D{di}TH{th}_平头形态"`
///
/// 信号逻辑：
/// 1. 对比两根K线高点或低点差值比例，识别 `顶部/底部`；
/// 2. 实体条件满足时给出 `实体标准` 标签；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D2TH100_平头形态_顶部_实体标准_任意_0')`
/// - `Signal('15分钟_D2TH100_平头形态_底部_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `2`；
/// - `th`：高低点容差阈值（BP），默认 `100`。
/// 对齐说明：与 Python `jcc_ping_tou_V221113` 一致。
#[signal(
    category = "kline",
    name = "jcc_ping_tou_V221113",
    template = "{freq}_D{di}TH{th}_平头形态V221113",
    opcode = "JccPingTouV221113",
    param_kind = "JccPingTouV221113"
)]
pub fn jcc_ping_tou_v221113(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 2);
    let th = get_usize_param(params, "th", 100) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TH{}", di, th as i32);
    let k3 = "平头形态";

    let bars = get_sub_elements(&c.bars_raw, di, 2);
    if bars.len() != 2 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }
    let bar2 = &bars[0];
    let bar1 = &bars[1];

    let v1 = if (bar2.low - bar1.low).abs() * 10000.0 / bar2.low.max(bar1.low) < th {
        "底部"
    } else if (bar2.high - bar1.high).abs() * 10000.0 / bar2.high.max(bar1.high) < th {
        "顶部"
    } else {
        "其他"
    };

    let v2 = if solid(bar2) > solid(bar1).max(upper(bar1)) {
        "实体标准"
    } else {
        "任意"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_two_crow_V221108：两只乌鸦
///
/// 参数模板：`"{freq}_D{di}K_两只乌鸦"`
///
/// 信号逻辑：
/// 1. 第一根长阳；
/// 2. 第二根高开低走且收在第一根高点之上；
/// 3. 第三根阴线继续下压，判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K_两只乌鸦_看空_任意_任意_0')`
/// - `Signal('60分钟_D1K_两只乌鸦_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `jcc_two_crow_V221108` 一致。
#[signal(
    category = "kline",
    name = "jcc_two_crow_V221108",
    template = "{freq}_D{di}K_两只乌鸦V221108",
    opcode = "JccTwoCrowV221108",
    param_kind = "JccTwoCrowV221108"
)]
pub fn jcc_two_crow_v221108(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "两只乌鸦";

    let bars = get_sub_elements(&c.bars_raw, di, 3);
    if bars.len() != 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bar3 = &bars[0];
    let bar2 = &bars[1];
    let bar1 = &bars[2];

    let c1 = bar3.close > bar3.open && solid(bar3) > upper(bar3).max(lower(bar3));
    let c2 = bar2.open > bar2.close && bar2.close > bar3.high;
    let c3 = bar1.close < bar1.open && bar1.close < bar2.close;
    let v1 = if c1 && c2 && c3 { "看空" } else { "其他" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// jcc_three_crow_V221108：三只乌鸦
///
/// 参数模板：`"{freq}_D{di}_三只乌鸦"`
///
/// 信号逻辑：
/// 1. 三根连续阴线且高低收盘递降；
/// 2. 影线和实体关系满足强空形态；
/// 3. 根据开盘关系细分 `常规/加强/半加强`。
///
/// 信号列表示例：
/// - `Signal('30分钟_D1_三只乌鸦_满足_常规_任意_0')`
/// - `Signal('30分钟_D1_三只乌鸦_满足_加强_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `jcc_three_crow_V221108` 一致。
#[signal(
    category = "kline",
    name = "jcc_three_crow_V221108",
    template = "{freq}_D{di}_三只乌鸦V221108",
    opcode = "JccThreeCrowV221108",
    param_kind = "JccThreeCrowV221108"
)]
pub fn jcc_three_crow_v221108(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}", di);
    let k3 = "三只乌鸦";

    if c.bars_raw.len() < di + 2 || di == 0 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }

    let bar1 = &c.bars_raw[c.bars_raw.len() - di];
    let bar2 = &c.bars_raw[c.bars_raw.len() - di - 1];
    let bar3 = &c.bars_raw[c.bars_raw.len() - di - 2];

    if c.bars_raw.len() > 23 {
        let left_bars = get_sub_elements(&c.bars_raw, 3, 20);
        if !left_bars.is_empty() {
            let left_max = left_bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max);
            let left_min = left_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
            let gap = left_max - left_min;
            if bar3.high < left_max - 0.25 * gap {
                return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
            }
            let _ = left_min;
        }
    }

    let mut v1 = "其他";
    let mut v2 = "其他";
    if bar1.close < bar1.open
        && bar2.close < bar2.open
        && bar3.open > bar3.close
        && bar3.close > bar2.close
        && bar2.close > bar1.close
        && bar3.high > bar2.high
        && bar2.high > bar1.high
    {
        let c_low = (bar1.close - bar1.low) < 0.5 * (bar1.open - bar1.close)
            && (bar2.close - bar2.low) < 0.5 * (bar2.open - bar2.close)
            && (bar3.close - bar3.low) < 0.5 * (bar3.open - bar3.close);
        let c_up = (bar1.high - bar1.open) < (bar1.open - bar1.close)
            && (bar2.high - bar2.open) < (bar2.open - bar2.close)
            && (bar3.high - bar3.open) < (bar3.open - bar3.close);
        if c_low && c_up {
            if bar2.close <= bar1.open
                && bar1.open <= bar2.open
                && bar3.close <= bar2.open
                && bar2.open <= bar3.open
            {
                v1 = "满足";
                v2 = "常规";
            } else if bar1.open < bar2.close && bar2.open < bar3.close {
                v1 = "满足";
                v2 = "加强";
            } else if (bar2.close <= bar1.open
                && bar1.open <= bar2.open
                && bar3.open < bar3.close)
                || (bar3.close <= bar2.open && bar2.open <= bar3.open && bar1.open < bar2.close)
            {
                v1 = "满足";
                v2 = "半加强";
            }
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_szx_V221111：十字线
///
/// 参数模板：`"{freq}_D{di}TH{th}_十字线"`
///
/// 信号逻辑：
/// 1. `(high-low)/|close-open| > th` 或 `close==open` 判十字线；
/// 2. 按上下影长度细分 `蜻蜓/墓碑/长腿/十字线`；
/// 3. 前一根强阳时追加 `北方`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1TH10_十字线_蜻蜓十字线_北方_任意_0')`
/// - `Signal('60分钟_D1TH10_十字线_墓碑十字线_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `th`：十字线阈值，默认 `10`。
/// 对齐说明：与 Python `jcc_szx_V221111` 一致。
#[signal(
    category = "kline",
    name = "jcc_szx_V221111",
    template = "{freq}_D{di}TH{th}_十字线V221111",
    opcode = "JccSzxV221111",
    param_kind = "JccSzxV221111"
)]
pub fn jcc_szx_v221111(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 10) as i32;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TH{}", di, th);
    let k3 = "十字线";

    if c.bars_raw.len() < di + 10 || di == 0 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, 2);
    if bars.len() != 2 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let bar2 = &bars[0];
    let bar1 = &bars[1];

    let v1 = if check_szx(bar1, th) {
        let upper = upper(bar1);
        let body = solid(bar1);
        let lower = lower(bar1);
        if lower > upper * 2.0 {
            "蜻蜓十字线"
        } else if lower == 0.0 || lower < body {
            "墓碑十字线"
        } else if lower > solid(bar2) && upper > solid(bar2) {
            "长腿十字线"
        } else {
            "十字线"
        }
    } else {
        "其他"
    };

    let v2 = if bar2.close > bar2.open && solid(bar2) > (upper(bar2) + lower(bar2)) * 3.0 {
        "北方"
    } else {
        "任意"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_san_szx_V221122：三星形态
///
/// 参数模板：`"{freq}_D{di}T{th}_三星"`
///
/// 信号逻辑：
/// 1. 取最近5根K线；
/// 2. 统计十字线数量；
/// 3. 不少于3根判 `满足`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1T10_三星_满足_任意_任意_0')`
/// - `Signal('15分钟_D1T10_三星_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `th`：十字线阈值，默认 `10`。
/// 对齐说明：与 Python `jcc_san_szx_V221122` 一致。
#[signal(
    category = "kline",
    name = "jcc_san_szx_V221122",
    template = "{freq}_D{di}T{th}_三星V221122",
    opcode = "JccSanSzxV221122",
    param_kind = "JccSanSzxV221122"
)]
pub fn jcc_san_szx_v221122(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 10) as i32;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}T{}", di, th);
    let k3 = "三星";

    let mut v1 = "其他";
    if c.bars_raw.len() > 6 + di {
        let bars = get_sub_elements(&c.bars_raw, di, 5);
        let cnt = bars.iter().filter(|b| check_szx(b, th)).count();
        if cnt >= 3 {
            v1 = "满足";
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// jcc_fan_ji_xian_V221121：反击线
///
/// 参数模板：`"{freq}_D{di}_反击线"`
///
/// 信号逻辑：
/// 1. 最近20根内检测收盘接近、跳空幅度和实体强度；
/// 2. 满足基础条件后，按区间位置和方向细分 `看涨反击线/看跌反击线`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1_反击线_满足_看涨反击线_任意_0')`
/// - `Signal('15分钟_D1_反击线_满足_看跌反击线_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `jcc_fan_ji_xian_V221121` 一致。
#[signal(
    category = "kline",
    name = "jcc_fan_ji_xian_V221121",
    template = "{freq}_D{di}_反击线V221121",
    opcode = "JccFanJiXianV221121",
    param_kind = "JccFanJiXianV221121"
)]
pub fn jcc_fan_ji_xian_v221121(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}", di);
    let k3 = "反击线";

    if c.bars_raw.len() < 20 + di {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }

    let left_bars = get_sub_elements(&c.bars_raw, di, 20);
    if left_bars.len() < 3 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }
    let left_max = left_bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let left_min = left_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let gap = left_max - left_min;

    let bar1 = &left_bars[left_bars.len() - 3];
    let bar2 = &left_bars[left_bars.len() - 2];
    let bar3 = &left_bars[left_bars.len() - 1];

    let mut v1 = "其他";
    if bar2.close != bar2.open {
        let bar2h = (bar2.close - bar2.open).abs();
        let x1 = (bar3.open - bar2.close).abs() / bar2h;
        let x2 = (bar3.close - bar2.close).abs() / bar2h;
        let x3 = bar2h / gap;
        if x1 >= 1.0 && x2 <= 0.1 && x3 >= 0.02 {
            v1 = "满足";
        }
    }

    let mut v2 = "任意";
    if v1 == "满足" {
        if bar1.low <= left_min + 0.25 * gap
            && bar1.close > bar2.close
            && bar2.open > bar2.close
            && bar2.close > bar3.open
        {
            v2 = "看涨反击线";
        } else if bar1.high >= left_max - 0.25 * gap
            && bar2.close > bar1.close
            && bar3.open > bar2.close
            && bar2.close > bar2.open
        {
            v2 = "看跌反击线";
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// jcc_shan_chun_V221121：山川形态
///
/// 参数模板：`"{freq}_D{di}B_山川形态"`
///
/// 信号逻辑：
/// 1. 取最近5笔；
/// 2. 末笔向上且 `5/3/1` 笔高点方差小，判 `三山`；
/// 3. 末笔向下且 `5/3/1` 笔低点方差小，判 `三川`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1B_山川形态_三山_任意_任意_0')`
/// - `Signal('15分钟_D1B_山川形态_三川_任意_任意_0')`
///
/// 参数说明：
/// - `di`：截止倒数第 `di` 笔，默认 `1`。
/// 对齐说明：方差阈值与 Python `jcc_shan_chun_V221121` 一致。
#[signal(
    category = "kline",
    name = "jcc_shan_chun_V221121",
    template = "{freq}_D{di}B_山川形态V221121",
    opcode = "JccShanChunV221121",
    param_kind = "JccShanChunV221121"
)]
pub fn jcc_shan_chun_v221121(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}B", di);
    let k3 = "山川形态";

    let mut v1 = "其他";
    if c.bi_list.len() >= 6 + di {
        let bis = get_sub_elements(&c.bi_list, di, 5);
        if bis.len() == 5 {
            let b5 = &bis[0];
            let b3 = &bis[2];
            let b1 = &bis[4];
            if matches!(b1.direction, Direction::Up)
                && variance(&[b5.get_high(), b3.get_high(), b1.get_high()]) < 0.2
            {
                v1 = "三山";
            }
            if matches!(b1.direction, Direction::Down)
                && variance(&[b5.get_low(), b3.get_low(), b1.get_low()]) < 0.2
            {
                v1 = "三川";
            }
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// jcc_gap_yin_yang_V221121：跳空并列阴阳
///
/// 参数模板：`"{freq}_D{di}K_并列阴阳"`
///
/// 信号逻辑：
/// 1. 最近三根满足跳空窗口；
/// 2. 两根并列阴阳实体方差小于阈值；
/// 3. 判定 `向上跳空/向下跳空`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1K_并列阴阳_向上跳空_任意_任意_0')`
/// - `Signal('15分钟_D1K_并列阴阳_向下跳空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `jcc_gap_yin_yang_V221121` 一致。
#[signal(
    category = "kline",
    name = "jcc_gap_yin_yang_V221121",
    template = "{freq}_D{di}K_并列阴阳V221121",
    opcode = "JccGapYinYangV221121",
    param_kind = "JccGapYinYangV221121"
)]
pub fn jcc_gap_yin_yang_v221121(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "并列阴阳";

    let mut v1 = "其他";
    if c.bars_raw.len() > di + 5 {
        let bars = get_sub_elements(&c.bars_raw, di, 3);
        if bars.len() == 3 {
            let bar3 = &bars[0];
            let bar2 = &bars[1];
            let bar1 = &bars[2];

            if bar1.low.min(bar2.low) > bar3.high
                && bar2.close > bar2.open
                && bar1.close < bar1.open
                && variance(&[solid(bar1), solid(bar2)]) < 0.2
            {
                v1 = "向上跳空";
            } else if bar1.high.max(bar2.high) < bar3.low
                && bar2.close < bar2.open
                && bar1.close > bar1.open
                && variance(&[solid(bar1), solid(bar2)]) < 0.2
            {
                v1 = "向下跳空";
            }
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// jcc_ta_xing_V221124：塔形顶底
///
/// 参数模板：`"{freq}_D{di}K_塔形"`
///
/// 信号逻辑：
/// 1. 在 5~9 根窗口内扫描；
/// 2. 首尾实体最大且中间高低点聚集；
/// 3. 判定 `顶部/底部`，并返回窗口长度。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1K_塔形_顶部_6K_任意_0')`
/// - `Signal('15分钟_D1K_塔形_底部_8K_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `jcc_ta_xing_V221124` 一致。
#[signal(
    category = "kline",
    name = "jcc_ta_xing_V221124",
    template = "{freq}_D{di}K_塔形V221124",
    opcode = "JccTaXingV221124",
    param_kind = "JccTaXingV221124"
)]
pub fn jcc_ta_xing_v221124(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "塔形";

    let check = |bars: &[RawBar]| -> &'static str {
        if bars.len() < 5 {
            return "其他";
        }
        let rb = &bars[0];
        let lb = bars.last().unwrap();
        let mut solids: Vec<f64> = bars.iter().map(solid).collect();
        solids.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        if solid(rb).min(solid(lb)) >= solids[solids.len() - 2] {
            let mid = &bars[1..bars.len() - 1];
            let g_c1 = rb.close > rb.open && lb.close < lb.open;
            let g_c2 = variance(&mid.iter().map(|x| x.high).collect::<Vec<_>>()) < 0.5;
            let g_c3 = mid.iter().all(|x| x.low > rb.open.max(lb.close));
            if g_c1 && g_c2 && g_c3 {
                return "顶部";
            }

            let d_c1 = rb.close < rb.open && lb.close > lb.open;
            let d_c2 = variance(&mid.iter().map(|x| x.low).collect::<Vec<_>>()) < 0.5;
            let d_c3 = mid.iter().all(|x| x.high < rb.open.min(lb.close));
            if d_c1 && d_c2 && d_c3 {
                return "底部";
            }
        }
        "其他"
    };

    let mut v1 = "其他";
    let mut v2 = "其他";
    for n in [5usize, 6, 7, 8, 9] {
        let bars = get_sub_elements(&c.bars_raw, di, n);
        let t = check(bars);
        if t != "其他" {
            v1 = t;
            v2 = if n == 5 {
                "5K"
            } else if n == 6 {
                "6K"
            } else if n == 7 {
                "7K"
            } else if n == 8 {
                "8K"
            } else {
                "9K"
            };
            break;
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}
