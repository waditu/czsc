use crate::params::ParamView;
use chrono::{Datelike, Duration, Timelike};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::RawBar;
use czsc_core::objects::operate::Operate;
use czsc_core::objects::position::OperateRecord;
use czsc_core::objects::signal::Signal;
use czsc_core::objects::state::TraderState;
use std::collections::HashMap;
use std::str::FromStr;

/// 获取截止到倒数第 `di` 个元素的前 `n` 个元素
///
/// 对齐 Python `get_sub_elements` 语义：
/// - `di == 1` 时返回最后 `n` 个；
/// - `di > 1` 时返回 `[-n-di+1 : -di+1]`；
/// - 数量不足时返回可用区间（可能为空）。
pub fn get_sub_elements<T>(elements: &[T], di: usize, n: usize) -> &[T] {
    assert!(di >= 1, "di must be >= 1");
    if elements.is_empty() || di > elements.len() {
        return &elements[0..0];
    }
    // 对齐 Python 切片语义：
    // get_sub_elements(elements, di=1, n=0) -> elements[-0:] -> 全量
    if n == 0 {
        return if di == 1 {
            &elements[0..elements.len()]
        } else {
            &elements[0..0]
        };
    }

    let end = elements.len() - di + 1;
    let start = end.saturating_sub(n);
    &elements[start..end]
}

/// 解析数字或字符串为 usize
pub fn get_usize_param(params: &ParamView, key: &str, default: usize) -> usize {
    if let Some(val) = params.value(key) {
        if let Some(n) = val.as_u64() {
            return n as usize;
        }
        if let Some(s) = val.as_str() {
            if let Ok(n) = s.parse::<usize>() {
                return n;
            }
        }
    }
    default
}

/// 将 `bar.id -> 索引` 映射成哈希表，便于在信号函数中做 O(1) 定位。
pub fn bar_index_map(czsc: &CZSC) -> HashMap<i32, usize> {
    czsc.bars_raw
        .iter()
        .enumerate()
        .map(|(i, b)| (b.id, i))
        .collect()
}

/// 构建 `bar.id -> 最新 RawBar` 映射，用于在信号层对齐 Python 的“按当前 bars_raw 读取”语义。
pub fn raw_bar_map(czsc: &CZSC) -> HashMap<i32, RawBar> {
    czsc.bars_raw.iter().map(|b| (b.id, b.clone())).collect()
}

/// 用最新 `bars_raw` 覆盖同 id 的历史快照；未命中的 id 保留原值。
pub fn remap_raw_bars(raw_bars: &[RawBar], latest_by_id: &HashMap<i32, RawBar>) -> Vec<RawBar> {
    raw_bars
        .iter()
        .map(|rb| {
            latest_by_id
                .get(&rb.id)
                .cloned()
                .unwrap_or_else(|| rb.clone())
        })
        .collect()
}

/// 从 `RawBar` 序列中提取对应索引的数值序列（会过滤非有限值）。
pub fn values_from_raw_bars(
    raw_bars: &[RawBar],
    id_to_idx: &HashMap<i32, usize>,
    values: &[f64],
) -> Vec<f64> {
    raw_bars
        .iter()
        .filter_map(|rb| id_to_idx.get(&rb.id).map(|i| values[*i]))
        .filter(|x| x.is_finite())
        .collect()
}

/// 从 `FX` 的嵌套 K 线中提取对应索引的数值序列（会过滤非有限值）。
pub fn values_from_fx(
    fx: &czsc_core::objects::fx::FX,
    id_to_idx: &HashMap<i32, usize>,
    values: &[f64],
) -> Vec<f64> {
    let raw_bars: Vec<RawBar> = fx
        .elements
        .iter()
        .flat_map(|nb| nb.elements.iter().cloned())
        .collect();
    values_from_raw_bars(&raw_bars, id_to_idx, values)
}

/// 解析分钟级别周期，如 `60分钟` -> `60`
pub fn parse_minute_freq(freq: &str) -> Option<i64> {
    if !freq.ends_with("分钟") {
        return None;
    }
    let n = freq.trim_end_matches("分钟").parse::<i64>().ok()?;
    if n > 0 {
        Some(n)
    } else {
        None
    }
}

