//! 信号函数性能基准（spec §6 P2）。
//!
//! 验收目标：
//! - 单根 K 线分派全部 K 线信号（30+ 信号），P50 ≤ 50 µs（per-signal 单次调用）
//! - 批量 1 万根 K 线下分派全部 K 线信号一次，总耗时 ≤ 80 ms
//!
//! 这里把"全部 K 线信号在同一 CZSC 实例上各调用一次"的总耗时记录下来；
//! 可由总耗时除以 SIGNAL_REGISTRY 大小得到 per-signal P50 估计值。
//!
//! 触发：cargo bench -p czsc-signals

use std::collections::HashMap;
use std::hint::black_box;
use std::sync::Arc;

use chrono::{TimeZone, Utc};
use criterion::{Criterion, criterion_group, criterion_main};
use czsc_core::analyze::CZSC;
use czsc_core::objects::bar::{RawBar, RawBarBuilder};
use czsc_core::objects::freq::Freq;
use czsc_signals::registry::SIGNAL_REGISTRY;
use czsc_signals::types::TaCache;
use serde_json::Value;

/// 与 czsc-core/benches/czsc_analyze_bench.rs 同款 K 线生成器（独立 copy 避免
/// 跨 crate dev-dep 依赖；spec §4.2 测试隔离原则）。
fn generate_bars(count: usize) -> Vec<RawBar> {
    let symbol: Arc<str> = Arc::from("000001.SH");
    let base_ts = 1704067200i64;

    (0..count)
        .map(|i| {
            let slow = (i as f64 * 0.001).sin() * 30.0;
            let fast = (i as f64 * 0.07).sin() * 4.0;
            let drift = i as f64 * 0.0002;
            let close = 100.0 + slow + fast + drift;
            let open = close - fast * 0.5;
            let high = close.max(open) + 0.6;
            let low = close.min(open) - 0.6;
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

/// 在给定 CZSC 实例上把 ``SIGNAL_REGISTRY`` 中所有 kline 信号各调用一次，
/// 返回成功调用次数（用于 black_box 防止整体被优化掉）。
fn dispatch_all_signals(czsc: &CZSC) -> usize {
    let empty_params: HashMap<String, Value> = HashMap::new();
    let mut cache = TaCache::default();
    let mut count = 0usize;
    for (_name, meta) in SIGNAL_REGISTRY.iter() {
        let signals = (meta.func)(czsc, &empty_params, &mut cache);
        // black_box 让 LLVM 不能把 signals 作为死代码消除
        let _ = black_box(signals);
        count += 1;
    }
    count
}

fn bench_signals_dispatch(c: &mut Criterion) {
    // ① 单根代表 K 线下分派全部信号——把 100 根 bar 的 CZSC 视为典型回放截面
    let small_bars = generate_bars(100);
    let small_czsc = CZSC::new(small_bars, 50, 6);
    let signals_count = SIGNAL_REGISTRY.len();

    let mut group = c.benchmark_group("signals_dispatch");
    group.sample_size(20);

    group.bench_function(
        format!("dispatch_all({signals_count} signals, bars=100)"),
        |b| {
            b.iter(|| {
                let n = dispatch_all_signals(black_box(&small_czsc));
                black_box(n)
            });
        },
    );

    // ② 1 万根 K 线场景——目标整体 ≤ 80 ms
    let large_bars = generate_bars(10_000);
    let large_czsc = CZSC::new(large_bars, 50, 6);
    group.bench_function(
        format!("dispatch_all({signals_count} signals, bars=10000)"),
        |b| {
            b.iter(|| {
                let n = dispatch_all_signals(black_box(&large_czsc));
                black_box(n)
            });
        },
    );

    group.finish();
}

criterion_group!(
    name = benches;
    config = Criterion::default();
    targets = bench_signals_dispatch
);
criterion_main!(benches);
