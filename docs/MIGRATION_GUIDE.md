# CZSC Utils 模块重构迁移指南

**最后更新**: 2026-02-16

## 概述

CZSC utils 模块已完成重构，采用更清晰的模块化结构。所有旧的导入方式仍然有效（向后兼容），但推荐使用新的导入方式。

## ✅ 重构完成状态

**旧文件已删除**: 9个重复文件已移除
- ✅ 所有导入已更新
- ✅ 向后兼容性已保持
- ✅ 测试通过

## 新的目录结构

```
czsc/utils/
├── plotting/        # 可视化工具
│   ├── __init__.py
│   ├── backtest.py   # 回测可视化 (原 plot_backtest.py)
│   ├── weight.py     # 权重可视化 (原 plot_weight.py)
│   ├── kline.py      # K线图表 (原 plotly_plot.py)
│   └── common.py     # 公共函数和常量 (新增)
├── data/            # 数据处理
│   ├── __init__.py
│   ├── cache.py      # 磁盘缓存 (原 cache.py)
│   ├── client.py     # 数据客户端 (原 data_client.py)
│   ├── validators.py # 数据验证 (新增)
│   └── converters.py # 格式转换 (新增)
├── crypto/          # 加密工具
│   ├── __init__.py
│   └── fernet.py     # Fernet加密 (原 fernet.py)
├── analysis/        # 分析工具
│   ├── __init__.py
│   ├── stats.py      # 统计分析 (原 stats.py)
│   ├── corr.py       # 相关性 (原 corr.py)
│   └── events.py     # 事件分析 (原 events.py)
└── __init__.py      # 向后兼容导出
```

## 导入方式对照表

### 绘图函数 (Plotting)

#### 回测可视化

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.plot_backtest import plot_colored_table
from czsc.utils.plot_backtest import plot_cumulative_returns
from czsc.utils.plot_backtest import plot_monthly_heatmap

# ✅ 新方式（推荐）
from czsc.utils.plotting.backtest import plot_colored_table
from czsc.utils.plotting.backtest import plot_cumulative_returns
from czsc.utils.plotting.backtest import plot_monthly_heatmap

# ✅ 向后兼容方式（通过 utils.__init__ 重新导出）
from czsc.utils import plot_colored_table
from czsc.utils import plot_cumulative_returns
from czsc.utils import plot_monthly_heatmap
```

**可用函数**:
- `plot_cumulative_returns()` - 累计收益曲线
- `plot_drawdown_analysis()` - 回撤分析
- `plot_daily_return_distribution()` - 日收益分布
- `plot_monthly_heatmap()` - 月度收益热力图
- `plot_backtest_stats()` - 回测统计概览
- `plot_colored_table()` - 带颜色编码的表格
- `plot_long_short_comparison()` - 多空对比

#### 权重可视化

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.plot_weight import plot_weight_histogram_kde
from czsc.utils.plot_weight import plot_turnover_overview

# ✅ 新方式（推荐）
from czsc.utils.plotting.weight import plot_weight_histogram_kde
from czsc.utils.plotting.weight import plot_turnover_overview
from czsc.utils.plotting.weight import plot_weight_time_series  # 新增

# ✅ 向后兼容方式
from czsc.utils import plot_weight_histogram_kde
from czsc.utils import plot_turnover_overview
from czsc.utils import plot_weight_time_series
```

**可用函数**:
- `plot_weight_histogram_kde()` - 权重分布直方图
- `plot_weight_cdf()` - 累积分布函数
- `plot_turnover_overview()` - 换手率总览
- `plot_turnover_cost_analysis()` - 成本分析
- `plot_weight_time_series()` - 权重时序分析 (新增)

#### K线图表

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.plotly_plot import KlineChart

# ✅ 新方式（推荐）
from czsc.utils.plotting.kline import KlineChart

# ✅ 向后兼容方式
from czsc.utils import KlineChart
```

### 数据处理 (Data)

#### 缓存

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.cache import DiskCache, home_path, disk_cache
from czsc.utils.cache import clear_cache, get_dir_size

# ✅ 新方式（推荐）
from czsc.utils.data.cache import DiskCache, home_path, disk_cache
from czsc.utils.data.cache import clear_cache, get_dir_size

# ✅ 向后兼容方式
from czsc.utils import DiskCache, home_path
from czsc.utils import disk_cache, clear_cache, get_dir_size
```

#### 数据客户端

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.data_client import DataClient
from czsc.utils.data_client import set_url_token, get_url_token

# ✅ 新方式（推荐）
from czsc.utils.data.client import DataClient
from czsc.utils.data.client import set_url_token, get_url_token

