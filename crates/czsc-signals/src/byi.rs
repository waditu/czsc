use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{
    get_sub_elements, make_kline_signal_v1, make_kline_signal_v2, make_kline_signal_v3,
};
use crate::utils::ta::update_macd_cache;
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::bi::BI;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::fx::FX;
use czsc_core::objects::mark::Mark;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::zs::ZS;
use czsc_signal_macros::signal;
use std::collections::HashMap;

fn fx_raw_bars(fx: &FX) -> Vec<RawBar> {
    fx.elements
        .iter()
        .flat_map(|nb| nb.elements.iter().cloned())
        .collect()
}

fn raw_bar_solid(bar: &RawBar) -> f64 {
    (bar.open - bar.close).abs()
}

fn raw_bar_upper(bar: &RawBar) -> f64 {
    bar.high - bar.open.max(bar.close)
}

fn raw_bar_lower(bar: &RawBar) -> f64 {
    bar.open.min(bar.close) - bar.low
}

fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        f64::NAN
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

fn std_pop(values: &[f64]) -> f64 {
    let m = mean(values);
    if !m.is_finite() || values.is_empty() {
        return f64::NAN;
    }
    let var = values.iter().map(|x| (x - m).powi(2)).sum::<f64>() / values.len() as f64;
    var.sqrt()
}

fn is_symmetry_zs(bis: &[BI], th: f64) -> bool {
    if bis.len().is_multiple_of(2) {
        return false;
    }
    let zs = ZS::new(bis.to_vec());
    if zs.zd > zs.zg {
        return false;
    }
    let max_low = bis.iter().map(|x| x.get_low()).fold(f64::NEG_INFINITY, f64::max);
    let min_high = bis.iter().map(|x| x.get_high()).fold(f64::INFINITY, f64::min);
    if max_low > min_high {
        return false;
    }
    let zns: Vec<f64> = bis.iter().map(|x| x.get_power_price()).collect();
    let m = mean(&zns);
    let s = std_pop(&zns);
    m.is_finite() && s.is_finite() && m != 0.0 && s / m <= th
}

/// byi_symmetry_zs_V221107：对称中枢识别信号
///
/// 参数模板：`"{freq}_D{di}B_对称中枢"`
///
/// 信号逻辑：
/// 1. 取倒数 `di` 截止最近 10 笔；
/// 2. 依次检查最近 `7/5/3` 笔是否构成对称中枢；
/// 3. 命中则输出 `是 + {i}笔`，否则 `否 + 任意`；
/// 4. 方向位按最后一笔反向映射（最后笔向下 -> `向上`）。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1B_对称中枢_是_向上_7笔_0')`
/// - `Signal('60分钟_D1B_对称中枢_否_向下_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始，默认 `1`。
/// 对齐说明：与 Python `byi_symmetry_zs_V221107` 的 7/5/3 笔判定序一致。
#[signal(
    category = "kline",
    name = "byi_symmetry_zs_V221107",
    template = "{freq}_D{di}B_对称中枢V221107",
    opcode = "ByiSymmetryZsV221107",
    param_kind = "ByiSymmetryZsV221107"
)]
pub fn byi_symmetry_zs_v221107(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let bis = get_sub_elements(&c.bi_list, di, 10);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}B", di);
    let k3 = "对称中枢";
    if bis.len() < 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut ok = false;
    let mut v3 = "任意".to_string();
    for i in [7usize, 5, 3] {
        ok = is_symmetry_zs(&bis[bis.len() - i..], 0.3);
        if ok {
            v3 = format!("{}笔", i);
            break;
        }
    }
    let v1 = if ok { "是" } else { "否" };
    let v2 = if bis[bis.len() - 1].direction == Direction::Down {
        "向上"
    } else {
        "向下"
    };
    make_kline_signal_v3(&k1, &k2, k3, v1, v2, &v3)
}

