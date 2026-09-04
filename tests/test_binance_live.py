"""scripts/binance_live.py 的自动化测试：全部使用模拟 HTTP / WebSocket 数据，不访问网络。"""

from __future__ import annotations

import csv
import datetime as _dt
import importlib.util
import json
import re
import signal
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "binance_live.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("binance_live", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["binance_live"] = module
    spec.loader.exec_module(module)
    return module


bl = _load_script()

MINUTE_MS = 60_000
T0 = 1_700_000_000_000 - (1_700_000_000_000 % MINUTE_MS)  # 对齐到整分钟的开盘时间


def _rest_row(open_ms: int, close: float = 100.0):
    """构造一行 Binance REST /api/v3/klines 返回的 12 元素数组。"""
    return [
        open_ms,
        "99.0",
        "101.0",
        "98.0",
        str(close),
        "12.5",
        open_ms + MINUTE_MS - 1,
        "1250.0",
        10,
        "6.0",
        "600.0",
        "0",
    ]


def _ws_event(open_ms: int, closed: bool, close: float = 100.0):
    """构造一条 Binance kline WebSocket 推送。"""
    return {
        "e": "kline",
        "E": open_ms + MINUTE_MS,
        "s": "BTCUSDT",
        "k": {
            "t": open_ms,
            "T": open_ms + MINUTE_MS - 1,
            "s": "BTCUSDT",
            "i": "1m",
            "o": "99.0",
            "c": str(close),
            "h": "101.0",
            "l": "98.0",
            "v": "12.5",
            "q": "1250.0",
            "x": closed,
        },
    }


# --------------------------------------------------------------------------- 解析层


def test_interval_ms_supports_minutes_hours_days():
    assert bl.interval_ms("1m") == MINUTE_MS
    assert bl.interval_ms("15m") == 15 * MINUTE_MS
    assert bl.interval_ms("1h") == 60 * MINUTE_MS
    assert bl.interval_ms("1d") == 24 * 60 * MINUTE_MS


def test_interval_ms_rejects_unknown_interval():
    with pytest.raises(ValueError):
        bl.interval_ms("7x")


def test_kline_from_rest_row_parses_prices_as_float():
    k = bl.kline_from_rest_row(_rest_row(T0, close=100.5))
    assert k.open_time_ms == T0
    assert (k.open, k.high, k.low, k.close) == (99.0, 101.0, 98.0, 100.5)
    assert k.volume == 12.5
    assert k.quote_volume == 1250.0


def test_kline_from_ws_event_returns_none_for_unclosed_candle():
    assert bl.kline_from_ws_event(_ws_event(T0, closed=False)) is None


def test_kline_from_ws_event_returns_kline_for_closed_candle():
    k = bl.kline_from_ws_event(_ws_event(T0, closed=True, close=100.5))
    assert k is not None
    assert k.open_time_ms == T0
    assert k.close == 100.5
    assert k.quote_volume == 1250.0


def test_kline_from_ws_event_ignores_non_kline_messages():
    assert bl.kline_from_ws_event({"result": None, "id": 1}) is None


def test_kline_to_bar_uses_naive_utc_close_time_as_dt():
    k = bl.kline_from_rest_row(_rest_row(T0))
    bar = bl.kline_to_bar(k, symbol="BTCUSDT", interval="1m", bar_id=7)
    expected_dt = _dt.datetime.fromtimestamp((T0 + MINUTE_MS) / 1000, tz=_dt.timezone.utc).replace(tzinfo=None)
    assert bar.dt == expected_dt
    assert bar.dt.tzinfo is None
    assert bar.id == 7
    assert bar.symbol == "BTCUSDT"
    assert (bar.open, bar.close, bar.high, bar.low) == (99.0, 100.0, 101.0, 98.0)
    assert bar.vol == 12.5
    assert bar.amount == 1250.0


# --------------------------------------------------------------------------- REST 回补


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _fake_http(rows, calls):
    def http_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": dict(params or {}), "timeout": timeout})
        return _FakeResponse(rows)

    return http_get


def test_fetch_closed_klines_drops_bar_that_has_not_closed_yet():
    rows = [_rest_row(T0), _rest_row(T0 + MINUTE_MS), _rest_row(T0 + 2 * MINUTE_MS)]
    now_ms = T0 + 2 * MINUTE_MS + 30_000  # 第三根还在进行中
    calls = []
    klines = bl.fetch_closed_klines("BTCUSDT", "1m", limit=1000, http_get=_fake_http(rows, calls), now_ms=now_ms)
    assert [k.open_time_ms for k in klines] == [T0, T0 + MINUTE_MS]


def test_fetch_closed_klines_requests_spot_endpoint_with_symbol_interval_limit():
    calls = []
    bl.fetch_closed_klines("BTCUSDT", "1m", limit=500, http_get=_fake_http([], calls), now_ms=T0)
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.binance.com/api/v3/klines"
    # 不给 endTime 时 Binance 一定会带上正在形成的那根，实际只剩 limit-1 根已收盘的
    assert calls[0]["params"] == {"symbol": "BTCUSDT", "interval": "1m", "limit": 500, "endTime": T0 - 1}
    assert calls[0]["timeout"]


def test_fetch_closed_klines_caps_end_time_at_last_closed_candle():
    """请求就截到最后一根已收盘 K 线，才能真的拿满 limit 根。"""
    now_ms = T0 + 5 * MINUTE_MS + 30_000  # 第 6 根正在形成
    rows = [_rest_row(T0 + i * MINUTE_MS) for i in range(5)]
    calls = []

    klines = bl.fetch_closed_klines("BTCUSDT", "1m", limit=5, http_get=_fake_http(rows, calls), now_ms=now_ms)

    assert calls[0]["params"]["endTime"] == T0 + 5 * MINUTE_MS - 1  # 最后一根已收盘 K 线的收盘时刻
    assert len(klines) == 5  # 没有被正在形成的那根挤掉一根


def test_fetch_closed_klines_drops_forming_candle_even_if_server_returns_it():
    """兜底：本地时钟走快 / 服务端多给一根时，正在形成的 K 线仍必须被丢掉。

    放进 CZSC 的脏 K 线会被后续同 open_time 的收盘推送当成重复丢弃，从此永远冻在那里。
    """
    now_ms = T0 + 3 * MINUTE_MS  # 第 4 根刚开盘
    rows = [_rest_row(T0 + i * MINUTE_MS) for i in range(4)]
    calls = []

    klines = bl.fetch_closed_klines("BTCUSDT", "1m", limit=4, http_get=_fake_http(rows, calls), now_ms=now_ms)

    assert calls[0]["params"]["endTime"] == T0 + 3 * MINUTE_MS - 1
    assert [k.open_time_ms for k in klines] == [T0 + i * MINUTE_MS for i in range(3)]


def test_fetch_closed_klines_passes_time_window_for_gap_fill():
    calls = []
    bl.fetch_closed_klines(
        "BTCUSDT",
        "1m",
        limit=1000,
        start_ms=T0,
        end_ms=T0 + 5 * MINUTE_MS,
        http_get=_fake_http([], calls),
        now_ms=T0 + 10 * MINUTE_MS,
    )
    assert calls[0]["params"]["startTime"] == T0
    assert calls[0]["params"]["endTime"] == T0 + 5 * MINUTE_MS


