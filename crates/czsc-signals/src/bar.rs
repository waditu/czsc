use crate::params::ParamView;
use crate::types::TaCache;
use crate::utils::sig::{
    get_sub_elements, intraday_time_segment, make_kline_signal_v1, make_kline_signal_v2,
    make_kline_signal_v3, minute_freq_end_time, pd_cut_last_label, qcut_last_label, weekday_cn,
};
use crate::utils::ta::{update_ma_cache, update_macd_cache};
use czsc_core::analyze::CZSC;
use czsc_core::objects::signal::Signal;
use czsc_core::utils::corr::LinearRegression;
use czsc_signal_macros::signal;
use std::collections::HashMap;

/// bar_single_V230506：单K趋势分层信号
///
/// 参数模板：`"{freq}_D{di}单K趋势N{n}_BS辅助V230506"`
///
/// 信号逻辑：
/// 1. 取截止到倒数第 `di` 根的最近 100 根K线；
/// 2. 计算每根K线因子 `(close-open)/(open*vol)`；
/// 3. 参考 Python `pd.cut(..., n)` 将末根因子分层，输出 `第1层 ~ 第n层`；
/// 4. 若样本不足或存在 `open=0/vol=0`，返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1单K趋势N5_BS辅助V230506_第3层_任意_任意_0')`
/// - `Signal('60分钟_D1单K趋势N5_BS辅助V230506_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
/// - `n`：分层数量，默认 `5`。
#[signal(
    category = "kline",
    name = "bar_single_V230506",
    template = "{freq}_D{di}单K趋势N{n}_BS辅助V230506",
    opcode = "BarSingleV230506",
    param_kind = "BarSingleV230506"
)]
pub fn bar_single_v230506(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}单K趋势N{}", di, n);
    let k3 = "BS辅助V230506";

    let mut v1 = "其他".to_string();

    if c.bars_raw.len() >= 100 + di {
        let bars = get_sub_elements(&c.bars_raw, di, 100);
        if bars.len() < 100 {
            return make_kline_signal_v1(&k1, &k2, k3, &v1);
        }
        let mut factors = Vec::with_capacity(100);
        let mut valid = true;
        for bar in bars {
            // 与 Python bar_single_V230506 对齐：
            // factors = [(x.close / x.open - 1) / x.vol for x in bars]
            // 当 open/vol 为 0 时，Python 实测会走 safe 包装并回退为“其他”。
            // 这里直接对齐为默认信号，而不是返回空键。
            if bar.open == 0.0 || bar.vol == 0.0 {
                valid = false;
                break;
            }
            factors.push((bar.close - bar.open) / (bar.open * bar.vol));
        }

        if valid && !factors.is_empty() {
            if let Some(q) = pd_cut_last_label(&factors, n) {
                v1 = format!("第{}层", q);
            }
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// bar_zdt_V230331：涨跌停识别信号
///
/// 参数模板：`"{freq}_D{di}_涨跌停V230331"`
///
/// 信号逻辑：
/// 1. 取倒数第 `di` 根与其前一根K线；
/// 2. 若当前K线收盘等于最高且不低于前收，记为 `涨停`；
/// 3. 若当前K线收盘等于最低且不高于前收，记为 `跌停`；
/// 4. 否则记为 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1_涨跌停V230331_涨停_任意_任意_0')`
/// - `Signal('60分钟_D1_涨跌停V230331_跌停_任意_任意_0')`
/// - `Signal('60分钟_D1_涨跌停V230331_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`。
#[signal(
    category = "kline",
    name = "bar_zdt_V230331",
    template = "{freq}_D{di}_涨跌停V230331",
    opcode = "BarZdtV230331",
    param_kind = "BarZdtV230331"
)]
pub fn bar_zdt_v230331(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}", di);
    let k3 = "涨跌停V230331";
    let mut v1 = "其他".to_string();

    let bars = get_sub_elements(&c.bars_raw, di, 2);
    if bars.len() == 2 {
        let b2 = &bars[0];
        let b1 = &bars[1];

        let is_close_high = (b1.close - b1.high).abs() < 1e-6;
        let is_close_low = (b1.close - b1.low).abs() < 1e-6;

        if is_close_high && b1.close >= b2.close {
            v1 = "涨停".to_string();
        } else if is_close_low && b1.close <= b2.close {
            v1 = "跌停".to_string();
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// bar_triple_V230506：三K加速形态信号
///
/// 参数模板：`"{freq}_D{di}三K加速_裸K形态V230506"`
///
/// 信号逻辑：
/// 1. 取倒数第 `di` 根开始的最近3根K线；
/// 2. 三根连续阳线判定 `三连涨`，若高低点依次抬升判定 `新高涨`；
/// 3. 三根连续阴线判定 `三连跌`，若高低点依次下降判定 `新低跌`；
/// 4. 若已形成形态，再按成交量关系细分为 `依次放量/依次缩量/量柱无序`；
/// 5. 数据不足时返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1三K加速_裸K形态V230506_新高涨_依次放量_任意_0')`
/// - `Signal('60分钟_D1三K加速_裸K形态V230506_三连跌_量柱无序_任意_0')`
/// - `Signal('60分钟_D1三K加速_裸K形态V230506_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`。
#[signal(
    category = "kline",
    name = "bar_triple_V230506",
    template = "{freq}_D{di}三K加速_裸K形态V230506",
    opcode = "BarTripleV230506",
    param_kind = "BarTripleV230506"
)]
pub fn bar_triple_v230506(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}三K加速", di);
    let k3 = "裸K形态V230506";

    let mut v1 = "其他".to_string();
    let mut v2 = "任意".to_string();

    // 对齐 Python: len(c.bars_raw) < 7 直接返回“其他”
    // 同时保留 di 的安全边界，避免索引越界。
    if c.bars_raw.len() >= 7 {
        let bars = get_sub_elements(&c.bars_raw, di, 3);
        if bars.len() < 3 {
            return make_kline_signal_v2(&k1, &k2, k3, &v1, &v2);
        }
        let b3 = &bars[0];
        let b2 = &bars[1];
        let b1 = &bars[2];

        let red1 = b1.close > b1.open;
        let red2 = b2.close > b2.open;
        let red3 = b3.close > b3.open;

        let green1 = b1.close < b1.open;
        let green2 = b2.close < b2.open;
        let green3 = b3.close < b3.open;

        if red1 && red2 && red3 {
            v1 = "三连涨".to_string();
            if b1.high > b2.high && b2.high > b3.high && b1.low > b2.low && b2.low > b3.low {
                v1 = "新高涨".to_string();
            }
        }

        if green1 && green2 && green3 {
            v1 = "三连跌".to_string();
            if b1.high < b2.high && b2.high < b3.high && b1.low < b2.low && b2.low < b3.low {
                v1 = "新低跌".to_string();
            }
        }

        if v1 != "其他" {
            if b1.vol > b2.vol && b2.vol > b3.vol {
                v2 = "依次放量".to_string();
            } else if b1.vol < b2.vol && b2.vol < b3.vol {
                v2 = "依次缩量".to_string();
            } else {
                v2 = "量柱无序".to_string();
            }
        }
    }

    make_kline_signal_v2(&k1, &k2, k3, &v1, &v2)
}

/// bar_end_V221211：判断大周期K线是否闭合
///
/// 参数模板：`"{freq}_{freq1}结束_BS辅助221211"`
///
/// 信号逻辑：
/// 1. 以当前基础周期 `freq` 与目标分钟周期 `freq1` 计算当前K线对应结束时间；
/// 2. 从最新K线向前统计同属该结束时间的连续数量 `i`；
/// 3. 若 `end_time == last_dt` 判定 `闭合`，否则判定 `未闭{i}`。
///
/// 信号列表示例：
/// - `Signal('15分钟_60分钟结束_BS辅助221211_闭合_任意_任意_0')`
/// - `Signal('15分钟_60分钟结束_BS辅助221211_未闭2_任意_任意_0')`
///
/// 参数说明：
/// - `freq1`：目标分钟周期，默认 `60分钟`。
/// 对齐说明：闭合/未闭计数语义与 Python `bar_end_V221211` 保持一致。
#[signal(
    category = "kline",
    name = "bar_end_V221211",
    template = "{freq}_{freq1}结束_BS辅助221211",
    opcode = "BarEndV221211",
    param_kind = "BarEndV221211"
)]
pub fn bar_end_v221211(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let freq1 = params.str("freq1", "60分钟");
    let k1 = c.freq.to_string();
    let k2 = format!("{freq1}结束");
    let k3 = "BS辅助221211";

    if !freq1.contains("分钟") || c.bars_raw.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let last_dt = c.bars_raw.last().map(|x| x.dt).unwrap();
    let Some(c1_dt) = minute_freq_end_time(last_dt, freq1) else {
        return vec![];
    };
    let mut i = 0usize;
    for bar in c.bars_raw.iter().rev() {
        let Some(edt) = minute_freq_end_time(bar.dt, freq1) else {
            break;
        };
        if edt != c1_dt {
            break;
        }
        i += 1;
    }

    let v1 = if c1_dt == last_dt {
        "闭合".to_string()
    } else {
        format!("未闭{i}")
    };
    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// bar_operate_span_V221111：日内时间区间过滤
///
/// 参数模板：`"{freq}_T{t1}#{t2}_时间区间V221111"`
///
/// 信号逻辑：
/// 1. 读取最新K线时间 `HHMM`；
/// 2. 若 `t1 <= HHMM <= t2` 判定 `是`，否则判定 `否`。
///
/// 信号列表示例：
/// - `Signal('60分钟_T0935#1450_时间区间_是_任意_任意_0')`
/// - `Signal('60分钟_T0935#1450_时间区间_否_任意_任意_0')`
///
/// 参数说明：
/// - `t1`：起始时间（`HHMM`），默认 `0935`；
/// - `t2`：结束时间（`HHMM`），默认 `1450`。
/// 对齐说明：边界包含比较与 Python `bar_operate_span_V221111` 一致。
#[signal(
    category = "kline",
    name = "bar_operate_span_V221111",
    template = "{freq}_T{t1}#{t2}_时间区间V221111",
    opcode = "BarOperateSpanV221111",
    param_kind = "BarOperateSpanV221111"
)]
pub fn bar_operate_span_v221111(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let t1 = params.str("t1", "0935");
    let t2 = params.str("t2", "1450");
    let k1 = c.freq.to_string();
    let k2 = format!("T{t1}#{t2}");
    let k3 = "时间区间";
    if c.bars_raw.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let dt = c.bars_raw.last().unwrap().dt;
    let hm = dt.format("%H%M").to_string();
    let v1 = if t1 <= hm.as_str() && hm.as_str() <= t2 {
        "是"
    } else {
        "否"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_time_V230327：日内时间分段信号
///
/// 参数模板：`"{freq}_日内时间_分段V230327"`
///
/// 信号逻辑：
/// 1. 仅支持 `30分钟/60分钟` 周期；
/// 2. 取最近 100 根K线的 `HH:MM` 去重并排序；
/// 3. 输出当前K线时间在分段序列中的位置：`第{n}段`。
///
/// 信号列表示例：
/// - `Signal('60分钟_日内时间_分段V230327_第1段_任意_任意_0')`
/// - `Signal('60分钟_日内时间_分段V230327_第4段_任意_任意_0')`
///
/// 参数说明：
/// - 无额外参数。
/// 对齐说明：分段生成与 Python `bar_time_V230327` 的排序与编号口径一致。
#[signal(
    category = "kline",
    name = "bar_time_V230327",
    template = "{freq}_日内时间_分段V230327",
    opcode = "BarTimeV230327",
    param_kind = "BarTimeV230327"
)]
pub fn bar_time_v230327(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "日内时间";
    let k3 = "分段V230327";
    let mut v1 = "其他".to_string();
    if c.freq.to_string() != "30分钟" && c.freq.to_string() != "60分钟" {
        return make_kline_signal_v1(&k1, k2, k3, &v1);
    }
    if let Some(seg) = intraday_time_segment(&c.bars_raw, 100) {
        v1 = format!("第{}段", seg);
    }
    make_kline_signal_v1(&k1, k2, k3, &v1)
}

/// bar_weekday_V230328：周内时间分段信号
///
/// 参数模板：`"{freq}_周内时间_分段V230328"`
///
/// 信号逻辑：
/// 1. 当样本数量不足 20 根时返回 `其他`；
/// 2. 否则将最新K线日期按 `weekday` 映射到 `周一~周日`。
///
/// 信号列表示例：
/// - `Signal('60分钟_周内时间_分段V230328_周一_任意_任意_0')`
/// - `Signal('60分钟_周内时间_分段V230328_周五_任意_任意_0')`
///
/// 参数说明：
/// - 无额外参数。
/// 对齐说明：weekday 映射表与 Python `bar_weekday_V230328` 一致。
#[signal(
    category = "kline",
    name = "bar_weekday_V230328",
    template = "{freq}_周内时间_分段V230328",
    opcode = "BarWeekdayV230328",
    param_kind = "BarWeekdayV230328"
)]
pub fn bar_weekday_v230328(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "周内时间";
    let k3 = "分段V230328";
    let mut v1 = "其他";
    if c.bars_raw.len() >= 20 {
        v1 = weekday_cn(c.bars_raw.last().unwrap().dt);
    }
    make_kline_signal_v1(&k1, k2, k3, v1)
}

