use crate::types::TaCache;
use crate::params::ParamView;
use crate::utils::cxt::{
    calc_bi_status_values, check_first_buy, check_first_sell, fx_has_zs, fx_power_str,
    fx_raw_bars, get_zs_seq, raw_bar_lower, raw_bar_upper, rebuild_ubi, ubi_raw_bars,
    unique_prices_from_bars,
};
use crate::utils::math::{linreg_predict, max_amplitude_pct, mean, overlap};
use crate::utils::sig::{
    bar_index_map, get_sub_elements, get_usize_param, make_kline_signal_v1, make_kline_signal_v2,
    qcut_last_label,
};
use crate::utils::ta::{
    ma_snapshot_value, macd_snapshot_field_value, update_ma_cache, update_macd_cache, MacdField,
};
use czsc_signal_macros::signal;
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::bi::BI;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::fx::FX;
use czsc_core::objects::mark::Mark;
use czsc_core::objects::signal::Signal;
use std::collections::HashMap;

/// cxt_bi_base_V230228：笔基础状态信号
///
/// 参数模板：`"{freq}_D0BL{bi_init_length}_V230228"`
///
/// 信号逻辑：
/// 1. 读取最新一笔方向；
/// 2. 若最新笔为向下笔，当前状态记为 `向上`，反之记为 `向下`；
/// 3. 若未完成笔长度 `bars_ubi` 大于等于 `bi_init_length`，记为 `中继`，否则记为 `转折`；
/// 4. 笔数据不足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0BL9_V230228_向上_中继_任意_0')`
/// - `Signal('60分钟_D0BL9_V230228_向下_转折_任意_0')`
/// - `Signal('60分钟_D0BL9_V230228_其他_任意_任意_0')`
///
/// 参数说明：
/// - `bi_init_length`：未完成笔长度阈值，默认 `9`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_base_V230228` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_base_V230228",
    template = "{freq}_D0BL{bi_init_length}_V230228",
    opcode = "CxtBiBaseV230228",
    param_kind = "CxtBiBase"
)]
pub fn cxt_bi_base_v230228(
    czsc: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let bi_init_length = params.usize("bi_init_length", 9);

    let k1 = czsc.freq.to_string();
    let k2 = format!("D0BL{}", bi_init_length);
    let k3 = "V230228";

    if czsc.bi_list.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let last_bi = czsc.bi_list.last().unwrap();
    let v1 = match last_bi.direction {
        Direction::Down => "向上",
        Direction::Up => "向下",
    };

    let v2 = if czsc.bars_ubi.len() >= bi_init_length {
        "中继"
    } else {
        "转折"
    };

    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// cxt_bi_status_V230101：笔表里关系信号
///
/// 参数模板：`"{freq}_D1_表里关系V230101"`
///
/// 信号逻辑：
/// 1. 依据最后一笔方向和 `bars_ubi` 长度判定外部方向（`向上/向下`）；
/// 2. 结合未完成笔最后一个分型（顶分/底分）判定内部状态（`顶分/底分/延伸`）；
/// 3. 笔或分型数据不足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1_表里关系V230101_向上_顶分_任意_0')`
/// - `Signal('60分钟_D1_表里关系V230101_向下_底分_任意_0')`
/// - `Signal('60分钟_D1_表里关系V230101_向上_延伸_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_status_V230101` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_status_V230101",
    template = "{freq}_D1_表里关系V230101",
    opcode = "CxtBiStatusV230101",
    param_kind = "CxtBiStatus"
)]
pub fn cxt_bi_status_v230101(
    czsc: &CZSC,
    _params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let k1 = czsc.freq.to_string();
    let k2 = "D1";
    let k3 = "表里关系V230101";

    // 对齐 Python:
    // if len(c.bi_list) < 3 or len(fxs) < 1: v1 = "其他"
    let Some(ubi_fxs) = czsc.get_ubi_fxs() else {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    };

    if czsc.bi_list.len() < 3 || ubi_fxs.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }

    let (v1, v2) = calc_bi_status_values(czsc, &ubi_fxs);

    make_kline_signal_v2(&k1, k2, k3, v1, v2)
}

/// cxt_bi_status_V230102：笔表里关系信号
///
/// 参数模板：`"{freq}_D1_表里关系V230102"`
///
/// 信号逻辑：
/// 1. 沿用 `cxt_bi_status_V230101` 的表里方向和分型判定规则；
/// 2. 仅当最后一根原始K线时间等于最新 UBI 分型确认结束时间时触发；
/// 3. 不满足触发时机或数据不足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1_表里关系V230102_向下_底分_任意_0')`
/// - `Signal('60分钟_D1_表里关系V230102_向下_延伸_任意_0')`
/// - `Signal('60分钟_D1_表里关系V230102_向上_顶分_任意_0')`
/// - `Signal('60分钟_D1_表里关系V230102_向上_延伸_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_status_V230102` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_status_V230102",
    template = "{freq}_D1_表里关系V230102",
    opcode = "CxtBiStatusV230102",
    param_kind = "CxtBiStatus"
)]
pub fn cxt_bi_status_v230102(
    czsc: &CZSC,
    _params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let k1 = czsc.freq.to_string();
    let k2 = "D1";
    let k3 = "表里关系V230102";

    let Some(ubi_fxs) = czsc.get_ubi_fxs() else {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    };
    if czsc.bi_list.len() < 3 || ubi_fxs.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }

    let Some(last_bar_dt) = czsc.bars_raw.last().map(|x| x.dt) else {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    };
    let last_fx = ubi_fxs.last().unwrap();
    let Some(last_fx_end_dt) = last_fx
        .elements
        .last()
        .and_then(|nb| nb.elements.last().map(|rb| rb.dt))
        .or_else(|| last_fx.elements.last().map(|nb| nb.dt))
    else {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    };
    if last_bar_dt != last_fx_end_dt {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }

    let (v1, v2) = calc_bi_status_values(czsc, &ubi_fxs);
    make_kline_signal_v2(&k1, k2, k3, v1, v2)
}

/// cxt_fx_power_V221107：倒数分型强弱
///
/// 参数模板：`"{freq}_D{di}F_分型强弱V221107"`
///
/// 信号逻辑：
/// 1. 读取倒数第 `di` 个分型；
/// 2. `v1 = 分型强弱(power_str) + 顶/底`；
/// 3. `v2 = 有中枢/无中枢`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1F_分型强弱_强顶_有中枢_任意_0')`
/// - `Signal('60分钟_D2F_分型强弱_弱底_无中枢_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 个分型，默认 `1`；
/// - 仅当分型列表长度满足要求时输出具体强弱，否则返回 `其他`。
/// 对齐说明：与 Python `czsc.signals.cxt_fx_power_V221107` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_fx_power_V221107",
    template = "{freq}_D{di}F_分型强弱V221107",
    opcode = "CxtFxPowerV221107",
    param_kind = "CxtFxPowerV221107"
)]
pub fn cxt_fx_power_v221107(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}F", di);
    let k3 = "分型强弱";

    if di == 0 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let fxs = c.get_fx_list();
    if fxs.len() < di {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let last_fx = &fxs[fxs.len() - di];
    let mark = match last_fx.mark {
        Mark::G => "顶",
        Mark::D => "底",
    };
    let v1 = format!("{}{}", fx_power_str(last_fx), mark);
    let v2 = if fx_has_zs(last_fx) { "有中枢" } else { "无中枢" };
    make_kline_signal_v2(&k1, &k2, k3, &v1, v2)
}

