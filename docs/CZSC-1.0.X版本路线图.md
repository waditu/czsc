# CZSC 1.0.X 版本路线图

> 本文档基于 czsc 库最新代码（v0.10.11，2026-02-24）整理，规划 1.0.X 正式版本的发布进度及核心功能说明。

---

## 1. 重要功能说明

### 1.1 核心架构：Rust/Python 混合实现

CZSC 1.0.X 采用 **Rust/Python 混合架构**，通过 `rs-czsc` 扩展包提供高性能实现，同时保留 Python 纯实现作为回退方案。

```python
# 默认优先使用 Rust 实现，性能更高
# 可通过环境变量强制使用 Python 实现
import os
os.environ['CZSC_USE_PYTHON'] = '1'  # 强制使用 Python 版本
```

已迁移至 Rust 的模块：
- `CZSC` 缠论分析器（分型、笔识别）
- `BarGenerator` K线合成器
- `WeightBacktest` 持仓权重回测
- 核心数据对象：`RawBar`、`NewBar`、`FX`、`BI`、`ZS`、`Signal`、`Event`、`Position`
- 枚举类型：`Freq`、`Operate`、`Mark`、`Direction`

### 1.2 缠论核心分析（CZSC）

CZSC 类是缠论技术分析的核心，实现了自动识别分型、笔等缠论要素：

```python
from czsc.core import CZSC, format_standard_kline, Freq
from czsc.mock import generate_symbol_kines

df = generate_symbol_kines('000001', '30分钟', '20240101', '20240105')
bars = format_standard_kline(df, freq=Freq.F30)
czsc_obj = CZSC(bars)
```

**核心概念**：
- **分型（FX）**：顶分型（Mark.G）/ 底分型（Mark.D）
- **笔（BI）**：相邻分型构成的价格运动
- **线段（ZS）**：中枢结构识别
- **包含关系处理**：`remove_include()` 函数

### 1.3 K线合成与多级别联立

`BarGenerator` 支持 K 线的多级别合成，是多级别联立分析的基础：

```python
from czsc.core import BarGenerator, Freq

bg = BarGenerator(base_freq='1分钟', freqs=['5分钟', '30分钟', '日线'])
for bar in bars:
    bg.update(bar)
```

支持的 K 线周期：Tick、1/2/3/4/5/6/10/12/15/20/30/60/120 分钟、日线、周线、月线、季线、年线。

### 1.4 信号系统

CZSC 信号系统按类别组织，支持版本化命名（如 `V241013`）：

| 模块 | 说明 |
|------|------|
| `czsc.signals.bar` | K线级别信号 |
| `czsc.signals.pos` | 持仓相关信号 |
| `czsc.signals.cxt` | 上下文信号 |
| `czsc.signals.tas` | 技术指标信号（均线、MACD、RSI 等）|
| `czsc.signals.vol` | 成交量信号 |
| `czsc.signals.byi` | 笔、线段信号 |
| `czsc.signals.jcc` | 日本蜡烛图形态信号 |
| `czsc.signals.zdy` | 自定义信号 |

### 1.5 交易框架

**核心类**：
- `CzscSignals`：多级别信号计算
- `CzscTrader`：完整交易执行（信号 → 事件 → 持仓）
- `Position`：单仓位策略，管理开平仓逻辑
- `WeightBacktest`：按持仓权重回测

**策略开发基础**：
- `CzscStrategyBase`：策略抽象基类
- `CzscJsonStrategy`：JSON 配置化策略实现

**集成权重方法**：
```python
get_ensemble_weight(trader, method="mean")  # mean/max/min/vote 或自定义函数
```

### 1.6 持仓权重回测（WeightBacktest）

WeightBacktest 是 1.0.X 的核心回测引擎，支持：
- 基于持仓权重（-1 ~ 1）的向量化回测
- 多品种并行回测
- 止损方向控制（`stoploss_by_direction`）
- 回测统计：年化收益、最大回撤、夏普比率、胜率等

### 1.7 可视化组件（SVC）

`czsc.svc` 提供完整的 Streamlit 可视化组件库：

| 模块 | 包含组件 |
|------|----------|
| `returns` | 日收益、累计收益、月度收益、回撤、滚动绩效 |
| `correlation` | 相关性矩阵、截面IC、时序相关性、协整检验 |
| `factor` | 因子收益、因子分层、因子值、事件收益 |
| `backtest` | 权重回测、持仓回测、止损分析、分年回测 |
| `statistics` | 年度统计、分段统计、PSI、分类统计 |
| `strategy` | Optuna调参、CzscTrader展示、组合分析 |
| `weights` | 权重时序、权重分布、权重绝对值分析 |

