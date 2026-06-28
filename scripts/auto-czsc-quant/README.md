# auto-czsc-quant

`auto-czsc-quant` 是一个脚本级实验编排器，用来跑通“大模型改 Position 配置 + CZSC 自动评分”的闭环。

当前实现不改 `czsc` 核心包；它可以读取人工候选 JSONL，也可以调用 `.env` 中配置的 Anthropic 兼容 LLM 生成完整 `position` 候选，然后用 mock、Tushare 或标准 feather 行情完成校验、回测、评分和实验记录。

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
  report.html
  best_positions/
  curves/              # 每个候选的组合日收益序列，供报告叠加收益曲线对比
```

`report.html` 是结构化优化报告，包含运行配置、**top-k 策略累计收益曲线对比**、最佳对比、数据加载、执行记录、leaderboard、候选详情、拒绝原因和产物索引。

## 优化语义

优化只允许两种合法操作（可重复执行上百、上千次，逐步累积变好）：

- **入场优化**：修改 `opens` 中某个 event 的 `signals_all` / `signals_any` / `signals_not`，换用不同的完全分类 signal，改进入场点。
- **出场优化**：在 `exits` 中新增 event，让策略提前正确止盈/止损，降低收益回撤。

每次迭代**必须真正改变 opens/exits 的 event 信号**，否则候选会被校验拒绝：

- **信号必须真实存在**：候选里每个信号都要能被 `czsc.derive_signals_config` 解析（即在 czsc 信号注册表中），臆造信号一律拒绝。
- **必须与 baseline 不同**：opens/exits 信号签名与 baseline 完全相同的候选（无效克隆）会被拒绝；同一批里签名重复的候选也会被拒。

LLM 优化（`candidate_mode=llm` 或 `/goal` 提示）会把一份「信号目录」注入 prompt：从 czsc 注册表 + `signal-functions` skill 文档中提取经校验可直接使用的开多/平多方向信号字符串（参考 `.claude/skills/signal-functions`），让模型每轮都从真实信号池里选。

`interval` / `timeout` / `stop_loss` / `T0` **不参与优化**：无论候选提交什么值，都会被 baseline（若配置 `baseline_position_path`）或安全默认值强制覆盖。`/goal` 下一轮提示会把上一轮 best 的 Position 作为新 baseline 喂回去，让优化持续迭代。

## 候选协议

候选文件是 JSONL，一行一个完整候选：

```json
{"id":"trial_001","hypothesis":"入场优化：在开多 event 加入顶分型过滤","position":{...}}
```

约束：

- `id` 必须唯一。
- `hypothesis` 必须非空。
- `position` 必须能被 `czsc.Position.load` 加载。
- `position.opens` 不能为空。
- 候选数量不能超过配置中的 `max_candidates`。
- `interval` / `timeout` / `stop_loss` / `T0` 即便填写也会被系统锁定覆盖。

## 数据源

`data_source` 支持三种模式：

- `mock`：使用 `czsc.mock.generate_symbol_kines` 生成确定性行情，适合测试。
- `tushare`：直接通过 `czsc.connectors.ts_connector.get_raw_bars` 拉取真实行情；需要在环境变量或仓库根 `.env` 配置 `TUSHARE_TOKEN`。
- `feather`：读取用户传入的标准行情 feather/ipc 文件；必需列为 `dt,symbol,open,close,high,low,vol,amount`。

Tushare + 真实 LLM 示例：

```bash
PYTHONPATH=scripts/auto-czsc-quant uv run python -m auto_quant.cli run \
  --config scripts/auto-czsc-quant/configs/example.tushare-llm.json
```

`.env` 中默认读取：

```text
TUSHARE_TOKEN=...
ANTHROPIC_BASE_URL=...
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=...
```

## CLI

```bash
PYTHONPATH=scripts/auto-czsc-quant uv run python -m auto_quant.cli run --config <config.json>
PYTHONPATH=scripts/auto-czsc-quant uv run python -m auto_quant.cli prompt --run-dir <results/.../run_id>
```

`prompt` 会读取上一轮 `leaderboard.csv` 和 `journal.md`，输出一个适合交给 `/goal` 的窄目标：只生成下一轮候选 JSONL，不修改源码。
