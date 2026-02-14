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
- 模拟数据使用 `generate_symbol_kines` 函数生成，支持多品种、多频率、可重现的随机数据


## 代码架构

### 核心组件

1. **`czsc/core.py`** - 混合架构核心模块，智能选择 Rust/Python 实现：
   - Rust 版本优先（rs-czsc），性能优化
   - Python 版本作为回退方案
   - 导入核心类：`CZSC`、`RawBar`、`NewBar`、`Signal`、`Event`、`Position` 等

2. **`czsc/py/`** - Python 实现的核心算法：
   - `analyze.py`: 缠论分析核心类，实现分型、笔的自动识别
   - `objects.py`: 核心数据结构定义
   - `bar_generator.py`: K线数据生成和重采样

3. **`czsc/traders/`** - 交易执行框架：
   - `base.py`: CzscSignals 和 CzscTrader 核心类
   - `cwc.py`: 权重交易客户端
   - `rwc.py`: Redis权重管理客户端
   - `dummy.py`: 模拟回测框架
   - `optimize.py`: 开仓平仓参数优化

4. **`czsc/signals/`** - 按类别组织的信号生成函数：
   - `bar.py`: K线级别信号
   - `pos.py`: 持仓相关信号  
   - `cxt.py`: 上下文信号
   - `tas.py`: 技术指标信号
   - `vol.py`: 成交量信号
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
   - `data_client.py`: 统一数据客户端接口
   - `plot_backtest.py`: **回测可视化工具（已优化）**
     - 提供 Plotly 交互式图表绘制函数
     - 支持累计收益曲线、回撤分析、收益分布、月度热力图等
     - 包含模块级常量（颜色、分位数等）和辅助函数
     - 所有函数支持 HTML 导出和深色/浅色主题
     - 主要函数：
       - `plot_cumulative_returns()`: 累计收益曲线
       - `plot_drawdown_analysis()`: 回撤分析图
       - `plot_daily_return_distribution()`: 日收益分布
       - `plot_monthly_heatmap()`: 月度收益热力图
       - `plot_backtest_stats()`: 回测统计概览（3图组合）
       - `plot_colored_table()`: 带颜色编码的绩效表格
       - `plot_long_short_comparison()`: 多空收益对比

7. **`czsc/svc/`** - 统计和可视化服务：
   - `backtest.py`: 回测分析工具
   - `factor.py`: 因子分析
   - `correlation.py`: 相关性分析
   - `statistics.py`: 统计分析工具

8. **`czsc/connectors/`** - 数据源连接器：
   - 支持天勤、Tushare、聚宽、CCXT等多个数据源
   - 统一的数据接口封装

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
- 信号函数版本化命名（如 `V241013`）便于管理
- **代码质量原则**：
  - **DRY（Don't Repeat Yourself）**: 提取重复代码为辅助函数
  - **KISS（Keep It Simple）**: 保持函数简洁，职责单一
  - **使用模块级常量**: 避免魔法值，集中管理配置
  - **类型提示优先**: 使用 `Literal`、`Optional` 等提升代码可读性
  - **向后兼容性**: 公共 API 修改需谨慎，避免破坏现有代码
  - **文档完整**: 所有公共函数必须有完整的 docstring

### 信号函数开发
- 信号函数应遵循飞书文档中的规范说明
- 所有信号函数必须经过适当测试
- 使用 `czsc/signals/` 中现有的信号模板作为参考
- 按类别组织信号函数（bar、pos、cxt、tas、vol等）

### 数据处理最佳实践
- 测试数据统一通过 `czsc.mock.generate_symbol_kines` 生成
- 使用 `format_standard_kline` 将DataFrame转换为RawBar对象列表
- 使用 `BarGenerator` 进行K线合成和多级别分析
- 通过 `DataClient` 统一访问不同数据源
- 注意使用磁盘缓存提高重复计算效率

### 数据格式转换
```python
# 从mock数据生成CZSC对象的正确模式
from czsc.core import CZSC, format_standard_kline, Freq
from czsc.mock import generate_symbol_kines

# 生成K线数据
df = generate_symbol_kines('000001', '30分钟', '20240101', '20240105')

# 转换为RawBar对象列表
bars = format_standard_kline(df, freq=Freq.F30)

# 创建CZSC分析对象
czsc_obj = CZSC(bars)
```

