use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{
    get_str_param, get_sub_elements, get_usize_param, last_open_operate, latest_price, make_signal,
    make_signal_v1,
};
use crate::utils::ta::{update_atr_cache, update_ma_cache};
use czsc_signal_macros::signal;
use czsc_core::objects::mark::Mark;
use czsc_core::objects::operate::Operate;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::state::TraderState;

/// pos_ma_V230414：判断开仓后是否升破/跌破均线
///
/// 参数模板：`"{pos_name}_{freq1}#{ma_type}#{timeperiod}_持有状态V230414"`
///
/// 信号逻辑：
/// - 多头持仓：开仓后任一 bar 出现 `close > MA`，记 `多头_升破均线`；
/// - 空头持仓：开仓后任一 bar 出现 `close < MA`，记 `空头_跌破均线`；
/// - 其余场景返回 `其他_其他`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_60分钟#SMA#5_持有状态V230414_多头_升破均线_任意_0')`
/// - `Signal('日线三买多头N1_60分钟#SMA#5_持有状态V230414_空头_跌破均线_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期参数，默认 `5`。
#[signal(
    category = "trader",
    name = "pos_ma_V230414",
    template = "{pos_name}_{freq1}#{ma_type}#{timeperiod}_持有状态V230414",
    opcode = "PosMaV230414",
    param_kind = "PosMaV230414"
)]
pub fn pos_ma_v230414(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let ma_type = get_str_param(params, "ma_type", "SMA").to_uppercase();
    let timeperiod = get_usize_param(params, "timeperiod", 5);

    let k1 = pos_name.to_string();
    let k2 = format!("{}#{}#{}", freq1, ma_type, timeperiod);
    let k3 = "持有状态V230414";
    let mut v1 = "其他";
    let mut v2 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };

    let cache_key = format!("{}#{}", ma_type, timeperiod);
    let mut cache = TaCache::new();
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, &mut cache);
    let ma = match cache.series.get(&cache_key) {
        Some(ma) => ma,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };

    let start = c.bars_raw.len().saturating_sub(100);
    let bars = &c.bars_raw[start..];
    for bar in bars.iter().filter(|x| x.dt > op.dt) {
        let idx = match c.bars_raw.iter().position(|b| b.id == bar.id) {
            Some(i) => i,
            None => continue,
        };
        let ma_v = ma.get(idx).copied().unwrap_or(f64::NAN);
        if op.op == Operate::LO && bar.close > ma_v {
            v1 = "多头";
            v2 = "升破均线";
            break;
        }
        if op.op == Operate::SO && bar.close < ma_v {
            v1 = "空头";
            v2 = "跌破均线";
            break;
        }
    }

    make_signal(&k1, &k2, k3, v1, v2)
}

