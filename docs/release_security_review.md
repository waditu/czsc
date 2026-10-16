# 1.0.2 发布安全处置记录

维护者已选择 1.0.2 并保留新信号键。本次只同步项目版本和内部精确依赖，不回退下列安全修复或
变更第三方解析图。下文是此前 2.0.0 候选阶段对同一依赖图的审核记录；历史证据不是新 1.0.2
产物验证或全库安全认证，新版本仍须重新构建、安装和运行检查。

本轮针对审核 head `f7e5cc6` 的 30 项 open Dependabot 告警逐项处置。
来源为只读 `gh api --paginate 'repos/waditu/czsc/dependabot/alerts?state=open&per_page=100'`；漏洞条件与修复阈值来自各项 `security_advisory` / `security_vulnerability`。
共 1 critical、13 high、13 medium、3 low。该快照不是全库安全认证；GitHub 默认分支告警不会因草稿 PR 的锁文件更新自动关闭，本任务不 dismiss 告警。

## 每项影响与处理

“升级锁”只表示该 PR 解析图排除了本次审核涉及的漏洞版本，不表示已复现利用、用户旧环境已修复或所有平台产物已验证。版本分支由 Python marker 决定。

| 告警/级别 | GHSA | 影响及触发条件 | 版本与可达路径 | 处理 / 残余风险编号 |
| --- | --- | --- | --- | --- |
| #93 low | GHSA-6g2r-675j-hx59 | 短自定义 xxh3 secret 可能越界 | xxhash-rust：0.8.15 → 0.8.16；native/Polars 传递依赖 | 升级至首个修复版本；R1 |
| #92 high | GHSA-8988-9cw3-xx77 | HTTPS 代理可能忽略 TLS 配置 | urllib3：2.7.0 → 2.8.0；运行时 requests，以及发布工具 | 升级锁并声明 urllib3>=2.8.0；R3 |
| #91 medium | GHSA-3jqq-pw4j-pqcj | 恶意语言包导致前端 XSS | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #90 medium | GHSA-3325-v43h-43rv | 扩展卸载参数注入与文件/URL 泄漏 | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #89 high | GHSA-6966-vjj6-99xv | 剪贴板单元格触发 XSS | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #88 high | GHSA-6966-vjj6-99xv | 剪贴板单元格触发 XSS | notebook：7.5.0 → 7.6.3；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #87 high | GHSA-c2m8-h5v5-343r | 静态文件符号链接越界读取 | tornado：6.5.7 → 6.5.10；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #86 medium | GHSA-3hv7-mjh2-fv65 | 无限查询参数阻塞事件循环 | tornado：6.5.7 → 6.5.10；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #85 high | GHSA-chx6-46f5-w4vp | 解压响应缺少大小限制导致 OOM | tornado：6.5.7 → 6.5.10；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #84 medium | GHSA-gh4c-6fx4-qh6g | Deflate 分块流可能无限循环 | urllib3：2.7.0 → 2.8.0；运行时 requests，以及发布工具 | 升级锁并声明 urllib3>=2.8.0；R3 |
| #83 high | GHSA-jwv3-5hgf-82ww | 重复自签中间证书导致指数路径搜索 | cryptography：48.0.1 → 50.0.2；Linux release/all extra：Twine→keyring→secretstorage | 升级锁；R4 |
| #82 medium | GHSA-m2h6-j472-rp4c | 通配 DNS 名可逃逸证书子树约束 | cryptography：48.0.1 → 50.0.2；Linux release/all extra：Twine→keyring→secretstorage | 升级锁；R4 |
| #81 medium | GHSA-5p39-cfhj-2xmp | 进程池 stderr 不排空导致永久阻塞 | anyio：4.10.0 → 4.14.2/4.15.1；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #80 critical | GHSA-82r6-8w77-94w6 | 非 ASCII 域名的旧 IDNA 编码可能接受攻击者证书 | anyio：4.10.0 → 4.14.2/4.15.1；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #79 medium | GHSA-gjv8-xp57-g29c | 恶意 CSS selector 正则二次复杂度 | soupsieve：2.8.4 → 2.10/3.0.3；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #78 medium | GHSA-j934-xhv5-fg8f | 合法 selector 尾部空白/注释触发 ReDoS | soupsieve：2.8.4 → 2.10/3.0.3；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #77 high | GHSA-mpf4-983q-p7j4 | 表单字段无限解析阻塞事件循环 | tornado：6.5.7 → 6.5.10；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #76 high | GHSA-6m44-fpc8-c3rq | 过多 Markdown emphasis 导致递归异常/DoS | mistune：3.3.0 → 3.3.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #75 medium | GHSA-8423-8fgw-73vq | multipart split 临时列表导致内存放大 | tornado：6.5.7 → 6.5.10；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #74 low | GHSA-wwv5-g3v4-889x | cookie 属性注入修复可被旧 kwargs 路径绕过 | tornado：6.5.7 → 6.5.10；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #73 high | GHSA-g6cj-pr64-35w5 | PKCS#7 解密错误/时序可形成 padding oracle | cryptography：48.0.1 → 50.0.2；Linux release/all extra：Twine→keyring→secretstorage | 升级锁；R4 |
| #72 high | GHSA-4w2j-m93h-cj5j | 乱序流重组无界内存导致远程耗尽 | quinn-proto：0.11.14 → 0.11.15；锁内，默认 normal tree 不活动 | 升级至首个修复版本；R2 |
| #71 low | GHSA-whvh-wf3x-g77j | 直接安装扩展可绕过允许/禁止列表 | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #70 high | GHSA-gx64-gj6p-pc4c | 恶意图片在新标签触发 XSS | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #69 high | GHSA-pppj-hq3g-57pj | 恶意 settings 文件触发 XSS | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #68 medium | GHSA-h5v5-8746-g7mm | PluginManager 锁规则可绕过 | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #67 medium | GHSA-89vp-jrxv-24w8 | 扩展 blocklist 包名规范化可绕过 | jupyterlab：4.5.9 → 4.6.4；Jupyter 开发依赖 / dev、all extra | 升级锁与必要兼容依赖；R4 |
| #66 medium | GHSA-h35f-9h28-mq5c | Unicode 规范化可绕过 sdist MANIFEST 排除 | setuptools：80.9.0 → 已移除；旧构建/开发传递依赖 | 移出锁图，maturin 构建不依赖它；R5 |
| #52 medium | GHSA-chgr-c6px-7xpp | Python closure 缺 Sync 约束可能跨线程竞态 | pyo3：0.28.3 → 0.29.3；native 实际依赖 | 升级 PyO3 及 NumPy/stub 兼容链；R1 |
| #51 high | GHSA-36hh-v3qg-5jq4 | list/tuple nth/nth_back 溢出导致越界读 | pyo3：0.28.3 → 0.29.3；native 实际依赖 | 升级 PyO3 及 NumPy/stub 兼容链；R1 |