# --------------------------------------------------------------------------- 引擎

CSV_HEADER = ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]
SUMMARY_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC close=\S+ fx=\d+ bi=\d+ last_bi=(-|向上|向下)$")


def _kline(open_ms: int, close: float = 100.0, *, open_: float = 99.0, high: float = 101.0, low: float = 98.0):
    """构造一根扁平的已收盘 K 线（默认 OHLC 恒定，不会形成分型 / 笔）。"""
    return bl.Kline(
        open_time_ms=open_ms,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=12.5,
        quote_volume=1250.0,
    )


def _klines(n: int, start_ms: int = T0):
    return [_kline(start_ms + i * MINUTE_MS) for i in range(n)]


def _no_fetch(start_ms, end_ms):
    raise AssertionError(f"不应触发缺口回补: {start_ms}~{end_ms}")


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def _dt_text(open_ms: int) -> str:
    return _dt.datetime.fromtimestamp((open_ms + MINUTE_MS) / 1000, tz=_dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def test_engine_bootstrap_rejects_empty_klines():
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=[].append)
    with pytest.raises(ValueError):
        engine.bootstrap([])


def test_engine_bootstrap_builds_czsc_and_emits_one_line():
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap(_klines(5))
    assert len(engine.czsc.bars_raw) == 5
    assert [b.id for b in engine.czsc.bars_raw] == [0, 1, 2, 3, 4]
    assert engine.last_open_time_ms == T0 + 4 * MINUTE_MS
    assert engine.last_id == 4
    assert len(lines) == 1
    assert lines[0] == f"已回补 5 根 BTCUSDT 1m K 线，最新收盘时间 {_dt_text(T0 + 4 * MINUTE_MS)} UTC"


def test_engine_bootstrap_writes_csv_header_and_rows(tmp_path):
    path = tmp_path / "nested" / "btc.csv"
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=[].append)
    engine.bootstrap(_klines(3))
    rows = _read_csv(path)
    assert rows[0] == CSV_HEADER
    assert len(rows) == 4
    assert [r[0] for r in rows[1:]] == [_dt_text(T0 + i * MINUTE_MS) for i in range(3)]
    assert rows[1][1] == "BTCUSDT"
    assert rows[1][2:] == ["99.0", "100.0", "101.0", "98.0", "12.5", "1250.0"]


def _seed_csv(path, klines, symbol="BTCUSDT"):
    """用生产代码（一次性引擎的 bootstrap）预置历史 CSV，避免测试重复实现 CSV 格式。"""
    bl.LiveEngine(symbol, "1m", csv_path=path, fetch_range=_no_fetch, sink=[].append).bootstrap(klines)


def test_engine_bootstrap_merges_existing_csv_and_rest_wins(tmp_path):
    path = tmp_path / "btc.csv"
    _seed_csv(path, [_kline(T0 + i * MINUTE_MS, close=50.0) for i in range(3)])
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap([_kline(T0 + i * MINUTE_MS, close=100.0) for i in (2, 3, 4)])

    assert len(engine.czsc.bars_raw) == 5
    assert [b.id for b in engine.czsc.bars_raw] == [0, 1, 2, 3, 4]
    assert [b.close for b in engine.czsc.bars_raw] == [50.0, 50.0, 100.0, 100.0, 100.0]
    assert engine.last_open_time_ms == T0 + 4 * MINUTE_MS
    assert len(lines) == 1

    rows = _read_csv(path)
    assert rows[0] == CSV_HEADER
    assert [r[0] for r in rows[1:]] == [_dt_text(T0 + i * MINUTE_MS) for i in range(5)]
    assert [r[3] for r in rows[1:]] == ["50.0", "50.0", "100.0", "100.0", "100.0"]


def test_engine_bootstrap_fills_hole_between_csv_tail_and_rest_head(tmp_path):
    path = tmp_path / "btc.csv"
    _seed_csv(path, [_kline(T0 + i * MINUTE_MS) for i in range(2)])
    calls = []

    def fetch_range(start_ms, end_ms):
        calls.append((start_ms, end_ms))
        return [_kline(T0 + i * MINUTE_MS) for i in (2, 3)]

    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=fetch_range, sink=[].append)
    engine.bootstrap([_kline(T0 + i * MINUTE_MS) for i in (4, 5)])

    assert calls == [(T0 + 2 * MINUTE_MS, T0 + 4 * MINUTE_MS - 1)]
    assert [b.id for b in engine.czsc.bars_raw] == list(range(6))
    assert [r[0] for r in _read_csv(path)[1:]] == [_dt_text(T0 + i * MINUTE_MS) for i in range(6)]


def test_engine_on_kline_ignores_duplicate_open_time(tmp_path):
    path = tmp_path / "btc.csv"
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap(_klines(3))
    lines.clear()

    assert engine.on_kline(_kline(T0 + 2 * MINUTE_MS)) is False
    assert len(engine.czsc.bars_raw) == 3
    assert engine.last_id == 2
    assert len(_read_csv(path)) == 4
    assert lines == []


def test_engine_on_kline_ignores_out_of_order_bar():
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap(_klines(3))
    lines.clear()

    assert engine.on_kline(_kline(T0)) is False
    assert len(engine.czsc.bars_raw) == 3
    assert lines == []


def test_engine_on_kline_applies_next_bar(tmp_path):
    path = tmp_path / "btc.csv"
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap(_klines(3))
    lines.clear()

    assert engine.on_kline(_kline(T0 + 3 * MINUTE_MS, close=100.5)) is True
    assert len(engine.czsc.bars_raw) == 4
    assert engine.czsc.bars_raw[-1].id == 3
    assert engine.last_id == 3
    assert engine.last_open_time_ms == T0 + 3 * MINUTE_MS

    rows = _read_csv(path)
    assert len(rows) == 5
    assert rows[-1][0] == _dt_text(T0 + 3 * MINUTE_MS)
    assert rows[-1][3] == "100.5"

    assert len(lines) == 1
    assert lines[0] == f"{_dt_text(T0 + 3 * MINUTE_MS)} UTC close=100.5 fx=0 bi=0 last_bi=-"


def test_engine_on_kline_fills_three_bar_gap(tmp_path):
    path = tmp_path / "btc.csv"
    lines = []
    calls = []

    def fetch_range(start_ms, end_ms):
        calls.append((start_ms, end_ms))
        return [_kline(T0 + i * MINUTE_MS) for i in (3, 4, 5)]

    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=fetch_range, sink=lines.append)
    engine.bootstrap(_klines(3))
    lines.clear()

    assert engine.on_kline(_kline(T0 + 6 * MINUTE_MS)) is True
    assert calls == [(T0 + 3 * MINUTE_MS, T0 + 6 * MINUTE_MS - 1)]
    assert [b.id for b in engine.czsc.bars_raw] == list(range(7))
    assert [b.dt for b in engine.czsc.bars_raw][-1] == _dt.datetime.strptime(
        _dt_text(T0 + 6 * MINUTE_MS), "%Y-%m-%d %H:%M:%S"
    )
    assert [r[0] for r in _read_csv(path)[1:]] == [_dt_text(T0 + i * MINUTE_MS) for i in range(7)]

    assert len(lines) == 3  # 缺口提示 + 回补完成 + 1 根实时摘要（补齐的 3 根不逐条打印）
    assert "缺口" in lines[0]
    assert lines[1].startswith("回补完成 3 根")
    assert SUMMARY_RE.match(lines[2]), lines[2]


