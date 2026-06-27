//! CZSC 核心分析性能基准（spec §6 P1）。
//!
//! 验收目标：10 万根 K 线做完整 CZSC 分析（分型 / 笔 / 中枢识别）≤ 200 ms。
//!
//! 触发：
//!   cargo bench -p czsc-core
//!
//! 在 M2 Mac、release 构建（lto=true / opt-level=3 / codegen-units=1）下，
//! criterion 默认 100 个样本输出 mean / median / std-dev，把 mean 与 200 ms
//! 比对即可判定 P1 是否达标。

use std::hint::black_box;
use std::sync::Arc;

use chrono::{TimeZone, Utc};
use criterion::{BatchSize, Criterion, criterion_group, criterion_main};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::{RawBar, RawBarBuilder};
use czsc_core::objects::freq::Freq;

/// 生成 `count` 根模拟 30 分钟 K 线，价格用正弦+游走，振幅与噪声足以触发
/// 分型与笔的形成（不会出现一直单调推高/降低导致缠论分析路径退化）。
fn generate_bars(count: usize) -> Vec<RawBar> {
    let symbol: Arc<str> = Arc::from("000001.SH");
    let base_ts = 1704067200i64; // 2024-01-01 00:00 UTC

    (0..count)
        .map(|i| {
            // 基础价格围绕 100，慢周期正弦 + 快周期高频抖动 + 渐进漂移
            let slow = (i as f64 * 0.001).sin() * 30.0;
            let fast = (i as f64 * 0.07).sin() * 4.0;
            let drift = i as f64 * 0.0002;
            let close = 100.0 + slow + fast + drift;
            let open = close - fast * 0.5;
            let high = close.max(open) + 0.6;
            let low = close.min(open) - 0.6;
            // 30 分钟一根：每根递增 1800 秒
            let dt = Utc.timestamp_opt(base_ts + i as i64 * 1800, 0).unwrap();

            RawBarBuilder::default()
                .symbol(symbol.clone())
                .id(i as i32)
                .dt(dt)
                .freq(Freq::F30)
                .open(open)
                .close(close)
                .high(high)
                .low(low)
                .vol(1_000_000.0)
                .amount(close * 1_000_000.0)
                .build()
                .expect("RawBar 构造失败")
        })
        .collect()
}

fn bench_czsc_analyze(c: &mut Criterion) {
    // spec §6 P1 目标：10 万根 K 线 ≤ 200 ms
    const N: usize = 100_000;
    let bars = generate_bars(N);

    let mut group = c.benchmark_group("czsc_analyze");
    group.sample_size(20); // 大样本下 20 已经足够稳定

    group.bench_function(format!("CZSC::new(bars={N}, max_bi_num=50)"), |b| {
        b.iter_batched(
            || bars.clone(),
            |input| {
                let c = CZSC::new(black_box(input), 50, 6);
                black_box(c)
            },
            BatchSize::LargeInput,
        );
    });

    group.finish();
}

criterion_group!(
    name = benches;
    config = Criterion::default();
    targets = bench_czsc_analyze
);
criterion_main!(benches);