## 残余风险和接受边界

- R1：PyO3 位于 native 路径，更新至 0.29.3；NumPy Rust binding 0.29.0、stub generator 0.23.1 是匹配升级，编译与回归必须重新执行。项目直接调用中未找到 Python list/tuple `nth`/`nth_back` 或 `PyCFunction::new_closure`，不是第三方依赖不可达证明。xxhash 的短 secret 攻击未做压力/内存安全复现；以修复版本及产物重建处置，不靠未发现直接调用豁免。
- R2：`cargo tree --workspace -e normal -i quinn-proto --locked` 默认图不活动；未来开启 HTTP/3/相关 feature 可能改变可达性。因此仍升级到 0.11.15，不仅记录“当前没用”。未做远程 DoS 攻击复现。
- R3：urllib3 位于正常 requests 路径，新增 wheel 安装下限 `urllib3>=2.8.0`，不能只升级开发锁。依赖解析与安装检查不代表部署代理/TLS 配置正确，须部署方核查。
- R4：AnyIO critical 与其他 Jupyter 告警已按锁升级；JupyterLab 4.6.4 是 Notebook 7.6.3 的兼容要求，不是无关升级。cryptography 在 Linux 发布工具 extra，经 Twine/keyring/secretstorage 可达，不是正常 wheel native 库。没有运行恶意 notebook、域名、证书、HTTP/Markdown 压力复现。开发/发布环境应按该锁重建；用户自选旧版 extras 不会被 wheel 强制升级，须固定安全基线并限制不可信文档、扩展和输入。
- R5：setuptools 已从本次锁图移除；原生构建后端仍为 maturin。用户外部构建工具/系统环境中的 setuptools 不在本 PR 处置范围，尤其 macOS sdist 路径仍应核查其版本。

本 PR 没有将 CodeQL 成功当作依赖安全通过。`tests/test_release_dependencies.py` 为这次处置的版本阈值和 urllib3 安装下限加了防回退守卫；未来新告警仍需重新审查，不能复用本表作为永久豁免。

## 可执行追溯

```bash
python -m pytest tests/test_release_dependencies.py -q
cargo tree --workspace --all-features -e normal -i pyo3 --locked
cargo tree --workspace -e normal -i quinn-proto --locked
cargo tree --workspace -e normal -i xxhash-rust --locked
uv tree --universal --locked --invert --package anyio
uv tree --universal --locked --invert --package cryptography
uv tree --universal --locked --invert --package urllib3
```

跨平台重建、平台漏洞行为验证、线上利用路径、上传凭据有效性仍不可由版本守卫证明；剩余发布门禁见 `docs/release_validation.md`。正式版/RC、发布范围和风险接受须维护者确认。
