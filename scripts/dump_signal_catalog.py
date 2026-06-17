"""扫描 crates/czsc-signals/src/*.rs，重生成「信号函数模块深度介绍」第 6 章速查表。

用法：
    uv run --no-sync python scripts/dump_signal_catalog.py                 # 输出 markdown
    uv run --no-sync python scripts/dump_signal_catalog.py --format xml   # 输出飞书文档 XML
    uv run --no-sync python scripts/dump_signal_catalog.py --output catalog.md

输出包含 4 个分组（K 线基础 / 缠论结构 / 自定义 / Trader），每行 = 一个 .rs 文件 + 信号数 + 主题。
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SIGNAL_ATTR_RE = re.compile(
    r'#\[signal\s*\(\s*[^)]*?category\s*=\s*"(?P<category>[^"]+)"',
    re.DOTALL,
)
ROOT = Path(__file__).resolve().parents[1]
SIGNALS_DIR = ROOT / "crates" / "czsc-signals" / "src"

# 文件 -> (分组, 主题)。每次新增 .rs 时在此处登记一行。
FILE_METADATA: dict[str, tuple[str, str]] = {
    "bar.rs":         ("K线基础", "原始 K 线特征：涨跌停、累积成交额、单 K 形态、时间段过滤"),
    "tas.rs":         ("K线基础", "TA 指标系：MA / MACD / KDJ / BOLL / RSI / SAR / ATR 等"),
    "vol.rs":         ("K线基础", "成交量分位、成交量异动窗口"),
    "obv.rs":         ("K线基础", "OBV 能量潮上下穿信号"),
    "cvolp.rs":       ("K线基础", "成交量价压力上下穿"),
    "kcatr.rs":       ("K线基础", "K-Channel + ATR 突破"),
    "ntmdk.rs":       ("K线基础", "NTMDK 综合动能"),
    "clv.rs":         ("K线基础", "CLV 收盘价相对强弱"),
    "jcc.rs":         ("K线基础", "经典 K 线形态：吃头、反击线、分手线、乌云盖顶、三星等"),
    "byi.rs":         ("K线基础", "「白伊」系：对称中枢、笔的结束判定"),
    "xl.rs":          ("K线基础", "线性化 K 线：位置 / 趋势 / 基差"),
    "coo.rs":         ("K线基础", "共振组合：TD / CCI / KDJ / SAR 联合决策"),
    "ang.rs":         ("K线基础", "角度 / 斜率类：均线斜率、回归角度"),
    "pressure.rs":    ("K线基础", "支撑 / 阻力位密度"),

    "cxt.rs":         ("缠论结构", "笔 / 分型 / 中枢 / 一二三类买卖点等核心缠论判定"),

    "zdy.rs":         ("自定义指标", "用户自定义指标沙箱：MACD 变种、自定义中枢空间等"),

    "pos.rs":         ("Trader", "持仓状态、固定止损 / 止盈、移动止损、持仓时间窗"),
    "cat.rs":         ("Trader", "跨周期 MACD 共振"),
    "cxt_trader.rs":  ("Trader", "跨周期缠论：中枢共振、日内策略"),
    "zdy_trader.rs":  ("Trader", "自定义 trader 信号：止损止盈 / 震荡识别"),
}

GROUP_ORDER = ["K线基础", "缠论结构", "自定义指标", "Trader"]


@dataclass
class FileStat:
    filename: str
    group: str
    topic: str
    kline_count: int = 0
    trader_count: int = 0
    unknown_categories: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.kline_count + self.trader_count


def scan_signals_dir() -> list[FileStat]:
    if not SIGNALS_DIR.is_dir():
        sys.exit(f"目录不存在: {SIGNALS_DIR}")

    stats: list[FileStat] = []
    seen_files: set[str] = set()

    for rs in sorted(SIGNALS_DIR.glob("*.rs")):
        if rs.name in {"lib.rs", "registry.rs", "params.rs", "types.rs"}:
            continue

        text = rs.read_text(encoding="utf-8")
        meta = FILE_METADATA.get(rs.name)
        if meta is None:
            sys.stderr.write(
                f"[warn] {rs.name} 未登记 FILE_METADATA，临时归入「未分类」组\n"
            )
            group, topic = "未分类", "(待登记)"
        else:
            group, topic = meta

        stat = FileStat(filename=rs.name, group=group, topic=topic)
        for m in SIGNAL_ATTR_RE.finditer(text):
            cat = m.group("category")
            if cat == "kline":
                stat.kline_count += 1
            elif cat == "trader":
                stat.trader_count += 1
            else:
                stat.unknown_categories.append(cat)
        stats.append(stat)
        seen_files.add(rs.name)

    expected = set(FILE_METADATA) - seen_files
    if expected:
        sys.stderr.write(
            f"[warn] FILE_METADATA 中的文件未在 crate 中找到: {sorted(expected)}\n"
        )

    return stats


def render_markdown(stats: list[FileStat]) -> str:
    lines: list[str] = ["# 信号函数模块速查表（自动生成）", ""]
    total_signals = sum(s.total for s in stats)
    kline = sum(s.kline_count for s in stats)
    trader = sum(s.trader_count for s in stats)
    lines.append(
        f"**汇总**：{len(stats)} 个 .rs 文件 / {total_signals} 个 `#[signal]`"
        f"（K-line {kline} + Trader {trader}）"
    )
    lines.append("")

    by_group: dict[str, list[FileStat]] = {}
    for s in stats:
        by_group.setdefault(s.group, []).append(s)

    for group in GROUP_ORDER + sorted(set(by_group) - set(GROUP_ORDER)):
        group_stats = by_group.get(group)
        if not group_stats:
            continue
        group_total = sum(s.total for s in group_stats)
        lines.append(f"## {group}（{len(group_stats)} 文件 / {group_total} 信号）")
        lines.append("")
        lines.append("| 文件 | 信号数 | 主题 |")
        lines.append("|------|--------|------|")
        for s in sorted(group_stats, key=lambda x: -x.total):
            lines.append(f"| `{s.filename}` | {s.total} | {s.topic} |")
        lines.append("")

    return "\n".join(lines)


def render_xml(stats: list[FileStat]) -> str:
    """飞书文档 XML，可直接用于 docs +update --command block_replace。"""
    by_group: dict[str, list[FileStat]] = {}
    for s in stats:
        by_group.setdefault(s.group, []).append(s)

    parts: list[str] = []
    for group in GROUP_ORDER + sorted(set(by_group) - set(GROUP_ORDER)):
        group_stats = by_group.get(group)
        if not group_stats:
            continue
        group_total = sum(s.total for s in group_stats)
        parts.append(
            f"<h2>{escape(group)}（{len(group_stats)} 文件 / {group_total} 信号）</h2>"
        )
        parts.append(
            '<table>'
            '<colgroup><col width="100"/><col width="80"/><col width="320"/></colgroup>'
            '<thead><tr>'
            '<th background-color="light-gray">文件</th>'
            '<th background-color="light-gray">信号数</th>'
            '<th background-color="light-gray">主题</th>'
            '</tr></thead><tbody>'
        )
        for s in sorted(group_stats, key=lambda x: -x.total):
            parts.append(
                f"<tr><td><code>{escape(s.filename)}</code></td>"
                f"<td>{s.total}</td>"
                f"<td>{escape(s.topic)}</td></tr>"
            )
        parts.append("</tbody></table>")
    return "\n".join(parts)


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format", choices=["markdown", "xml"], default="markdown",
        help="输出格式（默认 markdown）",
    )
    parser.add_argument("--output", type=Path, help="写入文件而非 stdout")
    args = parser.parse_args()

    stats = scan_signals_dir()
    payload = render_markdown(stats) if args.format == "markdown" else render_xml(stats)

    if args.output:
        args.output.write_text(payload, encoding="utf-8")
        print(f"已写入 {args.output}（{len(payload)} bytes）", file=sys.stderr)
    else:
        print(payload)


if __name__ == "__main__":
    main()
