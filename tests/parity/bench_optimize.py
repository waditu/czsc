"""性能基准测试脚本：对比 ``rs_czsc`` 与迁移后的 ``czsc`` 在
``OpensOptimize`` / ``ExitsOptimize`` 工作流上的耗时表现。

使用场景与定位：
    * 我们已经在 ``compare_optimize_full.py`` 中证明了两套实现的输出
      在比特层面完全一致，因此本脚本不再做正确性校验，而是专注于
      墙钟耗时（wall time）的对比。
    * 本脚本会对每种工作流（开仓优化 / 出场优化）执行 N 次试验，
      每次试验都使用一个全新的临时目录，避免缓存干扰。
    * 输出包含均值±标准差以及 czsc / rs_czsc 的耗时比，帮助快速识别
      性能回归。

候选信号集合默认使用 ``list_all_signals`` 输出的 222 条 K 线信号，
通过 ``_signal_defaults.render`` 渲染成具体的信号字符串后传入。

运行方式（在 worktree 根目录下）：

    uv run python test/parity/bench_optimize.py [--trials N]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import tempfile
import time
from pathlib import Path

# 把 parity 测试目录加入 sys.path，方便复用其中的辅助函数
ROOT = Path(__file__).resolve().parents[2]
PARITY_DIR = ROOT / "test" / "parity"
sys.path.insert(0, str(PARITY_DIR))
sys.path.insert(0, str(PARITY_DIR / "_compare_optimize"))


# 复用 parity 脚本中的工具函数（数据准备、模块导入、仓位文件落盘等）
from compare_optimize_full import (  # noqa: E402
    _import_module,
    _make_read_bars,
    all_kline_candidate_events,
    all_kline_candidate_signals,
    make_bars_df,
    write_beta_positions,
)


def time_open(module_name: str, results_root: Path, candidates: list[str]) -> float:
    """测量一次 ``OpensOptimize.execute`` 的耗时。

    参数:
        module_name: 待测模块名，``"rs_czsc"`` 或 ``"czsc"``。
        results_root: 用于存放本次试验输出的临时目录。
        candidates: 候选开仓信号字符串列表。

    返回:
        ``execute`` 调用的耗时（秒）。
    """
    czsc_mod, optim_mod = _import_module(module_name)
    OpensOptimize = optim_mod.OpensOptimize

    bar_sdt, bar_edt, sdt = "20200101", "20200310", "20200104"
    bars_5min = make_bars_df("5分钟", bar_sdt, bar_edt)
    bars_daily = make_bars_df("日线", bar_sdt, bar_edt)
    get_raw_bars = _make_read_bars(czsc_mod, bars_5min, bars_daily)
    files_position = write_beta_positions(czsc_mod, results_root / "base_positions", "000001")

    oop = OpensOptimize(
        symbols=["000001"],
        files_position=files_position,
        task_name="BenchOpen",
        candidate_signals=candidates,
        read_bars=get_raw_bars,
        results_path=results_root,
        bar_sdt=bar_sdt,
        bar_edt=bar_edt,
        sdt=sdt,
    )
    t0 = time.perf_counter()
    oop.execute(n_jobs=1)
    return time.perf_counter() - t0


def time_exit(module_name: str, results_root: Path, candidate_events: list[dict]) -> float:
    """测量一次 ``ExitsOptimize.execute`` 的耗时。

    参数:
        module_name: 待测模块名，``"rs_czsc"`` 或 ``"czsc"``。
        results_root: 用于存放本次试验输出的临时目录。
        candidate_events: 候选出场事件 dict 列表。

    返回:
        ``execute`` 调用的耗时（秒）。
    """
    czsc_mod, optim_mod = _import_module(module_name)
    ExitsOptimize = optim_mod.ExitsOptimize

    bar_sdt, bar_edt, sdt = "20200101", "20200310", "20200104"
    bars_5min = make_bars_df("5分钟", bar_sdt, bar_edt)
    bars_daily = make_bars_df("日线", bar_sdt, bar_edt)
    get_raw_bars = _make_read_bars(czsc_mod, bars_5min, bars_daily)
    files_position = write_beta_positions(czsc_mod, results_root / "base_positions", "000001")

    eop = ExitsOptimize(
        symbols=["000001"],
        files_position=files_position,
        task_name="BenchExit",
        candidate_events=candidate_events,
        read_bars=get_raw_bars,
        results_path=results_root,
        # 显式指定 base_freq 是为了绕过 czsc 在自动推导时对 strategy.positions 的处理 bug
        base_freq="5分钟",
        bar_sdt=bar_sdt,
        bar_edt=bar_edt,
        sdt=sdt,
    )
    t0 = time.perf_counter()
    eop.execute(n_jobs=1)
    return time.perf_counter() - t0


def fmt(times: list[float]) -> str:
    """把多次试验的耗时列表格式化为 ``mean±stdev (min/max)`` 字符串。"""
    if len(times) < 2:
        return f"{times[0] * 1000:.0f}ms"
    return (
        f"{statistics.mean(times) * 1000:.0f}±{statistics.stdev(times) * 1000:.0f}ms "
        f"(min {min(times) * 1000:.0f}ms / max {max(times) * 1000:.0f}ms)"
    )


def main():
    """命令行入口：解析参数、收集基准数据、打印汇总表。"""
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=5)
    args = ap.parse_args()

    # 候选信号 / 候选事件预计算一次即可：parity 测试已经证明两套实现
    # 在这部分输入上完全一致，因此可以放心共享。
    import czsc as _cz

    candidate_signals = all_kline_candidate_signals(_cz)
    candidate_events = all_kline_candidate_events(_cz)
    # 把可能存在的 dict 形式的信号统一回退成字符串形式，确保两套实现
    # 在最终消费时拿到完全相同的输入（双保险）。
    for e in candidate_events:
        e["signals_all"] = [(s if isinstance(s, str) else f"{s['key']}_{s['value']}") for s in e["signals_all"]]

    print(f"trials={args.trials}, candidate_signals={len(candidate_signals)}, candidate_events={len(candidate_events)}")
    print()

    # 每种 (module × kind) 组合都先做一次 warmup 以摊销 import / 首次调用开销，
    # 然后再跑 args.trials 次正式试验。
    results: dict = {"open": {}, "exit": {}}

    for kind, module in [("open", "rs_czsc"), ("open", "czsc"), ("exit", "rs_czsc"), ("exit", "czsc")]:
        # warm-up 阶段：失败时记录但不阻塞后续测量
        with tempfile.TemporaryDirectory() as tmp:
            try:
                if kind == "open":
                    time_open(module, Path(tmp), candidate_signals)
                else:
                    time_exit(module, Path(tmp), candidate_events)
            except Exception as e:
                print(f"[{module}/{kind}] warmup FAIL: {e}")
                continue

        times: list[float] = []
        for i in range(args.trials):
            with tempfile.TemporaryDirectory() as tmp:
                if kind == "open":
                    t = time_open(module, Path(tmp), candidate_signals)
                else:
                    t = time_exit(module, Path(tmp), candidate_events)
                times.append(t)
            print(f"  [{module}/{kind}] trial {i + 1}: {t * 1000:.0f}ms")
        results[kind][module] = times

    # 汇总输出
    print()
    print("=" * 64)
    print("BENCHMARK SUMMARY")
    print("=" * 64)
    print(f"{'kind':<8} {'rs_czsc':<28} {'czsc':<28} {'czsc/rs':<8}")
    for kind in ("open", "exit"):
        rs = results[kind].get("rs_czsc", [])
        cs = results[kind].get("czsc", [])
        if not rs or not cs:
            continue
        rs_mean = statistics.mean(rs)
        cs_mean = statistics.mean(cs)
        ratio = cs_mean / rs_mean
        print(f"{kind:<8} {fmt(rs):<28} {fmt(cs):<28} {ratio:.3f}x")
    print()


if __name__ == "__main__":
    main()
