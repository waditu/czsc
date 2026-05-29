"""案例 14：Tushare 真实数据跑 Event 策略回测 + wbt HTML 报告

基于父文档「案例：基于 Event 的策略回测 + wbt HTML 报告」的 mock 版本，
改用 Tushare Pro 获取真实 A 股 30 分钟 K 线数据，跑通同样的三买策略。

两个版本：
    - single_event：30 分钟笔三买（cxt_third_buy_V230228）开多 + 笔向下平多
    - multi_event ：同 Position 内叠加 V230228 / V230318 / V230319 三种三买

运行：
    export TUSHARE_TOKEN="your_token"
    python 14_tushare_event_backtest.py

产物：
    _output/14_tushare_event_backtest/
        ├── single_event.html
        └── multi_event.html
"""

from __future__ import annotations

import os
from pathlib import Path

import czsc
import tushare as ts

# ---------- Tushare 配置（必须在 import ts_connector 之前） ----------
TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
if not TUSHARE_TOKEN:
    raise ValueError(
        "请先设置 Tushare token: export TUSHARE_TOKEN='your_token'\n"
        "注册地址: https://tushare.pro/register"
    )
ts.set_token(TUSHARE_TOKEN)
czsc.set_url_token(token=TUSHARE_TOKEN, url="http://api.tushare.pro")

import pandas as pd
from wbt import generate_backtest_report

from czsc import (
    CzscStrategyBase,
    Event,
    Position,
    WeightBacktest,
)
from czsc.connectors.ts_connector import get_raw_bars

# 所有案例统一把产物落到 _output/
OUTPUT_DIR = Path(__file__).resolve().parent / "_output" / "14_tushare_event_backtest"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 全局回测参数
SYMBOL = "000001.SZ#E"   # 平安银行；可替换为任意 A 股 / ETF
BASE_FREQ = "30分钟"
SDT_DATA = "20200101"
EDT_DATA = "20240601"
SDT_BT = "2020-07-01"    # 预留半年给 CZSC 缓存中枢 / 笔
FEE_RATE = 0.0002         # 单边 2 BP

# 平仓事件：笔向下；涨停过滤：开多禁开
_EXIT_SIG_BI_DOWN = f"{BASE_FREQ}_D1_表里关系V230101_向下_任意_任意_0"
_NOT_SIG_ZHANGTING = f"{BASE_FREQ}_D1_涨跌停V230331_涨停_任意_任意_0"


# ----------------------------- Event / Position 构造 ----------------------------- #


def _build_exit_event() -> Event:
    """统一的平多事件：30 分钟笔向下即平。"""
    return Event.load({
        "name": "笔向下_平多",
        "operate": "平多",
        "signals_all": [_EXIT_SIG_BI_DOWN],
    })


def build_single_event_position(symbol: str) -> Position:
    """单 Event 版本：纯笔三买（cxt_third_buy_V230228）开多 + 笔向下平多。"""
    open_event = Event.load({
        "name": "三买V230228_开多",
        "operate": "开多",
        "signals_all": [f"{BASE_FREQ}_D1_三买辅助V230228_三买_任意_任意_0"],
        "signals_not": [_NOT_SIG_ZHANGTING],
    })
    return Position(
        name="30min_三买_single",
        symbol=symbol,
        opens=[open_event],
        exits=[_build_exit_event()],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=300,
        t0=False,
    )


def build_multi_event_position(symbol: str) -> Position:
    """多 Event 版本：同 Position 内放 3 个 open Event，OR 语义触发。"""
    opens = [
        Event.load({
            "name": "三买V230228_开多",
            "operate": "开多",
            "signals_all": [f"{BASE_FREQ}_D1_三买辅助V230228_三买_任意_任意_0"],
            "signals_not": [_NOT_SIG_ZHANGTING],
        }),
        Event.load({
            "name": "三买V230318_开多",
            "operate": "开多",
            "signals_all": [f"{BASE_FREQ}_D1#SMA#34_BS3辅助V230318_三买_任意_任意_0"],
            "signals_not": [_NOT_SIG_ZHANGTING],
        }),
        Event.load({
            "name": "三买V230319_开多",
            "operate": "开多",
            "signals_all": [f"{BASE_FREQ}_D1#SMA#34_BS3辅助V230319_三买_均线新高_任意_0"],
            "signals_not": [_NOT_SIG_ZHANGTING],
        }),
    ]
    return Position(
        name="30min_三买_multi",
        symbol=symbol,
        opens=opens,
        exits=[_build_exit_event()],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=300,
        t0=False,
    )


