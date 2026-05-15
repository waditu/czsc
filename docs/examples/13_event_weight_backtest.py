"""案例 13：基于 Event 的策略回测 + wbt HTML 报告

演示从一个 / 多个 ``Event`` 出发，跑通 ``CzscStrategyBase.backtest`` 并把 holds
转成 wbt 权重表，最后用 ``wbt.generate_backtest_report`` 一键生成 HTML 报告。

两个版本：
    - single_event：30 分钟三买（``cxt_third_buy_V230228``）开多 + 笔向下平多
    - multi_event ：同 Position 内叠加 V230228 / V230318 / V230319 三种三买
      触发条件，演示 OR 语义的事件组合

设计文档：
    https://s0cqcxuy3p.feishu.cn/wiki/YLUFwg0Q6iF62gkRQBacT1RDn4g

运行：
    uv run --no-sync python docs/examples/13_event_weight_backtest.py

产物：
    docs/examples/_output/13_event_weight_backtest/
        ├── single_event.html
        └── multi_event.html
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from wbt import generate_backtest_report

from czsc import (
    CzscStrategyBase,
    Event,
    Position,
    WeightBacktest,
    cal_yearly_days,
    format_standard_kline,
)
from czsc.mock import generate_symbol_kines

# 所有案例统一把产物落到 docs/examples/_output/，已在 .gitignore 中忽略
OUTPUT_DIR = Path(__file__).resolve().parent / "_output" / "13_event_weight_backtest"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 全局回测参数（保持单 / 多 Event 之间可比）
SYMBOL = "SYM"
BASE_FREQ = "30分钟"
SDT_DATA = "20200101"
EDT_DATA = "20240101"
SDT_BT = "2020-06-01"  # 预留半年给 CZSC 缓存中枢 / 笔
FEE_RATE = 0.0002  # 单边 2 BP
SEED = 42

# 平仓事件：笔向下；涨停过滤：开多禁开
_EXIT_SIG_BI_DOWN = f"{BASE_FREQ}_D1_表里关系V230101_向下_任意_任意_0"
_NOT_SIG_ZHANGTING = f"{BASE_FREQ}_D1_涨跌停V230331_涨停_任意_任意_0"


# ----------------------------- Event / Position 构造 ----------------------------- #


def _build_exit_event() -> Event:
    """统一的平多事件：30 分钟笔向下即平。"""
    return Event.load(
        {
            "name": "笔向下_平多",
            "operate": "平多",
            "signals_all": [_EXIT_SIG_BI_DOWN],
        }
    )


def build_single_event_position(symbol: str) -> Position:
    """单 Event 版本：纯笔三买（``cxt_third_buy_V230228``）开多 + 笔向下平多。"""
    open_event = Event.load(
        {
            "name": "三买V230228_开多",
            "operate": "开多",
            "signals_all": [f"{BASE_FREQ}_D1_三买辅助V230228_三买_任意_任意_0"],
            # 涨停日禁开仓——signals_not 用于演示 NOT 语义的否决条件
            "signals_not": [_NOT_SIG_ZHANGTING],
        }
    )
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
    """多 Event 版本（组合 A）：同 Position 内放 3 个 open Event，OR 语义触发。

    三种三买的差异：
        - V230228：纯笔三买，无均线辅助
        - V230318：第 5 笔离开中枢 + 34 日 SMA 同向抬升
        - V230319：在 V230318 基础上要求"均线新高"
    """
    opens = [
        Event.load(
            {
                "name": "三买V230228_开多",
                "operate": "开多",
                "signals_all": [f"{BASE_FREQ}_D1_三买辅助V230228_三买_任意_任意_0"],
                "signals_not": [_NOT_SIG_ZHANGTING],
            }
        ),
        Event.load(
            {
                "name": "三买V230318_开多",
                "operate": "开多",
                "signals_all": [f"{BASE_FREQ}_D1#SMA#34_BS3辅助V230318_三买_任意_任意_0"],
                "signals_not": [_NOT_SIG_ZHANGTING],
            }
        ),
        Event.load(
            {
                "name": "三买V230319_开多",
                "operate": "开多",
                "signals_all": [f"{BASE_FREQ}_D1#SMA#34_BS3辅助V230319_三买_均线新高_任意_0"],
                "signals_not": [_NOT_SIG_ZHANGTING],
            }
        ),
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


# --------------------------- holds → wbt weight 表 --------------------------- #


def holds_to_weight_df(holds: pd.DataFrame) -> pd.DataFrame:
    """把 ``ResearchResult.holds_df()`` 转成 wbt 期望的权重表。

    holds 列：``[dt, pos, price, n1b, symbol, pos_name]``
        - pos 已经是 ``{-1, 0, 1}``，直接 rename 为 weight 即可
        - 多 Position 时同 (dt, symbol) 会有多行（按 pos_name 拆），用 ``groupby``
          求平均得到组合权重，对应 wbt 的 ``weight_type="ts"``
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
    """跑一遍 backtest -> wbt -> HTML 报告，返回 stats 摘要。

    流程：
        1. ``strategy.backtest(bars, sdt=sdt)``  -> ResearchResult
        2. ``holds_df`` 转 wbt 权重表
        3. ``WeightBacktest`` 计算绩效（控制台打印）
        4. ``wbt.generate_backtest_report`` 落盘 HTML
    """
    print(f"\n=== [{tag}] 开始回测 ===")
    print(f"  策略类     = {strategy.__class__.__name__}")
    print(f"  base_freq  = {strategy.base_freq} | freqs = {strategy.freqs}")
    print(f"  signals_config 共 {len(strategy.signals_config)} 项")

    # 1) 回测，拿到 ResearchResult（含 signals / pairs / holds 三份 Arrow）
    res = strategy.backtest(bars, sdt=sdt)
    pairs = res.pairs_df()
    holds = res.holds_df()
    print(f"  pairs.shape = {pairs.shape} | holds.shape = {holds.shape}")

    # 2) holds -> wbt 权重表
    dfw = holds_to_weight_df(holds)
    yearly = cal_yearly_days(dts=dfw["dt"].unique())
    print(f"  权重表 shape = {dfw.shape} | yearly_days = {yearly}")

    # 3) WeightBacktest 拿绩效指标（不依赖 HTML 路径，方便单测 / 对比）
    wb = WeightBacktest(data=dfw, fee_rate=FEE_RATE, weight_type="ts", yearly_days=yearly)
    print(f"  [{tag}] 核心绩效指标：")
    for k, v in wb.stats.items():
        print(f"    {k}: {v}")

    # 4) HTML 报告（wbt 一键产出）
    out_html = OUTPUT_DIR / f"{tag}.html"
    generate_backtest_report(
        df=dfw,
        output_path=str(out_html),
        title=f"案例 13 - {tag} 回测报告",
        fee_rate=FEE_RATE,
        weight_type="ts",
        yearly_days=yearly,
    )
    print(f"  [{tag}] HTML 报告: {out_html}  (size={out_html.stat().st_size:,} bytes)")
    return wb.stats