/// cxt_bi_end_V230104：单均线辅助判断笔结束
///
/// 参数模板：`"{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230104"`
///
/// 信号逻辑：
/// 1. 计算指定均线，并取最近 3 根原始 K 线；
/// 2. 若向下笔尾部出现三连阳且收盘强于均线阈值，判定 `看多`；向上笔尾部三连阴且收盘弱于均线阈值，判定 `看空`；
/// 3. 不满足边界、均线或形态条件时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0SMA#5T50_BE辅助V230104_看多_任意_任意_0')`
/// - `Signal('60分钟_D0EMA#8T30_BE辅助V230104_看空_任意_任意_0')`
///
/// 参数说明：
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`；
/// - `th`：收盘价相对均线的 BP 阈值，默认 `50`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230104` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230104",
    template = "{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230104",
    opcode = "CxtBiEndV230104",
    param_kind = "CxtBiEndV230104"
)]
pub fn cxt_bi_end_v230104(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let th = get_usize_param(params, "th", 50) as f64;
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let cache_key = format!("{}#{}", ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let k1 = c.freq.to_string();
    let k2 = format!("D0{}#{}T{}", ma_type, timeperiod, th as i32);
    let k3 = "BE辅助V230104";
    let mut v1 = "其他";

    if c.bi_list.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bars = get_sub_elements(&c.bars_raw, 1, 3);
    if bars.len() != 3 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let id_to_idx = bar_index_map(c);
    let bar1 = &bars[0];
    let bar2 = &bars[1];
    let bar3 = &bars[2];
    let Some(&bar3_idx) = id_to_idx.get(&bar3.id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(bar3_ma) = ma.get(bar3_idx).copied() else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let last_bi = c.bi_list.last().unwrap();

    let lows_min = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let highs_max = bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);

    let lc1 = last_bi.direction == Direction::Down && lows_min == last_bi.get_low();
    let lc2 = bar1.close > bar1.open && bar2.close > bar2.open && bar3.close > bar3.open;
    let lc3 = bar3_ma * (1.0 + th / 10000.0) < bar3.close;
    if c.bars_ubi.len() < 7 && lc1 && lc2 && lc3 {
        v1 = "看多";
    }

    let sc1 = last_bi.direction == Direction::Up && highs_max == last_bi.get_high();
    let sc2 = bar1.close < bar1.open && bar2.close < bar2.open && bar3.close < bar3.open;
    let sc3 = bar3_ma * (1.0 - th / 10000.0) > bar3.close;
    if c.bars_ubi.len() < 7 && sc1 && sc2 && sc3 {
        v1 = "看空";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_bi_end_V230105：K线形态+均线辅助判断笔结束
///
/// 参数模板：`"{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230105"`
///
/// 信号逻辑：
/// 1. 提取最后一笔终点分型的两根原始 K 线，并计算指定均线；
/// 2. 向下笔若先阴后强阳上穿均线阈值，判定 `看多`；向上笔若先阳后强阴下破均线阈值，判定 `看空`；
/// 3. 未完成笔过长、分型样本不足或均线不可用时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0SMA#5T50_BE辅助V230105_看多_任意_任意_0')`
/// - `Signal('60分钟_D0EMA#8T30_BE辅助V230105_看空_任意_任意_0')`
///
/// 参数说明：
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`；
/// - `th`：第二根 K 线相对均线的突破阈值，默认 `50` BP。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230105` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230105",
    template = "{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230105",
    opcode = "CxtBiEndV230105",
    param_kind = "CxtBiEndV230105"
)]
pub fn cxt_bi_end_v230105(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let th = get_usize_param(params, "th", 50) as f64;
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let cache_key = format!("{}#{}", ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let k1 = c.freq.to_string();
    let k2 = format!("D0{}#{}T{}", ma_type, timeperiod, th as i32);
    let k3 = "BE辅助V230105";
    let mut v1 = "其他";

    if c.bi_list.len() < 3 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let id_to_idx = bar_index_map(c);
    let last_bi = c.bi_list.last().unwrap();
    let fx_raw = fx_raw_bars(&last_bi.fx_b);
    if fx_raw.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bar1 = &fx_raw[fx_raw.len() - 2];
    let bar2 = &fx_raw[fx_raw.len() - 1];
    let Some(&bar2_idx) = id_to_idx.get(&bar2.id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(bar2_ma) = ma.get(bar2_idx).copied() else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };

    let lc1 = last_bi.direction == Direction::Down && bar1.low == last_bi.get_low();
    let lc2 = bar1.close < bar1.open
        && bar2.close > bar2_ma * (1.0 + th / 10000.0)
        && bar2_ma * (1.0 + th / 10000.0) > bar2.open;
    if c.bars_ubi.len() < 7 && lc1 && lc2 {
        v1 = "看多";
    }

    let sc1 = last_bi.direction == Direction::Up && bar1.high == last_bi.get_high();
    let sc2 = bar1.close > bar1.open
        && bar2.close < bar2_ma * (1.0 - th / 10000.0)
        && bar2_ma * (1.0 - th / 10000.0) < bar2.open;
    if c.bars_ubi.len() < 7 && sc1 && sc2 {
        v1 = "看空";
    }

    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_bi_end_V230224：量价配合笔结束辅助
///
/// 参数模板：`"{freq}_D1_BE辅助V230224"`
///
/// 信号逻辑：
/// 1. 统计最后一笔整体均量与终点分型均量；
/// 2. 长上影且分型显著放量时判定 `看空`，长下影且分型显著缩量时判定 `看多`；
/// 3. 若笔或分型样本不足，或未完成笔过长，则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1_BE辅助V230224_看多_任意_任意_0')`
/// - `Signal('60分钟_D1_BE辅助V230224_看空_任意_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 仅在 UBI 较短时使用量价关系辅助判断笔结束。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230224` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230224",
    template = "{freq}_D1_BE辅助V230224",
    opcode = "CxtBiEndV230224",
    param_kind = "CxtBiEndV230224"
)]
pub fn cxt_bi_end_v230224(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "D1";
    let k3 = "BE辅助V230224";
    let mut v1 = "其他";
    if c.bi_list.len() <= 3 || c.bars_ubi.len() >= 7 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    let last_bi = c.bi_list.last().unwrap();
    let bi_bars = last_bi.get_raw_bars();
    let fx_bars = fx_raw_bars(&last_bi.fx_b);
    if bi_bars.is_empty() || fx_bars.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    let bi_vol_mean = bi_bars.iter().map(|x| x.vol).sum::<f64>() / bi_bars.len() as f64;
    let fx_vol_mean = fx_bars.iter().map(|x| x.vol).sum::<f64>() / fx_bars.len() as f64;

    let bar1 = fx_bars
        .iter()
        .skip(1)
        .fold(&fx_bars[0], |acc, x| if x.low < acc.low { x } else { acc });
    let bar2 = fx_bars
        .iter()
        .skip(1)
        .fold(&fx_bars[0], |acc, x| if x.high > acc.high { x } else { acc });

    if raw_bar_upper(bar1) > raw_bar_lower(bar1) * 2.0 && fx_vol_mean > bi_vol_mean * 2.0 {
        v1 = "看空";
    }
    if 2.0 * raw_bar_upper(bar2) < raw_bar_lower(bar2) && fx_vol_mean < bi_vol_mean * 0.618 {
        v1 = "看多";
    }

    make_kline_signal_v1(&k1, k2, k3, v1)
}

/// cxt_bi_end_V230312：MACD辅助判断笔结束
///
/// 参数模板：`"{freq}_D0MACD{fastperiod}#{slowperiod}#{signalperiod}_BE辅助V230312"`
///
/// 信号逻辑：
/// 1. 计算指定参数的 MACD，并读取最后一笔终点分型对应的首末原始 K 线；
/// 2. 向下笔若分型尾部 MACD 柱值高于分型起点，判定 `看多`；向上笔反向判定 `看空`；
/// 3. MACD 缓存、分型样本或边界条件不满足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0MACD12#26#9_BE辅助V230312_看多_任意_任意_0')`
/// - `Signal('60分钟_D0MACD12#26#9_BE辅助V230312_看空_任意_任意_0')`
///
/// 参数说明：
/// - `fastperiod`：MACD 快线周期，默认 `12`；
/// - `slowperiod`：MACD 慢线周期，默认 `26`；
/// - `signalperiod`：信号线周期，默认 `9`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230312` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230312",
    template = "{freq}_D0MACD{fastperiod}#{slowperiod}#{signalperiod}_BE辅助V230312",
    opcode = "CxtBiEndV230312",
    param_kind = "CxtBiEndV230312"
)]
pub fn cxt_bi_end_v230312(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let fastperiod = get_usize_param(params, "fastperiod", 12);
    let slowperiod = get_usize_param(params, "slowperiod", 26);
    let signalperiod = get_usize_param(params, "signalperiod", 9);
    let k1 = c.freq.to_string();
    let k2 = format!("D0MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    let k3 = "BE辅助V230312";
    let mut v1 = "其他";
    let cache_key = format!("MACD{}#{}#{}", fastperiod, slowperiod, signalperiod);
    update_macd_cache(c, &cache_key, fastperiod, slowperiod, signalperiod, cache);

    if c.bi_list.len() < 3 || c.bars_ubi.len() >= 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let last_bi = c.bi_list.last().unwrap();
    let fx_bars = fx_raw_bars(&last_bi.fx_b);
    if fx_bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let Some(macd) = cache.macd.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let id_to_idx = bar_index_map(c);
    let mut snapshot_overrides: HashMap<i32, (f64, f64, f64)> = HashMap::new();
    let macd1 = macd_snapshot_field_value(
        c,
        macd,
        &id_to_idx,
        fx_bars.last().unwrap(),
        fastperiod,
        slowperiod,
        signalperiod,
        MacdField::Macd,
        &mut snapshot_overrides,
    )
    .unwrap_or(f64::NAN);
    let macd2 = macd_snapshot_field_value(
        c,
        macd,
        &id_to_idx,
        fx_bars.first().unwrap(),
        fastperiod,
        slowperiod,
        signalperiod,
        MacdField::Macd,
        &mut snapshot_overrides,
    )
    .unwrap_or(f64::NAN);
    if !macd1.is_finite() || !macd2.is_finite() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    if last_bi.direction == Direction::Down && macd1 > macd2 {
        v1 = "看多";
    }
    if last_bi.direction == Direction::Up && macd1 < macd2 {
        v1 = "看空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_bi_end_V230324：笔结束分型均线突破
///
/// 参数模板：`"{freq}_D0{ma_type}#{timeperiod}均线突破_BE辅助V230324"`
///
/// 信号逻辑：
/// 1. 计算指定均线，并提取最后一笔终点分型除最后一根之外的均线序列；
/// 2. 向上笔若上一根收盘跌破分型内最低均线，判定 `看空`；向下笔若上一根收盘突破分型内最高均线，判定 `看多`；
/// 3. 数据不足、UBI 过长或均线不可用时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0SMA#5均线突破_BE辅助V230324_看多_任意_任意_0')`
/// - `Signal('60分钟_D0EMA#13均线突破_BE辅助V230324_看空_任意_任意_0')`
///
/// 参数说明：
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230324` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230324",
    template = "{freq}_D0{ma_type}#{timeperiod}均线突破_BE辅助V230324",
    opcode = "CxtBiEndV230324",
    param_kind = "CxtBiEndV230324"
)]
pub fn cxt_bi_end_v230324(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let cache_key = format!("{}#{}", ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let k1 = c.freq.to_string();
    let k2 = format!("D0{}#{}均线突破", ma_type, timeperiod);
    let k3 = "BE辅助V230324";
    let mut v1 = "其他";
    let ubi_fxs = c.get_ubi_fxs().unwrap_or_default();

    if c.bi_list.len() < 3 || c.bars_ubi.len() > 7 || ubi_fxs.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    if c.bars_raw.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let id_to_idx = bar_index_map(c);
    let last_bi = c.bi_list.last().unwrap();
    let fx_raw = fx_raw_bars(&last_bi.fx_b);
    if fx_raw.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let mut ma_vals: Vec<f64> = Vec::new();
    for rb in fx_raw.iter().take(fx_raw.len() - 1) {
        if let Some(idx) = id_to_idx.get(&rb.id) {
            if let Some(x) = ma.get(*idx) {
                if x.is_finite() {
                    ma_vals.push(*x);
                }
            }
        }
    }
    if ma_vals.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let max_ma = ma_vals.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let min_ma = ma_vals.iter().copied().fold(f64::INFINITY, f64::min);
    let last_close = c.bars_raw[c.bars_raw.len() - 2].close;

    if last_bi.direction == Direction::Up && last_close < min_ma {
        v1 = "看空";
    }
    if last_bi.direction == Direction::Down && last_close > max_ma {
        v1 = "看多";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_bi_end_V230815：快速突破反向笔
///
/// 参数模板：`"{freq}_快速突破_BE辅助V230815"`
///
/// 信号逻辑：
/// 1. 读取最后一笔和当前未完成笔最后一根 K 线；
/// 2. 向上笔若被最新低点快速跌破，输出 `向下`；向下笔若被最新高点快速突破，输出 `向上`；
/// 3. 笔数不足或 UBI 已延伸过长时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_快速突破_BE辅助V230815_向上_任意_任意_0')`
/// - `Signal('60分钟_快速突破_BE辅助V230815_向下_任意_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 仅用于很短的 UBI 场景，强调“快速突破”。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230815` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230815",
    template = "{freq}_快速突破_BE辅助V230815",
    opcode = "CxtBiEndV230815",
    param_kind = "CxtBiEndV230815"
)]
pub fn cxt_bi_end_v230815(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "快速突破";
    let k3 = "BE辅助V230815";
    let mut v1 = "其他";
    if c.bi_list.len() < 5 || c.bars_ubi.len() >= 5 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let bi = c.bi_list.last().unwrap();
    let last_bar = c.bars_ubi.last().unwrap();
    if bi.direction == Direction::Up && last_bar.low < bi.get_low() {
        v1 = "向下";
    }
    if bi.direction == Direction::Down && last_bar.high > bi.get_high() {
        v1 = "向上";
    }
    make_kline_signal_v1(&k1, k2, k3, v1)
}

/// cxt_bi_stop_V230815：笔止损距离状态
///
/// 参数模板：`"{freq}_距离{th}BP_止损V230815"`
///
/// 信号逻辑：
/// 1. 读取最后一笔方向，并把其高低点作为止损基准；
/// 2. 向上场景比较最新收盘距笔高的回撤，向下场景比较最新收盘距笔低的反弹；
/// 3. 若落在 `th` BP 阈值内则标记 `阈值内`，否则标记 `阈值外`。
///
/// 信号列表示例：
/// - `Signal('60分钟_距离50BP_止损V230815_向上_阈值内_任意_0')`
/// - `Signal('60分钟_距离50BP_止损V230815_向下_阈值外_任意_0')`
///
/// 参数说明：
/// - `th`：距离阈值，单位 BP，默认 `50`；
/// - 信号只读取最后一笔和当前 UBI，不做更长历史统计。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_stop_V230815` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_stop_V230815",
    template = "{freq}_距离{th}BP_止损V230815",
    opcode = "CxtBiStopV230815",
    param_kind = "CxtBiStopV230815"
)]
pub fn cxt_bi_stop_v230815(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let th = get_usize_param(params, "th", 50) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("距离{}BP", th as i32);
    let k3 = "止损V230815";
    let mut v1 = "其他";
    let mut v2 = "其他";
    if c.bi_list.len() < 5 || c.bars_ubi.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, v1, v2);
    }
    let bi = c.bi_list.last().unwrap();
    let last_bar = c.bars_ubi.last().unwrap();
    if bi.direction == Direction::Up {
        v1 = "向下";
        v2 = if last_bar.close > bi.get_high() * (1.0 - th / 10000.0) {
            "阈值内"
        } else {
            "阈值外"
        };
    }
    if bi.direction == Direction::Down {
        v1 = "向上";
        v2 = if last_bar.close < bi.get_low() * (1.0 + th / 10000.0) {
            "阈值内"
        } else {
            "阈值外"
        };
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// cxt_bi_trend_V230824：N笔形态判断
///
/// 参数模板：`"{freq}_D{di}N{n}TH{th}_形态V230824"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 笔的中位价格均值；
/// 2. 用首笔中位价格相对均值的偏离程度判断 `向上/向下/横盘`；
/// 3. 偏离阈值由 `th` 控制，数据不足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N4TH2_形态V230824_向上_任意_任意_0')`
/// - `Signal('60分钟_D1N4TH2_形态V230824_横盘_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `n`：参与比较的笔数，默认 `4`；
/// - `th`：相对均值的偏离阈值，默认 `2`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_trend_V230824` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_trend_V230824",
    template = "{freq}_D{di}N{n}TH{th}_形态V230824",
    opcode = "CxtBiTrendV230824",
    param_kind = "CxtBiTrendV230824"
)]
pub fn cxt_bi_trend_v230824(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 4);
    let th = get_usize_param(params, "th", 2) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}TH{}", di, n, th as i32);
    let k3 = "形态V230824";
    let mut v1 = "其他";
    if c.bi_list.len() < di + n + 2 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis = get_sub_elements(&c.bi_list, di, n);
    if bis.len() != n {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let means: Vec<f64> = bis.iter().map(|bi| (bi.get_low() + bi.get_high()) / 2.0).collect();
    let avg = means.iter().sum::<f64>() / n as f64;
    if !avg.is_finite() || avg == 0.0 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let ratio = means[0] / avg;
    if ratio * 100.0 > 100.0 + th {
        v1 = "向下";
    } else if ratio * 100.0 < 100.0 - th {
        v1 = "向上";
    } else {
        v1 = "横盘";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_bi_zdf_V230601：BI涨跌幅分层
///
/// 参数模板：`"{freq}_D{di}N{n}_分层V230601"`
///
/// 信号逻辑：
/// 1. 取最近最多 50 笔的力度序列；
/// 2. 读取最新笔方向作为 `v1`；
/// 3. 用 `qcut_last_label` 将最新力度分到 `n` 层中的某一层，输出 `第X层`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N5_分层V230601_向上_第3层_任意_0')`
/// - `Signal('60分钟_D1N5_分层V230601_向下_第1层_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始统计，默认 `1`；
/// - `n`：分层数量，默认 `5`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_zdf_V230601` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_zdf_V230601",
    template = "{freq}_D{di}N{n}_分层V230601",
    opcode = "CxtBiZdfV230601",
    param_kind = "CxtBiZdfV230601"
)]
pub fn cxt_bi_zdf_v230601(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let n = get_usize_param(params, "n", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}", di, n);
    let k3 = "分层V230601";
    if c.bi_list.len() < 10 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 50);
    if bis.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let v1 = bis.last().unwrap().direction.to_string();
    let powers: Vec<f64> = bis.iter().map(|x| x.get_power()).collect();
    let v2 = qcut_last_label(&powers, n)
        .map(|layer| format!("第{}层", layer + 1))
        .unwrap_or_else(|| "其他".to_string());
    make_kline_signal_v2(&k1, &k2, k3, &v1, &v2)
}