/// pos_fx_stop_V230414：按开仓点附近分型止损
///
/// 参数模板：`"{freq1}_{pos_name}N{n}_止损V230414"`
///
/// 信号逻辑：
/// - 多头：取开仓前最近 `n` 个底分型，最新价跌破最低分型低点，记 `多头止损`；
/// - 空头：取开仓前最近 `n` 个顶分型，最新价突破最高分型高点，记 `空头止损`；
/// - 其余场景记 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_日线三买多头N1_止损V230414_多头止损_任意_任意_0')`
/// - `Signal('日线_日线三买多头N1_止损V230414_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `n`：向前取分型数量，默认 `3`。
#[signal(
    category = "trader",
    name = "pos_fx_stop_V230414",
    template = "{freq1}_{pos_name}N{n}_止损V230414",
    opcode = "PosFxStopV230414",
    param_kind = "PosFxStop"
)]
pub fn pos_fx_stop_v230414(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let n = get_usize_param(params, "n", 3);
    let k1 = freq1.to_string();
    let k2 = format!("{}N{}", pos_name, n);
    let k3 = "止损V230414";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let latest = latest_price(cat, freq1).unwrap_or(0.0);
    let fxs = c.get_fx_list();

    if op.op == Operate::LO {
        let all: Vec<_> = fxs
            .iter()
            .filter(|x| x.mark == Mark::D && x.dt < op.dt)
            .collect();
        let start = all.len().saturating_sub(n);
        if !all.is_empty() {
            let ll = all[start..]
                .iter()
                .fold(f64::INFINITY, |acc, x| acc.min(x.low));
            if latest < ll {
                v1 = "多头止损";
            }
        }
    }
    if op.op == Operate::SO {
        let all: Vec<_> = fxs
            .iter()
            .filter(|x| x.mark == Mark::G && x.dt < op.dt)
            .collect();
        let start = all.len().saturating_sub(n);
        if !all.is_empty() {
            let hh = all[start..]
                .iter()
                .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
            if latest > hh {
                v1 = "空头止损";
            }
        }
    }

    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_bar_stop_V230524：按开仓点附近N根K线极值止损
///
/// 参数模板：`"{pos_name}_{freq1}N{n}K_止损V230524"`
///
/// 信号逻辑：
/// - 多头：开仓前最近 `n` 根K线最低价被最新价跌破，记 `多头止损`；
/// - 空头：开仓前最近 `n` 根K线最高价被最新价突破，记 `空头止损`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头_日线N3K_止损V230524_多头止损_任意_任意_0')`
/// - `Signal('日线三买多头_日线N3K_止损V230524_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `n`：向前取K线数量，默认 `3`，有效范围 `[1, 20]`。
#[signal(
    category = "trader",
    name = "pos_bar_stop_V230524",
    template = "{pos_name}_{freq1}N{n}K_止损V230524",
    opcode = "PosBarStopV230524",
    param_kind = "PosBarStopV230524"
)]
pub fn pos_bar_stop_v230524(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let n = get_usize_param(params, "n", 3).clamp(1, 20);
    let k1 = pos_name.to_string();
    let k2 = format!("{}N{}K", freq1, n);
    let k3 = "止损V230524";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let latest = latest_price(cat, freq1).unwrap_or(0.0);
    let start = c.bars_raw.len().saturating_sub(100);
    let mut bars: Vec<_> = c.bars_raw[start..]
        .iter()
        .filter(|x| x.dt < op.dt)
        .collect();
    if bars.len() > n {
        bars = bars[bars.len() - n..].to_vec();
    }

    if !bars.is_empty() && op.op == Operate::LO {
        let ll = bars.iter().fold(f64::INFINITY, |acc, x| acc.min(x.low));
        if latest < ll {
            v1 = "多头止损";
        }
    }
    if !bars.is_empty() && op.op == Operate::SO {
        let hh = bars
            .iter()
            .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
        if latest > hh {
            v1 = "空头止损";
        }
    }

    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_holds_V230414：开仓后 N 根K线收益与阈值比较
///
/// 参数模板：`"{pos_name}_{freq1}N{n}M{m}_趋势判断V230414"`
///
/// 信号逻辑：
/// - 多头：`zdf=(最新收盘-开仓价)/开仓价*10000`，`zdf<m` 为 `多头存疑`，否则 `多头良好`；
/// - 空头：`zdf=(开仓价-最新收盘)/开仓价*10000`，同样按 `m` 分层。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_60分钟N5M100_趋势判断V230414_多头存疑_任意_任意_0')`
/// - `Signal('日线三买多头N1_60分钟N5M100_趋势判断V230414_多头良好_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `n`：开仓后最少持有K线数量，默认 `5`；
/// - `m`：收益阈值（BP），默认 `100`。
#[signal(
    category = "trader",
    name = "pos_holds_V230414",
    template = "{pos_name}_{freq1}N{n}M{m}_趋势判断V230414",
    opcode = "PosHoldsV230414",
    param_kind = "PosHoldsV230414"
)]
pub fn pos_holds_v230414(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let n = get_usize_param(params, "n", 5);
    let m = get_usize_param(params, "m", 100);
    let k1 = pos_name.to_string();
    let k2 = format!("{}N{}M{}", freq1, n, m);
    let k3 = "趋势判断V230414";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let start = c.bars_raw.len().saturating_sub(100);
    let bars: Vec<_> = c.bars_raw[start..]
        .iter()
        .filter(|x| x.dt > op.dt)
        .collect();
    if bars.len() < n {
        return make_signal_v1(&k1, &k2, k3, v1);
    }
    let last_close = bars.last().map(|x| x.close).unwrap_or(op.price);
    if op.op == Operate::LO {
        let zdf = (last_close - op.price) / op.price * 10000.0;
        v1 = if zdf < m as f64 {
            "多头存疑"
        } else {
            "多头良好"
        };
    }
    if op.op == Operate::SO {
        let zdf = (op.price - last_close) / op.price * 10000.0;
        v1 = if zdf < m as f64 {
            "空头存疑"
        } else {
            "空头良好"
        };
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_fix_exit_V230624：固定 BP 止盈止损
///
/// 参数模板：`"{pos_name}_固定{th}BP止盈止损_出场V230624"`
///
/// 信号逻辑：
/// - 多头：现价低于 `开仓价*(1-th/10000)` 为 `多头止损`，高于 `开仓价*(1+th/10000)` 为 `多头止盈`；
/// - 空头：规则镜像为 `空头止损/空头止盈`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头_固定100BP止盈止损_出场V230624_多头止损_任意_任意_0')`
/// - `Signal('日线三买多头_固定100BP止盈止损_出场V230624_空头止盈_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `th`：止盈止损阈值（BP），默认 `300`。
#[signal(
    category = "trader",
    name = "pos_fix_exit_V230624",
    template = "{pos_name}_固定{th}BP止盈止损_出场V230624",
    opcode = "PosFixExitV230624",
    param_kind = "PosFixExitV230624"
)]
pub fn pos_fix_exit_v230624(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let th = get_usize_param(params, "th", 300);
    let k1 = pos_name.to_string();
    let k2 = format!("固定{}BP止盈止损", th);
    let k3 = "出场V230624";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let freq1 = get_str_param(params, "freq1", "");
    let lp = latest_price(cat, freq1).unwrap_or(op.price);
    if op.op == Operate::LO {
        if lp < op.price * (1.0 - th as f64 / 10000.0) {
            v1 = "多头止损";
        }
        if lp > op.price * (1.0 + th as f64 / 10000.0) {
            v1 = "多头止盈";
        }
    }
    if op.op == Operate::SO {
        if lp > op.price * (1.0 + th as f64 / 10000.0) {
            v1 = "空头止损";
        }
        if lp < op.price * (1.0 - th as f64 / 10000.0) {
            v1 = "空头止盈";
        }
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_profit_loss_V230624：盈亏比阈值判断
///
/// 参数模板：`"{pos_name}_{freq1}YKB{ykb}N{n}_盈亏比判断V230624"`
///
/// 信号逻辑：
/// - 基于开仓前 `n` 个分型确定止损价，计算 `ykb = (现价-开仓价)/(开仓价-止损价)*10`；
/// - `ykb > 阈值` 记 `多头达标/空头达标`；
/// - 未达标时若击穿止损价，记 `多头止损/空头止损`。
///
/// 信号列表示例：
/// - `Signal('日线通道突破_60分钟YKB20N3_盈亏比判断V230624_多头达标_任意_任意_0')`
/// - `Signal('日线通道突破_60分钟YKB20N3_盈亏比判断V230624_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `ykb`：盈亏比阈值（×10），默认 `20`；
/// - `n`：止损分型窗口，默认 `3`。
#[signal(
    category = "trader",
    name = "pos_profit_loss_V230624",
    template = "{pos_name}_{freq1}YKB{ykb}N{n}_盈亏比判断V230624",
    opcode = "PosProfitLossV230624",
    param_kind = "PosProfitLossV230624"
)]
pub fn pos_profit_loss_v230624(
    cat: &dyn TraderState,
    params: &ParamView,
) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let ykb = get_usize_param(params, "ykb", 20);
    let n = get_usize_param(params, "n", 3);
    let k1 = pos_name.to_string();
    let k2 = format!("{}YKB{}N{}", freq1, ykb, n);
    let k3 = "盈亏比判断V230624";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let last_close = c.bars_raw.last().map(|b| b.close).unwrap_or(op.price);
    let fxs = c.get_fx_list();

    if op.op == Operate::LO {
        let all: Vec<_> = fxs
            .iter()
            .filter(|x| x.mark == Mark::D && x.dt < op.dt)
            .collect();
        let start = all.len().saturating_sub(n);
        if !all.is_empty() {
            let stop_price = all[start..]
                .iter()
                .fold(f64::INFINITY, |acc, x| acc.min(x.low));
            let denom = op.price - stop_price;
            if denom != 0.0 {
                let y = ((last_close - op.price) / denom) * 10.0;
                if y > ykb as f64 {
                    v1 = "多头达标";
                } else if last_close < stop_price {
                    v1 = "多头止损";
                }
            }
        }
    }
    if op.op == Operate::SO {
        let all: Vec<_> = fxs
            .iter()
            .filter(|x| x.mark == Mark::G && x.dt < op.dt)
            .collect();
        let start = all.len().saturating_sub(n);
        if !all.is_empty() {
            let stop_price = all[start..]
                .iter()
                .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
            let denom = op.price - stop_price;
            if denom != 0.0 {
                let y = ((last_close - op.price) / denom) * 10.0;
                if y > ykb as f64 {
                    v1 = "空头达标";
                } else if last_close > stop_price {
                    v1 = "空头止损";
                }
            }
        }
    }

    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_status_V230808：持仓状态
