"""案例 18：Tushare 全市场日线 + 三买事件选股 + WeightBacktest

任务来源：飞书 t101178（新增 tushare 数据下的日线事件选股策略研究案例）。

与已有案例的差异：
    - 案例 13 / 14 演示**单只标的 + 30 分钟**的事件触发逻辑
    - 本案例演示**截面（多只股票）+ 日线**：在采样的 A 股股票池上跑同一
      三买事件，每根日线 K 线打 0 / 1 标记，再用 ``adjust_holding_weights``
      把瞬时事件扩展为固定持仓周期，最后交给 ``WeightBacktest`` 出 HTML 报告。

核心流程：
    1. 读取股票池：默认从 ``ts_connector.get_symbols('stock')`` 随机抽 50 只
       （把 ``SYMBOL_LIMIT`` 改成 ``"all"`` 即可切到全市场）。
    2. 拉每只股票的后复权日线（``get_raw_bars(freq='日线', fq='后复权')``），
       磁盘缓存由 ``czsc.DataClient`` 自动接管。
    3. ``generate_czsc_signals`` 跑 ``cxt_third_buy_V230228`` 信号；
       ``Event.is_match`` 把每根 bar 打成 0 / 1。
    4. ``adjust_holding_weights(hold_periods=5)`` 把瞬时事件扩展为 5 日持仓。
    5. ``WeightBacktest(weight_type='ts')`` 算 stats；
       ``wbt.generate_backtest_report`` 落 HTML 报告。

依赖：
    - ``TUSHARE_TOKEN`` 环境变量（脚本会优先从仓库根 ``.env`` 加载）

运行：
    uv run --no-sync python docs/examples/18_tushare_daily_event_universe.py

产物：
    docs/examples/_output/18_tushare_daily_event_universe/
        ├── report.html        # 真实数据回测报告（自包含 HTML）
        └── stats.csv          # 核心绩效指标
"""

from __future__ import annotations

import os
import random
from collections.abc import Iterable
from pathlib import Path

import pandas as pd
from tqdm import tqdm
from wbt import generate_backtest_report

from czsc import (
    Event,
    WeightBacktest,
    adjust_holding_weights,
    generate_czsc_signals,
    get_signals_config,
)

# ============================ 全局参数 ============================ #

OUTPUT_DIR = Path(__file__).resolve().parent / "_output" / "18_tushare_daily_event_universe"

BASE_FREQ = "日线"
SDT_DATA = "20200101"
EDT_DATA = "20241231"
SDT_BT = "2020-07-01"  # 预留半年给 CZSC 笔 / 中枢预热
FEE_RATE = 0.0002  # 单边 2 BP
HOLD_PERIODS = 5  # 事件触发后持仓 5 个交易日
SYMBOL_LIMIT: int | str = 50  # 抽样股票数；改成 "all" 表示全市场
SAMPLE_SEED = 42  # 抽样可复现
YEARLY_DAYS = 252  # A 股年化口径

# 三买信号编码（与案例 13 / 14 同源；通过 get_signals_config 自动派生配置）
EVENT_SIGNAL = f"{BASE_FREQ}_D1_三买辅助V230228_三买_任意_任意_0"


# ============================ Event 构造 ============================ #


def build_open_event() -> Event:
    """日线三买 → 开多事件。"""
    return Event.load(
        {
            "name": "日线三买V230228_开多",
            "operate": "开多",
            "signals_all": [EVENT_SIGNAL],
        }
    )


# ============================ 信号 → 权重 ============================ #


