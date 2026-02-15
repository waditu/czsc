# CZSC Utils 模块迁移指南

## 概述

CZSC 的 `utils` 模块已重构为更清晰的模块化结构。本指南帮助您了解如何使用新的模块结构。

## 重要提示

**所有旧的导入方式仍然有效！** 我们保持了完整的向后兼容性，您不需要立即修改现有代码。

## 新的模块结构

### 1. 绘图模块 (`czsc.utils.plotting`)

**功能**: 所有可视化相关的工具

**子模块**:
- `backtest`: 回测可视化
- `weight`: 权重分析可视化  
- `kline`: K线图表
- `common`: 公共绘图函数和常量

**使用示例**:

```python
# 方式1: 从子模块直接导入
from czsc.utils.plotting.backtest import (
    plot_cumulative_returns,
    plot_drawdown_analysis,
    plot_colored_table,
)

# 方式2: 从 plotting 包导入（推荐）
from czsc.utils.plotting import (
    plot_cumulative_returns,
    plot_colored_table,
    KlineChart,
)

# 方式3: 旧的导入方式（仍然支持）
from czsc.utils.plot_backtest import plot_colored_table
from czsc.utils.plotly_plot import KlineChart
```

### 2. 数据模块 (`czsc.utils.data`)

**功能**: 数据处理、缓存、验证和转换

**子模块**:
- `cache`: 磁盘缓存工具
- `client`: 数据客户端
- `validators`: 数据验证器（新增）
- `converters`: 格式转换器（新增）

**使用示例**:

```python
# 缓存和客户端
from czsc.utils.data import (
    DiskCache,
    disk_cache,
    DataClient,
)

# 新增的验证工具
from czsc.utils.data import (
    validate_dataframe_columns,
    validate_datetime_index,
    validate_numeric_column,
)

# 新增的转换工具
from czsc.utils.data import (
    to_standard_kline_format,
    pivot_weight_data,
    normalize_symbol,
)

# 旧的导入方式（仍然支持）
from czsc.utils.cache import DiskCache
from czsc.utils.data_client import DataClient
```

### 3. 加密模块 (`czsc.utils.crypto`)

**功能**: 数据加密和解密

**使用示例**:

```python
# 新的导入方式
from czsc.utils.crypto import (
    generate_fernet_key,
    fernet_encrypt,
    fernet_decrypt,
)

# 旧的导入方式（仍然支持）
from czsc.utils.fernet import generate_fernet_key
```

### 4. 分析模块 (`czsc.utils.analysis`)

**功能**: 统计分析、相关性分析、事件分析

**子模块**:
- `stats`: 统计分析工具
- `corr`: 相关性分析
- `events`: 事件分析

**使用示例**:

```python
# 统计分析
from czsc.utils.analysis import (
    daily_performance,
    holds_performance,
    top_drawdowns,
)

# 相关性分析
from czsc.utils.analysis import (
    nmi_matrix,
    single_linear,
    cross_sectional_ic,
)

# 事件分析
from czsc.utils.analysis import overlap

# 旧的导入方式（仍然支持）
from czsc.utils.stats import daily_performance
from czsc.utils.corr import nmi_matrix
from czsc.utils.events import overlap
```

## 完整的导入对照表

### 绘图相关

| 功能 | 旧导入方式 | 新导入方式 |
|------|-----------|-----------|
| 回测图表 | `from czsc.utils.plot_backtest import ...` | `from czsc.utils.plotting import ...` |
| 权重图表 | `from czsc.utils.plot_weight import ...` | `from czsc.utils.plotting import ...` |
| K线图表 | `from czsc.utils.plotly_plot import KlineChart` | `from czsc.utils.plotting import KlineChart` |

### 数据相关

| 功能 | 旧导入方式 | 新导入方式 |
|------|-----------|-----------|
| 缓存工具 | `from czsc.utils.cache import DiskCache` | `from czsc.utils.data import DiskCache` |
| 数据客户端 | `from czsc.utils.data_client import DataClient` | `from czsc.utils.data import DataClient` |

### 加密相关

| 功能 | 旧导入方式 | 新导入方式 |
|------|-----------|-----------|
| 加密工具 | `from czsc.utils.fernet import ...` | `from czsc.utils.crypto import ...` |

### 分析相关

| 功能 | 旧导入方式 | 新导入方式 |
|------|-----------|-----------|
| 统计分析 | `from czsc.utils.stats import ...` | `from czsc.utils.analysis import ...` |
| 相关性分析 | `from czsc.utils.corr import ...` | `from czsc.utils.analysis import ...` |
| 事件分析 | `from czsc.utils.events import ...` | `from czsc.utils.analysis import ...` |

## 新增功能

### 数据验证器

```python
from czsc.utils.data import (
    validate_dataframe_columns,
    validate_datetime_index,
    validate_numeric_column,
    validate_weight_data,
)

import pandas as pd

# 验证DataFrame包含必需的列
df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
validate_dataframe_columns(df, ['a', 'b'], 'my_data')

# 验证DateTime索引
validate_datetime_index(df, 'my_data')

# 验证数值列
validate_numeric_column(df, 'a', 'my_data')
```

### 数据转换器

```python
from czsc.utils.data import (
    to_standard_kline_format,
    pivot_weight_data,
    normalize_symbol,
)

# 转换为标准K线格式
standard_df = to_standard_kline_format(
    df,
    dt_col='datetime',
    open_col='open_price',
)

# 权重数据透视
pivot_df = pivot_weight_data(weight_df)

# 标准化品种代码
symbol = normalize_symbol(' aapl ')  # 返回 'AAPL'
```

## 迁移建议

### 对于新项目
直接使用新的导入方式，享受更清晰的模块结构。

### 对于现有项目
1. **无需立即迁移** - 所有旧的导入都能正常工作
2. **逐步迁移** - 在修改代码时更新为新的导入方式
3. **IDE支持** - 新的结构提供更好的自动补全和文档

### 迁移示例

**旧代码**:
```python
from czsc.utils.plot_backtest import plot_colored_table
from czsc.utils.cache import DiskCache
from czsc.utils.stats import daily_performance
```

**新代码**:
```python
from czsc.utils.plotting import plot_colored_table
from czsc.utils.data import DiskCache
from czsc.utils.analysis import daily_performance
```

## 常见问题

### Q: 我必须修改现有代码吗？
**A**: 不需要。所有旧的导入方式都保持兼容。

### Q: 新的导入方式有什么好处？
**A**: 
- 更清晰的模块组织
- 更好的IDE支持和自动补全
- 更容易找到相关功能
- 新增的验证和转换工具

### Q: 如何查看某个函数的新位置？
**A**: 使用IDE的"查找定义"功能，或查看 `czsc/utils/__init__.py` 文件中的导入。

### Q: 遇到导入错误怎么办？
**A**: 
1. 确认您使用的是最新版本的CZSC
2. 尝试使用旧的导入方式
3. 查看文档或提交issue

## 获取帮助

- 查看完整的重构报告: `docs/REFACTORING_REPORT.md`
- 查看测试示例: `test/test_utils_refactored.py`
- 提交问题: GitHub Issues

## 总结

新的模块结构设计更清晰、更易于维护，同时完全保持向后兼容。您可以按照自己的节奏逐步迁移到新的导入方式。