/// 计算分钟周期对应的结束时间（与 Python freq_end_time 口径一致）
pub fn minute_freq_end_time(
    dt: chrono::DateTime<chrono::Utc>,
    freq: &str,
) -> Option<chrono::DateTime<chrono::Utc>> {
    let Some(m) = parse_minute_freq(freq) else {
        return Some(dt);
    };

    // 与 Python `freq_end_time(..., market="A股")` 对齐：
    // A 股分钟数据在 09:30/13:30 等边界点不是简单的整除向上取整。
    let hm = dt.format("%H:%M").to_string();
    if freq == "30分钟" {
        let hm_edt = match hm.as_str() {
            "09:30" | "10:00" => Some("10:00"),
            "10:30" => Some("10:30"),
            "11:00" => Some("11:00"),
            "11:30" => Some("11:30"),
            "13:30" => Some("13:30"),
            "14:00" => Some("14:00"),
            "14:30" => Some("14:30"),
            "15:00" => Some("15:00"),
            _ => None,
        };
        if let Some(edt) = hm_edt {
            let mut it = edt.split(':');
            let h = it.next().and_then(|x| x.parse::<u32>().ok())?;
            let m = it.next().and_then(|x| x.parse::<u32>().ok())?;
            return dt.date_naive().and_hms_opt(h, m, 0).map(|x| x.and_utc());
        }
    }

    if freq == "60分钟" {
        let hm_edt = match hm.as_str() {
            "09:30" | "10:00" | "10:30" => Some("10:30"),
            "11:00" | "11:30" => Some("11:30"),
            "13:30" | "14:00" => Some("14:00"),
            "14:30" | "15:00" => Some("15:00"),
            _ => None,
        };
        if let Some(edt) = hm_edt {
            let mut it = edt.split(':');
            let h = it.next().and_then(|x| x.parse::<u32>().ok())?;
            let m = it.next().and_then(|x| x.parse::<u32>().ok())?;
            return dt.date_naive().and_hms_opt(h, m, 0).map(|x| x.and_utc());
        }
    }

    let hm = i64::from(dt.hour()) * 60 + i64::from(dt.minute());
    let mut end_hm = if hm % m == 0 { hm } else { (hm / m + 1) * m };
    let mut day = dt.date_naive();
    if end_hm >= 24 * 60 {
        end_hm -= 24 * 60;
        if let Some(next_day) = day.checked_add_signed(Duration::days(1)) {
            day = next_day;
        }
    }
    let h = (end_hm / 60) as u32;
    let mm = (end_hm % 60) as u32;
    day.and_hms_opt(h, mm, 0).map(|x| x.and_utc())
}

/// 获取最新价，优先 trader 直接提供，否则回退到指定级别最后一根K线收盘
pub fn latest_price(cat: &dyn TraderState, freq1: &str) -> Option<f64> {
    cat.latest_price().or_else(|| {
        cat.get_czsc(freq1)
            .and_then(|c| c.bars_raw.last().map(|b| b.close))
    })
}

/// 获取最后一次开仓操作（过滤平仓）
pub fn last_open_operate<'a>(
    cat: &'a dyn TraderState,
    pos_name: &str,
) -> Option<&'a OperateRecord> {
    let pos = cat.get_position(pos_name)?;
    let op = pos.operates.last()?;
    if matches!(op.op, Operate::SE | Operate::LE) {
        None
    } else {
        Some(op)
    }
}

/// 解析信号字符串，失败时返回空向量
pub fn signal_from_str(sig_str: &str) -> Vec<Signal> {
    Signal::from_str(sig_str).map_or_else(|_| vec![], |s| vec![s])
}

/// 底层统一构造器：生成标准 7 段信号并严格校验格式。
pub fn make_signal7(
    k1: &str,
    k2: &str,
    k3: &str,
    v1: &str,
    v2: &str,
    v3: &str,
    score: i32,
) -> Vec<Signal> {
    let sig_str = format!("{}_{}_{}_{}_{}_{}_{}", k1, k2, k3, v1, v2, v3, score);
    match Signal::from_str(&sig_str) {
        Ok(sig) => vec![sig],
        Err(err) => panic!("invalid signal generated: {sig_str}; error: {err}"),
    }
}