def test_engine_gap_with_empty_fetch_warns_but_keeps_going():
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=lambda s, e: [], sink=lines.append)
    engine.bootstrap(_klines(3))
    lines.clear()

    assert engine.on_kline(_kline(T0 + 6 * MINUTE_MS)) is True
    assert len(engine.czsc.bars_raw) == 4
    assert engine.last_open_time_ms == T0 + 6 * MINUTE_MS
    assert len(lines) == 3
    assert "缺口" in lines[0]
    assert lines[1].startswith("警告")
    assert SUMMARY_RE.match(lines[2]), lines[2]

    # 引擎仍可继续处理后续 K 线
    assert engine.on_kline(_kline(T0 + 7 * MINUTE_MS)) is True


def test_engine_gap_larger_than_one_page_is_fetched_repeatedly():
    calls = []

    def fetch_range(start_ms, end_ms):
        calls.append((start_ms, end_ms))
        opens = list(range(start_ms, end_ms + 1, MINUTE_MS))
        return [_kline(t) for t in opens[:2]]

    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=fetch_range, sink=[].append)
    engine.bootstrap(_klines(1))

    assert engine.on_kline(_kline(T0 + 7 * MINUTE_MS)) is True
    assert [c[0] for c in calls] == [T0 + MINUTE_MS, T0 + 3 * MINUTE_MS, T0 + 5 * MINUTE_MS]
    assert all(c[1] == T0 + 7 * MINUTE_MS - 1 for c in calls)
    assert [b.id for b in engine.czsc.bars_raw] == list(range(8))


def test_engine_works_without_csv_persistence():
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap(_klines(3))
    assert engine.on_kline(_kline(T0 + 3 * MINUTE_MS)) is True
    assert engine.on_kline(_kline(T0 + 3 * MINUTE_MS)) is False
    assert len(engine.czsc.bars_raw) == 4
    assert len(lines) == 2


def _zigzag_klines(runs: int = 5, run_len: int = 8, start_ms: int = T0):
    """交替上涨 / 下跌的锯齿行情，用于让 CZSC 形成分型与笔。"""
    klines = []
    prev = 100.0
    rising = True
    idx = 0
    for _ in range(runs):
        for _ in range(run_len):
            close = prev + 1.0 if rising else prev - 1.0
            klines.append(
                _kline(
                    start_ms + idx * MINUTE_MS,
                    close=close,
                    open_=prev,
                    high=max(prev, close) + 0.5,
                    low=min(prev, close) - 0.5,
                )
            )
            prev = close
            idx += 1
        rising = not rising
    return klines


def test_engine_summary_last_bi_dash_when_no_bi_then_direction_once_bi_forms():
    # 只有 3 根平盘 K 线，形不成分型 / 笔
    flat_lines = []
    flat = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=flat_lines.append)
    flat.bootstrap(_klines(3))
    flat.on_kline(_kline(T0 + 3 * MINUTE_MS))
    assert flat_lines[-1].endswith("close=100.0 fx=0 bi=0 last_bi=-")

    # 锯齿行情下分型与笔都会出现
    zig_lines = []
    klines = _zigzag_klines()
    zig = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=zig_lines.append)
    zig.bootstrap(klines[:-1])
    assert zig.on_kline(klines[-1]) is True

    summary = zig_lines[-1]
    assert SUMMARY_RE.match(summary), summary
    assert len(zig.czsc.fx_list) > 0
    assert len(zig.czsc.bi_list) > 0
    assert f"fx={len(zig.czsc.fx_list)} bi={len(zig.czsc.bi_list)}" in summary
    assert summary.rsplit("last_bi=", 1)[1] in {"向上", "向下"}


def test_engine_on_kline_before_bootstrap_raises():
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=[].append)
    with pytest.raises(RuntimeError):
        engine.on_kline(_kline(T0))


def test_interval_ms_rejects_zero_or_negative_multiplier():
    with pytest.raises(ValueError):
        bl.interval_ms("0m")


def test_interval_freq_supports_common_binance_intervals():
    from czsc import Freq

    assert bl.interval_freq("1m") is Freq.F1
    assert bl.interval_freq("5m") is Freq.F5
    assert bl.interval_freq("15m") is Freq.F15
    assert bl.interval_freq("30m") is Freq.F30
    assert bl.interval_freq("1h") is Freq.F60
    assert bl.interval_freq("4h") is Freq.F240
    assert bl.interval_freq("1d") is Freq.D


def test_engine_init_rejects_interval_without_freq_mapping():
    with pytest.raises(ValueError):
        bl.LiveEngine("BTCUSDT", "2h", csv_path=None, fetch_range=_no_fetch, sink=[].append)


def test_engine_summary_keeps_full_price_precision():
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=lines.append)
    tiny = [_kline(T0 + i * MINUTE_MS, close=1e-08, open_=1e-08, high=2e-08, low=5e-09) for i in range(3)]
    engine.bootstrap(tiny)
    engine.on_kline(_kline(T0 + 3 * MINUTE_MS, close=1e-08, open_=1e-08, high=2e-08, low=5e-09))
    assert "close=1e-08 " in lines[-1]
    assert SUMMARY_RE.match(lines[-1]), lines[-1]


# --------------------------------------------------------------------------- CSV 读写


def test_read_csv_klines_round_trips_awkward_floats(tmp_path):
    path = tmp_path / "btc.csv"
    klines = [
        bl.Kline(
            open_time_ms=T0 + i * MINUTE_MS,
            open=0.1 + 0.2,
            high=123456.789012345,
            low=1e-08,
            close=123456.789012345 if i % 2 else 0.30000000000000004,
            volume=1e-08,
            quote_volume=0.1 + 0.2,
        )
        for i in range(3)
    ]
    _seed_csv(path, klines)
    assert bl.read_csv_klines(path, "1m", symbol="BTCUSDT") == klines


def test_read_csv_klines_skips_malformed_rows_and_warns(tmp_path):
    path = tmp_path / "btc.csv"
    _seed_csv(path, _klines(3))
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n")  # 空行：DictReader 会跳过，行号不能靠计数器推算
        f.write(f"{_dt_text(T0 + 3 * MINUTE_MS)},BTCUSDT,99.0\n")  # 第 6 行：截断
        f.write(f"{_dt_text(T0 + 4 * MINUTE_MS)},BTCUSDT,abc,100.0,101.0,98.0,12.5,1250.0\n")  # 第 7 行：脏字段

    warnings = []
    klines = bl.read_csv_klines(path, "1m", symbol="BTCUSDT", warn=warnings.append)
    assert [k.open_time_ms for k in klines] == [T0 + i * MINUTE_MS for i in range(3)]
    assert len(warnings) == 2
    assert all(w.startswith("警告：") for w in warnings)
    assert "第 6 行" in warnings[0], warnings[0]
    assert "第 7 行" in warnings[1], warnings[1]


