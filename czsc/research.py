"""
策略研究 / 回放 / 优化的 Python 入口（Rust 后端薄封装）

模块职责:
    把 Python 端友好的入参（DataFrame、dict、Path 等）转换为 Rust 函数所需的
    紧凑布局（Arrow 字节流 + JSON 字符串），再把 Rust 返回的 dict 包装为
    更易消费的 dataclass（ResearchResult / ReplayResult / OptimizeResult）。

为何"薄封装"也值得单独成模块:
    1. 入参归一化逻辑（normalize_candidate_events / signal_config_to_runtime /
       position_dump_to_runtime）需要在多个入口复用，集中放在这里避免重复
    2. 序列化/反序列化（pandas <-> Arrow IPC、Python dict <-> JSON）也需要复用
    3. 屏蔽 Rust 端 PyO3 函数的"裸调用"，便于将来切换实现而不影响调用方
"""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import pandas as pd

# Rust/Python 兼容层：负责"用户层 dict <-> Rust 运行时 dict"的格式互转
from czsc._compat import (
    normalize_candidate_events,
    position_dump_to_runtime,
    signal_config_to_runtime,
)

# 直接调用 PyO3 暴露的 Rust 实现（带下划线别名表示"不要在调用方代码中再展开"）
from czsc._native import (
    build_exit_optim_positions as _build_exit_optim_positions,
)
from czsc._native import (
    build_open_optim_positions as _build_open_optim_positions,
)
from czsc._native import (
    run_optimize,
)
from czsc._native import (
    run_optimize_batch as _run_optimize_batch,
)
from czsc._native import (
    run_replay as _run_replay,
)
from czsc._native import (
    run_research as _run_research,
)
from czsc._utils._df_convert import pandas_to_arrow_bytes
from czsc.models import OptimizeResult, ReplayResult, ResearchResult

# 类型别名：bars 入参允许传 DataFrame 或已就绪的 Arrow IPC 字节
# 这种"两可"形式可以让上层在已经持有字节流的场景下省一次序列化
BarsLike = pd.DataFrame | bytes


def _ensure_arrow_bytes(bars: BarsLike) -> bytes:
    """
    将 bars 入参统一规范为 Arrow IPC 字节流

    支持的输入:
        - bytes / bytearray —— 直接转 bytes 返回，零成本
        - pd.DataFrame      —— 调用 ``pandas_to_arrow_bytes`` 完成序列化
        - 其他              —— 抛 TypeError，避免在 Rust 端再触发难懂的错误

    单独抽出此辅助函数的目的是同时被 ``run_research`` 与 ``run_replay`` 复用，
    避免分别实现导致两个入口的入参契约出现漂移。
    """
    if isinstance(bars, (bytes, bytearray)):
        return bytes(bars)
    if isinstance(bars, pd.DataFrame):
        return pandas_to_arrow_bytes(bars)
    raise TypeError(f"bars must be pd.DataFrame or bytes, got {type(bars)}")


def _to_research_result(payload: dict[str, Any], cls=ResearchResult):
    """
    把 Rust 返回的 dict 装配为 ResearchResult / ReplayResult dataclass

    参数:
        payload: Rust PyO3 函数返回的字典，键名固定（meta / *_arrow / *_path）
        cls:     目标 dataclass，默认 ResearchResult；run_replay 会传 ReplayResult

    备注:
        Rust 侧返回的 *_arrow 字段类型是 ``PyBytes``，
        通过 ``bytes(...)`` 显式转换可消除任何潜在的视图引用，避免上层
        在跨线程/异步场景下意外持有底层缓冲区。
    """
    return cls(
        meta=payload["meta"],
        signals_arrow=bytes(payload["signals_arrow"]),
        pairs_arrow=bytes(payload["pairs_arrow"]),
        holds_arrow=bytes(payload["holds_arrow"]),
        signals_path=payload.get("signals_path"),
        pairs_path=payload.get("pairs_path"),
        holds_path=payload.get("holds_path"),
    )


