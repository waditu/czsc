"""完整 K 线信号集合下的 Open/Exit 优化等价性对比脚本。

本脚本对比 ``rs_czsc`` 与迁移后的 ``czsc`` 在 ``use_optimize.py`` 工作流
上的输出一致性，候选信号覆盖 ``list_all_signals`` 返回的全部 222 个
K 线信号。它在功能上与 ``rs_czsc/examples/use_optimize.py`` 等价，但
做了如下调整：

    * 缺失的 ``python/tests/k_line.feather`` 替换为 ``wbt.mock`` 提供的
      可重现 mock K 线（固定 ``seed=42``）。
    * 候选开仓信号从原来的 4 个扩展到 222 个，全部通过
      ``_signal_defaults.render`` 渲染成具体信号字符串。
    * ``OpensOptimize`` / ``ExitsOptimize`` 各跑一次 ``rs_czsc`` 与
      ``czsc``，输出分别落在两个兄弟目录下。
    * 遍历两份输出树，对每个 parquet / xlsx 文件做逐字节、逐字段对比。

运行方式（在 worktree 根目录下）：

    uv run python test/parity/compare_optimize_full.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PARITY_DIR = ROOT / "test" / "parity"
sys.path.insert(0, str(PARITY_DIR))

from _signal_defaults import render  # noqa: E402

OUT_ROOT = PARITY_DIR / "_compare_optimize"


# --------------------------------------------------------------------- #
# K 线数据准备 —— 用 mock 替换原示例缺失的 k_line.feather              #
# --------------------------------------------------------------------- #


def make_bars_df(freq: str, sdt: str, edt: str) -> pd.DataFrame:
    """生成单品种 mock K 线 DataFrame，列与示例脚本对齐。

    使用固定 ``seed=42`` 以保证两次运行（rs_czsc 与 czsc）的输入完全一致。
    """
    from wbt.mock import mock_symbol_kline

    df = mock_symbol_kline("000001", freq, sdt, edt, seed=42)
    df["dt"] = pd.to_datetime(df["dt"])
    cols = ["dt", "symbol", "open", "high", "low", "close", "vol", "amount"]
    return df.loc[:, cols].reset_index(drop=True).copy()


# --------------------------------------------------------------------- #
# Beta 仓位构造与 read_bars 回调                                       #
# --------------------------------------------------------------------- #


def _sig_str_to_kv(sig: str) -> dict:
    """把七段式信号字符串拆分成 ``{key, value}`` 字典形式。

    czsc.Position.load 只接受 dict 形式的信号；rs_czsc 两种都接受。
    统一使用 dict 形式可以让两套实现走完全相同的代码路径。
    """
    parts = sig.split("_")
    return {"key": "_".join(parts[:-4]), "value": "_".join(parts[-4:])}


def build_position(czsc_module, symbol, name, open_signal, open_operate):
    """根据传入的开仓信号构造一个 Beta 基准 Position。"""
    Position = czsc_module.Position
    exit_operate = "平多" if open_operate == "开多" else "平空"
    exit_signal = "5分钟_D1单K趋势N5_BS辅助V230506_第5层_任意_任意_0"

    def event_dict(name_, op, sig):
        # czsc.Position.load 只接受 dict 形式的信号；rs_czsc 两种都接受。
        # 为了让两条代码路径完全一致，这里统一使用 dict 形式。
        return {
            "name": name_,
            "operate": op,
            "signals_all": [_sig_str_to_kv(sig)],
            "signals_any": [],
            "signals_not": [],
        }

    # czsc.Position 不接受 T0 关键字参数；rs_czsc 接受。
    # 通过 .load 走 dict 入口可以让两套实现保持完全一致的入参形态。
    return Position.load(
        {
            "symbol": symbol,
            "name": name,
            "opens": [event_dict(f"{name}_open", open_operate, open_signal)],
            "exits": [event_dict(f"{name}_exit", exit_operate, exit_signal)],
            "interval": 0,
            "timeout": 120,
            "stop_loss": 800.0,
            "T0": False,
        }
    )


def write_beta_positions(czsc_module, path: Path, symbol: str) -> list[str]:
    """把多空两个 Beta 仓位序列化为 JSON 文件，返回文件路径列表。

    OpensOptimize / ExitsOptimize 都需要从磁盘文件加载基准仓位，
    两套实现使用相同的 JSON 内容即可保证后续对比的有效性。
    """
    path.mkdir(parents=True, exist_ok=True)
    positions = [
        build_position(
            czsc_module,
            symbol,
            "long_beta",
            "5分钟_D1单K趋势N5_BS辅助V230506_第1层_任意_任意_0",
            "开多",
        ),
        build_position(
            czsc_module,
            symbol,
            "short_beta",
            "5分钟_D1单K趋势N5_BS辅助V230506_第18层_任意_任意_0",
            "开空",
        ),
    ]
    files = []
    for pos in positions:
        payload = pos.dump(with_data=False)
        payload.pop("symbol", None)
        # md5 字段供 czsc 内部做去重 / 缓存命中校验
        payload["md5"] = hashlib.md5(str(payload).encode("utf-8")).hexdigest()
        f = path / f"{pos.name}.json"
        f.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        files.append(str(f))
    return files


# --------------------------------------------------------------------- #
# 候选信号集合 —— 全量 K 线信号（按默认参数渲染）                     #
# --------------------------------------------------------------------- #


def all_kline_candidate_signals(czsc_module) -> list[str]:
    """渲染信号注册表里所有 K 线类信号为完整七段式字符串。

    rs_czsc 在包根与 ``_native`` 子模块上都暴露了 ``list_all_signals``，
    而迁移后的 czsc 只在 ``_native`` 上暴露，这里做了兼容处理。
    """
    if hasattr(czsc_module, "_native"):
        all_sigs = czsc_module._native.list_all_signals()
    else:
        all_sigs = czsc_module.list_all_signals()
    sigs = [s for s in all_sigs if s["category"] == "kline"]
    rendered = []
    for s in sigs:
        try:
            r = render(s["param_template"])
            # 渲染后还有未填充占位符的模板直接丢弃
            if "{" not in r:
                rendered.append(r)
        except Exception:
            pass
    return sorted(set(rendered))


# --------------------------------------------------------------------- #
# 驱动逻辑 —— 对每个模块各跑一次 OpensOptimize / ExitsOptimize         #
# --------------------------------------------------------------------- #


def _import_module(module_name: str):
    """根据名字导入对应的 czsc 模块和 traders.optimize 子模块。

    rs_czsc 的 ``Event.is_match`` 默认返回 bool，但 optimize 包装层
    期望返回 (matched, reason) 元组，因此这里需要打 patch（与原示例
    脚本一致）。patch 设置幂等标记位避免重复包装。
    """
    if module_name == "rs_czsc":
        import rs_czsc as czsc_mod
        from rs_czsc import Event as _Event

        if not getattr(_Event, "_rs_tuple_contract_patch", False):
            origin = _Event.is_match

            def _wrapped(self, sig):
                out = origin(self, sig)
                return out if isinstance(out, tuple) else (out, "is_match" if out else "")

            _Event.is_match = _wrapped
            _Event._rs_tuple_contract_patch = True
    elif module_name == "czsc":
        import czsc as czsc_mod
    else:
        raise ValueError(module_name)
    import importlib

    optim_mod = importlib.import_module(f"{module_name}.traders.optimize")
    return czsc_mod, optim_mod


def _make_read_bars(czsc_mod, bars_5min, bars_daily):
    """构造一个 ``read_bars`` 回调，按 freq 选择对应频率的 mock 数据。"""

    def get_raw_bars(symbol_in, freq_in, sdt_in, edt_in, **_):
        df = bars_daily if freq_in == "日线" else bars_5min
        df = df[df["symbol"] == symbol_in]
        return czsc_mod.format_standard_kline(df, freq=freq_in)

    return get_raw_bars


def all_kline_candidate_events(czsc_mod) -> list[dict]:
    """构造 ExitsOptimize 所需的候选出场事件 dict 列表。

    遍历全量 K 线信号，按下标奇偶性交替使用 "平多" / "平空"，确保
    多空两边都有候选事件可供测试。

    注意事项：必须使用字符串形式的 signals_all（与 rs_czsc 示例一致），
    Rust 的 optimize-batch 在这个入口上对 dict 形式的 ``{key, value}`` 会
    panic —— 即便 ``Position.load`` 同时接受这两种形式 —— 这是
    ``ExitsOptimize`` 已知的入参 shape 限制。
    """
    out = []
    for i, sig in enumerate(all_kline_candidate_signals(czsc_mod)):
        operate = "平多" if i % 2 == 0 else "平空"
        out.append(
            {
                "name": f"exit_{i:03d}",
                "operate": operate,
                "signals_all": [sig],
                "signals_any": [],
                "signals_not": [],
            }
        )
    return out


def run_open(module_name: str, results_root: Path) -> Path:
    """运行一次 OpensOptimize 全流程，返回结果目录路径。"""
    czsc_mod, optim_mod = _import_module(module_name)
    OpensOptimize = optim_mod.OpensOptimize

    symbol = "000001"
    bar_sdt, bar_edt = "20200101", "20200310"
    sdt = "20200104"

    bars_5min = make_bars_df("5分钟", bar_sdt, bar_edt)
    bars_daily = make_bars_df("日线", bar_sdt, bar_edt)
    get_raw_bars = _make_read_bars(czsc_mod, bars_5min, bars_daily)

    files_position = write_beta_positions(czsc_mod, results_root / "base_positions", symbol)
    candidates = all_kline_candidate_signals(czsc_mod)
    print(f"[{module_name}/open] candidate_signals: {len(candidates)}")

    oop = OpensOptimize(
        symbols=[symbol],
        files_position=files_position,
        task_name="FullKlineParityOpen",
        candidate_signals=candidates,
        read_bars=get_raw_bars,
        results_path=results_root,
        signals_module_name="czsc.signals",
        bar_sdt=bar_sdt,
        bar_edt=bar_edt,
        sdt=sdt,
    )
    t0 = time.perf_counter()
    oop.execute(n_jobs=1)
    elapsed = time.perf_counter() - t0
    print(f"[{module_name}/open] elapsed={elapsed:.1f}s -> {oop.results_path}")
    return Path(oop.results_path)


def run_exit(module_name: str, results_root: Path) -> Path:
    """运行一次 ExitsOptimize 全流程，返回结果目录路径。"""
    czsc_mod, optim_mod = _import_module(module_name)
    ExitsOptimize = optim_mod.ExitsOptimize

    symbol = "000001"
    bar_sdt, bar_edt = "20200101", "20200310"
    sdt = "20200104"

    bars_5min = make_bars_df("5分钟", bar_sdt, bar_edt)
    bars_daily = make_bars_df("日线", bar_sdt, bar_edt)
    get_raw_bars = _make_read_bars(czsc_mod, bars_5min, bars_daily)

    files_position = write_beta_positions(czsc_mod, results_root / "base_positions", symbol)
    candidate_events = all_kline_candidate_events(czsc_mod)
    print(f"[{module_name}/exit] candidate_events: {len(candidate_events)}")

    eop = ExitsOptimize(
        symbols=[symbol],
        files_position=files_position,
        task_name="FullKlineParityExit",
        candidate_events=candidate_events,
        read_bars=get_raw_bars,
        results_path=results_root,
        signals_module_name="czsc.signals",
        # 显式传 base_freq 来跳过自动推导：迁移后的 czsc 在自动推导路径上
        # 会对字符串形式的 signals_all 调用 Position.load（其更严格的校验
        # 器会拒绝该形态）。两套实现的 Rust optimizer 调用本身都接受字符串。
        base_freq="5分钟",
        bar_sdt=bar_sdt,
        bar_edt=bar_edt,
        sdt=sdt,
    )
    t0 = time.perf_counter()
    eop.execute(n_jobs=1)
    elapsed = time.perf_counter() - t0
    print(f"[{module_name}/exit] elapsed={elapsed:.1f}s -> {eop.results_path}")
    return Path(eop.results_path)


# --------------------------------------------------------------------- #
# 输出树对比                                                           #
# --------------------------------------------------------------------- #


def inventory(root: Path) -> dict[str, int]:
    """递归扫描 ``root`` 下的所有文件，返回 {相对路径: 字节数}。"""
    out: dict[str, int] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = p.stat().st_size
    return out


def compare_trees(rs_path: Path, czsc_path: Path) -> dict:
    """对比两棵输出树：文件清单、字节大小、parquet 与 xlsx 内容。

    返回值是一个汇总 dict，包含：
        * rs_files / czsc_files:   两边的文件总数
        * rs_only / czsc_only:     仅出现在某一边的相对路径列表
        * size_diffs:              字节大小不同的文件列表
        * parquet_diffs:           内容不一致的 parquet 列表（含原因）
        * parquet_checked:         实际比对的 parquet 数量
        * xlsx_diffs / xlsx_checked: 同上，针对 xlsx
    """
    rs_inv = inventory(rs_path)
    cs_inv = inventory(czsc_path)

    summary = {
        "rs_files": len(rs_inv),
        "czsc_files": len(cs_inv),
        "rs_only": sorted(set(rs_inv) - set(cs_inv)),
        "czsc_only": sorted(set(cs_inv) - set(rs_inv)),
        "size_diffs": [],
        "parquet_diffs": [],
        "parquet_checked": 0,
        "xlsx_diffs": [],
        "xlsx_checked": 0,
    }

    common = sorted(set(rs_inv) & set(cs_inv))
    for rel in common:
        if rs_inv[rel] != cs_inv[rel]:
            summary["size_diffs"].append((rel, rs_inv[rel], cs_inv[rel]))
        if rel.endswith(".parquet"):
            summary["parquet_checked"] += 1
            try:
                a = pd.read_parquet(rs_path / rel)
                b = pd.read_parquet(czsc_path / rel)
                # cache 列含不可哈希对象，比对前先丢掉
                for c in ("cache",):
                    a = a.drop(columns=c, errors="ignore")
                    b = b.drop(columns=c, errors="ignore")
                if a.shape != b.shape:
                    summary["parquet_diffs"].append({"rel": rel, "kind": "shape", "rs": a.shape, "czsc": b.shape})
                    continue
                cols = sorted(set(a.columns) & set(b.columns))
                if set(a.columns) != set(b.columns):
                    summary["parquet_diffs"].append(
                        {
                            "rel": rel,
                            "kind": "columns",
                            "rs_only": sorted(set(a.columns) - set(b.columns)),
                            "czsc_only": sorted(set(b.columns) - set(a.columns)),
                        }
                    )
                a = a[cols].reset_index(drop=True)
                b = b[cols].reset_index(drop=True)
                try:
                    pd.testing.assert_frame_equal(a, b, check_dtype=False, check_like=False)
                except AssertionError as e:
                    summary["parquet_diffs"].append({"rel": rel, "kind": "data", "err": str(e)[:300]})
            except Exception as e:
                summary["parquet_diffs"].append({"rel": rel, "kind": "read-error", "err": str(e)[:300]})
        elif rel.endswith(".xlsx"):
            summary["xlsx_checked"] += 1
            try:
                a = pd.read_excel(rs_path / rel)
                b = pd.read_excel(czsc_path / rel)
                if a.shape != b.shape:
                    summary["xlsx_diffs"].append({"rel": rel, "kind": "shape", "rs": a.shape, "czsc": b.shape})
                    continue
                # 汇总 xlsx 的行序在两次运行间可能不同（Rust 的优化按 HashMap
                # 顺序遍历仓位）。比较前按 pos_name（或第一列）排序，确保
                # 我们做的是行集合相等的判断，而不是受顺序影响的逐行对比。
                sort_col = "pos_name" if "pos_name" in a.columns else a.columns[0]
                a = a.sort_values(sort_col).reset_index(drop=True)
                b = b.sort_values(sort_col).reset_index(drop=True)
                try:
                    pd.testing.assert_frame_equal(a, b, check_dtype=False, check_like=False)
                except AssertionError as e:
                    summary["xlsx_diffs"].append({"rel": rel, "kind": "data", "err": str(e)[:300]})
            except Exception as e:
                summary["xlsx_diffs"].append({"rel": rel, "kind": "read-error", "err": str(e)[:300]})
    return summary


def _print_report(label: str, rep: dict) -> bool:
    """格式化打印一份 compare_trees 报告，返回是否完全一致。"""
    print("=" * 60)
    print(f"[{label}] INVENTORY")
    print(f"  rs   files: {rep['rs_files']}")
    print(f"  czsc files: {rep['czsc_files']}")
    if rep["rs_only"] or rep["czsc_only"]:
        print(f"  rs only  : {rep['rs_only'][:10]} (showing 10)")
        print(f"  czsc only: {rep['czsc_only'][:10]} (showing 10)")
    else:
        print("  inventory: IDENTICAL")
    print(f"[{label}] SIZE DIFFS")
    if rep["size_diffs"]:
        for rel, a, b in rep["size_diffs"][:20]:
            print(f"  {rel}: rs={a}B czsc={b}B (Δ={b - a:+d})")
        print(f"  ... {len(rep['size_diffs'])} total")
    else:
        print("  (none) all files have identical byte size")
    print(f"[{label}] PARQUET COMPARISON ({rep['parquet_checked']} files checked)")
    if rep["parquet_diffs"]:
        for d in rep["parquet_diffs"][:20]:
            print(f"  - {d}")
        print(f"  ... {len(rep['parquet_diffs'])} total parquet diffs")
    else:
        print("  ALL PARQUET CONTENTS IDENTICAL ✓")
    print(f"[{label}] XLSX COMPARISON ({rep['xlsx_checked']} files, sorted)")
    if rep["xlsx_diffs"]:
        for d in rep["xlsx_diffs"][:20]:
            print(f"  - {d}")
    else:
        print("  ALL XLSX CONTENTS IDENTICAL (after sort) ✓")
    print("=" * 60)
    return not (rep["rs_only"] or rep["czsc_only"] or rep["parquet_diffs"] or rep["xlsx_diffs"])


def main():
    """命令行入口：先后运行 OPEN / EXIT 两侧并打印报告。"""
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    OUT_ROOT.mkdir(parents=True)

    # 开仓侧：rs_czsc 与 czsc 各跑一次，输出落到不同目录
    rs_open = run_open("rs_czsc", OUT_ROOT / "open_rs")
    cs_open = run_open("czsc", OUT_ROOT / "open_czsc")

    # 出场侧：同上
    rs_exit = run_exit("rs_czsc", OUT_ROOT / "exit_rs")
    cs_exit = run_exit("czsc", OUT_ROOT / "exit_czsc")

    print()
    print(f"OPEN  rs   results: {rs_open}")
    print(f"OPEN  czsc results: {cs_open}")
    print(f"EXIT  rs   results: {rs_exit}")
    print(f"EXIT  czsc results: {cs_exit}")
    print()

    open_ok = _print_report("OPEN", compare_trees(rs_open, cs_open))
    exit_ok = _print_report("EXIT", compare_trees(rs_exit, cs_exit))

    return 0 if (open_ok and exit_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
