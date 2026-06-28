"""Build narrow /goal prompts from previous experiment artifacts.

优化只允许改 opens/exits 的 event 定义（入场/出场优化），
interval/timeout/stop_loss/T0 由系统锁定。每轮把上一轮 best 的 position 作为
「下一个 baseline」喂回去，让优化可以重复执行上百、上千次、持续变好。
"""

from __future__ import annotations

import csv
from pathlib import Path


def _read_tail(path: Path, max_chars: int = 6000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[-max_chars:]


def _best_position_json(run_dir: Path) -> str:
    """读取上一轮 best_positions/ 下得分最高的候选，作为下一轮的 baseline。"""
    best_dir = run_dir / "best_positions"
    if not best_dir.exists():
        return ""
    files = sorted(best_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return ""
    return files[0].read_text(encoding="utf-8")


def _top_leaderboard(path: Path, n: int = 8) -> str:
    if not path.exists():
        return ""
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return ""
    rows = rows[:n]
    cols = ["rank", "id", "score", "annual_return", "sharpe", "max_drawdown", "trade_count"]
    lines = [",".join(c for c in cols)]
    for r in rows:
        lines.append(",".join(str(r.get(c, "")) for c in cols))
    return "\n".join(lines)


def build_goal_prompt(run_dir: Path) -> str:
    """Return a prompt that asks an LLM to produce candidate JSONL only."""
    from auto_quant.signals import render_signal_catalog

    leaderboard = _top_leaderboard(run_dir / "leaderboard.csv")
    journal = _read_tail(run_dir / "journal.md")
    best_position = _best_position_json(run_dir)

    # 从上一轮 best 推断目标周期，注入信号目录。
    import json

    freq = "30分钟"
    if best_position:
        try:
            data = json.loads(best_position)
            opens = data.get("opens") or []
            if opens and opens[0].get("signals_all"):
                first = opens[0]["signals_all"][0]
                if isinstance(first, str) and "_" in first:
                    freq = first.split("_", 1)[0]
        except Exception:  # noqa: BLE001
            pass
    catalog = render_signal_catalog(freq)

    return f"""请基于上一轮 auto-czsc-quant 实验结果，提出下一轮最多 20 个完整 Position 候选，目标是让回测 score 持续变好。这是一个会重复执行上百、上千次的迭代过程。

## 核心约束：每次迭代必须真正改变 event 信号
- 每个候选的 opens / exits event 信号必须与下一轮 baseline **不同**。只照抄 baseline 信号、或只改 interval/timeout/stop_loss/T0 的候选会被校验当作无效克隆拒绝。
- 信号必须从下面的「信号目录」里选真实存在的信号字符串，不能臆造。

合法的优化操作（只允许这两类）：
- 入场优化：修改 opens 中某个 event 的 signals_all / signals_any / signals_not，**换一个不同的完全分类 signal**，改进入场点。
- 出场优化：在 exits 中新增 event（用目录里的平多方向信号），让策略提前正确止盈/止损，降低回撤。

禁止操作（系统会自动丢弃）：
- 不要修改 interval / timeout / stop_loss / T0；不要修改 symbol。
- 不要输出与下一轮 baseline event 信号完全相同的候选。

硬性要求：
- 只输出 JSONL，不输出解释性文字。
- 每行格式为 {{"id": "...", "hypothesis": "...", "position": {{...}}}}。
- position 必须是完整的 czsc Position JSON，能被 czsc.Position.from_json 加载。
- opens 不得为空；每个 hypothesis 必须说明改了哪个 event、用了哪个新信号、验证假设。
- 以「下一轮 baseline」为基础做小步变化，避免重复已尝试的配置。

{catalog}

下一轮 baseline（上一轮 best 的 Position）：
```json
{best_position}
```

上一轮 leaderboard.csv（前 8 名）：
```csv
{leaderboard}
```

上一轮 journal.md：
```markdown
{journal}
```
"""