def run_research(
    bars: BarsLike,
    strategy: dict[str, Any],
    *,
    sdt: str | None = None,
    opts: dict[str, Any] | None = None,
) -> ResearchResult:
    """
    内存模式执行策略研究，返回 Arrow 格式的统一结果

    参数:
        bars:
            两种形式之一：
              - 标准 OHLCV 列布局的 ``pandas.DataFrame``
              - 同一 schema 序列化后的 Arrow IPC 字节流（bytes）
        strategy:
            Python 用户层格式的策略字典（含 ``signals_config`` / ``positions`` 等）。
            进入 Rust 之前会自动把其中的 positions 与 signals_config 归一化为
            运行时格式，调用方无需关心两套格式的差异。
        sdt:
            可选的起始时间覆盖；不传则使用 strategy 内默认设置。
        opts:
            可选的执行参数开关，例如 ``{"emit_signals": False}`` 用于禁用信号产物输出。

    返回:
        :class:`ResearchResult`，含元数据与三份 Arrow 字节流（信号 / 成对交易 / 持仓）

    备注:
        - 内存模式：完全在内存中产出 Arrow 字节，不会写盘；如需落盘请用 :func:`run_replay`
        - 入参 strategy 不会被原地修改：函数内部走浅拷贝
    """
    # 选项序列化为 JSON，传给 Rust 解析；None 直接透传，由 Rust 处理默认
    opts_json = json.dumps(opts, ensure_ascii=False) if opts else None

    # 浅拷贝避免修改调用方传入的 dict
    strategy_payload = dict(strategy)

    # positions / signals_config 都是用户层格式，需要先归一化为 Rust 运行时期望的紧凑布局
    if "positions" in strategy_payload:
        strategy_payload["positions"] = [
            position_dump_to_runtime(pos) if isinstance(pos, dict) else pos for pos in strategy_payload["positions"]
        ]
    if "signals_config" in strategy_payload:
        strategy_payload["signals_config"] = [
            signal_config_to_runtime(cfg) if isinstance(cfg, dict) else cfg
            for cfg in strategy_payload["signals_config"]
        ]

    # 进入 Rust：bars 转字节，strategy 转 JSON 字符串
    payload = _run_research(
        _ensure_arrow_bytes(bars),
        json.dumps(strategy_payload, ensure_ascii=False),
        sdt,
        opts_json,
    )
    return _to_research_result(payload, ResearchResult)


def run_replay(
    bars: BarsLike,
    strategy: dict[str, Any],
    *,
    res_path: str | Path | None = None,
    sdt: str | None = None,
    opts: dict[str, Any] | None = None,
) -> ReplayResult:
    """
    执行单标的回放任务，可选将 parquet 结果落盘

    与 :func:`run_research` 的差异:
        - 多了一个 ``res_path`` 参数：传入时会在该目录写入
          ``signals.parquet``、``pairs.parquet``、``holds.parquet``
        - 不传 ``res_path`` 时仍返回内存中的 Arrow 结果，行为退化为内存模式

    参数:
        bars:      OHLCV DataFrame 或同 schema 的 Arrow 字节
        strategy:  策略 dict，会自动归一化 positions/signals_config
        res_path:  结果落盘根目录；None 表示不落盘
        sdt:       可选起始时间覆盖
        opts:      可选执行参数开关

    返回:
        :class:`ReplayResult`（结构同 ResearchResult，仅类型语义不同）
    """
    path_str = str(res_path) if res_path is not None else None
    opts_json = json.dumps(opts, ensure_ascii=False) if opts else None

    strategy_payload = dict(strategy)
    if "positions" in strategy_payload:
        strategy_payload["positions"] = [
            position_dump_to_runtime(pos) if isinstance(pos, dict) else pos for pos in strategy_payload["positions"]
        ]
    if "signals_config" in strategy_payload:
        strategy_payload["signals_config"] = [
            signal_config_to_runtime(cfg) if isinstance(cfg, dict) else cfg
            for cfg in strategy_payload["signals_config"]
        ]

    payload = _run_replay(
        _ensure_arrow_bytes(bars),
        json.dumps(strategy_payload, ensure_ascii=False),
        path_str,
        sdt,
        opts_json,
    )
    return _to_research_result(payload, ReplayResult)