/// bar_vol_grow_V221112：成交量放大信号
///
/// 参数模板：`"{freq}_D{di}K{n}B_放量V221112"`
///
/// 信号逻辑：
/// 1. 取倒数第 `di` 根及其前 `n` 根，共 `n+1` 根K线；
/// 2. 计算前 `n` 根平均成交量 `mean_vol`；
/// 3. 若当前量在 `[2*mean_vol, 4*mean_vol]`，判 `是`，否则 `否`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D2K5B_放量V221112_是_任意_任意_0')`
/// - `Signal('60分钟_D2K5B_放量V221112_否_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `2`；
/// - `n`：回看K线数量，默认 `5`。
/// 对齐说明：判定区间与 Python `bar_vol_grow_V221112` 保持一致。
#[signal(
    category = "kline",
    name = "bar_vol_grow_V221112",
    template = "{freq}_D{di}K{n}B_放量V221112",
    opcode = "BarVolGrowV221112",
    param_kind = "BarVolGrowV221112"
)]
pub fn bar_vol_grow_v221112(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 2);
    let n = params.usize("n", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K{}B", di, n);
    let k3 = "放量V221112";

    let v1 = if c.bars_raw.len() < di + n + 10 {
        "其他"
    } else {
        let bars = get_sub_elements(&c.bars_raw, di, n + 1);
        if bars.len() != n + 1 {
            "其他"
        } else {
            let mean_vol = bars[..n].iter().map(|x| x.vol).sum::<f64>() / n as f64;
            if bars[n].vol >= mean_vol * 2.0 && bars[n].vol <= mean_vol * 4.0 {
                "是"
            } else {
                "否"
            }
        }
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_mean_amount_V221112：区间均额分类信号
///
/// 参数模板：`"{freq}_D{di}K{n}B均额_{th1}至{th2}千万"`
///
/// 信号逻辑：
/// 1. 取倒数第 `di` 根截止的最近 `n` 根K线；
/// 2. 计算平均成交额 `m`；
/// 3. 若 `m/1e7` 在 `[th1, th2]` 判 `是`，否则判 `否`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K10B均额_1至4千万_是_任意_任意_0')`
/// - `Signal('60分钟_D1K10B均额_1至4千万_否_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：样本长度，默认 `10`；
/// - `th1`：下限（千万），默认 `1`；
/// - `th2`：上限（千万），默认 `4`。
/// 对齐说明：均额口径与 Python `bar_mean_amount_V221112` 保持一致。
#[signal(
    category = "kline",
    name = "bar_mean_amount_V221112",
    template = "{freq}_D{di}K{n}B均额_{th1}至{th2}千万V221112",
    opcode = "BarMeanAmountV221112",
    param_kind = "BarMeanAmountV221112"
)]
pub fn bar_mean_amount_v221112(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 10);
    let th1 = params.usize("th1", 1);
    let th2 = params.usize("th2", 4);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}K{}B均额", di, n);
    let k3 = format!("{}至{}千万", th1, th2);

    let mut v1 = "其他";
    if c.bars_raw.len() > di + n + 5 {
        let bars = get_sub_elements(&c.bars_raw, di, n);
        if bars.len() == n {
            let m = bars.iter().map(|x| x.amount).sum::<f64>() / n as f64 / 10_000_000.0;
            v1 = if m >= th1 as f64 && m <= th2 as f64 {
                "是"
            } else {
                "否"
            };
        }
    }
    make_kline_signal_v1(&k1, &k2, &k3, v1)
}

/// bar_zdf_V221203：单根涨跌幅区间信号
///
/// 参数模板：`"{freq}_D{di}{mode}_{t1}至{t2}"`
///
/// 信号逻辑：
/// 1. 读取倒数第 `di` 根及其前一根K线；
/// 2. `mode=ZF` 使用涨幅 `close/prev_close-1`，`mode=DF` 使用跌幅 `1-close/prev_close`；
/// 3. 换算为 BP 后在 `[t1, t2]` 判 `满足`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_D1ZF_300至600_满足_任意_任意_0')`
/// - `Signal('日线_D1DF_300至600_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `mode`：`ZF` 或 `DF`，默认 `ZF`；
/// - `span`：区间下上界（`t1,t2`），默认 `300,600`。
/// 对齐说明：BP 计算与 Python `bar_zdf_V221203` 保持一致。
#[signal(
    category = "kline",
    name = "bar_zdf_V221203",
    template = "{freq}_D{di}{mode}_{t1}至{t2}V221203",
    opcode = "BarZdfV221203",
    param_kind = "BarZdfV221203"
)]
pub fn bar_zdf_v221203(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let mode = params.str("mode", "ZF").to_uppercase();
    let span = params.str("span", "300,600");
    let parts: Vec<&str> = span.split(',').collect();
    let t1 = parts
        .first()
        .and_then(|x| x.parse::<f64>().ok())
        .unwrap_or(300.0);
    let t2 = parts
        .get(1)
        .and_then(|x| x.parse::<f64>().ok())
        .unwrap_or(600.0);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}{}", di, mode);
    let k3 = format!("{}至{}", t1 as i32, t2 as i32);

    let bars = get_sub_elements(&c.bars_raw, di, 3);
    if bars.len() < 2 || t2 <= t1 || t1 <= 0.0 {
        return make_kline_signal_v1(&k1, &k2, &k3, "其他");
    }
    let prev = bars[bars.len() - 2].close;
    let last = bars[bars.len() - 1].close;
    if prev == 0.0 {
        return make_kline_signal_v1(&k1, &k2, &k3, "其他");
    }
    let edge = if mode == "ZF" {
        (last / prev - 1.0) * 10_000.0
    } else {
        (1.0 - last / prev) * 10_000.0
    };
    let v1 = if edge >= t1 && edge <= t2 {
        "满足"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, &k3, v1)
}

/// bar_amount_acc_V230214：区间累计成交额信号
///
/// 参数模板：`"{freq}_D{di}N{n}_累计超{t}千万"`
///
/// 信号逻辑：
/// 1. 取倒数第 `di` 根截止的最近 `n` 根K线；
/// 2. 计算累计成交额 `sum(amount)`；
/// 3. 若大于 `t * 1e7` 判 `是`，否则 `否`。
///
/// 信号列表示例：
/// - `Signal('日线_D2N5_累计超10千万_是_任意_任意_0')`
/// - `Signal('日线_D2N5_累计超10千万_否_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `2`；
/// - `n`：回看K线数，默认 `5`；
/// - `t`：阈值（千万），默认 `10`。
/// 对齐说明：累计金额阈值判断与 Python `bar_amount_acc_V230214` 一致。
#[signal(
    category = "kline",
    name = "bar_amount_acc_V230214",
    template = "{freq}_D{di}N{n}_累计超{t}千万V230214",
    opcode = "BarAmountAccV230214",
    param_kind = "BarAmountAccV230214"
)]
pub fn bar_amount_acc_v230214(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 2);
    let n = params.usize("n", 5);
    let t = params.usize("t", 10);

    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}", di, n);
    let k3 = format!("累计超{}千万", t);
    let mut v1 = "其他";

    if c.bars_raw.len() > di + n + 5 {
        let bars = get_sub_elements(&c.bars_raw, di, n);
        if bars.len() == n {
            let acc = bars.iter().map(|x| x.amount).sum::<f64>();
            v1 = if acc > t as f64 * 10_000_000.0 {
                "是"
            } else {
                "否"
            };
        }
    }
    make_kline_signal_v1(&k1, &k2, &k3, v1)
}

/// bar_single_V230214：单K状态信号
///
/// 参数模板：`"{freq}_D{di}T{t}_状态V230214"`
///
/// 信号逻辑：
/// 1. 倒数第 `di` 根K线，按 `close/open` 判 `阳线/阴线`；
/// 2. 若 `solid > (upper+lower)*t/10` 判 `长实体`；
/// 3. 若 `upper > (solid+lower)*t/10` 判 `长上影`；
/// 4. 若 `lower > (solid+upper)*t/10` 判 `长下影`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_D1T10_状态V230214_阳线_长实体_任意_0')`
/// - `Signal('日线_D1T10_状态V230214_阴线_长上影_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `t`：长实体/长影阈值（/10），默认 `10`。
/// 对齐说明：分类阈值与 Python `bar_single_V230214` 保持一致。
#[signal(
    category = "kline",
    name = "bar_single_V230214",
    template = "{freq}_D{di}T{t}_状态V230214",
    opcode = "BarSingleV230214",
    param_kind = "BarSingleV230214"
)]
pub fn bar_single_v230214(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let t = params.usize("t", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}T{}", di, t);
    let k3 = "状态";

    if c.bars_raw.len() < di + 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let k = &c.bars_raw[c.bars_raw.len() - di];
    let v1 = if k.close > k.open { "阳线" } else { "阴线" };
    let solid = (k.open - k.close).abs();
    let upper = k.high - k.open.max(k.close);
    let lower = k.open.min(k.close) - k.low;
    let v2 = if solid > (upper + lower) * t as f64 / 10.0 {
        "长实体"
    } else if upper > (solid + lower) * t as f64 / 10.0 {
        "长上影"
    } else if lower > (solid + upper) * t as f64 / 10.0 {
        "长下影"
    } else {
        "其他"
    };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// bar_big_solid_V230215：窗口最大实体中位多空信号
///
/// 参数模板：`"{freq}_D{di}N{n}_MIDV230215"`
///
/// 信号逻辑：
/// 1. 在窗口内找到实体最大K线；
/// 2. 取该K线实体中位价 `mid`；
/// 3. 最新收盘价高于 `mid` 判 `看多`，否则 `看空`；
/// 4. 最大实体K线按方向标注 `大阳/大阴`。
///
/// 信号列表示例：
/// - `Signal('日线_D1N20_MIDV230215_看多_大阳_任意_0')`
/// - `Signal('日线_D1N20_MIDV230215_看空_大阴_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：窗口长度，默认 `20`。
/// 对齐说明：最大实体与中位价定义对齐 Python `bar_big_solid_V230215`。
#[signal(
    category = "kline",
    name = "bar_big_solid_V230215",
    template = "{freq}_D{di}N{n}_MIDV230215",
    opcode = "BarBigSolidV230215",
    param_kind = "BarBigSolidV230215"
)]
pub fn bar_big_solid_v230215(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 20);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}", di, n);
    let k3 = "MID";

    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.is_empty() || c.bars_raw.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let mut max_i = 0usize;
    let mut max_solid = f64::NEG_INFINITY;
    for (i, b) in bars.iter().enumerate() {
        let s = (b.open - b.close).abs();
        if s > max_solid {
            max_solid = s;
            max_i = i;
        }
    }
    let b = &bars[max_i];
    let max_mid = b.open.min(b.close) + 0.5 * (b.open - b.close).abs();
    let v1 = if c.bars_raw.last().map(|x| x.close).unwrap_or(max_mid) > max_mid {
        "看多"
    } else {
        "看空"
    };
    let v2 = if b.close > b.open { "大阳" } else { "大阴" };
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// bar_bpm_V230227：绝对动量分层
///
/// 参数模板：`"{freq}_D{di}N{n}T{th}_绝对动量V230227"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 根，计算区间 BP：`(last_close/first_open-1)*10000`；
/// 2. `bp>0` 时，`bp>th` 判 `超强` 否则 `强势`；
/// 3. `bp<=0` 时，`|bp|>th` 判 `超弱` 否则 `弱势`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N20T1000_绝对动量V230227_强势_任意_任意_0')`
/// - `Signal('60分钟_D1N20T1000_绝对动量V230227_超弱_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：窗口长度，默认 `20`；
/// - `th`：强弱阈值（BP），默认 `1000`。
/// 对齐说明：分层规则与 Python `bar_bpm_V230227` 保持一致。
#[signal(
    category = "kline",
    name = "bar_bpm_V230227",
    template = "{freq}_D{di}N{n}T{th}_绝对动量V230227",
    opcode = "BarBpmV230227",
    param_kind = "BarBpmV230227"
)]
pub fn bar_bpm_v230227(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 20);
    let th = params.usize("th", 1000);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}T{}", di, n, th);
    let k3 = "绝对动量V230227";

    if c.bars_raw.len() < di + n {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.len() < n || bars[0].open == 0.0 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bp = (bars[bars.len() - 1].close / bars[0].open - 1.0) * 10_000.0;
    let v1 = if bp > 0.0 {
        if bp > th as f64 {
            "超强"
        } else {
            "强势"
        }
    } else if bp.abs() > th as f64 {
        "超弱"
    } else {
        "弱势"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_section_momentum_V221112：区间动量强弱与波动
///
/// 参数模板：`"{freq}_D{di}K{n}B_阈值{th}BPV221112"`
///
/// 信号逻辑：
/// 1. 区间 BP：`(last_close/first_open-1)*10000`；
/// 2. 区间波动：`(max_high/min_low-1)*10000`；
/// 3. `v1`：`上涨/下跌`；`v2`：`强势/弱势`（`|bp|>=th`）；
/// 4. `v3`：`高波动/低波动`（`|wave|/|bp| >= 3`）。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K10B_阈值100BPV221112_上涨_强势_高波动_0')`
/// - `Signal('60分钟_D1K10B_阈值100BPV221112_下跌_弱势_低波动_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：窗口长度，默认 `10`；
/// - `th`：强弱阈值（BP），默认 `100`。
/// 对齐说明：三段分类与 Python `bar_section_momentum_V221112` 一致。
#[signal(
    category = "kline",
    name = "bar_section_momentum_V221112",
    template = "{freq}_D{di}K{n}B_阈值{th}BPV221112",
    opcode = "BarSectionMomentumV221112",
    param_kind = "BarSectionMomentumV221112"
)]
pub fn bar_section_momentum_v221112(
    c: &CZSC,
    params: &ParamView,
    _cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 10);
    let th = params.usize("th", 100);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K{}B", di, n);
    let k3 = format!("阈值{}BP", th);

    if c.bars_raw.len() < di + n {
        return make_kline_signal_v3(&k1, &k2, &k3, "其他", "其他", "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.len() < n || bars[0].open == 0.0 {
        return make_kline_signal_v3(&k1, &k2, &k3, "其他", "其他", "其他");
    }
    let bp = (bars[bars.len() - 1].close / bars[0].open - 1.0) * 10_000.0;
    let high = bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let low = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    if low == 0.0 || !high.is_finite() || !low.is_finite() {
        return make_kline_signal_v3(&k1, &k2, &k3, "其他", "其他", "其他");
    }
    let wave = (high / low - 1.0) * 10_000.0;
    let rate = if bp.abs() == 0.0 {
        0.0
    } else {
        wave.abs() / bp.abs()
    };
    let v1 = if bp >= 0.0 { "上涨" } else { "下跌" };
    let v2 = if bp.abs() >= th as f64 {
        "强势"
    } else {
        "弱势"
    };
    let v3 = if rate >= 3.0 {
        "高波动"
    } else {
        "低波动"
    };
    make_kline_signal_v3(&k1, &k2, &k3, v1, v2, v3)
}