/// cxt_second_bs_V230320：均线辅助识别第二类买卖点
///
/// 参数模板：`"{freq}_D{di}#{ma_type}#{timeperiod}_BS2辅助V230320"`
///
/// 信号逻辑：
/// 1. 取最近 5 笔，并计算关键分型右侧原始 K 线的均线值；
/// 2. 若前两次同向回撤/反弹已偏离均线，而第 5 笔重新回到均线同向，判定 `二买/二卖`；
/// 3. 均线、分型样本或笔数量不足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1#SMA#21_BS2辅助V230320_二买_任意_任意_0')`
/// - `Signal('60分钟_D1#EMA#34_BS2辅助V230320_二卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `21`。
/// 对齐说明：与 Python `czsc.signals.cxt_second_bs_V230320` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_second_bs_V230320",
    template = "{freq}_D{di}#{ma_type}#{timeperiod}_BS2辅助V230320",
    opcode = "CxtSecondBsV230320",
    param_kind = "CxtSecondBsV230320"
)]
pub fn cxt_second_bs_v230320(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 21);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let cache_key = format!("{}#{}", ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}#{}#{}", di, ma_type, timeperiod);
    let k3 = "BS2辅助V230320";
    let mut v1 = "其他";
    if c.bi_list.len() < di + 6 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let bis = get_sub_elements(&c.bi_list, di, 5);
    if bis.len() != 5 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let b1 = &bis[0];
    let b3 = &bis[2];
    let b5 = &bis[4];
    let b1_fx_bars = fx_raw_bars(&b1.fx_b);
    let b3_fx_bars = fx_raw_bars(&b3.fx_b);
    let b5_fx_a_bars = fx_raw_bars(&b5.fx_a);
    let b5_fx_b_bars = fx_raw_bars(&b5.fx_b);
    if b1_fx_bars.len() < 2 || b3_fx_bars.len() < 2 || b5_fx_a_bars.len() < 2 || b5_fx_b_bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let id_to_idx = bar_index_map(c);

    let get_ma = |bar_id: i32| -> Option<f64> {
        let idx = *id_to_idx.get(&bar_id)?;
        ma.get(idx).copied()
    };
    let Some(b1_ma_b) = get_ma(b1_fx_bars[b1_fx_bars.len() - 2].id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(b3_ma_b) = get_ma(b3_fx_bars[b3_fx_bars.len() - 2].id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(b5_ma_a) = get_ma(b5_fx_a_bars[b5_fx_a_bars.len() - 2].id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(b5_ma_b) = get_ma(b5_fx_b_bars[b5_fx_b_bars.len() - 2].id) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };

    let lc1 = b1.get_low() < b1_ma_b && b3.get_low() < b3_ma_b;
    if b5.direction == Direction::Down && lc1 && b5_ma_a < b5_ma_b {
        v1 = "二买";
    }

    let sc1 = b1.get_high() > b1_ma_b && b3.get_high() > b3_ma_b;
    if b5.direction == Direction::Up && sc1 && b5_ma_a > b5_ma_b {
        v1 = "二卖";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_third_bs_V230318：均线辅助识别第三类买卖点
///
/// 参数模板：`"{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230318"`
///
/// 信号逻辑：
/// 1. 取最近 5 笔构造中枢，并计算第 1、3、5 笔终点分型的均线；
/// 2. 若第 5 笔离开中枢，且三次均线值同向抬升或下降，则判定 `三买/三卖`；
/// 3. 中枢无效、均线缺失或笔数不足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1#SMA#34_BS3辅助V230318_三买_任意_任意_0')`
/// - `Signal('60分钟_D1#EMA#34_BS3辅助V230318_三卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `34`。
/// 对齐说明：与 Python `czsc.signals.cxt_third_bs_V230318` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_third_bs_V230318",
    template = "{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230318",
    opcode = "CxtThirdBsV230318",
    param_kind = "CxtThirdBsV230318"
)]
pub fn cxt_third_bs_v230318(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 34);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let cache_key = format!("{}#{}", ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}#{}#{}", di, ma_type, timeperiod);
    let k3 = "BS3辅助V230318";
    let mut v1 = "其他";

    if c.bi_list.len() < di + 6 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis = get_sub_elements(&c.bi_list, di, 5);
    if bis.len() != 5 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let b1 = &bis[0];
    let b3 = &bis[2];
    let b5 = &bis[4];
    let zs_zd = b1.get_low().max(b3.get_low());
    let zs_zg = b1.get_high().min(b3.get_high());
    if zs_zd > zs_zg {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let id_to_idx = bar_index_map(c);
    let b1_fx = fx_raw_bars(&b1.fx_b);
    let b3_fx = fx_raw_bars(&b3.fx_b);
    let b5_fx = fx_raw_bars(&b5.fx_b);
    if b1_fx.is_empty() || b3_fx.is_empty() || b5_fx.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let mut snapshot_overrides: HashMap<i32, f64> = HashMap::new();
    let Some(ma_1) = ma_snapshot_value(
        c,
        ma,
        &id_to_idx,
        &b1_fx[b1_fx.len() - 1],
        &ma_type,
        timeperiod,
        &mut snapshot_overrides,
    ) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(ma_3) = ma_snapshot_value(
        c,
        ma,
        &id_to_idx,
        &b3_fx[b3_fx.len() - 1],
        &ma_type,
        timeperiod,
        &mut snapshot_overrides,
    ) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };
    let Some(ma_5) = ma_snapshot_value(
        c,
        ma,
        &id_to_idx,
        &b5_fx[b5_fx.len() - 1],
        &ma_type,
        timeperiod,
        &mut snapshot_overrides,
    ) else {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    };

    if b5.direction == Direction::Down && b5.get_low() > zs_zg && ma_5 > ma_3 && ma_3 > ma_1 {
        v1 = "三买";
    }
    if b5.direction == Direction::Up && b5.get_high() < zs_zd && ma_5 < ma_3 && ma_3 < ma_1 {
        v1 = "三卖";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_double_zs_V230311：双中枢 BS1 辅助
///
/// 参数模板：`"{freq}_D{di}双中枢_BS1辅助V230311"`
///
/// 信号逻辑：
/// 1. 提取最近 20 笔并重建中枢序列；
/// 2. 若最近两个中枢都有效，比较后一中枢内部两笔的时长与前后中枢极值关系；
/// 3. 向下笔满足衰竭条件判定 `看多`，向上笔满足衰竭条件判定 `看空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1双中枢_BS1辅助V230311_看多_任意_任意_0')`
/// - `Signal('60分钟_D1双中枢_BS1辅助V230311_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 需要至少形成两个有效中枢，否则返回 `其他`。
/// 对齐说明：与 Python `czsc.signals.cxt_double_zs_V230311` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_double_zs_V230311",
    template = "{freq}_D{di}双中枢_BS1辅助V230311",
    opcode = "CxtDoubleZsV230311",
    param_kind = "CxtDoubleZsV230311"
)]
pub fn cxt_double_zs_v230311(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}双中枢", di);
    let k3 = "BS1辅助V230311";
    let mut v1 = "其他";
    let bis = get_sub_elements(&c.bi_list, di, 20);
    if bis.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let zss = get_zs_seq(bis);
    if zss.len() >= 2 && zss[zss.len() - 2].bis.len() >= 2 && zss[zss.len() - 1].bis.len() >= 2 {
        let zs1 = &zss[zss.len() - 2];
        let zs2 = &zss[zss.len() - 1];
        let ts1 = zs2.bis[zs2.bis.len() - 1].bars.len();
        let ts2 = zs2.bis[zs2.bis.len() - 2].bars.len();
        let last_bi = bis.last().unwrap();
        if last_bi.direction == Direction::Down && ts1 >= ts2 * 2 && zs1.gg > zs2.gg {
            v1 = "看多";
        }
        if last_bi.direction == Direction::Up && ts1 >= ts2 * 2 && zs1.dd < zs2.dd {
            v1 = "看空";
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_overlap_V240526：收盘价与最近分型区间重合次数
///
/// 参数模板：`"{freq}_顶底重合_支撑压力V240526"`
///
/// 信号逻辑：
/// 1. 取最近 9 笔，读取最新收盘价；
/// 2. 分别统计收盘价落在向上笔顶分型区间和向下笔底分型区间中的次数；
/// 3. 输出 `顶重合X次` 与 `底重合Y次`，用于支撑压力观察。
///
/// 信号列表示例：
/// - `Signal('60分钟_顶底重合_支撑压力V240526_顶重合2次_底重合1次_任意_0')`
/// - `Signal('60分钟_顶底重合_支撑压力V240526_顶重合0次_底重合3次_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 至少要求 11 笔与非空原始 K 线序列。
/// 对齐说明：与 Python `czsc.signals.cxt_overlap_V240526` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_overlap_V240526",
    template = "{freq}_顶底重合_支撑压力V240526",
    opcode = "CxtOverlapV240526",
    param_kind = "CxtOverlapV240526"
)]
pub fn cxt_overlap_v240526(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "顶底重合";
    let k3 = "支撑压力V240526";
    if c.bi_list.len() < 11 || c.bars_raw.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, 1, 9);
    if bis.is_empty() {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let last_close = c.bars_raw.last().unwrap().close;
    let overlap_count_g = bis
        .iter()
        .filter(|x| x.direction == Direction::Up)
        .filter(|x| x.fx_b.low <= last_close && last_close <= x.fx_b.high)
        .count();
    let overlap_count_d = bis
        .iter()
        .filter(|x| x.direction == Direction::Down)
        .filter(|x| x.fx_b.low <= last_close && last_close <= x.fx_b.high)
        .count();
    let v1 = format!("顶重合{}次", overlap_count_g);
    let v2 = format!("底重合{}次", overlap_count_d);
    make_kline_signal_v2(&k1, k2, k3, &v1, &v2)
}