def event_matches_to_weight_df(
    bars: list,
    signals_config: list[dict],
    event: Event,
    sdt: str,
) -> pd.DataFrame:
    """对单只股票跑信号 + 事件匹配，返回 (dt, symbol, price, weight) 长表。

    - ``weight`` 取 ``1.0`` 表示该 bar 触发了开多事件，否则 ``0.0``
    - ``symbol`` 从 ``signals`` 里读，避免和上游传入的代码标签不一致
    """
    sigs = generate_czsc_signals(bars, signals_config, sdt=sdt, df=False)
    if not sigs:
        return pd.DataFrame(columns=["dt", "symbol", "price", "weight"])

    rows = []
    for s in sigs:
        dt = pd.to_datetime(s["dt"])
        # 真实 tushare 数据是 naive；统一去 tz 避免后续 merge 报错
        if dt.tzinfo is not None:
            dt = dt.tz_localize(None)
        rows.append(
            {
                "dt": dt,
                "symbol": s["symbol"],
                "price": float(s["close"]),
                "weight": 1.0 if event.is_match(s) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def _attach_n1b(df: pd.DataFrame) -> pd.DataFrame:
    """按 symbol 计算下一根 bar 的简单收益率，作为 ``adjust_holding_weights`` 输入。"""
    df = df.sort_values(["symbol", "dt"]).reset_index(drop=True)
    df["n1b"] = df.groupby("symbol")["price"].pct_change().shift(-1).fillna(0)
    return df


# ============================ 主流程封装 ============================ #


def run_universe(
    bars_iter: Iterable[tuple[str, list]],
    *,
    sdt_bt: str,
    hold_periods: int,
    output_path: Path,
    title: str,
) -> dict[str, float]:
    """跑一遍多 symbol 的事件 → 权重 → 回测 → HTML 报告。

    :param bars_iter: ``(label, bars)`` 可迭代序列；``label`` 仅用于日志，
        实际 symbol 列以 ``bars[0].symbol`` 为准（与信号 / 回测一致）
    :param sdt_bt: 信号开始计算日期
    :param hold_periods: 事件持仓周期（个交易日）
    :param output_path: HTML 报告输出路径
    :param title: HTML 报告标题
    """
    event = build_open_event()
    signals_config = get_signals_config([EVENT_SIGNAL])
    print(f"[config] signals_config = {signals_config}")

    pieces: list[pd.DataFrame] = []
    matched_total = 0
    for _label, bars in bars_iter:
        if not bars:
            continue
        df = event_matches_to_weight_df(bars, signals_config, event, sdt_bt)
        if df.empty:
            continue
        matched_total += int((df["weight"] == 1.0).sum())
        pieces.append(df)

    if not pieces:
        raise RuntimeError("所有 symbol 都没产生权重数据；检查数据源 / 信号配置")

    dfw = pd.concat(pieces, ignore_index=True)
    dfw = _attach_n1b(dfw)
    print(f"[event] 共 {len(pieces)} 只 symbol 入库；权重表 shape = {dfw.shape}；三买触发 {matched_total} 次")

    adj = adjust_holding_weights(dfw, hold_periods=hold_periods)
    # adjust_holding_weights 丢掉了 price，需要从原表 merge 回来
    adj = adj.merge(dfw[["dt", "symbol", "price"]], on=["dt", "symbol"], how="left")
    wb_df = adj[["dt", "symbol", "weight", "price"]].copy()
    print(f"[hold] 扩展为 {hold_periods} 日持仓后；非零权重 bar 数 = {int((wb_df['weight'] > 0).sum())}")

    wb = WeightBacktest(
        data=wb_df,
        fee_rate=FEE_RATE,
        weight_type="ts",
        yearly_days=YEARLY_DAYS,
    )
    print("[backtest] 核心绩效指标：")
    for k, v in wb.stats.items():
        print(f"    {k}: {v}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    generate_backtest_report(
        df=wb_df,
        output_path=str(output_path),
        title=title,
        fee_rate=FEE_RATE,
        weight_type="ts",
        yearly_days=YEARLY_DAYS,
    )
    print(f"[report] HTML 报告: {output_path} (size={output_path.stat().st_size:,} bytes)")
    return dict(wb.stats)


# ============================ 真实 tushare 数据入口 ============================ #


def _load_tushare_token() -> str:
    """优先从环境变量；其次从仓库根 ``.env`` 解析 ``TUSHARE_TOKEN``。"""
    token = os.environ.get("TUSHARE_TOKEN", "")
    if token:
        return token

    repo_root = Path(__file__).resolve().parents[2]
    env_file = repo_root / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            if k.strip() == "TUSHARE_TOKEN":
                return v.strip().strip("'\"")
    return ""


def _resolve_universe() -> list[str]:
    """从 tushare ``stock_basic`` 拉股票池，按 ``SYMBOL_LIMIT`` 抽样。"""
    from czsc.connectors.ts_connector import get_symbols

    full = get_symbols("stock")
    if isinstance(SYMBOL_LIMIT, str) and SYMBOL_LIMIT.lower() == "all":
        return full
    if isinstance(SYMBOL_LIMIT, int) and SYMBOL_LIMIT > 0:
        rng = random.Random(SAMPLE_SEED)
        return rng.sample(full, min(SYMBOL_LIMIT, len(full)))
    raise ValueError(f"不支持的 SYMBOL_LIMIT 值：{SYMBOL_LIMIT!r}")


def _fetch_one(symbol: str) -> list:
    """单只股票拉日线；失败时返回空列表（不中断主流程）。"""
    from czsc.connectors.ts_connector import get_raw_bars

    try:
        return get_raw_bars(
            symbol=symbol,
            freq=BASE_FREQ,
            sdt=SDT_DATA,
            edt=EDT_DATA,
            fq="后复权",
            raw_bar=True,
        )
    except Exception as e:  # noqa: BLE001
        tqdm.write(f"[warn] {symbol} 拉取失败：{e}")
        return []


def main() -> None:
    token = _load_tushare_token()
    if not token:
        raise SystemExit(
            "未找到 TUSHARE_TOKEN。请 `export TUSHARE_TOKEN=...` 或在仓库根 `.env` 写入 `TUSHARE_TOKEN=...`。"
        )

    import tushare as ts

    import czsc as cz

    ts.set_token(token)
    cz.set_url_token(token=token, url="http://api.tushare.pro")

    symbols = _resolve_universe()
    print(f"[universe] 标的池共 {len(symbols)} 只 (SYMBOL_LIMIT={SYMBOL_LIMIT})")

    bars_iter: list[tuple[str, list]] = []
    for sym in tqdm(symbols, desc="拉日线"):
        bars = _fetch_one(sym)
        if bars:
            bars_iter.append((sym, bars))

    if not bars_iter:
        raise SystemExit("没有任何股票拉到数据，请检查 TUSHARE_TOKEN 权限 / 网络")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stats = run_universe(
        bars_iter=bars_iter,
        sdt_bt=SDT_BT,
        hold_periods=HOLD_PERIODS,
        output_path=OUTPUT_DIR / "report.html",
        title=(f"案例 18 - 日线三买事件选股 (universe={len(bars_iter)}, hold={HOLD_PERIODS}d)"),
    )
    pd.Series(stats).to_csv(OUTPUT_DIR / "stats.csv", header=["value"])
    print(f"[done] stats 已保存到 {OUTPUT_DIR / 'stats.csv'}")


if __name__ == "__main__":
    main()
