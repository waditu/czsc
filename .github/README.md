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

## UV 集成优势

### 🚀 性能提升
- 依赖安装速度比传统 pip 快 10-100 倍
- 并行处理多个 Python 版本

### 🔒 可重现性
- 锁定文件确保环境一致性
- 精确的依赖版本控制

### 🛠️ 现代化工具链
- 基于 pyproject.toml 标准
- 一体化包管理解决方案

### 📦 简化的构建流程
- 无需复杂的 setup.py 配置
- 自动化的包构建和发布

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

项目需要在 GitHub 中配置以下环境和密钥：

#### 环境 (Environments)
- `testpypi`: 用于测试发布
- `pypi`: 用于正式发布

#### 权限 (Permissions)
- `id-token: write`: 用于 Trusted Publishing
- `contents: write`: 用于 GitHub Release

#### 推荐的 PyPI 配置
使用 Trusted Publishing 替代传统的用户名/密码：
1. 在 PyPI 项目设置中配置 Trusted Publisher
2. 指定 GitHub 仓库和工作流文件

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