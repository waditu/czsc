---
name: signal-functions
description: rs_czsc 信号函数完整参考手册。查询信号函数用法、参数模板、模块分类时使用。触发场景：（1）查找某个信号函数的参数模板或含义（2）按模块浏览所有可用信号（3）编写 signals_config 时需要知道信号名称和参数（4）理解信号字符串格式（5）配置 CzscTrader/CzscSignals 的信号列表。不触发：编写新信号函数的 Rust 实现代码。
---

# rs_czsc 信号函数参考

## 概述

rs_czsc 通过 Rust 实现、PyO3 暴露的信号函数体系，提供 232 个信号函数，分两大类：

- **K线级信号 (kline)**: 208 个，基于 CZSC 分析结果 + K线数据计算
- **交易级信号 (trader)**: 24 个，基于持仓/策略状态计算

## Python API

```python
from rs_czsc import list_all_signals, derive_signals_config, derive_signals_freqs

# 列出所有注册信号
signals = list_all_signals(include_kline=True, include_trader=True)
# 返回 list[dict]，每项: {name, param_template, category, namespace}

# 从信号字符串反推 signals_config
config = derive_signals_config(["60分钟_D1SMA#5_分类V221101_多头_向上_任意_0"])

# 从 signals_config 提取所需周期
freqs = derive_signals_freqs(config)
```

## 信号字符串格式

7 段式：`k1_k2_k3_v1_v2_v3_score`

```
60分钟_D1SMA#5_分类V221101_多头_向上_任意_0
 ├─k1──┤ ├─k2───┤ ├k3──────┤ ├v1┤ ├v2┤ ├v3┤ ├s┤
```

- `k1,k2,k3`：键字段（通常为：周期、参数描述、版本标签）
- `v1,v2,v3`：值字段（信号状态，如"看多"/"看空"/"其他"）
- `score`：整数 0-100

## 通用模板参数

| 参数 | 含义 | 示例 |
|------|------|------|
| `{freq}` | K线周期 | `60分钟`, `日线`, `周线` |
| `{di}` | 倒数第几根K线/笔，0=当前 | `0`, `1`, `2` |
| `{n}` / `{m}` | 窗口长度 / 辅助窗口 | `5`, `10`, `20` |
| `{th}` | 阈值 | `100`, `500` |
| `{ma_type}` | 均线类型 | `SMA`, `EMA`, `WMA` |
| `{timeperiod}` | 均线/指标周期 | `5`, `10`, `20` |
| `{fastperiod}` / `{slowperiod}` / `{signalperiod}` | MACD 参数 | `12`, `26`, `9` |
| `{max_overlap}` | 最大重叠次数 | `1`, `3` |
| `{pos_name}` | 持仓名称（trader信号） | `多头持仓` |
| `{freq1}` / `{freq2}` | 双周期信号的两个周期 | `60分钟`, `日线` |

## 信号模块索引

### K线级信号

| 模块 | 数量 | 说明 | 模块索引 |
|------|------|------|----------|
| **bar** | 46 | K线形态、动量、突破、统计 | [signals-bar.md](references/signals-bar.md) |
| **cxt** | 41 | 缠论笔、分型、买卖点、形态 | [signals-cxt.md](references/signals-cxt.md) |
| **tas** | 59 | MACD/均线/布林/KDJ/RSI/ATR等 | [signals-tas.md](references/signals-tas.md) |
| **jcc** | 19 | 日本蜡烛图经典形态 | [signals-jcc.md](references/signals-jcc.md) |
| **ang** | 10 | ADTM/AMV/ASI/CMO/SKDJ等辅助指标 | [signals-ang.md](references/signals-ang.md) |
| **xl** | 7 | XL系列（位置/趋势/突破/通道） | [signals-xl.md](references/signals-xl.md) |
| **vol** | 6 | 成交量均线/缩量/高低/窗口能量 | [signals-vol.md](references/signals-vol.md) |
| **coo** | 5 | TD序列/CCI/KDJ/SAR组合 | [signals-coo.md](references/signals-coo.md) |
| **byi** | 5 | 对称中枢/停顿分型/验证分型 | [signals-byi.md](references/signals-byi.md) |
| **pressure** | 4 | 支撑压力位 | [signals-pressure.md](references/signals-pressure.md) |
| **obv** | 2 | OBV能量 | [signals-obv.md](references/signals-obv.md) |
| **cvolp** | 1 | CVOLP动量变化率 | [signals-cvolp.md](references/signals-cvolp.md) |
| **ntmdk** | 1 | NTMDK多空 | [signals-ntmdk.md](references/signals-ntmdk.md) |
| **kcatr** | 1 | KCATR多空 | [signals-kcatr.md](references/signals-kcatr.md) |
| **clv** | 1 | CLV多空 | [signals-clv.md](references/signals-clv.md) |

### 交易级信号

| 模块 | 数量 | 说明 | 模块索引 |
|------|------|------|----------|
| **pos** | 16 | 持仓管理（止损/止盈/保本/状态） | [signals-pos.md](references/signals-pos.md) |
| **zdy_trader** | 4 | 自定义交易（震荡/止损/止盈） | [signals-zdy_trader.md](references/signals-zdy_trader.md) |
| **cat** | 2 | MACD联立信号 | [signals-cat.md](references/signals-cat.md) |
| **cxt_trader** | 2 | 缠论交易（中枢共振/日内走势） | [signals-cxt_trader.md](references/signals-cxt_trader.md) |

### 单信号详细文档

每个信号函数都有独立的详细文档，包含**信号逻辑**、**信号列表示例**、**参数说明**。

文件位于 `references/signals/{signal_name}.md`，如 [er_up_dw_line_V230604.md](references/signals/er_up_dw_line_V230604.md)。

## 使用示例

### 在 CzscSignals/CzscTrader 中配置信号

```python
signals_config = [
    {"name": "tas_ma_base_V221101", "freq": "60分钟", "di": 1, "ma_type": "SMA", "timeperiod": 5},
    {"name": "tas_macd_base_V221028", "freq": "日线", "di": 1, "fastperiod": 12, "slowperiod": 26, "signalperiod": 9},
    {"name": "cxt_bi_end_V230224", "freq": "30分钟", "di": 1},
    {"name": "pos_stop_V240428", "freq1": "60分钟", "pos_name": "多头", "t": 200, "n": 3},
]
```

### 从信号字符串反推配置

```python
from rs_czsc import derive_signals_config

signal_str = "60分钟_D1SMA#5_分类V221101_多头_向上_任意_0"
config = derive_signals_config([signal_str])
# 返回: [{"name": "tas_ma_base_V221101", "freq": "60分钟", "di": 1, "ma_type": "SMA", "timeperiod": 5}]
```
