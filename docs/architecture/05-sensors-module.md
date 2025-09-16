# Sensors 模块架构分析

## 模块概述

`sensors/` 模块是 CZSC 库的传感器和事件检测系统，提供事件匹配、CTA策略研究和特征选择等高级分析功能。这是连接信号分析与实际交易应用的智能感知层。

## 模块架构图

```
                           Sensors 模块架构
                    ┌─────────────────────────────────────┐
                    │           sensors/                  │
                    │        (传感器感知系统)              │  
                    └─────────────────────────────────────┘
                                       │
            ┌──────────────┬───────────┼───────────┬──────────────┐
            │              │           │           │              │
       ┌─────────┐    ┌─────────┐ ┌─────────┐ ┌─────────┐    ┌─────────┐
       │CTA研究  │    │事件匹配 │ │特征选择 │ │工具函数 │    │扩展组件 │
       │框架     │    │传感器   │ │器       │ │        │    │        │
       └─────────┘    └─────────┘ └─────────┘ └─────────┘    └─────────┘
            │              │           │           │              │
       ┌─────────┐    ┌─────────┐ ┌─────────┐ ┌─────────┐    ┌─────────┐
       │cta.py   │    │event.py │ │feature.py│ │utils.py │    │future   │
       │策略回测 │    │多事件   │ │选股逻辑 │ │概念效应 │    │expansion│
       │性能分析 │    │并行匹配 │ │组合优化 │ │换手率   │    │modules  │
       └─────────┘    └─────────┘ └─────────┘ └─────────┘    └─────────┘
```

## 核心组件关系图

```
                          传感器系统核心关系
    
    数据输入层           信号处理层             事件检测层            应用输出层
    RawBar[]      ──►   Signal Processing ──►  Event Matching  ──►  Research Results
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    多品种K线数据         信号计算和缓存         事件条件判断           策略性能报告
    时间序列数据          generate_signals()     event.is_match()       统计分析结果
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    CTAResearch          EventMatchSensor        FixedNumberSelector     回测结果
    批量回测框架          并行事件匹配           特征选择优化            可视化报告
```

## 详细模块分析

### 1. cta.py - CTA研究框架

#### CTAResearch 类架构
```python
class CTAResearch:
    """CTA策略研究统一入口
    
    核心功能:
    - 多品种批量回测
    - 策略性能评估  
    - 信号有效性检验
    - 并行计算优化
    """
    
    def __init__(self, strategy, read_bars, results_path, **kwargs):
        self.strategy = strategy           # 策略类 (CzscStrategyBase子类)
        self.read_bars = read_bars        # K线数据读取函数
        self.results_path = results_path  # 结果保存路径
        self.signals_module_name = kwargs.get('signals_module_name', 'czsc.signals')
```

#### CTA研究流程图
```
                        CTA研究完整流程
    
    策略定义             数据准备              并行回测               结果分析
    Strategy Class ──►   read_bars()    ──►   Multi-Processing ──►  Performance
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    继承CzscStrategyBase    多品种K线数据        ProcessPoolExecutor     统计指标计算
    定义交易逻辑            时间序列对齐         并行执行回测            风险收益分析
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    信号配置               数据质量检查           异常处理机制            报告生成
    events定义             缺失值处理            错误日志记录            可视化输出
```

#### 核心方法功能
```python
class CTAResearch:
    
    def replay(self, symbol, sdt, edt, refresh=True):
        """单品种交易回放 - 详细的逐K线分析"""
        
    def check_signals(self, symbol, sdt, edt):
        """信号有效性检查 - 验证信号函数正确性"""
        
    def dummy(self, symbols, sdt, edt, max_workers=1):
        """使用DummyBacktest进行快速批量回测"""
        
    def backtest(self, symbols, sdt, edt, max_workers=1):
        """完整的策略回测 - 包含资金管理和风控"""
        
    def research(self, symbols, sdt, edt, max_workers=1):
        """综合研究分析 - 包含信号、回测、性能评估"""
```

### 2. event.py - 事件匹配传感器

