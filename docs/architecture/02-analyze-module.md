# Analyze 模块架构分析

## 模块概述

`analyze.py` 是 CZSC 库的核心分析引擎，实现了缠中说禅理论的核心算法，包括去包含关系、分型识别、笔的构建等基础功能。

## 模块架构图

```
                        Analyze 模块架构
                 ┌─────────────────────────────────────┐
                 │           analyze.py                │
                 └─────────────────────────────────────┘
                                    │
        ┌───────────────┬───────────┼───────────┬───────────────┐
        │               │           │           │               │
   ┌─────────┐    ┌─────────┐ ┌─────────┐ ┌─────────┐    ┌─────────┐
   │包含关系 │    │分型识别 │ │笔构建   │ │核心类   │    │可视化   │
   │处理     │    │算法     │ │算法     │ │CZSC     │    │工具     │
   └─────────┘    └─────────┘ └─────────┘ └─────────┘    └─────────┘
        │               │           │           │               │
  remove_include   check_fx     check_bi      CZSC          kline_pro
                  check_fxs                   (Rust)
```

## 核心算法流程图

```
                         缠论分析核心流程
    
    RawBar[]                NewBar[]               FX[]                BI[]
    (原始K线)      ─────►   (去包含K线)    ─────►   (分型序列)   ─────►   (笔序列)
        │                      │                     │                    │
        │                      │                     │                    │
        ▼                      ▼                     ▼                    ▼
   包含关系判断            分型识别算法           顶底交替验证         笔的有效性检查
   remove_include          check_fx              check_fxs           check_bi
        │                      │                     │                    │
        │                      │                     │                    │
        ▼                      ▼                     ▼                    ▼
   Direction判断           高低点对比判断         分型序列构建          笔长度验证
   (Up/Down)              (顶分型/底分型)        (交替序列)            (≥最小笔长)
```

## 核心函数详细分析

### 1. remove_include - 去包含关系算法

```python
def remove_include(k1: NewBar, k2: NewBar, k3: RawBar):
    """去除包含关系的核心算法
    
    算法步骤:
    1. 确定趋势方向 (通过k1和k2的高点比较)
    2. 判断k2和k3是否存在包含关系  
    3. 根据趋势方向合并K线
    
    包含关系判断:
    - (k2.high <= k3.high and k2.low >= k3.low) 或
    - (k2.high >= k3.high and k2.low <= k3.low)
    """
```

#### 算法逻辑图
```
    确定方向                包含关系判断              合并规则
    
    k1.high < k2.high  ──►  存在包含关系    ──►   向上趋势: 取较高点
      ↓ (Up方向)              ↓                      high = max(k2.high, k3.high)
                         k2完全包含k3                  low = max(k2.low, k3.low)  
    k1.high > k2.high  ──►  k3完全包含k2    ──►   向下趋势: 取较低点
      ↓ (Down方向)            ↓                      high = min(k2.high, k3.high)
                         需要合并处理                  low = min(k2.low, k3.low)
    k1.high = k2.high  ──►  直接返回k3      ──►   无需合并
```

### 2. check_fx - 分型识别算法

```python
def check_fx(k1: NewBar, k2: NewBar, k3: NewBar):
    """识别分型的核心算法
    
    顶分型条件: k1.high < k2.high > k3.high AND k1.low < k2.low > k3.low
    底分型条件: k1.low > k2.low < k3.low AND k1.high > k2.high < k3.high
    """
```

#### 分型识别图示
```
         顶分型 (Mark.G)                    底分型 (Mark.D)
    
         k2 (高点)                          k1     k3  
        /  \                               /  \   /  \
       /    \                             /    \ /    \
      k1      k3                                k2 (低点)
    
    条件: k2同时是高点和低点的局部极值      条件: k2同时是高点和低点的局部极值
    k1.high < k2.high > k3.high          k1.low > k2.low < k3.low
    k1.low < k2.low > k3.low             k1.high > k2.high < k3.high
```

### 3. check_fxs - 分型序列构建

```python  
def check_fxs(bars: List[NewBar]) -> List[FX]:
    """构建分型序列并确保顶底交替
    
    算法特点:
    1. 遍历所有可能的三K线组合
    2. 调用check_fx识别分型
    3. 强制要求顶底分型交替 (质量控制)
    """
```

#### 序列构建逻辑
```
    K线序列          分型识别             交替验证           最终序列
    
    [K1,K2,K3]  ──►   check_fx      ──►   顶分型?     ──►   [G,D,G,D...]
    [K2,K3,K4]        (滑动窗口)          底分型?           (交替序列)
    [K3,K4,K5]           ↓                 ↓
        ...              FX              如果连续相同标记
    [Kn-2,Kn-1,Kn]      (分型)           则记录错误日志
```

