"""CzscTrader 热启动状态快照（dump_state / restore_state）行为 parity 测试。

业务背景：
    1.0 架构下启动 CzscTrader 需从头逐根 on_bar 重放 1 分钟 K 线，把缠论计算
    状态与持仓决策状态推到当下，历史长时极慢。dump_state / restore_state 提供
    完整快照、零重放热启动：缠论计算状态（bg / kas / ta_cache 全历史）、仓位
    配置与运行时决策状态（pos / operates / holds）一并落盘，restore 后可继续
    流式喂 bar，结果与连续喂等价。

核心断言（零重放等价性）：
    喂 N 根后 dump_state、restore_state、再续喂 M 根，其末态必须与连续喂 N+M
    根**完全相等**——逐 Position 的 pos / pairs / holds / operates，以及 signals
    的 s 信号字典与各级别 CZSC（kas）末态。
"""

from __future__ import annotations

import time

import pytest

# 仓位使用的 日线 ADTM 信号（注册表中真实存在）
_SIGNAL_KEY = "日线_D1N5M5TH10_ADTMV230603"
_SIGNAL_STR = f"{_SIGNAL_KEY}_看多_任意_任意_0"

_POSITION_DICT = {
    "name": "test_pos",
    "symbol": "000001",
    "opens": [
        {
            "name": "open_long",
            "operate": "开多",
            "signals_all": [{"key": _SIGNAL_KEY, "value": "看多_任意_任意_0"}],
            "signals_any": [],
            "signals_not": [],
        },
    ],
    "exits": [
        {
            "name": "exit_long",
            "operate": "平多",
            "signals_all": [{"key": _SIGNAL_KEY, "value": "看空_任意_任意_0"}],
            "signals_any": [],
            "signals_not": [],
        },
    ],
    "interval": 0,
    "timeout": 100,
    "stop_loss": 500.0,
    "T0": False,
}


def _build_bars():
    """构造一段较长的 30 分钟基础 K 线，使 日线 信号有充分的演化与触发机会。"""
    from czsc import Freq, format_standard_kline
    from czsc.mock import generate_symbol_kines

    df = generate_symbol_kines("000001", "30分钟", "20200101", "20231231", seed=42)
    return format_standard_kline(df, freq=Freq.F30)


# 反向（开空/平空）仓位，与多头共用同一 日线 ADTM 信号源，用于多仓位用例
_SHORT_POSITION_DICT = {
    "name": "test_pos_short",
    "symbol": "000001",
    "opens": [
        {
            "name": "open_short",
            "operate": "开空",
            "signals_all": [{"key": _SIGNAL_KEY, "value": "看空_任意_任意_0"}],
            "signals_any": [],
            "signals_not": [],
        },
    ],
    "exits": [
        {
            "name": "exit_short",
            "operate": "平空",
            "signals_all": [{"key": _SIGNAL_KEY, "value": "看多_任意_任意_0"}],
            "signals_any": [],
            "signals_not": [],
        },
    ],
    "interval": 0,
    "timeout": 100,
    "stop_loss": 500.0,
    "T0": False,
}


def _new_trader(position_dicts=None, extra_signals=None):
    """构造 trader。``position_dicts`` 为 None 时用单个多头仓位；
    ``extra_signals`` 可追加 trader 级（freq=None）信号配置，覆盖
    maintain_all_kas + compiled_trader_ops 路径。"""
    import czsc
    from czsc.traders import get_signals_config

    if position_dicts is None:
        position_dicts = [_POSITION_DICT]
    bg = czsc.BarGenerator(base_freq="30分钟", freqs=["日线"])
    positions = [czsc.Position.load(d) for d in position_dicts]
    signals_config = get_signals_config([_SIGNAL_STR])
    if extra_signals:
        signals_config = signals_config + list(extra_signals)
    return czsc.CzscTrader(bg, positions, signals_config)


