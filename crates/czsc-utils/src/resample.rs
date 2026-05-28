//! 批量 K 线重采样：等价于历史 Python `czsc.resample_bars`。
//!
//! 实现复用 [`BarGenerator`] 的单桶滚动聚合逻辑，并通过
//! [`infer_market_from_bars`] 自动推断市场，避免调用方手动判定。
//!
//! 与历史 Python 版的行为对齐口径：
//! - 推断 base_freq：从 `bars[0].freq` 直接取，不再额外接受参数；
//! - 推断 market：分钟级走 [`infer_market_from_bars`]（等价于 Python 端
//!   `check_freq_and_market`），非分钟级返回 `Market::Default`；
//! - `drop_unfinished`：若最后一根 base bar 的 `dt` 严格小于最后一根 target bar
//!   的 `freq_edt`，认为该 target bar 尚未完成、丢弃；空输入直接返回空 `Vec`。
//!
//! 关键行为差异（与 BarGenerator 流式 API 区分）：
//!   - **batch 语义要求 fail-loud**：BarGenerator 在 `last.dt == bar.dt` 时会静默
//!     去重、对乱序输入会把 freq_edt 相等的 bar 合并到上一桶（语义模糊）。批量
//!     resample 不能容忍这些情况——上游若给到 duplicate dt 或乱序 dt，本函数
//!     直接返回 [`UtilsError`] 让调用方修上游，避免悄无声息地丢数据。
//!   - 同 symbol、同 freq：列表里出现混合 symbol 或混合 freq 会触发显式错误。
//!   - OHLCV 字段不接受 NaN：BarGenerator 的 `last.vol + bar.vol` 会让 NaN
//!     沿桶传染（与历史 pandas `sum(skipna=True)` 不一致），batch 模式直接拒绝。
//!
//! `drop_unfinished` 的已知限制：
//!   对非分钟 target（D/W/M/S/Y），[`freq_end_time`] 把桶 dt 归到日界 00:00:00，
//!   而 base bar 的 dt 是日内值，`lb < lt` 恒为假，所以 `drop_unfinished` 对
//!   非分钟 target 实际是 no-op。这与历史 Python 版（依赖 pandas freq_end_time
//!   返回市场收盘时间）的行为不一致；要改正需重设计 [`freq_end_time`] 对非分钟
//!   target 的返回口径，影响面外溢，暂作为已知限制留待单独 PR 处理。

use czsc_core::objects::{bar::RawBar, freq::Freq};

use crate::bar_generator::{BarGenerator, nan_ohlcv_field};
use crate::errors::UtilsError;
use crate::freq_data::infer_market_from_bars;

/// 将一组基础周期 K 线重采样为目标周期 K 线。
///
/// 详见模块级文档关于 base_freq / market 推断、`drop_unfinished` 语义、
/// 以及 batch 模式与流式 BarGenerator 的差异。
///
/// # Errors
/// - 输入 bars 中出现两个不同的 `symbol`（batch 模式不做 symbol 分组）；
/// - 输入 bars 中出现两个不同的 `freq`（不能混合频率）；
/// - 输入 bars 的 `dt` 不是严格单调递增（含重复 dt）；
/// - 任一 OHLCV 字段（open/close/high/low/vol/amount）含 NaN；
/// - 内部 `freq_end_time` 计算失败（非交易时间且无可用回退）。
pub fn resample_bars(
    bars: &[RawBar],
    target_freq: Freq,
    drop_unfinished: bool,
) -> Result<Vec<RawBar>, UtilsError> {
    if bars.is_empty() {
        return Ok(Vec::new());
    }

    validate_batch_invariants(bars)?;

    let base_freq = bars[0].freq;
    let market = infer_market_from_bars(bars, base_freq);

    // 上界：base 与 target 1:1 时输出与 bars 同长，再 +1 给未完成的尾桶留位。
    // BarGenerator 用 `VecDeque::with_capacity(max_count)` 预分配，不能传 usize::MAX。
    let max_count = bars.len().saturating_add(1);
    let bg = BarGenerator::new(base_freq, vec![target_freq], max_count, market)?;

    for bar in bars {
        bg.update_bar(bar)?;
    }

    let mut out: Vec<RawBar> = bg
        .freq_bars
        .get(&target_freq)
        .map(|lock| lock.read().iter().cloned().collect())
        .unwrap_or_default();

    if drop_unfinished {
        let last_base_dt = bars.last().map(|b| b.dt);
        let last_target_dt = out.last().map(|b| b.dt);
        if let (Some(lb), Some(lt)) = (last_base_dt, last_target_dt)
            && lb < lt
        {
            out.pop();
        }
    }

    Ok(out)
}

