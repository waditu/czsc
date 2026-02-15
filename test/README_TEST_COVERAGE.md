# CZSC 单元测试说明

## 测试数据规范

所有单元测试使用 `czsc.mock` 模块生成测试数据，确保测试的可重现性和一致性。

### Mock 数据格式

所有测试数据通过 `czsc.mock.generate_symbol_kines` 函数生成：

```python
from czsc import mock
df = mock.generate_symbol_kines(
    symbol="000001",      # 品种代码
    freq="日线",           # K线频率：1分钟、5分钟、15分钟、30分钟、日线
    sdt="20220101",       # 开始日期（YYYYMMDD格式）
    edt="20250101",       # 结束日期（YYYYMMDD格式）
    seed=42               # 随机数种子，确保可重现
)
```

### 数据格式说明

生成的 DataFrame 包含以下列：
- `dt`: 日期时间
- `symbol`: 品种代码
- `open`: 开盘价
- `close`: 收盘价
- `high`: 最高价
- `low`: 最低价
- `vol`: 成交量
- `amount`: 成交额

### 数据时间范围要求

**所有测试必须使用至少3年的数据覆盖。**

推荐配置：
- **短线测试**（1分钟、5分钟、15分钟）：20220101 - 20250101（3年）
- **中线测试**（30分钟、60分钟）：20200101 - 20250101（5年）
- **长线测试**（日线、周线、月线）：20200101 - 20250101（5年）

## 测试文件组织

### 核心模块测试
- `test_analyze.py` - CZSC核心分析功能
- `test_bar_generator.py` - K线生成器和重采样
- `test_objects.py` - 核心数据对象测试
- `test_rs.py` / `test_rs_analyze.py` - Rust版本功能测试

### Utils 模块测试
- `test_utils_ta.py` - 技术分析指标（SMA、EMA、MACD、RSI、BOLL、ATR、KDJ等）
- `test_utils_cache.py` - 磁盘缓存功能
- `test_utils.py` - 其他工具函数
- `test_plot_backtest_report.py` - 回测报告可视化
- `test_plot_colored_table.py` - 彩色表格绘制
- `test_plotly_plot.py` - Plotly交互式图表
- `test_weights_convert.py` - 权重转换功能
- `test_weights_components.py` - 权重组件

### Signals 模块测试
- `test_signals.py` - 信号生成函数测试
  - bar.py: K线级别信号
  - vol.py: 成交量信号
  - cxt.py: 上下文信号
  - tas.py: 技术指标信号
  - pos.py: 持仓相关信号

### Traders 模块测试
- `test_traders.py` - 交易执行框架测试
  - base.py: CzscSignals 和 CzscTrader 核心类
  - optimize.py: 开仓平仓参数优化
  - performance.py: 交易绩效分析

### Sensors 模块测试
- `test_sensors.py` - 事件检测和特征分析测试
  - cta.py: CTA研究框架
  - feature.py: 特征选择器和滚动特征分析
  - event.py: 事件匹配和检测

### 其他测试
- `test_backtest_report.py` - 回测报告功能
- `test_calendar.py` - 日历功能
- `test_cross_sectional_strategy.py` - 横截面策略
- `test_eda.py` - 探索性数据分析
- `test_features.py` - 特征工程
- `test_html_report_builder.py` - HTML报告生成器
- `test_kline_quality.py` - K线质量检查
- `test_mark_czsc_status.py` - CZSC状态标记
- `test_mock_quality.py` - Mock数据质量检查
- `test_trade_utils.py` - 交易工具函数
- `test_trader_sig.py` - 交易信号测试
- `test_warning_capture.py` - 警告信息捕获

## 测试编写规范

### 1. 测试文件结构

```python
# -*- coding: utf-8 -*-
"""
describe: 模块功能描述
author: 作者名
create_dt: 创建日期

Mock数据格式说明：
- 使用 czsc.mock.generate_symbol_kines 生成
- 日期范围：20220101-20250101（3年数据，满足3年+要求）
- K线格式：OHLCVA（开高低收成交量成交额）
- 频率：支持 1分钟、5分钟、15分钟、30分钟、日线
"""
import pytest
from czsc import mock
from czsc.core import format_standard_kline, Freq


def get_test_data(symbol="000001", sdt="20220101", edt="20250101"):
    """获取测试数据（3年+数据）

    Args:
        symbol: 品种代码
        sdt: 开始日期（YYYYMMDD格式）
        edt: 结束日期（YYYYMMDD格式）

    Returns:
        DataFrame: K线数据
    """
    return mock.generate_symbol_kines(symbol, "日线", sdt=sdt, edt=edt, seed=42)


def test_function_name():
    """测试功能描述"""
    # 准备测试数据
    df = get_test_data()

    # 执行测试逻辑
    assert len(df) > 0, "数据不应为空"
```