def run_optimize_batch(
    bars_dir: str | Path,
    optimize_cfg: dict[str, Any],
    res_path: str | Path,
    *,
    n_threads: int = 1,
) -> OptimizeResult:
    """
    根据 Python dict 配置批量执行参数优化任务

    参数:
        bars_dir:
            含多个标的 K 线 parquet 文件的目录（每个标的一份文件）。
            Rust 端会按 ``optimize_cfg["symbols"]`` 顺序加载对应文件。
        optimize_cfg:
            用户层格式的优化配置 dict。必须包含 ``symbols`` 字段，否则报错。
            若为平仓优化（``optim_type == "exit"``），函数会先把
            ``candidate_events`` 字段转换为 Rust 运行时格式，调用方无需手工归一化。
        res_path:
            优化结果输出根目录，Rust 端会在其中创建子目录写入参数组合产物。
        n_threads:
            Rust 端并行优化使用的线程数；默认为 1（串行），CPU 核多的机器
            可适当调大以加速。

    返回:
        :class:`OptimizeResult`，仅含一段简短的运行状态消息（成功/警告/错误概要）

    异常:
        TypeError:  optimize_cfg 不是 dict
        ValueError: 缺少 symbols 字段
    """
    if not isinstance(optimize_cfg, dict):
        raise TypeError("optimize_cfg must be dict")
    if "symbols" not in optimize_cfg:
        raise ValueError("optimize_cfg 缺少 symbols 字段")

    cfg = dict(optimize_cfg)
    # 平仓优化的候选事件字典需要先归一化为 Rust 运行时格式（统一 signals_all/any/not 等字段）
    if cfg.get("optim_type") == "exit" and "candidate_events" in cfg:
        cfg["candidate_events"] = normalize_candidate_events(cfg["candidate_events"])

    msg = _run_optimize_batch(
        str(bars_dir),
        json.dumps(cfg, ensure_ascii=False),
        str(res_path),
        n_threads,
    )
    return OptimizeResult(message=msg)


def build_open_optim_positions(
    files_position: list[str | Path],
    candidate_signals: list[str],
) -> list[dict[str, Any]]:
    """
    仅构造开仓优化的候选仓位（不真正执行回测）

    用途:
        在正式跑优化之前，先把候选 Position 列表导出来供人工审阅、对比或留档。
        典型流程是：build_open_optim_positions -> 人工筛选 -> run_optimize_batch。

    参数:
        files_position:    现有 Position JSON 文件路径列表，作为候选仓位的模板基准
        candidate_signals: 待与每个 Position 组合的候选信号 key 列表

    返回:
        Position.dump() 风格的字典列表，可直接序列化或喂给后续优化流程
    """
    payload = _build_open_optim_positions([str(x) for x in files_position], candidate_signals)
    return json.loads(payload)


def build_exit_optim_positions(
    files_position: list[str | Path],
    candidate_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    仅构造平仓优化的候选仓位（不真正执行回测）

    与 :func:`build_open_optim_positions` 类似，差别在于这里组合的是"候选平仓事件"。

    参数:
        files_position:   现有 Position JSON 文件路径列表
        candidate_events: 旧版 czsc 优化脚本使用的 Python 事件字典列表，
                          函数会自动调用 :func:`normalize_candidate_events` 做格式归一

    返回:
        Position.dump() 风格的字典列表
    """
    payload = _build_exit_optim_positions(
        [str(x) for x in files_position],
        json.dumps(normalize_candidate_events(candidate_events), ensure_ascii=False),
    )
    return json.loads(payload)


# === 兼容性回退入口（仅保留以平滑迁移）===
# 旧工作流依赖"先把 cfg dump 成临时 JSON，再调用 run_optimize"的两步式流程。
# 新代码请直接使用上方的 ``run_optimize_batch``（一步式、无临时文件）。
def run_optimize_batch_legacy(
    bars_dir: str | Path,
    optimize_cfg: dict[str, Any],
    res_path: str | Path,
    *,
    n_threads: int = 1,
) -> OptimizeResult:
    """
    兼容性回退入口：通过临时 JSON 文件调用旧版 ``run_optimize``

    仅供尚未切换到 ``run_optimize_batch`` 的存量代码使用。
    新项目不要再依赖本函数；它会创建临时文件、留下额外 IO，
    且不参与未来的接口演进。
    """
    # delete=False 是为了把文件路径继续传给 Rust，由 Rust 读取后无需 Python 持有句柄
    # （Python 出 with 块时 NamedTemporaryFile 默认会删除文件，会破坏 Rust 端读取）
    with NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as f:
        json.dump(optimize_cfg, f, ensure_ascii=False)
        config_path = f.name
    msg = run_optimize(str(bars_dir), config_path, str(res_path), n_threads)
    return OptimizeResult(message=msg)
