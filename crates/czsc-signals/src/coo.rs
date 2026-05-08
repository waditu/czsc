use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{get_sub_elements, make_kline_signal_v1, make_kline_signal_v2};
use crate::utils::ta::{update_cci_cache, update_kdj_cache, update_ma_cache, update_sar_cache};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_signal_macros::signal;

fn cal_td_seq(close: &[f64]) -> Vec<i32> {
    if close.len() < 5 {
        return vec![0; close.len()];
    }
    let mut res = vec![0; close.len()];
    for i in 4..close.len() {
        if close[i] > close[i - 4] {
            res[i] = res[i - 1] + 1;
        } else if close[i] < close[i - 4] {
            res[i] = res[i - 1] - 1;
        }
    }
    res
}

fn td_signal_from_close(close: &[f64]) -> (&'static str, &'static str) {
    let td = cal_td_seq(close);
    let x = *td.last().unwrap_or(&0);
    if x > 0 {
        let v1 = if td.len() > 1 && td[td.len() - 2] < -8 {
            "看多"
        } else {
            "延续"
        };
        let v2 = if x > 8 { "TD顶" } else { "非顶" };
        (v1, v2)
    } else if x < 0 {
        let v1 = if td.len() > 1 && td[td.len() - 2] > 8 {
            "看空"
        } else {
            "延续"
        };
        let v2 = if x < -8 { "TD底" } else { "非底" };
        (v1, v2)
    } else {
        ("其他", "其他")
    }
}