### 回测可视化最佳实践
```python
# 使用 plot_backtest.py 绘制回测图表
from czsc.utils.plot_backtest import (
    plot_cumulative_returns,
    plot_backtest_stats,
    plot_monthly_heatmap
)

# 准备日收益数据（index为日期，columns为策略收益）
dret = ...  # DataFrame with datetime index and returns columns

# 1. 绘制累计收益曲线
fig = plot_cumulative_returns(
    dret,
    title="策略累计收益",
    template="plotly",  # 或 "plotly_dark"
    to_html=False  # 返回 Figure 对象，True 则返回 HTML 字符串
)
fig.show()

# 2. 绘制综合回测统计图（包含回撤分析、收益分布、月度热力图）
fig = plot_backtest_stats(
    dret,
    ret_col="total",  # 指定收益列
    title="回测统计概览",
    template="plotly"
)
fig.show()

# 3. 单独绘制月度收益热力图
fig = plot_monthly_heatmap(dret, ret_col="total")
fig.show()

# 4. 导出为 HTML（用于报告）
html_str = plot_cumulative_returns(dret, to_html=True)
with open("backtest_report.html", "w", encoding="utf-8") as f:
    f.write(html_str)
```

**模块级常量使用：**
```python
from czsc.utils.plot_backtest import (
    COLOR_DRAWDOWN,
    COLOR_RETURN,
    QUANTILES_DRAWDOWN,
    MONTH_LABELS
)

# 使用预定义常量确保图表风格统一
# 避免硬编码颜色值和配置参数
```

### 依赖管理（UV配置）
- 核心运行时依赖定义在 `pyproject.toml` 的 `[project.dependencies]` 中
- 开发依赖在 `[project.optional-dependencies.dev]` 中
- 测试依赖在 `[project.optional-dependencies.test]` 中
- 使用 UV 进行依赖管理和虚拟环境控制
- 参考 `docs/UV管理开源项目指南.md` 获取详细指导

## 关键环境变量和设置

- `CZSC_USE_PYTHON`: 强制使用 Python 版本实现（默认优先使用 Rust 版本）
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

## Rust/Python 混合架构

项目核心功能使用 Rust 重构以提升性能：
- **版本控制**: 通过环境变量 `CZSC_USE_PYTHON` 控制，默认优先使用 Rust 版本
- **回退机制**: Rust 版本不可用时自动回退到 Python 版本（见 `czsc/core.py`）
- **核心模块**: 已迁移的模块包括 `CZSC` 分析器、K线生成器、枚举类型等
- **版本检测**: 运行时自动检测 `rs-czsc` 库可用性和版本信息

## 数据连接器支持

项目集成多个数据源连接器（见 `czsc/connectors/`）：
- `tq_connector.py`: 天勤数据源
- `ts_connector.py`: Tushare数据源
- `jq_connector.py`: 聚宽数据源
- `ccxt_connector.py`: 数字货币数据源
- `research.py`: 研究数据接口
- `cooperation.py`: 合作数据接口

## 回测和策略研究框架

### 策略开发基础（`czsc/strategies.py`）
- `CzscStrategyBase`: 策略开发的抽象基类
- `CzscJsonStrategy`: JSON配置化的策略实现
- 策略要素：品种参数、K线周期、信号配置、持仓策略
- 支持策略序列化和反序列化

### CTA研究框架（`czsc/sensors/cta.py`）
- `CTAResearch` 类提供统一的策略回测接口
- 支持单品种回放、多品种优化、参数网格搜索
- 并行处理支持，提升大规模回测效率
- 自动保存回测结果和策略配置

### 信号函数体系（`czsc/signals/`）
- 信号函数按类别组织：`bar.py`（K线级别）、`pos.py`（持仓）、`cxt.py`（上下文）等
- 版本化命名规范（如 `V241013`）便于管理和兼容性
- 支持信号匹配、分类和决策逻辑
- 信号配置支持动态加载和解析

### 特征分析工具（`czsc/sensors/`）
- `feature.py`: 特征选择器和滚动特征分析
- `event.py`: 事件匹配和检测
- `utils.py`: 特征工程工具函数

### 探索性数据分析（`czsc/eda.py`）
- `vwap`/`twap`: 成交量和时间加权平均价
- `remove_beta_effects`: 去除beta对因子的影响
- `cross_sectional_strategy`: 横截面策略分析
- `judge_factor_direction`: 因子方向判断
- `monotonicity`: 单调性分析
- `turnover_rate`: 换手率计算
- `make_price_features`: 价格特征工程

## 重要文档和资源