def _split_parity_check(bars, position_dicts, k, extra_signals=None):
    """喂前 k 根 -> dump -> restore -> 续喂剩余，断言末态与连续喂全量一致。
    返回 dump 边界处各仓位的 pos 列表（用于确认是否覆盖了"持仓中"场景）。"""
    full = _new_trader(position_dicts, extra_signals)
    for b in bars:
        full.on_bar(b)

    warm = _new_trader(position_dicts, extra_signals)
    for b in bars[:k]:
        warm.on_bar(b)
    boundary_pos = [p.pos for p in warm.positions]

    blob = warm.dump_state()
    hot = type(warm).restore_state(blob)
    for b in bars[k:]:
        hot.on_bar(b)

    assert _pos_state(hot) == _pos_state(full), f"k={k}: Position 决策末态不一致"
    assert _snapshot_kas(hot) == _snapshot_kas(full), f"k={k}: CZSC 末态不一致"
    assert hot.s == full.s, f"k={k}: 信号字典 s 不一致"
    assert hot.get_ensemble_pos() == full.get_ensemble_pos(), f"k={k}: 集成仓位不一致"
    return boundary_pos


def _first_in_position_split(bars, position_dicts, extra_signals=None):
    """返回首个"至少一个仓位持仓中"的切分点 k（喂前 k 根后 pos≠0）。"""
    trader = _new_trader(position_dicts, extra_signals)
    for i, bar in enumerate(bars):
        trader.on_bar(bar)
        if any(p.pos != 0 for p in trader.positions):
            return i + 1
    return None


def _snapshot_kas(trader) -> dict:
    """提取各级别 CZSC 的可比较末态：bars_raw / bars_ubi / bi_list 规模与末元素。"""
    out = {}
    for freq, czsc_obj in trader.kas.items():
        bars_raw = czsc_obj.bars_raw
        bi_list = czsc_obj.bi_list
        last_bar = bars_raw[-1] if bars_raw else None
        last_bi = bi_list[-1] if bi_list else None
        out[freq] = {
            "n_bars_raw": len(bars_raw),
            "n_bars_ubi": len(czsc_obj.bars_ubi),
            "n_bi": len(bi_list),
            "last_bar_dt": str(last_bar.dt) if last_bar is not None else None,
            "last_bar_close": round(last_bar.close, 8) if last_bar is not None else None,
            "last_bi_dir": str(last_bi.direction) if last_bi is not None else None,
            "last_bi_high": round(last_bi.high, 8) if last_bi is not None else None,
            "last_bi_low": round(last_bi.low, 8) if last_bi is not None else None,
        }
    return out


def _pos_state(trader) -> dict:
    """提取逐 Position 决策状态：pos / pairs / holds / operates。"""
    out = {}
    for p in trader.positions:
        out[p.name] = {
            "pos": p.pos,
            "pos_changed": p.pos_changed,
            "pairs": p.pairs,
            "holds": p.holds,
            "operates": p.operates,
        }
    return out


def test_dump_restore_zero_replay_parity():
    """restore + 续喂 M 根 ≡ 连续喂 N+M 根（零重放等价性）。"""
    bars = _build_bars()
    assert len(bars) > 200, "mock 数据应足够长以充分演化缠论状态"
    n = len(bars) // 2

    # 1) 基线：连续喂全部 bar
    trader_full = _new_trader()
    for bar in bars:
        trader_full.on_bar(bar)

    # 2) 热启动：喂前 N 根 -> dump -> restore -> 续喂后 M 根
    trader_warm = _new_trader()
    t0 = time.perf_counter()
    for bar in bars[:n]:
        trader_warm.on_bar(bar)
    replay_ns = time.perf_counter() - t0

    blob = trader_warm.dump_state()
    assert isinstance(blob, (bytes, bytearray)) and len(blob) > 0

    t1 = time.perf_counter()
    trader_hot = type(trader_warm).restore_state(blob)
    restore_ns = time.perf_counter() - t1

    for bar in bars[n:]:
        trader_hot.on_bar(bar)

    # 3) 等价性断言
    assert _pos_state(trader_hot) == _pos_state(trader_full), "Position 决策末态不一致"
    assert _snapshot_kas(trader_hot) == _snapshot_kas(trader_full), "各级别 CZSC 末态不一致"
    assert trader_hot.s == trader_full.s, "信号字典 s 末态不一致"
    assert trader_hot.get_ensemble_pos() == trader_full.get_ensemble_pos()

    # 4) 性能：restore 一次性反序列化应远快于重放 N 根
    print(
        f"\n[hot-start] N={n} bars | replay(N)={replay_ns * 1e3:.1f}ms "
        f"restore={restore_ns * 1e3:.3f}ms | speedup={replay_ns / max(restore_ns, 1e-9):.0f}x "
        f"| blob={len(blob) / 1024:.1f}KiB"
    )
    assert restore_ns < replay_ns, "restore 应快于重放 N 根（状态有界，一次性反序列化）"