#### EventMatchSensor 类架构
```python
class EventMatchSensor:
    """事件匹配传感器
    
    核心能力:
    - 多事件并行匹配
    - 跨品种事件统计
    - 实时事件监控
    - 截面分析功能
    """
    
    def __init__(self, events, symbols, read_bars, **kwargs):
        self.events = events              # 事件配置列表
        self.symbols = symbols            # 监控品种列表
        self.read_bars = read_bars        # 数据读取函数
        self.signals_config = []          # 信号配置
        self.data = None                  # 匹配结果数据
        self.csc = None                   # 截面统计数据
```

#### 事件匹配流程
```
                         事件匹配完整流程
    
    事件定义             信号生成              匹配计算               结果统计
    Event Config   ──►   Signal Calculation ──►  Event Matching  ──►  Cross Section
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    因子组合定义          多周期信号计算         逐K线匹配判断          截面计数统计
    Factor Logic          generate_signals()     event.is_match()       时间序列分析
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    条件阈值设置          信号标准化处理         并行品种处理           趋势效应分析
    参数优化配置          缓存机制优化           ProcessPoolExecutor    统计显著性检验
```

#### 关键算法实现
```python
def _get_signals_config(self):
    """提取所有事件的唯一信号配置
    
    算法步骤:
    1. 遍历所有事件，收集信号配置
    2. 去重处理，避免重复计算  
    3. 合并为统一的配置列表
    4. 返回最小信号计算集合
    """
    
def get_event_csc(self, event_name):
    """获取单个事件的截面统计
    
    功能:
    - 计算事件在不同时间点的触发次数
    - 分析事件的时间分布特征
    - 生成截面统计报告
    """
```

### 3. feature.py - 特征选择器

#### FixedNumberSelector 类架构  
```python
class FixedNumberSelector:
    """选择固定数量（等权）的交易品种
    
    应用场景:
    - 多因子选股策略
    - 动态组合调整
    - 风险平价配置
    - A股涨跌停处理
    """
    
    def __init__(self, dfs, k, d, **kwargs):
        self.dfs = dfs          # 所有品种特征数据  
        self.k = k              # 固定选择数量
        self.d = d              # 允许变动数量
        self.holds = {}         # 持仓记录
        self.operates = {}      # 操作记录
        self.is_stocks = kwargs.get("is_stocks", False)  # A股标识
```

#### 选股算法流程
```
                         固定数量选股算法
    
    特征打分             排序筛选              组合调整               风控处理
    Feature Scoring ──►  Ranking & Filter ──►  Portfolio Adjust ──►  Risk Control
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    多维度打分模型        Score排序选择          新旧持仓对比           涨跌停过滤
    综合评估体系          Top-K选择策略          换手约束控制           交易限制处理
        │                      │                      │                      │
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
    因子标准化处理        动态阈值调整           成本效益分析           合规性检查
    归一化计算           自适应参数             交易成本估算           监管要求满足
```

#### 核心算法逻辑
```python
def __deal_one_time(self, dt):
    """单次调整算法
    
    算法逻辑:
    1. 获取当期所有品种的特征分数
    2. 过滤涨跌停品种 (A股市场)
    3. 按分数排序，选取前k个品种
    4. 与上期持仓对比，控制换手数量d
    5. 生成买卖操作记录
    6. 计算预期边际收益 (扣除交易成本)
    """
```

### 4. utils.py - 工具函数集

#### 核心工具函数
```python
def holds_concepts_effect(df, concepts):
    """概念板块轮动效应分析
    
    功能:
    - 分析不同概念的表现差异
    - 计算板块轮动的统计特征
    - 识别强势概念和弱势概念
    """
    
def turn_over_rate(df, **kwargs):
    """换手率计算和分析
    
    功能: 
    - 计算组合换手率指标
    - 分析换手成本对收益的影响
    - 优化调仓频率设置
    """
```

## 高级特性和算法

### 1. 并行计算优化