- [项目文档](https://s0cqcxuy3p.feishu.cn/wiki/wikcn3gB1MKl3ClpLnboHM1QgKf)
- [信号函数编写规范](https://s0cqcxuy3p.feishu.cn/wiki/wikcnCFLLTNGbr2THqo7KtWfBkd)
- [API文档](https://czsc.readthedocs.io/en/latest/modules.html)
- [B站视频教程](https://space.bilibili.com/243682308/channel/series)
- [UV管理开源项目指南](./docs/UV管理开源项目指南.md)：详细的UV包管理和开发工作流程指南

## 示例代码和用例

项目提供丰富的示例代码（`examples/` 目录）：

### 核心功能示例
- `30分钟笔非多即空.py`: 基础缠论策略实现
- `use_cta_research.py`: CTA研究框架使用
- `use_optimize.py`: 参数优化工具使用
- `策略持仓权重管理.ipynb`: 权重管理策略

### 数据源集成示例
- `TS数据源的形态选股.py`: Tushare数据源集成
- `test_offline/`: 离线测试和集成测试案例

### 开发工具示例
- `develop/`: 开发工具和测试脚本
- `signals_dev/`: 信号函数开发和测试
- `test_offline/`: 各种连接器和功能测试

### Streamlit应用
- `animotion/`: Streamlit可视化应用
  - `czsc_app.py`: 主应用界面
  - `czsc_human_replay.py`: 人工回放工具
  - `czsc_stream.py`: 实时数据流展示

### 文档资源
- `docs/`: 项目文档，包括开发日志、学习资料等
- `docs/source/`: Sphinx文档源文件

## 项目特色和最佳实践

1. **混合架构设计**: Rust性能优化 + Python灵活性
2. **多级别联立分析**: 支持多时间周期综合决策
3. **系统化信号体系**: 信号→因子→事件→交易的完整流程
4. **丰富的数据源**: 支持A股、期货、数字货币等多市场
5. **完善的测试框架**: 统一的模拟数据生成和测试规范
6. **可视化工具**: Streamlit组件库支持快速分析展示
7. **策略研究工具**: CTA框架、参数优化、回测分析一体化
8. **代码质量优化**: 遵循 DRY、KISS、SOLID 原则
   - 使用模块级常量消除魔法值
   - 提取辅助函数减少代码重复
   - 完善的类型提示（Type Hints）
   - 清晰的函数职责分离
   - 保持向后兼容性的 API 设计

### 代码优化案例（plot_backtest.py）

`czsc/utils/plot_backtest.py` 模块展示了代码优化的最佳实践：

**优化前的问题：**
- HTML 转换逻辑重复 8 次
- 年度分隔线添加代码重复 3 次
- 回撤计算逻辑重复 2 次
- 大量魔法值（颜色、分位数等）散落各处
- 函数过于复杂（`plot_backtest_stats` 有 165 行）

**优化措施：**

1. **提取辅助函数**（6 个）：
   ```python
   _figure_to_html()              # 统一 HTML 转换
   _add_year_boundary_lines()     # 统一年度分隔线
   _calculate_drawdown()          # 统一回撤计算
   _create_monthly_heatmap_data() # 统一月度数据准备
   _add_drawdown_annotation()     # 统一回撤标注
   _add_sigma_lines()             # 统一 Sigma 标注
   ```

2. **定义模块级常量**（10 个）：
   ```python
   COLOR_DRAWDOWN = "salmon"
   COLOR_RETURN = "#34a853"
   QUANTILES_DRAWDOWN = [0.05, 0.1, 0.2]
   SIGMA_LEVELS = [-3, -2, -1, 1, 2, 3]
   MONTH_LABELS = ['1月', '2月', ..., '12月']
   ```

3. **完善类型提示**：
   ```python
   TemplateType = Literal['plotly', 'plotly_dark', ...]
   def plot_cumulative_returns(..., template: TemplateType = "plotly", ...)
   ```

**优化效果：**
- ✅ 消除所有 HTML 转换重复代码（8 处 → 1 处）
- ✅ 消除所有年度分隔线重复（3 处 → 1 处）
- ✅ 消除所有回撤计算重复（2 处 → 1 处）
- ✅ 使用模块级常量替代魔法值
- ✅ 函数更简洁易读（165 行 → 129 行）
- ✅ 提升可维护性和可测试性
- ✅ 保持向后兼容性（API 未改变）

**参考文件：** `czsc/utils/plot_backtest.py:1-742`