def test_read_csv_klines_handles_header_only_and_empty_file(tmp_path):
    header_only = tmp_path / "header.csv"
    header_only.write_text(",".join(CSV_HEADER) + "\n", encoding="utf-8")
    assert bl.read_csv_klines(header_only, "1m", symbol="BTCUSDT") == []

    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    assert bl.read_csv_klines(empty, "1m", symbol="BTCUSDT") == []


def test_read_csv_klines_rejects_rows_of_another_symbol(tmp_path):
    path = tmp_path / "eth.csv"
    _seed_csv(path, _klines(3), symbol="ETHUSDT")
    with pytest.raises(ValueError, match="ETHUSDT"):
        bl.read_csv_klines(path, "1m", symbol="BTCUSDT")


def test_engine_bootstrap_rejects_csv_of_another_symbol(tmp_path):
    path = tmp_path / "eth.csv"
    _seed_csv(path, _klines(3), symbol="ETHUSDT")
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=[].append)
    with pytest.raises(ValueError):
        engine.bootstrap(_klines(2, start_ms=T0 + 3 * MINUTE_MS))


def test_read_csv_klines_rejects_dt_not_aligned_to_interval(tmp_path):
    path = tmp_path / "btc.csv"
    _seed_csv(path, _klines(2))
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{_dt_text(T0 + 2 * MINUTE_MS)[:-2]}30,BTCUSDT,99.0,100.0,101.0,98.0,12.5,1250.0\n")
    with pytest.raises(ValueError, match="周期"):
        bl.read_csv_klines(path, "1m", symbol="BTCUSDT")


# --------------------------------------------------------------------------- 缺口告警与落盘


def test_engine_gap_fill_warns_about_hole_inside_a_batch():
    lines = []
    engine = bl.LiveEngine(
        "BTCUSDT",
        "1m",
        csv_path=None,
        fetch_range=lambda s, e: [_kline(T0 + i * MINUTE_MS) for i in (1, 2, 4)],
        sink=lines.append,
    )
    engine.bootstrap(_klines(1))
    lines.clear()

    assert engine.on_kline(_kline(T0 + 5 * MINUTE_MS)) is True
    holes = [line for line in lines if line.startswith("警告：") and "缺失" in line]
    assert len(holes) == 1, lines
    assert _dt_text(T0 + 3 * MINUTE_MS) in holes[0]  # 缺失那根的收盘时间
    assert [b.id for b in engine.czsc.bars_raw] == [0, 1, 2, 3, 4]


def test_engine_bootstrap_warns_about_hole_in_merged_series():
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap([_kline(T0 + i * MINUTE_MS) for i in (0, 1, 3)])
    holes = [line for line in lines if line.startswith("警告：") and "缺失" in line]
    assert len(holes) == 1, lines
    assert _dt_text(T0 + 2 * MINUTE_MS) in holes[0]


def test_engine_bootstrap_write_leaves_no_temp_file(tmp_path):
    path = tmp_path / "btc.csv"
    _seed_csv(path, _klines(2))
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=[].append)
    engine.bootstrap(_klines(2, start_ms=T0 + 2 * MINUTE_MS))

    assert [p.name for p in tmp_path.iterdir()] == ["btc.csv"]
    assert [r[0] for r in _read_csv(path)[1:]] == [_dt_text(T0 + i * MINUTE_MS) for i in range(4)]


def test_engine_bootstrap_hole_fill_announces_itself(tmp_path):
    path = tmp_path / "btc.csv"
    _seed_csv(path, _klines(2))
    lines = []
    engine = bl.LiveEngine(
        "BTCUSDT",
        "1m",
        csv_path=path,
        fetch_range=lambda s, e: [_kline(T0 + i * MINUTE_MS) for i in (2, 3)],
        sink=lines.append,
    )
    engine.bootstrap([_kline(T0 + i * MINUTE_MS) for i in (4, 5)])

    assert len(lines) == 2, lines
    assert "缺口" in lines[0]
    assert lines[1].startswith("已回补 6 根")


def test_engine_apply_warns_when_csv_append_fails_but_keeps_czsc_state(tmp_path):
    path = tmp_path / "btc.csv"
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=lines.append)
    engine.bootstrap(_klines(3))
    path.unlink()
    path.mkdir()  # 让后续追加写必定抛 OSError
    lines.clear()

    assert engine.on_kline(_kline(T0 + 3 * MINUTE_MS)) is True
    assert len(engine.czsc.bars_raw) == 4
    assert engine.last_open_time_ms == T0 + 3 * MINUTE_MS
    assert engine.last_id == 3
    assert any(line.startswith("警告：") and "CSV" in line for line in lines), lines
    assert SUMMARY_RE.match(lines[-1]), lines[-1]


def test_engine_append_rewrites_header_when_csv_was_removed(tmp_path):
    path = tmp_path / "btc.csv"
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=path, fetch_range=_no_fetch, sink=[].append)
    engine.bootstrap(_klines(3))
    path.unlink()  # 模拟运行中被轮转 / 删除

    live = _kline(T0 + 3 * MINUTE_MS, close=100.5)
    assert engine.on_kline(live) is True
    assert _read_csv(path)[0] == CSV_HEADER
    assert bl.read_csv_klines(path, "1m", symbol="BTCUSDT") == [live]


def test_read_csv_klines_rejects_unexpected_header(tmp_path):
    path = tmp_path / "btc.csv"
    path.write_text("dt,symbol,open,high,low,close,vol,amount\n", encoding="utf-8")
    with pytest.raises(ValueError, match="表头"):
        bl.read_csv_klines(path, "1m", symbol="BTCUSDT")

    headerless = tmp_path / "headerless.csv"
    headerless.write_text(f"{_dt_text(T0)},BTCUSDT,99.0,100.0,101.0,98.0,12.5,1250.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="表头"):
        bl.read_csv_klines(headerless, "1m", symbol="BTCUSDT")


def test_engine_gap_fill_warns_about_leading_hole():
    lines = []
    engine = bl.LiveEngine(
        "BTCUSDT",
        "1m",
        csv_path=None,
        fetch_range=lambda s, e: [_kline(T0 + i * MINUTE_MS) for i in (3, 4, 5)],
        sink=lines.append,
    )
    engine.bootstrap(_klines(1))
    lines.clear()

    assert engine.on_kline(_kline(T0 + 6 * MINUTE_MS)) is True
    holes = [line for line in lines if line.startswith("警告：") and "缺失" in line]
    assert len(holes) == 1, lines
    assert "缺失 2 根" in holes[0]
    assert _dt_text(T0 + MINUTE_MS) in holes[0] and _dt_text(T0 + 2 * MINUTE_MS) in holes[0]


def test_engine_gap_fill_warns_about_hole_between_pages():
    pages = [
        [_kline(T0 + i * MINUTE_MS) for i in (1, 2)],
        [_kline(T0 + i * MINUTE_MS) for i in (4, 5)],  # 与上一页不衔接，缺 3
        [_kline(T0 + i * MINUTE_MS) for i in (6, 7)],
    ]
    lines = []
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=lambda s, e: pages.pop(0), sink=lines.append)
    engine.bootstrap(_klines(1))
    lines.clear()

    assert engine.on_kline(_kline(T0 + 8 * MINUTE_MS)) is True
    holes = [line for line in lines if line.startswith("警告：") and "缺失" in line]
    assert len(holes) == 1, lines
    assert "缺失 1 根" in holes[0]
    assert _dt_text(T0 + 3 * MINUTE_MS) in holes[0]