/// cxt_decision_V240526：分型区域决策
///
/// 参数模板：`"{freq}_分型区域N{n}_决策区域V240526"`
///
/// 信号逻辑：
/// 1. 在最近 100 根 K 线中提取离散价格层；
/// 2. 若最后一笔向上，统计最新收盘到顶分型上沿之间的价位层数，层数不多于 `n` 时判定 `开空`；向下笔反向判定 `开多`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_分型区域N9_决策区域V240526_开多_任意_任意_0')`
/// - `Signal('60分钟_分型区域N9_决策区域V240526_开空_任意_任意_0')`
///
/// 参数说明：
/// - `n`：允许的价位层数量阈值，默认 `9`；
/// - 至少要求 120 根原始 K 线和一笔已完成笔。
/// 对齐说明：与 Python `czsc.signals.cxt_decision_V240526` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_decision_V240526",
    template = "{freq}_分型区域N{n}_决策区域V240526",
    opcode = "CxtDecisionV240526",
    param_kind = "CxtDecisionV240526"
)]
pub fn cxt_decision_v240526(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 9);
    let k1 = c.freq.to_string();
    let k2 = format!("分型区域N{}", n);
    let k3 = "决策区域V240526";
    let mut v1 = "其他";
    if c.bars_raw.len() < 120 || c.bi_list.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bars = get_sub_elements(&c.bars_raw, 1, 100);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let prices = unique_prices_from_bars(bars);
    let bi = c.bi_list.last().unwrap();
    let bar = c.bars_raw.last().unwrap();
    if bi.direction == Direction::Up {
        let in_count = prices
            .iter()
            .filter(|&&x| bar.close <= x && x <= bi.fx_b.high)
            .count();
        if in_count <= n {
            v1 = "开空";
        }
    } else if bi.direction == Direction::Down {
        let in_count = prices
            .iter()
            .filter(|&&x| bi.fx_b.low <= x && x <= bar.close)
            .count();
        if in_count <= n {
            v1 = "开多";
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_decision_V240612：高低点N档决策区间
///
/// 参数模板：`"{freq}_W{w}N{n}高低点_决策区域V240612"`
///
/// 信号逻辑：
/// 1. 用最近 100 根 K 线生成离散价格层，再用最近 `w` 根 K 线确定高低点；
/// 2. 在低点上方和高点下方各取第 `n` 档价格，形成低区和高区阈值；
/// 3. 最新收盘落入低区判定 `开多`，落入高区判定 `开空`。
///
/// 信号列表示例：
/// - `Signal('60分钟_W10N9高低点_决策区域V240612_开多_任意_任意_0')`
/// - `Signal('60分钟_W10N9高低点_决策区域V240612_开空_任意_任意_0')`
///
/// 参数说明：
/// - `w`：最近高低点统计窗口，默认 `10`；
/// - `n`：从高低点向内取第 `n` 档价格，默认 `9`。
/// 对齐说明：与 Python `czsc.signals.cxt_decision_V240612` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_decision_V240612",
    template = "{freq}_W{w}N{n}高低点_决策区域V240612",
    opcode = "CxtDecisionV240612",
    param_kind = "CxtDecisionV240612"
)]
pub fn cxt_decision_v240612(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let w = get_usize_param(params, "w", 10);
    let n = get_usize_param(params, "n", 9);
    let k1 = c.freq.to_string();
    let k2 = format!("W{}N{}高低点", w, n);
    let k3 = "决策区域V240612";
    let mut v1 = "其他";
    if c.bars_raw.len() < 120 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }

    let bars = get_sub_elements(&c.bars_raw, 1, 100);
    let prices = unique_prices_from_bars(bars);
    if prices.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let w_bars = get_sub_elements(&c.bars_raw, 1, w);
    if w_bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let max_high = w_bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let min_low = w_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let last_bar = c.bars_raw.last().unwrap();

    let mut min_low_upper: Vec<f64> = prices.iter().copied().filter(|x| *x >= min_low).collect();
    min_low_upper.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    let low_range = if min_low_upper.len() > n {
        min_low_upper[n]
    } else {
        *min_low_upper.last().unwrap()
    };

    let mut max_high_lower: Vec<f64> = prices.iter().copied().filter(|x| *x <= max_high).collect();
    max_high_lower.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
    let high_range = if max_high_lower.len() > n {
        max_high_lower[n]
    } else {
        *max_high_lower.last().unwrap()
    };

    if last_bar.close < low_range && last_bar.low != min_low {
        v1 = "开多";
    }
    if last_bar.close > high_range && last_bar.high != max_high {
        v1 = "开空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_decision_V240613：放量笔N4BS2决策区
///
/// 参数模板：`"{freq}_放量笔N{n}BS2_决策区域V240613"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 笔并定位成交量最大的最后一笔；
/// 2. 若该笔向下但未创新低，判定 `开多`；若向上但未创新高，判定 `开空`；
/// 3. 只有最后一笔同时满足“放量且不是极值笔”时才触发。
///
/// 信号列表示例：
/// - `Signal('60分钟_放量笔N4BS2_决策区域V240613_开多_任意_任意_0')`
/// - `Signal('60分钟_放量笔N4BS2_决策区域V240613_开空_任意_任意_0')`
///
/// 参数说明：
/// - `n`：比较最近 `n` 笔的放量程度，默认 `4`；
/// - 仅在 UBI 不超过 7 时使用该决策信号。
/// 对齐说明：与 Python `czsc.signals.cxt_decision_V240613` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_decision_V240613",
    template = "{freq}_放量笔N{n}BS2_决策区域V240613",
    opcode = "CxtDecisionV240613",
    param_kind = "CxtDecisionV240613"
)]
pub fn cxt_decision_v240613(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 4);
    let k1 = c.freq.to_string();
    let k2 = format!("放量笔N{}BS2", n);
    let k3 = "决策区域V240613";
    let mut v1 = "其他";
    if c.bi_list.len() < n + 2 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis = get_sub_elements(&c.bi_list, 1, n);
    if bis.len() < n {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis_max_vol = bis
        .iter()
        .map(|x| x.get_power_volume())
        .fold(f64::NEG_INFINITY, f64::max);
    let last_bi = bis.last().unwrap();
    if last_bi.get_power_volume() != bis_max_vol {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
    let max_high = bis
        .iter()
        .map(|x| x.get_high())
        .fold(f64::NEG_INFINITY, f64::max);

    if last_bi.direction == Direction::Down && last_bi.get_low() != min_low {
        v1 = "开多";
    }
    if last_bi.direction == Direction::Up && last_bi.get_high() != max_high {
        v1 = "开空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_decision_V240614：放量新高/新低决策区
///
/// 参数模板：`"{freq}_放量笔N{n}_决策区域V240614"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 笔并定位成交量最大的最后一笔；
/// 2. 若该笔向下且同时创新低，判定 `开多`；若向上且同时创新高，判定 `开空`；
/// 3. 用于识别放量突破后的反向决策区域。
///
/// 信号列表示例：
/// - `Signal('60分钟_放量笔N4_决策区域V240614_开多_任意_任意_0')`
/// - `Signal('60分钟_放量笔N4_决策区域V240614_开空_任意_任意_0')`
///
/// 参数说明：
/// - `n`：比较最近 `n` 笔的放量程度，默认 `4`；
/// - 需要最后一笔既是放量笔，又是最近 `n` 笔的新高或新低笔。
/// 对齐说明：与 Python `czsc.signals.cxt_decision_V240614` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_decision_V240614",
    template = "{freq}_放量笔N{n}_决策区域V240614",
    opcode = "CxtDecisionV240614",
    param_kind = "CxtDecisionV240614"
)]
pub fn cxt_decision_v240614(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 4);
    let k1 = c.freq.to_string();
    let k2 = format!("放量笔N{}", n);
    let k3 = "决策区域V240614";
    let mut v1 = "其他";
    if c.bi_list.len() < n + 2 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis = get_sub_elements(&c.bi_list, 1, n);
    if bis.len() < n {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let bis_max_vol = bis
        .iter()
        .map(|x| x.get_power_volume())
        .fold(f64::NEG_INFINITY, f64::max);
    let last_bi = bis.last().unwrap();
    if last_bi.get_power_volume() != bis_max_vol {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
    let max_high = bis
        .iter()
        .map(|x| x.get_high())
        .fold(f64::NEG_INFINITY, f64::max);

    if last_bi.direction == Direction::Down && last_bi.get_low() == min_low {
        v1 = "开多";
    }
    if last_bi.direction == Direction::Up && last_bi.get_high() == max_high {
        v1 = "开空";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_bs_V240526：趋势跟随 BS 辅助
///
/// 参数模板：`"{freq}_趋势跟随_BS辅助V240526"`
///
/// 信号逻辑：
/// 1. 读取最近 7 笔，要求倒数第二笔具备高 SNR、强价格力度、强成交量或斜率特征；
/// 2. 再比较最后一笔相对前一强势笔的价格力度区间；
/// 3. 满足小回撤条件时输出 `买点/卖点`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_趋势跟随_BS辅助V240526_买点_任意_任意_0')`
/// - `Signal('60分钟_趋势跟随_BS辅助V240526_卖点_任意_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 重点观察倒数第二笔是否是“顺畅强趋势笔”。
/// 对齐说明：与 Python `czsc.signals.cxt_bs_V240526` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bs_V240526",
    template = "{freq}_趋势跟随_BS辅助V240526",
    opcode = "CxtBsV240526",
    param_kind = "CxtBsV240526"
)]
pub fn cxt_bs_v240526(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "趋势跟随";
    let k3 = "BS辅助V240526";
    let mut v1 = "其他";
    if c.bi_list.len() < 11 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let bis = get_sub_elements(&c.bi_list, 1, 7);
    if bis.len() < 7 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let b2 = &bis[bis.len() - 2];
    let b1 = &bis[bis.len() - 1];
    let max_power_price = bis
        .iter()
        .map(|x| x.get_power_price())
        .fold(f64::NEG_INFINITY, f64::max);
    let max_power_volume = bis
        .iter()
        .map(|x| x.get_power_volume())
        .fold(f64::NEG_INFINITY, f64::max);
    let max_slope_abs = bis
        .iter()
        .map(|x| x.get_slope().abs())
        .fold(f64::NEG_INFINITY, f64::max);

    if b2.get_snr() < 0.7
        || (b2.get_power_price() < max_power_price
            && b2.get_power_volume() < max_power_volume
            && b2.get_slope() < max_slope_abs)
    {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    if b2.direction == Direction::Up
        && b1.direction == Direction::Down
        && 0.1 * b2.get_power_price() < b1.get_power_price()
        && b1.get_power_price() < 0.7 * b2.get_power_price()
    {
        v1 = "买点";
    }
    if b2.direction == Direction::Down
        && b1.direction == Direction::Up
        && 0.2 * b2.get_power_price() < b1.get_power_price()
        && b1.get_power_price() < 0.7 * b2.get_power_price()
    {
        v1 = "卖点";
    }
    make_kline_signal_v1(&k1, k2, k3, v1)
}

/// cxt_bs_V240527：未完成笔上的趋势跟随 BS 辅助
///
/// 参数模板：`"{freq}_趋势跟随_BS辅助V240527"`
///
/// 信号逻辑：
/// 1. 读取最近 7 笔，要求最后一笔本身是高 SNR 的强趋势笔；
/// 2. 再读取当前 UBI 原始 K 线，比较其价格力度相对最后一笔的回撤比例；
/// 3. 满足小回撤条件时输出 `买点/卖点`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_趋势跟随_BS辅助V240527_买点_任意_任意_0')`
/// - `Signal('60分钟_趋势跟随_BS辅助V240527_卖点_任意_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 与 `V240526` 的区别在于这里评估的是未完成笔上的回撤。
/// 对齐说明：与 Python `czsc.signals.cxt_bs_V240527` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bs_V240527",
    template = "{freq}_趋势跟随_BS辅助V240527",
    opcode = "CxtBsV240527",
    param_kind = "CxtBsV240527"
)]
pub fn cxt_bs_v240527(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "趋势跟随";
    let k3 = "BS辅助V240527";
    let mut v1 = "其他";
    if c.bi_list.len() < 11 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let bis = get_sub_elements(&c.bi_list, 1, 7);
    if bis.len() < 7 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let b1 = &bis[bis.len() - 1];
    let max_power_price = bis
        .iter()
        .map(|x| x.get_power_price())
        .fold(f64::NEG_INFINITY, f64::max);
    let max_power_volume = bis
        .iter()
        .map(|x| x.get_power_volume())
        .fold(f64::NEG_INFINITY, f64::max);
    let max_slope_abs = bis
        .iter()
        .map(|x| x.get_slope().abs())
        .fold(f64::NEG_INFINITY, f64::max);

    if b1.get_snr() < 0.7
        || (b1.get_power_price() < max_power_price
            && b1.get_power_volume() < max_power_volume
            && b1.get_slope() < max_slope_abs)
    {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }

    let ubi_bars = ubi_raw_bars(c);
    if ubi_bars.len() < 7 {
        return make_kline_signal_v1(&k1, k2, k3, v1);
    }
    let ubi_high = ubi_bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let ubi_low = ubi_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let ubi_power_price = ubi_high - ubi_low;

    if b1.direction == Direction::Up
        && 0.1 * b1.get_power_price() < ubi_power_price
        && ubi_power_price < 0.7 * b1.get_power_price()
    {
        v1 = "买点";
    }
    if b1.direction == Direction::Down
        && 0.2 * b1.get_power_price() < ubi_power_price
        && ubi_power_price < 0.7 * b1.get_power_price()
    {
        v1 = "卖点";
    }
    make_kline_signal_v1(&k1, k2, k3, v1)
}

/// cxt_first_buy_V221126：一买信号
///
/// 参数模板：`"{freq}_D{di}B_BUY1V221126"`
///
/// 信号逻辑：
/// 1. 依次尝试最近 `21/19/17/15/13/11/9/7/5` 笔；
/// 2. 调用统一的 `check_first_buy` 结构判定函数识别一买；
/// 3. 命中后输出对应笔数，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1B_BUY1_一买_5笔_任意_0')`
/// - `Signal('60分钟_D1B_BUY1_一买_13笔_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 一买结构判定复用 Python 同名逻辑。
/// 对齐说明：与 Python `czsc.signals.cxt_first_buy_V221126` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_first_buy_V221126",
    template = "{freq}_D{di}B_BUY1V221126",
    opcode = "CxtFirstBuyV221126",
    param_kind = "CxtFirstBuyV221126"
)]
pub fn cxt_first_buy_v221126(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}B", di);
    let k3 = "BUY1";
    for n in [21, 19, 17, 15, 13, 11, 9, 7, 5] {
        let bis = get_sub_elements(&c.bi_list, di, n);
        if bis.len() == n && check_first_buy(bis) {
            return make_kline_signal_v2(&k1, &k2, k3, "一买", &format!("{}笔", n));
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// cxt_first_sell_V221126：一卖信号
///
/// 参数模板：`"{freq}_D{di}B_SELL1V221126"`
///
/// 信号逻辑：
/// 1. 依次尝试最近 `21/19/17/15/13/11/9/7/5` 笔；
/// 2. 调用统一的 `check_first_sell` 结构判定函数识别一卖；
/// 3. 命中后输出对应笔数，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1B_SELL1_一卖_5笔_任意_0')`
/// - `Signal('60分钟_D1B_SELL1_一卖_13笔_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 一卖结构判定复用 Python 同名逻辑。
/// 对齐说明：与 Python `czsc.signals.cxt_first_sell_V221126` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_first_sell_V221126",
    template = "{freq}_D{di}B_SELL1V221126",
    opcode = "CxtFirstSellV221126",
    param_kind = "CxtFirstSellV221126"
)]
pub fn cxt_first_sell_v221126(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}B", di);
    let k3 = "SELL1";
    for n in [21, 19, 17, 15, 13, 11, 9, 7, 5] {
        let bis = get_sub_elements(&c.bi_list, di, n);
        if bis.len() == n && check_first_sell(bis) {
            return make_kline_signal_v2(&k1, &k2, k3, "一卖", &format!("{}笔", n));
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// cxt_bi_end_V230222：未完成笔分型新高新低次数
///
/// 参数模板：`"{freq}_D1MO{max_overlap}_BE辅助V230222"`
///
/// 信号逻辑：
/// 1. 拼接最后一笔内部已确认分型与当前 UBI 分型序列；
/// 2. 仅当最新分型刚确认，或距最新原始 K 线不超过 `max_overlap` 根时继续判断；
/// 3. 若最新顶分型创序列新高，输出 `新高_第X次`；若底分型创新低，输出 `新低_第X次`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MO3_BE辅助V230222_新高_第2次_任意_0')`
/// - `Signal('60分钟_D1MO3_BE辅助V230222_新低_第1次_任意_0')`
///
/// 参数说明：
/// - `max_overlap`：允许最新分型与当前原始 K 线的最大重叠根数，默认 `3`；
/// - 超出确认时机或分型不足时返回 `其他_其他`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230222` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230222",
    template = "{freq}_D1MO{max_overlap}_BE辅助V230222",
    opcode = "CxtBiEndV230222",
    param_kind = "CxtBiEndV230222"
)]
pub fn cxt_bi_end_v230222(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let max_overlap = get_usize_param(params, "max_overlap", 3);
    let k1 = c.freq.to_string();
    let k2 = format!("D1MO{}", max_overlap);
    let k3 = "BE辅助V230222";
    let ubi_fxs = c.get_ubi_fxs().unwrap_or_default();
    if ubi_fxs.is_empty() || c.bars_ubi.len() >= 7 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }

    let mut fxs: Vec<FX> = Vec::new();
    if let Some(last_bi) = c.bi_list.last() {
        if last_bi.fxs.len() > 1 {
            fxs.extend_from_slice(&last_bi.fxs[1..]);
        }
    }
    for x in ubi_fxs {
        if fxs.last().map(|y| x.dt > y.dt).unwrap_or(true) {
            fxs.push(x);
        }
    }
    if fxs.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "第其他次");
    }
    let last_fx = fxs.last().unwrap();
    let last_fx_raw = fx_raw_bars(last_fx);
    if last_fx_raw.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "第其他次");
    }
    if !(last_fx.elements.last().unwrap().dt == c.bars_ubi.last().unwrap().dt
        || (c.bars_raw.last().unwrap().id - last_fx_raw.last().unwrap().id) as usize <= max_overlap)
    {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "第其他次");
    }

    if last_fx.mark == Mark::G {
        let up: Vec<&FX> = fxs.iter().filter(|x| x.mark == Mark::G).collect();
        let mut high_max = f64::NEG_INFINITY;
        let mut cnt = 0;
        for fx in up {
            if fx.high > high_max {
                cnt += 1;
                high_max = fx.high;
            }
        }
        if last_fx.high == high_max {
            return make_kline_signal_v2(&k1, &k2, k3, "新高", &format!("第{}次", cnt));
        }
    } else {
        let down: Vec<&FX> = fxs.iter().filter(|x| x.mark == Mark::D).collect();
        let mut low_min = f64::INFINITY;
        let mut cnt = 0;
        for fx in down {
            if fx.low < low_min {
                cnt += 1;
                low_min = fx.low;
            }
        }
        if last_fx.low == low_min {
            return make_kline_signal_v2(&k1, &k2, k3, "新低", &format!("第{}次", cnt));
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, "其他", "第其他次")
}