### 2. 测试命名规范

- 测试文件：`test_<module_name>.py`
- 测试函数：`test_<function_name>` 或 `test_<feature_description>`
- 测试类：`Test<ClassName>`

### 3. 测试覆盖要求

#### 必须覆盖的测试场景：
1. **正常情况**：功能在正常输入下的行为
2. **边界情况**：空数据、单条数据、最大最小值等
3. **异常情况**：错误输入、无效参数等
4. **一致性验证**：相同输入多次调用应得到相同结果
5. **数据完整性**：验证输出数据的格式、类型、范围

#### 关键测试点：
- 所有公共函数必须有测试
- 所有公共类必须有测试
- 关键算法需要多组输入验证
- 边界条件必须覆盖（空数组、单个元素、极值等）

### 4. Mock 数据使用

```python
# ✅ 正确：使用 mock 模块生成数据
from czsc import mock
df = mock.generate_symbol_kines("000001", "日线", sdt="20220101", edt="20250101", seed=42)

# ❌ 错误：硬编码测试数据
df = pd.DataFrame({
    'dt': ['2023-01-01', '2023-01-02'],
    'close': [100, 101]
})
```

### 5. 断言规范

```python
# ✅ 好的断言：清晰的错误信息
assert len(result) > 0, "结果不应为空"
assert isinstance(value, int), f"值应该是整数，实际为{type(value)}"
assert abs(expected - actual) < 0.01, f"计算值不正确，期望{expected}，实际{actual}"

# ❌ 不好的断言：没有错误信息
assert len(result) > 0
assert isinstance(value, int)
```

## 运行测试

### 运行所有测试
```bash
# 使用 uv（推荐）
uv run pytest

# 使用 pip
pytest
```

### 运行指定测试文件
```bash
uv run pytest test/test_utils_ta.py
```

### 运行指定测试函数
```bash
uv run pytest test/test_utils_ta.py::test_sma -v
```

### 运行带覆盖率的测试
```bash
uv run pytest --cov=czsc --cov-report=html
```

### 查看覆盖率报告
```bash
# HTML报告
open htmlcov/index.html

# 终端报告
uv run pytest --cov=czsc --cov-report=term-missing
```

## 测试覆盖率目标

- **整体覆盖率**：目标 ≥ 80%
- **核心模块**（czsc/core.py, czsc/py/analyze.py）：目标 ≥ 90%
- **工具模块**（czsc/utils/）：目标 ≥ 75%
- **信号模块**（czsc/signals/）：目标 ≥ 70%
- **交易模块**（czsc/traders/）：目标 ≥ 75%

## 持续集成

测试会在以下情况自动运行：
- Push 到 master 分支
- 创建 Pull Request
- 手动触发 GitHub Actions

确保所有测试在提交前通过：
```bash
# 本地运行完整测试套件
uv run pytest --cov=czsc
```

## 常见问题

### Q: 为什么必须使用 3 年以上的数据？
A: 为了确保测试覆盖不同市场环境（牛市、熊市、震荡市），提高测试的可靠性和泛化能力。

### Q: 如何选择测试的时间范围？
A:
- 短周期测试（分钟级）：至少 1 年数据
- 日线测试：至少 3 年数据
- 周线/月线测试：至少 5 年数据

### Q: 测试失败时如何调试？
A:
1. 使用 `-v` 参数查看详细输出：`pytest -v`
2. 使用 `-s` 参数查看 print 输出：`pytest -s`
3. 使用 `pdb` 进入调试模式：在测试中添加 `import pdb; pdb.set_trace()`

### Q: 如何跳过某些测试？
A: 使用 `pytest.mark.skip` 或 `pytest.mark.skipif`：
```python
@pytest.mark.skip("暂时跳过此测试")
def test_something():
    pass

@pytest.mark.skipif(condition, reason="条件不满足时跳过")
def test_something_else():
    pass
```

## 更新日志

### 2026-02-15
- 新增 `test_utils_ta.py` - 技术指标测试
- 新增 `test_signals.py` - 信号函数测试
- 新增 `test_traders.py` - 交易框架测试
- 新增 `test_sensors.py` - 传感器模块测试
- 更新现有测试使用 3 年+数据覆盖
- 完善测试文档和使用规范
