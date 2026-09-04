# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "czsc>=1.0.1",
#   "requests>=2.24",
#   "websockets>=13",
# ]
# ///
"""Binance 现货公开行情 → CZSC 实时缠论分析（第一版）。

- REST 回补最近 N 根已收盘 K 线，初始化 CZSC 分析器
- WebSocket 只在 ``k.x == true``（K 线收盘）时增量更新
- 自动去重、检测断线缺口并用 REST 补齐
- 持续追加保存到 CSV
- 仅使用公开行情：不接账户、不保存密钥、不下单

运行方式（二选一）::

    uv run scripts/binance_live.py                       # PEP 723 隔离环境，czsc 取自 PyPI
    uv run --no-sync --with websockets python scripts/binance_live.py   # 复用项目虚拟环境（本地开发版 czsc）

命令行参数::

    --symbol BTCUSDT     交易对（自动转大写），默认 BTCUSDT
    --interval 1m        K 线周期，取值 1m/5m/15m/30m/1h/4h/1d，默认 1m
    --limit 1000         启动时 REST 回补的根数，1~1000，默认 1000
    --csv PATH           CSV 落盘路径，默认 data/<SYMBOL>_<interval>.csv
    --no-csv             不落盘，只在内存里分析（与 --csv 互斥）
    --max-bars N         增量处理 N 根后退出，默认一直运行
    --duration SECONDS   运行指定秒数后退出，默认一直运行

按 Ctrl+C 或收到 SIGTERM 可随时安全退出（退避等待也会被立刻打断）：退出提示会立刻打印，
随后才关闭连接，且关闭握手最多等 2 秒（再按一次 Ctrl+C 会直接强制退出）；断线会按 1s → 2s → … →
60s 的指数退避自动重连，重连后的第一根收盘 K 线会触发 REST 回补；回补失败会告警并跳过，
留下缺口（不会自动重试）。
连续 10 根 K 线处理失败会判定为持续性故障并以退出码 1 退出；缺少 ``websockets`` 这类永久性
配置错误会直接报错退出，不会反复重连。

时间约定：``dt`` 为 K 线**收盘时间**，tz-naive 且按 UTC 解释（与 RawBar 的约定一致）。
"""

from __future__ import annotations

import argparse
import csv
import datetime as _dt
import json
import math
import os
import signal
import stat as _stat
import tempfile
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from czsc import CZSC, Freq, RawBar

BINANCE_REST = "https://api.binance.com"
BINANCE_WS = "wss://stream.binance.com:9443/ws"

_INTERVAL_UNIT_MS = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
_INTERVAL_FREQ = {
    "1m": Freq.F1,
    "5m": Freq.F5,
    "15m": Freq.F15,
    "30m": Freq.F30,
    "1h": Freq.F60,
    "4h": Freq.F240,
    "1d": Freq.D,
}

CSV_COLUMNS = ["dt", "symbol", "open", "close", "high", "low", "vol", "amount"]
_DT_FMT = "%Y-%m-%d %H:%M:%S"
_WARN = "警告："
_BANNER = "仅公开行情，不接账户、不保存密钥、不下单"
_CTRL_C_MSG = "收到 Ctrl+C，安全退出"
_CTRL_C_AGAIN_MSG = "再次收到 Ctrl+C，强制退出"
_SERVER_CLOSED_MSG = "连接已被服务端关闭"
_CONNECTING_TMPL = "连接 {symbol}@kline_{interval} …"

RECONNECT_INITIAL_S = 1.0  # 断线重连的初始退避
RECONNECT_MAX_S = 60.0  # 退避上限
RECV_TIMEOUT_S = 90.0  # 1m kline 每 ~2 秒推一次，静默超过 90 秒视为死连接
CLOSE_TIMEOUT_S = 2.0  # 关闭握手上限：websockets 默认 10 秒，退出时不值得为它干等
MIN_LIMIT = 1  # Binance klines 单次请求根数下限
MAX_LIMIT = 1000  # ……上限
MAX_ENGINE_FAILURES = 10  # 连续处理失败上限：再多就不是偶发问题了

FetchRange = Callable[[int, int], "list[Kline]"]
Sink = Callable[[str], None]
HttpGet = Callable[..., Any]
StreamFactory = Callable[[str, str], "Iterator[dict[str, Any]]"]


class EngineFailureLimit(RuntimeError):
    """连续 :data:`MAX_ENGINE_FAILURES` 次处理 K 线失败：继续空转只会掩盖故障，直接退出。"""


