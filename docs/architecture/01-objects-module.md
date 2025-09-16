# Objects 模块架构分析

## 模块概述

`objects.py` 是 CZSC 库的核心数据结构定义模块，定义了缠论分析和量化交易中使用的所有基础对象。

## 核心对象架构图

```
                        CZSC Objects 模块架构
                 ┌─────────────────────────────────────┐
                 │            objects.py               │
                 └─────────────────────────────────────┘
                                    │
        ┌───────────────┬───────────┼───────────┬───────────────┐
        │               │           │           │               │
   ┌─────────┐    ┌─────────┐ ┌─────────┐ ┌─────────┐    ┌─────────┐
   │K线数据  │    │缠论对象 │ │信号体系 │ │交易对象 │    │工具函数 │
   └─────────┘    └─────────┘ └─────────┘ └─────────┘    └─────────┘
        │               │           │           │               │
   ┌─────────┐    ┌─────────┐ ┌─────────┐ ┌─────────┐    ┌─────────┐
   │ RawBar  │    │   FX    │ │ Signal  │ │Position │    │single_  │
   │ NewBar  │    │   BI    │ │ Factor  │ │         │    │linear   │
   │         │    │   ZS    │ │ Event   │ │         │    │         │
   └─────────┘    └─────────┘ └─────────┘ └─────────┘    └─────────┘
```

## 详细对象关系图

```
                         对象继承和依赖关系
    
    RawBar ────────┬────────► NewBar ────────┬────────► FX
    (原始K线)       │        (处理后K线)       │         (分型)
                   │                        │            │
                   │                        │            ▼
                   │                        │         FakeBI
                   │                        │         (虚笔)
                   │                        │            │
                   │                        │            ▼
                   │                        └────────► BI ────────► ZS
                   │                                  (笔)        (中枢)
                   │
    Signal ────────┼────────► Factor ────────┬────────► Event
    (信号)          │         (因子)          │         (事件)
                   │                        │            │
                   │                        │            ▼
                   └────────► Position ◄─────┘         Trading
                              (持仓)                   (交易决策)
```

## 对象详细分析

### 1. K线数据对象

#### RawBar (原始K线)
```python
# 从 rs_czsc 模块导入，使用 Rust 实现
# 包含基本的 OHLCV 数据
- symbol: 交易品种
- dt: 时间戳  
- open/high/low/close: 开高低收价格
- vol: 成交量
- amount: 成交金额
```

#### NewBar (处理后K线)
```python
# 去除包含关系后的K线
# 继承 RawBar 的所有属性，增加：
- elements: List[RawBar]  # 构成该 NewBar 的原始K线列表
```

### 2. 缠论分析对象

#### FX (分型)
```python
# 从 rs_czsc 模块导入
- symbol: 交易品种
- dt: 分型时间
- mark: Mark.G(顶分型) 或 Mark.D(底分型)
- high/low: 分型的高低点价格
- fx: 分型对应的K线索引
- power: 分型力度
```

#### BI (笔)
```python  
# 从 rs_czsc 模块导入
- symbol: 交易品种
- sdt/edt: 开始和结束时间
- direction: Direction.Up/Down 方向
- high/low: 笔的高低点
- power: 笔的力度 (价格变化幅度)
```

#### ZS (中枢)
```python
@dataclass
class ZS:
    bis: List[BI]  # 构成中枢的笔序列
    cache: dict    # 缓存计算结果
    
    # 关键属性
    - zg: 中枢上沿 = min(前3笔的高点)
    - zd: 中枢下沿 = max(前3笔的低点)  
    - zz: 中枢中轴 = (zg + zd) / 2
    - gg: 中枢最高点
    - dd: 中枢最低点
    - is_valid: 中枢有效性验证
```

### 3. 信号-因子-事件体系