### 1.8 数据连接器

支持多个主流数据源：

| 连接器 | 数据源 |
|--------|--------|
| `ts_connector` | Tushare（A股数据）|
| `tq_connector` | 天勤（期货实时数据）|
| `ccxt_connector` | CCXT（数字货币）|
| `research` | 内置研究数据接口 |

### 1.9 CTA 研究框架

`CTAResearch` 提供统一的 CTA 策略研究入口：
- 单品种交易回放（`replay`）
- 多品种回测优化
- 参数网格搜索
- 并行处理支持

### 1.10 探索性数据分析（EDA）

`czsc.eda` 模块提供量化研究常用分析工具：
- `vwap` / `twap`：成交量/时间加权均价
- `remove_beta_effects`：去除 Beta 影响
- `cross_sectional_strategy`：横截面策略
- `judge_factor_direction`：因子方向判断
- `monotonicity`：单调性分析
- `rolling_layers`：因子分层回测
- `mark_cta_periods`：CTA 行情分类
- `make_price_features`：价格特征工程

### 1.11 飞书集成（FSA）

`czsc.fsa` 模块提供飞书平台集成：
- 即时消息推送（`IM`）
- 电子表格读写（`SpreadSheets`）
- 多维表格操作（`BiTable`）
- 策略信息推送（`push_strategy_latest`）

---

## 2. 版本发布进度规划

### 当前状态（v0.10.11，2026-02-24）

✅ 已完成：
- Rust/Python 混合架构（核心模块已迁移 Rust）
- 核心 CZSC 算法（分型、笔识别）
- 多级别 BarGenerator
- 完整信号系统（bar/pos/cxt/tas/vol 等分类）
- CzscTrader + Position 交易框架
- WeightBacktest 权重回测引擎
- SVC Streamlit 可视化组件库
- 多数据源连接器（Tushare/天勤/CCXT）
- CTA 研究框架
- EDA 分析工具
- 飞书集成

⚠️ 待完善（1.0.0 前需完成）：
- 弃用 `Tick` 类（已标注 DeprecationWarning，1.0.0 将正式移除）
- API 稳定性保证（完成兼容性测试）
- 文档完善（所有公共函数 docstring）
- 测试覆盖率提升

---

### v1.0.0 — 正式首版（目标：2026 Q2）

**里程碑**：API 正式稳定，进入语义化版本管理

**核心变更**：
- 🔴 **Breaking**: 正式移除 `Tick` 类（使用 `RawBar` 替代）
- ✅ 稳定 `WeightBacktest` 公共 API，不再破坏性变更
- ✅ 稳定 `CzscTrader` / `CzscSignals` / `Position` 接口
- ✅ 稳定信号函数注册与解析机制
- ✅ 稳定 `BarGenerator` 多级别合成接口
- ✅ 完善 `czsc.core` 导出列表，确保 `from czsc import *` 正确工作
- ✅ `rs-czsc` Rust 实现与 Python 实现完全功能对齐
- ✅ 补全所有核心模块的 docstring 和类型提示
- ✅ 测试覆盖率 ≥ 80%
- ✅ 发布正式 PyPI 包，版本号 `1.0.0`

**发布条件**：
1. 所有已知 Breaking Change 已处理完毕
2. 核心功能全覆盖测试通过
3. `uv run pytest` 全部通过
4. 完整的 ReadTheDocs / API 文档更新

---

### v1.0.1 — 稳定性补丁（目标：1.0.0 发布后 2 周内）

**重点**：修复 1.0.0 上报的 Bug

- 🐛 修复 1.0.0 发现的回归问题
- 🐛 修复 Rust 版本与 Python 版本的边界差异
- 🐛 修复 `BarGenerator` 在特殊 K 线序列下的包含关系处理
- 📦 依赖版本锁定优化

---

### v1.0.2 — 性能与信号增强（目标：2026 Q3）

**重点**：性能优化 + 信号函数扩充

- ⚡ `WeightBacktest` 大规模多品种回测性能优化
- ⚡ `BarGenerator` 内存占用优化
- 📊 新增信号函数：
  - 更多蜡烛图形态信号（`jcc` 模块扩充）
  - 波动率类信号（`vol` 模块扩充）
  - 自适应均线信号
- 🛠️ `SignalsParser` 增强：支持信号函数热加载
- 🔗 新增聚宽（JoinQuant）数据连接器

---

### v1.0.3 — EDA 与因子分析增强（目标：2026 Q3）

**重点**：因子研究工具完善

