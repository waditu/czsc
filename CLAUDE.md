# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

CZSC（缠中说禅技术分析工具）是基于缠中说禅理论的综合性量化交易Python库，提供技术分析、信号生成、回测和市场分析等功能。本项目专注于实现缠论的分型、笔、线段等核心概念的自动识别，以及基于此的多级别量化交易策略。

## 常用开发命令

### UV 包管理 (项目使用UV管理依赖)
```bash
# 同步依赖并安装开发工具
uv sync --extra dev

# 安装所有依赖组合
uv sync --extra all

# 运行测试
uv run pytest

# 运行指定测试文件
uv run pytest test/test_analyze.py -v

# 运行单个测试函数
uv run pytest test/test_analyze.py::test_czsc_basic -v

# 带覆盖率的测试
uv run pytest --cov=czsc

# 代码格式化和检查
uv run black czsc/ test/ --line-length 120
uv run isort czsc/ test/
uv run flake8 czsc/ test/
```

### 测试规范
- 所有测试文件位于 `test/` 目录，使用 pytest 格式
- **关键原则**：测试数据统一通过 `czsc.mock` 模块获取，不要在测试中硬编码模拟数据
- 测试文件命名模式：`test_*.py`


## 代码架构

### 核心组件

1. **`czsc/analyze.py`** - 缠论分析核心类，实现分型、笔的自动识别
2. **`czsc/objects.py`** - 核心数据结构定义：
   - `RawBar`: 原始K线数据
   - `NewBar`: 去除包含关系后的处理K线
   - `Signal`, `Factor`, `Event`: 信号-因子-事件交易体系组件
   - `Position`: 持仓管理

3. **`czsc/traders/`** - 交易执行框架：
   - `base.py`: CzscSignals 和 CzscTrader 核心类
   - `cwc.py`: 权重交易客户端
   - `rwc.py`: Redis权重管理客户端

4. **`czsc/signals/`** - 按类别组织的信号生成函数：
   - `bar.py`: K线级别信号
   - `pos.py`: 持仓相关信号  
   - `cxt.py`: 上下文信号
   - 每个信号模块包含专业的技术分析函数

5. **`czsc/sensors/`** - 事件检测和特征分析：
   - `cta.py`: CTA研究框架
   - `feature.py`: 特征选择器和分析器
   - `event.py`: 事件匹配和检测

6. **`czsc/utils/`** - 工具模块：
   - `bar_generator.py`: K线数据生成和重采样
   - `cache.py`: 磁盘缓存工具
   - `st_components.py`: Streamlit仪表板组件
   - `ta.py`: 技术分析指标

### 信号-因子-事件-交易体系

项目实现了系统化的量化交易方法：
- **信号（Signals）**: 基础技术指标和市场状态
- **因子（Factors）**: 信号的线性组合
- **事件（Events）**: 因子的同类合并，代表市场事件
- **交易（Trading）**: 基于事件和风险管理的执行

### 多级别联立分析

CZSC 支持使用 `CzscTrader` 类进行多级别联立分析，可同时分析不同时间周期（如1分钟、5分钟、30分钟、日线）进行全面的市场决策。

## 开发指南

### 代码规范
- 行长度：120字符（在 pyproject.toml 中配置）
- 适当使用类型提示
- 遵循代码库中现有的命名约定

### 信号函数开发
- 信号函数应遵循飞书文档中的规范说明
- 所有信号函数必须经过适当测试
- 使用 `czsc/signals/` 中现有的信号模板作为参考

### 依赖管理（UV配置）
- 核心运行时依赖定义在 `pyproject.toml` 的 `[project.dependencies]` 中
- 开发依赖在 `[project.optional-dependencies.dev]` 中
- 测试依赖在 `[project.optional-dependencies.test]` 中
- 使用阿里云镜像源：`http://mirrors.aliyun.com/pypi/simple/`

## 关键环境变量和设置

- `czsc_min_bi_len`: 最小笔长度（来自 `czsc.envs`）
- `czsc_max_bi_num`: 最大笔数量（来自 `czsc.envs`）
- 缓存目录自动管理，具备大小监控功能

## 缓存管理

项目大量使用磁盘缓存：
- 缓存位置：`czsc.utils.cache.home_path`
- 清除缓存：`czsc.empty_cache_path()`
- 监控大小：`czsc.get_dir_size(home_path)`
- 当缓存超过1GB时会显示清理提示

## Streamlit集成

项目在 `czsc/utils/st_components.py` 中包含丰富的 Streamlit 分析组件，提供回测结果、相关性分析、因子分析等可视化工具。

## 重要文档和资源

- [项目文档](https://s0cqcxuy3p.feishu.cn/wiki/wikcn3gB1MKl3ClpLnboHM1QgKf)
- [信号函数编写规范](https://s0cqcxuy3p.feishu.cn/wiki/wikcnCFLLTNGbr2THqo7KtWfBkd)
- [API文档](https://czsc.readthedocs.io/en/latest/modules.html)
- [B站视频教程](https://space.bilibili.com/243682308/channel/series)