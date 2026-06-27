请生成下一轮 auto-czsc-quant 候选 Position JSONL。

只输出 JSONL，不要解释。每一行必须满足：

```json
{"id":"trial_001","hypothesis":"一句话说明要验证的策略结构假设","position":{完整 Position JSON}}
```

约束：

- 最多输出 20 行。
- `position` 必须能被 `czsc.Position.load` 加载。
- 不要修改 `symbol`。
- 不要输出空 `opens`。
- 可以直接调整 `opens`、`exits`、`signals_all`、`signals_any`、`signals_not`、`interval`、`timeout`、`stop_loss`、`T0`。
- 避免重复上一轮已经出现在 `accepted.jsonl` 的配置。
- 优先围绕 leaderboard 中表现最好的候选做小步结构变化，再保留少量探索性变化。