def main() -> None:
    # 1) 准备 30 分钟 K 线（mock，可重现）
    df = generate_symbol_kines(SYMBOL, BASE_FREQ, SDT_DATA, EDT_DATA, seed=SEED)
    bars = format_standard_kline(df, freq=BASE_FREQ)
    print(f"[数据] {bars[0].symbol} {bars[0].freq} 共 {len(bars)} 根；{bars[0].dt} ~ {bars[-1].dt}")

    # 2) 跑两个版本
    stats_single = run_one("single_event", SingleEventStrategy(symbol=SYMBOL), bars, sdt=SDT_BT)
    stats_multi = run_one("multi_event", MultiEventStrategy(symbol=SYMBOL), bars, sdt=SDT_BT)

    # 3) stats 对比汇总
    cmp = pd.DataFrame({"single_event": stats_single, "multi_event": stats_multi})
    print("\n=== 单 / 多 Event 绩效对比 ===")
    print(cmp.to_string())

    print("\n[完成] HTML 报告全部生成到：", OUTPUT_DIR)
    print("下一步：用浏览器打开任一 .html 查看交互式图表。")


# --------------------------- 组合 B：多周期多 Position（参考实现） --------------------------- #
# 注释保留，避免一次跑两遍把案例时长拖长；如需启用：
#
# def build_multi_freq_positions(symbol: str) -> list[Position]:
#     """组合 B：30 分钟 / 60 分钟 各跑一个三买子策略，wbt 自动按品种汇总权重。"""
#     positions = []
#     for freq in ("30分钟", "60分钟"):
#         open_event = Event.load({
#             "name": f"{freq}三买_开多",
#             "operate": "开多",
#             "signals_all": [f"{freq}_D1_三买辅助V230228_三买_任意_任意_0"],
#         })
#         exit_event = Event.load({
#             "name": f"{freq}笔向下_平多",
#             "operate": "平多",
#             "signals_all": [f"{freq}_D1_表里关系V230101_向下_任意_任意_0"],
#         })
#         positions.append(Position(
#             name=f"{freq}_三买",
#             symbol=symbol,
#             opens=[open_event],
#             exits=[exit_event],
#             interval=3600 * 4, timeout=16 * 30, stop_loss=300,
#         ))
#     return positions
#
# class MultiFreqStrategy(CzscStrategyBase):
#     @property
#     def positions(self) -> list[Position]:
#         return build_multi_freq_positions(self.symbol)


if __name__ == "__main__":
    main()
