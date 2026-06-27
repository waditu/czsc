"""Build narrow /goal prompts from previous experiment artifacts."""

from __future__ import annotations

from pathlib import Path


def _read_tail(path: Path, max_chars: int = 6000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    return text[-max_chars:]


def build_goal_prompt(run_dir: Path) -> str:
    """Return a prompt that asks an LLM to produce candidate JSONL only."""
    leaderboard = _read_tail(run_dir / "leaderboard.csv")
    journal = _read_tail(run_dir / "journal.md")
    accepted = _read_tail(run_dir / "accepted.jsonl")

    return f"""请基于上一轮 auto-czsc-quant 实验结果，提出下一轮最多 20 个完整 Position 候选。

硬性要求：
- 只输出 JSONL，不输出解释性文字。
- 每行格式为 {{"id": "...", "hypothesis": "...", "position": {{...}}}}。
- position 必须是完整的 czsc Position JSON，能被 czsc.Position.load 加载。
- 不要修改 symbol；不要输出空 opens；T+0 字段使用 CZSC JSON 里的 `T0`。
- 每个 hypothesis 必须说明本次结构调整想验证的假设。
- 避免重复上一轮已经尝试过的配置。

上一轮 leaderboard.csv：

```csv
{leaderboard}
```

上一轮 journal.md：

```markdown
{journal}
```

上一轮 accepted.jsonl 尾部：

```jsonl
{accepted}
```
"""