# --------------------------------------------------------------------------- 主循环


def _clear_sink(sink):
    """sink 是 list.append 时清空它，让断言只看主循环产生的输出。"""
    owner = getattr(sink, "__self__", None)
    if isinstance(owner, list):
        owner.clear()


def _bootstrapped(sink, *, fetch_range=_no_fetch, csv_path=None, n=3):
    """构造一个已 bootstrap 的引擎（默认 3 根，最后一根开盘时间为 T0+2m）。"""
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=csv_path, fetch_range=fetch_range, sink=sink)
    engine.bootstrap(_klines(n))
    _clear_sink(sink)
    return engine


def _boom(exc: BaseException | None = None):
    """返回一个一取值就抛异常的迭代器（模拟断线）。"""
    error = exc if exc is not None else ConnectionError("socket 断了")

    def gen():
        raise error
        yield  # pragma: no cover - 仅为把函数变成生成器

    return gen()


def test_run_stops_after_max_bars_and_ignores_unclosed_events():
    lines = []
    engine = _bootstrapped(lines.append)
    events = [
        _ws_event(T0 + 3 * MINUTE_MS, closed=False),
        _ws_event(T0 + 3 * MINUTE_MS, closed=True),
        _ws_event(T0 + 4 * MINUTE_MS, closed=False),
        _ws_event(T0 + 4 * MINUTE_MS, closed=True),
        _ws_event(T0 + 5 * MINUTE_MS, closed=True),  # max_bars 已满，不应被消费
    ]
    calls = []

    def factory(symbol, interval):
        calls.append((symbol, interval))
        return iter(events)

    assert bl.run(engine, stream_factory=factory, max_bars=2) == 2
    assert calls == [("BTCUSDT", "1m")]
    assert lines[0] == bl._CONNECTING_TMPL.format(symbol="BTCUSDT", interval="1m")
    assert engine.last_open_time_ms == T0 + 4 * MINUTE_MS
    assert len(engine.czsc.bars_raw) == 5
    assert len([line for line in lines if SUMMARY_RE.match(line)]) == 2


def test_run_does_not_count_duplicate_closed_event():
    lines = []
    engine = _bootstrapped(lines.append)
    events = [
        _ws_event(T0 + 3 * MINUTE_MS, closed=True),
        _ws_event(T0 + 3 * MINUTE_MS, closed=True),  # 重复推送
        _ws_event(T0 + 4 * MINUTE_MS, closed=True),
    ]

    assert bl.run(engine, stream_factory=lambda s, i: iter(events), max_bars=2) == 2
    assert len(engine.czsc.bars_raw) == 5


def test_run_reconnects_after_stream_error():
    lines = []
    engine = _bootstrapped(lines.append)
    sleeps = []
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        if len(calls) == 1:
            return _boom()
        return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, max_bars=1, sleep=sleeps.append) == 1
    assert len(calls) == 2
    assert sleeps == [bl.RECONNECT_INITIAL_S] == [1.0]
    assert engine.last_open_time_ms == T0 + 3 * MINUTE_MS
    assert any(line.startswith("警告：") and "socket 断了" in line for line in lines), lines


def test_run_reconnects_when_stream_factory_itself_raises():
    """建连本身失败（握手 / DNS）也应退避重连，而不是把异常抛给调用方。"""
    lines = []
    engine = _bootstrapped(lines.append)
    sleeps = []
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        if len(calls) == 1:
            raise ConnectionError("握手失败")
        return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, max_bars=1, sleep=sleeps.append) == 1
    assert len(calls) == 2
    assert sleeps == [1.0]
    assert any(line.startswith("警告：") and "握手失败" in line for line in lines), lines


def _forbid_sleep(_seconds):
    raise AssertionError("不应发生不可中断的退避等待")


class _FakeStop:
    """假 threading.Event：记录每次退避等待的时长，便于断言指数退避序列。"""

    def __init__(self):
        self.waits = []
        self._set = False

    def is_set(self):
        return self._set

    def set(self):
        self._set = True

    def wait(self, timeout=None):
        self.waits.append(timeout)
        return self._set


def test_run_backoff_doubles_and_caps_at_max():
    lines = []
    engine = _bootstrapped(lines.append)
    stop = _FakeStop()
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        if len(calls) >= 8:
            stop.set()
        return _boom()

    assert bl.run(engine, stream_factory=factory, stop=stop, sleep=_forbid_sleep) == 0
    assert stop.waits == [1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0]
    assert any("2 秒后重连" in line for line in lines), lines


def test_run_backoff_wait_is_interrupted_by_stop():
    """给了 stop 就必须用 stop.wait 退避，否则 SIGTERM 要等满 60 秒才生效。"""
    engine = _bootstrapped([].append)
    stop = _FakeStop()

    def factory(symbol, interval):
        stop.set()
        return _boom()

    assert bl.run(engine, stream_factory=factory, stop=stop, sleep=_forbid_sleep) == 0
    assert stop.waits == [1.0]


def test_run_backoff_resets_after_a_successful_bar():
    engine = _bootstrapped([].append)
    sleeps = []
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        if len(calls) == 3:
            return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])
        if len(calls) >= 4:
            return _boom(KeyboardInterrupt())
        return _boom()

    assert bl.run(engine, stream_factory=factory, sleep=sleeps.append) == 1
    assert sleeps == [1.0, 2.0, 1.0]  # 成功应用一根后退避重置


def test_run_reconnects_when_stream_ends_normally():
    lines = []
    engine = _bootstrapped(lines.append)
    sleeps = []
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        if len(calls) == 1:
            return iter([])  # 服务端主动关闭连接
        return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, max_bars=1, sleep=sleeps.append) == 1
    assert len(calls) == 2
    assert sleeps == [1.0]  # 正常结束也走退避，避免服务端秒断时热循环
    assert any(bl._SERVER_CLOSED_MSG in line and "1 秒后重连" in line for line in lines), lines