#### Signal (信号)
```python
@dataclass  
class Signal:
    # 信号键值 (k1_k2_k3 格式)
    k1, k2, k3: str
    
    # 信号值 (v1_v2_v3_score 格式)  
    v1, v2, v3: str
    score: int = 0
    
    # 核心方法
    - key: 生成信号键名
    - value: 生成信号值
    - is_match(s: dict): 判断是否匹配信号字典
```

#### Factor (因子)
```python
@dataclass
class Factor:
    signals_all: List[Signal]  # 必须全部满足
    signals_any: List[Signal]  # 满足任一即可  
    signals_not: List[Signal]  # 不能满足任一
    name: str
    
    # 逻辑运算
    - is_match(s: dict): AND(signals_all) AND OR(signals_any) AND NOT(signals_not)
```

#### Event (事件)
```python
@dataclass
class Event:
    operate: Operate           # 操作类型 (开多/开空/平多/平空)
    factors: List[Factor]      # 因子列表，任一满足即触发
    signals_all: List[Signal] # 事件级别的全局信号约束
    signals_any: List[Signal] # 事件级别的任一信号约束
```

### 4. 交易对象

#### Position (持仓)
```python
@dataclass  
class Position:
    symbol: str
    holds: List[dict]  # 持仓列表
    
    # 持仓统计
    - long_pos: 多头持仓
    - short_pos: 空头持仓  
    - pos: 净持仓
    - 各种持仓计算方法
```

## 设计模式和特点

### 1. 数据驱动设计
- 所有对象都基于数据类 `@dataclass` 实现
- 自动生成构造函数、比较函数等
- 类型提示增强代码可读性

### 2. 分层架构
```
Raw Data Layer    → RawBar (原始数据)
Processing Layer  → NewBar, FX (数据处理)  
Analysis Layer    → BI, ZS (缠论分析)
Signal Layer      → Signal, Factor, Event (信号处理)
Trading Layer     → Position (交易执行)
```

### 3. 缓存优化
- ZS 对象包含 cache 字段用于缓存计算结果
- 避免重复计算，提高性能

### 4. 灵活匹配机制
- Signal 支持"任意"值匹配
- Factor 支持复杂的逻辑组合 (AND/OR/NOT)
- Event 提供多层级的条件判断

### 5. 哈希唯一性
- Factor 和 Event 使用 SHA256 生成唯一标识
- 确保相同配置的对象具有相同标识

## 核心算法

### 1. 中枢有效性验证
```python
def is_valid(self):
    # 1. 中枢上沿必须大于等于下沿
    if self.zg < self.zd:
        return False
        
    # 2. 中枢内每笔都必须与上下沿有交集
    for bi in self.bis:
        if not (上沿 >= bi.high >= 下沿 or 
                上沿 >= bi.low >= 下沿 or 
                bi.high >= 上沿 > 下沿 >= bi.low):
            return False
    return True
```

### 2. 信号匹配算法
```python
def is_match(self, s: dict) -> bool:
    # 解析信号值: "v1_v2_v3_score"
    v1, v2, v3, score = s[self.key].split("_")
    
    # 分数阈值判断
    if int(score) < self.score:
        return False
        
    # 三维匹配 (支持"任意"通配符)
    return (v1 == self.v1 or self.v1 == "任意") and \
           (v2 == self.v2 or self.v2 == "任意") and \
           (v3 == self.v3 or self.v3 == "任意")
```

## 模块依赖关系

```
objects.py 依赖:
├── rs_czsc (Rust 扩展模块)
│   ├── RawBar, NewBar  
│   ├── FX, BI, FakeBI
│   └── 高性能计算函数
├── czsc.enum
│   ├── Mark, Direction
│   ├── Freq, Operate  
│   └── 枚举类型定义
├── czsc.utils.corr
│   └── single_linear (线性相关计算)
└── 标准库
    ├── hashlib (SHA256计算)
    ├── dataclasses
    └── typing
```

这个模块是整个 CZSC 库的基础，为上层的分析、交易、信号等模块提供了统一的数据结构和接口规范。