def test_dump_restore_immediate_parity():
    """dump 后立即 restore（无后续 bar）应与原 trader 末态一致。"""
    bars = _build_bars()
    trader = _new_trader()
    for bar in bars:
        trader.on_bar(bar)

    blob = trader.dump_state()
    restored = type(trader).restore_state(blob)

    assert _pos_state(restored) == _pos_state(trader)
    assert _snapshot_kas(restored) == _snapshot_kas(trader)
    assert restored.s == trader.s
    assert restored.symbol == trader.symbol
    assert restored.name == trader.name


def _scan_position_phases(bars):
    """扫描单多头仓位在每根 bar 后的 pos，返回 (持仓中切分点列表, 空仓切分点列表)。

    切分点 k 表示"喂前 k 根后 dump"，即在 bar k-1 处的状态。"""
    trader = _new_trader()
    in_pos, flat = [], []
    for i, bar in enumerate(bars):
        trader.on_bar(bar)
        (in_pos if trader.positions[0].pos != 0 else flat).append(i + 1)
    return in_pos, flat


def test_dump_restore_parity_at_many_split_points():
    """在多个切分点（含若干"持仓中"边界）验证零重放等价性。

    这是热启动的核心场景：在仓位**持有中**（pos≠0、last_event/temp_state/进行中
    的 holds 都非平凡）做 dump，restore 后必须无缝接续，结果与连续喂完全一致。
    """
    bars = _build_bars()
    in_pos, flat = _scan_position_phases(bars)
    assert in_pos, "mock 数据应至少触发一次持仓，否则无法验证持仓中热启动"

    # 取若干持仓中切分点 + 一个空仓切分点
    split_points = sorted(
        {
            in_pos[len(in_pos) // 4],
            in_pos[len(in_pos) // 2],
            in_pos[-1],
            flat[len(flat) // 2] if flat else in_pos[0],
        }
    )

    covered_in_position = False
    for k in split_points:
        boundary_pos = _split_parity_check(bars, [_POSITION_DICT], k)
        if any(p != 0 for p in boundary_pos):
            covered_in_position = True
    # 显式确认：至少有一个切分点确实落在"持仓中"边界上
    assert covered_in_position, "未覆盖到持仓中（pos≠0）的 dump 边界，测试不充分"
    print(f"\n[hot-start] 验证切分点={split_points}，含持仓中边界 ✓")


def test_multi_position_zero_replay_parity():
    """多仓位（多头 + 空头）热启动等价性，覆盖 positions↔runtime 对齐与集成。"""
    bars = _build_bars()
    position_dicts = [_POSITION_DICT, _SHORT_POSITION_DICT]

    # 选一个让"至少一个仓位持仓中"的切分点
    trader = _new_trader(position_dicts)
    chosen_k = None
    for i, bar in enumerate(bars):
        trader.on_bar(bar)
        if any(p.pos != 0 for p in trader.positions):
            chosen_k = i + 1
            break
    assert chosen_k is not None, "多仓位场景应至少触发一次持仓"

    boundary_pos = _split_parity_check(bars, position_dicts, chosen_k)
    assert any(p != 0 for p in boundary_pos)
    print(f"\n[hot-start] 多仓位切分点 k={chosen_k}，边界 pos={boundary_pos} ✓")


# trader 级信号要求 pos_name 不含下划线（否则破坏 k1_k2_k3_v1_v2_v3_score 七段格式）
_TRADER_SIG_POSITION = {**_POSITION_DICT, "name": "longpos"}
_TRADER_LEVEL_SIGNAL = {"name": "pos_status_V230808", "freq": None, "pos_name": "longpos"}


def test_trader_level_signal_zero_replay_parity():
    """含 trader 级（pos）信号时的热启动等价性。

    覆盖 maintain_all_kas + compiled_trader_ops 重建路径：trader 级信号
    pos_status_V230808 读取 ``operates.last()``，正是 restore 还原的运行时状态，
    因此 restore 后该信号的取值必须与连续喂完全一致。
    """
    bars = _build_bars()
    pos_dicts = [_TRADER_SIG_POSITION]
    extra = [_TRADER_LEVEL_SIGNAL]

    k = _first_in_position_split(bars, pos_dicts, extra)
    assert k is not None, "应至少触发一次持仓"
    boundary_pos = _split_parity_check(bars, pos_dicts, k, extra)
    assert any(p != 0 for p in boundary_pos), "切分点应落在持仓中"

    # 额外确认：连续喂的末态信号字典确实含 trader 级信号键
    full = _new_trader(pos_dicts, extra)
    for b in bars:
        full.on_bar(b)
    assert any("BS辅助V230808" in key for key in full.s), "trader 级信号未进入 s，覆盖无效"
    print(f"\n[hot-start] trader 级信号切分点 k={k}，边界 pos={boundary_pos} ✓")


def test_interval_and_t0_constraints_parity():
    """interval>0 + T0=True 约束下的热启动等价性。

    interval 约束依赖 temp_state 的 last_lo_dt/last_so_dt（运行时状态），
    若快照漏掉它，restore 后的开仓节流行为会与连续喂分叉。此用例用大 interval
    显著改变 operate 序列，再在持仓中边界 dump/restore，强制校验 temp_state 携带。
    """
    bars = _build_bars()
    # interval=10 天（秒）：同类型开仓被节流；T0 允许当日开平
    pos_dict = {
        **_POSITION_DICT,
        "name": "intervalpos",
        "interval": 10 * 24 * 3600,
        "T0": True,
    }
    pos_dicts = [pos_dict]

    # 基线无约束 vs 有约束的 operate 数应当不同，确保 interval 真的生效
    base = _new_trader([_POSITION_DICT])
    constrained = _new_trader(pos_dicts)
    for b in bars:
        base.on_bar(b)
        constrained.on_bar(b)
    assert len(constrained.positions[0].operates) != len(base.positions[0].operates), (
        "interval 约束未改变 operate 序列，用例无法验证 temp_state 携带"
    )

    k = _first_in_position_split(bars, pos_dicts)
    assert k is not None
    boundary_pos = _split_parity_check(bars, pos_dicts, k)
    assert any(p != 0 for p in boundary_pos)
    print(f"\n[hot-start] interval/T0 切分点 k={k}，边界 pos={boundary_pos} ✓")


def test_restore_state_rejects_garbage():
    """非法字节应被干净拒绝，而非崩溃。"""
    import czsc

    # restore_state 内部错误统一映射为 ValueError
    with pytest.raises(ValueError):
        czsc.CzscTrader.restore_state(b"not-a-valid-snapshot")


def test_restore_state_rejects_version_mismatch():
    """快照版本不匹配应被显式拒绝（区别于解码失败）。

    快照为 MessagePack named-map，``version`` 字段当前为 1（fixint 0x01）。
    将其篡改为 0x02 后 restore 必须报"版本"错误而非崩溃。"""
    import czsc

    trader = _new_trader()
    for bar in _build_bars()[:300]:
        trader.on_bar(bar)
    blob = bytearray(trader.dump_state())

    key = b"version"
    idx = blob.find(key)
    assert idx != -1, "快照应包含 version 字段（named-map 编码）"
    vpos = idx + len(key)
    assert blob[vpos] == 0x01, "version 当前应编码为 msgpack fixint 0x01"
    blob[vpos] = 0x02  # 伪造一个不支持的版本

    with pytest.raises(ValueError, match="版本|version"):
        czsc.CzscTrader.restore_state(bytes(blob))