/// batch 模式必须的输入不变量：单 symbol、单 freq、dt 严格递增。
///
/// 故意做成一次 O(n) 扫描而不是分摊到 BarGenerator 里，原因是 BarGenerator 的
/// 流式 API 对重复 / 乱序有合法语义（前者去重、后者合并），把校验上提保证
/// batch 调用方拿到清晰的失败信号。
fn validate_batch_invariants(bars: &[RawBar]) -> Result<(), UtilsError> {
    debug_assert!(!bars.is_empty(), "caller must short-circuit empty input");

    let first_symbol = &bars[0].symbol;
    let first_freq = bars[0].freq;
    let mut prev_dt = bars[0].dt;

    // bars[0] 也要查 NaN（循环从 idx=1 开始不覆盖第 0 根）
    check_no_nan(&bars[0], 0)?;

    for (idx, bar) in bars.iter().enumerate().skip(1) {
        if bar.symbol != *first_symbol {
            return Err(UtilsError::Unexpected(anyhow::anyhow!(
                "resample_bars: bars 列表混合了多个 symbol（bars[0]={}, bars[{}]={}），\
                 batch 重采样不做 symbol 分组，请先按 symbol 拆分输入",
                first_symbol,
                idx,
                bar.symbol
            )));
        }
        if bar.freq != first_freq {
            return Err(UtilsError::Unexpected(anyhow::anyhow!(
                "resample_bars: bars 列表混合了多个 freq（bars[0]={}, bars[{}]={}），\
                 batch 重采样要求输入同频率",
                first_freq,
                idx,
                bar.freq
            )));
        }
        if bar.dt <= prev_dt {
            let reason = if bar.dt == prev_dt {
                "存在重复 dt"
            } else {
                "存在乱序 dt"
            };
            return Err(UtilsError::Unexpected(anyhow::anyhow!(
                "resample_bars: bars[{}].dt={} 与 bars[{}].dt={} {}（要求严格单调递增），\
                 请在调用前去重并按 dt 升序排列",
                idx,
                bar.dt,
                idx - 1,
                prev_dt,
                reason,
            )));
        }
        check_no_nan(bar, idx)?;
        prev_dt = bar.dt;
    }

    Ok(())
}