/// cxt_third_buy_V230228：笔三买辅助
///
/// 参数模板：`"{freq}_D{di}_三买辅助V230228"`
///
/// 信号逻辑：
/// 1. 依次尝试最近 `13/11/9/7/5` 笔加末笔，共 `n + 1` 笔；
/// 2. 从奇数位上升关键笔中提取突破结构，要求末笔低点在关键高点上方并满足价格约束；
/// 3. 满足条件时输出 `三买_XX笔`，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1_三买辅助V230228_三买_6笔_任意_0')`
/// - `Signal('60分钟_D1_三买辅助V230228_三买_10笔_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 该函数仅输出三买，不输出三卖。
/// 对齐说明：与 Python `czsc.signals.cxt_third_buy_V230228` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_third_buy_V230228",
    template = "{freq}_D{di}_三买辅助V230228",
    opcode = "CxtThirdBuyV230228",
    param_kind = "CxtThirdBuyV230228"
)]
pub fn cxt_third_buy_v230228(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}", di);
    let k3 = "三买辅助V230228";
    if c.bi_list.len() < di + 11 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }

    for n in [13, 11, 9, 7, 5] {
        let bis = get_sub_elements(&c.bi_list, di, n + 1);
        if bis.len() != n + 1 {
            continue;
        }
        if bis.last().unwrap().direction == Direction::Up || bis.first().unwrap().direction == bis.last().unwrap().direction {
            continue;
        }
        let mut key_bis: Vec<&BI> = Vec::new();
        for i in (0..=(bis.len() - 3)).step_by(2) {
            if i == 0 {
                key_bis.push(&bis[i]);
            } else {
                let b1 = &bis[i - 2];
                let b3 = &bis[i];
                if b3.get_high() > b1.get_high() {
                    key_bis.push(b3);
                }
            }
        }
        if key_bis.len() < 2 {
            continue;
        }
        let tb_break = bis.last().unwrap().get_low()
            > key_bis.iter().map(|x| x.get_high()).fold(f64::INFINITY, f64::min)
            && key_bis.iter().map(|x| x.get_high()).fold(f64::INFINITY, f64::min)
                > key_bis.iter().map(|x| x.get_low()).fold(f64::NEG_INFINITY, f64::max);
        let tb_price = bis.last().unwrap().get_low()
            < bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min)
                + 1.618 * mean(&key_bis.iter().map(|x| x.get_power_price()).collect::<Vec<_>>());
        if tb_break && tb_price {
            return make_kline_signal_v2(&k1, &k2, k3, "三买", &format!("{}笔", bis.len()));
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, "其他", "其他")
}

/// cxt_third_bs_V230319：带均线形态的第三类买卖点辅助
///
/// 参数模板：`"{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230319"`
///
/// 信号逻辑：
/// 1. 取最近 5 笔构造中枢，并读取第 1、3、5 笔终点分型的均线值；
/// 2. 先根据第 5 笔是否离开中枢，判定 `三买/三卖`；
/// 3. 再根据三次均线相对位置补充 `均线新高/新低/顶分/底分/否定`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1#SMA#34_BS3辅助V230319_三买_均线新高_任意_0')`
/// - `Signal('60分钟_D1#EMA#34_BS3辅助V230319_三卖_均线顶分_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `34`。
/// 对齐说明：与 Python `czsc.signals.cxt_third_bs_V230319` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_third_bs_V230319",
    template = "{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230319",
    opcode = "CxtThirdBsV230319",
    param_kind = "CxtThirdBsV230319"
)]
pub fn cxt_third_bs_v230319(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let timeperiod = get_usize_param(params, "timeperiod", 34);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let cache_key = format!("{}#{}", ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}#{}#{}", di, ma_type, timeperiod);
    let k3 = "BS3辅助V230319";
    if c.bi_list.len() < di + 6 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 5);
    if bis.len() != 5 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let b1 = &bis[0];
    let b3 = &bis[2];
    let b5 = &bis[4];
    let zs_zd = b1.get_low().max(b3.get_low());
    let zs_zg = b1.get_high().min(b3.get_high());
    if zs_zd > zs_zg {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let id_to_idx = bar_index_map(c);
    let mut snapshot_overrides: HashMap<i32, f64> = HashMap::new();
    let get_last_ma = |bi: &BI, snapshot_overrides: &mut HashMap<i32, f64>| -> Option<f64> {
        let rb = fx_raw_bars(&bi.fx_b);
        let last = rb.last()?;
        ma_snapshot_value(c, ma, &id_to_idx, last, &ma_type, timeperiod, snapshot_overrides)
    };
    let Some(ma_1) = get_last_ma(b1, &mut snapshot_overrides) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(ma_3) = get_last_ma(b3, &mut snapshot_overrides) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(ma_5) = get_last_ma(b5, &mut snapshot_overrides) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };

    let v1 = if b5.direction == Direction::Down && b5.get_low() > zs_zg {
        "三买"
    } else if b5.direction == Direction::Up && b5.get_high() < zs_zd {
        "三卖"
    } else {
        "其他"
    };
    if v1 == "其他" {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let v2 = if ma_5 > ma_3 && ma_3 > ma_1 {
        "均线新高"
    } else if ma_5 < ma_3 && ma_3 < ma_1 {
        "均线新低"
    } else if ma_5 > ma_3 && ma_3 < ma_1 {
        "均线底分"
    } else if ma_5 < ma_3 && ma_3 > ma_1 {
        "均线顶分"
    } else {
        "均线否定"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// cxt_bi_end_V230320：质数窗口笔结束辅助
///
/// 参数模板：`"{freq}_D0质数窗口MO{max_overlap}_BE辅助V230320"`
///
/// 信号逻辑：
/// 1. 展开当前 UBI 原始 K 线，统计其长度是否落在预设质数集合中；
/// 2. 若向上笔后的 UBI 在最近 `max_overlap` 根内创新低，判定 `看多`；向下笔反向判定 `看空`；
/// 3. 输出时补充 `XXK` 表示当前 UBI 长度。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0质数窗口MO3_BE辅助V230320_看多_13K_任意_0')`
/// - `Signal('60分钟_D0质数窗口MO3_BE辅助V230320_看空_17K_任意_0')`
///
/// 参数说明：
/// - `max_overlap`：允许用末尾 `max_overlap` 根 K 线判断极值，默认 `3`；
/// - 质数窗口集合固定为 `11~97` 内常用质数。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230320` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230320",
    template = "{freq}_D0质数窗口MO{max_overlap}_BE辅助V230320",
    opcode = "CxtBiEndV230320",
    param_kind = "CxtBiEndV230320"
)]
pub fn cxt_bi_end_v230320(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let max_overlap = get_usize_param(params, "max_overlap", 3);
    let k1 = c.freq.to_string();
    let k2 = format!("D0质数窗口MO{}", max_overlap);
    let k3 = "BE辅助V230320";
    if c.bi_list.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let primes = [11usize, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97];
    let last_bi = c.bi_list.last().unwrap();
    let bars = &c.bars_ubi[1..];
    let raw_bars: Vec<RawBar> = bars.iter().flat_map(|x| x.elements.iter().cloned()).collect();
    if raw_bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let ubi_len = raw_bars.len();
    let ubi_min = raw_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let ubi_max = raw_bars.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let mop_bars = &raw_bars[raw_bars.len().saturating_sub(max_overlap)..];
    if last_bi.direction == Direction::Up
        && primes.contains(&ubi_len)
        && mop_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min) == ubi_min
    {
        return make_kline_signal_v2(&k1, &k2, k3, "看多", &format!("{}K", ubi_len));
    }
    if last_bi.direction == Direction::Down
        && primes.contains(&ubi_len)
        && mop_bars.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max) == ubi_max
    {
        return make_kline_signal_v2(&k1, &k2, k3, "看空", &format!("{}K", ubi_len));
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// cxt_bi_end_V230322：分型配合均线的笔结束辅助
///
/// 参数模板：`"{freq}_D0分型配合{ma_type}#{timeperiod}_BE辅助V230322"`
///
/// 信号逻辑：
/// 1. 读取最新 UBI 分型对应的原始 K 线，并提取分型区间内的均线序列；
/// 2. 向上笔若最新分型与均线位置形成顶部配合，判定 `看空`；向下笔反向判定 `看多`；
/// 3. 再用 `同向分型/反向分型` 说明分型方向与笔方向关系。
///
/// 信号列表示例：
/// - `Signal('60分钟_D0分型配合SMA#5_BE辅助V230322_看多_反向分型_任意_0')`
/// - `Signal('60分钟_D0分型配合EMA#8_BE辅助V230322_看空_同向分型_任意_0')`
///
/// 参数说明：
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `5`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230322` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230322",
    template = "{freq}_D0分型配合{ma_type}#{timeperiod}_BE辅助V230322",
    opcode = "CxtBiEndV230322",
    param_kind = "CxtBiEndV230322"
)]
pub fn cxt_bi_end_v230322(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let timeperiod = get_usize_param(params, "timeperiod", 5);
    let cache_key = format!("{}#{}", ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let k1 = c.freq.to_string();
    let k2 = format!("D0分型配合{}#{}", ma_type, timeperiod);
    let k3 = "BE辅助V230322";
    let ubi_fxs = c.get_ubi_fxs().unwrap_or_default();
    let last_bar = c.bars_raw.last().unwrap();
    if c.bi_list.len() < 3
        || c.bars_ubi.len() > 7
        || ubi_fxs.is_empty()
        || last_bar.dt != fx_raw_bars(ubi_fxs.last().unwrap()).last().map(|x| x.dt).unwrap_or(last_bar.dt)
    {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let id_to_idx = bar_index_map(c);
    let last_bi = c.bi_list.last().unwrap();
    let last_fx = ubi_fxs.last().unwrap();
    let last_fx_raw = fx_raw_bars(last_fx);
    let mut ma_vals = Vec::new();
    for rb in &last_fx_raw {
        if let Some(idx) = id_to_idx.get(&rb.id) {
            if let Some(v) = ma.get(*idx) {
                ma_vals.push(*v);
            }
        }
    }
    if ma_vals.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let max_ma = ma_vals.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    let min_ma = ma_vals.iter().copied().fold(f64::INFINITY, f64::min);
    let right_id = last_fx_raw.last().unwrap().id;
    let right_ma = ma[*id_to_idx.get(&right_id).unwrap_or(&0)];

    if last_bi.direction == Direction::Up {
        if last_fx.mark == Mark::G && right_ma == min_ma {
            return make_kline_signal_v2(&k1, &k2, k3, "看空", "同向分型");
        }
        if last_fx.mark == Mark::D && right_ma != max_ma {
            return make_kline_signal_v2(&k1, &k2, k3, "看空", "反向分型");
        }
    }
    if last_bi.direction == Direction::Down {
        if last_fx.mark == Mark::D && right_ma == max_ma {
            return make_kline_signal_v2(&k1, &k2, k3, "看多", "同向分型");
        }
        if last_fx.mark == Mark::G && right_ma != min_ma {
            return make_kline_signal_v2(&k1, &k2, k3, "看多", "反向分型");
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// cxt_bi_end_V230618：笔结束小中枢辅助
///
/// 参数模板：`"{freq}_D{di}MO{max_overlap}_BE辅助V230618"`
///
/// 信号逻辑：
/// 1. 读取倒数第 `di` 笔的原始 K 线并做价格覆盖计数；
/// 2. 统计覆盖次数形成的峰值数量，近似识别笔内小中枢；
/// 3. 输出 `看多/看空` 和 `X小中枢/其他`，用于辅助笔结束判断。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1MO3_BE辅助V230618_看多_1小中枢_任意_0')`
/// - `Signal('60分钟_D1MO3_BE辅助V230618_看空_其他_任意_0')`
///
/// 参数说明：
/// - `di`：取倒数第 `di` 笔，默认 `1`；
/// - `max_overlap`：控制 UBI 最大允许延伸长度，默认 `3`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_end_V230618` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_end_V230618",
    template = "{freq}_D{di}MO{max_overlap}_BE辅助V230618",
    opcode = "CxtBiEndV230618",
    param_kind = "CxtBiEndV230618"
)]
pub fn cxt_bi_end_v230618(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let max_overlap = get_usize_param(params, "max_overlap", 3);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}MO{}", di, max_overlap);
    let k3 = "BE辅助V230618";
    if c.bi_list.len() < di + 6 || c.bars_ubi.len() > 3 + max_overlap - 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bi = &c.bi_list[c.bi_list.len() - di];
    let raw_bars = bi.get_raw_bars();
    if raw_bars.len() < 2 {
        return make_kline_signal_v2(&k1, &k2, k3, if bi.direction == Direction::Down { "看多" } else { "看空" }, "其他");
    }
    let max_price = raw_bars[..raw_bars.len() - 1].iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let min_price = raw_bars[..raw_bars.len() - 1].iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let price_range = max_price - min_price;
    let mut counts = vec![0usize; 101];
    if price_range > 0.0 {
        for bar in &raw_bars[..raw_bars.len() - 1] {
            let high_pct = (100.0 * (bar.high - min_price) / price_range) as usize;
            let low_pct = (100.0 * (bar.low - min_price) / price_range) as usize;
            if high_pct == low_pct {
                counts[high_pct.min(100)] += 1;
            } else {
                for count in counts
                    .iter_mut()
                    .take(high_pct.min(100) + 1)
                    .skip(low_pct.min(100))
                {
                    *count += 1;
                }
            }
        }
    }
    let mut peak_count = 0usize;
    for i in 1..counts.len() - 1 {
        if counts[i] == 1 && counts[i] < counts[i - 1] {
            peak_count += 1;
        }
    }
    let v1 = if bi.direction == Direction::Down { "看多" } else { "看空" };
    let v2 = if bi.fxs.len() >= 4 && peak_count >= 1 && (bi.fxs[bi.fxs.len() - 4].fx - bi.fxs[bi.fxs.len() - 3].fx) - (bi.fxs[bi.fxs.len() - 2].fx - bi.fxs[bi.fxs.len() - 1].fx) > 0.0 {
        format!("{}小中枢", peak_count)
    } else {
        "其他".to_string()
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, &v2)
}

