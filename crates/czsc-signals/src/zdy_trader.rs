use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{
    get_str_param, get_usize_param, last_open_operate, make_signal, make_signal_v1,
};
use crate::utils::ta::update_macd_cache;
use czsc_core::objects::direction::Direction;
use czsc_core::objects::freq::Freq;
use czsc_core::objects::mark::Mark;
use czsc_core::objects::operate::Operate;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::state::TraderState;
use czsc_signal_macros::signal;
use std::collections::HashMap;
use std::str::FromStr;

fn macd_map(cache: &TaCache, cache_key: &str) -> HashMap<i32, f64> {
    let mut out = HashMap::new();
    if let Some(series) = cache.macd.get(cache_key) {
        for (i, id) in series.ids.iter().enumerate() {
            out.insert(*id, series.macd[i]);
        }
    }
    out
}

/// zdy_vibrate_V230406：中枢震荡短差辅助
#[signal(
    category = "trader",
    name = "zdy_vibrate_V230406",
    template = "中枢震荡_{freq1}#{freq2}_BS辅助V230406",
    opcode = "ZdyVibrateV230406",
    param_kind = "ZdyVibrateV230406"
)]
pub fn zdy_vibrate_v230406(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let freq1 = get_str_param(params, "freq1", "5分钟");
    let freq2 = get_str_param(params, "freq2", "60分钟");
    let k1 = "中枢震荡";
    let k2 = format!("{}#{}", freq1, freq2);
    let k3 = "BS辅助V230406";

    let Ok(f1) = Freq::from_str(freq1) else {
        return make_signal_v1(k1, &k2, k3, "其他");
    };
    let Ok(f2) = Freq::from_str(freq2) else {
        return make_signal_v1(k1, &k2, k3, "其他");
    };
    assert!(f1 < f2, "freq1 必须小于 freq2");

    let Some(c1) = cat.get_czsc(freq1) else {
        return make_signal_v1(k1, &k2, k3, "其他");
    };
    let Some(c2) = cat.get_czsc(freq2) else {
        return make_signal_v1(k1, &k2, k3, "其他");
    };
    if c2.bi_list.len() < 5
        || c1.bi_list.is_empty()
        || c1.bars_raw.is_empty()
        || c2.bars_raw.is_empty()
    {
        return make_signal_v1(k1, &k2, k3, "其他");
    }

    let mut cache = TaCache::new();
    let cache_key = "MACD12#26#9";
    update_macd_cache(c2, cache_key, 12, 26, 9, &mut cache);
    let macd = macd_map(&cache, cache_key);

    let b1 = &c2.bi_list[c2.bi_list.len() - 4];
    let b2 = &c2.bi_list[c2.bi_list.len() - 3];
    let b3 = &c2.bi_list[c2.bi_list.len() - 2];
    let zg = b1.get_high().min(b2.get_high()).min(b3.get_high());
    let zd = b1.get_low().max(b2.get_low()).max(b3.get_low());
    if zd > zg {
        return make_signal_v1(k1, &k2, k3, "其他");
    }

    let c1_lbi = c1.bi_list.last().unwrap();
    let c1_bar = c1.bars_raw.last().unwrap();
    let c1_fx_bars = c1_lbi
        .fx_b
        .elements
        .last()
        .map(|x| x.elements.clone())
        .unwrap_or_default();
    if c1_fx_bars.is_empty() || c1_bar.dt == c1_fx_bars.last().unwrap().dt || c1.bars_ubi.len() > 6
    {
        return make_signal_v1(k1, &k2, k3, "其他");
    }

    let temp = if c1_lbi.direction == Direction::Down
        && c1_bar.close > c1_bar.open
        && c1_bar.close > c1_fx_bars.last().unwrap().high
    {
        Some("底分停顿")
    } else if c1_lbi.direction == Direction::Up
        && c1_bar.close < c1_bar.open
        && c1_bar.close < c1_fx_bars.last().unwrap().low
    {
        Some("顶分停顿")
    } else {
        None
    };
    let Some(temp) = temp else {
        return make_signal_v1(k1, &k2, k3, "其他");
    };

    let c2_bar = c2.bars_raw.last().unwrap();
    let c2_macd = *macd.get(&c2_bar.id).unwrap_or(&f64::NAN);
    if temp == "顶分停顿" && c2_macd < 0.0 {
        let p = c1_bar.close;
        let h = c1_lbi.get_high();
        if h >= zg && (h - zg) < (zg - zd) && (h - p) * 3.0 < (zg - zd) {
            return make_signal_v1(k1, &k2, k3, "看空");
        }
    }
    if temp == "底分停顿" && c2_macd > 0.0 {
        let p = c1_bar.close;
        let l = c1_lbi.get_low();
        if l <= zd && (zd - l) < (zg - zd) && (p - l) * 3.0 < (zg - zd) {
            return make_signal_v1(k1, &k2, k3, "看多");
        }
    }
    make_signal_v1(k1, &k2, k3, "其他")
}