/// bar_vol_bs1_V230224：量价高低点辅助
///
/// 参数模板：`"{freq}_D{di}N{n}量价_BS1辅助V230224"`
///
/// 信号逻辑：
/// 1. 窗口末根创新高且上影显著、成交额远高于均值，判 `看空`；
/// 2. 窗口末根创新低且下影显著、成交额远低于均值，判 `看多`；
/// 3. 否则返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N20量价_BS1辅助V230224_看空_任意_任意_0')`
/// - `Signal('60分钟_D1N20量价_BS1辅助V230224_看多_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：窗口长度，默认 `20`。
/// 对齐说明：量价条件阈值与 Python `bar_vol_bs1_V230224` 一致。
#[signal(
    category = "kline",
    name = "bar_vol_bs1_V230224",
    template = "{freq}_D{di}N{n}量价_BS1辅助V230224",
    opcode = "BarVolBs1V230224",
    param_kind = "BarVolBs1V230224"
)]
pub fn bar_vol_bs1_v230224(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 20);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}量价", di, n);
    let k3 = "BS1辅助";

    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let last = &bars[bars.len() - 1];
    let mean_amount = bars.iter().map(|x| x.amount).sum::<f64>() / bars.len() as f64;
    let max_high = bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let min_low = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);

    let last_upper = last.high - last.open.max(last.close);
    let last_lower = last.open.min(last.close) - last.low;
    let short_c1 = (last.high - max_high).abs() <= f64::EPSILON
        && last_upper > 2.0 * last_lower
        && last_lower > 0.0;
    let short_c2 = last.amount > mean_amount * 3.0;
    let long_c1 = (last.low - min_low).abs() <= f64::EPSILON
        && last_lower > 2.0 * last_upper
        && last_upper > 0.0;
    let long_c2 = last.amount < mean_amount * 0.7;

    let v1 = if short_c1 && short_c2 {
        "看空"
    } else if long_c1 && long_c2 {
        "看多"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_zt_count_V230504：窗口涨停计数
///
/// 参数模板：`"{freq}_D{di}W{window}涨停计数_裸K形态V230504"`
///
/// 信号逻辑：
/// 1. 在窗口内按相邻K线判断 `涨停`：`b2.close > b1.close*1.07 && b2.close==b2.high`；
/// 2. 统计总次数 `sum(c1)`；
/// 3. 统计连续双涨停次数 `cc`（相邻两个都为1）；
/// 4. 若总次数为0返回 `其他`，否则输出 `"{sum}次" + "连续{cc}次"`。
///
/// 信号列表示例：
/// - `Signal('日线_D1W5涨停计数_裸K形态V230504_1次_连续0次_任意_0')`
/// - `Signal('日线_D1W5涨停计数_裸K形态V230504_3次_连续2次_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `window`：统计窗口，默认 `5`。
/// 对齐说明：涨停阈值与连续计次与 Python `bar_zt_count_V230504` 一致。
#[signal(
    category = "kline",
    name = "bar_zt_count_V230504",
    template = "{freq}_D{di}W{window}涨停计数_裸K形态V230504",
    opcode = "BarZtCountV230504",
    param_kind = "BarZtCountV230504"
)]
pub fn bar_zt_count_v230504(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let window = params.usize("window", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}涨停计数", di, window);
    let k3 = "裸K形态V230504";

    if c.freq.to_string() != "日线" {
        return vec![];
    }
    if c.bars_raw.len() < 7 + di + window {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, window);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut c1: Vec<i32> = Vec::with_capacity(bars.len() - 1);
    let mut cc = 0i32;
    for w in bars.windows(2) {
        let b1 = &w[0];
        let b2 = &w[1];
        let is_zt = b2.close > b1.close * 1.07 && (b2.close - b2.high).abs() <= f64::EPSILON;
        c1.push(if is_zt { 1 } else { 0 });
        if c1.len() >= 2 && c1[c1.len() - 1] == 1 && c1[c1.len() - 2] == 1 {
            cc += 1;
        }
    }
    let sum_zt: i32 = c1.iter().sum();
    if sum_zt == 0 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let v1 = format!("{}次", sum_zt);
    let v2 = format!("连续{}次", cc);
    make_kline_signal_v2(&k1, &k2, k3, &v1, &v2)
}

/// bar_limit_down_V230525：跌停后反包阳线
///
/// 参数模板：`"{freq}_跌停后无下影线长实体阳线_短线V230525"`
///
/// 信号逻辑：
/// 1. 仅日线级别；
/// 2. 前一日近似跌停：`low==close<prev_close && close/prev_close<0.95`；
/// 3. 当日无下影长阳：`low==open && close>open && solid>2*upper && close/open>1.07`；
/// 4. 且当日最低低于前日最低，判 `满足`。
///
/// 信号列表示例：
/// - `Signal('日线_跌停后无下影线长实体阳线_短线V230525_满足_任意_任意_0')`
/// - `Signal('日线_跌停后无下影线长实体阳线_短线V230525_其他_任意_任意_0')`
///
/// 参数说明：
/// - 无额外参数。
/// 对齐说明：条件组合与 Python `bar_limit_down_V230525` 保持一致。
#[signal(
    category = "kline",
    name = "bar_limit_down_V230525",
    template = "{freq}_跌停后无下影线长实体阳线_短线V230525",
    opcode = "BarLimitDownV230525",
    param_kind = "BarLimitDownV230525"
)]
pub fn bar_limit_down_v230525(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "跌停后无下影线长实体阳线";
    let k3 = "短线V230525";
    if k1 != "日线" {
        return vec![];
    }
    if c.bars_raw.len() < 10 {
        return make_kline_signal_v1(&k1, k2, k3, "其他");
    }
    let b1 = &c.bars_raw[c.bars_raw.len() - 3];
    let b2 = &c.bars_raw[c.bars_raw.len() - 2];
    let b3 = &c.bars_raw[c.bars_raw.len() - 1];
    let b2_condition = (b2.low - b2.close).abs() <= f64::EPSILON
        && b2.close < b1.close
        && b2.close / b1.close < 0.95;
    let b3_solid = (b3.open - b3.close).abs();
    let b3_upper = b3.high - b3.open.max(b3.close);
    let b3_condition = (b3.low - b3.open).abs() <= f64::EPSILON
        && b3.close > b3.open
        && b3_solid > b3_upper * 2.0
        && b3.close / b3.open > 1.07;
    let v1 = if b2_condition && b3_condition && b3.low < b2.low {
        "满足"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, k2, k3, v1)
}

#[inline]
fn bar_solid(b: &czsc_core::objects::bar::RawBar) -> f64 {
    (b.open - b.close).abs()
}

#[inline]
fn bar_upper(b: &czsc_core::objects::bar::RawBar) -> f64 {
    b.high - b.open.max(b.close)
}

#[inline]
fn bar_lower(b: &czsc_core::objects::bar::RawBar) -> f64 {
    b.open.min(b.close) - b.low
}

fn percentile_linear(values: &[f64], p: f64) -> Option<f64> {
    if values.is_empty() || !p.is_finite() {
        return None;
    }
    let mut x: Vec<f64> = values.iter().copied().filter(|v| v.is_finite()).collect();
    if x.is_empty() {
        return None;
    }
    x.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));
    if x.len() == 1 {
        return Some(x[0]);
    }
    let q = p.clamp(0.0, 100.0) / 100.0;
    let h = (x.len() - 1) as f64 * q;
    let i = h.floor() as usize;
    let j = h.ceil() as usize;
    if i == j {
        Some(x[i])
    } else {
        Some(x[i] + (h - i as f64) * (x[j] - x[i]))
    }
}

fn overlap_center(bars: &[czsc_core::objects::bar::RawBar]) -> (bool, Option<f64>, Option<f64>) {
    if bars.is_empty() {
        return (false, None, None);
    }
    let min_high = bars.iter().map(|x| x.high).fold(f64::INFINITY, f64::min);
    let max_low = bars.iter().map(|x| x.low).fold(f64::NEG_INFINITY, f64::max);
    if min_high > max_low {
        let dd = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
        let gg = bars
            .iter()
            .map(|x| x.high)
            .fold(f64::NEG_INFINITY, f64::max);
        (true, Some(dd), Some(gg))
    } else {
        (false, None, None)
    }
}

