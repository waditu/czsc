# Release Checklist —— 权威版本指针

> ⚠️ **不要在此处复制 checklist 内容** —— 会与项目根的权威版本漂移。
>
> 完整清单（9 节、214 行）保存在仓库根目录：
>
> 👉 **[`docs/release_checklist.md`](../../../../docs/release_checklist.md)**
>
> 维护者修改清单时**只改 `docs/release_checklist.md` 这一份**，本指针文件不需要同步更新。

## 为什么本目录不放副本

- **单源不漂移**：复制一份到 references/ 后，每次更新都得改两处；漂移后 LLM 不知道该信哪份。
- **不用 symlink**：跨 OS（Windows）+ 某些 git 配置下软链接行为不一致；skill 可能被复制/分发到其他工作目录，断链后 silent 失败。
- **保留 references/ 目录结构**：符合 Anthropic skill convention（references/ 承载参考材料），让 SKILL.md 的引用路径稳定。

## SKILL.md 是怎么用这份清单的

`../SKILL.md` 在 **Phase 0** 和 **Phase 2** 把这份清单作为 **ratchet** 强制引入：

- **Phase 0**：用 `Read` 工具读 `docs/release_checklist.md` 全文（一次性，加载到上下文）。
- **Phase 2 预检**：把 docs §3 / §4 / §5 / §9 的命令逐条跑完；任何一条 fail → 停。
- **不许跳**：哪怕"只是 docs 改动"也要按 §1 跑代码/文档一致性检查（`czsc.xxx` 引用是否还存在、已退役关键字是否还有残留、文件路径是否还在）—— 历史教训里大量发版事故来自"docs 改了但忘了 push、或 docs 引用了已删 API 让下游 demo 炸"。

## 9 节速览（详情看 docs）

1. **代码冻结前**：所有 PR 已合 / CHANGELOG 已更 / 迁移说明已写；**代码 ↔ Markdown 文档一致性硬性检查**（含 3 段命令找漂移）
2. **版本号**：SemVer 决策树、单一版本源、prerelease 规则
3. **本地 Rust 验证**：cargo fmt / clippy / test / stub_gen + git diff 校验
4. **本地 Python 验证**：`pytest --run-slow`、ruff、冒烟 import 链
5. **本地 Wheel 验证**：含 Linux aarch64 / musllinux 的 docker 验证（CI 不覆盖）
6. **发布动作**：TestPyPI 演练 → tag push 触发 PyPI 真发 → 手动 dispatch crates.io 真发
7. **发布后验证**：PyPI / crates.io 页面、GitHub Release、干净环境冒烟
8. **隐藏缺陷雷达**：按历史踩坑频度排序的 10 项风险表
9. **一键自检脚本**：把 §3+§4+§5 串成可跑的 bash 一脚本