///
/// 参数模板：`"{pos_name}_持仓状态_BS辅助V230808"`
///
/// 信号逻辑：
/// - 最近操作为 `LO` 输出 `持多`；
/// - 最近操作为 `SO` 输出 `持空`；
/// - 其余输出 `持币`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_持仓状态_BS辅助V230808_持多_任意_任意_0')`
/// - `Signal('日线三买多头N1_持仓状态_BS辅助V230808_持币_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称。
#[signal(
    category = "trader",
    name = "pos_status_V230808",
    template = "{pos_name}_持仓状态_BS辅助V230808",
    opcode = "PosStatusV230808",
    param_kind = "PosStatus"
)]
pub fn pos_status_v230808(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let k1 = pos_name.to_string();
    let k2 = "持仓状态";
    let k3 = "BS辅助V230808";
    let v1 = match cat.get_position(pos_name).and_then(|p| p.operates.last()) {
        Some(op) if op.op == Operate::LO => "持多",
        Some(op) if op.op == Operate::SO => "持空",
        _ => "持币",
    };
    make_signal_v1(&k1, k2, k3, v1)
}

/// pos_holds_V230807：开仓后收益在 (t, m) 之间触发保本
///
/// 参数模板：`"{pos_name}_{freq1}N{n}M{m}T{t}_BS辅助V230807"`
///
/// 信号逻辑：
/// - 当开仓后收益落在 `(t, m)` 区间时触发 `多头保本/空头保本`；
/// - 含义是“达到最低保本收益但未达到趋势确认阈值”，优先保本离场。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_60分钟N5M50T10_BS辅助V230807_多头保本_任意_任意_0')`
/// - `Signal('日线三买多头N1_60分钟N5M50T10_BS辅助V230807_空头保本_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `n`：最少持有K线数量，默认 `5`；
/// - `m`：收益上限阈值（BP），默认 `50`；
/// - `t`：保本收益阈值（BP），默认 `10`，且要求 `m > t > 0`。
#[signal(
    category = "trader",
    name = "pos_holds_V230807",
    template = "{pos_name}_{freq1}N{n}M{m}T{t}_BS辅助V230807",
    opcode = "PosHoldsV230807",
    param_kind = "PosHoldsV230807"
)]
pub fn pos_holds_v230807(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let n = get_usize_param(params, "n", 5);
    let m = get_usize_param(params, "m", 50);
    let t = get_usize_param(params, "t", 10);
    let k1 = pos_name.to_string();
    let k2 = format!("{}N{}M{}T{}", freq1, n, m, t);
    let k3 = "BS辅助V230807";
    let mut v1 = "其他";
    if m <= t || t == 0 {
        return make_signal_v1(&k1, &k2, k3, v1);
    }
    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let start = c.bars_raw.len().saturating_sub(100);
    let bars: Vec<_> = c.bars_raw[start..]
        .iter()
        .filter(|x| x.dt > op.dt)
        .collect();
    if bars.len() < n {
        return make_signal_v1(&k1, &k2, k3, v1);
    }
    let last_close = bars.last().map(|x| x.close).unwrap_or(op.price);
    if op.op == Operate::LO {
        let zdf = (last_close - op.price) / op.price * 10000.0;
        if zdf > t as f64 && zdf < m as f64 {
            v1 = "多头保本";
        }
    }
    if op.op == Operate::SO {
        let zdf = (op.price - last_close) / op.price * 10000.0;
        if zdf > t as f64 && zdf < m as f64 {
            v1 = "空头保本";
        }
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_holds_V240428：最大盈利回撤比例保本
///
/// 参数模板：`"{pos_name}_{freq1}H{h}T{t}N{n}_保本V240428"`
///
/// 信号逻辑：
/// - 多头：最大盈利 `y1` 超过 `h` 且当前盈利 `y2 < y1*t/100`，记 `多头保本`；
/// - 空头：按镜像规则记 `空头保本`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_60分钟H100T20N5_保本V240428_多头保本_任意_任意_0')`
/// - `Signal('日线三买多头N1_60分钟H100T20N5_保本V240428_空头保本_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `h`：最大盈利阈值（BP），默认 `100`；
/// - `t`：回撤比例阈值（%），默认 `20`；
/// - `n`：最少持有K线数量，默认 `5`。
#[signal(
    category = "trader",
    name = "pos_holds_V240428",
    template = "{pos_name}_{freq1}H{h}T{t}N{n}_保本V240428",
    opcode = "PosHoldsV240428",
    param_kind = "PosHoldsV240428"
)]
pub fn pos_holds_v240428(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let h = get_usize_param(params, "h", 100);
    let t = get_usize_param(params, "t", 20);
    let n = get_usize_param(params, "n", 5);
    let k1 = pos_name.to_string();
    let k2 = format!("{}H{}T{}N{}", freq1, h, t, n);
    let k3 = "保本V240428";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let start = c.bars_raw.len().saturating_sub(100);
    let bars: Vec<_> = c.bars_raw[start..]
        .iter()
        .filter(|x| x.dt > op.dt)
        .collect();
    if bars.len() < n {
        return make_signal_v1(&k1, &k2, k3, v1);
    }
    let last_close = bars.last().map(|x| x.close).unwrap_or(op.price);

    if op.op == Operate::LO {
        let max_close = bars
            .iter()
            .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.close));
        let y1 = (max_close - op.price) / op.price * 10000.0;
        let y2 = (last_close - op.price) / op.price * 10000.0;
        if y1 > h as f64 && y2 < y1 * t as f64 / 100.0 {
            v1 = "多头保本";
        }
    }
    if op.op == Operate::SO {
        let min_close = bars.iter().fold(f64::INFINITY, |acc, x| acc.min(x.close));
        let y1 = (op.price - min_close) / op.price * 10000.0;
        let y2 = (op.price - last_close) / op.price * 10000.0;
        if y1 > h as f64 && y2 < y1 * t as f64 / 100.0 {
            v1 = "空头保本";
        }
    }

    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_holds_V240608：跌破/升破开仓前窗口极值后，回到成本价指定档位保本