def test_run_warns_and_continues_when_engine_raises():
    lines = []
    fetch_calls = []

    def fetch_range(start_ms, end_ms):
        fetch_calls.append(1)
        if len(fetch_calls) == 1:
            raise RuntimeError("REST 回补失败")
        return []

    engine = _bootstrapped(lines.append, fetch_range=fetch_range)
    sleeps = []
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        return iter([_ws_event(T0 + 6 * MINUTE_MS, closed=True), _ws_event(T0 + 7 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, max_bars=1, sleep=sleeps.append) == 1
    assert calls == [1]  # 引擎异常不算断线，不重连
    assert sleeps == []  # 也不退避
    assert any(line.startswith("警告：") and "REST 回补失败" in line for line in lines), lines
    assert engine.last_open_time_ms == T0 + 7 * MINUTE_MS


def test_run_returns_count_on_keyboard_interrupt_from_stream():
    lines = []
    engine = _bootstrapped(lines.append)

    def gen():
        yield _ws_event(T0 + 3 * MINUTE_MS, closed=True)
        raise KeyboardInterrupt

    assert bl.run(engine, stream_factory=lambda s, i: gen()) == 1
    assert lines[-1] == bl._CTRL_C_MSG


def test_run_returns_count_on_keyboard_interrupt_from_sleep():
    lines = []
    engine = _bootstrapped(lines.append)

    def sleep(_seconds):
        raise KeyboardInterrupt

    def factory(symbol, interval):
        return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, sleep=sleep) == 1
    assert lines[-1] == bl._CTRL_C_MSG


def test_run_stops_when_stop_event_is_set_inside_stream():
    lines = []
    engine = _bootstrapped(lines.append)
    stop = threading.Event()

    def gen():
        yield _ws_event(T0 + 3 * MINUTE_MS, closed=True)
        stop.set()
        yield _ws_event(T0 + 4 * MINUTE_MS, closed=False)  # 未收盘，不计数；处理完应检测到 stop
        raise AssertionError("stop 置位后不应继续消费消息")

    assert bl.run(engine, stream_factory=lambda s, i: gen(), stop=stop) == 1


def test_run_returns_once_duration_elapsed():
    engine = _bootstrapped([].append)
    ticks = [0.0, 0.0]

    def clock():
        return ticks.pop(0) if ticks else 3.0

    def gen():
        yield _ws_event(T0 + 3 * MINUTE_MS, closed=True)
        raise AssertionError("超时后不应继续消费消息")

    assert bl.run(engine, stream_factory=lambda s, i: gen(), duration_s=2.0, clock=clock) == 1


def test_run_closes_the_stream_when_it_stops():
    engine = _bootstrapped([].append)
    closed = []
    made = []

    def gen():
        try:
            yield _ws_event(T0 + 3 * MINUTE_MS, closed=True)
            yield _ws_event(T0 + 4 * MINUTE_MS, closed=True)
        finally:
            closed.append(True)

    def factory(symbol, interval):
        g = gen()
        made.append(g)  # 持有引用：只有显式 close 才会走到 finally
        return g

    assert bl.run(engine, stream_factory=factory, max_bars=1) == 1
    assert closed == [True]


def test_run_before_bootstrap_raises():
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch, sink=[].append)
    with pytest.raises(RuntimeError):
        bl.run(engine, stream_factory=lambda s, i: iter([]))


def test_stream_url_uses_lowercase_symbol():
    assert bl.stream_url("BTCUSDT", "1m") == "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
    assert bl.stream_url("ETHUSDT", "15m", url="wss://example.test/ws") == "wss://example.test/ws/ethusdt@kline_15m"


# --------------------------------------------------------------------------- CLI


def test_parser_defaults():
    args = bl.build_parser().parse_args([])
    assert args.symbol == "BTCUSDT"
    assert args.interval == "1m"
    assert args.limit == 1000
    assert args.csv is None
    assert args.no_csv is False
    assert args.max_bars is None
    assert args.duration is None
    assert bl.default_csv_path(args.symbol, args.interval) == Path("data") / "BTCUSDT_1m.csv"


def test_parser_upper_cases_symbol():
    assert bl.build_parser().parse_args(["--symbol", "ethusdt"]).symbol == "ETHUSDT"
    assert bl.default_csv_path("ETHUSDT", "15m") == Path("data") / "ETHUSDT_15m.csv"


def test_parser_rejects_interval_without_freq_mapping():
    with pytest.raises(SystemExit):
        bl.build_parser().parse_args(["--interval", "2h"])


def test_parser_rejects_limit_out_of_range():
    for bad in ("0", "1001", "abc"):
        with pytest.raises(SystemExit):
            bl.build_parser().parse_args(["--limit", bad])
    assert bl.build_parser().parse_args(["--limit", "500"]).limit == 500


def test_parser_no_csv_flag():
    assert bl.build_parser().parse_args(["--no-csv"]).no_csv is True
    assert bl.build_parser().parse_args(["--csv", "x.csv"]).csv == Path("x.csv")


def test_main_end_to_end_with_fake_fetch_and_stream(tmp_path):
    path = tmp_path / "btc.csv"
    lines = []
    fetch_calls = []

    def fetch(symbol, interval, *, limit=None, start_ms=None, end_ms=None):
        fetch_calls.append((symbol, interval, limit, start_ms, end_ms))
        if start_ms is None:
            return _klines(5)
        return [_kline(t) for t in range(start_ms, end_ms + 1, MINUTE_MS)]

    def stream_factory(symbol, interval):
        return iter([_ws_event(T0 + 5 * MINUTE_MS, closed=True), _ws_event(T0 + 6 * MINUTE_MS, closed=True)])

    rc = bl.main(
        ["--symbol", "btcusdt", "--max-bars", "2", "--csv", str(path)],
        fetch=fetch,
        stream_factory=stream_factory,
        sink=lines.append,
    )

    assert rc == 0
    assert fetch_calls == [("BTCUSDT", "1m", 1000, None, None)]  # 无缺口，不触发回补
    rows = _read_csv(path)
    assert rows[0] == CSV_HEADER
    assert len(rows) == 8  # 表头 + 7 根
    assert [r[0] for r in rows[1:]] == [_dt_text(T0 + i * MINUTE_MS) for i in range(7)]

    assert "仅公开行情，不接账户、不保存密钥、不下单" in lines[0]
    assert any(line.startswith("已回补 5 根") for line in lines), lines
    assert len([line for line in lines if SUMMARY_RE.match(line)]) == 2
    assert "WebSocket 实时处理 2 根" in lines[-1] and "不含回补" in lines[-1], lines[-1]
    assert any(str(path.resolve()) in line for line in lines), lines


# --------------------------------------------------------------------------- 默认日志 sink


def test_log_prefixes_utc_timestamp(capsys):
    bl._log("hello")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} hello\n", capsys.readouterr().out)


def test_live_engine_defaults_to_timestamped_log_sink():
    engine = bl.LiveEngine("BTCUSDT", "1m", csv_path=None, fetch_range=_no_fetch)
    assert engine.sink is bl._log


def test_run_disconnect_warning_names_the_exception_type():
    """TimeoutError() 的 str 是空串，日志必须靠 repr 才有信息量。"""
    lines = []
    engine = _bootstrapped(lines.append)
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        if len(calls) == 1:
            return _boom(TimeoutError())
        return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, max_bars=1, sleep=[].append) == 1
    assert any("TimeoutError" in line for line in lines), lines


# --------------------------------------------------------------------------- 主循环健壮性


class _ExplodingCloseStream:
    """迭代正常、但 close() 抛异常的流：清理失败不该打断主循环。"""

    def __init__(self, events):
        self._events = iter(events)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._events)

    def close(self):
        raise OSError("关闭连接失败")


