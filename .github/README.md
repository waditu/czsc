# GitHub Actions 工作流说明

本项目使用基于 UV 的现代化 CI/CD 流程，包含以下工作流：

## 工作流概览

### 1. 测试和构建 (`pythonpackage.yml`)
**触发条件**: 推送到 `master`、`V0.9.68` 分支或创建 Pull Request

**主要功能**:
- 多 Python 版本测试 (3.10, 3.11, 3.12, 3.13)
- 自动运行测试套件
- 代码覆盖率报告
- 包构建验证
- 构建产物上传

**任务说明**:
- `test`: 在多个 Python 版本上运行测试
- `build`: 验证包能正确构建并检查元数据

### 2. 代码质量检查 (`code-quality.yml`)
**触发条件**: 推送到 `master`、`V0.9.68` 分支或创建 Pull Request

**主要功能**:
- 代码格式检查 (Black)
- 导入排序检查 (isort)
- 代码风格检查 (flake8)
- 类型检查 (mypy)
- 安全漏洞扫描 (safety, bandit)
- 依赖分析和许可证检查

**任务说明**:
- `formatting`: 检查代码格式和导入排序
- `linting`: 代码风格和类型检查
- `security`: 安全漏洞扫描
- `dependency-check`: 依赖分析

### 3. 构建和发布 (`python-publish.yml`)
**触发条件**: 
- 发布新版本 (GitHub Release)
- 手动触发 (workflow_dispatch)

**主要功能**:
- 发布前完整检查
- 包构建
- TestPyPI 测试发布
- PyPI 正式发布
- 数字签名 (Sigstore)
- GitHub Release 文件上传

**任务说明**:
- `pre-publish-checks`: 发布前的完整测试和检查
- `build`: 构建发布包
- `publish-to-testpypi`: 发布到测试环境 (可选)
- `publish-to-pypi`: 发布到正式 PyPI
- `create-github-release`: 创建 GitHub Release 并上传文件

## 开发者使用指南

### 本地开发环境设置
```bash
# 安装 uv
pip install uv

# 克隆项目
git clone https://github.com/waditu/czsc.git
cd czsc

# 安装依赖（开发模式）
uv sync --extra all

# 运行测试
uv run pytest

# 代码格式化
uv run black czsc/
uv run isort czsc/

# 构建包
uv build
```

### 发布新版本

1. **更新版本号**
   ```bash
   # 编辑 czsc/__init__.py 中的 __version__
   vim czsc/__init__.py
   ```

2. **本地测试**
   ```bash
   # 运行完整测试
   uv run pytest
   
   # 构建包
   uv build
   
   # 检查包
   uv run twine check dist/*
   ```

3. **创建 GitHub Release**
   - 在 GitHub 上创建新的 Release
   - 标签格式: `v0.9.70`
   - 自动触发发布流程

4. **手动测试发布** (可选)
   ```bash
   # 通过 GitHub Actions 界面手动触发
   # 选择 "Publish to TestPyPI" 选项
   ```

### CI/CD 状态监控

所有工作流都有详细的日志和状态报告：

- ✅ **测试通过**: 所有 Python 版本测试成功
- 📊 **覆盖率报告**: 自动上传到 Codecov
- 🔍 **代码质量**: 格式、风格、安全检查
- 📦 **构建状态**: 包构建和元数据验证
- 🚀 **发布状态**: PyPI 发布成功

### 环境配置

项目需要在 GitHub 和 PyPI 中进行配置，以支持自动化发布流程。

#### 🔧 必需配置

##### 1. PyPI Trusted Publishing 配置 ⭐ 推荐
**最安全的方式，无需在 GitHub 中存储 PyPI 密钥**