/// 构造标准 7 段信号（含 v1/v2，v3=`任意`）
pub fn make_signal(k1: &str, k2: &str, k3: &str, v1: &str, v2: &str) -> Vec<Signal> {
    make_signal7(k1, k2, k3, v1, v2, "任意", 0)
}

/// 构造标准 7 段信号（仅 v1，v2/v3 默认 `任意`）
pub fn make_signal_v1(k1: &str, k2: &str, k3: &str, v1: &str) -> Vec<Signal> {
    make_signal7(k1, k2, k3, v1, "任意", "任意", 0)
}

/// K线级：仅设置 v1，v2/v3 固定 `任意`
pub fn make_kline_signal_v1(k1: &str, k2: &str, k3: &str, v1: &str) -> Vec<Signal> {
    make_signal7(k1, k2, k3, v1, "任意", "任意", 0)
}

/// K线级：设置 v1/v2，v3 固定 `任意`
pub fn make_kline_signal_v2(k1: &str, k2: &str, k3: &str, v1: &str, v2: &str) -> Vec<Signal> {
    make_signal7(k1, k2, k3, v1, v2, "任意", 0)
}

/// K线级：设置 v1/v2/v3，score 固定 `0`
pub fn make_kline_signal_v3(
    k1: &str,
    k2: &str,
    k3: &str,
    v1: &str,
    v2: &str,
    v3: &str,
) -> Vec<Signal> {
    make_signal7(k1, k2, k3, v1, v2, v3, 0)
}

/// 周内中文标签（周一到周日）
pub fn weekday_cn(dt: chrono::DateTime<chrono::Utc>) -> &'static str {
    match dt.weekday().num_days_from_monday() {
        0 => "周一",
        1 => "周二",
        2 => "周三",
        3 => "周四",
        4 => "周五",
        5 => "周六",
        _ => "周日",
    }
}

/// 最近 `window` 根中的日内时间去重排序后，返回最后一根所在分段（1-based）
pub fn intraday_time_segment(bars: &[RawBar], window: usize) -> Option<usize> {
    if bars.len() < window || window == 0 {
        return None;
    }
    let sub = &bars[bars.len() - window..];
    let mut spans: Vec<String> = sub
        .iter()
        .map(|x| x.dt.format("%H:%M").to_string())
        .collect();
    spans.sort();
    spans.dedup();
    let cur = bars.last()?.dt.format("%H:%M").to_string();
    spans.iter().position(|x| x == &cur).map(|i| i + 1)
}

/// 快慢线交叉信息（基础版）
pub fn fast_slow_cross(fast: &[f64], slow: &[f64]) -> Vec<HashMap<&'static str, f64>> {
    let mut res = Vec::new();
    let len = fast.len();
    if len < 2 {
        return res;
    }

    let mut last_cross_idx = 0;
    for i in 2..len {
        let f0 = fast[i - 1];
        let s0 = slow[i - 1];
        let f1 = fast[i];
        let s1 = slow[i];

        if f0 <= s0 && f1 > s1 {
            let mut cross = HashMap::new();
            cross.insert("类型", 1.0);
            cross.insert("快线", f1);
            cross.insert("慢线", s1);
            cross.insert("距离", (i - last_cross_idx) as f64);
            res.push(cross);
            last_cross_idx = i;
        } else if f0 >= s0 && f1 < s1 {
            let mut cross = HashMap::new();
            cross.insert("类型", -1.0);
            cross.insert("快线", f1);
            cross.insert("慢线", s1);
            cross.insert("距离", (i - last_cross_idx) as f64);
            res.push(cross);
            last_cross_idx = i;
        }
    }
    res
}

#[derive(Clone, Debug)]
pub struct CrossInfoExt {
    pub kind: i32,
    pub slow: f64,
    pub distance: usize,
    pub to_now: usize,
    pub area: f64,
}