def _log(msg: str) -> None:
    """默认日志 sink：以 ``YYYY-MM-DD HH:MM:SS`` 的 **UTC** 时间戳为前缀，并立即 flush。

    前缀只加在这个默认 sink 里（重定向到文件 / 管道时也不丢日志）；注入自定义 sink 的调用方
    拿到的仍是原始文本。摘要行自带的 ``UTC`` 标注指的是 K 线收盘时间，与本前缀不是同一个时刻。
    """
    stamp = _dt.datetime.now(tz=_dt.timezone.utc).strftime(_DT_FMT)
    print(f"{stamp} {msg}", flush=True)


def interval_ms(interval: str) -> int:
    """把 Binance 周期字符串（1m / 15m / 1h / 1d）换算为毫秒。"""
    unit = interval[-1:]
    if unit not in _INTERVAL_UNIT_MS or not interval[:-1].isdigit():
        raise ValueError(f"不支持的周期: {interval!r}")
    value = int(interval[:-1])
    if value <= 0:
        raise ValueError(f"周期倍数必须为正整数: {interval!r}")
    return value * _INTERVAL_UNIT_MS[unit]


def interval_freq(interval: str) -> Freq:
    """把 Binance 周期字符串映射为 CZSC 的 Freq 枚举。"""
    try:
        return _INTERVAL_FREQ[interval]
    except KeyError as e:
        raise ValueError(f"暂不支持映射到 Freq 的周期: {interval!r}") from e


@dataclass(frozen=True)
class Kline:
    """一根已收盘的 Binance K 线（价格 / 量全部为 float，时间为毫秒开盘时间）。"""

    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    quote_volume: float


def kline_from_rest_row(row: list[Any]) -> Kline:
    """解析 ``GET /api/v3/klines`` 返回的单行 12 元素数组。"""
    return Kline(
        open_time_ms=int(row[0]),
        open=float(row[1]),
        high=float(row[2]),
        low=float(row[3]),
        close=float(row[4]),
        volume=float(row[5]),
        quote_volume=float(row[7]),
    )


def kline_from_ws_event(msg: dict[str, Any]) -> Kline | None:
    """解析 ``<symbol>@kline_<interval>`` 推送；只有 ``k.x == true`` 的收盘 K 线才返回。"""
    if msg.get("e") != "kline":
        return None
    k = msg["k"]
    if not k.get("x"):
        return None
    return Kline(
        open_time_ms=int(k["t"]),
        open=float(k["o"]),
        high=float(k["h"]),
        low=float(k["l"]),
        close=float(k["c"]),
        volume=float(k["v"]),
        quote_volume=float(k["q"]),
    )


def close_time_utc(k: Kline, interval: str) -> _dt.datetime:
    """K 线收盘时间 = 开盘时间 + 周期，返回 tz-naive 的 UTC datetime。"""
    ms = k.open_time_ms + interval_ms(interval)
    return _dt.datetime.fromtimestamp(ms / 1000, tz=_dt.timezone.utc).replace(tzinfo=None)


def kline_to_bar(k: Kline, *, symbol: str, interval: str, bar_id: int) -> RawBar:
    """把 Kline 转成 CZSC 的 RawBar，``dt`` 为 naive UTC 收盘时间。"""
    return RawBar(
        symbol=symbol,
        dt=close_time_utc(k, interval),
        freq=interval_freq(interval),
        open=k.open,
        close=k.close,
        high=k.high,
        low=k.low,
        vol=k.volume,
        amount=k.quote_volume,
        id=bar_id,
    )


def _now_ms() -> int:
    return int(_dt.datetime.now(tz=_dt.timezone.utc).timestamp() * 1000)