/// byi_bi_end_V230106：分型停顿辅助笔结束信号
///
/// 参数模板：`"{freq}_D0停顿分型_BE辅助V230106"`
///
/// 信号逻辑：
/// 1. 基于最后一笔方向与末端分型，判断停顿分型是否成立；
/// 2. 满足底分型停顿给出 `看多`，满足顶分型停顿给出 `看空`；
/// 3. 再按最后一根K线实体强弱输出 `强/弱`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0停顿分型_BE辅助V230106_看多_强_任意_0')`
/// - `Signal('60分钟_D0停顿分型_BE辅助V230106_看空_弱_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空。
/// 对齐说明：与 Python `byi_bi_end_V230106` 的停顿判定条件一致。
#[signal(
    category = "kline",
    name = "byi_bi_end_V230106",
    template = "{freq}_D0停顿分型_BE辅助V230106",
    opcode = "ByiBiEndV230106",
    param_kind = "ByiBiEndV230106"
)]
pub fn byi_bi_end_v230106(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "D0停顿分型";
    let k3 = "BE辅助V230106";
    if c.bi_list.len() < 3 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, 3);
    if bars.len() < 3 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_bi = &c.bi_list[c.bi_list.len() - 1];
    let last_fx = &last_bi.fx_b;
    let bar1 = &bars[0];
    let bar3 = &bars[2];
    let fx_raw = fx_raw_bars(last_fx);
    if fx_raw.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }

    let lc1 = last_bi.direction == Direction::Down && last_fx.mark == Mark::D && bar1.low == last_fx.low;
    if lc1 {
        let fx_high = fx_raw.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
        if bar3.close > fx_high {
            let v2 = if bar3.close > bar3.open
                && raw_bar_solid(bar3) > raw_bar_upper(bar3).max(raw_bar_lower(bar3))
            {
                "强"
            } else {
                "弱"
            };
            return make_kline_signal_v2(&k1, k2, k3, "看多", v2);
        }
    }

    let sc1 = last_bi.direction == Direction::Up && last_fx.mark == Mark::G && bar1.high == last_fx.high;
    if sc1 {
        let fx_low = fx_raw.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
        if bar3.close < fx_low {
            let v2 = if bar3.close < bar3.open
                && raw_bar_solid(bar3) > raw_bar_upper(bar3).max(raw_bar_lower(bar3))
            {
                "强"
            } else {
                "弱"
            };
            return make_kline_signal_v2(&k1, k2, k3, "看空", v2);
        }
    }
    make_kline_signal_v1(&k1, k2, k3, "其他")
}

/// byi_bi_end_V230107：验证分型辅助笔结束信号
///
/// 参数模板：`"{freq}_D0验证分型_BE辅助V230107"`
///
/// 信号逻辑：
/// 1. 校验最后一笔末端分型与末三分型结构关系；
/// 2. 满足验证底分型给出 `看多`，验证顶分型给出 `看空`；
/// 3. 依据最后一根K线实体强弱输出 `强/弱`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0验证分型_BE辅助V230107_看多_强_任意_0')`
/// - `Signal('60分钟_D0验证分型_BE辅助V230107_看空_弱_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空。
/// 对齐说明：与 Python `byi_bi_end_V230107` 的结构校验和强弱规则一致。
#[signal(
    category = "kline",
    name = "byi_bi_end_V230107",
    template = "{freq}_D0验证分型_BE辅助V230107",
    opcode = "ByiBiEndV230107",
    param_kind = "ByiBiEndV230107"
)]
pub fn byi_bi_end_v230107(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "D0验证分型";
    let k3 = "BE辅助V230107";
    if c.bi_list.len() < 3 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let fxs = c.get_fx_list();
    if fxs.len() < 3 || c.bars_raw.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_bi = &c.bi_list[c.bi_list.len() - 1];
    let fx1 = &fxs[fxs.len() - 3];
    let fx2 = &fxs[fxs.len() - 2];
    let fx3 = &fxs[fxs.len() - 1];
    let bar1 = &c.bars_raw[c.bars_raw.len() - 1];
    let fx3_raw = fx_raw_bars(fx3);
    if fx3_raw.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    if !(last_bi.fx_b.dt == fx1.dt && fx1.mark == fx3.mark && bar1.dt == fx3_raw[fx3_raw.len() - 1].dt) {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }

    let mut close_seq = Vec::new();
    close_seq.extend(
        fx_raw_bars(fx1).into_iter().map(|x| x.close),
    );
    close_seq.extend(fx_raw_bars(fx2).into_iter().map(|x| x.close));
    if close_seq.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let high_c = close_seq.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let low_c = close_seq.iter().copied().fold(f64::INFINITY, f64::min);

    let lc1 = raw_bar_solid(bar1) > raw_bar_upper(bar1).max(raw_bar_lower(bar1))
        && bar1.close > bar1.open
        && bar1.close > high_c;
    if last_bi.direction == Direction::Down && fx1.mark == Mark::D && fx3.low > fx1.low {
        let v2 = if lc1 { "强" } else { "弱" };
        return make_kline_signal_v2(&k1, k2, k3, "看多", v2);
    }

    let sc1 = raw_bar_solid(bar1) > raw_bar_upper(bar1).max(raw_bar_lower(bar1))
        && bar1.close < bar1.open
        && bar1.close < low_c;
    if last_bi.direction == Direction::Up && fx1.mark == Mark::G && fx3.high < fx1.high {
        let v2 = if sc1 { "强" } else { "弱" };
        return make_kline_signal_v2(&k1, k2, k3, "看空", v2);
    }
    make_kline_signal_v1(&k1, k2, k3, "其他")
}