/// cxt_three_bi_V230618：三笔形态分类信号
///
/// 参数模板：`"{freq}_D{di}三笔_形态V230618"`
///
/// 信号逻辑：
/// 1. 读取最近 3 笔，依据第 1 笔和第 3 笔的高低点关系划分形态；
/// 2. 识别不重合、奔走、收敛、扩张、盘背、无背等典型三笔结构；
/// 3. 若不满足任何预定义结构，则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1三笔_形态V230618_向下盘背_任意_任意_0')`
/// - `Signal('60分钟_D1三笔_形态V230618_向上扩张_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 仅在未完成笔较短时评估三笔形态。
/// 对齐说明：与 Python `czsc.signals.cxt_three_bi_V230618` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_three_bi_V230618",
    template = "{freq}_D{di}三笔_形态V230618",
    opcode = "CxtThreeBiV230618",
    param_kind = "CxtThreeBiV230618"
)]
pub fn cxt_three_bi_v230618(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}三笔", di);
    let k3 = "形态V230618";
    if c.bi_list.len() < di + 6 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 3);
    let (bi1, bi2, bi3) = (&bis[0], &bis[1], &bis[2]);
    let v1 = if bi3.direction == Direction::Down {
        if bi3.get_low() > bi1.get_high() {
            "向下不重合"
        } else if bi2.get_low() < bi3.get_low() && bi3.get_low() < bi1.get_high() && bi1.get_high() < bi2.get_high() {
            "向下奔走型"
        } else if bi1.get_high() > bi3.get_high() && bi1.get_low() < bi3.get_low() {
            "向下收敛"
        } else if bi1.get_high() < bi3.get_high() && bi1.get_low() > bi3.get_low() {
            "向下扩张"
        } else if bi3.get_low() < bi1.get_low() && bi3.get_high() < bi1.get_high() {
            if bi3.get_power() < bi1.get_power() { "向下盘背" } else { "向下无背" }
        } else {
            "其他"
        }
    } else if bi3.get_high() < bi1.get_low() {
        "向上不重合"
    } else if bi2.get_low() < bi1.get_low() && bi1.get_low() < bi3.get_high() && bi3.get_high() < bi2.get_high() {
        "向上奔走型"
    } else if bi1.get_high() > bi3.get_high() && bi1.get_low() < bi3.get_low() {
        "向上收敛"
    } else if bi1.get_high() < bi3.get_high() && bi1.get_low() > bi3.get_low() {
        "向上扩张"
    } else if bi3.get_low() > bi1.get_low() && bi3.get_high() > bi1.get_high() {
        if bi3.get_power() < bi1.get_power() { "向上盘背" } else { "向上无背" }
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_five_bi_V230619：五笔形态分类信号
///
/// 参数模板：`"{freq}_D{di}五笔_形态V230619"`
///
/// 信号逻辑：
/// 1. 读取最近 5 笔并计算整体最高点、最低点；
/// 2. 依据中枢重合、首末笔力度与突破位置识别底背驰、顶背驰、颈线突破、类三买卖等形态；
/// 3. 未命中任何预定义结构时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1五笔_形态V230619_aAb式底背驰_任意_任意_0')`
/// - `Signal('60分钟_D1五笔_形态V230619_类三卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 该信号直接输出形态标签，不再附加次级分类。
/// 对齐说明：与 Python `czsc.signals.cxt_five_bi_V230619` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_five_bi_V230619",
    template = "{freq}_D{di}五笔_形态V230619",
    opcode = "CxtFiveBiV230619",
    param_kind = "CxtFiveBiV230619"
)]
pub fn cxt_five_bi_v230619(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}五笔", di);
    let k3 = "形态V230619";
    if c.bi_list.len() < di + 6 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 5);
    let (bi1, bi2, bi3, bi4, bi5) = (&bis[0], &bis[1], &bis[2], &bis[3], &bis[4]);
    let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
    let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
    let v1 = if bi1.direction == Direction::Down {
        if bi2.get_high().min(bi4.get_high()) > bi2.get_low().max(bi4.get_low())
            && max_high == bi1.get_high()
            && bi5.get_power() < bi1.get_power()
            && ((min_low == bi3.get_low() && bi5.get_low() < bi1.get_low()) || min_low == bi5.get_low())
        {
            "aAb式底背驰"
        } else if max_high == bi1.get_high()
            && min_low == bi5.get_low()
            && bi4.get_high() < bi2.get_low()
            && bi5.get_power() < bi3.get_power().max(bi1.get_power())
        {
            "类趋势底背驰"
        } else if (min_low == bi1.get_low()
            && bi5.get_high() > bi1.get_high().min(bi2.get_high())
            && bi1.get_high().min(bi2.get_high()) > bi5.get_low()
            && bi5.get_low() > bi1.get_low())
            || (min_low == bi3.get_low()
                && bi5.get_high() > bi3.get_high()
                && bi3.get_high() > bi5.get_low()
                && bi5.get_low() > bi3.get_low())
        {
            "上颈线突破"
        } else if max_high == bi5.get_high()
            && bi5.get_high() > bi5.get_low()
            && bi5.get_low() > bi1.get_high().max(bi3.get_high())
            && bi1.get_high().min(bi3.get_high()) > bi1.get_low().max(bi3.get_low())
            && bi1.get_low().max(bi3.get_low()) > min_low
        {
            "类三买"
        } else {
            "其他"
        }
    } else if bi2.get_high().min(bi4.get_high()) > bi2.get_low().max(bi4.get_low())
        && min_low == bi1.get_low()
        && bi5.get_power() < bi1.get_power()
        && ((max_high == bi3.get_high() && bi5.get_high() > bi1.get_high()) || max_high == bi5.get_high())
    {
        "aAb式顶背驰"
    } else if min_low == bi1.get_low()
        && max_high == bi5.get_high()
        && bi5.get_power() < bi1.get_power().max(bi3.get_power())
        && bi4.get_low() > bi2.get_high()
    {
        "类趋势顶背驰"
    } else if (max_high == bi1.get_high()
        && bi5.get_low() < bi1.get_low().max(bi2.get_low())
        && bi1.get_low().max(bi2.get_low()) < bi5.get_high()
        && bi5.get_high() < max_high)
        || (max_high == bi3.get_high()
            && bi5.get_low() < bi3.get_low()
            && bi3.get_low() < bi5.get_high()
            && bi5.get_high() < max_high)
    {
        "下颈线突破"
    } else if min_low == bi5.get_low()
        && bi5.get_low() < bi5.get_high()
        && bi5.get_high() < bi1.get_low().min(bi3.get_low())
        && bi1.get_low().min(bi3.get_low()) < bi1.get_low().max(bi3.get_low())
        && bi1.get_low().max(bi3.get_low()) < bi1.get_high().min(bi3.get_high())
        && bi1.get_high().min(bi3.get_high()) < max_high
    {
        "类三卖"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_seven_bi_V230620：七笔形态分类信号
///
/// 参数模板：`"{freq}_D{di}七笔_形态V230620"`
///
/// 信号逻辑：
/// 1. 读取最近 7 笔并统计极值与关键中枢关系；
/// 2. 识别 aAbcd、abcAd、类趋势、向上/向下中枢完成、类三买卖等七笔结构；
/// 3. 未命中预定义结构时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1七笔_形态V230620_aAbcd式底背驰_任意_任意_0')`
/// - `Signal('60分钟_D1七笔_形态V230620_向上中枢完成_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 仅在最近结构已基本完成且 UBI 不长时评估。
/// 对齐说明：与 Python `czsc.signals.cxt_seven_bi_V230620` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_seven_bi_V230620",
    template = "{freq}_D{di}七笔_形态V230620",
    opcode = "CxtSevenBiV230620",
    param_kind = "CxtSevenBiV230620"
)]
pub fn cxt_seven_bi_v230620(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}七笔", di);
    let k3 = "形态V230620";
    if c.bi_list.len() < di + 10 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 7);
    let (bi1, bi2, bi3, bi4, bi5, bi6, bi7) = (&bis[0], &bis[1], &bis[2], &bis[3], &bis[4], &bis[5], &bis[6]);
    let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
    let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
    let v1 = if bi7.direction == Direction::Down {
        if bi1.get_high() == max_high && bi7.get_low() == min_low {
            if bi2.get_high().min(bi4.get_high()) > bi2.get_low().max(bi4.get_low()) && bi2.get_low().max(bi4.get_low()) > bi6.get_high() && bi7.get_power() < bi5.get_power() {
                "aAbcd式底背驰"
            } else if bi2.get_low() > bi4.get_high().min(bi6.get_high()) && bi4.get_low().max(bi6.get_low()) < bi4.get_high().min(bi6.get_high()) && bi7.get_power() < bi1.get_high() - bi3.get_low() {
                "abcAd式底背驰"
            } else if bi2.get_high().min(bi4.get_high()).min(bi6.get_high()) > bi2.get_low().max(bi4.get_low()).max(bi6.get_low()) && bi7.get_power() < bi1.get_power() {
                "aAb式底背驰"
            } else if bi2.get_low() > bi4.get_high() && bi4.get_low() > bi6.get_high() && bi7.get_power() < bi5.get_power().max(bi3.get_power()).max(bi1.get_power()) {
                "类趋势底背驰"
            } else {
                "其他"
            }
        } else if bi4.get_low() == min_low
            && bi1.get_high().min(bi3.get_high()) > bi1.get_low().max(bi3.get_low())
            && bi5.get_high().min(bi7.get_high()) > bi5.get_low().max(bi7.get_low())
            && bi4.get_high().max(bi6.get_high()) > bi3.get_high().min(bi4.get_high())
            && bi1.get_low().max(bi3.get_low()) < bi5.get_high().max(bi7.get_high())
        {
            "向上中枢完成"
        } else if bi1.get_low().min(bi3.get_low()) == min_low
            && bi5.get_high().max(bi7.get_high()) == max_high
            && bi5.get_low().min(bi7.get_low()) > bi1.get_high().max(bi3.get_high())
            && bi1.get_high().min(bi3.get_high()) > bi1.get_low().max(bi3.get_low())
        {
            "类三买"
        } else {
            "其他"
        }
    } else if bi1.get_low() == min_low && bi7.get_high() == max_high {
        if bi6.get_low() > bi2.get_high().min(bi4.get_high()) && bi2.get_high().min(bi4.get_high()) > bi2.get_low().max(bi4.get_low()) && bi7.get_power() < bi5.get_power() {
            "aAbcd式顶背驰"
        } else if bi4.get_high().min(bi6.get_high()) > bi4.get_low().max(bi6.get_low()) && bi4.get_low().max(bi6.get_low()) > bi2.get_high() && bi7.get_power() < bi3.get_high() - bi1.get_low() {
            "abcAd式顶背驰"
        } else if bi2.get_high().min(bi4.get_high()).min(bi6.get_high()) > bi2.get_low().max(bi4.get_low()).max(bi6.get_low()) && bi7.get_power() < bi1.get_power() {
            "aAb式顶背驰"
        } else if bi2.get_high() < bi4.get_low() && bi4.get_high() < bi6.get_low() && bi7.get_power() < bi5.get_power().max(bi3.get_power()).max(bi1.get_power()) {
            "类趋势顶背驰"
        } else {
            "其他"
        }
    } else if bi4.get_high() == max_high
        && bi1.get_high().min(bi3.get_high()) > bi1.get_low().max(bi3.get_low())
        && bi5.get_high().min(bi7.get_high()) > bi5.get_low().max(bi7.get_low())
        && bi4.get_low().min(bi6.get_low()) < bi3.get_low().max(bi4.get_low())
        && bi1.get_high().min(bi3.get_high()) > bi5.get_low().min(bi7.get_low())
    {
        "向下中枢完成"
    } else if bi5.get_low().min(bi7.get_low()) == min_low
        && bi1.get_high().max(bi3.get_high()) == max_high
        && bi7.get_high().max(bi5.get_high()) < bi1.get_low().min(bi3.get_low())
        && bi1.get_high().min(bi3.get_high()) > bi1.get_low().max(bi3.get_low())
    {
        "类三卖"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_range_oscillation_V230620：区间震荡笔数统计
///
/// 参数模板：`"{freq}_D{di}TH{th}_区间震荡V230620"`
///
/// 信号逻辑：
/// 1. 读取最近 12 笔的中位价格中心；
/// 2. 从最新笔向前逐笔比较中心振幅，只要最大振幅百分比小于 `th` 就继续累加；
/// 3. 若累计笔数超过 1，则输出 `X笔震荡 + 向上/向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1TH2_区间震荡V230620_4笔震荡_向上_任意_0')`
/// - `Signal('60分钟_D1TH2_区间震荡V230620_6笔震荡_向下_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `th`：中心振幅百分比阈值，默认 `2`。
/// 对齐说明：与 Python `czsc.signals.cxt_range_oscillation_V230620` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_range_oscillation_V230620",
    template = "{freq}_D{di}TH{th}_区间震荡V230620",
    opcode = "CxtRangeOscillationV230620",
    param_kind = "CxtRangeOscillationV230620"
)]
pub fn cxt_range_oscillation_v230620(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let th = get_usize_param(params, "th", 2);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TH{}", di, th);
    let k3 = "区间震荡V230620";
    if c.bi_list.len() < di + 11 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 12);
    if bis.len() != 12 {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    }
    let mut centers = Vec::new();
    let mut count = 1usize;
    for bi in bis.iter().rev() {
        centers.push((bi.get_high() + bi.get_low()) / 2.0);
        if centers.len() > 1 {
            if max_amplitude_pct(&centers) < th as f64 {
                count += 1;
            } else {
                break;
            }
        }
    }
    if count != 1 {
        return make_kline_signal_v2(&k1, &k2, k3, &format!("{}笔震荡", count), if bis.last().unwrap().direction == Direction::Up { "向上" } else { "向下" });
    }
    make_kline_signal_v2(&k1, &k2, k3, "其他", "其他")
}

