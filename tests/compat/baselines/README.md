# PR-1 基线快照

由 PR-1（盘点冻结）记录的"清理前"状态。

| 文件 | 说明 |
|---|---|
| `streamlit_imports.txt` | `czsc/` `tests/` `docs/` 下所有 `import streamlit` / `from streamlit` 行 |
| `svc_refs.txt` | 同上范围下所有 `from czsc.svc` / `czsc.svc.*` 引用行 |
| `ta_refs.txt` | 同上范围下所有 `from czsc.ta` / `czsc.ta.` / `from .ta ` 引用行 |

后续 PR 在 review 阶段用以下命令对比，每个 PR 应当**只减不增**：

```bash
git grep -nE "import streamlit|from streamlit" -- 'czsc/**/*.py' 'tests/**/*.py' 'docs/**/*.py' | diff - tests/compat/baselines/streamlit_imports.txt
```

最终 PR-5 完成时，三份基线对应的现状都应为空。
