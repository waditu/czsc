# UV 管理开源项目指南

## 目录
2. [安装 UV](#安装-uv)
3. [项目迁移步骤](#项目迁移步骤)
4. [依赖管理最佳实践](#依赖管理最佳实践)
5. [常用命令参考](#常用命令参考)
6. [发布流程](#发布流程)
7. [常见问题解决](#常见问题解决)
8. [UV 启动脚本慢的分析方法](#uv-启动脚本慢的分析方法)

## 安装 UV

### Windows (PowerShell)
```powershell
# 使用 pip 安装
pip install uv

# 或使用 scoop
scoop install uv

# 或下载安装脚本
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Linux/macOS
```bash
# 使用 curl
curl -LsSf https://astral.sh/uv/install.sh | sh

# 或使用 pip
pip install uv

# 或使用 homebrew (macOS)
brew install uv
```

## 项目迁移步骤

### 1. 备份原项目
```bash
# 建议先备份整个项目
git checkout -b backup-before-uv-migration
git commit -am "备份：迁移到 UV 之前的状态"
```

### 2. 创建现代化的 pyproject.toml

如果项目只有 `requirements.txt` 和 `setup.py`，需要创建 `pyproject.toml`：

```toml
[build-system]
requires = ["hatchling"]  # 推荐使用 hatchling 作为构建后端
build-backend = "hatchling.build"

[project]
name = "your-project-name"
version = "0.1.0"  # 或从 __init__.py 动态读取
description = "项目简短描述"
readme = "README.md"
license = "MIT"  # 或其他许可证
authors = [
    { name = "Your Name", email = "your@email.com" }
]
keywords = ["keyword1", "keyword2"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
requires-python = ">=3.10"

# 核心运行时依赖
dependencies = [
    "requests>=2.25.0",
    "pandas>=1.0.0",
    # ... 其他核心依赖
]

# 可选依赖组
[project.optional-dependencies]
# 测试依赖
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock",
]

# 开发工具
dev = [
    "black",
    "isort", 
    "flake8",
    "mypy",
]

# 文档生成
docs = [
    "sphinx",
    "sphinx-rtd-theme",
]

# 完整开发环境
all = [
    "your-project[test,dev,docs]",
]

[project.urls]
Homepage = "https://github.com/username/project"
Repository = "https://github.com/username/project"
Documentation = "https://project.readthedocs.io"
"Bug Tracker" = "https://github.com/username/project/issues"

# 如果有命令行工具
[project.scripts]
your-cli = "your_package.cli:main"

# 构建配置
[tool.hatch.build.targets.wheel]
packages = ["src/your_package"]  # 如果使用 src 布局

# 或者简单布局
# packages = ["your_package"]
```

### 3. 迁移依赖分类

#### 分析现有依赖
```bash
# 查看当前依赖
cat requirements.txt
cat requirements-dev.txt  # 如果有的话
```

#### 依赖分类原则
- **核心依赖**: 项目运行必需的包
- **测试依赖**: 运行测试需要的包
- **开发依赖**: 开发时使用的工具（linting、formatting等）
- **文档依赖**: 生成文档需要的包

#### 示例分类
```toml
dependencies = [
    # 数据处理
    "pandas>=1.0.0",
    "numpy",
    
    # 网络请求
    "requests>=2.25.0",
    "aiohttp",
    
    # 配置和日志
    "pydantic>=2.0.0",
    "loguru",
]

[project.optional-dependencies]
test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-asyncio",
    "httpx",  # 用于测试 HTTP 请求
]

dev = [
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit",
]
```

### 4. 初始化 UV 环境

```bash
# 在项目根目录
cd your-project

# 同步依赖（创建虚拟环境并安装依赖）
uv sync

# 安装开发依赖
uv sync --extra dev

# 安装所有依赖
uv sync --extra all
```

### 5. 验证迁移

```bash
# 检查依赖树
uv tree

# 运行测试
uv run pytest

# 检查项目是否可以正常导入
uv run python -c "import your_package; print('导入成功')"

# 如果有命令行工具
uv run your-cli --help
```

## 依赖管理最佳实践

### 1. 依赖版本管理

#### 版本约束策略
```toml
dependencies = [
    # 主要版本锁定：允许小版本更新，避免重大变更
    "requests>=2.25.0,<3.0.0",
    
    # 最小版本：只指定最小版本，给用户更多选择
    "pandas>=1.0.0",
    
    # 精确版本：对于可能有破坏性变更的包
    "some-unstable-package==0.1.2",
    
    # 兼容版本：允许补丁级别更新
    "stable-package~=1.5.0",  # 等价于 >=1.5.0,<1.6.0
]
```

#### 依赖组织
```toml
dependencies = [
    # 按功能分组并添加注释
    
    # 核心数据处理
    "pandas>=1.0.0",
    "numpy",
    "pyarrow",
    
    # 网络和API
    "requests>=2.25.0",
    "httpx",
    
    # 配置和验证
    "pydantic>=2.0.0",
    "python-dotenv",
    
    # 日志和监控
    "loguru",
    "prometheus-client",
]
```

### 2. 可选依赖设计

```toml
[project.optional-dependencies]
# 按使用场景分组
web = [
    "fastapi>=0.100.0",
    "uvicorn",
]

database = [
    "sqlalchemy>=2.0.0",
    "psycopg2-binary",
]

redis = [
    "redis>=4.0.0",
]

# 组合依赖
full = [
    "your-project[web,database,redis]",
]

# 环境特定依赖
dev = [
    "black>=23.0.0",
    "isort>=5.12.0",
    "mypy>=1.0.0",
    "pre-commit",
]

test = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock",
    "factory-boy",
]
```

### 3. 环境管理

```bash
# 开发环境：安装所有依赖
uv sync --extra all

# 生产环境：只安装核心依赖
uv sync --no-dev

# 测试环境：安装核心 + 测试依赖
uv sync --extra test

# CI/CD 环境：使用锁定文件确保一致性
uv sync --frozen
```

## 常用命令参考

### 依赖管理
```bash
# 添加依赖
uv add requests pandas

# 添加开发依赖
uv add --dev pytest black

# 添加可选依赖
uv add --optional database sqlalchemy

# 移除依赖
uv remove requests

# 更新依赖
uv sync --upgrade

# 更新特定包
uv add requests@latest

# 查看过时的包
uv tree --outdated
```

### 环境管理
```bash
# 创建/同步环境
uv sync

# 安装可选依赖组
uv sync --extra dev,test

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# 运行命令
uv run python script.py
uv run pytest
uv run black .

# 查看环境信息
uv python list
uv python install 3.11
```

### 项目管理
```bash
# 查看项目信息
uv show

# 查看依赖树
uv tree

# 锁定依赖
uv lock

# 构建项目
uv build

# 发布到 PyPI
uv publish
```

## 发布流程

### 1. 版本管理

#### 动态版本（推荐）
```toml
[project]
dynamic = ["version"]

[tool.hatch.version]
path = "src/your_package/__init__.py"
```

#### 静态版本
```toml
[project]
version = "1.0.0"
```

### 2. 构建配置

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/your_package"]

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests", 
    "/docs",
    "/README.md",
    "/LICENSE",
]
exclude = [
    "/.git",
    "/.github",
    "/docs/_build",
]
```

### 3. 发布步骤

```bash
# 1. 更新版本号
# 编辑 __init__.py 或 pyproject.toml

# 2. 运行测试
uv run pytest

# 3. 构建包
uv build

# 4. 检查构建结果
ls dist/

# 5. 发布到 TestPyPI（测试）
uv publish --repository testpypi

# 6. 测试安装
pip install --index-url https://test.pypi.org/simple/ your-package

# 7. 发布到正式 PyPI
uv publish

# 8. 打标签
git tag v1.0.0
git push origin v1.0.0
```

## 常见问题解决

### 1. 迁移过程中的问题

#### Q: setup.py 中的复杂逻辑如何处理？
```python
# 原 setup.py 中的动态配置
import os
from setuptools import setup

def get_version():
    # 复杂的版本获取逻辑
    pass

def get_long_description():
    # 读取多个文件
    pass

setup(
    version=get_version(),
    long_description=get_long_description(),
    # ...
)
```

**解决方案**: 使用 hatchling 的动态配置
```toml
[project]
dynamic = ["version", "description"]

[tool.hatch.version]
path = "src/your_package/__init__.py"

[tool.hatch.metadata]
allow-direct-references = true

[tool.hatch.build.hooks.custom]
# 可以编写自定义构建钩子
```

#### Q: requirements.txt 有 -e . 怎么处理？
```bash
# 原 requirements.txt
-e .
requests>=2.25.0
```

**解决方案**: UV 会自动以可编辑模式安装当前项目
```bash
uv sync  # 自动以可编辑模式安装当前项目
```

#### Q: 有多个 requirements 文件怎么处理？
```
requirements/
├── base.txt
├── dev.txt
├── test.txt
└── prod.txt
```

**解决方案**: 转换为可选依赖组
```toml
[project.optional-dependencies]
dev = [
    # 从 requirements/dev.txt 迁移
]
test = [
    # 从 requirements/test.txt 迁移  
]
```

### 2. 依赖解析问题

#### Q: 依赖冲突怎么办？
```bash
# 查看冲突详情
uv sync --verbose

# 使用依赖覆盖
```

```toml
[tool.uv]
override-dependencies = [
    "conflicting-package==1.0.0",
]
```

#### Q: 私有包怎么处理？
```toml
dependencies = [
    "private-package @ git+https://github.com/company/private-repo.git",
]

# 或使用私有 PyPI 源
[tool.uv.sources]
private-package = { index = "private-pypi" }

[[tool.uv.index]]
name = "private-pypi"
url = "https://pypi.company.com/simple/"
```

### 3. 性能优化

#### Q: 如何加速依赖安装？
```bash
# 使用本地缓存
export UV_CACHE_DIR="/path/to/cache"

# 并行安装
export UV_CONCURRENT_INSTALLS=10

# 使用国内镜像
uv sync --index-url https://pypi.tuna.tsinghua.edu.cn/simple/
```

#### Q: 如何减少构建时间？
```toml
[tool.hatch.build.targets.wheel]
exclude = [
    "tests/",
    "docs/", 
    ".github/",
    "*.pyc",
]
```

### 4. CI/CD 集成

#### GitHub Actions 示例
```yaml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Install uv
      uses: astral-sh/setup-uv@v2
      with:
        version: "latest"
    
    - name: Set up Python
      run: uv python install ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: uv sync --extra test
    
    - name: Run tests
      run: uv run pytest
    
    - name: Build package
      run: uv build
```

## 高级配置

### 1. 工作空间管理

对于单仓库多包项目：

```toml
# 根目录 pyproject.toml
[tool.uv.workspace]
members = ["packages/*"]

# packages/package-a/pyproject.toml
[project]
name = "package-a"
# ...

# packages/package-b/pyproject.toml  
[project]
name = "package-b"
dependencies = ["package-a"]  # 内部依赖
```

### 2. 自定义脚本

```toml
[project.scripts]
your-cli = "your_package.cli:main"

[tool.uv.scripts]
# 开发脚本
test = "pytest tests/"
lint = "black . && isort . && flake8"
docs = "sphinx-build docs docs/_build"
clean = "rm -rf dist/ build/ *.egg-info/"

# 复合脚本
check = ["lint", "test"]
```

### 3. 环境变量配置

```toml
[tool.uv]
# 全局配置
index-url = "https://pypi.org/simple/"
extra-index-url = ["https://download.pytorch.org/whl/cpu"]

# 开发环境变量
[tool.uv.env]
PYTHONPATH = "src"
DEBUG = "1"
```


## UV 启动脚本慢的分析方法

目标：判断慢在 uv 的环境解析/同步，还是 Python 本身的导入/IO。

- 1) 基线对比（先看 uv 带来的额外开销）
```bash
# 纯 Python
time python -c "pass"

# uv，不同步环境（只测 uv 调度 + 启动）
time uv run --no-sync python -c "pass"

# 基准测试（可选）
hyperfine "python -c 'pass'" "uv run --no-sync python -c 'pass'"
```

- 2) 排除依赖解析/同步
```bash
# 锁定并一次性同步
uv lock
uv sync

# 运行时跳过同步
uv run --no-sync python your_script.py

# 观察是否在做解析/安装
uv run -vv python your_script.py
```

- 3) 固定解释器，避免解释器探测耗时
```bash
uv run --no-sync --python 3.11 python your_script.py
```

- 4) 分析 Python 导入开销（多数“启动慢”在这里）
```bash
# 打印各模块导入耗时
uv run --no-sync python -X importtime your_script.py 2> import.log
# 关注 import.log 顶部最慢的模块，做延迟导入或精简依赖
```

- 5) 系统层 IO/杀毒排查
```bash
# Linux
strace -f -tt -o trace.log uv run --no-sync python -c "pass"

# macOS（需要 sudo）
sudo dtruss -t wallclock uv run --no-sync python -c "pass"

# Windows
# 使用 Process Monitor 观察磁盘/杀毒拦截；将项目/.venv/.uv 加入 Defender 排除
```

- 6) 常见原因与对策
  - 首次运行/未锁定导致解析与安装：先 uv lock && uv sync，再 uv run --no-sync
  - 解释器探测慢：使用 --python 指定版本
  - 脚本大量/重量级导入：用 -X importtime 找到热点，做延迟导入、移除未用库
  - 磁盘/杀毒干扰：排除 .venv、.uv、项目目录；避免网络盘，改用本地 SSD
  - 频繁变更依赖：在 CI/生产使用 uv sync --frozen，开发期尽量减少每次运行触发的同步
