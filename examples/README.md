# CZSC 示例脚本

本目录包含 czsc 库的核心功能使用示例。所有脚本均可独立运行，使用内置的 mock 数据，无需外部数据源。

## 快速开始

```bash
# 安装 czsc
pip install czsc

# 运行任意示例
python examples/30分钟笔非多即空.py
```

## 示例列表

### 策略开发

| 文件 | 说明 | 运行方式 |
|------|------|----------|
| `30分钟笔非多即空.py` | 基于缠论笔方向的多空策略示例，展示 `CzscStrategyBase`、`Position`、`Event` 的用法 | `python examples/30分钟笔非多即空.py` |
| `use_cta_research.py` | CTA 策略研究框架，展示 `CTAResearch` 的策略回测流程 | `python examples/use_cta_research.py` |
| `use_optimize.py` | 入场/出场信号优化，展示 `OpensOptimize` 的用法 | `python examples/use_optimize.py` |

### 报告与可视化

| 文件 | 说明 | 运行方式 |
|------|------|----------|
| `use_html_report_builder.py` | HTML 报告构建器，支持绩效指标、图表、表格等 | `python examples/use_html_report_builder.py` |
| `svc_demos.py` | Streamlit 交互式分析仪表板，展示 SVC 组件 | `streamlit run examples/svc_demos.py` |

### Jupyter Notebook

| 文件 | 说明 |
|------|------|
| `事件策略研究工具使用案例.ipynb` | CZSC 对象的创建、笔的分析和可视化 |

### 开发工具 (`develop/`)

| 文件 | 说明 |
|------|------|
| `czsc_benchmark.py` | CZSC 分析性能基准测试 |
| `test_trading_view_kline.py` | K 线图可视化测试 |

### 信号开发 (`signals_dev/`)

| 文件 | 说明 |
|------|------|
| `bar_volatility_V241013.py` | 自定义信号函数开发示例（波动率分层） |
| `signal_match.py` | 信号解析和匹配工具 |

## 核心概念

### 信号-事件-交易体系

```
信号 (Signal) → 事件 (Event) → 持仓 (Position) → 交易 (Trade)
```

- **信号**：基于K线数据计算的技术指标状态，如 `日线_D1_表里关系V230101_向上_任意_任意_0`
- **事件**：信号的逻辑组合，通过 `signals_all`（AND）、`signals_any`（OR）、`signals_not`（NOT）组合
- **持仓**：由开仓事件和平仓事件定义的交易策略
- **交易**：由 `CzscTrader` 执行的实际交易过程

### Mock 数据

所有示例使用 `czsc.mock` 模块生成模拟数据，无需任何外部数据源：

```python
from czsc.mock import generate_symbol_kines
from czsc import format_standard_kline, Freq

# 生成日线数据
df = generate_symbol_kines('000001', '日线', '20200101', '20230101', seed=42)
bars = format_standard_kline(df, freq=Freq.D)
```

### 策略开发流程

```python
import czsc

# 1. 定义策略类
class MyStrategy(czsc.CzscStrategyBase):
    @property
    def positions(self):
        # 定义持仓策略列表
        ...

# 2. 回测验证
tactic = MyStrategy(symbol='000001')
trader = tactic.backtest(bars, sdt='20210101')

# 3. 保存策略配置
tactic.save_positions('path/to/positions')
```

## 注意事项

- 示例中的 `signal_match.py` 在解析所有信号后运行信号生成时，部分信号函数可能因 mock 数据格式限制而报错，这不影响信号解析功能的演示
- `svc_demos.py` 需要安装 `streamlit`，通过 `streamlit run` 命令启动
- 回测结果默认输出到 `/tmp/czsc_examples/` 目录