/// bar_accelerate_V221110：区间加速走势判定
///
/// 参数模板：`"{freq}_D{di}W{window}_加速V221110"`
///
/// 信号逻辑：
/// 1. 取倒数第 `di` 根截止的最近 `window` 根K线，计算区间最高/最低；
/// 2. 若末根收盘位于区间上20%且阳线占比>=80%，判 `上涨`；
/// 3. 若末根收盘位于区间下20%且阴线占比>=80%，判 `下跌`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W13_加速V221110_上涨_任意_任意_0')`
/// - `Signal('60分钟_D1W13_加速V221110_下跌_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `window`：观察窗口长度，默认 `10`。
/// 对齐说明：收盘位置与阳阴占比阈值对齐 Python `bar_accelerate_V221110`。
#[signal(
    category = "kline",
    name = "bar_accelerate_V221110",
    template = "{freq}_D{di}W{window}_加速V221110",
    opcode = "BarAccelerateV221110",
    param_kind = "BarAccelerateV221110"
)]
pub fn bar_accelerate_v221110(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let window = params.usize("window", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}", di, window);
    let k3 = "加速V221110";

    let mut v1 = "其他";
    if c.bars_raw.len() > di + window + 10 {
        let bars = get_sub_elements(&c.bars_raw, di, window);
        if bars.len() == window {
            let hhv = bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max);
            let llv = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
            let close = bars[bars.len() - 1].close;
            let c1 = close > llv + (hhv - llv) * 0.8;
            let c2 = close < llv + (hhv - llv) * 0.2;
            let red_pct =
                bars.iter().filter(|x| x.close > x.open).count() as f64 / bars.len() as f64 >= 0.8;
            let green_pct =
                bars.iter().filter(|x| x.close < x.open).count() as f64 / bars.len() as f64 >= 0.8;
            if c1 && red_pct {
                v1 = "上涨";
            }
            if c2 && green_pct {
                v1 = "下跌";
            }
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_accelerate_V221118：均线偏离加速判定
///
/// 参数模板：`"{freq}_D{di}W{window}#{ma_type}#{timeperiod}_加速V221118"`
///
/// 信号逻辑：
/// 1. 计算窗口内每根 `close - ma` 偏离值；
/// 2. 全部偏离为正，且最后三根偏离值递增，判 `上涨`；
/// 3. 全部偏离为负，且最后三根偏离值递减，判 `下跌`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_D1W13#SMA#10_加速V221118_上涨_任意_任意_0')`
/// - `Signal('日线_D1W13#SMA#10_加速V221118_下跌_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `window`：观察窗口，默认 `13`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `10`。
/// 对齐说明：偏离序列与三根单调条件对齐 Python `bar_accelerate_V221118`。
#[signal(
    category = "kline",
    name = "bar_accelerate_V221118",
    template = "{freq}_D{di}W{window}#{ma_type}#{timeperiod}_加速V221118",
    opcode = "BarAccelerateV221118",
    param_kind = "BarAccelerateV221118"
)]
pub fn bar_accelerate_v221118(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let window = params.usize("window", 13);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let timeperiod = params.usize("timeperiod", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}#{}#{}", di, window, ma_type, timeperiod);
    let k3 = "加速V221118";

    if window <= 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let cache_key = format!("{}_{}_{}", c.freq, ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let bars = get_sub_elements(&c.bars_raw, di, window);
    let ma_sub = get_sub_elements(ma.as_slice(), di, window);
    if bars.len() != window || ma_sub.len() != window {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let delta: Vec<f64> = bars
        .iter()
        .zip(ma_sub.iter())
        .map(|(b, m)| b.close - *m)
        .collect();
    let all_pos = delta.iter().all(|x| *x > 0.0);
    let all_neg = delta.iter().all(|x| *x < 0.0);
    let n = delta.len();
    let v1 = if all_pos && delta[n - 1] > delta[n - 2] && delta[n - 2] > delta[n - 3] {
        "上涨"
    } else if all_neg && delta[n - 1] < delta[n - 2] && delta[n - 2] < delta[n - 3] {
        "下跌"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_accelerate_V240428：滚动差分加速判定
///
/// 参数模板：`"{freq}_D{di}W{w}T{t}_加速V240428"`
///
/// 信号逻辑：
/// 1. 计算 `diff = close - close[w]`，取最近300根 `|diff|` 的75分位阈值；
/// 2. 若最新 `|diff|` 超阈且 `diff>0`，窗口内倍量阳线数>=`t` 判 `上涨`；
/// 3. 若最新 `|diff|` 超阈且 `diff<0`，窗口内倍量阴线数>=`t` 判 `下跌`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_D1W21T2_加速V240428_上涨_任意_任意_0')`
/// - `Signal('日线_D1W21T2_加速V240428_下跌_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `w`：差分窗口，默认 `21`；
/// - `t`：倍量同向K线最小数量，默认 `1`。
/// 对齐说明：阈值分位与倍量计数口径对齐 Python `bar_accelerate_V240428`。
#[signal(
    category = "kline",
    name = "bar_accelerate_V240428",
    template = "{freq}_D{di}W{w}T{t}_加速V240428",
    opcode = "BarAccelerateV240428",
    param_kind = "BarAccelerateV240428"
)]
pub fn bar_accelerate_v240428(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 21);
    let t = params.usize("t", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}T{}", di, w, t);
    let k3 = "加速V240428";

    if c.bars_raw.len() < w + 100 + di || w == 0 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut diff = vec![f64::NAN; c.bars_raw.len()];
    for (i, diff_i) in diff.iter_mut().enumerate().skip(w) {
        *diff_i = c.bars_raw[i].close - c.bars_raw[i - w].close;
    }
    let start = c.bars_raw.len().saturating_sub(300);
    let diff_abs: Vec<f64> = diff[start..]
        .iter()
        .copied()
        .filter(|x| x.is_finite())
        .map(f64::abs)
        .collect();
    let Some(th) = percentile_linear(&diff_abs, 75.0) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let last_diff = diff[c.bars_raw.len() - 1];
    if !last_diff.is_finite() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut v1 = "其他";
    if last_diff.abs() > th && last_diff > 0.0 {
        let mut cnt = 0usize;
        for pair in bars.windows(2) {
            let b1 = &pair[0];
            let b2 = &pair[1];
            if b2.close > b2.open && b2.vol > b1.vol * 2.0 {
                cnt += 1;
            }
        }
        if cnt >= t {
            v1 = "上涨";
        }
    }
    if last_diff.abs() > th && last_diff < 0.0 {
        let mut cnt = 0usize;
        for pair in bars.windows(2) {
            let b1 = &pair[0];
            let b2 = &pair[1];
            if b2.close < b2.open && b2.vol > b1.vol * 2.0 {
                cnt += 1;
            }
        }
        if cnt >= t {
            v1 = "下跌";
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_fake_break_V230204：区间假突破判定
///
/// 参数模板：`"{freq}_D{di}N{n}M{m}_假突破V230204"`
///
/// 信号逻辑：
/// 1. 在最近 `N` 根内寻找滑动 `M` 窗口重叠中枢；
/// 2. 阳线末根创新高且“跌破DD后拉回”，判 `看多`；
/// 3. 阴线末根创新低且“突破GG后回落”，判 `看空`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1N20M5_假突破_看多_任意_任意_0')`
/// - `Signal('15分钟_D1N20M5_假突破_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：观察窗口，默认 `20`；
/// - `m`：中枢滑窗，默认 `5`。
/// 对齐说明：中枢重叠与真假突破条件对齐 Python `bar_fake_break_V230204`。
#[signal(
    category = "kline",
    name = "bar_fake_break_V230204",
    template = "{freq}_D{di}N{n}M{m}_假突破V230204",
    opcode = "BarFakeBreakV230204",
    param_kind = "BarFakeBreakV230204"
)]
pub fn bar_fake_break_v230204(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 20);
    let m = params.usize("m", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}M{}", di, n, m);
    let k3 = "假突破";

    let last_bars = get_sub_elements(&c.bars_raw, di, n);
    if last_bars.len() != n {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let last = &last_bars[last_bars.len() - 1];
    if bar_solid(last) < bar_upper(last) + bar_lower(last) {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut right_bars: Vec<czsc_core::objects::bar::RawBar> = Vec::new();
    let mut dd = 0.0f64;
    let mut gg = 0.0f64;
    if n > 2 * m {
        for i in m..(n - m) {
            let a = n - i - m;
            let b = n - i;
            let (ok, _dd, _gg) = overlap_center(&last_bars[a..b]);
            if ok {
                dd = _dd.unwrap_or(0.0);
                gg = _gg.unwrap_or(0.0);
                right_bars = last_bars[n - i..].to_vec();
                break;
            }
        }
    }

    let mut v1 = "其他";
    if last.close > last.open {
        let c1_a = (last.high
            - last_bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max))
        .abs()
            <= f64::EPSILON;
        let c1_b = (last.close
            - last_bars
                .iter()
                .map(|x| x.close)
                .fold(f64::NEG_INFINITY, f64::max))
        .abs()
            <= f64::EPSILON;
        let c2 = if right_bars.is_empty() {
            false
        } else {
            let min_low = right_bars
                .iter()
                .map(|x| x.low)
                .fold(f64::INFINITY, f64::min);
            0.0 < min_low && min_low < dd
        };
        if (c1_a || c1_b) && c2 {
            v1 = "看多";
        }
    }
    if last.close < last.open {
        let c1_a = (last.low
            - last_bars
                .iter()
                .map(|x| x.low)
                .fold(f64::INFINITY, f64::min))
        .abs()
            <= f64::EPSILON;
        let c1_b = (last.close
            - last_bars
                .iter()
                .map(|x| x.close)
                .fold(f64::INFINITY, f64::min))
        .abs()
            <= f64::EPSILON;
        let c2 = if right_bars.is_empty() {
            false
        } else {
            let max_high = right_bars
                .iter()
                .map(|x| x.high)
                .fold(f64::NEG_INFINITY, f64::max);
            max_high > gg && gg > 0.0
        };
        if (c1_a || c1_b) && c2 {
            v1 = "看空";
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_reversal_V230227：末根反转迹象判定
///
/// 参数模板：`"{freq}_D{di}A{avg_bp}_反转V230227"`
///
/// 信号逻辑：
/// 1. 以末根K线形态（阴线/长上影、阳线/长下影）确定反转方向候选；
/// 2. 左侧13根满足 3/5/8 平均涨跌幅阈值，或 13 连阳/连阴，触发反向信号；
/// 3. 输出 `看多/看空/其他`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1A300_反转V230227_看多_任意_任意_0')`
/// - `Signal('15分钟_D1A300_反转V230227_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `avg_bp`：平均单根涨跌幅阈值（BP），默认 `300`。
/// 对齐说明：触发条件与优先级对齐 Python `bar_reversal_V230227`。
#[signal(
    category = "kline",
    name = "bar_reversal_V230227",
    template = "{freq}_D{di}A{avg_bp}_反转V230227",
    opcode = "BarReversalV230227",
    param_kind = "BarReversalV230227"
)]
pub fn bar_reversal_v230227(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let avg_bp = params.usize("avg_bp", 300) as f64;
    let k1 = c.freq.to_string();
    let k2 = format!("D{}A{}", di, avg_bp as usize);
    let k3 = "反转V230227";

    let bars = get_sub_elements(&c.bars_raw, di, 14);
    if bars.len() != 14 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let last = &bars[bars.len() - 1];
    let left = &bars[..bars.len() - 1];
    let last_up_c1 =
        last.close > last.open && bar_upper(last) > 2.0 * bar_solid(last).max(bar_lower(last));
    let last_dn_c1 =
        last.close < last.open && bar_lower(last) > 2.0 * bar_solid(last).max(bar_upper(last));

    let mut v1 = "其他";
    if last.close < last.open || last_up_c1 {
        let up_c1 =
            (left[left.len() - 1].close / left[left.len() - 3].open - 1.0) / 3.0 > avg_bp / 10000.0;
        let up_c2 =
            (left[left.len() - 1].close / left[left.len() - 5].open - 1.0) / 5.0 > avg_bp / 10000.0;
        let up_c3 =
            (left[left.len() - 1].close / left[left.len() - 8].open - 1.0) / 8.0 > avg_bp / 10000.0;
        let up_c4 = left.iter().all(|x| x.close > x.open);
        if up_c1 || up_c2 || up_c3 || up_c4 {
            v1 = "看空";
        }
    }
    if last.close > last.open || last_dn_c1 {
        let dn_c1 = (left[left.len() - 1].close / left[left.len() - 3].open - 1.0) / 3.0
            < -avg_bp / 10000.0;
        let dn_c2 = (left[left.len() - 1].close / left[left.len() - 5].open - 1.0) / 5.0
            < -avg_bp / 10000.0;
        let dn_c3 = (left[left.len() - 1].close / left[left.len() - 8].open - 1.0) / 8.0
            < -avg_bp / 10000.0;
        let dn_c4 = left.iter().all(|x| x.close < x.open);
        if dn_c1 || dn_c2 || dn_c3 || dn_c4 {
            v1 = "看多";
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_r_breaker_V230326：RBreaker 价格位判定
///
/// 参数模板：`"{freq}_RBreaker_BS辅助V230326"`
///
/// 信号逻辑：
/// 1. 用前一根K线 `H/C/L` 计算突破位、观察位、反转位；
/// 2. 当前收盘突破上/下轨判 `趋势做多/趋势做空`；
/// 3. 满足观察后反转条件判 `反转做多/反转做空`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_RBreaker_BS辅助V230326_做多_趋势_任意_0')`
/// - `Signal('日线_RBreaker_BS辅助V230326_做空_反转_任意_0')`
///
/// 参数说明：
/// - 无额外参数。
/// 对齐说明：六价位与判定顺序对齐 Python `bar_r_breaker_V230326`。
#[signal(
    category = "kline",
    name = "bar_r_breaker_V230326",
    template = "{freq}_RBreaker_BS辅助V230326",
    opcode = "BarRBreakerV230326",
    param_kind = "BarRBreakerV230326"
)]
pub fn bar_r_breaker_v230326(c: &CZSC, _params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let k1 = c.freq.to_string();
    let k2 = "RBreaker";
    let k3 = "BS辅助V230326";
    if c.bars_raw.len() < 3 {
        return make_kline_signal_v2(&k1, k2, k3, "其他", "其他");
    }
    let prev = &c.bars_raw[c.bars_raw.len() - 2];
    let cur = &c.bars_raw[c.bars_raw.len() - 1];
    let h = prev.high;
    let c0 = prev.close;
    let l = prev.low;
    let p = (h + c0 + l) / 3.0;
    let break_buy = h + 2.0 * p - 2.0 * l;
    let see_sell = p + h - l;
    let verse_sell = 2.0 * p - l;
    let verse_buy = 2.0 * p - h;
    let see_buy = p - (h - l);
    let break_sell = l - 2.0 * (h - p);

    let (v1, v2) = if cur.close > break_buy {
        ("做多", "趋势")
    } else if cur.close < break_sell {
        ("做空", "趋势")
    } else if cur.high > see_sell && cur.close < verse_sell {
        ("做空", "反转")
    } else if cur.low < see_buy && cur.close > verse_buy {
        ("做多", "反转")
    } else {
        ("其他", "其他")
    };
    make_kline_signal_v2(&k1, k2, k3, v1, v2)
}

/// bar_dual_thrust_V230403：Dual Thrust 通道突破
///
/// 参数模板：`"{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403"`
///
/// 信号逻辑：
/// 1. 用前 `N+1` 根计算 `HH/HC/LC/LL` 与 `Range=max(HH-LC, HC-LL)`；
/// 2. 构造当根上/下轨：`open + Range*K1%`、`open - Range*K2%`；
/// 3. 收盘上破判 `看多`，下破判 `看空`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_D1通道突破#5#20#20_BS辅助V230403_看多_任意_任意_0')`
/// - `Signal('日线_D1通道突破#5#20#20_BS辅助V230403_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `N`：回看天数，默认 `5`；
/// - `K1`：上轨系数（百分比），默认 `20`；
/// - `K2`：下轨系数（百分比），默认 `20`。
/// 对齐说明：通道计算与突破判断对齐 Python `bar_dual_thrust_V230403`。
#[signal(
    category = "kline",
    name = "bar_dual_thrust_V230403",
    template = "{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403",
    opcode = "BarDualThrustV230403",
    param_kind = "BarDualThrustV230403"
)]
pub fn bar_dual_thrust_v230403(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("N", params.usize("n", 5));
    let k1v = params.usize("K1", params.usize("k1", 20));
    let k2v = params.usize("K2", params.usize("k2", 20));
    let k1 = c.freq.to_string();
    let k2 = format!("D{}通道突破#{}#{}#{}", di, n, k1v, k2v);
    let k3 = "BS辅助V230403";

    if c.bars_raw.len() < 3 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di + 1, n + 1);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let hh = bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let hc = bars
        .iter()
        .map(|x| x.close)
        .fold(f64::NEG_INFINITY, f64::max);
    let lc = bars.iter().map(|x| x.close).fold(f64::INFINITY, f64::min);
    let ll = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let range = (hh - lc).max(hc - ll);

    let cur = &c.bars_raw[c.bars_raw.len() - di];
    let buy_line = cur.open + range * k1v as f64 / 100.0;
    let sell_line = cur.open - range * k2v as f64 / 100.0;
    let v1 = if cur.close > buy_line {
        "看多"
    } else if cur.close < sell_line {
        "看空"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

fn calc_tnr_series(c: &CZSC, timeperiod: usize) -> Vec<f64> {
    if c.bars_raw.is_empty() {
        return vec![];
    }
    let mut out = vec![0.0; c.bars_raw.len()];
    for (i, out_i) in out.iter_mut().enumerate() {
        if i < timeperiod {
            *out_i = 0.0;
            continue;
        }
        let start = i.saturating_sub(timeperiod);
        let win = &c.bars_raw[start..=i];
        let mut sum_abs = 0.0;
        for j in 1..win.len() {
            sum_abs += (win[j].close - win[j - 1].close).abs();
        }
        *out_i = if sum_abs == 0.0 {
            0.0
        } else {
            (win[win.len() - 1].close - win[0].close).abs() / sum_abs
        };
    }
    out
}

/// bar_tnr_V230630：TNR 噪音变化判定
///
/// 参数模板：`"{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630"`
///
/// 信号逻辑：
/// 1. 计算 TNR：`|close_t-close_{t-n}| / sum(|diff(close)|)`；
/// 2. 取最近 `k` 根 TNR 均值，与当前 TNR 比较；
/// 3. 当前值大于均值判 `噪音减少`，否则判 `噪音增加`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1TNR14K3_趋势V230630_噪音减少_任意_任意_0')`
/// - `Signal('15分钟_D1TNR14K3_趋势V230630_噪音增加_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：TNR周期，默认 `14`；
/// - `k`：均值窗口，默认 `3`。
/// 对齐说明：TNR与噪音方向定义对齐 Python `bar_tnr_V230630`。
#[signal(
    category = "kline",
    name = "bar_tnr_V230630",
    template = "{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630",
    opcode = "BarTnrV230630",
    param_kind = "BarTnrV230630"
)]
pub fn bar_tnr_v230630(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let timeperiod = params.usize("timeperiod", 14);
    let k = params.usize("k", 3);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TNR{}K{}", di, timeperiod, k);
    let k3 = "趋势V230630";

    if c.bars_raw.len() < di + timeperiod + 8 || k == 0 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let tnr = calc_tnr_series(c, timeperiod);
    let sub = get_sub_elements(tnr.as_slice(), di, k);
    if sub.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let mean = sub.iter().sum::<f64>() / sub.len() as f64;
    let delta_tnr = sub[sub.len() - 1] - mean;
    let v1 = if delta_tnr > 0.0 {
        "噪音减少"
    } else {
        "噪音增加"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_tnr_V230629：TNR 分层信号
///
/// 参数模板：`"{freq}_D{di}TNR{timeperiod}_趋势V230629"`
///
/// 信号逻辑：
/// 1. 计算每根K线 TNR 值；
/// 2. 取最近100个 TNR 做 `qcut(10)`；
/// 3. 输出末根所在层：`第{n}层`。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1TNR14_趋势V230629_第7层_任意_任意_0')`
/// - `Signal('15分钟_D1TNR14_趋势V230629_第2层_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `timeperiod`：TNR周期，默认 `14`。
/// 对齐说明：分层逻辑与 `duplicates='drop'` 行为对齐 Python `bar_tnr_V230629`。
#[signal(
    category = "kline",
    name = "bar_tnr_V230629",
    template = "{freq}_D{di}TNR{timeperiod}_趋势V230629",
    opcode = "BarTnrV230629",
    param_kind = "BarTnrV230629"
)]
pub fn bar_tnr_v230629(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let timeperiod = params.usize("timeperiod", 14);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TNR{}", di, timeperiod);
    let k3 = "趋势V230629";

    if c.bars_raw.len() < di + timeperiod + 8 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let tnr = calc_tnr_series(c, timeperiod);
    let sub = get_sub_elements(tnr.as_slice(), di, 100);
    if sub.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let v1 = if let Some(lev) = qcut_last_label(sub, 10) {
        format!("第{}层", lev + 1)
    } else {
        "其他".to_string()
    };
    make_kline_signal_v1(&k1, &k2, k3, &v1)
}

/// bar_shuang_fei_V230507：双飞涨停形态
///
/// 参数模板：`"{freq}_D{di}双飞_短线V230507"`
///
/// 信号逻辑：
/// 1. 前天近似涨停、昨天大阴回撤、今天再度强势上涨；
/// 2. 且今天收盘突破昨天高点，判 `看多`；
/// 3. 不满足返回 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_D1双飞_短线V230507_看多_任意_任意_0')`
/// - `Signal('日线_D1双飞_短线V230507_其他_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：三日组合条件对齐 Python `bar_shuang_fei_V230507`。
#[signal(
    category = "kline",
    name = "bar_shuang_fei_V230507",
    template = "{freq}_D{di}双飞_短线V230507",
    opcode = "BarShuangFeiV230507",
    param_kind = "BarShuangFeiV230507"
)]
pub fn bar_shuang_fei_v230507(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}双飞", di);
    let k3 = "短线V230507";

    if c.bars_raw.len() < di + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, 4);
    if bars.len() != 4 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let b4 = &bars[0];
    let b3 = &bars[1];
    let b2 = &bars[2];
    let b1 = &bars[3];
    if b4.close == 0.0 || b3.close == 0.0 || b2.close == 0.0 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let first_zt = (b3.close - b3.high).abs() <= f64::EPSILON && b3.close / b4.close - 1.0 > 0.07;
    let last_zt =
        b1.close / b2.close - 1.0 > 0.07 && bar_upper(b1) < bar_lower(b1).max(bar_solid(b1)) / 2.0;
    let bar2_down = b2.close < b2.open && b2.close / b3.close - 1.0 < -0.05;
    let v1 = if first_zt && last_zt && b1.close > b2.high && bar2_down {
        "看多"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

fn std_pop(values: &[f64]) -> f64 {
    if values.is_empty() || values.iter().any(|x| !x.is_finite()) {
        return f64::NAN;
    }
    let mean = values.iter().sum::<f64>() / values.len() as f64;
    let var = values.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / values.len() as f64;
    var.sqrt()
}

fn qcut_labels(values: &[f64], q: usize) -> Option<Vec<usize>> {
    if q == 0 || values.is_empty() || values.iter().any(|x| !x.is_finite()) {
        return None;
    }
    let mut sorted: Vec<f64> = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let quantile = |p: f64| -> f64 {
        if sorted.len() == 1 {
            return sorted[0];
        }
        let h = (sorted.len() - 1) as f64 * p;
        let i = h.floor() as usize;
        let j = h.ceil() as usize;
        if i == j {
            sorted[i]
        } else {
            sorted[i] + (h - i as f64) * (sorted[j] - sorted[i])
        }
    };

    let mut edges = Vec::with_capacity(q + 1);
    for i in 0..=q {
        edges.push(quantile(i as f64 / q as f64));
    }
    edges.dedup_by(|a, b| (*a - *b).abs() <= f64::EPSILON);
    if edges.len() <= 1 {
        return None;
    }
    let bins = edges.len() - 1;
    let mut labels = Vec::with_capacity(values.len());
    for &x in values {
        if x < edges[0] || x > edges[bins] {
            return None;
        }
        let mut found = None;
        for i in 0..bins {
            let left_ok = if i == 0 { x >= edges[i] } else { x > edges[i] };
            let right_ok = x <= edges[i + 1];
            if left_ok && right_ok {
                found = Some(i);
                break;
            }
        }
        labels.push(found.unwrap_or(bins - 1));
    }
    Some(labels)
}

fn qcut_three_label_last(values: &[f64]) -> Option<&'static str> {
    if values.is_empty() || values.iter().any(|x| !x.is_finite()) {
        return None;
    }
    let mut sorted: Vec<f64> = values.to_vec();
    sorted.sort_by(|a, b| a.partial_cmp(b).unwrap_or(std::cmp::Ordering::Equal));

    let quantile = |p: f64| -> f64 {
        if sorted.len() == 1 {
            return sorted[0];
        }
        let h = (sorted.len() - 1) as f64 * p;
        let i = h.floor() as usize;
        let j = h.ceil() as usize;
        if i == j {
            sorted[i]
        } else {
            sorted[i] + (h - i as f64) * (sorted[j] - sorted[i])
        }
    };

    let mut edges = Vec::with_capacity(4);
    for i in 0..=3 {
        edges.push(quantile(i as f64 / 3.0));
    }
    edges.dedup_by(|a, b| (*a - *b).abs() <= f64::EPSILON);

    // 对齐 pandas.qcut(labels=["低波动","中波动","高波动"], duplicates="drop"):
    // 当重复边界导致箱数 < 3 时，会因为 labels 数量不匹配抛异常，外层返回“其他”。
    if edges.len() != 4 {
        return None;
    }
    let x = *values.last()?;
    if x < edges[0] || x > edges[3] {
        return None;
    }
    if x >= edges[0] && x <= edges[1] {
        return Some("低波动");
    }
    if x > edges[1] && x <= edges[2] {
        return Some("中波动");
    }
    if x > edges[2] && x <= edges[3] {
        return Some("高波动");
    }
    None
}

