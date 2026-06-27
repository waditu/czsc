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
```

`report.html` 是结构化优化报告，包含运行配置、数据加载、执行记录、leaderboard、候选详情、拒绝原因和产物索引。

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
