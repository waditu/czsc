# auto-czsc-quant

`auto-czsc-quant` 是一个脚本级实验编排器，用来跑通“大模型改 Position 配置 + CZSC 自动评分”的闭环。

当前 MVP 不调用真实 LLM，也不改 `czsc` 核心包；它读取人工或 LLM 产出的候选 `position` JSONL，用 mock 行情数据完成校验、回测、评分和实验记录。后续可以把 `prompts/mutate_position.md` 交给 Claude Code `/goal` 生成下一轮候选。

## 快速运行

从仓库根目录执行：

```bash
PYTHONPATH=scripts/auto-czsc-quant uv run python -m auto_quant.cli run \
  --config scripts/auto-czsc-quant/configs/example.json
```

运行后会生成：

```text
scripts/auto-czsc-quant/results/mock_position_demo/<run_id>/
  config.json
  accepted.jsonl
  rejected.jsonl
  leaderboard.csv
  journal.md
  best_positions/
```

## 候选协议

候选文件是 JSONL，一行一个完整候选：

```json
{"id":"trial_001","hypothesis":"减少假突破开仓，缩短最长持仓","position":{...}}
```

约束：

- `id` 必须唯一。
- `hypothesis` 必须非空。
- `position` 必须能被 `czsc.Position.load` 加载。
- `position.opens` 不能为空。
- 候选数量不能超过配置中的 `max_candidates`。

## CLI

```bash
PYTHONPATH=scripts/auto-czsc-quant uv run python -m auto_quant.cli run --config <config.json>
PYTHONPATH=scripts/auto-czsc-quant uv run python -m auto_quant.cli prompt --run-dir <results/.../run_id>
```

`prompt` 会读取上一轮 `leaderboard.csv` 和 `journal.md`，输出一个适合交给 `/goal` 的窄目标：只生成下一轮候选 JSONL，不修改源码。
