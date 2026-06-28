请生成下一轮 auto-czsc-quant 候选 Position JSONL，目标是让回测 score 持续变好。
这个过程会重复上百、上千次，每一步都要是可解释、可累积的小变化。

只输出 JSONL，不要解释。每一行必须满足：

```json
{"id":"trial_001","hypothesis":"一句话说明改了哪个 event、用了哪个新信号、验证假设","position":{完整 Position JSON}}
```

## 核心约束：每次迭代必须真正改变 event 信号
- 每个候选的 opens / exits event 信号必须与 baseline **不同**。完全照抄 baseline 信号、或只改 interval/timeout/stop_loss/T0 的候选会被校验当作无效克隆拒绝。
- 信号必须使用 czsc 注册表中真实存在的信号函数构造（参考 signal-functions skill 的信号字符串格式 `k1_k2_k3_v1_v2_v3_score`），不能臆造。臆造的信号会被校验拒绝。
- 优先使用已校验可直接复制的信号字符串（详见 auto_quant/signals.py 注入到 prompt 的「信号目录」）。

合法的优化操作（只允许这两类）：

- **入场优化**：修改 `opens` 中某个 event 的 `signals_all` / `signals_any` / `signals_not`，**换一个不同的真实完全分类 signal**，过滤假突破、捕捉更早的开仓点。
- **出场优化**：在 `exits` 中**新增**一个 event（用真实平多方向信号），让策略提前正确止盈，降低回撤。

约束：

- 最多输出 20 行。
- `position` 必须能被 `czsc.Position.load` 加载。
- 不要修改 `symbol`。
- 不要输出空 `opens`。
- **禁止**修改 `interval` / `timeout` / `stop_loss` / `T0`——被系统锁定，写了也会被丢弃。
- 优先围绕 leaderboard 中表现最好的候选做小步结构变化，再保留少量探索性变化。
- 避免重复上一轮已经出现在 `accepted.jsonl` 的配置。