/// 快慢线交叉信息（扩展版）
pub fn fast_slow_cross_ext(fast: &[f64], slow: &[f64]) -> Vec<CrossInfoExt> {
    let len = fast.len().min(slow.len());
    if len < 3 {
        return Vec::new();
    }

    let delta: Vec<f64> = (0..len).map(|i| fast[i] - slow[i]).collect();
    let mut cross = Vec::new();
    let mut last_i: isize = -1;
    let mut last_v = 0.0;

    for i in 0..len {
        let v = delta[i];
        last_i += 1;
        last_v += v.abs();
        let kind = if i >= 2 && delta[i - 1] <= 0.0 && delta[i] > 0.0 {
            1
        } else if i >= 2 && delta[i - 1] >= 0.0 && delta[i] < 0.0 {
            -1
        } else {
            0
        };
        if kind == 0 {
            continue;
        }
        cross.push(CrossInfoExt {
            kind,
            slow: slow[i],
            distance: last_i as usize,
            to_now: len - i,
            area: (last_v * 10000.0).round() / 10000.0,
        });
        last_i = 0;
        last_v = 0.0;
    }
    cross
}

/// 计算两序列最近一次穿越零轴以来的长度
pub fn cross_zero_axis(n1: &[f64], n2: &[f64]) -> usize {
    assert_eq!(n1.len(), n2.len(), "输入两个数列长度不等");
    if n1.is_empty() {
        return 0;
    }
    let mut num1 = 0usize;
    let mut num2 = 0usize;

    let mut n1_rev = n1.to_vec();
    n1_rev.reverse();
    let a = n1_rev[0];
    if n1_rev.iter().any(|x| a * *x < 0.0) {
        let x: Vec<bool> = n1_rev.iter().map(|v| a * *v < 0.0).collect();
        let mut found = false;
        for i in 0..x.len().saturating_sub(1) {
            if x[i] != x[i + 1] {
                num1 = i + 2;
                found = true;
                break;
            }
        }
        if !found {
            num1 = 2;
        }
    }

    let mut n2_rev = n2.to_vec();
    n2_rev.reverse();
    let b = n2_rev[0];
    if n2_rev.iter().any(|x| b * *x < 0.0) {
        let x: Vec<bool> = n2_rev.iter().map(|v| b * *v < 0.0).collect();
        let mut found = false;
        for i in 0..x.len().saturating_sub(1) {
            if x[i] != x[i + 1] {
                num2 = i + 2;
                found = true;
                break;
            }
        }
        if !found {
            num2 = 2;
        }
    }
    num1.max(num2)
}

/// 统计 x1 从上向下穿越 x2 的次数
pub fn down_cross_count(x1: &[f64], x2: &[f64]) -> usize {
    let mut num = 0usize;
    if x1.len() != x2.len() || x1.len() < 2 {
        return num;
    }
    for i in 0..x1.len() - 1 {
        let b1 = x1[i] < x2[i];
        let b2 = x1[i + 1] < x2[i + 1];
        if b2 && b1 != b2 {
            num += 1;
        }
    }
    num
}

