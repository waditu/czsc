# CZSC 单元测试覆盖率规范

本文档描述CZSC项目的单元测试规范、mock数据格式要求和测试覆盖率目标。

## 目录

- [Mock数据格式规范](#mock数据格式规范)
- [测试文件组织](#测试文件组织)
- [测试编写规范](#测试编写规范)
- [覆盖率要求](#覆盖率要求)
- [运行测试](#运行测试)
- [CI/CD集成](#cicd集成)

---

## Mock数据格式规范

### 数据来源

所有测试必须使用 `czsc.mock.generate_symbol_kines` 生成模拟数据：

```python
from czsc import mock

df = mock.generate_symbol_kines(
    symbol="000001",      # 品种代码
    freq="日线",          # K线频率
    sdt="20220101",       # 开始日期（至少3年前）
    edt="20250101",       # 结束日期
    seed=42               # 随机种子（确保可重现）
)
```

### 数据结构

生成的DataFrame包含以下列：

| 列名 | 类型 | 说明 |
|------|------|------|
| `dt` | datetime | K线时间戳 |
| `symbol` | str | 品种代码 |
| `open` | float | 开盘价 |
| `close` | float | 收盘价 |
| `high` | float | 最高价 |
| `low` | float | 最低价 |
| `vol` | float | 成交量 |
| `amount` | float | 成交额 |

### 数据质量要求

1. **OHLC价格关系**：必须满足 `high >= close >= low` 和 `high >= open >= low`
2. **时间范围**：标准测试使用3-5年数据，边界测试可使用较短数据
3. **可重现性**：必须设置固定seed（推荐42）确保测试可重现
4. **频率支持**：
   - `1分钟`、`5分钟`、`15分钟`、`30分钟`、`60分钟`
   - `日线`、`周线`、`月线`

### 示例：标准测试数据

```python
def get_test_data():
    """获取标准测试数据（3年+）"""
    df = mock.generate_symbol_kines(
        symbol="000001",
        freq="日线",
        sdt="20220101",  # 3年前
        edt="20250101",  # 当前
        seed=42
    )
    return df
```

### 示例：多频率测试

```python
def get_multi_freq_test_data():
    """获取多频率测试数据"""
    freqs = ["1分钟", "5分钟", "30分钟", "日线"]
    data = {}

    for freq in freqs:
        df = mock.generate_symbol_kines(
            symbol="000001",
            freq=freq,
            sdt="20240101",
            edt="20240601",
            seed=42
        )
        data[freq] = df

    return data
```

---

## 测试文件组织

### 目录结构

```
test/
├── README_TEST_COVERAGE.md       # 本文档
├── test_*.py                     # 所有测试文件
│   ├── test_core.py              # 核心功能测试
│   ├── test_utils_*.py           # 工具模块测试
│   ├── test_signals.py           # 信号函数测试
│   ├── test_traders.py           # 交易器测试
│   └── test_sensors.py           # 传感器测试
└── conftest.py                   # pytest配置（如有）
```

### 命名规范

- **测试文件**：`test_<module_name>.py`
- **测试类**：`Test<ClassName>` 或 `Test<feature_name>`
- **测试函数**：`test_<function_name>` 或 `test_<feature_description>`

### 示例：测试文件结构

```python
# test_signals.py

"""
test_signals.py - 信号生成函数单元测试

Mock数据格式说明:
- 数据来源: czsc.mock.generate_symbol_kines
- 数据列: dt, symbol, open, close, high, low, vol, amount
- 时间范围: 20200101-20250101（5年数据，满足3年+要求）
- 频率: 30分钟 / 60分钟 / 日线
- Seed: 42（确保可重现）
"""

import pytest
from czsc import mock
from czsc.core import CZSC, format_standard_kline, Freq


def get_czsc_obj(symbol="000001", freq="日线", sdt="20200101", edt="20250101"):
    """获取CZSC对象用于测试"""
    df = mock.generate_symbol_kines(symbol=symbol, freq=freq, sdt=sdt, edt=edt, seed=42)
    bars = format_standard_kline(df, freq=freq)
    return CZSC(bars)


class TestBarSignals:
    """测试K线级别信号"""

    def test_is_third_buy(self):
        """测试三买信号"""
        c = get_czsc_obj()
        if c is None or len(c.bars_raw) < 100:
            pytest.skip("数据不足，跳过测试")

        signal = is_third_buy(c, di=1)
        assert signal is None or isinstance(signal, (bool, dict))
```

---

## 测试编写规范

### 1. 测试文档

每个测试文件必须包含文档说明：

```python
"""
test_<module>.py - 模块测试说明

Mock数据格式说明:
- 数据来源: czsc.mock.generate_symbol_kines
- 数据列: dt, symbol, open, close, high, low, vol, amount
- 时间范围: 20220101-20250101（3年数据，满足3年+要求）
- 频率: 日线 / 30分钟
- Seed: 42（确保可重现）

测试覆盖范围:
- 功能1：说明
- 功能2：说明
"""
```

### 2. 边界情况测试

每个测试函数应包含以下边界情况：

```python
class TestFunction:
    """测试某功能"""

    def test_normal_case(self):
        """测试正常情况"""
        pass

    def test_empty_array(self):
        """测试空数组"""
        pass

    def test_single_value(self):
        """测试单值"""
        pass

    def test_with_nan(self):
        """测试包含NaN"""
        pass

    def test_with_inf(self):
        """测试包含Inf"""
        pass

    def test_with_zeros(self):
        """测试全0数据"""
        pass
```

### 3. 断言规范

使用清晰的断言消息：

```python
# 推荐
assert len(result) > 0, "结果不应为空"
assert isinstance(signal, dict), "信号应为字典类型"

# 避免
assert len(result) > 0
assert isinstance(signal, dict)
```

### 4. 异常处理

对于可选依赖或环境问题，使用 `pytest.skip`：

```python
try:
    from czsc.sensors.cta import CTAResearch
    cta = CTAResearch(symbol="000001", df=df)
    assert cta is not None
except ImportError as e:
    pytest.skip(f"CTAResearch模块导入失败: {e}")
```

### 5. 数据验证

测试前验证数据充足性：

```python
def test_function():
    df = get_test_data()

    if len(df) < 100:
        pytest.skip("数据不足，跳过测试")

    # 执行测试
    result = some_function(df)
    assert result is not None
```

---

## 覆盖率要求

### 整体目标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 整体覆盖率 | ~40% | 80%+ |
| 核心模块覆盖率 | 60% | 90%+ |
| 工具模块覆盖率 | 60% | 80%+ |
| 信号函数覆盖率 | <20% | 70%+ |

### 模块覆盖率详情

#### 高优先级模块（≥90%）

- `czsc/core.py` - 核心CZSC分析
- `czsc/utils/cache.py` - 缓存工具
- `czsc/utils/ta.py` - 技术分析指标
- `czsc/eda.py` - 探索性数据分析

#### 中优先级模块（≥80%）

- `czsc/py/bar_generator.py` - K线生成器
- `czsc/py/objects.py` - 对象定义
- `czsc/utils/*.py` - 其他工具模块

#### 标准优先级模块（≥70%）

- `czsc/signals/*.py` - 信号函数
- `czsc/traders/*.py` - 交易执行
- `czsc/sensors/*.py` - 事件检测

---

## 运行测试

### 基础命令

```bash
# 安装依赖
uv sync --extra dev

# 运行所有测试
uv run pytest

# 运行指定测试文件
uv run pytest test/test_signals.py -v

# 运行指定测试函数
uv run pytest test/test_signals.py::TestBarSignals::test_is_third_buy -v
```

### 带覆盖率报告

```bash
# 生成覆盖率报告
uv run pytest --cov=czsc --cov-report=html

# 查看HTML报告
open htmlcov/index.html
```

### 只运行失败的测试

```bash
uv run pytest --lf
```

### 详细输出

```bash
# 显示详细输出
uv run pytest -v

# 显示print输出
uv run pytest -s
```

---

## CI/CD集成

### GitHub Actions

项目使用GitHub Actions自动运行测试：

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install UV
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync --extra dev
      - name: Run tests
        run: uv run pytest --cov=czsc
```

### 本地预测试

提交前运行以下命令：

```bash
# 运行所有测试
uv run pytest

# 检查代码格式
uv run black czsc/ test/ --line-length 120
uv run isort czsc/ test/

# 类型检查
uv run mypy czsc/
```

---

## 测试模板

### 标准测试模板

```python
# -*- coding: utf-8 -*-
"""
test_<module>.py - <模块>单元测试

Mock数据格式说明:
- 数据来源: czsc.mock.generate_symbol_kines
- 数据列: dt, symbol, open, close, high, low, vol, amount
- 时间范围: 20220101-20250101（3年数据，满足3年+要求）
- 频率: 日线
- Seed: 42（确保可重现）

测试覆盖范围:
- <功能1>：说明
- <功能2>：说明
"""

import pytest
import pandas as pd
import numpy as np
from czsc import mock
from czsc.core import CZSC, format_standard_kline, Freq


def get_test_data(symbol="000001", freq="日线", sdt="20220101", edt="20250101"):
    """获取测试数据"""
    df = mock.generate_symbol_kines(symbol=symbol, freq=freq, sdt=sdt, edt=edt, seed=42)
    return df


class TestFeature:
    """测试功能"""

    def test_normal_case(self):
        """测试正常情况"""
        df = get_test_data()

        if len(df) < 100:
            pytest.skip("数据不足，跳过测试")

        result = function_to_test(df)
        assert result is not None, "结果不应为None"

    def test_edge_cases(self):
        """测试边界情况"""
        # 空数据
        result = function_to_test([])
        assert result is not None

        # NaN数据
        data = [1, 2, np.nan, 4]
        result = function_to_test(data)
        assert result is not None
```

---

## 贡献指南

### 添加新测试

1. 确定测试模块和功能
2. 创建测试文件（如 `test_<module>.py`）
3. 添加文档说明（Mock数据格式、时间范围、测试覆盖）
4. 编写测试函数（正常情况、边界情况）
5. 运行测试确保通过
6. 更新本文档

### 审查检查清单

- [ ] 测试文件有完整文档
- [ ] Mock数据使用3年+时间范围
- [ ] Mock数据设置固定seed
- [ ] 包含边界情况测试
- [ ] 断言有清晰的消息
- [ ] 可选依赖使用pytest.skip
- [ ] 测试函数命名清晰
- [ ] 遵循项目代码规范

---

## 常见问题

### Q: 为什么要求3年+数据？

A: 较长时间范围可以：
- 验证算法在不同市场环境下的稳定性
- 测试更多边界情况（如长期趋势、周期性变化）
- 提高测试的可靠性和代表性

### Q: 如何处理可选依赖？

A: 使用try-except包裹导入，失败时使用pytest.skip：

```python
try:
    from optional_module import function
except ImportError as e:
    pytest.skip(f"可选模块导入失败: {e}")
```

### Q: 如何保证测试可重现？

A:
1. 使用固定seed（推荐42）
2. 避免使用随机数（如time.time()）
3. 避免依赖外部状态（如文件系统、网络）

### Q: 如何测试需要大量数据的功能？

A:
1. 使用较长时间范围（如5年）的mock数据
2. 使用数据采样（如df.head(10000)）
3. 使用pytest.mark.slow标记慢速测试

---

## 参考资源

- [pytest文档](https://docs.pytest.org/)
- [CZSC项目文档](https://czsc.readthedocs.io/)
- [项目CLAUDE.md](../CLAUDE.md)

---

最后更新：2025年2月