### 4. check_bi - 笔构建算法

```python
def check_bi(bars: List[NewBar], **kwargs):
    """从分型序列构建笔
    
    成笔条件:
    1. 顶底分型之间无包含关系
    2. 笔长度 >= min_bi_len (环境变量控制)
    3. 方向明确 (向上笔/向下笔)
    """
```

#### 笔构建流程图
```
                            笔构建算法流程
    
    输入分型序列           选择起止分型              验证成笔条件
    [fx1,fx2,fx3...]  ──►  fx_a (起点)      ──►    1. 无包含关系?
         ↓                 fx_b (终点)             2. 长度足够?
    确定第一个分型          ↓                      3. 方向明确?
    fx_a = fxs[0]          根据fx_a方向选择:             ↓
         ↓                 - 底分型→找最高顶分型          满足条件
    判断分型类型            - 顶分型→找最低底分型    ──►   构建BI对象
    fx_a.mark == D?        价格条件:                      返回笔和剩余K线
    fx_a.mark == G?        - 向上笔: fx_b.fx > fx_a.fx    
                          - 向下笔: fx_b.fx < fx_a.fx    不满足条件
                                                    ──►   返回None
```

## CZSC 核心类 (Rust 实现)

```python
from rs_czsc import CZSC  # 从Rust模块导入高性能实现
```

### CZSC 类架构
```
                          CZSC 类结构
                    ┌─────────────────────┐
                    │      CZSC类         │  
                    │   (Rust实现)        │
                    └─────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
       ┌─────────┐        ┌─────────┐        ┌─────────┐
       │数据输入 │        │核心计算 │        │结果输出 │
       └─────────┘        └─────────┘        └─────────┘
            │                  │                  │
       RawBar[]            分型、笔识别         BI[], FX[]
       输入序列            线段、中枢构建        分析结果
```

## 算法复杂度分析

### 时间复杂度
- `remove_include`: O(1) - 常数时间判断和合并
- `check_fx`: O(1) - 三个K线的比较操作  
- `check_fxs`: O(n) - n为K线数量，单次遍历
- `check_bi`: O(m) - m为分型数量，通常 m << n

### 空间复杂度  
- 所有算法的空间复杂度均为 O(1) 或 O(n)
- 主要内存占用在存储中间结果 (分型列表、K线列表)

## 关键参数配置

```python
from czsc import envs

# 环境变量控制的关键参数
min_bi_len = envs.get_min_bi_len()  # 最小笔长度，默认值
max_bi_num = envs.get_max_bi_num()  # 最大笔数量限制
```

## 模块依赖关系

```
analyze.py 依赖:
├── rs_czsc (Rust核心)
│   └── CZSC (高性能分析类)
├── czsc.objects  
│   ├── BI, FX (分型笔对象)
│   ├── RawBar, NewBar (K线对象)
│   └── Direction, Mark (枚举类型)
├── czsc.enum
│   ├── Mark.G/Mark.D (分型标记)
│   └── Direction.Up/Down (方向)
├── czsc.envs  
│   ├── get_min_bi_len() (参数配置)
│   └── get_max_bi_num()
├── czsc.utils.echarts_plot
│   └── kline_pro (可视化工具)
└── 标准库
    ├── typing (类型提示)
    └── loguru (日志记录)
```

## 性能优化特点

### 1. Rust 加速
- 核心计算逻辑使用 Rust 实现 (`rs_czsc` 模块)
- 大幅提升分型识别和笔构建的计算速度

### 2. 流式处理  
- 算法支持增量更新，无需重新计算全部数据
- `check_bi` 返回处理后的剩余K线，支持继续处理

### 3. 缓存机制
- 中间结果可缓存，避免重复计算
- 配合上层的 DiskCache 实现持久化缓存

### 4. 参数化配置
- 通过环境变量动态调整算法参数
- 支持不同市场和品种的个性化配置

## 质量控制机制

### 1. 数据完整性检查
- 分型序列必须顶底交替
- 笔的构建需满足严格的数学条件

### 2. 错误日志记录
- 异常情况下记录详细的错误信息
- 便于调试和质量监控

### 3. 边界条件处理
- 处理K线数量不足的情况
- 优雅处理无法构成分型或笔的场景

这个模块是整个 CZSC 库的计算核心，为上层的信号生成、策略分析提供了可靠的缠论基础分析能力。