/// 计算过滤后的金叉/死叉次数
pub fn cal_cross_num(cross: &[HashMap<&'static str, f64>], distance: usize) -> (usize, usize) {
    if cross.is_empty() {
        return (0, 0);
    }

    let mut cross_work = cross.to_vec();
    let mut filtered: Vec<HashMap<&'static str, f64>> = Vec::new();

    if cross_work.len() == 1 {
        filtered = cross_work;
    } else if cross_work.len() == 2 {
        let dist = cross_work
            .last()
            .and_then(|x| x.get("距离"))
            .copied()
            .unwrap_or(0.0);
        filtered = if dist < distance as f64 {
            Vec::new()
        } else {
            cross_work
        };
    } else {
        let last_dist = cross_work
            .last()
            .and_then(|x| x.get("距离"))
            .copied()
            .unwrap_or(0.0);
        let re_cross: Vec<HashMap<&'static str, f64>> = if last_dist < distance as f64 {
            let last_cross = cross_work.pop().unwrap();
            let _ = cross_work.pop();
            let mut tmp: Vec<HashMap<&'static str, f64>> = cross_work
                .into_iter()
                .filter(|x| x.get("距离").copied().unwrap_or(0.0) >= distance as f64)
                .collect();
            tmp.push(last_cross);
            tmp
        } else {
            cross_work
                .into_iter()
                .filter(|x| x.get("距离").copied().unwrap_or(0.0) >= distance as f64)
                .collect()
        };

        for i in 0..re_cross.len() {
            if !filtered.is_empty() && i >= 1 {
                let t_i = re_cross[i].get("类型").copied().unwrap_or(0.0);
                let t_prev = re_cross[i - 1].get("类型").copied().unwrap_or(0.0);
                if (t_i - t_prev).abs() <= f64::EPSILON {
                    filtered.pop();
                    filtered.push(re_cross[i].clone());
                    continue;
                }
            }
            filtered.push(re_cross[i].clone());
        }
    }

    let jc = filtered
        .iter()
        .filter(|x| x.get("类型").copied().unwrap_or(0.0) > 0.0)
        .count();
    let sc = filtered
        .iter()
        .filter(|x| x.get("类型").copied().unwrap_or(0.0) < 0.0)
        .count();
    (jc, sc)
}

/// 线性回归斜率
pub fn linear_slope(y: &[f64]) -> f64 {
    let n = y.len();
    if n < 2 {
        return 0.0;
    }
    let n_f = n as f64;
    let sum_x = (n_f - 1.0) * n_f / 2.0;
    let sum_xx = (n_f - 1.0) * n_f * (2.0 * n_f - 1.0) / 6.0;
    let sum_y: f64 = y.iter().sum();
    let sum_xy: f64 = y.iter().enumerate().map(|(i, v)| i as f64 * *v).sum();
    let denom = n_f * sum_xx - sum_x * sum_x;
    if denom.abs() <= f64::EPSILON {
        return 0.0;
    }
    (n_f * sum_xy - sum_x * sum_y) / denom
}

/// 统计序列末尾连续相同元素个数
pub fn count_last_same<T: PartialEq>(seq: &[T]) -> usize {
    if seq.is_empty() {
        return 0;
    }
    let last = &seq[seq.len() - 1];
    let mut c = 0usize;
    for x in seq.iter().rev() {
        if x == last {
            c += 1;
        } else {
            break;
        }
    }
    c
}

/// 等宽分箱：返回最后一个值所在分箱
pub fn cut_last_bin_label(values: &[f64], n: usize) -> Option<usize> {
    if n == 0 || values.is_empty() {
        return None;
    }
    let finite: Vec<f64> = values.iter().copied().filter(|x| x.is_finite()).collect();
    if finite.is_empty() {
        return None;
    }
    let min_v = finite.iter().copied().fold(f64::INFINITY, f64::min);
    let max_v = finite.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    if !min_v.is_finite() || !max_v.is_finite() {
        return None;
    }
    if (max_v - min_v).abs() <= f64::EPSILON {
        return Some(n.div_ceil(2));
    }
    let last = *values.last()?;
    if !last.is_finite() {
        return None;
    }
    let width = (max_v - min_v) / n as f64;
    if width <= 0.0 || !width.is_finite() {
        return Some(1);
    }
    let mut idx = ((last - min_v) / width).floor() as isize + 1;
    if idx < 1 {
        idx = 1;
    }
    if idx > n as isize {
        idx = n as isize;
    }
    Some(idx as usize)
}

/// 标准差（基于绝对值序列）
pub fn std_abs_series(values: &[f64]) -> f64 {
    if values.is_empty() || values.iter().any(|x| !x.is_finite()) {
        return f64::NAN;
    }
    let abs_vals: Vec<f64> = values.iter().map(|x| x.abs()).collect();
    let mean = abs_vals.iter().sum::<f64>() / abs_vals.len() as f64;
    let var = abs_vals.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / abs_vals.len() as f64;
    var.sqrt()
}