**配置步骤**：
1. 登录 [PyPI](https://pypi.org/)
2. 进入项目 `czsc` 的管理页面
3. 点击 "Settings" → "Publishing" 
4. 点击 "Add a new publisher"
5. 填写以下信息：
   ```
   PyPI project name: czsc
   Owner: waditu
   Repository name: czsc  
   Workflow name: python-publish.yml
   Environment name: pypi
   ```
6. 保存配置

**可选：TestPyPI 配置**（用于测试发布）：
1. 登录 [TestPyPI](https://test.pypi.org/)
2. 重复上述步骤，环境名设为 `testpypi`

##### 2. GitHub 环境 (Environments) 配置

**操作路径**：`https://github.com/waditu/czsc/settings/environments`

**创建环境**：
1. 点击 "New environment"
2. 创建以下环境：
   - `pypi` - 用于正式发布到 PyPI
   - `testpypi` - 用于测试发布（可选）
3. 保存配置

**环境保护规则**（可选）：
- 设置必需的审查者
- 限制特定分支才能部署
- 设置等待时间

#### 🔐 可选的 Secrets 配置

##### 1. Codecov Token（推荐）
**用途**：代码覆盖率报告集成

**配置步骤**：
1. 访问 [Codecov](https://codecov.io/)
2. 使用 GitHub 账号登录
3. 添加仓库 `waditu/czsc`
4. 复制提供的 token
5. 在 GitHub 仓库中添加 Secret：
   ```
   路径：Settings → Secrets and variables → Actions → New repository secret
   Name: CODECOV_TOKEN
   Value: [从 Codecov 复制的 token]
   ```

##### 2. 备用方案：传统 PyPI API Token（不推荐）
**仅在无法使用 Trusted Publishing 时使用**

| Secret 名称 | 获取方式 | 说明 |
|------------|----------|------|
| `PYPI_API_TOKEN` | PyPI 账户设置 → API tokens | 正式发布用 |
| `TEST_PYPI_API_TOKEN` | TestPyPI 账户设置 → API tokens | 测试发布用 |

#### ⚙️ 权限配置

工作流需要以下权限（已在 workflow 文件中配置）：

| 权限 | 用途 | 状态 |
|------|------|------|
| `id-token: write` | Trusted Publishing 身份验证 | ✅ 已配置 |
| `contents: write` | GitHub Release 文件上传 | ✅ 已配置 |
| `packages: write` | GitHub Packages 发布（如需要） | 可选 |

#### 🔍 配置验证

##### 验证配置是否正确
```bash
# 1. 本地构建测试
uv build
uv run twine check dist/*

# 2. 手动触发测试发布
# GitHub Actions → Build & Publish → Run workflow → 选择 "TestPyPI"

# 3. 创建测试 Release
git tag v0.9.69-test
git push origin v0.9.69-test
# 在 GitHub 创建 pre-release 验证完整流程
```

##### 配置检查清单
- [ ] PyPI Trusted Publishing 已配置
- [ ] GitHub 环境 `pypi` 已创建
- [ ] GitHub 环境 `testpypi` 已创建（可选）
- [ ] Codecov token 已添加（可选）
- [ ] 工作流权限正确配置
- [ ] 测试发布流程正常

#### 🚨 安全提醒

**✅ 推荐使用**：
- Trusted Publishing（无需存储密钥）
- GitHub Environment 保护
- 自动 token 生成

**❌ 避免使用**（旧方式）：
- `PYPI_USERNAME` / `PYPI_PASSWORD`
- `TWINE_USERNAME` / `TWINE_PASSWORD`  
- 长期有效的 API tokens

#### 🆘 常见问题

**Q: Trusted Publishing 配置失败**
```bash
# 检查配置信息是否完全匹配：
Repository: waditu/czsc
Workflow file: python-publish.yml
Environment: pypi（区分大小写）
```

**Q: 环境访问被拒绝**
```bash
# 确保：
1. 环境名称正确（pypi/testpypi）
2. workflow 文件中的 environment 配置匹配
3. 分支保护规则允许该操作
```

**Q: 发布时权限错误**
```bash
# 检查 workflow 文件中的权限配置：
permissions:
  id-token: write  # 必需用于 Trusted Publishing
  contents: write  # 用于 GitHub Release
```

## 故障排除

### 常见问题

1. **UV 安装失败**
   ```bash
   # 使用官方安装脚本
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **依赖冲突**
   ```bash
   # 清理缓存重新安装
   uv cache clean
   uv sync --extra all
   ```

3. **测试失败**
   ```bash
   # 本地调试
   uv run pytest -v --tb=short
   ```

4. **发布失败**
   - 检查版本号是否已存在
   - 验证 Trusted Publishing 配置
   - 查看 GitHub Actions 日志

### 性能优化

- UV 缓存默认存储在 `~/.cache/uv/`
- CI 中使用了依赖缓存加速构建
- 并行任务执行减少总体运行时间

### 安全考虑

- 使用 Trusted Publishing 避免密钥泄露
- 自动化安全扫描 (safety, bandit)
- 依赖许可证合规检查
- 包签名验证 (Sigstore)

## 贡献指南

1. Fork 项目并创建功能分支
2. 本地开发并运行测试
3. 确保代码质量检查通过
4. 提交 Pull Request
5. 等待 CI 检查通过后合并

所有提交都会自动触发完整的 CI 流程，确保代码质量和项目稳定性。 