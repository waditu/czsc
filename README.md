# czsc - 缠中说禅技术分析工具

[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=total&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Total)](https://pepy.tech/project/czsc)
[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=month&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Month)](https://pepy.tech/project/czsc)
[![Downloads](https://static.pepy.tech/personalized-badge/czsc?period=week&units=international_system&left_color=red&right_color=orange&left_text=Downloads/Week)](https://pepy.tech/project/czsc)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/czsc.svg)](https://pypi.org/project/czsc/)

**[项目文档](https://s0cqcxuy3p.feishu.cn/wiki/wikcn3gB1MKl3ClpLnboHM1QgKf)** |
**[投研数据共享](https://s0cqcxuy3p.feishu.cn/wiki/wikcnzuPawXtBB7Cj7mqlYZxpDh)** |
**[信号函数编写规范](https://s0cqcxuy3p.feishu.cn/wiki/wikcnCFLLTNGbr2THqo7KtWfBkd)** |
**[DEVIN生成的文档](https://deepwiki.com/waditu/czsc/1-overview)**

> **1.0.X 版本开始，缠论核心算法（分型、笔、中枢等）已全部迁移到 Rust 实现，通过 PyO3 扩展（`czsc._native`）暴露给 Python。** 需要了解旧 Python 实现逻辑的，可查看 [0.9.X](https://github.com/waditu/czsc/tree/v0.9.69) 版本。

> [czsc_skills](https://github.com/zengbin93/czsc_skills)

> 源于[缠中说缠博客](http://blog.sina.com.cn/chzhshch)，原始博客中的内容不太完整，且没有评论，以下是网友整理的原文备份

* 备份网址1：http://www.fxgan.com
* 备份网址2：https://chzhshch.blog

* 已经开始用czsc库进行量化研究的朋友，欢迎[加入飞书群](https://applink.feishu.cn/client/chat/chatter/add_by_link?link_token=0bak668e-7617-452c-b935-94d2c209e6cf)，快点击加入吧！
* [B站视频教程合集（持续更新...）](https://space.bilibili.com/243682308/channel/series)


## 架构概览

CZSC 1.0 采用 **Rust + Python 混合架构**：

```
czsc (Python 包)
├── czsc._native          ← Rust 扩展（PyO3），缠论核心
│   ├── CZSC / FX / BI / ZS / RawBar / NewBar / BarGenerator
│   ├── Freq / Mark / Direction / Signal / Event / Position / Operate
│   ├── CzscTrader / CzscSignals / generate_czsc_signals
│   ├── signals.*         ← 250+ 信号函数（13+ 子模块；详见 crates/czsc-signals/src/）
│   └── ta.*              ← Rust TA 算子 (ema/sma/boll 等，本次清理 起仅内部使用)
├── czsc.traders          ← Python 门面，汇聚 Rust 交易 API
├── czsc.utils            ← 工具函数（绘图/缓存/统计/交易工具）
├── czsc.connectors       ← 数据源连接器（天勤/Tushare/CCXT/本地缓存）
├── czsc.eda              ← 探索性数据分析（因子/特征/权重）
├── czsc.strategies       ← 策略门面（CzscStrategyBase/CzscJsonStrategy）
├── czsc.fsa              ← 飞书自动化工具
├── czsc.mock             ← 测试用模拟数据（转发自 wbt）
└── czsc.envs             ← 环境变量管理
```

底层 Rust workspace 包含 9 个 crate：`czsc` / `czsc-core` / `czsc-derive` / `czsc-signals` /
`czsc-trader` / `czsc-utils` / `czsc-ta` / `czsc-signal-macros` /
`czsc-python`（PyO3 绑定入口）。


## 项目贡献

* 缠论的 `分型、笔` 的自动识别，由 Rust 实现并通过 `czsc._native` 暴露
* 定义并实现 `信号-事件-交易` 量化交易逻辑体系，事件通过 `signals_all/signals_any/signals_not` 实现信号的逻辑组合
* 定义并实现了 250+ 信号函数（Rust 实现），见 `czsc._native.signals`
* 缠论多级别联立决策分析交易，详见 `CzscTrader`
* HTML 可视化（plotly + lightweight-charts）：`czsc.utils.plotting.{kline,backtest,lightweight}.*`


## 安装使用

**注意：** Python 版本必须 **≥ 3.10**

从 PyPI 安装预编译版本（推荐）：

```bash
pip install czsc -U
```

使用 `uv` 安装（推荐开发环境）：

```bash
uv pip install czsc
```

从源码构建（需要 Rust 工具链和 maturin）：

```bash
# 安装 Rust：https://rustup.rs/
# 安装 maturin
pip install maturin

# 克隆并构建
git clone https://github.com/waditu/czsc.git
cd czsc
maturin develop --release
```

> **Rust 构建环境约束**：底层依赖 `pyo3` / `pyo3-stub-gen` 0.22 要求 Python ≥ 3.10。
> 当系统默认 Python 低于 3.10 时，请通过环境变量显式指定：
>
> ```bash
> export PYO3_PYTHON=$(which python3.12)   # 或任意 3.10+ 的解释器
> ```
>
> 否则 `cargo build` / `cargo test` 会在 `crates/czsc-python/build.rs` 提前 panic 并给出修复建议。
> 用 `uv sync --extra dev` 走 UV 流程时，UV 会自动选择项目声明的 Python，不需要额外设置。


## 快速开始

### 核心缠论分析

```python
import czsc
from czsc import CZSC, Freq, format_standard_kline
from czsc.mock import generate_symbol_kines

# 生成模拟 K 线数据
df = generate_symbol_kines('000001', '30分钟', '20240101', '20240601')

# 转换为 RawBar 对象列表
bars = format_standard_kline(df, freq=Freq.F30)

# 创建 CZSC 分析对象（自动识别分型、笔、中枢）
czsc_obj = CZSC(bars)
print(f"笔数量：{len(czsc_obj.bi_list)}")
print(f"中枢数量：{len(czsc_obj.zs_list)}")
```

### K 线合成与多级别分析

```python
from czsc import BarGenerator, Freq

# 使用 BarGenerator 进行 K 线合成
bg = BarGenerator(base_freq='1分钟', freqs=['5分钟', '30分钟', '日线'])
for bar in raw_bars:
    bg.update(bar)

# 获取各周期 K 线
bars_5m = bg.bars['5分钟']
bars_30m = bg.bars['30分钟']
```

### 信号生成

```python
from czsc import generate_czsc_signals, get_signals_config, get_signals_freqs

# 配置信号序列（使用 Rust 实现的信号函数）
signals_seq = [
    "czsc._native.signals.bar.bar_end_V230331",
    "czsc._native.signals.cxt.cxt_bi_status_V230101",
]

# 解析信号所需的周期配置
freqs = get_signals_freqs(signals_seq)
config = get_signals_config(signals_seq)

# 生成信号序列
results = generate_czsc_signals(bars, signals_seq)
```

### 权重回测

```python
from czsc import WeightBacktest
from czsc.mock import generate_klines_with_weights

# 生成带权重的模拟数据
dfw = generate_klines_with_weights(seed=42)

# 运行权重回测
wb = WeightBacktest(dfw, fee_rate=0.0002)
print(wb.stats)  # 回测统计汇总
```

### 策略研究

```python
from czsc import run_research, run_replay

# 单品种回放
run_replay(bars, signals_seq, pos_seq, res_path='./results/')

# 批量品种研究
run_research(symbols, signals_seq, pos_seq, res_path='./results/')
```

### 回测可视化

```python
from czsc.utils.plotting.backtest import plot_backtest_stats, plot_cumulative_returns

# 综合回测统计图（含回撤/收益分布/月度热力图）
fig = plot_backtest_stats(dret, ret_col='total', title='策略回测统计')
fig.show()

# 累计收益曲线
fig = plot_cumulative_returns(dret, title='策略累计收益')
fig.show()
```


## 核心 API 一览

| 类型 | 符号 | 说明 |
|------|------|------|
| **缠论对象** | `CZSC`, `FX`, `BI`, `ZS` | 缠论核心数据结构（Rust） |
| **K线对象** | `RawBar`, `NewBar`, `BarGenerator` | K线与合成器（Rust） |
| **枚举** | `Freq`, `Mark`, `Direction`, `Operate` | 方向/频率等枚举（Rust） |
| **信号/事件** | `Signal`, `Event`, `Position` | 信号与持仓逻辑（Rust） |
| **分析工具** | `check_fx`, `check_bi`, `remove_include` | 分型/笔校验工具（Rust） |
| **TA算子顶层别名** | `czsc.ema`, `czsc.sma`, `czsc.rolling_rank`, `czsc.boll_positions`, `czsc.ultimate_smoother` | 技术指标算子顶层别名（Rust） |
| **交易器** | `CzscTrader`, `CzscSignals` | 多级别交易决策（Rust） |
| **信号生成** | `generate_czsc_signals` | 批量信号生成（Rust） |
| **权重回测** | `WeightBacktest` | 权重序列回测（来自 wbt） |
| **策略** | `CzscStrategyBase`, `CzscJsonStrategy` | 策略封装（Python） |
| **模拟数据** | `generate_symbol_kines` | 测试用 K线数据（来自 wbt） |
| **格式转换** | `format_standard_kline` | DataFrame → RawBar 列表 |


## 数据源连接器

`czsc.connectors` 提供多个数据源适配器：

| 模块 | 数据源 | 说明 |
|------|--------|------|
| `tq_connector.py` | 天勤（TQSdk） | 期货实时/历史行情 |
| `ts_connector.py` | Tushare | A股历史数据 |
| `ccxt_connector.py` | CCXT | 数字货币交易所 |
| `local_data.py` | 投研数据本地缓存 | CZSC 共享数据本地读取入口 |


## 可视化（HTML 输出）

本次清理 起项目不再依赖 streamlit，可视化统一以 plotly + lightweight-charts 输出 HTML：

| 模块 | 功能 |
|------|------|
| `czsc.utils.plotting.kline` | 单周期 K 线 + 缠论结构（plotly Figure） |
| `czsc.utils.plotting.backtest` | 累计收益 / 回撤 / 月度热力图 / 综合回测概览 |
| `czsc.utils.plotting.lightweight` | lightweight-charts 自包含 HTML，多周期联立 + 信号叠加 |

如需 streamlit 集成，调用方自行 `pip install streamlit` 后用 `st.components.v1.html(plot_czsc(c, output='html'))` 嵌入即可。从 1.x 升级请参考 [`docs/migration/cleanup-non-czsc-core.md`](docs/migration/cleanup-non-czsc-core.md)。


## 开发环境搭建

```bash
# 使用 UV 管理依赖（推荐）
uv sync --extra dev

# 构建 Rust 扩展（开发模式）
maturin develop

# 运行测试
uv run pytest tests/ -v

# 代码格式化
uv run ruff format czsc/ tests/
uv run ruff check czsc/ tests/
```


## 关键环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CZSC_MIN_BI_LEN` | 最小笔长度 | 6 |
| `CZSC_MAX_BI_NUM` | 最大笔数量 | 50 |
| `CZSC_VERBOSE` | 是否输出详细日志 | False |


## 使用前必看

* 1.0.X 版本核心算法已迁移到 Rust，与 0.9.X 版本 **不兼容**；旧代码需按新 API 迁移；
* 免责声明：项目开源仅用于技术交流！
* 如果你发现了项目中的 Bug，可以先读一下《[如何有效地报告 Bug](https://www.chiark.greenend.org.uk/~sgtatham/bugs-cn.html)》，然后在 [issues](https://github.com/waditu/czsc/issues) 中报告 Bug


## 缠论精华

> 学了本ID的理论，去再看其他的理论，就可以更清楚地看到其缺陷与毛病，因此，广泛地去看不同的理论，不仅不影响本ID理论的学习，更能明白本ID理论之所以与其他理论不同的根本之处。

> 为什么要去了解其他理论，就是这些理论操作者的行为模式，将构成以后我们猎杀的对象，他们操作模式的缺陷，就是以后猎杀他们的最好武器，这就如同学独孤九剑，必须学会发现所有派别招数的缺陷，这也是本ID理论学习中一个极为关键的步骤。

> 真正的预测，就是不测而测。所有预测的基础，就是分类，把所有可能的情况进行完全分类。有人可能说，分类以后，把不可能的排除，最后一个结果就是精确的。
> 这是脑子锈了的想法，任何的排除，等价于一次预测，每排除一个分类，按概率的乘法原则，就使得最后的所谓精确变得越不精确，最后还是逃不掉概率的套子。
> 对于预测分类的唯一正确原则就是不进行任何排除，而是要严格分清每种情况的边界条件。任何的分类，其实都等价于一个分段函数，就是要把这分段函数的边界条件确定清楚。
> 边界条件分段后，就要确定一旦发生哪种情况就如何操作，也就是把操作也同样给分段化了。然后，把所有情况交给市场本身，让市场自己去当下选择。
> 所有的操作，其实都是根据不同分段边界的一个结果，只是每个人的分段边界不同而已。因此，问题不是去预测什么，而是确定分段边界。


## 原文整理

* [缠中说禅重新编排版《论语》（整理版）](https://blog.csdn.net/baidu_25764509/article/details/109517775)
* [缠中说禅交易指南](https://blog.csdn.net/baidu_25764509/article/details/109598229)
* [缠中说禅技术原理](https://blog.csdn.net/baidu_25764509/article/details/109597255)
* [缠中说禅图解分析示范](https://blog.csdn.net/baidu_25764509/article/details/110195063)
* [缠中说禅：缠非缠、禅非禅，枯木龙吟照大千（整理版）](https://blog.csdn.net/baidu_25764509/article/details/110775662)
* [缠中说禅教你打坐（整理版）](https://blog.csdn.net/baidu_25764509/article/details/113735170)


## 资料分享

* 链接：https://pan.baidu.com/s/1RXkP3188F0qu8Yk6CjbxRQ
* 提取码：vhue