class SingleEventStrategy(CzscStrategyBase):
    """30 分钟单 Event 三买策略。"""

    @property
    def positions(self) -> list[Position]:
        return [build_single_event_position(self.symbol)]


class MultiEventStrategy(CzscStrategyBase):
    """30 分钟多 Event 三买策略（OR 语义叠加 3 个开多事件）。"""

    @property
    def positions(self) -> list[Position]:
        return [build_multi_event_position(self.symbol)]


# --------------------------- holds -> wbt weight 表 --------------------------- #


def holds_to_weight_df(holds: pd.DataFrame) -> pd.DataFrame:
    """把 ResearchResult.holds_df() 转成 wbt 期望的权重表。

    holds 列：[dt, pos, price, n1b, symbol, pos_name]
    wbt 期望：[dt, symbol, weight, price]
    """
    df = holds[["dt", "symbol", "pos", "price"]].rename(columns={"pos": "weight"})
    if df.duplicated(subset=["dt", "symbol"]).any():
        df = df.groupby(["dt", "symbol"], as_index=False).agg(
            weight=("weight", "mean"),
            price=("price", "first"),
        )
    return df[["dt", "symbol", "weight", "price"]]


# ------------------------------- 主流程封装 ------------------------------- #


def run_one(tag: str, strategy: CzscStrategyBase, bars: list, sdt: str) -> dict[str, float]:
    """跑一遍 backtest -> wbt -> HTML 报告，返回 stats 摘要。"""
    print(f"\n=== [{tag}] 开始回测 ===")
    print(f"  策略类     = {strategy.__class__.__name__}")
    print(f"  base_freq  = {strategy.base_freq} | freqs = {strategy.freqs}")
    print(f"  signals_config 共 {len(strategy.signals_config)} 项")

    # 1) 回测
    res = strategy.backtest(bars, sdt=sdt)
    pairs = res.pairs_df()
    holds = res.holds_df()
    print(f"  pairs.shape = {pairs.shape} | holds.shape = {holds.shape}")

    # 2) holds -> wbt 权重表
    dfw = holds_to_weight_df(holds)
    yearly = 252  # A 股标准
    print(f"  权重表 shape = {dfw.shape} | yearly_days = {yearly}")

    # 3) WeightBacktest 拿绩效指标
    wb = WeightBacktest(data=dfw, fee_rate=FEE_RATE, weight_type="ts", yearly_days=yearly)
    print(f"  [{tag}] 核心绩效指标：")
    for k, v in wb.stats.items():
        print(f"    {k}: {v}")

    # 4) HTML 报告
    out_html = OUTPUT_DIR / f"{tag}.html"
    generate_backtest_report(
        df=dfw,
        output_path=str(out_html),
        title=f"案例 14 - {tag} 回测报告（Tushare 真实数据）",
        fee_rate=FEE_RATE,
        weight_type="ts",
        yearly_days=yearly,
    )
    print(f"  [{tag}] HTML 报告: {out_html}  (size={out_html.stat().st_size:,} bytes)")
    return wb.stats


def main() -> None:
    # 1) 用 Tushare 拉真实 30 分钟 K 线（后复权）
    print(f"[数据] 正在从 Tushare 获取 {SYMBOL} {BASE_FREQ} K 线...")
    bars = get_raw_bars(
        symbol=SYMBOL,
        freq=BASE_FREQ,
        sdt=SDT_DATA,
        edt=EDT_DATA,
        fq="后复权",
        raw_bar=True,
    )
    print(f"[数据] {bars[0].symbol} {bars[0].freq} 共 {len(bars)} 根；{bars[0].dt} ~ {bars[-1].dt}")

    # 2) 跑两个版本
    stats_single = run_one(
        "single_event",
        SingleEventStrategy(symbol=SYMBOL),
        bars,
        sdt=SDT_BT,
    )
    stats_multi = run_one(
        "multi_event",
        MultiEventStrategy(symbol=SYMBOL),
        bars,
        sdt=SDT_BT,
    )

    # 3) stats 对比汇总
    cmp = pd.DataFrame({"single_event": stats_single, "multi_event": stats_multi})
    print("\n=== 单 / 多 Event 绩效对比（Tushare 真实数据）===")
    print(cmp.to_string())

    print("\n[完成] HTML 报告全部生成到：", OUTPUT_DIR)
    print("下一步：用浏览器打开任一 .html 查看交互式图表。")


if __name__ == "__main__":
    main()