///
/// 参数模板：`"{pos_name}_{freq1}W{w}N{n}_保本V240608"`
///
/// 信号逻辑：
/// - 多头：若开仓后最低价跌破开仓前 `w` 根最低价，且现价回到成本价上方第 `n` 档，记 `多头保本`；
/// - 空头：若开仓后最高价突破开仓前 `w` 根最高价，且现价回到成本价下方第 `n` 档，记 `空头保本`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_60分钟W20N2_保本V240608_多头保本_任意_任意_0')`
/// - `Signal('日线三买多头N1_60分钟W20N2_保本V240608_空头保本_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `w`：开仓前观察窗口，默认 `20`；
/// - `n`：成本价上下档位偏移，默认 `2`。
#[signal(
    category = "trader",
    name = "pos_holds_V240608",
    template = "{pos_name}_{freq1}W{w}N{n}_保本V240608",
    opcode = "PosHoldsV240608",
    param_kind = "PosHoldsV240608"
)]
pub fn pos_holds_v240608(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let w = get_usize_param(params, "w", 20);
    let n = get_usize_param(params, "n", 2);
    let k1 = pos_name.to_string();
    let k2 = format!("{}W{}N{}", freq1, w, n);
    let k3 = "保本V240608";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };

    let s200 = c.bars_raw.len().saturating_sub(200);
    let w_bars_all: Vec<_> = c.bars_raw[s200..]
        .iter()
        .filter(|x| x.dt <= op.dt)
        .collect();
    let w_bars = if w_bars_all.len() > w {
        &w_bars_all[w_bars_all.len() - w..]
    } else {
        &w_bars_all[..]
    };
    let s100 = c.bars_raw.len().saturating_sub(100);
    let a_bars: Vec<_> = c.bars_raw[s100..].iter().filter(|x| x.dt > op.dt).collect();
    if w_bars.is_empty() || a_bars.is_empty() {
        return make_signal_v1(&k1, &k2, k3, v1);
    }

    let mut unique_prices: Vec<f64> = c.bars_raw[s200..]
        .iter()
        .flat_map(|x| [x.high, x.low, x.close, x.open])
        .collect();
    unique_prices.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    unique_prices.dedup_by(|a, b| (*a - *b).abs() < f64::EPSILON);
    let lp = latest_price(cat, freq1).unwrap_or(op.price);

    if op.op == Operate::LO {
        let w_low = w_bars.iter().fold(f64::INFINITY, |acc, x| acc.min(x.low));
        let a_low = a_bars.iter().fold(f64::INFINITY, |acc, x| acc.min(x.low));
        let up_prices: Vec<f64> = unique_prices
            .iter()
            .copied()
            .filter(|x| *x > op.price)
            .collect();
        if up_prices.len() > n && a_low < w_low && lp > up_prices[n] {
            v1 = "多头保本";
        }
    }
    if op.op == Operate::SO {
        let w_high = w_bars
            .iter()
            .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
        let a_high = a_bars
            .iter()
            .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
        let down_prices: Vec<f64> = unique_prices
            .iter()
            .copied()
            .filter(|x| *x < op.price)
            .collect();
        if down_prices.len() > n && a_high > w_high && lp < down_prices[down_prices.len() - n] {
            v1 = "空头保本";
        }
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_stop_V240428：按开仓前离散价位跳数止损
///
/// 参数模板：`"{pos_name}_{freq1}T{t}N{n}_止损V240428"`
///
/// 信号逻辑：
/// - 使用开仓前历史K线提取离散价位；
/// - 多头取低于开仓价的第 `t` 档止损位，空头取高于开仓价的第 `t` 档止损位；
/// - 开仓后至少持有 `n` 根后，收盘穿越止损位触发 `多头止损/空头止损`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_60分钟T20N5_止损V240428_多头止损_任意_任意_0')`
/// - `Signal('日线三买多头N1_60分钟T20N5_止损V240428_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `t`：离散价位档位，默认 `20`；
/// - `n`：最少持有K线数量，默认 `5`。
#[signal(
    category = "trader",
    name = "pos_stop_V240428",
    template = "{pos_name}_{freq1}T{t}N{n}_止损V240428",
    opcode = "PosStopV240428",
    param_kind = "PosStopV240428"
)]
pub fn pos_stop_v240428(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let t = get_usize_param(params, "t", 20);
    let n = get_usize_param(params, "n", 5);
    let k1 = pos_name.to_string();
    let k2 = format!("{}T{}N{}", freq1, t, n);
    let k3 = "止损V240428";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let s100 = c.bars_raw.len().saturating_sub(100);
    let right_bars: Vec<_> = c.bars_raw[s100..].iter().filter(|x| x.dt > op.dt).collect();
    if right_bars.len() < n {
        return make_signal_v1(&k1, &k2, k3, v1);
    }
    let left_bars: Vec<_> = c.bars_raw.iter().filter(|x| x.dt < op.dt).collect();
    let mut unique_prices: Vec<f64> = left_bars
        .iter()
        .flat_map(|x| [x.high, x.low, x.close, x.open])
        .collect();
    unique_prices.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    unique_prices.dedup_by(|a, b| (*a - *b).abs() < f64::EPSILON);

    if op.op == Operate::LO {
        let mut low_prices: Vec<f64> = unique_prices
            .iter()
            .copied()
            .filter(|x| *x < op.price)
            .collect();
        low_prices.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
        if low_prices.is_empty() {
            return make_signal_v1(&k1, &k2, k3, v1);
        }
        let y = if low_prices.len() > t {
            low_prices[low_prices.len() - t]
        } else {
            low_prices[0]
        };
        if right_bars.last().map(|b| b.close).unwrap_or(op.price) < y {
            v1 = "多头止损";
        }
    }
    if op.op == Operate::SO {
        let mut high_prices: Vec<f64> = unique_prices
            .iter()
            .copied()
            .filter(|x| *x > op.price)
            .collect();
        high_prices.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
        if high_prices.is_empty() {
            return make_signal_v1(&k1, &k2, k3, v1);
        }
        let y = if high_prices.len() > t {
            high_prices[t]
        } else {
            high_prices[high_prices.len() - 1]
        };
        if right_bars.last().map(|b| b.close).unwrap_or(op.price) > y {
            v1 = "空头止损";
        }
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_take_V240428：倍量阳/阴线计数止盈
///
/// 参数模板：`"{pos_name}_{freq1}T{t}N{n}_止盈V240428"`
///
/// 信号逻辑：
/// - 多头统计开仓后“阳线且成交量 > 前一根 2 倍”的次数，达到 `t` 触发 `多头止盈`；
/// - 空头统计对应倍量阴线次数，达到 `t` 触发 `空头止盈`。
///
/// 信号列表示例：
/// - `Signal('日线三买多头N1_60分钟T3N5_止盈V240428_多头止盈_任意_任意_0')`
/// - `Signal('日线三买多头N1_60分钟T3N5_止盈V240428_空头止盈_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `t`：倍量K线数量阈值，默认 `3`；
/// - `n`：最少持有K线数量，默认 `5`。
#[signal(
    category = "trader",
    name = "pos_take_V240428",
    template = "{pos_name}_{freq1}T{t}N{n}_止盈V240428",
    opcode = "PosTakeV240428",
    param_kind = "PosTakeV240428"
)]
pub fn pos_take_v240428(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let t = get_usize_param(params, "t", 3);
    let n = get_usize_param(params, "n", 5);
    let k1 = pos_name.to_string();
    let k2 = format!("{}T{}N{}", freq1, t, n);
    let k3 = "止盈V240428";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let s100 = c.bars_raw.len().saturating_sub(100);
    let bars: Vec<_> = c.bars_raw[s100..].iter().filter(|x| x.dt > op.dt).collect();
    if bars.len() < n {
        return make_signal_v1(&k1, &k2, k3, v1);
    }
    if op.op == Operate::LO {
        let mut c1 = 0usize;
        for i in 1..bars.len() {
            if bars[i].close > bars[i].open && bars[i].vol > bars[i - 1].vol * 2.0 {
                c1 += 1;
            }
        }
        if c1 >= t {
            v1 = "多头止盈";
        }
    }
    if op.op == Operate::SO {
        let mut c2 = 0usize;
        for i in 1..bars.len() {
            if bars[i].close < bars[i].open && bars[i].vol > bars[i - 1].vol * 2.0 {
                c2 += 1;
            }
        }
        if c2 >= t {
            v1 = "空头止盈";
        }
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_stop_V240331：最近 N 根K线追踪止损
///
/// 参数模板：`"{pos_name}_{freq1}#{n}_止损V240331"`
///
/// 信号逻辑：
/// - 多头：最新K线低点跌破前 `n` 根最低价且 bar_id 晚于开仓 bar，触发 `多头止损`；
/// - 空头：最新K线高点突破前 `n` 根最高价且 bar_id 晚于开仓 bar，触发 `空头止损`。
///
/// 信号列表示例：
/// - `Signal('SMA5多头_15分钟#10_止损V240331_多头止损_任意_任意_0')`
/// - `Signal('SMA5空头_15分钟#10_止损V240331_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `n`：追踪窗口，默认 `10`。
#[signal(
    category = "trader",
    name = "pos_stop_V240331",
    template = "{pos_name}_{freq1}#{n}_止损V240331",
    opcode = "PosStopV240331",
    param_kind = "PosStopV240331"
)]
pub fn pos_stop_v240331(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let n = get_usize_param(params, "n", 10);
    let k1 = pos_name.to_string();
    let k2 = format!("{}#{}", freq1, n);
    let k3 = "止损V240331";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let bars = get_sub_elements(&c.bars_raw, 1, n + 1);
    if bars.len() < n + 1 {
        return make_signal_v1(&k1, &k2, k3, v1);
    }
    let last_bar = match bars.last() {
        Some(x) => x,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    if op.op == Operate::LO {
        let ll = bars[..bars.len() - 1]
            .iter()
            .fold(f64::INFINITY, |acc, x| acc.min(x.low));
        if last_bar.low < ll && last_bar.id > op.bar_id {
            v1 = "多头止损";
        }
    }
    if op.op == Operate::SO {
        let hh = bars[..bars.len() - 1]
            .iter()
            .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
        if last_bar.high > hh && last_bar.id > op.bar_id {
            v1 = "空头止损";
        }
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_stop_V240608：开仓后突破开仓前窗口极值 N 档止损
///
/// 参数模板：`"{pos_name}_{freq1}W{w}N{n}_止损V240608"`
///
/// 信号逻辑：
/// - 多头：开仓后最低价低于“开仓前 `w` 根最低价下方第 `n` 档”触发 `多头止损`；
/// - 空头：开仓后最高价高于“开仓前 `w` 根最高价上方第 `n` 档”触发 `空头止损`。
///
/// 信号列表示例：
/// - `Signal('SMA5多头_15分钟W20N10_止损V240608_多头止损_任意_任意_0')`
/// - `Signal('SMA5空头_15分钟W20N10_止损V240608_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `w`：开仓前观察窗口，默认 `20`；
/// - `n`：上下档位偏移，默认 `10`。
#[signal(
    category = "trader",
    name = "pos_stop_V240608",
    template = "{pos_name}_{freq1}W{w}N{n}_止损V240608",
    opcode = "PosStopV240608",
    param_kind = "PosStopV240608"
)]
pub fn pos_stop_v240608(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let w = get_usize_param(params, "w", 20);
    let n = get_usize_param(params, "n", 10);
    let k1 = pos_name.to_string();
    let k2 = format!("{}W{}N{}", freq1, w, n);
    let k3 = "止损V240608";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };

    let w_all: Vec<_> = c.bars_raw.iter().filter(|x| x.dt < op.dt).collect();
    let w_bars = if w_all.len() > w {
        &w_all[w_all.len() - w..]
    } else {
        &w_all[..]
    };
    let s100 = c.bars_raw.len().saturating_sub(100);
    let a_bars: Vec<_> = c.bars_raw[s100..].iter().filter(|x| x.dt > op.dt).collect();
    if w_bars.is_empty() || a_bars.is_empty() {
        return make_signal_v1(&k1, &k2, k3, v1);
    }

    let s200 = c.bars_raw.len().saturating_sub(200);
    let mut unique_prices: Vec<f64> = c.bars_raw[s200..]
        .iter()
        .flat_map(|x| [x.high, x.low, x.close, x.open])
        .collect();
    unique_prices.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    unique_prices.dedup_by(|a, b| (*a - *b).abs() < f64::EPSILON);

    if op.op == Operate::LO {
        let w_low = w_bars.iter().fold(f64::INFINITY, |acc, x| acc.min(x.low));
        let a_low = a_bars.iter().fold(f64::INFINITY, |acc, x| acc.min(x.low));
        let w_low_prices: Vec<f64> = unique_prices
            .iter()
            .copied()
            .filter(|x| *x < w_low)
            .collect();
        if w_low_prices.len() > n && a_low < w_low_prices[w_low_prices.len() - n] {
            v1 = "多头止损";
        }
    }
    if op.op == Operate::SO {
        let w_high = w_bars
            .iter()
            .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
        let a_high = a_bars
            .iter()
            .fold(f64::NEG_INFINITY, |acc, x| acc.max(x.high));
        let w_high_prices: Vec<f64> = unique_prices
            .iter()
            .copied()
            .filter(|x| *x > w_high)
            .collect();
        if w_high_prices.len() > n && a_high > w_high_prices[n] {
            v1 = "空头止损";
        }
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_stop_V240614：开仓后低于/高于成本价的 K线数量计数止损
///
/// 参数模板：`"{pos_name}_{freq1}N{n}_止损V240614"`
///
/// 信号逻辑：
/// - 多头：开仓后 `low < 开仓价` 的K线数量达到 `n`，触发 `多头止损`；
/// - 空头：开仓后 `high > 开仓价` 的K线数量达到 `n`，触发 `空头止损`。
///
/// 信号列表示例：
/// - `Signal('SMA5多头_15分钟N10_止损V240614_多头止损_任意_任意_0')`
/// - `Signal('SMA5空头_15分钟N10_止损V240614_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `n`：计数阈值，默认 `10`。
#[signal(
    category = "trader",
    name = "pos_stop_V240614",
    template = "{pos_name}_{freq1}N{n}_止损V240614",
    opcode = "PosStopV240614",
    param_kind = "PosStopV240614"
)]
pub fn pos_stop_v240614(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let n = get_usize_param(params, "n", 10);
    let k1 = pos_name.to_string();
    let k2 = format!("{}N{}", freq1, n);
    let k3 = "止损V240614";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let a_bars: Vec<_> = c.bars_raw.iter().filter(|x| x.dt >= op.dt).collect();
    if op.op == Operate::LO && a_bars.iter().filter(|x| x.low < op.price).count() >= n {
        v1 = "多头止损";
    }
    if op.op == Operate::SO && a_bars.iter().filter(|x| x.high > op.price).count() >= n {
        v1 = "空头止损";
    }
    make_signal_v1(&k1, &k2, k3, v1)
}