/// coo_td_V221110：TD 神奇九转信号（旧版模板）
///
/// 参数模板：`"{freq}_D{di}K_TD"`
///
/// 信号逻辑：
/// 1. 取倒数 `di` 截止的最近 50 根收盘价；
/// 2. 按 `close[i]` 与 `close[i-4]` 比较累计 TD 计数；
/// 3. 根据最新 TD 值及前一值输出 `看多/看空/延续` 与 `TD顶/TD底/非顶/非底`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K_TD_延续_非顶_任意_0')`
/// - `Signal('60分钟_D1K_TD_看空_TD底_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `coo_td_V221110` 的 TD 计数递推一致。
#[signal(
    category = "kline",
    name = "coo_td_V221110",
    template = "{freq}_D{di}K_TDV221110",
    opcode = "CooTdV221110",
    param_kind = "CooTdV221110"
)]
pub fn coo_td_v221110(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K", di);
    let k3 = "TD";
    let bars = get_sub_elements(&c.bars_raw, di, 50);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let close: Vec<f64> = bars.iter().map(|x| x.close).collect();
    let (v1, v2) = td_signal_from_close(&close);
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// coo_td_V221111：TD 神奇九转信号
///
/// 参数模板：`"{freq}_D{di}TD_BS辅助V221111"`
///
/// 信号逻辑：
/// 1. 取倒数 `di` 截止的最近 50 根收盘价；
/// 2. 计算 TD 计数序列；
/// 3. 输出 `看多/看空/延续` 与 `TD顶/TD底/非顶/非底` 组合。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1TD_BS辅助V221111_延续_非顶_任意_0')`
/// - `Signal('60分钟_D1TD_BS辅助V221111_看多_TD顶_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：与 Python `coo_td_V221111` 的窗口和判定分支一致。
#[signal(
    category = "kline",
    name = "coo_td_V221111",
    template = "{freq}_D{di}TD_BS辅助V221111",
    opcode = "CooTdV221111",
    param_kind = "CooTdV221111"
)]
pub fn coo_td_v221111(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TD", di);
    let k3 = "BS辅助V221111";
    if c.bars_raw.len() < 50 + di {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, 50);
    let close: Vec<f64> = bars.iter().map(|x| x.close).collect();
    let (v1, v2) = td_signal_from_close(&close);
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// coo_cci_V230323：CCI 结合均线的多空与方向信号
///
/// 参数模板：`"{freq}_D{di}CCI{n}#{ma_type}#{m}_BS辅助V230323"`
///
/// 信号逻辑：
/// 1. 计算 `CCI(n)` 与 `MA(n*m)`；
/// 2. `CCI>100` 且 `close>MA` 判 `多头`，`CCI<-100` 且 `close<MA` 判 `空头`；
/// 3. 若非 `其他`，再比较前后两根 CCI 输出 `向上/向下`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1CCI20#SMA#5_BS辅助V230323_多头_向上_任意_0')`
/// - `Signal('60分钟_D1CCI20#SMA#5_BS辅助V230323_空头_向下_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：CCI 周期，默认 `20`；
/// - `m`：均线倍数（最终周期 `n*m`），默认 `5`；
/// - `ma_type`：均线类型，默认 `SMA`。
/// 对齐说明：与 Python `coo_cci_V230323` 的阈值和方向判定一致。
#[signal(
    category = "kline",
    name = "coo_cci_V230323",
    template = "{freq}_D{di}CCI{n}#{ma_type}#{m}_BS辅助V230323",
    opcode = "CooCciV230323",
    param_kind = "CooCciV230323"
)]
pub fn coo_cci_v230323(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 20);
    let m = params.usize("m", 5);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();

    let cci_key = format!("CCI{}", n);
    let ma_key = format!("{}#{}", ma_type, n * m);
    update_cci_cache(c, &cci_key, n, cache);
    update_ma_cache(c, &ma_key, &ma_type, n * m, cache);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}CCI{}#{}#{}", di, n, ma_type, m);
    let k3 = "BS辅助V230323";
    if c.bars_raw.len() < n * m + di {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    if c.bars_raw.len() < di + 1 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let idx = c.bars_raw.len() - di;
    let prev_idx = idx.saturating_sub(1);
    let cci = cache
        .series
        .get(&cci_key)
        .and_then(|x| x.get(idx))
        .copied()
        .unwrap_or(f64::NAN);
    let cci_prev = cache
        .series
        .get(&cci_key)
        .and_then(|x| x.get(prev_idx))
        .copied()
        .unwrap_or(f64::NAN);
    let ma = cache
        .series
        .get(&ma_key)
        .and_then(|x| x.get(idx))
        .copied()
        .unwrap_or(f64::NAN);
    let close = c.bars_raw[idx].close;

    let mut v1 = "其他";
    if cci > 100.0 && close > ma {
        v1 = "多头";
    }
    if cci < -100.0 && close < ma {
        v1 = "空头";
    }
    if v1 == "其他" {
        return make_kline_signal_v1(&k1, &k2, k3, v1);
    }
    let v2 = if cci >= cci_prev { "向上" } else { "向下" };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// coo_kdj_V230322：均线与 KDJ 配合多空信号
///
/// 参数模板：`"{freq}_D{di}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{ma_type}#{n}_BS辅助V230322"`
///
/// 信号逻辑：
/// 1. 计算 `KDJ` 与 `MA(n)`；
/// 2. `close > MA` 且 `K < D` 判 `多头`；
/// 3. `close < MA` 且 `K > D` 判 `空头`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1KDJ9#3#3#EMA#3_BS辅助V230322_多头_任意_任意_0')`
/// - `Signal('60分钟_D1KDJ9#3#3#EMA#3_BS辅助V230322_空头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：均线周期，默认 `3`；
/// - `ma_type`：均线类型，默认 `EMA`；
/// - `fastk_period/slowk_period/slowd_period`：KDJ 参数，默认 `9/3/3`。
/// 对齐说明：与 Python `coo_kdj_V230322` 的组合条件一致。
#[signal(
    category = "kline",
    name = "coo_kdj_V230322",
    template = "{freq}_D{di}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{ma_type}#{n}_BS辅助V230322",
    opcode = "CooKdjV230322",
    param_kind = "CooKdjV230322"
)]
pub fn coo_kdj_v230322(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 3);
    let ma_type = params.str("ma_type", "EMA").to_uppercase();
    let fastk_period = params.usize("fastk_period", 9);
    let slowk_period = params.usize("slowk_period", 3);
    let slowd_period = params.usize("slowd_period", 3);

    let ma_key = format!("{}#{}", ma_type, n);
    let kdj_key = format!("KDJ{}#{}#{}", fastk_period, slowk_period, slowd_period);
    update_ma_cache(c, &ma_key, &ma_type, n, cache);
    update_kdj_cache(
        c,
        &kdj_key,
        fastk_period,
        slowk_period,
        slowd_period,
        cache,
    );

    let k1 = c.freq.to_string();
    let k2 = format!(
        "D{}KDJ{}#{}#{}#{}#{}",
        di, fastk_period, slowk_period, slowd_period, ma_type, n
    );
    let k3 = "BS辅助V230322";
    if c.bars_raw.len() < fastk_period * slowk_period + di {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let idx = c.bars_raw.len() - di;
    let close = c.bars_raw[idx].close;
    let ma = cache
        .series
        .get(&ma_key)
        .and_then(|x| x.get(idx))
        .copied()
        .unwrap_or(f64::NAN);
    let (k, d) = match cache.kdj.get(&kdj_key) {
        Some(kdj) => (
            kdj.k.get(idx).copied().unwrap_or(f64::NAN),
            kdj.d.get(idx).copied().unwrap_or(f64::NAN),
        ),
        None => (f64::NAN, f64::NAN),
    };
    let v1 = if close > ma && k < d {
        "多头"
    } else if close < ma && k > d {
        "空头"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// coo_sar_V230325：SAR 与区间极值配合信号
///
/// 参数模板：`"{freq}_D{di}N{n}SAR_BS辅助V230325"`
///
/// 信号逻辑：
/// 1. 计算最近 `n` 根收盘价区间高低点；
/// 2. 若 `close > SAR` 且 `high >= 区间最高收盘` 判 `多头`；
/// 3. 若 `close < SAR` 且 `low <= 区间最低收盘` 判 `空头`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N60SAR_BS辅助V230325_多头_任意_任意_0')`
/// - `Signal('60分钟_D1N60SAR_BS辅助V230325_空头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：区间窗口，默认 `60`。
/// 对齐说明：与 Python `coo_sar_V230325` 的 SAR 与区间条件一致。
#[signal(
    category = "kline",
    name = "coo_sar_V230325",
    template = "{freq}_D{di}N{n}SAR_BS辅助V230325",
    opcode = "CooSarV230325",
    param_kind = "CooSarV230325"
)]
pub fn coo_sar_v230325(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 60);
    let sar_key = "SAR".to_string();
    update_sar_cache(c, &sar_key, cache);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}SAR", di, n);
    let k3 = "BS辅助V230325";
    if c.bars_raw.len() < n + di + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let hhv = bars.iter().map(|x| x.close).fold(f64::NEG_INFINITY, f64::max);
    let llv = bars.iter().map(|x| x.close).fold(f64::INFINITY, f64::min);
    let idx = c.bars_raw.len() - di;
    let sar = cache
        .series
        .get(&sar_key)
        .and_then(|x| x.get(idx))
        .copied()
        .unwrap_or(f64::NAN);
    let last = &c.bars_raw[idx];
    let close = last.close;

    let mut v1 = "其他";
    if close > sar && last.high >= hhv {
        v1 = "多头";
    }
    if close < sar && last.low <= llv {
        v1 = "空头";
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