/// 分位数分箱：返回最后一个值所在分箱
pub fn qcut_last_label(values: &[f64], q: usize) -> Option<usize> {
    if q == 0 || values.is_empty() {
        return None;
    }
    let mut sorted: Vec<f64> = values.iter().copied().filter(|x| x.is_finite()).collect();
    if sorted.is_empty() {
        return None;
    }
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

    let x = *values.last()?;
    if !x.is_finite() {
        return None;
    }
    let bins = edges.len() - 1;
    if x < edges[0] || x > edges[bins] {
        return None;
    }
    for i in 0..bins {
        let left_ok = if i == 0 { x >= edges[i] } else { x > edges[i] };
        let right_ok = x <= edges[i + 1];
        if left_ok && right_ok {
            return Some(i);
        }
    }
    None
}

/// 对齐 `pandas.cut(values, bins=n, right=True)`，返回最后一个值的分箱标签（1..=n）
pub fn pd_cut_last_label(values: &[f64], n: usize) -> Option<usize> {
    if n == 0 || values.is_empty() {
        return None;
    }
    if values.iter().any(|x| !x.is_finite()) {
        return None;
    }
    let min_val = values.iter().copied().fold(f64::INFINITY, f64::min);
    let max_val = values.iter().copied().fold(f64::NEG_INFINITY, f64::max);
    if !min_val.is_finite() || !max_val.is_finite() {
        return None;
    }

    // 对齐 pandas.cut bins=int 行为：
    // - 常量序列：左右各扩展 0.1%（零值用固定 ±0.001）
    // - 非常量序列：只扩展左边界 0.1%
    let bins: Vec<f64> = if (max_val - min_val).abs() < f64::EPSILON {
        let (lo, hi) = if min_val != 0.0 {
            let delta = 0.001 * min_val.abs();
            (min_val - delta, max_val + delta)
        } else {
            (-0.001, 0.001)
        };
        (0..=n)
            .map(|i| lo + (hi - lo) * i as f64 / n as f64)
            .collect()
    } else {
        let mut bs: Vec<f64> = (0..=n)
            .map(|i| min_val + (max_val - min_val) * i as f64 / n as f64)
            .collect();
        bs[0] -= (max_val - min_val) * 0.001;
        bs
    };

    let x = *values.last()?;
    // lower_bound: 第一个 >= x 的索引，等价 pandas/numpy searchsorted(side='left')
    let mut l = 0usize;
    let mut r = bins.len();
    while l < r {
        let mid = (l + r) / 2;
        if bins[mid] < x {
            l = mid + 1;
        } else {
            r = mid;
        }
    }
    let idx = l;
    let q = if idx == 0 {
        1
    } else if idx >= bins.len() {
        n
    } else {
        idx
    };
    Some(q)
}

#[cfg(test)]
#[allow(clippy::items_after_test_module)]
mod tests {
    use super::{
        cut_last_bin_label, get_str_param, get_sub_elements, get_usize_param,
        intraday_time_segment, pd_cut_last_label, weekday_cn,
    };
    use crate::params::ParamView;
    use czsc_core::objects::bar::RawBar;
    use serde_json::Value;
    use std::collections::HashMap;

    #[test]
    fn test_get_sub_elements_di1() {
        let x = vec![1, 2, 3, 4, 5, 6, 7, 8, 9];
        assert_eq!(get_sub_elements(&x, 1, 3), &[7, 8, 9]);
    }

    #[test]
    fn test_get_sub_elements_di2() {
        let x = vec![1, 2, 3, 4, 5, 6, 7, 8, 9];
        assert_eq!(get_sub_elements(&x, 2, 3), &[6, 7, 8]);
    }

    #[test]
    fn test_get_sub_elements_short_and_out_of_range() {
        let x = vec![1, 2, 3];
        assert_eq!(get_sub_elements(&x, 1, 10), &[1, 2, 3]);
        assert_eq!(get_sub_elements(&x, 4, 2), &[] as &[i32]);
    }

    #[test]
    fn test_get_sub_elements_n_zero_aligns_python_slice() {
        let x = vec![1, 2, 3, 4];
        assert_eq!(get_sub_elements(&x, 1, 0), &[1, 2, 3, 4]);
        assert_eq!(get_sub_elements(&x, 2, 0), &[] as &[i32]);
    }