fn linear_slope_exact(y: &[f64]) -> Option<f64> {
    if y.len() < 2 {
        return None;
    }
    let n = y.len() as f64;
    let sum_x = (n - 1.0) * n / 2.0;
    let sum_xx = (n - 1.0) * n * (2.0 * n - 1.0) / 6.0;
    let sum_y = y.iter().sum::<f64>();
    let sum_xy = y
        .iter()
        .enumerate()
        .map(|(i, v)| i as f64 * *v)
        .sum::<f64>();
    let denom = n * sum_xx - sum_x * sum_x;
    if denom.abs() <= f64::EPSILON {
        return None;
    }
    Some((n * sum_xy - sum_x * sum_y) / denom)
}

fn solve_3x3(mut a: [[f64; 4]; 3]) -> Option<[f64; 3]> {
    for i in 0..3 {
        let mut pivot = i;
        for r in (i + 1)..3 {
            if a[r][i].abs() > a[pivot][i].abs() {
                pivot = r;
            }
        }
        if a[pivot][i].abs() <= f64::EPSILON {
            return None;
        }
        if pivot != i {
            a.swap(i, pivot);
        }
        let d = a[i][i];
        for value in a[i].iter_mut().skip(i) {
            *value /= d;
        }
        for r in 0..3 {
            if r == i {
                continue;
            }
            let f = a[r][i];
            let pivot_row = a[i];
            for (value, pivot_value) in a[r].iter_mut().zip(pivot_row.iter()).skip(i) {
                *value -= f * *pivot_value;
            }
        }
    }
    Some([a[0][3], a[1][3], a[2][3]])
}

fn quadratic_a_exact(y: &[f64]) -> Option<f64> {
    if y.len() < 3 {
        return None;
    }
    let n = y.len() as f64;
    let sx = (n - 1.0) * n / 2.0;
    let sx2 = (n - 1.0) * n * (2.0 * n - 1.0) / 6.0;
    let sx3 = (n * (n - 1.0) / 2.0).powi(2);
    let sx4 = (n - 1.0) * n * (2.0 * n - 1.0) * (3.0 * n * n - 3.0 * n - 1.0) / 30.0;
    let sy = y.iter().sum::<f64>();
    let sxy = y
        .iter()
        .enumerate()
        .map(|(i, v)| i as f64 * *v)
        .sum::<f64>();
    let sx2y = y
        .iter()
        .enumerate()
        .map(|(i, v)| (i as f64).powi(2) * *v)
        .sum::<f64>();
    let aug = [[n, sx, sx2, sy], [sx, sx2, sx3, sxy], [sx2, sx3, sx4, sx2y]];
    let coef = solve_3x3(aug)?;
    Some(coef[2])
}

fn current_ubi_high_low(c: &CZSC) -> Option<(f64, f64)> {
    if c.bars_ubi.is_empty() || c.bi_list.is_empty() {
        return None;
    }
    let raw: Vec<&czsc_core::objects::bar::RawBar> =
        c.bars_ubi.iter().flat_map(|x| x.elements.iter()).collect();
    if raw.is_empty() {
        return None;
    }
    let high = raw.iter().map(|x| x.high).fold(f64::NEG_INFINITY, f64::max);
    let low = raw.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    Some((high, low))
}

/// bar_fang_liang_break_V221216：放量突破与缩量回踩
///
/// 参数模板：`"{freq}_D{di}TH{th}#{ma_type}#{timeperiod}_突破V221216"`
///
/// 信号逻辑：
/// 1. 计算指定均线，检查末根是否放量且站上均线，判 `放量突破`；
/// 2. 检查末根是否缩量且收盘不破均线，且前序收盘与均线距离在阈值内，判 `缩量回踩`；
/// 3. 在窗口长度 `5~9` 中依次尝试，首次出现突破即返回。
///
/// 信号列表示例：
/// - `Signal('15分钟_D1TH300#SMA#233_突破V221216_放量突破_缩量回踩_任意_0')`
/// - `Signal('15分钟_D1TH300#SMA#233_突破V221216_其他_其他_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `th`：回踩距离阈值（BP），默认 `300`；
/// - `ma_type`：均线类型，默认 `SMA`；
/// - `timeperiod`：均线周期，默认 `233`。
/// 对齐说明：窗口扫描与两阶段条件对齐 Python `bar_fang_liang_break_V221216`。
#[signal(
    category = "kline",
    name = "bar_fang_liang_break_V221216",
    template = "{freq}_D{di}TH{th}#{ma_type}#{timeperiod}_突破V221216",
    opcode = "BarFangLiangBreakV221216",
    param_kind = "BarFangLiangBreakV221216"
)]
pub fn bar_fang_liang_break_v221216(
    c: &CZSC,
    params: &ParamView,
    cache: &mut TaCache,
) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let th = params.usize("th", 300);
    let ma_type = params.str("ma_type", "SMA").to_uppercase();
    let timeperiod = params.usize("timeperiod", 233);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}TH{}#{}#{}", di, th, ma_type, timeperiod);
    let k3 = "突破V221216";

    let cache_key = format!("{}_{}_{}", c.freq, ma_type, timeperiod);
    update_ma_cache(c, &cache_key, &ma_type, timeperiod, cache);
    let Some(ma) = cache.series.get(&cache_key) else {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "其他");
    };
    let id_idx: HashMap<i32, usize> = c
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();

    let mut v1 = "其他";
    let mut v2 = "其他";
    let base = if c.bars_raw.len() > 300 {
        &c.bars_raw[300..]
    } else {
        &[] as &[czsc_core::objects::bar::RawBar]
    };

    for n in 5..=9 {
        let bars = get_sub_elements(base, di, n);
        if bars.len() <= 4 {
            v1 = "其他";
            v2 = "其他";
            continue;
        }
        let last = &bars[bars.len() - 1];
        let prev = &bars[bars.len() - 2];
        let Some(&idx) = id_idx.get(&last.id) else {
            continue;
        };
        let ma1v = ma[idx];
        v1 = if last.vol >= prev.vol && last.close > ma1v {
            "放量突破"
        } else {
            "其他"
        };

        let vol_min =
            bars[..bars.len() - 1].iter().map(|x| x.vol).sum::<f64>() / (bars.len() - 1) as f64;
        let distance = if ma1v.abs() <= f64::EPSILON {
            false
        } else {
            bars[..bars.len() - 1]
                .iter()
                .all(|x| ((x.close / ma1v - 1.0).abs() * 10000.0) <= th as f64)
        };
        v2 = if last.close >= ma1v && last.vol < vol_min && distance {
            "缩量回踩"
        } else {
            "其他"
        };
        if v1 != "其他" {
            break;
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, v1, v2)
}