/// pos_stop_V240717：基于开仓时 ATR 的计数止损
///
/// 参数模板：`"{pos_name}_{freq1}N{n}T{timeperiod}_止损V240717"`
///
/// 信号逻辑：
/// - 先取开仓时刻 ATR(`timeperiod`)；
/// - 多头阈值为 `开仓价 - ATR*0.67`，空头阈值为 `开仓价 + ATR*0.67`；
/// - 开仓后超过阈值的K线数量达到 `n` 时触发 `多头止损/空头止损`。
///
/// 信号列表示例：
/// - `Signal('SMA5多头_15分钟N3T20_止损V240717_多头止损_任意_任意_0')`
/// - `Signal('SMA5空头_15分钟N3T20_止损V240717_空头止损_任意_任意_0')`
///
/// 参数说明：
/// - `pos_name`：仓位名称；
/// - `freq1`：K线周期；
/// - `n`：计数阈值，默认 `10`；
/// - `timeperiod`：ATR 周期，默认 `20`。
#[signal(
    category = "trader",
    name = "pos_stop_V240717",
    template = "{pos_name}_{freq1}N{n}T{timeperiod}_止损V240717",
    opcode = "PosStopV240717",
    param_kind = "PosStopV240717"
)]
pub fn pos_stop_v240717(cat: &dyn TraderState, params: &ParamView) -> Vec<Signal> {
    let pos_name = get_str_param(params, "pos_name", "");
    let freq1 = get_str_param(params, "freq1", "");
    let n = get_usize_param(params, "n", 10);
    let timeperiod = get_usize_param(params, "timeperiod", 20);
    let k1 = pos_name.to_string();
    let k2 = format!("{}N{}T{}", freq1, n, timeperiod);
    let k3 = "止损V240717";
    let mut v1 = "其他";

    let op = match last_open_operate(cat, pos_name) {
        Some(op) => op,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let c = match cat.get_czsc(freq1) {
        Some(c) => c,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    let cache_key = format!("ATR#{}", timeperiod);
    let mut ta_cache = TaCache::new();
    update_atr_cache(c, &cache_key, timeperiod, &mut ta_cache);
    let atr_series = match ta_cache.series.get(&cache_key) {
        Some(v) => v,
        None => return make_signal_v1(&k1, &k2, k3, v1),
    };
    // 对齐 Python:
    // atr = [x.cache[cache_key] if x.cache.get(cache_key) is not None else 0
    //        for x in c.bars_raw if x.dt == op["dt"]][0]
    let atr = c
        .bars_raw
        .iter()
        .enumerate()
        .find_map(|(i, b)| {
            if b.dt == op.dt.with_timezone(&chrono::Utc) {
                Some(*atr_series.get(i).unwrap_or(&0.0))
            } else {
                None
            }
        })
        .unwrap_or(0.0);
    let a_bars: Vec<_> = c.bars_raw.iter().filter(|x| x.dt >= op.dt).collect();

    if op.op == Operate::LO
        && a_bars
            .iter()
            .filter(|x| x.low < op.price - atr * 0.67)
            .count()
            >= n
    {
        v1 = "多头止损";
    }
    if op.op == Operate::SO
        && a_bars
            .iter()
            .filter(|x| x.high > op.price + atr * 0.67)
            .count()
            >= n
    {
        v1 = "空头止损";
    }
    make_signal_v1(&k1, &k2, k3, v1)
}