    #[test]
    fn test_param_helpers_accept_param_view() {
        let mut m = HashMap::new();
        m.insert("di".to_string(), Value::String("3".to_string()));
        m.insert("ma_type".to_string(), Value::String("EMA".to_string()));
        let p = ParamView::new(&m);
        assert_eq!(get_usize_param(&p, "di", 1), 3);
        assert_eq!(get_str_param(&p, "ma_type", "SMA"), "EMA");
        assert_eq!(get_usize_param(&p, "n", 5), 5);
    }

    #[test]
    fn test_cut_last_bin_label_constant_series_center_bin() {
        let v = vec![-13.858860437903786];
        assert_eq!(cut_last_bin_label(&v, 5), Some(3));
        assert_eq!(cut_last_bin_label(&v, 4), Some(2));
        assert_eq!(cut_last_bin_label(&v, 3), Some(2));
    }

    #[test]
    fn test_cut_last_bin_label_non_constant_series() {
        let v = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        assert_eq!(cut_last_bin_label(&v, 5), Some(5));
    }

    #[test]
    fn test_pd_cut_last_label_constant_center_bin() {
        let v1 = vec![5.0; 100];
        let v2 = vec![0.0; 100];
        assert_eq!(pd_cut_last_label(&v1, 5), Some(3));
        assert_eq!(pd_cut_last_label(&v2, 5), Some(3));
    }

    #[test]
    fn test_pd_cut_last_label_non_constant_boundary_bins() {
        let mut low = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        low[4] = 1.0;
        let high = vec![1.0, 2.0, 3.0, 4.0, 5.0];
        assert_eq!(pd_cut_last_label(&low, 5), Some(1));
        assert_eq!(pd_cut_last_label(&high, 5), Some(5));
    }

    #[test]
    fn test_pd_cut_last_label_rejects_non_finite() {
        let v = vec![1.0, 2.0, f64::NAN];
        assert_eq!(pd_cut_last_label(&v, 5), None);
    }

    #[test]
    fn test_intraday_time_segment_basic() {
        use chrono::TimeZone;
        let bars = vec![
            RawBar {
                symbol: "T".into(),
                id: 1,
                dt: chrono::Utc.with_ymd_and_hms(2024, 1, 1, 9, 30, 0).unwrap(),
                freq: czsc_core::objects::freq::Freq::F60,
                open: 1.0,
                close: 1.0,
                high: 1.0,
                low: 1.0,
                vol: 1.0,
                amount: 1.0,
                cache: Default::default(),
            },
            RawBar {
                symbol: "T".into(),
                id: 2,
                dt: chrono::Utc.with_ymd_and_hms(2024, 1, 2, 10, 30, 0).unwrap(),
                freq: czsc_core::objects::freq::Freq::F60,
                open: 1.0,
                close: 1.0,
                high: 1.0,
                low: 1.0,
                vol: 1.0,
                amount: 1.0,
                cache: Default::default(),
            },
            RawBar {
                symbol: "T".into(),
                id: 3,
                dt: chrono::Utc.with_ymd_and_hms(2024, 1, 3, 10, 30, 0).unwrap(),
                freq: czsc_core::objects::freq::Freq::F60,
                open: 1.0,
                close: 1.0,
                high: 1.0,
                low: 1.0,
                vol: 1.0,
                amount: 1.0,
                cache: Default::default(),
            },
        ];
        assert_eq!(intraday_time_segment(&bars, 3), Some(2));
        assert_eq!(intraday_time_segment(&bars, 4), None);
    }

    #[test]
    fn test_weekday_cn_mapping() {
        use chrono::TimeZone;
        let dt = chrono::Utc.with_ymd_and_hms(2024, 1, 1, 9, 30, 0).unwrap(); // 周一
        assert_eq!(weekday_cn(dt), "周一");
    }
}

/// 解析字符串参数
pub fn get_str_param<'a>(params: &'a ParamView, key: &str, default: &'a str) -> &'a str {
    if let Some(val) = params.value(key) {
        if let Some(s) = val.as_str() {
            return s;
        }
    }
    default
}