/// bar_channel_V230508：窄幅通道方向判定
///
/// 参数模板：`"{freq}_D{di}M{m}_通道V230507"`
///
/// 信号逻辑：
/// 1. 窗口内每根K线涨跌幅需不超过 `m` BP；
/// 2. 对高点和低点分别做一元线性拟合，要求 `r2 > 0.8`；
/// 3. 双斜率同向且右侧极值确认，判 `看多/看空`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('日线_D1M600_通道V230507_看多_任意_任意_0')`
/// - `Signal('日线_D1M600_通道V230507_看空_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `n`：窗口长度，默认 `20`；
/// - `m`：单根波动阈值（BP），默认 `600`。
/// 对齐说明：拟合阈值和右侧极值规则对齐 Python `bar_channel_V230508`。
#[signal(
    category = "kline",
    name = "bar_channel_V230508",
    template = "{freq}_D{di}M{m}_通道V230508",
    opcode = "BarChannelV230508",
    param_kind = "BarChannelV230508"
)]
pub fn bar_channel_v230508(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("n", 20);
    let m = params.usize("m", 600);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}M{}", di, m);
    let k3 = "通道V230507";

    if c.bars_raw.len() < di + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    if bars
        .iter()
        .any(|x| x.open == 0.0 || ((x.close / x.open - 1.0).abs() * 10000.0 > m as f64))
    {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let highs: Vec<f64> = bars.iter().map(|x| x.high).collect();
    let lows: Vec<f64> = bars.iter().map(|x| x.low).collect();
    let res_high = highs.as_slice().single_linear();
    let res_low = lows.as_slice().single_linear();
    if !(res_high.r2 > 0.8 && res_low.r2 > 0.8) {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let tail = bars.len().min(3);
    let high_right = bars[bars.len() - tail..]
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let low_right = bars[bars.len() - tail..]
        .iter()
        .map(|x| x.low)
        .fold(f64::INFINITY, f64::min);
    let max_high = bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let min_low = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let v1 = if res_high.slope > 0.0
        && res_low.slope > 0.0
        && (high_right - max_high).abs() <= f64::EPSILON
    {
        "看多"
    } else if res_high.slope < 0.0
        && res_low.slope < 0.0
        && (low_right - min_low).abs() <= f64::EPSILON
    {
        "看空"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_eight_V230702：8K 走势分类
///
/// 参数模板：`"{freq}_D{di}#8K_走势分类V230702"`
///
/// 信号逻辑：
/// 1. 统计8K中的三连K重叠中枢；
/// 2. 无中枢时输出 `无中枢上涨/无中枢下跌`；
/// 3. 双中枢满足不重叠时输出 `双中枢上涨/双中枢下跌`；
/// 4. 其余按前三根是否出现极值分为 `强平衡/弱平衡/转折平衡`。
///
/// 信号列表示例：
/// - `Signal('30分钟_D1#8K_走势分类V230702_双中枢上涨_任意_任意_0')`
/// - `Signal('30分钟_D1#8K_走势分类V230702_转折平衡市_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：中枢判定与分类分支顺序对齐 Python `bar_eight_V230702`。
#[signal(
    category = "kline",
    name = "bar_eight_V230702",
    template = "{freq}_D{di}#8K_走势分类V230702",
    opcode = "BarEightV230702",
    param_kind = "BarEightV230702"
)]
pub fn bar_eight_v230702(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}#8K", di);
    let k3 = "走势分类V230702";
    if c.bars_raw.len() < di + 12 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, 8);
    if bars.len() != 8 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let mut zs_list: Vec<[usize; 3]> = Vec::new();
    for i in 0..=bars.len() - 3 {
        let b1 = &bars[i];
        let b2 = &bars[i + 1];
        let b3 = &bars[i + 2];
        if b1.high.min(b2.high).min(b3.high) >= b1.low.max(b2.low).max(b3.low) {
            zs_list.push([i, i + 1, i + 2]);
        }
    }
    let dir = if bars[bars.len() - 1].close > bars[0].open {
        "上涨"
    } else {
        "下跌"
    };
    if zs_list.is_empty() {
        let v = format!("无中枢{}", dir);
        return make_kline_signal_v1(&k1, &k2, k3, &v);
    }

    if zs_list.len() >= 2 {
        let zs1 = zs_list[0];
        let zs2 = zs_list[zs_list.len() - 1];
        let zs1_high = [bars[zs1[0]].high, bars[zs1[1]].high, bars[zs1[2]].high]
            .iter()
            .copied()
            .fold(f64::NEG_INFINITY, f64::max);
        let zs1_low = [bars[zs1[0]].low, bars[zs1[1]].low, bars[zs1[2]].low]
            .iter()
            .copied()
            .fold(f64::INFINITY, f64::min);
        let zs2_high = [bars[zs2[0]].high, bars[zs2[1]].high, bars[zs2[2]].high]
            .iter()
            .copied()
            .fold(f64::NEG_INFINITY, f64::max);
        let zs2_low = [bars[zs2[0]].low, bars[zs2[1]].low, bars[zs2[2]].low]
            .iter()
            .copied()
            .fold(f64::INFINITY, f64::min);
        if dir == "上涨" && zs1_high < zs2_low {
            let v = format!("双中枢{}", dir);
            return make_kline_signal_v1(&k1, &k2, k3, &v);
        }
        if dir == "下跌" && zs1_low > zs2_high {
            let v = format!("双中枢{}", dir);
            return make_kline_signal_v1(&k1, &k2, k3, &v);
        }
    }

    let max_high = bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let min_low = bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let high_first = bars[0].high.max(bars[1].high).max(bars[2].high) == max_high;
    let low_first = bars[0].low.min(bars[1].low).min(bars[2].low) == min_low;
    let v1 = if high_first && !low_first {
        "弱平衡市"
    } else if low_first && !high_first {
        "强平衡市"
    } else {
        "转折平衡市"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_window_std_V230731：窗口波动分层特征
///
/// 参数模板：`"{freq}_D{di}W{w}M{m}N{n}_窗口波动V230731"`
///
/// 信号逻辑：
/// 1. 计算每根K线的 `STD20`（前20收盘标准差）；
/// 2. 取最近 `m` 个 `STD20` 做 `qcut(n)` 分层；
/// 3. 输出最近 `w` 根中的最大层和最小层。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W5M100N10_窗口波动V230731_高波N8_低波N6_任意_0')`
/// - `Signal('60分钟_D1W5M100N10_窗口波动V230731_高波N4_低波N3_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `w`：观察窗口，默认 `5`；
/// - `m`：分层样本长度，默认 `100`；
/// - `n`：分层数量，默认 `10`。
/// 对齐说明：STD20口径与 `qcut(..., duplicates='drop')` 对齐 Python `bar_window_std_V230731`。
#[signal(
    category = "kline",
    name = "bar_window_std_V230731",
    template = "{freq}_D{di}W{w}M{m}N{n}_窗口波动V230731",
    opcode = "BarWindowStdV230731",
    param_kind = "BarWindowStdV230731"
)]
pub fn bar_window_std_v230731(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 5);
    let m = params.usize("m", 100);
    let n = params.usize("n", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}M{}N{}", di, w, m, n);
    let k3 = "窗口波动V230731";

    if c.bars_raw.len() < di + m + w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let closes: Vec<f64> = c.bars_raw.iter().map(|x| x.close).collect();
    let mut std20 = vec![0.0; closes.len()];
    for i in 0..closes.len() {
        std20[i] = if i < 5 {
            0.0
        } else {
            std_pop(&closes[i.saturating_sub(20)..i])
        };
    }
    let stds = get_sub_elements(std20.as_slice(), di, m);
    if stds.len() != m {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let Some(layer) = qcut_labels(stds, n) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let t = layer.len().min(w);
    let tail = &layer[layer.len() - t..];
    let max_layer = tail.iter().copied().max().unwrap_or(0) + 1;
    let min_layer = tail.iter().copied().min().unwrap_or(0) + 1;
    let v1 = format!("高波N{}", max_layer);
    let v2 = format!("低波N{}", min_layer);
    make_kline_signal_v2(&k1, &k2, k3, &v1, &v2)
}

/// bar_window_ps_V230731：支撑压力位分位特征
///
/// 参数模板：`"{freq}_W{w}M{m}N{n}L{l}_支撑压力位V230731"`
///
/// 信号逻辑：
/// 1. 用最近 `n` 笔高低点构造压力线与支撑线；
/// 2. 计算收盘在区间中的位置 `pct=(close-L)/(H-L)`；
/// 3. 对最近 `m` 个 `pct` 做 `qcut(l)`，输出最近 `w` 根的压力/支撑层与当前层。
///
/// 信号列表示例：
/// - `Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N5_支撑N3_当前N4_0')`
/// - `Signal('15分钟_W5M40N8L5_支撑压力位V230731_压力N4_支撑N1_当前N2_0')`
///
/// 参数说明：
/// - `w`：观察窗口，默认 `5`；
/// - `m`：分位样本长度，默认 `40`；
/// - `n`：笔窗口长度，默认 `8`；
/// - `l`：分层数量，默认 `5`。
/// 对齐说明：参数约束与分位定义对齐 Python `bar_window_ps_V230731`。
#[signal(
    category = "kline",
    name = "bar_window_ps_V230731",
    template = "{freq}_W{w}M{m}N{n}L{l}_支撑压力位V230731",
    opcode = "BarWindowPsV230731",
    param_kind = "BarWindowPsV230731"
)]
pub fn bar_window_ps_v230731(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let w = params.usize("w", 5);
    let m = params.usize("m", 40);
    let n = params.usize("n", 8);
    let l = params.usize("l", 5);
    if !(m > l * 2 && l > 2) || w >= m {
        return vec![];
    }

    let k1 = c.freq.to_string();
    let k2 = format!("W{}M{}N{}L{}", w, m, n, l);
    let k3 = "支撑压力位V230731";
    if c.bi_list.len() < n + 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = &c.bi_list[c.bi_list.len() - n..];
    let h_line = bis
        .iter()
        .map(|x| x.get_high())
        .fold(f64::NEG_INFINITY, f64::max);
    let l_line = bis
        .iter()
        .map(|x| x.get_low())
        .fold(f64::INFINITY, f64::min);
    let d = h_line - l_line;
    if d.abs() <= f64::EPSILON {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    // 对齐 Python: bar.cache 仅对“尚未写入该键”的 bar 做一次写入，历史值不回溯覆盖。
    let pct_key = format!("bar_window_ps_V230731#pct#W{}M{}N{}L{}", w, m, n, l);
    let bar_ids: Vec<i32> = c.bars_raw.iter().map(|b| b.id).collect();
    let mut pct_series = if let (Some(vals), Some(ids)) =
        (cache.series.get(&pct_key), cache.series_ids.get(&pct_key))
    {
        let mut id_val: HashMap<i32, f64> = HashMap::with_capacity(ids.len());
        for (i, id) in ids.iter().enumerate() {
            id_val.insert(*id, vals[i]);
        }
        bar_ids
            .iter()
            .map(|id| *id_val.get(id).unwrap_or(&f64::NAN))
            .collect::<Vec<f64>>()
    } else {
        vec![f64::NAN; bar_ids.len()]
    };
    for (i, bar) in c.bars_raw.iter().enumerate() {
        let is_last = i + 1 == c.bars_raw.len();
        if is_last || !pct_series[i].is_finite() {
            // 对齐 Python 多频流式更新语义：最后一根未完成 bar 在每次 on_bar 时都会携带最新 close，
            // 不能复用更早时刻写入的 pct；历史 bar 仍保持“只写一次”。
            pct_series[i] = (bar.close - l_line) / d;
        }
    }
    cache.series.insert(pct_key.clone(), pct_series.clone());
    cache.series_ids.insert(pct_key, bar_ids);

    let fenwei = get_sub_elements(pct_series.as_slice(), 1, m);
    if fenwei.len() != m {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let Some(layer) = qcut_labels(fenwei, l) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let t = layer.len().min(w);
    let tail = &layer[layer.len() - t..];
    let max_layer = tail.iter().copied().max().unwrap_or(0) + 1;
    let min_layer = tail.iter().copied().min().unwrap_or(0) + 1;
    let cur_layer = layer[layer.len() - 1] + 1;
    let v1 = format!("压力N{}", max_layer);
    let v2 = format!("支撑N{}", min_layer);
    let v3 = format!("当前N{}", cur_layer);
    make_kline_signal_v3(&k1, &k2, k3, &v1, &v2, &v3)
}

/// bar_window_ps_V230801：支撑压力位窗口极值
///
/// 参数模板：`"{freq}_N{n}W{w}_支撑压力位V230801"`
///
/// 信号逻辑：
/// 1. 基于最近 `n` 笔和当前未完成笔计算压力/支撑区间；
/// 2. 将最近 `w` 根收盘映射到 `0~9` 分位整数；
/// 3. 输出窗口最大/最小/当前分位。
///
/// 信号列表示例：
/// - `Signal('60分钟_N8W5_支撑压力位V230801_最大N7_最小N3_当前N5_0')`
/// - `Signal('60分钟_N8W5_支撑压力位V230801_最大N4_最小N0_当前N2_0')`
///
/// 参数说明：
/// - `w`：观察窗口，默认 `5`；
/// - `n`：笔窗口长度，默认 `8`。
/// 对齐说明：`ubi` 口径与整数分位映射对齐 Python `bar_window_ps_V230801`。
#[signal(
    category = "kline",
    name = "bar_window_ps_V230801",
    template = "{freq}_N{n}W{w}_支撑压力位V230801",
    opcode = "BarWindowPsV230801",
    param_kind = "BarWindowPsV230801"
)]
pub fn bar_window_ps_v230801(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let w = params.usize("w", 5);
    let n = params.usize("n", 8);
    let k1 = c.freq.to_string();
    let k2 = format!("N{}W{}", n, w);
    let k3 = "支撑压力位V230801";

    // 对齐 Python `if len(c.bi_list) < n + 2 or not ubi: return 其他`：
    // Rust 中 ubi 判空需同时满足 bars_ubi/bi_list 非空且 ubi_fxs 非空。
    let Some(ubi_fxs) = c.get_ubi_fxs() else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    if ubi_fxs.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let Some((ubi_high, ubi_low)) = current_ubi_high_low(c) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    if c.bi_list.len() < n + 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bis = &c.bi_list[c.bi_list.len() - n..];
    let h_line = bis.iter().map(|x| x.get_high()).fold(ubi_high, f64::max);
    let l_line = bis.iter().map(|x| x.get_low()).fold(ubi_low, f64::min);
    let d = h_line - l_line;
    if d.abs() <= f64::EPSILON {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = if c.bars_raw.len() >= w {
        &c.bars_raw[c.bars_raw.len() - w..]
    } else {
        &c.bars_raw[..]
    };
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let pcts: Vec<i32> = bars
        .iter()
        .map(|x| (((x.close - l_line) / d).max(0.0) * 10.0) as i32)
        .collect();
    let v1 = format!("最大N{}", pcts.iter().copied().max().unwrap_or(0));
    let v2 = format!("最小N{}", pcts.iter().copied().min().unwrap_or(0));
    let v3 = format!("当前N{}", pcts[pcts.len() - 1]);
    make_kline_signal_v3(&k1, &k2, k3, &v1, &v2, &v3)
}

/// bar_trend_V240209：趋势跟踪结构判定
///
/// 参数模板：`"{freq}_D{di}N{N}趋势跟踪_BS辅助V240209"`
///
/// 信号逻辑：
/// 1. 在窗口内定位最高点和最低点，结合其先后顺序选择多头或空头分支；
/// 2. 右侧结构满足 `5<bar差<30`、回撤不破前极值、DIF/MACD 收敛；
/// 3. 满足时输出 `多头/空头`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1N60趋势跟踪_BS辅助V240209_多头_任意_任意_0')`
/// - `Signal('60分钟_D1N60趋势跟踪_BS辅助V240209_空头_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `N`：观察窗口，默认 `60`。
/// 对齐说明：结构过滤与 MACD 约束对齐 Python `bar_trend_V240209`。
#[signal(
    category = "kline",
    name = "bar_trend_V240209",
    template = "{freq}_D{di}N{N}趋势跟踪_BS辅助V240209",
    opcode = "BarTrendV240209",
    param_kind = "BarTrendV240209"
)]
pub fn bar_trend_v240209(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let n = params.usize("N", 60);
    let k1 = c.freq.to_string();
    let k2 = format!("D{}N{}趋势跟踪", di, n);
    let k3 = "BS辅助V240209";
    if c.bars_raw.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let cache_key = "MACD12#26#9";
    update_macd_cache(c, cache_key, 12, 26, 9, cache);
    let Some(macd) = cache.macd.get(cache_key) else {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    };
    let bars = get_sub_elements(&c.bars_raw, di, n);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    // 对齐 Python min/max(key=...): 并列时取首次出现。
    let mut max_bar = &bars[0];
    let mut min_bar = &bars[0];
    for b in &bars[1..] {
        if b.high > max_bar.high {
            max_bar = b;
        }
        if b.low < min_bar.low {
            min_bar = b;
        }
    }
    let id_to_idx: HashMap<i32, usize> =
        macd.ids.iter().enumerate().map(|(i, x)| (*x, i)).collect();
    let dif_vals: Vec<f64> = bars
        .iter()
        .filter_map(|x| id_to_idx.get(&x.id).map(|i| macd.dif[*i]))
        .collect();
    let macd_vals: Vec<f64> = bars
        .iter()
        .filter_map(|x| id_to_idx.get(&x.id).map(|i| macd.macd[*i]))
        .collect();
    let dif_std = std_pop(&dif_vals);
    let macd_std = std_pop(&macd_vals);

    if min_bar.dt < max_bar.dt {
        let right: Vec<&czsc_core::objects::bar::RawBar> =
            c.bars_raw.iter().filter(|x| x.dt >= max_bar.dt).collect();
        if !right.is_empty() {
            let mut right_min = right[0];
            for b in &right[1..] {
                if b.low < right_min.low {
                    right_min = b;
                }
            }
            let last = right[right.len() - 1];
            let c1 = right_min.id - max_bar.id < 30 && right_min.id - max_bar.id > 5;
            let c2 = id_to_idx
                .get(&last.id)
                .map(|i| macd.dif[*i].abs() < dif_std)
                .unwrap_or(false);
            let c3 = right_min.low > min_bar.low;
            let c4 = id_to_idx
                .get(&last.id)
                .map(|i| macd.macd[*i].abs() < macd_std)
                .unwrap_or(false);
            if c1 && c2 && c3 && c4 {
                return make_kline_signal_v1(&k1, &k2, k3, "多头");
            }
        }
    }

    if min_bar.dt > max_bar.dt {
        let right: Vec<&czsc_core::objects::bar::RawBar> =
            c.bars_raw.iter().filter(|x| x.dt >= min_bar.dt).collect();
        if !right.is_empty() {
            let mut right_max = right[0];
            for b in &right[1..] {
                if b.high > right_max.high {
                    right_max = b;
                }
            }
            let last = right[right.len() - 1];
            let c1 = right_max.id - min_bar.id < 30 && right_max.id - min_bar.id > 5;
            let c2 = id_to_idx
                .get(&last.id)
                .map(|i| macd.dif[*i].abs() < dif_std)
                .unwrap_or(false);
            let c3 = right_max.high < max_bar.high;
            let c4 = id_to_idx
                .get(&last.id)
                .map(|i| macd.macd[*i].abs() < macd_std)
                .unwrap_or(false);
            if c1 && c2 && c3 && c4 {
                return make_kline_signal_v1(&k1, &k2, k3, "空头");
            }
        }
    }

    make_kline_signal_v1(&k1, &k2, k3, "其他")
}