- 📈 `czsc.eda` 新增：
  - `factor_ic_decay`：IC 衰减分析
  - `factor_turnover`：因子换手率分析
  - `factor_group_return`：分组收益分析
- 📊 SVC 新增可视化组件：
  - `show_ic_decay`：IC 衰减图
  - `show_factor_group_return`：分组收益图
- 🔬 `czsc.sensors.feature` 特征分析增强
- 📋 `plot_backtest.py` 新增策略对比图表

---

### v1.0.4 — 数据层增强（目标：2026 Q4）

**重点**：数据质量与接入扩展

- 🗄️ `DataClient` 接口标准化，支持统一配置管理
- ✅ `check_kline_quality` K 线质量检测增强
- 🔗 扩展数据连接器：
  - Wind 数据源适配
  - 米筐（RiceQuant）数据源适配
- 💾 `DiskCache` 支持 TTL 过期策略优化
- 📊 新增 `czsc.utils.data.validators` 数据校验工具

---

### v1.0.5 — 策略研究框架增强（目标：2026 Q4）

**重点**：CTA 研究与策略优化

- 🔍 `CTAResearch` 增强：
  - 支持 Walk-Forward 滚动优化
  - 支持 Monte Carlo 模拟
- ⚙️ `OpensOptimize` / `ExitsOptimize` 参数优化增强
- 🎯 新增策略评估指标：
  - Calmar Ratio
  - Sortino Ratio
  - 盈亏比
- 📊 `czsc.svc.strategy` 新增策略组合分析

---

## 3. API 稳定性承诺（1.0.X 系列）

进入 1.0.X 系列后，以下 API 将保持向后兼容，不会在 1.0.X 系列中破坏性变更：

### 核心稳定 API

```python
# 核心类
from czsc import CZSC, BarGenerator, WeightBacktest
from czsc import CzscTrader, CzscSignals, Position
from czsc import RawBar, NewBar, FX, BI, ZS, Signal, Event
from czsc import Freq, Operate, Mark, Direction

# 格式转换
from czsc import format_standard_kline

# 策略基类
from czsc import CzscStrategyBase, CzscJsonStrategy

# 数据工具
from czsc.utils import daily_performance, top_drawdowns, DataClient

# 信号工具
from czsc.traders import generate_czsc_signals, check_signals_acc
```

### 可能在 2.0.0 中变更的 API

- `czsc.connectors.*`：依赖第三方数据源，可能随数据源 API 变化
- `czsc.fsa.*`：依赖飞书 API，可能随飞书 API 变化
- 信号函数内部实现细节

---

## 4. 升级指南（0.10.x → 1.0.0）

### Breaking Changes

#### 1. 移除 `Tick` 类

```python
# 旧代码（0.10.x）
from czsc.py.objects import Tick  # DeprecationWarning

# 新代码（1.0.0）
from czsc import RawBar  # 使用 RawBar 替代 Tick
```

#### 2. 导入路径规范化

```python
# 推荐使用顶层导入（稳定）
from czsc import CZSC, BarGenerator, WeightBacktest

# 不推荐直接导入内部模块（可能变更）
from czsc.py.analyze import CZSC  # 不稳定
```

### 迁移工具

1.0.0 将提供 `czsc migrate` 命令行工具，自动检测代码中使用了弃用 API 的位置。

---

## 5. 环境要求

| 版本 | Python | 推荐安装 |
|------|--------|----------|
| 1.0.0 | ≥ 3.10 | `pip install czsc==1.0.0` |
| 1.0.x | ≥ 3.10 | `pip install czsc` |

**可选依赖**：
- `rs-czsc`：Rust 高性能实现（强烈推荐，默认自动使用）
- `streamlit`：Streamlit 可视化组件（使用 `czsc.svc` 时需要）
- `tushare`、`tqsdk`、`ccxt`：对应数据源连接器

```bash
# 安装全部依赖
pip install "czsc[all]"

# 仅安装核心依赖
pip install czsc

# 开发环境
uv sync --extra dev
```

---

## 6. 反馈与贡献

- 问题反馈：[GitHub Issues](https://github.com/waditu/czsc/issues)
- 项目文档：[飞书文档](https://s0cqcxuy3p.feishu.cn/wiki/wikcn3gB1MKl3ClpLnboHM1QgKf)
- 信号函数规范：[信号函数编写规范](https://s0cqcxuy3p.feishu.cn/wiki/wikcnCFLLTNGbr2THqo7KtWfBkd)
- API 文档：[ReadTheDocs](https://czsc.readthedocs.io/en/latest/modules.html)
- 视频教程：[B站](https://space.bilibili.com/243682308/channel/series)
