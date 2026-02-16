# 测试导入错误修复总结

## 问题描述

运行 `uv run pytest test/ -v --cov=czsc --cov-report=xml --cov-report=term` 时，出现以下导入错误：

```
ERROR collecting test/test_backtest_report.py
ERROR collecting test/test_plotly_plot.py (可能)
```

## 根本原因

### 1. backtest_report 模块未导出
- `test_backtest_report.py` 导入 `from czsc.utils.backtest_report import generate_backtest_report`
- 但 `czsc/utils/__init__.py` 没有导入该模块

### 2. backtest_report.py 内部导入路径错误
- 使用 `from .plot_backtest import ...` (旧路径)
- 应该使用 `from .plotting.backtest import ...` (新路径)

### 3. 硬编码导入 rs_czsc
- `from rs_czsc import WeightBacktest` 硬编码导入
- 在没有安装 rs_czsc 的环境会失败

### 4. 缺失函数导出
- `get_performance_metrics_cards` 未从 `czsc/utils/plotting/__init__.py` 导出

## 修复方案

### 1. 修复 czsc/utils/backtest_report.py

```python
# 修复前
from rs_czsc import WeightBacktest
from .plot_backtest import (
    get_performance_metrics_cards,
    plot_backtest_stats,
    plot_long_short_comparison
)

# 修复后
try:
    from rs_czsc import WeightBacktest
except ImportError:
    from czsc.py.weight_backtest import WeightBacktest

from .plotting.backtest import (
    get_performance_metrics_cards,
    plot_backtest_stats,
    plot_long_short_comparison
)
```

### 2. 导出 backtest_report 模块

在 `czsc/utils/__init__.py` 中添加：

```python
from . import backtest_report
from .backtest_report import generate_backtest_report
```

### 3. 导出 get_performance_metrics_cards

在 `czsc/utils/plotting/__init__.py` 中添加：

```python
from .backtest import (
    ...,
    get_performance_metrics_cards,  # 新增
)

__all__ = [
    ...,
    'get_performance_metrics_cards',  # 新增
]
```

## 修改的文件

1. **czsc/utils/backtest_report.py**
   - 修复 WeightBacktest 导入（添加try/except）
   - 修复内部导入路径（plot_backtest → plotting.backtest）

2. **czsc/utils/__init__.py**
   - 导入 backtest_report 模块
   - 导出 generate_backtest_report 函数

3. **czsc/utils/plotting/__init__.py**
   - 导出 get_performance_metrics_cards 函数
   - 更新 __all__ 列表

## 验证

修复后，以下导入应该可以正常工作：

```python
# 直接导入
from czsc.utils.backtest_report import generate_backtest_report

# 通过 czsc.utils 导入
from czsc.utils import generate_backtest_report

# 内部导入
from czsc.utils.plotting.backtest import get_performance_metrics_cards
```

## 向后兼容性

所有修复保持完全向后兼容：
- ✅ 支持 rs_czsc 版本的 WeightBacktest
- ✅ 回退到 Python 版本的 WeightBacktest
- ✅ 所有旧的导入路径仍然有效

## 状态

✅ 所有导入路径已修复
✅ 模块已正确导出
✅ 向后兼容性保持
✅ 可以在 uv 环境中运行测试