/// bar_plr_V240427：盈亏比约束
///
/// 参数模板：`"{freq}_D{di}W{w}T{t}M{m}_盈亏比V240427"`
///
/// 信号逻辑：
/// 1. `多头`：以窗口最低点前的最高点与当前收盘计算盈亏比；
/// 2. `空头`：以窗口最高点前的最低点与当前收盘计算盈亏比；
/// 3. `plr > t/10` 判 `满足`，否则 `不满足`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W60T20M多头_盈亏比V240427_满足_任意_任意_0')`
/// - `Signal('60分钟_D1W60T20M空头_盈亏比V240427_不满足_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `w`：窗口长度，默认 `60`；
/// - `t`：阈值（`t/10`），默认 `20`；
/// - `m`：方向，`多头/空头`，默认 `多头`。
/// 对齐说明：盈亏比定义与阈值比较对齐 Python `bar_plr_V240427`。
#[signal(
    category = "kline",
    name = "bar_plr_V240427",
    template = "{freq}_D{di}W{w}T{t}M{m}_盈亏比V240427",
    opcode = "BarPlrV240427",
    param_kind = "BarPlrV240427"
)]
pub fn bar_plr_v240427(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 60);
    let t = params.usize("t", 20);
    let m = params.str("m", "多头");
    if m != "多头" && m != "空头" {
        return vec![];
    }
    if di == 0 || w < 10 {
        return vec![];
    }
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}T{}M{}", di, w, t, m);
    let k3 = "盈亏比V240427";
    if c.bars_raw.len() < 7 + w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.is_empty() {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let last_close = bars[bars.len() - 1].close;
    let mut v1 = "其他";

    if m == "多头" {
        let (idx_low, low_bar) = bars
            .iter()
            .enumerate()
            .min_by(|a, b| {
                a.1.low
                    .partial_cmp(&b.1.low)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap();
        if idx_low == 0 {
            return make_kline_signal_v1(&k1, &k2, k3, v1);
        }
        let high_bar = bars[..idx_low]
            .iter()
            .max_by(|a, b| {
                a.high
                    .partial_cmp(&b.high)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap();
        let profit = high_bar.high - last_close;
        let loss = last_close - low_bar.low;
        let plr = if loss > 0.0 { profit / loss } else { 0.0 };
        v1 = if plr > t as f64 / 10.0 {
            "满足"
        } else {
            "不满足"
        };
    }

    if m == "空头" {
        let (idx_high, high_bar) = bars
            .iter()
            .enumerate()
            .max_by(|a, b| {
                a.1.high
                    .partial_cmp(&b.1.high)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap();
        if idx_high == 0 {
            return make_kline_signal_v1(&k1, &k2, k3, v1);
        }
        let low_bar = bars[..idx_high]
            .iter()
            .min_by(|a, b| {
                a.low
                    .partial_cmp(&b.low)
                    .unwrap_or(std::cmp::Ordering::Equal)
            })
            .unwrap();
        let profit = last_close - low_bar.low;
        let loss = high_bar.high - last_close;
        let plr = if loss > 0.0 { profit / loss } else { 0.0 };
        v1 = if plr > t as f64 / 10.0 {
            "满足"
        } else {
            "不满足"
        };
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_polyfit_V240428：一阶二阶拟合分类
///
/// 参数模板：`"{freq}_D{di}W{w}_分类V240428"`
///
/// 信号逻辑：
/// 1. 对窗口收盘价做一阶拟合取斜率 `p1`；
/// 2. 做二阶拟合取二次项系数 `p2`；
/// 3. 按 `p1/p2` 符号组合输出 `加速上涨/减速上涨/加速下跌/减速下跌`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W20_分类V240428_加速上涨_任意_任意_0')`
/// - `Signal('60分钟_D1W20_分类V240428_减速下跌_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `w`：窗口长度，默认 `20`。
/// 对齐说明：一二阶系数组合分类对齐 Python `bar_polyfit_V240428`。
#[signal(
    category = "kline",
    name = "bar_polyfit_V240428",
    template = "{freq}_D{di}W{w}_分类V240428",
    opcode = "BarPolyfitV240428",
    param_kind = "BarPolyfitV240428"
)]
pub fn bar_polyfit_v240428(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 20);
    if di == 0 || w < 10 {
        return vec![];
    }
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}", di, w);
    let k3 = "分类V240428";
    if c.bars_raw.len() < 7 + w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.len() != w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let close: Vec<f64> = bars.iter().map(|x| x.close).collect();
    let p1 = linear_slope_exact(&close).unwrap_or(0.0);
    let p2 = quadratic_a_exact(&close).unwrap_or(0.0);
    let v1 = if p1 > 0.0 && p2 > 0.0 {
        "加速上涨"
    } else if p1 < 0.0 && p2 < 0.0 {
        "加速下跌"
    } else if p1 > 0.0 && p2 < 0.0 {
        "减速上涨"
    } else if p1 < 0.0 && p2 > 0.0 {
        "减速下跌"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_break_V240428：收盘极值突破
///
/// 参数模板：`"{freq}_D{di}W{w}_事件V240428"`
///
/// 信号逻辑：
/// 1. 在窗口内比较末根收盘与前序最高/最低；
/// 2. 收盘高于前序最高判 `收盘新高`；
/// 3. 收盘低于前序最低判 `收盘新低`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1W20_事件V240428_收盘新高_任意_任意_0')`
/// - `Signal('60分钟_D1W20_事件V240428_收盘新低_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`；
/// - `w`：窗口长度，默认 `20`。
/// 对齐说明：极值比较区间与 Python `bar_break_V240428` 一致。
#[signal(
    category = "kline",
    name = "bar_break_V240428",
    template = "{freq}_D{di}W{w}_事件V240428",
    opcode = "BarBreakV240428",
    param_kind = "BarBreakV240428"
)]
pub fn bar_break_v240428(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    let w = params.usize("w", 20);
    if di == 0 || w < 10 {
        return vec![];
    }
    let k1 = c.freq.to_string();
    let k2 = format!("D{}W{}", di, w);
    let k3 = "事件V240428";
    if c.bars_raw.len() < 7 + w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, w);
    if bars.len() < 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let last = &bars[bars.len() - 1];
    let prev_high = bars[..bars.len() - 1]
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let prev_low = bars[..bars.len() - 1]
        .iter()
        .map(|x| x.low)
        .fold(f64::INFINITY, f64::min);
    let v1 = if last.close > prev_high {
        "收盘新高"
    } else if last.close < prev_low {
        "收盘新低"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_classify_V240606：单根K线收盘位置分类
///
/// 参数模板：`"{freq}_D{di}收盘位置_分类V240606"`
///
/// 信号逻辑：
/// 1. 将K线高低区间三等分；
/// 2. 收盘落在上三分之一判 `高位`；
/// 3. 收盘落在下三分之一判 `低位`，否则 `中间`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1收盘位置_分类V240606_高位_任意_任意_0')`
/// - `Signal('60分钟_D1收盘位置_分类V240606_中间_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：三分位阈值与 Python `bar_classify_V240606` 一致。
#[signal(
    category = "kline",
    name = "bar_classify_V240606",
    template = "{freq}_D{di}收盘位置_分类V240606",
    opcode = "BarClassifyV240606",
    param_kind = "BarClassifyV240606"
)]
pub fn bar_classify_v240606(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    if di == 0 {
        return vec![];
    }
    let k1 = c.freq.to_string();
    let k2 = format!("D{}收盘位置", di);
    let k3 = "分类V240606";
    if c.bars_raw.len() < 7 + di {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bar = &c.bars_raw[c.bars_raw.len() - di];
    let gap = (bar.high - bar.low) / 3.0;
    let v1 = if bar.close > (bar.high - gap) {
        "高位"
    } else if bar.close < (bar.low + gap) {
        "低位"
    } else {
        "中间"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_classify_V240607：两根K线收盘位置分类
///
/// 参数模板：`"{freq}_D{di}K2收盘位置_分类V240607"`
///
/// 信号逻辑：
/// 1. 取最近两根K线（截至 `di`）；
/// 2. 第二根收盘高于第一根最高判 `看多`；
/// 3. 第二根收盘低于第一根最低判 `看空`，否则 `中性`。
///
/// 信号列表示例：
/// - `Signal('60分钟_D1K2收盘位置_分类V240607_看多_任意_任意_0')`
/// - `Signal('60分钟_D1K2收盘位置_分类V240607_中性_任意_任意_0')`
///
/// 参数说明：
/// - `di`：倒数第 `di` 根K线，默认 `1`。
/// 对齐说明：两根K线比较规则与 Python `bar_classify_V240607` 一致。
#[signal(
    category = "kline",
    name = "bar_classify_V240607",
    template = "{freq}_D{di}K2收盘位置_分类V240607",
    opcode = "BarClassifyV240607",
    param_kind = "BarClassifyV240607"
)]
pub fn bar_classify_v240607(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let di = params.usize("di", 1);
    if di == 0 {
        return vec![];
    }
    let k1 = c.freq.to_string();
    let k2 = format!("D{}K2收盘位置", di);
    let k3 = "分类V240607";
    if c.bars_raw.len() < 7 + di {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, di, 2);
    if bars.len() != 2 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bar1 = &bars[0];
    let bar2 = &bars[1];
    let v1 = if bar2.close > bar1.high {
        "看多"
    } else if bar2.close < bar1.low {
        "看空"
    } else {
        "中性"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_decision_V240608：放量反向决策区
///
/// 参数模板：`"{freq}_W{w}N{n}Q{q}放量_决策区域V240608"`
///
/// 信号逻辑：
/// 1. 在最近 `n` 根中取成交量最大的3根；
/// 2. 若三者成交量都大于最近 `w` 根的 `q` 分位；
/// 3. 且 `n` 窗口净涨则 `看空`，净跌则 `看多`。
///
/// 信号列表示例：
/// - `Signal('60分钟_W300N10Q80放量_决策区域V240608_看空_任意_任意_0')`
/// - `Signal('60分钟_W300N10Q80放量_决策区域V240608_看多_任意_任意_0')`
///
/// 参数说明：
/// - `w`：长窗口，默认 `300`；
/// - `n`：短窗口，默认 `10`；
/// - `q`：成交量分位阈值（0-100），默认 `80`。
/// 对齐说明：分位阈值与反向判定对齐 Python `bar_decision_V240608`。
#[signal(
    category = "kline",
    name = "bar_decision_V240608",
    template = "{freq}_W{w}N{n}Q{q}放量_决策区域V240608",
    opcode = "BarDecisionV240608",
    param_kind = "BarDecisionV240608"
)]
pub fn bar_decision_v240608(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let w = params.usize("w", 300);
    let n = params.usize("n", 10);
    let q = params.usize("q", 80);
    if !(w > n && n > 3) {
        return vec![];
    }
    let k1 = c.freq.to_string();
    let k2 = format!("W{}N{}Q{}放量", w, n, q);
    let k3 = "决策区域V240608";
    if c.bars_raw.len() < w + n {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let w_bars = get_sub_elements(&c.bars_raw, 1, w);
    let n_bars = get_sub_elements(&c.bars_raw, 1, n);
    if w_bars.len() != w || n_bars.len() != n {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let n_diff = n_bars[n_bars.len() - 1].close - n_bars[0].open;
    let mut top3: Vec<f64> = n_bars.iter().map(|x| x.vol).collect();
    top3.sort_by(|a, b| b.partial_cmp(a).unwrap_or(std::cmp::Ordering::Equal));
    top3.truncate(3);
    let vols: Vec<f64> = w_bars.iter().map(|x| x.vol).collect();
    let qth = percentile_linear(&vols, q as f64).unwrap_or(f64::INFINITY);
    let vol_match = top3.iter().all(|x| *x > qth);
    let v1 = if vol_match && n_diff > 0.0 {
        "看空"
    } else if vol_match && n_diff < 0.0 {
        "看多"
    } else {
        "其他"
    };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

fn close_position_label(bar: &czsc_core::objects::bar::RawBar) -> &'static str {
    let hl = bar.high - bar.low;
    let t1 = bar.low + hl * (2.0 / 3.0);
    let t2 = bar.low + hl * (1.0 / 3.0);
    if bar.close > t1 {
        "高位收盘"
    } else if bar.close > t2 && bar.close < t1 {
        "中位收盘"
    } else {
        "低位收盘"
    }
}

/// bar_decision_V240616：新高新低后的强弱决策
///
/// 参数模板：`"{freq}_W{w}N{n}强弱_决策区域V240616"`
///
/// 信号逻辑：
/// 1. 用 `di=n` 的 `w` 窗口给出历史新高/新低参考；
/// 2. 在最近 `n` 根中过滤出大实体K线并按顺序检查其右侧K线；
/// 3. 新高后转弱判 `看空`，新低后转强判 `看多`。
///
/// 信号列表示例：
/// - `Signal('60分钟_W100N5强弱_决策区域V240616_看空_任意_任意_0')`
/// - `Signal('60分钟_W100N5强弱_决策区域V240616_看多_任意_任意_0')`
///
/// 参数说明：
/// - `w`：参考窗口，默认 `100`；
/// - `n`：决策窗口，默认 `5`。
/// 对齐说明：候选筛选与右侧确认流程对齐 Python `bar_decision_V240616`。
#[signal(
    category = "kline",
    name = "bar_decision_V240616",
    template = "{freq}_W{w}N{n}强弱_决策区域V240616",
    opcode = "BarDecisionV240616",
    param_kind = "BarDecisionV240616"
)]
pub fn bar_decision_v240616(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let w = params.usize("w", 100);
    let n = params.usize("n", 5);
    if !(w > n && n > 2) {
        return vec![];
    }
    let k1 = c.freq.to_string();
    let k2 = format!("W{}N{}强弱", w, n);
    let k3 = "决策区域V240616";
    if c.bars_raw.len() < w + n + 10 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }

    let w_bars = get_sub_elements(&c.bars_raw, n, w);
    if w_bars.len() != w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let w_high = w_bars
        .iter()
        .map(|x| x.high)
        .fold(f64::NEG_INFINITY, f64::max);
    let w_low = w_bars.iter().map(|x| x.low).fold(f64::INFINITY, f64::min);
    let hl_mean = w_bars.iter().map(|x| x.high - x.low).sum::<f64>() / w_bars.len() as f64;

    let nb = get_sub_elements(&c.bars_raw, 1, n);
    let n_bars: Vec<&czsc_core::objects::bar::RawBar> =
        nb.iter().filter(|x| x.high - x.low > hl_mean).collect();

    let mut v1 = "其他";
    for i in 0..n_bars.len() {
        let bar = n_bars[i];
        let right = &n_bars[i + 1..];
        if right.is_empty() {
            return make_kline_signal_v1(&k1, &k2, k3, v1);
        }
        if bar.high >= w_high && close_position_label(bar) != "高位收盘" {
            for rb in right {
                if close_position_label(rb) == "低位收盘" || rb.close < rb.low {
                    v1 = "看空";
                    break;
                }
            }
        }
        if bar.low <= w_low && close_position_label(bar) != "低位收盘" {
            for rb in right {
                if close_position_label(rb) == "高位收盘" || rb.close > rb.high {
                    v1 = "看多";
                    break;
                }
            }
        }
    }
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_td9_V240616：神奇九转计数
///
/// 参数模板：`"{freq}_神奇九转N{n}_BS辅助V240616"`
///
/// 信号逻辑：
/// 1. 当前收盘与4根前收盘比较，得到 `1/-1/0`；
/// 2. 统计末端连续同号个数；
/// 3. 连续 `>=n` 个 `1` 输出 `卖点`，连续 `>=n` 个 `-1` 输出 `买点`。
///
/// 信号列表示例：
/// - `Signal('60分钟_神奇九转N9_BS辅助V240616_卖点_9转_任意_0')`
/// - `Signal('60分钟_神奇九转N9_BS辅助V240616_买点_9转_任意_0')`
///
/// 参数说明：
/// - `n`：连续计数阈值，默认 `9`。
/// 对齐说明：计数窗口与买卖点定义对齐 Python `bar_td9_V240616`。
#[signal(
    category = "kline",
    name = "bar_td9_V240616",
    template = "{freq}_神奇九转N{n}_BS辅助V240616",
    opcode = "BarTd9V240616",
    param_kind = "BarTd9V240616"
)]
pub fn bar_td9_v240616(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 9);
    let k1 = c.freq.to_string();
    let k2 = format!("神奇九转N{}", n);
    let k3 = "BS辅助V240616";
    if c.bars_raw.len() < 30 + n {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }
    let mut s = vec![0i32; c.bars_raw.len()];
    for (i, s_i) in s.iter_mut().enumerate().skip(4) {
        *s_i = if c.bars_raw[i].close > c.bars_raw[i - 4].close {
            1
        } else if c.bars_raw[i].close < c.bars_raw[i - 4].close {
            -1
        } else {
            0
        };
    }
    let bars = get_sub_elements(&c.bars_raw, 1, n * 2);
    if bars.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }
    let idx_map: HashMap<i32, usize> = c
        .bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect();
    let bar_signs: Vec<i32> = bars
        .iter()
        .filter_map(|b| idx_map.get(&b.id).map(|i| s[*i]))
        .collect();
    if bar_signs.is_empty() {
        return make_kline_signal_v2(&k1, &k2, k3, "其他", "任意");
    }

    let mut v1 = "其他".to_string();
    let mut v2 = "任意".to_string();
    if bar_signs[bar_signs.len() - 1] == 1 {
        let mut count = 0usize;
        for x in bar_signs.iter().rev() {
            if *x != 1 {
                break;
            }
            count += 1;
        }
        if count >= n {
            v1 = "卖点".to_string();
            v2 = format!("{}转", count);
        }
    } else if bar_signs[bar_signs.len() - 1] == -1 {
        let mut count = 0usize;
        for x in bar_signs.iter().rev() {
            if *x != -1 {
                break;
            }
            count += 1;
        }
        if count >= n {
            v1 = "买点".to_string();
            v2 = format!("{}转", count);
        }
    }
    make_kline_signal_v2(&k1, &k2, k3, &v1, &v2)
}