/// cxt_nine_bi_V230621：九笔形态分类信号
///
/// 参数模板：`"{freq}_D{di}九笔_形态V230621"`
///
/// 信号逻辑：
/// 1. 读取最近 9 笔，依据首末极值和中间中枢关系构造结构；
/// 2. 识别 aAb、aAbcd、ABC、类趋势一买卖、类三买卖、类二买卖等九笔形态；
/// 3. 未命中时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1九笔_形态V230621_aAb式类一买_任意_任意_0')`
/// - `Signal('60分钟_D1九笔_形态V230621_ZG三买_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 该分类信号直接返回形态名，不再附加辅助标签。
/// 对齐说明：与 Python `czsc.signals.cxt_nine_bi_V230621` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_nine_bi_V230621",
    template = "{freq}_D{di}九笔_形态V230621",
    opcode = "CxtNineBiV230621",
    param_kind = "CxtNineBiV230621"
)]
pub fn cxt_nine_bi_v230621(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}九笔", di);
    let k3 = "形态V230621";
    if c.bi_list.len() < di + 13 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 9);
    let (bi1, bi2, bi3, bi4, bi5, bi6, bi7, bi8, bi9) = (&bis[0], &bis[1], &bis[2], &bis[3], &bis[4], &bis[5], &bis[6], &bis[7], &bis[8]);
    let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
    let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
    let odd_1357 = [bi1, bi3, bi5, bi7];
    let v1 = if bi9.direction == Direction::Down {
        let mut v1 = "其他";
        if min_low == bi9.get_low() && max_high == bi1.get_high() {
            if bi2.get_high().min(bi4.get_high()).min(bi6.get_high()).min(bi8.get_high()) > bi2.get_low().max(bi4.get_low()).max(bi6.get_low()).max(bi8.get_low())
                && bi9.get_power() < bi1.get_power()
                && bi3.get_low() >= bi1.get_low()
                && bi7.get_high() <= bi9.get_high()
            {
                v1 = "aAb式类一买";
            } else if bi2.get_high().min(bi4.get_high()).min(bi6.get_high()) > bi2.get_low().max(bi4.get_low()).max(bi6.get_low()) && bi2.get_low().max(bi4.get_low()).max(bi6.get_low()) > bi8.get_high() && bi9.get_power() < bi7.get_power() {
                v1 = "aAbcd式类一买";
            } else if bi3.get_low() < bi1.get_low()
                && bi7.get_high() > bi9.get_high()
                && bi4.get_high().min(bi6.get_high()) > bi4.get_low().max(bi6.get_low())
                && (bi1.get_high() - bi3.get_low()) > (bi7.get_high() - bi9.get_low())
            {
                v1 = "ABC式类一买";
            } else if bi8.get_high() < bi6.get_low()
                && bi6.get_high() < bi4.get_low()
                && bi4.get_high() < bi2.get_low()
                && bi9.get_power() < bi1.get_power().max(bi3.get_power()).max(bi5.get_power()).max(bi7.get_power())
            {
                v1 = "类趋势一买";
            }
        }
        if max_high == bi1.get_high().max(bi3.get_high())
            && min_low == bi9.get_low()
            && bi2.get_high().min(bi4.get_high()) > bi2.get_low().max(bi4.get_low())
            && bi2.get_low().min(bi4.get_low()) > bi6.get_high().max(bi8.get_high())
            && bi6.get_high().min(bi8.get_high()) > bi6.get_low().max(bi8.get_low())
            && bi9.get_power() < bi5.get_power()
        {
            v1 = "aAbBc式类一买";
        }
        if max_high == bi9.get_high()
            && bi9.get_low() > odd_1357.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max)
            && odd_1357.iter().map(|x| x.get_high()).fold(f64::INFINITY, f64::min)
                > odd_1357.iter().map(|x| x.get_low()).fold(f64::NEG_INFINITY, f64::max)
            && bi3.get_low().min(bi5.get_low()) == min_low
        {
            v1 = "类三买A";
        }
        if bi8.get_power() < bi2.get_power()
            && max_high == bi9.get_high()
            && bi9.get_low() > bi3.get_high().max(bi5.get_high()).max(bi7.get_high())
            && bi3.get_high().min(bi5.get_high()).min(bi7.get_high()) > bi3.get_low().max(bi5.get_low()).max(bi7.get_low())
            && bi1.get_low() == min_low
        {
            v1 = "类三买B";
        }
        if min_low == bi5.get_low() && max_high == bi1.get_high() && bi4.get_high() < bi2.get_low() {
            let zd = bi5.get_low().max(bi7.get_low());
            let zg = bi5.get_high().min(bi7.get_high());
            let gg = bi5.get_high().max(bi7.get_high());
            if zg > zd && bi8.get_high() > gg {
                if bi9.get_low() > zg {
                    v1 = "ZG三买";
                } else if bi9.get_high() > gg && gg > zg && bi9.get_low() > zd {
                    v1 = "类二买";
                }
            }
        }
        v1
    } else if max_high == bi9.get_high() && min_low == bi1.get_low() {
        if bi6.get_low() > bi2.get_high().min(bi4.get_high())
            && bi2.get_high().min(bi4.get_high()) > bi2.get_low().max(bi4.get_low())
            && bi6.get_high().min(bi8.get_high()) > bi6.get_low().max(bi8.get_low())
            && bi2.get_high().max(bi4.get_high()) < bi6.get_low().min(bi8.get_low())
            && bi9.get_power() < bi5.get_power()
        {
            "aAbBc式类一卖"
        } else if bi2.get_high().min(bi4.get_high()).min(bi6.get_high()).min(bi8.get_high()) > bi2.get_low().max(bi4.get_low()).max(bi6.get_low()).max(bi8.get_low())
            && bi9.get_power() < bi1.get_power()
            && bi3.get_high() <= bi1.get_high()
            && bi7.get_low() >= bi9.get_low()
        {
            "aAb式类一卖"
        } else if bi8.get_low() > bi2.get_high().min(bi4.get_high()).min(bi6.get_high())
            && bi2.get_high().min(bi4.get_high()).min(bi6.get_high()) > bi2.get_low().max(bi4.get_low()).max(bi6.get_low())
            && bi9.get_power() < bi7.get_power()
        {
            "aAbcd式类一卖"
        } else if bi3.get_high() > bi1.get_high()
            && bi7.get_low() < bi9.get_low()
            && bi4.get_high().min(bi6.get_high()) > bi4.get_low().max(bi6.get_low())
            && (bi3.get_high() - bi1.get_low()) > (bi9.get_high() - bi7.get_low())
        {
            "ABC式类一卖"
        } else if bi8.get_low() > bi6.get_high()
            && bi6.get_low() > bi4.get_high()
            && bi4.get_low() > bi2.get_high()
            && bi9.get_power() < bi1.get_power().max(bi3.get_power()).max(bi5.get_power()).max(bi7.get_power())
        {
            "类趋势一卖"
        } else {
            "其他"
        }
    } else if max_high == bi1.get_high()
        && min_low == bi9.get_low()
        && bi9.get_high() < bi3.get_low().max(bi5.get_low()).max(bi7.get_low())
        && bi3.get_low().max(bi5.get_low()).max(bi7.get_low()) < bi3.get_high().min(bi5.get_high()).min(bi7.get_high())
    {
        "类三卖A"
    } else if min_low == bi1.get_low() && max_high == bi5.get_high() && bi2.get_high() < bi4.get_low() {
        let zd = bi5.get_low().max(bi7.get_low());
        let zg = bi5.get_high().min(bi7.get_high());
        let dd = bi5.get_low().min(bi7.get_low());
        if zg > zd && bi8.get_low() < dd {
            if bi9.get_high() < zd {
                "ZD三卖"
            } else if dd < zd && bi9.get_high() < zg {
                "类二卖"
            } else {
                "其他"
            }
        } else {
            "其他"
        }
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_eleven_bi_V230622：十一笔形态分类信号
///
/// 参数模板：`"{freq}_D{di}十一笔_形态V230622"`
///
/// 信号逻辑：
/// 1. 读取最近 11 笔并统计首末极值与中间结构关系；
/// 2. 识别 A5B3C3、A3B3C5、A3B5C3、类二买卖、类三买等十一笔结构；
/// 3. 若不满足任何预定义结构，则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1十一笔_形态V230622_A5B3C3式类一买_任意_任意_0')`
/// - `Signal('60分钟_D1十一笔_形态V230622_类二卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - 该信号面向更长结构分类，要求笔数和确认度更高。
/// 对齐说明：与 Python `czsc.signals.cxt_eleven_bi_V230622` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_eleven_bi_V230622",
    template = "{freq}_D{di}十一笔_形态V230622",
    opcode = "CxtElevenBiV230622",
    param_kind = "CxtElevenBiV230622"
)]
pub fn cxt_eleven_bi_v230622(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}十一笔", di);
    let k3 = "形态V230622";
    if c.bi_list.len() < di + 16 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, 11);
    let (bi1, _, bi3, bi4, bi5, bi6, bi7, bi8, bi9, bi10, bi11) =
        (&bis[0], &bis[1], &bis[2], &bis[3], &bis[4], &bis[5], &bis[6], &bis[7], &bis[8], &bis[9], &bis[10]);
    let max_high = bis.iter().map(|x| x.get_high()).fold(f64::NEG_INFINITY, f64::max);
    let min_low = bis.iter().map(|x| x.get_low()).fold(f64::INFINITY, f64::min);
    let v1 = if bi11.direction == Direction::Down {
        if min_low == bi11.get_low() && max_high == bi1.get_high() {
            if bi5.get_low() == [bi1.get_low(), bi3.get_low(), bi5.get_low()].into_iter().fold(f64::INFINITY, f64::min)
                && bi9.get_low() > bi11.get_low()
                && bi9.get_high() > bi11.get_high()
                && bi8.get_high() > bi6.get_low()
                && bi1.get_high() - bi5.get_low() > bi9.get_high() - bi11.get_low()
            {
                "A5B3C3式类一买"
            } else if bi1.get_high() > bi3.get_high()
                && bi1.get_low() > bi3.get_low()
                && bi7.get_high() == [bi7.get_high(), bi9.get_high(), bi11.get_high()].into_iter().fold(f64::NEG_INFINITY, f64::max)
                && bi6.get_high() > bi4.get_low()
                && bi1.get_high() - bi3.get_low() > bi7.get_high() - bi11.get_low()
            {
                "A3B3C5式类一买"
            } else if bi1.get_low() > bi3.get_low()
                && bi4.get_high().min(bi6.get_high()).min(bi8.get_high()) > bi4.get_low().max(bi6.get_low()).max(bi8.get_low())
                && bi9.get_high() > bi11.get_high()
                && bi1.get_high() - bi3.get_low() > bi9.get_high() - bi11.get_low()
            {
                "A3B5C3式类一买"
            } else if bis[1].get_low() > bi4.get_high()
                && bi4.get_low() > bi6.get_high()
                && bi5.get_low() > bi7.get_low()
                && bi10.get_high() > bi8.get_low()
            {
                "a1Ab式类一买"
            } else {
                "其他"
            }
        } else if (bi7.get_power() < bi1.get_power()
            && min_low == bi7.get_low()
            && bi7.get_low() < bis[1].get_low().max(bi4.get_low()).max(bi6.get_low())
            && bis[1].get_low().max(bi4.get_low()).max(bi6.get_low())
                < bis[1].get_high().min(bi4.get_high()).min(bi6.get_high())
            && bis[1].get_high().min(bi4.get_high()).min(bi6.get_high())
                < bi9.get_high().max(bi11.get_high())
            && bi9.get_high().max(bi11.get_high()) < bi1.get_high()
            && max_high == bi1.get_high()
            && bi11.get_low() > bis[1].get_low().min(bi4.get_low()).min(bi6.get_low())
            && bi9.get_high().min(bi11.get_high()) > bi9.get_low().max(bi11.get_low()))
            || (max_high == bi1.get_high()
                && min_low == bi7.get_low()
                && bi9.get_high().min(bi11.get_high()) > bi9.get_low().max(bi11.get_low())
                && bi11.get_high().max(bi9.get_high()) > bi4.get_high().max(bi6.get_high())
                && bi9.get_low().min(bi11.get_low()) > bi4.get_low().min(bi6.get_low()))
        {
            "类二买"
        } else {
            let gg = [bis[0].get_high(), bis[1].get_high(), bis[2].get_high()].into_iter().fold(f64::NEG_INFINITY, f64::max);
            let zg = [bis[0].get_high(), bis[1].get_high(), bis[2].get_high()].into_iter().fold(f64::INFINITY, f64::min);
            let zd = [bis[0].get_low(), bis[1].get_low(), bis[2].get_low()].into_iter().fold(f64::NEG_INFINITY, f64::max);
            let dd = [bis[0].get_low(), bis[1].get_low(), bis[2].get_low()].into_iter().fold(f64::INFINITY, f64::min);
            if max_high == bi11.get_high()
                && bi11.get_low() > zg
                && zg > zd
                && gg > bi5.get_low()
                && gg > bi7.get_low()
                && gg > bi9.get_low()
                && dd < bi5.get_high()
                && dd < bi7.get_high()
                && dd < bi9.get_high()
            {
                "类三买"
            } else {
                "其他"
            }
        }
    } else if max_high == bi11.get_high() && min_low == bi1.get_low() {
        if bi5.get_high() == [bi1.get_high(), bi3.get_high(), bi5.get_high()].into_iter().fold(f64::NEG_INFINITY, f64::max)
            && bi9.get_low() < bi11.get_low()
            && bi9.get_high() < bi11.get_high()
            && bi8.get_low() < bi6.get_high()
            && bi11.get_high() - bi9.get_low() < bi5.get_high() - bi1.get_low()
        {
            "A5B3C3式类一卖"
        } else if bi7.get_low() == [bi11.get_low(), bi9.get_low(), bi7.get_low()].into_iter().fold(f64::INFINITY, f64::min)
            && bi1.get_high() < bi3.get_high()
            && bi1.get_low() < bi3.get_low()
            && bi6.get_low() < bi4.get_high()
            && bi11.get_high() - bi7.get_low() < bi3.get_high() - bi1.get_low()
        {
            "A3B3C5式类一卖"
        } else if bi1.get_high() < bi3.get_high()
            && bi4.get_high().min(bi6.get_high()).min(bi8.get_high()) > bi4.get_low().max(bi6.get_low()).max(bi8.get_low())
            && bi9.get_low() < bi11.get_low()
            && bi3.get_high() - bi1.get_low() > bi11.get_high() - bi9.get_low()
        {
            "A3B5C3式类一卖"
        } else {
            "其他"
        }
    } else if max_high == bi9.get_high()
        && bi9.get_high() > bi8.get_low()
        && bi8.get_low() > bi6.get_high()
        && bi6.get_high() > bi6.get_low()
        && bi6.get_low() > bi4.get_high()
        && bi4.get_high() > bi4.get_low()
        && bi4.get_low() > bis[1].get_high()
        && min_low == bi1.get_low()
        && bi11.get_high() < bi9.get_high()
    {
        "类二卖"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// cxt_ubi_end_V230816：UBI 新高新低次数信号
///
/// 参数模板：`"{freq}_UBI_BE辅助V230816"`
///
/// 信号逻辑：
/// 1. 重建当前未完成笔 UBI 结构；
/// 2. 若 UBI 向上，则统计内部顶分型的逐次新高次数；若最后一根再次上破，则输出 `新高_第X次`；
/// 3. UBI 向下时对称统计新低次数，否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_UBI_BE辅助V230816_新高_第3次_任意_0')`
/// - `Signal('60分钟_UBI_BE辅助V230816_新低_第2次_任意_0')`
///
/// 参数说明：
/// - 本信号无额外参数，`params` 可为空；
/// - 需要 UBI 已形成足够分型和原始 K 线长度。
/// 对齐说明：与 Python `czsc.signals.cxt_ubi_end_V230816` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_ubi_end_V230816",
    template = "{freq}_UBI_BE辅助V230816",
    opcode = "CxtUbiEndV230816",
    param_kind = "CxtUbiEndV230816"
)]
pub fn cxt_ubi_end_v230816(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "UBI";
    let k3 = "BE辅助V230816";
    let Some(ubi) = rebuild_ubi(c) else {
        return make_kline_signal_v2(&k1, k2, k3, "其他", "其他");
    };
    if ubi.fxs.len() <= 2 || c.bars_ubi.len() <= 5 {
        return make_kline_signal_v2(&k1, k2, k3, "其他", "其他");
    }
    if ubi.direction == Direction::Up {
        let fxs: Vec<&FX> = ubi.fxs.iter().filter(|x| x.mark == Mark::G).collect();
        if fxs.is_empty() {
            return make_kline_signal_v2(&k1, k2, k3, "其他", "其他");
        }
        let mut cnt = 1;
        let mut cur_hfx = fxs[0];
        for fx in fxs.iter().skip(1) {
            if fx.high > cur_hfx.high {
                cnt += 1;
                cur_hfx = fx;
            }
        }
        if ubi.raw_bars.last().unwrap().high > cur_hfx.high {
            return make_kline_signal_v2(&k1, k2, k3, "新高", &format!("第{}次", cnt + 1));
        }
    }
    if ubi.direction == Direction::Down {
        let fxs: Vec<&FX> = ubi.fxs.iter().filter(|x| x.mark == Mark::D).collect();
        if fxs.is_empty() {
            return make_kline_signal_v2(&k1, k2, k3, "其他", "其他");
        }
        let mut cnt = 1;
        let mut cur_lfx = fxs[0];
        for fx in fxs.iter().skip(1) {
            if fx.low < cur_lfx.low {
                cnt += 1;
                cur_lfx = fx;
            }
        }
        if ubi.raw_bars.last().unwrap().low < cur_lfx.low {
            return make_kline_signal_v2(&k1, k2, k3, "新低", &format!("第{}次", cnt + 1));
        }
    }
    make_kline_signal_v2(&k1, k2, k3, "其他", "其他")
}