# ✅ 向后兼容方式
from czsc.utils import DataClient
from czsc.utils import set_url_token, get_url_token
```

#### 数据验证（新增）

```python
# ✅ 新功能
from czsc.utils.data.validators import (
    validate_dataframe_columns,
    validate_datetime_index,
    validate_numeric_column,
    validate_date_range,
    validate_no_duplicates,
    validate_weight_data
)
```

#### 数据转换（新增）

```python
# ✅ 新功能
from czsc.utils.data.converters import (
    to_standard_kline_format,
    pivot_weight_data,
    normalize_symbol,
    resample_to_period,
    ensure_datetime_column,
    flatten_multiindex_columns
)
```

### 加密工具 (Crypto)

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.fernet import generate_fernet_key
from czsc.utils.fernet import fernet_encrypt, fernet_decrypt

# ✅ 新方式（推荐）
from czsc.utils.crypto.fernet import generate_fernet_key
from czsc.utils.crypto.fernet import fernet_encrypt, fernet_decrypt

# ✅ 向后兼容方式
from czsc.utils import generate_fernet_key
from czsc.utils import fernet_encrypt, fernet_decrypt
```

### 分析工具 (Analysis)

#### 统计分析

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.stats import daily_performance
from czsc.utils.stats import holds_performance, top_drawdowns

# ✅ 新方式（推荐）
from czsc.utils.analysis.stats import daily_performance
from czsc.utils.analysis.stats import holds_performance, top_drawdowns

# ✅ 向后兼容方式
from czsc.utils import daily_performance
from czsc.utils import holds_performance, top_drawdowns
```

#### 相关性分析

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.corr import nmi_matrix, cross_sectional_ic

# ✅ 新方式（推荐）
from czsc.utils.analysis.corr import nmi_matrix, cross_sectional_ic

# ✅ 向后兼容方式
from czsc.utils import nmi_matrix, cross_sectional_ic
```

#### 事件分析

```python
# ❌ 旧方式（已删除源文件）
from czsc.utils.events import overlap

# ✅ 新方式（推荐）
from czsc.utils.analysis.events import overlap

# ✅ 向后兼容方式
from czsc.utils import overlap
```

## 迁移步骤

### 对于新项目

直接使用新的导入方式：

```python
from czsc.utils.plotting.backtest import plot_colored_table
from czsc.utils.data.cache import DiskCache
from czsc.utils.crypto import generate_fernet_key
```

### 对于现有项目

有两种选择：

#### 选项 1: 继续使用旧的导入方式（推荐，零修改）

```python
# 继续使用这种方式，完全兼容
from czsc.utils import home_path, DiskCache
from czsc.utils import plot_colored_table
```

#### 选项 2: 逐步迁移到新方式

1. 批量替换导入语句：
```bash
# 示例：替换 plot_backtest 导入
sed -i 's/from czsc.utils.plot_backtest import/from czsc.utils.plotting.backtest import/g' *.py

# 替换 cache 导入
sed -i 's/from czsc.utils.cache import/from czsc.utils.data.cache import/g' *.py
```

2. 或者逐个文件手动更新

3. 运行测试确保无问题

## 常见问题

### Q: 我的旧代码还能运行吗？

A: **能**。所有旧的导入方式都通过 `czsc/utils/__init__.py` 重新导出，完全向后兼容。

### Q: 我需要立即更新代码吗？

A: **不需要**。旧的导入方式会一直支持。但推荐新项目使用新的导入方式，代码更清晰。

### Q: 新增的 validators 和 converters 是什么？

A: 这是重构时新增的工具函数，用于：
- **validators**: 验证数据格式、列名、类型等
- **converters**: 格式转换、数据透视、标准化等

### Q: plot_weight_time_series 函数在哪里？

A: 这个函数在原始文件中没有实现，重构时添加为 `plot_turnover_overview` 的别名，保持兼容性。

### Q: 为什么要重构？

A: 
1. **模块化** - 相关功能集中管理
2. **可维护性** - 代码组织更清晰
3. **可扩展性** - 便于添加新功能
4. **消除重复** - 避免同一功能多处存在

## 优势

### 1. 更清晰的代码组织

```python
# 旧方式 - 不清楚函数来自哪个领域
from czsc.utils import (
    plot_colored_table,  # 是绘图？
    DiskCache,           # 是缓存？
    generate_fernet_key  # 是加密？
)

# 新方式 - 一目了然
from czsc.utils.plotting.backtest import plot_colored_table
from czsc.utils.data.cache import DiskCache
from czsc.utils.crypto import generate_fernet_key
```

### 2. 避免命名冲突

模块化避免了函数名冲突，每个子模块有自己的命名空间。

### 3. 便于维护和扩展

相关功能集中在一起，更容易维护和添加新功能。

## 参考文档

- [重构报告](./REFACTORING_REPORT.md)
- [测试报告](./TEST_REPORT.md)
- [API 文档](https://czsc.readthedocs.io/)

## 支持

如有问题，请在 GitHub Issues 中提出：
https://github.com/waditu/czsc/issues

---

**版本**: CZSC 0.10.10+  
**更新时间**: 2026-02-16