/// bar_volatility_V241013：波动率三层分类
///
/// 参数模板：`"{freq}_波动率分层W{w}N{n}_完全分类V241013"`
///
/// 信号逻辑：
/// 1. 定义 `volatility_n = 最近n根收盘最大值-最小值`；
/// 2. 对最近 `w` 根缓存值做三分位分层；
/// 3. 末根分层输出 `低波动/中波动/高波动`。
///
/// 信号列表示例：
/// - `Signal('60分钟_波动率分层W200N10_完全分类V241013_低波动_任意_任意_0')`
/// - `Signal('60分钟_波动率分层W200N10_完全分类V241013_高波动_任意_任意_0')`
///
/// 参数说明：
/// - `w`：分层窗口，默认 `200`；
/// - `n`：波动率窗口，默认 `10`。
/// 对齐说明：缓存写入与 `qcut` 退化行为对齐 Python `bar_volatility_V241013`。
#[signal(
    category = "kline",
    name = "bar_volatility_V241013",
    template = "{freq}_波动率分层W{w}N{n}_完全分类V241013",
    opcode = "BarVolatilityV241013",
    param_kind = "BarVolatilityV241013"
)]
pub fn bar_volatility_v241013(c: &CZSC, params: &ParamView, cache: &mut TaCache) -> Vec<Signal> {
    let w = params.usize("w", 200);
    let n = params.usize("n", 10);
    let k1 = c.freq.to_string();
    let k2 = format!("波动率分层W{}N{}", w, n);
    let k3 = "完全分类V241013";

    let key = format!("bar_volatility_V241013#volatility_{}", n);
    let ids: Vec<i32> = c.bars_raw.iter().map(|b| b.id).collect();
    let mut series =
        if let (Some(v), Some(sid)) = (cache.series.get(&key), cache.series_ids.get(&key)) {
            let mut m: HashMap<i32, f64> = HashMap::with_capacity(sid.len());
            for (i, id) in sid.iter().enumerate() {
                m.insert(*id, v[i]);
            }
            ids.iter()
                .map(|id| *m.get(id).unwrap_or(&f64::NAN))
                .collect::<Vec<f64>>()
        } else {
            vec![f64::NAN; ids.len()]
        };
    if !c.bars_raw.is_empty() {
        // 对齐 Python：仅检查“当前最后 n 根”是否缺 cache，
        // 若缺失则统一写入“当前最后 n 根 close 极差”。
        // 这意味着：
        // 1. 更早历史不会被回填，未初始化值继续保留为 NaN（后续按 0 参与分层）；
        // 2. 最后一根未完成高周期 bar 在流式更新时会被重建，因此末值需要每次覆盖。
        let last = c.bars_raw.len() - 1;
        let start = (last + 1).saturating_sub(n);
        let window = &c.bars_raw[start..=last];
        let n_max = window
            .iter()
            .map(|x| x.close)
            .fold(f64::NEG_INFINITY, f64::max);
        let n_min = window.iter().map(|x| x.close).fold(f64::INFINITY, f64::min);
        let current_vol = n_max - n_min;

        for item in series.iter_mut().take(last + 1).skip(start) {
            if !item.is_finite() {
                *item = current_vol;
            }
        }
        series[last] = current_vol;
    }
    cache.series.insert(key.clone(), series.clone());
    cache.series_ids.insert(key, ids);

    if c.bars_raw.len() < w + n + 100 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let tail = get_sub_elements(series.as_slice(), 1, w);
    if tail.len() != w {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let vols: Vec<f64> = tail
        .iter()
        .map(|x| if x.is_finite() { *x } else { 0.0 })
        .collect();
    let v1 = qcut_three_label_last(&vols).unwrap_or("其他");
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_zfzd_V241013：窄幅震荡（全重叠）
///
/// 参数模板：`"{freq}_窄幅震荡N{n}_形态V241013"`
///
/// 信号逻辑：
/// 1. 取最近 `n` 根K线；
/// 2. 若 `min(high) >= max(low)`，判为窗口内全重叠；
/// 3. 输出 `满足`，否则 `其他`。
///
/// 信号列表示例：
/// - `Signal('60分钟_窄幅震荡N5_形态V241013_满足_任意_任意_0')`
/// - `Signal('60分钟_窄幅震荡N5_形态V241013_其他_任意_任意_0')`
///
/// 参数说明：
/// - `n`：窗口长度，默认 `5`。
/// 对齐说明：重叠判定公式与 Python `bar_zfzd_V241013` 一致。
#[signal(
    category = "kline",
    name = "bar_zfzd_V241013",
    template = "{freq}_窄幅震荡N{n}_形态V241013",
    opcode = "BarZfzdV241013",
    param_kind = "BarZfzdV241013"
)]
pub fn bar_zfzd_v241013(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("窄幅震荡N{}", n);
    let k3 = "形态V241013";
    if c.bars_raw.len() < n + 50 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, n);
    if bars.len() != n {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let zg = bars.iter().map(|x| x.high).fold(f64::INFINITY, f64::min);
    let zd = bars.iter().map(|x| x.low).fold(f64::NEG_INFINITY, f64::max);
    let v1 = if zg >= zd { "满足" } else { "其他" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}

/// bar_zfzd_V241014：窄幅震荡（最大实体重叠）
///
/// 参数模板：`"{freq}_窄幅震荡N{n}_形态V241014"`
///
/// 信号逻辑：
/// 1. 找到窗口内最大实体K线；
/// 2. 若其实体明显过大（超过窗口实体均值2倍）直接排除；
/// 3. 若该K线与窗口内所有K线区间均重叠，判 `满足`。
///
/// 信号列表示例：
/// - `Signal('60分钟_窄幅震荡N10_形态V241014_满足_任意_任意_0')`
/// - `Signal('60分钟_窄幅震荡N10_形态V241014_其他_任意_任意_0')`
///
/// 参数说明：
/// - `n`：窗口长度，默认 `5`。
/// 对齐说明：最大实体筛选与重叠判断对齐 Python `bar_zfzd_V241014`。
#[signal(
    category = "kline",
    name = "bar_zfzd_V241014",
    template = "{freq}_窄幅震荡N{n}_形态V241014",
    opcode = "BarZfzdV241014",
    param_kind = "BarZfzdV241014"
)]
pub fn bar_zfzd_v241014(c: &CZSC, params: &ParamView, _cache: &mut TaCache) -> Vec<Signal> {
    let n = params.usize("n", 5);
    let k1 = c.freq.to_string();
    let k2 = format!("窄幅震荡N{}", n);
    let k3 = "形态V241014";
    if c.bars_raw.len() < n + 50 {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let bars = get_sub_elements(&c.bars_raw, 1, n);
    if bars.len() != n {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let mut max_bar = &bars[0];
    for b in &bars[1..] {
        if bar_solid(b) > bar_solid(max_bar) {
            max_bar = b;
        }
    }
    let mean_solid = bars.iter().map(bar_solid).sum::<f64>() / bars.len() as f64;
    if bar_solid(max_bar) > 2.0 * mean_solid {
        return make_kline_signal_v1(&k1, &k2, k3, "其他");
    }
    let ok = bars
        .iter()
        .all(|x| x.high.min(max_bar.high) > x.low.max(max_bar.low));
    let v1 = if ok { "满足" } else { "其他" };
    make_kline_signal_v1(&k1, &k2, k3, v1)
}