#### 多进程事件匹配
```python
def _multi_symbols(self, symbols, max_workers=1):
    """多品种并行处理
    
    技术特点:
    - ProcessPoolExecutor并行计算
    - 内存管理和异常处理
    - 进度监控和日志记录
    - 结果合并和数据一致性
    """
    
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(self._single_symbol, symbol): symbol 
                  for symbol in symbols}
        
        for future in tqdm(as_completed(futures), total=len(futures)):
            symbol = futures[future]
            try:
                result = future.result()
                # 处理结果
            except Exception as e:
                logger.exception(f"处理{symbol}时发生异常: {e}")
```

### 2. 缓存和性能优化

#### 数据缓存策略
```python
# 事件匹配结果缓存
file_data = os.path.join(self.results_path, "data.feather")
if os.path.exists(file_data):
    self.data = pd.read_feather(file_data)  # 快速加载
else:
    self.data = self._multi_symbols(symbols)
    self.data.to_feather(file_data)         # 持久化缓存
```

#### 内存优化技术
```python
# 分块处理大数据集
def process_large_dataset(self, chunk_size=10000):
    """大数据集分块处理
    
    优化策略:
    - 内存使用监控
    - 增量结果合并
    - 临时文件管理
    - 垃圾回收优化
    """
```

### 3. 统计分析功能

#### 截面分析
```python
def cross_section_analysis(self):
    """截面统计分析
    
    分析维度:
    - 时间维度的事件分布
    - 品种维度的事件频率  
    - 事件之间的相关性
    - 统计显著性检验
    """
```

#### 效应分析
```python
def concept_rotation_effect(self, concepts_data):
    """概念轮动效应分析
    
    统计方法:
    - 方差分析 (ANOVA)
    - 相关性分析
    - 回归分析
    - 时间序列分析
    """
```

## 应用场景和扩展

### 1. 量化研究应用
```python
# CTA策略研究
cta = CTAResearch(
    strategy=MyStrategy,
    read_bars=data_source.read_bars,
    results_path="./research_results"
)

# 批量回测
cta.research(symbols=['000001.SZ', '000002.SZ'], 
            sdt='20200101', edt='20220101', max_workers=4)
```

### 2. 事件驱动策略
```python
# 事件匹配传感器
sensor = EventMatchSensor(
    events=[event1, event2, event3],
    symbols=stock_pool,
    read_bars=data_reader,
    results_path="./event_results"
)

# 截面分析
cross_section_stats = sensor.csc
```

### 3. 多因子选股
```python
# 固定数量选股器
selector = FixedNumberSelector(
    dfs=factor_data,    # 包含dt, symbol, score等列
    k=50,               # 选择50只股票
    d=10,               # 每期最多调整10只
    is_stocks=True      # A股市场
)

# 获取持仓历史
holdings_history = selector.holds
operations_history = selector.operates
```

## 性能特点

### 1. 计算效率
- **并行处理**: 支持多核并行计算，提升处理速度
- **缓存机制**: 智能缓存减少重复计算
- **内存优化**: 分块处理大数据集，控制内存使用

### 2. 扩展性
- **模块化设计**: 各组件独立，易于扩展
- **接口标准化**: 统一的数据接口和函数签名
- **配置驱动**: 参数化配置，适应不同应用场景

### 3. 可靠性
- **异常处理**: 完善的错误处理和日志记录
- **数据校验**: 输入数据的完整性和一致性检查
- **结果验证**: 统计结果的合理性验证

## 模块依赖关系

```
sensors/ 模块依赖:
├── czsc.traders
│   ├── DummyBacktest (快速回测)
│   ├── generate_czsc_signals (信号生成)
│   └── get_signals_freqs (频率提取)
├── czsc.objects
│   └── Event (事件对象)
├── czsc.strategies  
│   └── CzscStrategyBase (策略基类)
├── czsc.utils
│   ├── save_json (数据保存)
│   └── dill_dump (对象序列化)
├── 数据处理库
│   ├── pandas (数据分析)
│   └── numpy (数值计算)
├── 并发处理
│   └── concurrent.futures (并行计算)
└── 标准库
    ├── os, shutil (文件操作)
    ├── datetime (时间处理)
    └── logging (日志记录)
```

这个模块是 CZSC 库的高级分析层，提供了从策略研究到事件监控的完整解决方案，特别适合量化研究和实盘交易的应用场景。