/// byi_second_bs_V230324：二类买卖点辅助信号
///
/// 参数模板：`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}回抽零轴_BS2辅助V230324"`
///
/// 信号逻辑：
/// 1. 基于最近 9 笔关键分型的 DIF 值和标准差构造条件；
/// 2. 满足向下笔回抽零轴条件判 `看多`；
/// 3. 满足向上笔回抽零轴条件判 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MACD12#26#9回抽零轴_BS2辅助V230324_看多_任意_任意_0')`
/// - `Signal('60分钟_D1MACD12#26#9回抽零轴_BS2辅助V230324_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始检查，默认 `1`；
/// - `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。
/// 对齐说明：按 Python `byi_second_bs_V230324` 的 DIF 取样点和不等式链实现。
#[signal(
    category = "kline",
    name = "byi_second_bs_V230324",
    template = "{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}回抽零轴_BS2辅助V230324",
    opcode = "ByiSecondBsV230324",
    param_kind = "ByiSecondBsV230324"
)]
pub fn byi_second_bs_v230324(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let fast = params.usize("fastperiod", 12);
    let slow = params.usize("slowperiod", 26);
    let signalperiod = params.usize("signalperiod", 9);
    let cache_key = format!("MACD{}#{}#{}", fast, slow, signalperiod);
    update_macd_cache(c, &cache_key, fast, slow, signalperiod, cache);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}{}回抽零轴", di, cache_key);
    let k3 = "BS2辅助V230324";
    if c.bi_list.len() < di + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 9);
    if bis.len() < 9 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let b1 = &bis[0];
    let b3 = &bis[2];
    let b5 = &bis[4];
    let b8 = &bis[7];
    let b9 = &bis[8];

    let macd = match cache.macd.get(&cache_key) {
        Some(m) => m,
        None => return make_kline_signal_v1(&k1, &k2, k3, "其他"),
    };
    let id_to_idx: HashMap<i32, usize> = macd
        .ids
        .iter()
        .enumerate()
        .map(|(i, id)| (*id, i))
        .collect();
    let dif_at = |id: i32| -> f64 {
        id_to_idx
            .get(&id)
            .and_then(|i| macd.dif.get(*i))
            .copied()
            .unwrap_or(f64::NAN)
    };
    let fx_mid_id = |bi: &BI| -> Option<i32> {
        let rb = fx_raw_bars(&bi.fx_b);
        if rb.len() > 1 { Some(rb[1].id) } else { None }
    };

    let b1_dif = fx_mid_id(b1).map(dif_at).unwrap_or(f64::NAN);
    let b3_dif = fx_mid_id(b3).map(dif_at).unwrap_or(f64::NAN);
    let b5_dif = fx_mid_id(b5).map(dif_at).unwrap_or(f64::NAN);
    let b8_dif = fx_mid_id(b8).map(dif_at).unwrap_or(f64::NAN);
    let b9_dif = fx_mid_id(b9).map(dif_at).unwrap_or(f64::NAN);
    let b1_raw = b1.get_raw_bars();
    let dif_seq: Vec<f64> = b1_raw.iter().map(|x| dif_at(x.id)).collect();
    let dif_std = std_pop(&dif_seq);

    let mut v1 = "其他";
    if b9.direction == Direction::Down
        && b1_dif.max(b3_dif).max(b5_dif) < 0.0
        && b1_dif.min(b3_dif).min(b5_dif) < -2.0 * dif_std
        && b8_dif > dif_std
        && b9_dif.abs() < 0.3 * dif_std
    {
        v1 = "看多";
    }
    if b9.direction == Direction::Up
        && b1_dif.min(b3_dif).min(b5_dif) > 0.0
        && b1_dif.max(b3_dif).max(b5_dif) > 2.0 * dif_std
        && b8_dif < -dif_std
        && b9_dif.abs() < 0.3 * dif_std
    {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// byi_fx_num_V230628：前笔分型数量约束信号
///
/// 参数模板：`"{freq}_D{di}笔分型数大于{num}_BE辅助V230628"`
///
/// 信号逻辑：
/// 1. 取倒数第 `di` 笔；
/// 2. 输出该笔方向（`向上/向下`）；
/// 3. 若该笔内部分型数量 `>= num` 记 `满足`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1笔分型数大于4_BE辅助V230628_向下_满足_任意_0')`
/// - `Signal('60分钟_D1笔分型数大于4_BE辅助V230628_向上_其他_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始检查，默认 `1`；
/// - `num`：分型数量阈值，默认 `4`。
/// 对齐说明：与 Python `byi_fx_num_V230628` 的数量判断一致。
#[signal(
    category = "kline",
    name = "byi_fx_num_V230628",
    template = "{freq}_D{di}笔分型数大于{num}_BE辅助V230628",
    opcode = "ByiFxNumV230628",
    param_kind = "ByiFxNumV230628"
)]
pub fn byi_fx_num_v230628(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let num = params.usize("num", 4);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}笔分型数大于{}", di, num);
    let k3 = "BE辅助V230628";
    if c.bi_list.len() < di + 1 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bi = &c.bi_list[c.bi_list.len() - di];
    let v1 = bi.direction.to_string();
    let v2 = if bi.fxs.len() >= num { "满足" } else { "其他" };
    make_kline_signal_v2(&k1, &k2, k3, &v1, v2)
}
