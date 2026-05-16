# v2.0.0 清理迁移指南（占位）

> 本文件由 PR-1 创建，PR-5 填充正式迁移指南。
>
> 关联：[飞书《清理非缠论核心 API》](https://s0cqcxuy3p.feishu.cn/wiki/OGUUwZMZdi2jtykaFpKcAPz4nig)
> 方案：[《执行方案与验收标准（v1）》](https://s0cqcxuy3p.feishu.cn/docx/UOv8dobnDoFO43xcTvbcsOxZntc)
> 执行细节：[《执行细节与验收记录》](https://s0cqcxuy3p.feishu.cn/docx/GRtMdbDBSopOtCxa4TYcckHVnnd)

## 删除清单（PR-5 时正式填充）

- `czsc.svc.*` 全部 `show_*` 函数
- `czsc.ta.*` Python 顶层 alias（Rust `czsc._native.ta` 仍保留）
- streamlit 运行时依赖
- 5 个 streamlit 示例 + `_streamlit_smoke.py`
- `czsc/utils/plotting/lightweight/_streamlit_renderer.py`

## 替代方案

待 PR-5 填充。

## 升级步骤

待 PR-5 填充。