/// cxt_bi_trend_V230913：笔趋势高低点回归信号
///
/// 参数模板：`"{freq}_D{di}N{n}笔趋势_高低点辅助判断V230913"`
///
/// 信号逻辑：
/// 1. 分别取最近 `di` 个向上笔高点和向下笔低点，做线性回归预测；
/// 2. 用当前 UBI 指定位置的时间点预测上沿、下沿及中轴；
/// 3. 将最新收盘相对预测区间的位置映射为 `上升趋势/下降趋势 + 强弱`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D4N1笔趋势_高低点辅助判断V230913_上升趋势_强_任意_0')`
/// - `Signal('60分钟_D4N1笔趋势_高低点辅助判断V230913_下降趋势_超强_任意_0')`
///
/// 参数说明：
/// - `di`：参与回归的同向笔数量，默认 `4`；
/// - `n`：使用 UBI 中倒数第 `n` 根 K 线做比较，默认 `1`。
/// 对齐说明：与 Python `czsc.signals.cxt_bi_trend_V230913` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_bi_trend_V230913",
    template = "{freq}_D{di}N{n}笔趋势_高低点辅助判断V230913",
    opcode = "CxtBiTrendV230913",
    param_kind = "CxtBiTrendV230913"
)]
pub fn cxt_bi_trend_v230913(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 4);
    let n = get_usize_param(params, "n", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}笔趋势", di, n);
    let k3 = "高低点辅助判断V230913";
    if c.bi_list.len() <= di + 2 || c.bars_ubi.len() <= n + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let up_bis: Vec<&BI> = c.bi_list.iter().filter(|x| x.direction == Direction::Up).collect();
    let down_bis: Vec<&BI> = c.bi_list.iter().filter(|x| x.direction == Direction::Down).collect();
    if up_bis.is_empty() || down_bis.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let up_take = up_bis.len().min(di);
    let down_take = down_bis.len().min(di);
    let up_sel = &up_bis[up_bis.len() - up_take..];
    let down_sel = &down_bis[down_bis.len() - down_take..];
    let up_xs: Vec<f64> = up_sel.iter().map(|x| x.end_dt().timestamp() as f64).collect();
    let up_ys: Vec<f64> = up_sel.iter().map(|x| x.get_high()).collect();
    let down_xs: Vec<f64> = down_sel.iter().map(|x| x.end_dt().timestamp() as f64).collect();
    let down_ys: Vec<f64> = down_sel.iter().map(|x| x.get_low()).collect();
    let x = c.bars_ubi[c.bars_ubi.len() - n].dt.timestamp() as f64;
    let Some(pre_up) = linreg_predict(&up_xs, &up_ys, x) else { return make_kline_signal_v1(&k1, &k2, k3, "其他"); };
    let Some(pre_down) = linreg_predict(&down_xs, &down_ys, x) else { return make_kline_signal_v1(&k1, &k2, k3, "其他"); };
    let pre_mid = (pre_up + pre_down) / 2.0;
    if pre_up <= pre_down {
        return make_kline_signal_v2(&k1, &k2, k3, "观望", "趋势线交叉");
    }
    if c.bars_ubi.len() >= 5 {
        return make_kline_signal_v2(&k1, &k2, k3, "观望", "末笔延伸");
    }
    let close = c.bars_raw[c.bars_raw.len() - n].close;
    if close >= pre_up {
        make_kline_signal_v2(&k1, &k2, k3, "上升趋势", "超强")
    } else if close > pre_mid {
        make_kline_signal_v2(&k1, &k2, k3, "上升趋势", "强")
    } else if close > pre_down {
        make_kline_signal_v2(&k1, &k2, k3, "下降趋势", "强")
    } else {
        make_kline_signal_v2(&k1, &k2, k3, "下降趋势", "超强")
    }
}

/// cxt_second_bs_V240524：第二买卖点重叠计数信号
///
/// 参数模板：`"{freq}_D{di}W{w}T{t}_第二买卖点V240524"`
///
/// 信号逻辑：
/// 1. 读取最近 `w` 笔，统计最后一笔终点分型与前面笔终点分型的重叠次数；
/// 2. 最后一笔为向下且长度足够、重叠次数不少于 `t` 时判定 `二买`；
/// 3. 最后一笔为向上且满足同样条件时判定 `二卖`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W9T2_第二买卖点V240524_二买_任意_任意_0')`
/// - `Signal('60分钟_D1W9T2_第二买卖点V240524_二卖_任意_任意_0')`
///
/// 参数说明：
/// - `di`：从倒数第 `di` 笔开始取样，默认 `1`；
/// - `w`：统计窗口笔数，默认 `9`；
/// - `t`：最少重叠次数，默认 `2`。
/// 对齐说明：与 Python `czsc.signals.cxt_second_bs_V240524` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_second_bs_V240524",
    template = "{freq}_D{di}W{w}T{t}_第二买卖点V240524",
    opcode = "CxtSecondBsV240524",
    param_kind = "CxtSecondBsV240524"
)]
pub fn cxt_second_bs_v240524(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = get_usize_param(params, "di", 1);
    let w = get_usize_param(params, "w", 9);
    let t = get_usize_param(params, "t", 2);
    assert!(w > 5);
    assert!(t >= 2);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}T{}", di, w, t);
    let k3 = "第二买卖点V240524";
    if c.bi_list.len() < w + di + 5 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = get_sub_elements(&c.bi_list, di, w);
    let last = bis.last().unwrap();
    let last_fx_high = last.fx_b.high;
    let last_fx_low = last.fx_b.low;
    let fxs: Vec<&FX> = bis[..bis.len() - 1]
        .iter()
        .filter(|x| x.get_length() >= 7)
        .map(|x| &x.fx_b)
        .collect();
    let zs_count = fxs
        .iter()
        .filter(|fx| overlap(fx.high, fx.low, last_fx_high, last_fx_low))
        .count();
    if last.direction == Direction::Down && last.get_length() >= 7 && zs_count >= t {
        return make_kline_signal_v1(&k1, &k2, k3, "二买");
    }
    if last.direction == Direction::Up && last.get_length() >= 7 && zs_count >= t {
        return make_kline_signal_v1(&k1, &k2, k3, "二卖");
    }
    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// cxt_overlap_V240612：顺畅笔分型支撑压力信号
///
/// 参数模板：`"{freq}_SNR顺畅N{n}_支撑压力V240612"`
///
/// 信号逻辑：
/// 1. 在最近 `n` 笔中筛选原始 K 线数量足够的笔，并按 SNR 排序；
/// 2. 选择 SNR 最高且大于阈值的“顺畅笔”，提取其顶分型与底分型区间；
/// 3. 若最新笔终点分型与这些区间重叠，则输出 `支撑/压力 + 顶分型/底分型`。
///
/// 信号列表示例：
/// - `Signal('60分钟_SNR顺畅N7_支撑压力V240612_支撑_顺畅笔顶分型_任意_0')`
/// - `Signal('60分钟_SNR顺畅N7_支撑压力V240612_压力_顺畅笔底分型_任意_0')`
///
/// 参数说明：
/// - `n`：候选顺畅笔数量窗口，默认 `7`；
/// - 仅当最大 SNR 不低于 `0.7` 时才输出具体支撑压力。
/// 对齐说明：与 Python `czsc.signals.cxt_overlap_V240612` 保持一致。
#[signal(
    category = "kline",
    name = "cxt_overlap_V240612",
    template = "{freq}_SNR顺畅N{n}_支撑压力V240612",
    opcode = "CxtOverlapV240612",
    param_kind = "CxtOverlapV240612"
)]
pub fn cxt_overlap_v240612(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = get_usize_param(params, "n", 7);
    let k1 = c.freq.to_string();
    let k2 = format!("SNR顺畅N{}", n);
    let k3 = "支撑压力V240612";
    if c.bi_list.len() < n + 2 || c.bars_ubi.len() > 7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let mut bis: Vec<&BI> = get_sub_elements(&c.bi_list, 3, n)
        .iter()
        .filter(|x| x.get_raw_bars().len() >= 9)
        .collect();
    if bis.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    bis.sort_by(|a, b| a.get_snr().partial_cmp(&b.get_snr()).unwrap_or(std::cmp::Ordering::Equal));
    let max_snr_bi = bis.last().unwrap();
    if max_snr_bi.get_snr() < 0.7 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let (fxg, fxd) = if max_snr_bi.direction == Direction::Down {
        (&max_snr_bi.fx_a, &max_snr_bi.fx_b)
    } else {
        (&max_snr_bi.fx_b, &max_snr_bi.fx_a)
    };
    let last_bi = c.bi_list.last().unwrap();
    let mut v1 = "其他";
    let mut v2 = "任意";
    if last_bi.direction == Direction::Down {
        if overlap(fxg.high, fxg.low, last_bi.fx_b.high, last_bi.fx_b.low) {
            v1 = "支撑";
            v2 = "顺畅笔顶分型";
        }
        if overlap(fxd.high, fxd.low, last_bi.fx_b.high, last_bi.fx_b.low) {
            v1 = "支撑";
            v2 = "顺畅笔底分型";
        }
    }
    if last_bi.direction == Direction::Up {
        if overlap(fxg.high, fxg.low, last_bi.fx_b.high, last_bi.fx_b.low) {
            v1 = "压力";
            v2 = "顺畅笔顶分型";
        }
        if overlap(fxd.high, fxd.low, last_bi.fx_b.high, last_bi.fx_b.low) {
            v1 = "压力";
            v2 = "顺畅笔底分型";
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}