def test_run_survives_stream_close_failure():
    lines = []
    engine = _bootstrapped(lines.append)
    stream = _ExplodingCloseStream([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=lambda s, i: stream, max_bars=1) == 1
    assert any(line.startswith(bl._WARN) and "关闭连接失败" in line for line in lines), lines


def test_run_skips_malformed_kline_frame_without_reconnecting():
    lines = []
    engine = _bootstrapped(lines.append)
    sleeps = []
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        return iter([{"e": "kline"}, _ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, max_bars=1, sleep=sleeps.append) == 1
    assert calls == [1]  # 坏帧不算断线
    assert sleeps == []
    assert any(line.startswith(bl._WARN) and "解析" in line for line in lines), lines


class _InterruptingStop(_FakeStop):
    """退避等待时被 Ctrl+C 打断的假 Event。"""

    def wait(self, timeout=None):
        super().wait(timeout)
        raise KeyboardInterrupt


def _capped_clock(*ticks, final: float):
    """按顺序返回 ticks，用完后固定返回 final。"""
    remaining = list(ticks)

    def clock():
        return remaining.pop(0) if remaining else final

    return clock


def test_run_backoff_wait_is_bounded_by_remaining_duration():
    """duration 只剩 0.5 秒时，不该再等满 1 秒的退避。"""
    engine = _bootstrapped([].append)
    stop = _FakeStop()
    clock = _capped_clock(0.0, 0.0, 9.5, final=10.0)

    assert (
        bl.run(
            engine,
            stream_factory=lambda s, i: _boom(),
            stop=stop,
            duration_s=10.0,
            clock=clock,
            sleep=_forbid_sleep,
        )
        == 0
    )
    assert stop.waits == [0.5]


def test_run_sleep_backoff_is_bounded_by_remaining_duration():
    engine = _bootstrapped([].append)
    sleeps = []
    clock = _capped_clock(0.0, 0.0, 9.5, final=10.0)

    assert bl.run(engine, stream_factory=lambda s, i: _boom(), duration_s=10.0, clock=clock, sleep=sleeps.append) == 0
    assert sleeps == [0.5]


def test_run_returns_count_on_keyboard_interrupt_during_backoff_wait():
    lines = []
    engine = _bootstrapped(lines.append)
    stop = _InterruptingStop()

    def factory(symbol, interval):
        return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    assert bl.run(engine, stream_factory=factory, stop=stop, sleep=_forbid_sleep) == 1
    assert stop.waits == [1.0]
    assert lines[-1] == bl._CTRL_C_MSG


def test_run_does_not_retry_a_missing_dependency():
    """缺 websockets 这类永久性配置错误，重连只会每 60 秒刷一次屏，应直接抛给调用方。"""
    engine = _bootstrapped([].append)
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        if len(calls) == 1:
            raise ImportError("No module named 'websockets'")
        return iter([_ws_event(T0 + 3 * MINUTE_MS, closed=True)])

    with pytest.raises(ImportError):
        bl.run(engine, stream_factory=factory, max_bars=1, sleep=_forbid_sleep)
    assert calls == [1]


def test_run_with_max_bars_zero_never_connects():
    calls = []
    engine = _bootstrapped([].append)

    def factory(symbol, interval):
        calls.append(1)
        return iter([])

    assert bl.run(engine, stream_factory=factory, max_bars=0) == 0
    assert calls == []


def _gapping_events(n: int):
    """每条都比上一条多跳一根，确保每次 on_kline 都会触发缺口回补。"""
    return [_ws_event(T0 + (4 + 2 * i) * MINUTE_MS, closed=True) for i in range(n)]


def test_run_raises_after_too_many_consecutive_engine_failures():
    lines = []

    def fetch_range(start_ms, end_ms):
        raise RuntimeError("REST 一直失败")

    engine = _bootstrapped(lines.append, fetch_range=fetch_range)
    calls = []

    def factory(symbol, interval):
        calls.append(1)
        return iter(_gapping_events(bl.MAX_ENGINE_FAILURES + 5))

    with pytest.raises(bl.EngineFailureLimit):
        bl.run(engine, stream_factory=factory)
    assert calls == [1]  # 引擎连续失败不是断线，不重连
    assert len([line for line in lines if line.startswith(bl._WARN)]) == bl.MAX_ENGINE_FAILURES


def test_run_resets_engine_failure_counter_after_a_success():
    calls = []

    def fetch_range(start_ms, end_ms):
        calls.append(1)
        if len(calls) % bl.MAX_ENGINE_FAILURES == 0:
            return []  # 第 10 / 20 次成功，把连续失败计数清零
        raise RuntimeError("REST 失败")

    engine = _bootstrapped([].append, fetch_range=fetch_range)
    events = _gapping_events(2 * bl.MAX_ENGINE_FAILURES)

    assert bl.run(engine, stream_factory=lambda s, i: iter(events), max_bars=2) == 2
    assert len(calls) == 2 * bl.MAX_ENGINE_FAILURES


# --------------------------------------------------------------------------- 默认 WebSocket 流


class _FakeClosedOK(Exception):
    """冒充 websockets.exceptions.ConnectionClosedOK（真包未安装，也不该在测试里连网）。"""


class _FakeWS:
    """按脚本逐条返回 recv 结果；脚本项是异常实例时抛出它。"""

    def __init__(self, script):
        self._script = list(script)
        self.timeouts = []

    def recv(self, timeout=None):
        self.timeouts.append(timeout)
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class _FakeConnect:
    """可注入的 connect：记录建连 URL，本身充当上下文管理器并记录 __exit__。"""

    def __init__(self, ws):
        self.ws = ws
        self.urls = []
        self.exited = []

    def __call__(self, url):
        self.urls.append(url)
        return self

    def __enter__(self):
        return self.ws

    def __exit__(self, exc_type, exc, tb):
        self.exited.append(exc_type)
        return False


def _fake_stream(script, symbol="BTCUSDT", interval="1m", **kwargs):
    connect = _FakeConnect(_FakeWS(script))
    gen = bl.binance_kline_stream(symbol, interval, connect=connect, closed_ok=_FakeClosedOK, **kwargs)
    return gen, connect


def test_binance_kline_stream_yields_parsed_json_from_lowercase_url():
    """ConnectionClosedOK 应让生成器正常结束，run() 才会走「服务端关闭」而不是告警分支。"""
    gen, connect = _fake_stream([json.dumps(_ws_event(T0, closed=True)), _FakeClosedOK()])

    assert [m["k"]["t"] for m in gen] == [T0]  # 正常耗尽，未抛异常
    assert connect.urls == ["wss://stream.binance.com:9443/ws/btcusdt@kline_1m"]
    assert connect.ws.timeouts == [bl.RECV_TIMEOUT_S, bl.RECV_TIMEOUT_S]  # 必须带 timeout 关键字
    assert connect.exited == [None]  # 连接被正常关闭


def test_binance_kline_stream_honours_custom_recv_timeout():
    gen, connect = _fake_stream([_FakeClosedOK()], recv_timeout_s=5.0)
    assert list(gen) == []
    assert connect.ws.timeouts == [5.0]


def test_binance_kline_stream_propagates_timeout_error():
    gen, connect = _fake_stream([TimeoutError()])
    with pytest.raises(TimeoutError):
        next(gen)
    assert connect.exited == [TimeoutError]


def test_binance_kline_stream_closes_connection_on_generator_close():
    events = [json.dumps(_ws_event(T0 + i * MINUTE_MS, closed=True)) for i in range(2)]
    gen, connect = _fake_stream(events)

    next(gen)
    assert connect.exited == []
    gen.close()
    assert connect.exited == [GeneratorExit]


def test_importing_the_script_does_not_import_websockets():
    """棘轮：websockets 只能在建连时惰性导入，模块本身必须在没装该依赖时也能导入。"""
    sys.modules.pop("websockets", None)
    _load_script()
    assert "websockets" not in sys.modules


# --------------------------------------------------------------------------- CLI 参数校验与失败处理


def test_parser_rejects_non_positive_max_bars():
    for bad in ("0", "-1", "abc"):
        with pytest.raises(SystemExit):
            bl.build_parser().parse_args(["--max-bars", bad])
    assert bl.build_parser().parse_args(["--max-bars", "3"]).max_bars == 3


def test_parser_rejects_non_positive_or_non_finite_duration():
    for bad in ("0", "-1", "nan", "inf", "-inf", "abc"):
        with pytest.raises(SystemExit):
            bl.build_parser().parse_args(["--duration", bad])
    assert bl.build_parser().parse_args(["--duration", "1.5"]).duration == 1.5


def test_parser_rejects_empty_csv_path():
    for bad in ("", "   "):
        with pytest.raises(SystemExit):
            bl.build_parser().parse_args(["--csv", bad])


def _ok_fetch(n: int = 5):
    """模拟 REST：不带时间窗时返回 n 根启动数据，带时间窗时补齐区间。"""

    def fetch(symbol, interval, *, limit=None, start_ms=None, end_ms=None):
        if start_ms is None:
            return _klines(n)
        return [_kline(t) for t in range(start_ms, end_ms + 1, MINUTE_MS)]

    return fetch


def _never_stream(symbol, interval):
    raise AssertionError("不应走到 WebSocket 主循环")


def test_main_reports_no_persistence_with_no_csv():
    lines = []
    rc = bl.main(
        ["--no-csv", "--max-bars", "1"],
        fetch=_ok_fetch(),
        stream_factory=lambda s, i: iter([_ws_event(T0 + 5 * MINUTE_MS, closed=True)]),
        sink=lines.append,
    )
    assert rc == 0
    assert any("不落盘" in line for line in lines), lines


def test_main_returns_zero_when_interrupted_during_bootstrap():
    lines = []

    def fetch(symbol, interval, **kwargs):
        raise KeyboardInterrupt

    assert bl.main(["--no-csv"], fetch=fetch, stream_factory=_never_stream, sink=lines.append) == 0
    assert any(bl._CTRL_C_MSG in line for line in lines), lines


def test_main_returns_one_on_rest_failure_and_shows_truncated_body():
    import types

    import requests

    lines = []

    def fetch(symbol, interval, **kwargs):
        raise requests.HTTPError("418 teapot", response=types.SimpleNamespace(text="X" * 500))

    assert bl.main(["--no-csv"], fetch=fetch, stream_factory=_never_stream, sink=lines.append) == 1
    failed = [line for line in lines if line.startswith(bl._WARN)]
    assert len(failed) == 1, lines
    assert "teapot" in failed[0]
    assert "X" * 200 in failed[0] and "X" * 201 not in failed[0]  # 只截前 200 字符


def test_main_returns_one_on_rest_failure_without_response_body():
    import requests

    lines = []

    def fetch(symbol, interval, **kwargs):
        raise requests.ConnectionError("DNS 解析失败")

    assert bl.main(["--no-csv"], fetch=fetch, stream_factory=_never_stream, sink=lines.append) == 1
    assert any(line.startswith(bl._WARN) and "DNS 解析失败" in line for line in lines), lines


def test_main_returns_one_when_engine_failure_limit_reached():
    lines = []

    def fetch(symbol, interval, *, limit=None, start_ms=None, end_ms=None):
        if start_ms is None:
            return _klines(5)
        raise RuntimeError("REST 一直失败")

    events = [_ws_event(T0 + (6 + 2 * i) * MINUTE_MS, closed=True) for i in range(bl.MAX_ENGINE_FAILURES)]
    rc = bl.main(["--no-csv"], fetch=fetch, stream_factory=lambda s, i: iter(events), sink=lines.append)

    assert rc == 1
    assert any(line.startswith(bl._WARN) and "连续" in line for line in lines), lines


def test_main_reports_missing_websockets_dependency_instead_of_traceback():
    lines = []

    def factory(symbol, interval):
        raise ImportError("No module named 'websockets'")

    assert bl.main(["--no-csv"], fetch=_ok_fetch(), stream_factory=factory, sink=lines.append) == 1
    hint = [line for line in lines if line.startswith(bl._WARN)]
    assert len(hint) == 1, lines
    assert "websockets" in hint[0] and "--with websockets" in hint[0]
    # 提示里的命令必须能从仓库根目录直接粘贴执行（测试就是从根目录跑的）
    assert str(Path("scripts") / "binance_live.py") in hint[0], hint[0]


def test_main_returns_one_when_bootstrap_data_is_invalid():
    """空回补 / CSV 与当前任务不匹配等都会抛 ValueError，应给一行说明而不是 traceback。"""
    lines = []

    def fetch(symbol, interval, **kwargs):
        return []

    assert bl.main(["--no-csv"], fetch=fetch, stream_factory=_never_stream, sink=lines.append) == 1
    assert len([line for line in lines if line.startswith(bl._WARN)]) == 1, lines


def test_main_reports_missing_requests_dependency(monkeypatch):
    """requests 也是惰性导入，缺它时同样应走友好提示而不是 traceback。"""
    monkeypatch.setitem(sys.modules, "requests", None)
    lines = []

    assert bl.main(["--no-csv"], fetch=_ok_fetch(), stream_factory=_never_stream, sink=lines.append) == 1
    assert any(line.startswith(bl._WARN) and "缺少依赖" in line for line in lines), lines


def test_main_installs_and_restores_sigterm_handler():
    before = signal.getsignal(signal.SIGTERM)
    seen = []

    def factory(symbol, interval):
        seen.append(signal.getsignal(signal.SIGTERM))
        if len(seen) == 1:
            signal.raise_signal(signal.SIGTERM)  # 真发一次信号：应立刻打断退避并退出
            return iter([])
        raise KeyboardInterrupt  # 兜底：万一 stop 没生效，也别让测试进程被下一次 SIGTERM 打死

    started = time.monotonic()
    assert bl.main(["--no-csv"], fetch=_ok_fetch(), stream_factory=factory, sink=[].append) == 0
    elapsed = time.monotonic() - started

    assert len(seen) == 1  # 收到 SIGTERM 后没有再重连
    assert seen[0] is not before  # 运行期间挂上了自己的 SIGTERM 处理器
    assert elapsed < 1.0, elapsed  # 退避等待被立刻打断，而不是睡满 1 秒
    assert signal.getsignal(signal.SIGTERM) is before  # 退出后还原，不污染宿主进程