/// 在 batch 边界拒绝 NaN OHLCV，错误信息点名 idx + 字段，方便上游定位。
///
/// BarGenerator::update_bar 同样会拒绝 NaN（错误里没有 idx），这里提前一步
/// 是为了给 batch 调用方更明确的"bars[N]"上下文。两层 check 复用同一个
/// [`nan_ohlcv_field`]，杜绝定义漂移。
fn check_no_nan(bar: &RawBar, idx: usize) -> Result<(), UtilsError> {
    if let Some(field) = nan_ohlcv_field(bar) {
        return Err(UtilsError::Unexpected(anyhow::anyhow!(
            "resample_bars: bars[{}].{} = NaN（dt={}），\
             batch 模式拒绝 NaN OHLCV 输入以避免桶聚合静默污染——请在上游 \
             dropna 或填充后再调用",
            idx,
            field,
            bar.dt,
        )));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::{NaiveDateTime, TimeZone, Utc};
    use czsc_core::objects::bar::RawBarBuilder;

    /// 构造一个 A 股 1 分钟 09:31 起的连续 K 线序列，便于驱动测试用例。
    fn build_ashare_1min_bars(n: usize) -> Vec<RawBar> {
        let start = Utc.from_utc_datetime(
            &NaiveDateTime::parse_from_str("2024-12-12 09:31:00", "%Y-%m-%d %H:%M:%S").unwrap(),
        );

        (0..n)
            .map(|i| {
                let price = 100.0 + i as f64;
                RawBarBuilder::default()
                    .symbol("000001.XSHG")
                    .id(i as i32)
                    .dt(start + chrono::Duration::minutes(i as i64))
                    .freq(Freq::F1)
                    .open(price)
                    .close(price + 0.1)
                    .high(price + 0.5)
                    .low(price - 0.5)
                    .vol(1_000.0 * (i as f64 + 1.0))
                    .amount(10_000.0 * (i as f64 + 1.0))
                    .build()
                    .unwrap()
            })
            .collect()
    }

    fn dt_str(bar: &RawBar) -> String {
        bar.dt.format("%Y-%m-%d %H:%M:%S").to_string()
    }

    #[test]
    fn empty_input_returns_empty() {
        let out = resample_bars(&[], Freq::F5, true).unwrap();
        assert!(out.is_empty());
    }

    /// 09:31 ~ 09:35 共 5 根 1 分钟 → 09:35 一根 5 分钟。
    /// 末根落在桶边界上，drop_unfinished=true 也不应丢。
    #[test]
    fn one_minute_to_five_minute_complete_bucket() {
        let bars = build_ashare_1min_bars(5);
        let out = resample_bars(&bars, Freq::F5, true).unwrap();
        assert_eq!(out.len(), 1, "5 根 1min 恰好凑成 1 根 5min");
        assert_eq!(dt_str(&out[0]), "2024-12-12 09:35:00");
        assert_eq!(out[0].freq, Freq::F5);
        assert_eq!(out[0].open, bars[0].open);
        assert_eq!(out[0].close, bars[4].close);
        assert_eq!(out[0].high, bars[4].high);
        assert_eq!(out[0].low, bars[0].low);
        let vol_sum: f64 = bars.iter().map(|b| b.vol).sum();
        let amt_sum: f64 = bars.iter().map(|b| b.amount).sum();
        assert_eq!(out[0].vol, vol_sum);
        assert_eq!(out[0].amount, amt_sum);
    }

    /// 09:31 ~ 09:37 共 7 根 1 分钟 → 5min 桶 [09:35, 09:40)，
    /// 09:35 满桶 + 09:40 半桶。drop_unfinished=true 应丢掉 09:40 那根。
    #[test]
    fn drop_unfinished_drops_partial_tail() {
        let bars = build_ashare_1min_bars(7);

        let kept = resample_bars(&bars, Freq::F5, true).unwrap();
        assert_eq!(kept.len(), 1);
        assert_eq!(dt_str(&kept[0]), "2024-12-12 09:35:00");

        let all = resample_bars(&bars, Freq::F5, false).unwrap();
        assert_eq!(all.len(), 2);
        assert_eq!(dt_str(&all[0]), "2024-12-12 09:35:00");
        assert_eq!(dt_str(&all[1]), "2024-12-12 09:40:00");
        // 未完成桶只聚合了 09:36、09:37 两根：OHLCV 全字段覆盖。
        assert_eq!(all[1].open, bars[5].open);
        assert_eq!(all[1].close, bars[6].close);
        assert_eq!(all[1].high, bars[5].high.max(bars[6].high));
        assert_eq!(all[1].low, bars[5].low.min(bars[6].low));
        assert_eq!(all[1].vol, bars[5].vol + bars[6].vol);
        assert_eq!(all[1].amount, bars[5].amount + bars[6].amount);
    }

    /// base==target 时 resample 应当返回与输入数量一致的 bar，
    /// 且 dt 全部对齐到 freq_end_time（对分钟级 base 等价于原 dt）。
    #[test]
    fn base_equals_target_is_identity_in_count() {
        let bars = build_ashare_1min_bars(3);
        let out = resample_bars(&bars, Freq::F1, true).unwrap();
        assert_eq!(out.len(), 3);
        for (a, b) in bars.iter().zip(out.iter()) {
            assert_eq!(a.dt, b.dt);
            assert_eq!(a.open, b.open);
            assert_eq!(a.close, b.close);
            assert_eq!(a.high, b.high);
            assert_eq!(a.low, b.low);
            assert_eq!(a.vol, b.vol);
        }
    }

    /// 1 分钟 → 日线。两根 1 分钟 bar 跨越 09:31 和 09:32，
    /// 都属于同一交易日，应聚合成 1 根日线，dt 归到日界。
    ///
    /// 注意：drop_unfinished 对非分钟 target 是 no-op（见模块级文档），
    /// 所以即便桶严格意义上未完成，这里也会保留。
    #[test]
    fn one_minute_to_daily_keeps_partial_known_limitation() {
        let bars = build_ashare_1min_bars(2);
        let out = resample_bars(&bars, Freq::D, true).unwrap();
        assert_eq!(out.len(), 1);
        assert_eq!(out[0].freq, Freq::D);
        assert_eq!(dt_str(&out[0]), "2024-12-12 00:00:00");
        assert_eq!(out[0].open, bars[0].open);
        assert_eq!(out[0].close, bars[1].close);
    }

    /// 输入混合 symbol → 显式 Err，不再静默串行聚合。
    #[test]
    fn mixed_symbol_returns_err() {
        let mut bars = build_ashare_1min_bars(3);
        bars[1].symbol = "OTHER.XSHG".into();
        let err = resample_bars(&bars, Freq::F5, true).unwrap_err();
        assert!(
            err.to_string().contains("symbol"),
            "错误信息应当点名 symbol 不一致：{err}"
        );
    }

    /// 输入混合 freq → 显式 Err。
    #[test]
    fn mixed_freq_returns_err() {
        let mut bars = build_ashare_1min_bars(3);
        bars[1].freq = Freq::F5;
        let err = resample_bars(&bars, Freq::F5, true).unwrap_err();
        assert!(
            err.to_string().contains("freq"),
            "错误信息应当点名 freq 不一致：{err}"
        );
    }

    /// 重复 dt → 显式 Err（BarGenerator 流式语义会静默去重，
    /// 但 batch 必须 fail-loud）。
    #[test]
    fn duplicate_dt_returns_err() {
        let mut bars = build_ashare_1min_bars(3);
        bars[2].dt = bars[1].dt;
        let err = resample_bars(&bars, Freq::F5, true).unwrap_err();
        assert!(
            err.to_string().contains("重复"),
            "错误信息应当点名重复 dt：{err}"
        );
    }

    /// 乱序 dt → 显式 Err。
    #[test]
    fn out_of_order_dt_returns_err() {
        let mut bars = build_ashare_1min_bars(3);
        bars.swap(1, 2);
        let err = resample_bars(&bars, Freq::F5, true).unwrap_err();
        assert!(
            err.to_string().contains("乱序"),
            "错误信息应当点名乱序：{err}"
        );
    }

    /// 任一 OHLCV 字段为 NaN → 显式 Err，避免 BarGenerator `last + bar` 沿桶传染。
    #[test]
    fn nan_ohlcv_returns_err() {
        for field in ["open", "close", "high", "low", "vol", "amount"] {
            let mut bars = build_ashare_1min_bars(3);
            match field {
                "open" => bars[1].open = f64::NAN,
                "close" => bars[1].close = f64::NAN,
                "high" => bars[1].high = f64::NAN,
                "low" => bars[1].low = f64::NAN,
                "vol" => bars[1].vol = f64::NAN,
                "amount" => bars[1].amount = f64::NAN,
                _ => unreachable!(),
            }
            let err = resample_bars(&bars, Freq::F5, true).unwrap_err();
            let msg = err.to_string();
            assert!(
                msg.contains(field) && msg.contains("NaN"),
                "字段 {field} 的 NaN 错误信息应当点名字段与 NaN：{err}"
            );
        }
    }

    /// bars[0] 本身就含 NaN 也要 fail-loud（之前的循环从 idx=1 起，需特别覆盖）。
    #[test]
    fn nan_at_first_bar_returns_err() {
        let mut bars = build_ashare_1min_bars(3);
        bars[0].vol = f64::NAN;
        let err = resample_bars(&bars, Freq::F5, true).unwrap_err();
        assert!(
            err.to_string().contains("bars[0]"),
            "错误信息应当点名 bars[0]：{err}"
        );
    }
}