def _default_http_get(url: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> Any:
    import requests

    return requests.get(url, params=params, timeout=timeout)


def fetch_closed_klines(
    symbol: str,
    interval: str,
    *,
    limit: int = 1000,
    start_ms: int | None = None,
    end_ms: int | None = None,
    http_get: HttpGet = _default_http_get,
    now_ms: int | None = None,
    timeout: float = 10.0,
) -> list[Kline]:
    """通过 REST 拉取已收盘 K 线，按开盘时间升序返回；仍在进行中的最后一根会被丢弃。

    ``start_ms`` / ``end_ms`` 对应 Binance 的 ``startTime`` / ``endTime``（毫秒），用于补缺口。
    ``http_get`` / ``now_ms`` 可注入，便于用模拟数据测试。

    不传 ``end_ms`` 时会自动把 ``endTime`` 压到「最后一根已收盘 K 线的收盘时刻」：Binance 在不给
    时间窗时**一定**会带上正在形成的那根，否则 ``limit`` 根里只有 ``limit - 1`` 根是已收盘的。
    客户端的 ``open + step <= now`` 过滤保留为兜底（本地时钟走快时仍能挡住脏 K 线——它一旦进了
    CZSC，后续同 ``open_time`` 的收盘推送会被当成重复丢弃，那根就永远冻住了）。
    """
    now = now_ms if now_ms is not None else _now_ms()
    step = interval_ms(interval)
    params: dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": limit}
    if start_ms is not None:
        params["startTime"] = start_ms
    params["endTime"] = end_ms if end_ms is not None else (now // step) * step - 1
    resp = http_get(f"{BINANCE_REST}/api/v3/klines", params=params, timeout=timeout)
    resp.raise_for_status()

    klines = [kline_from_rest_row(row) for row in resp.json()]
    return [k for k in klines if k.open_time_ms + step <= now]


def _fmt_ms(ms: int) -> str:
    """毫秒时间戳 → naive UTC 文本。"""
    return _dt.datetime.fromtimestamp(ms / 1000, tz=_dt.timezone.utc).strftime(_DT_FMT)


def _csv_row(k: Kline, *, symbol: str, interval: str) -> list[str]:
    """把一根 K 线写成 czsc 标准 K 线格式的一行（``dt`` 为 naive UTC 收盘时间）。"""
    return [
        close_time_utc(k, interval).strftime(_DT_FMT),
        symbol,
        repr(k.open),
        repr(k.close),
        repr(k.high),
        repr(k.low),
        repr(k.volume),
        repr(k.quote_volume),
    ]


def _parse_csv_row(row: dict[str, str], step: int) -> tuple[str, Kline]:
    """解析一行 CSV；字段缺失 / 格式非法时抛 ValueError / TypeError / KeyError。"""
    symbol = row["symbol"]
    if symbol is None:
        raise TypeError("symbol 字段缺失")
    close_dt = _dt.datetime.strptime(row["dt"], _DT_FMT).replace(tzinfo=_dt.timezone.utc)
    return symbol, Kline(
        open_time_ms=int(close_dt.timestamp() * 1000) - step,
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["vol"]),
        quote_volume=float(row["amount"]),
    )


def read_csv_klines(path: Path, interval: str, *, symbol: str, warn: Sink = _log) -> list[Kline]:
    """读回 :func:`_csv_row` 写出的 CSV；``open_time_ms = 收盘时间 - 周期``。

    单行解析失败只警告并跳过（一行脏数据不该让每次重启都崩）；但 ``symbol`` 不匹配或
    ``dt`` 与周期不对齐属于「文件根本不是这个任务的历史」，直接抛 ValueError。
    """
    step = interval_ms(interval)
    klines: list[Kline] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:  # 0 字节文件
            return []
        if list(reader.fieldnames) != CSV_COLUMNS:
            raise ValueError(f"{path} 的表头为 {reader.fieldnames}，期望 {CSV_COLUMNS}")
        for row in reader:
            lineno = reader.line_num  # DictReader 会跳过空行，不能用计数器推算行号
            try:
                row_symbol, k = _parse_csv_row(row, step)
            except (ValueError, TypeError, KeyError) as e:
                warn(f"{_WARN}{path} 第 {lineno} 行解析失败，已跳过：{e}")
                continue
            if row_symbol != symbol:
                raise ValueError(f"{path} 第 {lineno} 行的 symbol 为 {row_symbol!r}，与当前任务 {symbol!r} 不一致")
            if k.open_time_ms % step != 0:
                raise ValueError(f"{path} 第 {lineno} 行的 dt={row['dt']!r} 与周期 {interval} 不对齐")
            klines.append(k)
    return klines


class LiveEngine:
    """把逐根收盘 K 线增量喂给 CZSC 的同步引擎：去重、补缺口、落盘、输出摘要。

    引擎自身不访问网络：缺口回补通过注入的 ``fetch_range(start_ms, end_ms) -> list[Kline]`` 完成。
    """

    def __init__(
        self,
        symbol: str,
        interval: str,
        *,
        csv_path: Path | None,
        fetch_range: FetchRange,
        sink: Sink = _log,
    ):
        interval_freq(interval)  # 尽早校验：无法映射到 Freq 的周期直接拒绝
        self.symbol = symbol
        self.interval = interval
        self.step = interval_ms(interval)
        self.csv_path = csv_path
        self.fetch_range = fetch_range
        self.sink = sink
        self.czsc: CZSC | None = None
        self.last_open_time_ms: int = -1
        self.last_id: int = -1

    # ---------------------------------------------------------------- 落盘

    def _write(self, klines: list[Kline], *, mode: str) -> None:
        """``mode="w"`` 全量重写（先写同目录临时文件再 ``os.replace``，避免截断后崩溃丢历史）；
        ``mode="a"`` 追加单批，不写表头。"""
        if self.csv_path is None:
            return
        rows = [_csv_row(k, symbol=self.symbol, interval=self.interval) for k in klines]
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "a":
            # 文件可能在运行中被删除 / 轮转：重建时必须补表头，否则下次启动会把首行数据当成表头吃掉
            fresh = not self.csv_path.exists() or self.csv_path.stat().st_size == 0
            with self.csv_path.open("a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if fresh:
                    writer.writerow(CSV_COLUMNS)
                writer.writerows(rows)
            return
        mode_bits = _stat.S_IMODE(self.csv_path.stat().st_mode) if self.csv_path.exists() else None
        fd, tmp_name = tempfile.mkstemp(dir=self.csv_path.parent, prefix=f".{self.csv_path.name}.", suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(CSV_COLUMNS)
                writer.writerows(rows)
                f.flush()
                os.fsync(f.fileno())
            os.chmod(tmp, mode_bits if mode_bits is not None else 0o644)
            os.replace(tmp, self.csv_path)
        finally:
            tmp.unlink(missing_ok=True)

    # ---------------------------------------------------------------- 缺口回补

    def _warn_hole(self, from_open_ms: int, to_open_ms: int) -> None:
        n = (to_open_ms - from_open_ms) // self.step
        self.sink(
            f"{_WARN}{self.symbol} {self.interval} 缺失 {n} 根 K 线，"
            f"收盘时间 {_fmt_ms(from_open_ms + self.step)} ~ {_fmt_ms(to_open_ms)} UTC"
        )

    def _warn_holes(self, klines: list[Kline], *, expected_start: int | None = None) -> None:
        """检查一段 K 线的开盘时间是否逐根连续，每个空洞打印一条告警（静默丢数据是最难查的 bug）。"""
        if not klines:
            return
        if expected_start is not None and klines[0].open_time_ms != expected_start:
            self._warn_hole(expected_start, klines[0].open_time_ms)
        for prev, cur in zip(klines, klines[1:], strict=False):
            if prev.open_time_ms + self.step != cur.open_time_ms:
                self._warn_hole(prev.open_time_ms + self.step, cur.open_time_ms)

    def _page_missing(self, start_open_ms: int, until_open_ms: int) -> Iterator[Kline]:
        """按页拉取 ``[start_open_ms, until_open_ms)`` 区间内缺失的 K 线（支持超过单页上限的缺口）。"""
        expected = start_open_ms
        while expected < until_open_ms:
            batch = sorted(self.fetch_range(expected, until_open_ms - 1), key=lambda k: k.open_time_ms)
            batch = [k for k in batch if expected <= k.open_time_ms < until_open_ms]
            if not batch:
                miss_from = _fmt_ms(expected + self.step)
                miss_to = _fmt_ms(until_open_ms)
                self.sink(f"{_WARN}{self.symbol} {self.interval} 缺口 {miss_from} ~ {miss_to} UTC 未能回补，已跳过")
                return
            self._warn_holes(batch, expected_start=expected)
            yield from batch
            expected = batch[-1].open_time_ms + self.step

    # ---------------------------------------------------------------- 初始化

    def bootstrap(self, klines: list[Kline]) -> None:
        """用 REST 回补的 K 线（可与历史 CSV 合并）初始化 CZSC 分析器。

        注意：CSV 是跨重启累积的全量历史，会无限增长，且每次启动都整份读回内存；
        长期运行需要外部定期归档 / 截断，本脚本不做自动轮转。
        """
        if not klines:
            raise ValueError("bootstrap 需要至少一根 K 线")

        history: list[Kline] = []
        if self.csv_path is not None and self.csv_path.exists():
            history = read_csv_klines(self.csv_path, self.interval, symbol=self.symbol, warn=self.sink)

        merged = {k.open_time_ms: k for k in history}
        if history:
            hole_start = max(merged) + self.step
            hole_end = min(k.open_time_ms for k in klines)
            if hole_start < hole_end:
                missing = (hole_end - hole_start) // self.step
                self.sink(
                    f"检测到缺口：{self.symbol} {self.interval} CSV 历史与本次回补之间缺少约 {missing} 根 K 线，"
                    f"收盘时间 {_fmt_ms(hole_start + self.step)} ~ {_fmt_ms(hole_end)} UTC，开始回补"
                )
                for k in self._page_missing(hole_start, hole_end):
                    merged[k.open_time_ms] = k
        merged.update({k.open_time_ms: k for k in klines})  # REST 数据优先
        ordered = [merged[t] for t in sorted(merged)]
        self._warn_holes(ordered)

        bars = [kline_to_bar(k, symbol=self.symbol, interval=self.interval, bar_id=i) for i, k in enumerate(ordered)]
        self.czsc = CZSC(bars)
        self.last_open_time_ms = ordered[-1].open_time_ms
        self.last_id = len(ordered) - 1
        self._write(ordered, mode="w")
        last_dt = close_time_utc(ordered[-1], self.interval).strftime(_DT_FMT)
        self.sink(f"已回补 {len(ordered)} 根 {self.symbol} {self.interval} K 线，最新收盘时间 {last_dt} UTC")

    # ---------------------------------------------------------------- 增量更新

    def _require_czsc(self) -> CZSC:
        if self.czsc is None:
            raise RuntimeError("请先调用 bootstrap 初始化引擎")
        return self.czsc

    def _summary(self, bar: RawBar) -> str:
        """一行摘要。注意 ``bi`` 受 CZSC ``max_bi_num``（默认 50）限制、``bars_raw`` 也会被裁剪，
        所以笔数量增长到上限后会稳定在那里，不代表分析停止。"""
        czsc = self._require_czsc()
        bi_list = czsc.bi_list
        last_bi = bi_list[-1].direction.value if bi_list else "-"
        return (
            f"{bar.dt.strftime(_DT_FMT)} UTC close={bar.close} "
            f"fx={len(czsc.fx_list)} bi={len(bi_list)} last_bi={last_bi}"
        )

    def _apply(self, k: Kline, *, emit: bool = True) -> None:
        czsc = self._require_czsc()
        bar = kline_to_bar(k, symbol=self.symbol, interval=self.interval, bar_id=self.last_id + 1)
        czsc.update(bar)
        self.last_open_time_ms = k.open_time_ms  # CZSC 已接受，游标先推进，落盘失败不回滚
        self.last_id = bar.id
        try:
            self._write([k], mode="a")
        except OSError as e:
            self.sink(f"{_WARN}写入 CSV 失败，该根 K 线（{bar.dt.strftime(_DT_FMT)} UTC）不会再补写：{e}")
        if emit:
            self.sink(self._summary(bar))

    def on_kline(self, k: Kline) -> bool:
        """喂入一根已收盘 K 线；重复 / 乱序返回 False，正常（含先补缺口）应用返回 True。"""
        self._require_czsc()
        if k.open_time_ms <= self.last_open_time_ms:
            return False
        if k.open_time_ms > self.last_open_time_ms + self.step:
            self._fill_gap(k.open_time_ms)
        self._apply(k)
        return True

    def _fill_gap(self, until_open_ms: int) -> None:
        """把 ``last_open_time_ms`` 到 ``until_open_ms`` 之间缺失的 K 线补齐并逐根应用。

        补齐的 K 线不逐条打印摘要（断线几小时会刷屏），结束后只汇报一行。
        """
        start = self.last_open_time_ms + self.step
        missing = (until_open_ms - start) // self.step
        self.sink(
            f"检测到缺口：{self.symbol} {self.interval} 缺少约 {missing} 根 K 线，"
            f"收盘时间 {_fmt_ms(start + self.step)} ~ {_fmt_ms(until_open_ms)} UTC，开始回补"
        )
        filled = 0
        for k in self._page_missing(start, until_open_ms):
            self._apply(k, emit=False)
            filled += 1
        if filled:
            self.sink(f"回补完成 {filled} 根，最新收盘时间 {_fmt_ms(self.last_open_time_ms + self.step)} UTC")


# ---------------------------------------------------------------------------- 主循环


def run(
    engine: LiveEngine,
    *,
    stream_factory: StreamFactory,
    stop: threading.Event | None = None,
    max_bars: int | None = None,
    duration_s: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> int:
    """把 WebSocket 消息流逐条喂给已初始化的引擎，断线按指数退避自动重连。

    返回本次 **WebSocket 实时**应用（去重后进入 CZSC）的 K 线根数；缺口回补进去的不计入。
    停止条件（``stop`` / ``max_bars`` / ``duration_s``）在每条消息之后、以及每次建连之前
    检查。给了 ``stop`` 时退避改用
    ``stop.wait(delay)``，SIGTERM / Ctrl+C 不必等满 60 秒；否则用注入的 ``sleep``。

    重连本身不做补数据：下一根收盘 K 线会被引擎识别为缺口并自动 REST 回补。连续
    :data:`MAX_ENGINE_FAILURES` 次处理失败会抛 :class:`EngineFailureLimit`。
    """
    engine._require_czsc()  # 未 bootstrap 直接拒绝，避免连上以后才发现没法处理

    applied = 0
    failures = 0
    delay = RECONNECT_INITIAL_S
    started = clock()

    def should_stop() -> bool:
        if stop is not None and stop.is_set():
            return True
        if max_bars is not None and applied >= max_bars:
            return True
        return duration_s is not None and clock() - started >= duration_s

    try:
        while not should_stop():
            engine.sink(_CONNECTING_TMPL.format(symbol=engine.symbol, interval=engine.interval))
            stream: Iterator[dict[str, Any]] | None = None
            interrupted = False
            try:
                stream = stream_factory(engine.symbol, engine.interval)  # 建连失败也算断线，一并退避
                for msg in stream:
                    try:
                        k = kline_from_ws_event(msg)
                    except (ValueError, KeyError, TypeError) as e:  # 坏帧跳过即可，不必重连
                        engine.sink(f"{_WARN}跳过无法解析的推送：{e!r}")
                        k = None
                    if k is not None:
                        try:
                            if engine.on_kline(k):
                                applied += 1
                                delay = RECONNECT_INITIAL_S  # 只有真正应用过 K 线才重置退避
                            failures = 0
                        except Exception as e:  # 引擎异常（如 REST 回补失败）不算断线，下一根会自愈
                            failures += 1
                            engine.sink(
                                f"{_WARN}处理 K 线失败，已跳过（缺口会在下一根自动回补）"
                                f"[{failures}/{MAX_ENGINE_FAILURES}]：{e!r}"
                            )
                            if failures >= MAX_ENGINE_FAILURES:
                                raise EngineFailureLimit(f"连续 {failures} 根 K 线处理失败，放弃继续运行：{e!r}") from e
                    if should_stop():
                        return applied
                # 迭代正常结束 = 服务端主动断开（Binance 每 24 小时会断一次），同样走退避路径
                engine.sink(f"{_SERVER_CLOSED_MSG}，{delay:g} 秒后重连")
            except (EngineFailureLimit, ImportError):
                raise  # 引擎持续故障 / 缺依赖都是永久性问题，重连解决不了，直接抛给调用方
            except KeyboardInterrupt:
                # 必须赶在下面 finally 的关闭握手之前打印：握手要等最多 CLOSE_TIMEOUT_S 秒，
                # 交给外层兜底的话用户按完 Ctrl+C 只能对着空屏幕，以为进程卡死了。
                engine.sink(_CTRL_C_MSG)
                interrupted = True
            except Exception as e:
                engine.sink(f"{_WARN}连接中断，{delay:g} 秒后重连：{e!r}")
            finally:
                close = getattr(stream, "close", None) if stream is not None else None
                if close is not None:
                    try:
                        close()  # 生成器持有 socket，必须显式关闭，不能等 GC
                    except KeyboardInterrupt:  # 关闭握手期间又按了一次 Ctrl+C：别甩 traceback
                        engine.sink(_CTRL_C_AGAIN_MSG if interrupted else _CTRL_C_MSG)
                        interrupted = True
                    except Exception as e:
                        engine.sink(f"{_WARN}关闭连接失败（已忽略）：{e!r}")
            if interrupted:  # 用局部标志而不是 finally 里 return（B012）
                return applied
            wait_s = delay
            if duration_s is not None:  # 退避不能睡过头，否则 --duration 会被整整拖长一个退避周期
                wait_s = min(delay, max(0.0, duration_s - (clock() - started)))
            if stop is not None:
                if stop.wait(wait_s):  # 可中断的退避：SIGTERM / Ctrl+C 不必等满 60 秒
                    return applied
            else:
                sleep(wait_s)
            delay = min(delay * 2, RECONNECT_MAX_S)
        return applied
    except KeyboardInterrupt:
        engine.sink(_CTRL_C_MSG)
        return applied


def stream_url(symbol: str, interval: str, url: str = BINANCE_WS) -> str:
    """拼出单一 stream 的 WebSocket 地址；Binance 的 stream 名一律小写。"""
    return f"{url}/{symbol.lower()}@kline_{interval}"


def binance_kline_stream(
    symbol: str,
    interval: str,
    *,
    url: str = BINANCE_WS,
    recv_timeout_s: float = RECV_TIMEOUT_S,
    connect: Callable[[str], Any] | None = None,
    closed_ok: type[BaseException] | tuple[type[BaseException], ...] | None = None,
) -> Iterator[dict[str, Any]]:
    """连接 Binance 现货公开 WebSocket，逐条 yield 解析后的 JSON 消息。

    ``connect`` / ``closed_ok`` 默认从 ``websockets`` 惰性导入（模块本身在未安装该依赖的
    环境里依旧可导入），测试可注入假实现，无需联网。

    服务端**正常**关闭（Binance 每 24 小时一次，``ConnectionClosedOK``）会让生成器正常结束，
    从而走 :func:`run` 的「服务端关闭」分支；其余异常与 ``TimeoutError`` 一律向上抛出，由
    :func:`run` 当作断线告警并重连。
    """
    if connect is None or closed_ok is None:
        from websockets.exceptions import ConnectionClosedOK
        from websockets.sync.client import connect as ws_connect

        connect = connect if connect is not None else ws_connect
        closed_ok = closed_ok if closed_ok is not None else ConnectionClosedOK

    with connect(stream_url(symbol, interval, url), close_timeout=CLOSE_TIMEOUT_S) as ws:
        while True:
            try:
                raw = ws.recv(timeout=recv_timeout_s)
            except closed_ok:
                return
            yield json.loads(raw)


# ---------------------------------------------------------------------------- 命令行


def default_csv_path(symbol: str, interval: str) -> Path:
    """默认落盘路径：``data/<SYMBOL>_<interval>.csv``。"""
    return Path("data") / f"{symbol}_{interval}.csv"


def _interval_arg(value: str) -> str:
    """argparse 类型校验：周期必须能映射到 CZSC 的 Freq。"""
    try:
        interval_freq(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e
    return value


def _positive_int_arg(value: str) -> int:
    """argparse 类型校验：必须是正整数。"""
    try:
        n = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"必须是整数，收到 {value!r}") from e
    if n <= 0:
        raise argparse.ArgumentTypeError(f"必须是正整数，收到 {value!r}")
    return n


def _positive_seconds_arg(value: str) -> float:
    """argparse 类型校验：必须是有限的正秒数（拒绝 nan / inf / 负数）。"""
    try:
        seconds = float(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"必须是数字，收到 {value!r}") from e
    if not math.isfinite(seconds) or seconds <= 0:
        raise argparse.ArgumentTypeError(f"必须是有限的正秒数，收到 {value!r}")
    return seconds


def _csv_path_arg(value: str) -> Path:
    """argparse 类型校验：路径不能是空串 / 纯空白（否则会静默落到当前目录）。"""
    if not value.strip():
        raise argparse.ArgumentTypeError("路径不能为空；不想落盘请用 --no-csv")
    return Path(value)


def _limit_arg(value: str) -> int:
    """argparse 类型校验：Binance 单次 klines 请求上限为 1000。"""
    try:
        n = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"--limit 必须是整数，收到 {value!r}") from e
    if not MIN_LIMIT <= n <= MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"--limit 必须在 {MIN_LIMIT}~{MAX_LIMIT} 之间，收到 {value!r}")
    return n


def build_parser() -> argparse.ArgumentParser:
    """构造命令行解析器（非法周期 / limit 在解析阶段就报错）。"""
    parser = argparse.ArgumentParser(description=f"Binance 现货公开行情 → CZSC 实时缠论分析（{_BANNER}）")
    parser.add_argument("--symbol", default="BTCUSDT", type=str.upper, help="交易对，默认 BTCUSDT")
    parser.add_argument("--interval", default="1m", type=_interval_arg, help="K 线周期，默认 1m")
    parser.add_argument("--limit", default=MAX_LIMIT, type=_limit_arg, help=f"启动时 REST 回补根数，默认 {MAX_LIMIT}")
    persist = parser.add_mutually_exclusive_group()
    persist.add_argument(
        "--csv", default=None, type=_csv_path_arg, help="CSV 落盘路径，默认 data/<SYMBOL>_<interval>.csv"
    )
    persist.add_argument("--no-csv", action="store_true", help="不落盘，只在内存里分析")
    parser.add_argument("--max-bars", default=None, type=_positive_int_arg, help="实时处理指定根数后退出，默认一直运行")
    parser.add_argument("--duration", default=None, type=_positive_seconds_arg, help="运行指定秒数后退出，默认一直运行")
    return parser


def _script_display_path() -> str:
    """展示用的脚本路径：在当前工作目录之下就用相对路径（提示里的命令可直接粘贴执行），否则用绝对路径。"""
    path = Path(__file__).resolve()
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _install_sigterm_handler(stop: threading.Event) -> Callable[[], None]:
    """把 SIGTERM 接到 ``stop`` 上（容器 / systemd 停服时优雅退出），返回还原函数。

    非主线程或不支持信号的平台注册不了，此时退化为空操作，不影响其他退出方式。
    """
    try:
        previous = signal.signal(signal.SIGTERM, lambda *_: stop.set())
    except ValueError:
        return lambda: None
    if previous is None:  # 旧处理器来自 C 层，signal.signal(SIGTERM, None) 会 TypeError
        return lambda: None
    return lambda: signal.signal(signal.SIGTERM, previous)


def main(
    argv: list[str] | None = None,
    *,
    fetch: Callable[..., list[Kline]] = fetch_closed_klines,
    stream_factory: StreamFactory = binance_kline_stream,
    sink: Sink = _log,
) -> int:
    """命令行入口：REST 回补 → 初始化引擎 → WebSocket 主循环。正常结束返回 0，故障返回 1。"""
    args = build_parser().parse_args(argv)
    symbol: str = args.symbol
    interval: str = args.interval
    if args.no_csv:
        csv_path = None
    elif args.csv is not None:
        csv_path = args.csv
    else:
        csv_path = default_csv_path(symbol, interval)

    sink(f"{symbol} {interval} 实时缠论：{_BANNER}")
    sink(f"落盘路径：{csv_path.resolve()}" if csv_path is not None else "落盘路径：不落盘（--no-csv）")

    stop = threading.Event()
    restore_sigterm = _install_sigterm_handler(stop)
    try:
        # 延迟到这里才导入：只 import 本模块（如测试收集）不需要装 requests；缺它时会被下面的
        # ``except ImportError`` 接住 —— 该分支必须排在 ``except RequestException`` 之前，
        # 否则导入失败时求值 RequestException 会 NameError。
        from requests import RequestException

        klines = fetch(symbol, interval, limit=args.limit)
        engine = LiveEngine(
            symbol,
            interval,
            csv_path=csv_path,
            fetch_range=lambda start_ms, end_ms: fetch(symbol, interval, start_ms=start_ms, end_ms=end_ms),
            sink=sink,
        )
        engine.bootstrap(klines)
        n = run(
            engine,
            stream_factory=stream_factory,
            stop=stop,
            max_bars=args.max_bars,
            duration_s=args.duration,
        )
    except KeyboardInterrupt:
        sink(_CTRL_C_MSG)
        return 0
    except EngineFailureLimit as e:
        sink(f"{_WARN}{e}")
        return 1
    except ImportError as e:
        script = _script_display_path()
        sink(
            f"{_WARN}缺少依赖：{e}。请用 `uv run {script}`（PEP 723 自动装依赖），"
            f"或 `uv run --no-sync --with websockets python {script}` 复用项目虚拟环境"
        )
        return 1
    except RequestException as e:
        body = getattr(getattr(e, "response", None), "text", "") or ""
        detail = f"，响应片段：{body[:200]}" if body else ""
        sink(f"{_WARN}REST 请求失败：{e!r}{detail}")
        return 1
    except ValueError as e:  # 空回补、CSV symbol / 对齐 / 表头不匹配等
        sink(f"{_WARN}{e}")
        return 1
    finally:
        restore_sigterm()
    sink(f"结束：本次 WebSocket 实时处理 {n} 根 {symbol} {interval} K 线（不含回补）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