/// zdy_stop_loss_V230406：笔操作止损逻辑
#[signal(
    category = "trader",
    name = "zdy_stop_loss_V230406",
    template = "{freq1}_{pos_name}F{first_stop}_止损V230406",
    opcode = "ZdyStopLossV230406",
    param_kind = "ZdyStopLossV230406"
)]
pub fn zdy_stop_loss_v230406(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let first_stop = get_usize_param(params, "first_stop", 300) as f64;
    let k1 = freq1.to_string();
    let k2 = format!("{}F{}", pos_name, first_stop as i32);
    let k3 = "止损V230406";

    let Some(pos) = cat.get_position(pos_name) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    if pos.operates.is_empty()
        || matches!(pos.operates.last().unwrap().op, Operate::SE | Operate::LE)
    {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }
    let Some(op) = last_open_operate(cat, pos_name) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(c) = cat.get_czsc(freq1) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    if c.bi_list.len() < 3 || c.bars_raw.is_empty() {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }

    let d3bi = &c.bi_list[c.bi_list.len() - 3];
    let bis: Vec<_> = c.bi_list.iter().filter(|x| x.fx_b.dt >= op.dt).collect();
    let last_bar = c.bars_raw.last().unwrap();
    let fxs = c.get_fx_list();

    let mut v1 = "其他";
    let mut v2 = "其他";
    if op.op == Operate::LO {
        if let Some(open_base_fx) = fxs.iter().rfind(|x| x.mark == Mark::D && x.dt < op.dt) {
            if last_bar.close < open_base_fx.low {
                v1 = "多头止损";
                v2 = "跌破分型低点";
            }
        }
        if (last_bar.close / op.price - 1.0) * 10000.0 <= -first_stop {
            v1 = "多头止损";
            v2 = "进场点止损";
        }
        if !bis.is_empty()
            && bis.last().unwrap().direction == Direction::Up
            && bis.last().unwrap().get_high() > d3bi.get_high()
            && last_bar.close < op.price
        {
            v1 = "多头止损";
            v2 = "跌破成本价";
        }
        if bis.len() > 1
            && bis.last().unwrap().direction == Direction::Up
            && last_bar.close < bis[bis.len() - 2].fx_b.low
        {
            v1 = "多头止损";
            v2 = "跌破上个向下笔底";
        }
    }
    if op.op == Operate::SO {
        if let Some(open_base_fx) = fxs.iter().rfind(|x| x.mark == Mark::G && x.dt < op.dt) {
            if last_bar.close > open_base_fx.high {
                v1 = "空头止损";
                v2 = "升破分型高点";
            }
        }
        if (1.0 - last_bar.close / op.price) * 10000.0 <= -first_stop {
            v1 = "空头止损";
            v2 = "进场点止损";
        }
        if !bis.is_empty()
            && bis.last().unwrap().direction == Direction::Down
            && bis.last().unwrap().get_low() < d3bi.get_low()
            && last_bar.close > op.price
        {
            v1 = "空头止损";
            v2 = "升破成本价";
        }
        if bis.len() > 1
            && bis.last().unwrap().direction == Direction::Down
            && last_bar.close > bis[bis.len() - 2].fx_b.high
        {
            v1 = "空头止损";
            v2 = "升破上个向上笔顶";
        }
    }
    make_signal(&k1, &k2, k3, v1, v2)
}

/// zdy_take_profit_V230406：笔操作止盈逻辑
#[signal(
    category = "trader",
    name = "zdy_take_profit_V230406",
    template = "{freq1}_{pos_name}_止盈V230406",
    opcode = "ZdyTakeProfitV230406",
    param_kind = "ZdyTakeProfitV230406"
)]
pub fn zdy_take_profit_v230406(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let k1 = freq1.to_string();
    let k2 = pos_name.to_string();
    let k3 = "止盈V230406";

    let Some(_pos) = cat.get_position(pos_name) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(op) = last_open_operate(cat, pos_name) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(c) = cat.get_czsc(freq1) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let bis: Vec<_> = c.bi_list.iter().filter(|x| x.fx_b.dt >= op.dt).collect();
    let mut v1 = "其他";
    let mut v2 = "其他";
    if op.op == Operate::LO
        && bis.len() > 1
        && bis.last().unwrap().direction == Direction::Up
        && bis.last().unwrap().get_high() < bis[bis.len() - 2].get_high()
    {
        v1 = "多头止盈";
        v2 = "向上笔不创新高";
    }
    if op.op == Operate::SO
        && bis.len() > 1
        && bis.last().unwrap().direction == Direction::Down
        && bis.last().unwrap().get_low() > bis[bis.len() - 2].get_low()
    {
        v1 = "空头止盈";
        v2 = "向下笔不创新低";
    }
    make_signal(&k1, &k2, k3, v1, v2)
}

/// zdy_take_profit_V230407：按力度提前止盈
#[signal(
    category = "trader",
    name = "zdy_take_profit_V230407",
    template = "{freq1}_{pos_name}_止盈V230407",
    opcode = "ZdyTakeProfitV230407",
    param_kind = "ZdyTakeProfitV230407"
)]
pub fn zdy_take_profit_v230407(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let k1 = freq1.to_string();
    let k2 = pos_name.to_string();
    let k3 = "止盈V230407";

    let Some(_pos) = cat.get_position(pos_name) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(op) = last_open_operate(cat, pos_name) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    let Some(c) = cat.get_czsc(freq1) else {
        return make_signal_v1(&k1, &k2, k3, "其他");
    };
    if c.bi_list.len() < 2 {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis: Vec<_> = c.bi_list.iter().filter(|x| x.fx_b.dt >= op.dt).collect();
    let d2bi = &c.bi_list[c.bi_list.len() - 2];
    if bis.is_empty() || (bis.last().unwrap().get_length() as f64) < 1.5 * d2bi.get_length() as f64
    {
        return make_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut v1 = "其他";
    let mut v2 = "其他";
    if op.op == Operate::LO
        && bis.last().unwrap().direction == Direction::Up
        && bis.last().unwrap().get_high() < d2bi.get_high()
    {
        v1 = "多头止盈";
        v2 = "向上笔不创新高";
    }
    if op.op == Operate::SO
        && bis.last().unwrap().direction == Direction::Down
        && bis.last().unwrap().get_low() > d2bi.get_low()
    {
        v1 = "空头止盈";
        v2 = "向下笔不创新低";
    }
    make_signal(&k1, &k2, k3, v1, v2)
}
