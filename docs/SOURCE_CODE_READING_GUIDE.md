# CZSC Source Code Reading Guide (Quick Reference)

> A comprehensive guide to understanding the CZSC (Chan Theory Technical Analysis) quantitative trading library

## 🎯 Quick Start

### What is CZSC?

CZSC is a comprehensive Python library for quantitative trading based on Chan Theory (缠中说禅), featuring:

- ✅ Automated identification of patterns (分型), strokes (笔), segments (线段), and pivots (中枢)
- ✅ Multi-timeframe joint analysis framework
- ✅ Signal-Event-Trading system
- ✅ Strategy backtesting and optimization
- ✅ Multiple data source connectors
- ✅ Rust/Python hybrid architecture for performance

## 📚 Reading Order

### Phase 1: Core Data Structures (Must Read)

| File | Key Content | Focus |
|------|-------------|-------|
| `czsc/py/enum.py` | Enumerations | `Freq`, `Mark`, `Direction`, `Operate` |
| `czsc/py/objects.py` | Data structures | `RawBar`, `NewBar`, `FX`, `BI`, `ZS`, `Signal`, `Event`, `Position` |
| `czsc/core.py` | Hybrid architecture | Rust/Python smart import |

### Phase 2: Core Algorithms (Must Read)

| File | Key Content | Focus |
|------|-------------|-------|
| `czsc/py/analyze.py` | CZSC analysis class | `remove_include`, `check_fx`, `check_bi` |
| `czsc/py/bar_generator.py` | Bar generator | Multi-timeframe synthesis |

### Phase 3: Signal System (Important)

| File | Key Content |
|------|-------------|
| `czsc/signals/bar.py` | Bar-level signals |
| `czsc/signals/cxt.py` | Context signals |
| `czsc/signals/tas.py` | Technical indicator signals |
| `czsc/signals/vol.py` | Volume signals |
| `czsc/signals/pos.py` | Position-related signals |

### Phase 4: Trading Framework (Core Application)

| File | Key Content |
|------|-------------|
| `czsc/traders/base.py` | `CzscSignals`, `CzscTrader` |
| `czsc/strategies.py` | Strategy templates |
| `czsc/sensors/cta.py` | CTA research framework |
| `czsc/traders/dummy.py` | Simple backtest |

## 🔑 Core Concepts

### Signal-Event-Trading System

```
Raw Bars → Signals → Events → Trading Decisions
```

- **Signal**: Basic technical indicator or market state
- **Event**: Logical combination of signals (AND/OR/NOT) representing trading conditions
  - Contains `signals_all` (must satisfy all), `signals_any` (satisfy any), `signals_not` (must not appear)
- **Position**: Complete trading strategy with entry/exit rules

### Chan Theory Objects

```python
RawBar   # Raw K-line with OHLCV
  ↓ Remove inclusion relationship
NewBar   # Processed K-line without inclusion
  ↓ Identify patterns
FX       # Pattern (top/bottom)
  ↓ Identify strokes
BI       # Stroke (connection between adjacent patterns)
  ↓ Identify segments and pivots
ZS       # Pivot (price oscillation zone)
```

## 💻 Quick Examples

### Example 1: Basic Chan Analysis

```python
from czsc.core import CZSC, format_standard_kline, Freq
from czsc.mock import generate_symbol_kines

# Generate K-line data
df = generate_symbol_kines('000001', '30分钟', '20240101', '20240131')
bars = format_standard_kline(df, freq=Freq.F30)

# Create CZSC analysis object
czsc_obj = CZSC(bars)

# View results
print(f"Raw bars: {len(czsc_obj.bars_raw)}")
print(f"Patterns: {len(czsc_obj.fx_list)}")
print(f"Strokes: {len(czsc_obj.bi_list)}")
```

### Example 2: Multi-Timeframe Synthesis

```python
from czsc.core import BarGenerator, format_standard_kline, Freq
from czsc.mock import generate_symbol_kines

# Prepare 1-minute bars
df = generate_symbol_kines('000001', '1分钟', '20240101', '20240105')
bars = format_standard_kline(df, freq=Freq.F1)

# Create bar generator
bg = BarGenerator(
    base_freq='1分钟',
    freqs=['5分钟', '15分钟', '30分钟', '日线']
)

# Update bars
for bar in bars:
    bg.update(bar)

# Check results
for freq, freq_bars in bg.bars.items():
    print(f"{freq}: {len(freq_bars)} bars")
```

### Example 3: Calculate Signals

```python
from czsc.traders import CzscSignals

# Define signal configuration
signals_config = [
    {'name': 'czsc.signals.tas_ma_base_V221101', 
     'freq': '日线', 'di': 1, 'ma_type': 'SMA', 'timeperiod': 5},
]

# Create signal calculator
cs = CzscSignals(bg, signals_config=signals_config)

# View current signals
print("Current signals:")
for k, v in cs.s.items():
    print(f"  {k}: {v}")
```

## 📖 Learning Path

### Level 1: Beginner (1-2 weeks)
- Understand basic concepts
- Run example strategies
- Modify strategy parameters

### Level 2: Intermediate (2-4 weeks)
- Read signal functions
- Write custom signals
- Understand naming conventions

### Level 3: Advanced (4-8 weeks)
- Develop complete strategies
- Use CTAResearch framework
- Parameter optimization

### Level 4: Expert (Ongoing)
- Understand Rust implementation
- Contribute code
- Develop custom connectors

## 📦 Key Modules

### Core Modules (Must Read)
```
czsc/
├── core.py                    # Entry point
├── py/
│   ├── enum.py                # Enumerations
│   ├── objects.py             # Data structures
│   ├── analyze.py             # CZSC class
│   └── bar_generator.py       # Bar generator
├── signals/                   # Signal library
├── traders/                   # Trading framework
└── strategies.py              # Strategy templates
```

### Tools & Services (Optional)
```
czsc/
├── utils/                     # Utilities
│   ├── ta.py                  # Technical indicators
│   └── plotting/backtest.py   # Backtest visualization
├── svc/                       # Services
│   └── backtest.py            # Backtest analysis
└── connectors/                # Data connectors
```

## 🔗 Resources

### Documentation
- [API Documentation](https://czsc.readthedocs.io/en/latest/modules.html)
- [Feishu Wiki](https://s0cqcxuy3p.feishu.cn/wiki/wikcn3gB1MKl3ClpLnboHM1QgKf) (Chinese)
- [Video Tutorials](https://space.bilibili.com/243682308/channel/series) (Chinese)

### Community
- [Feishu Group](https://applink.feishu.cn/client/chat/chatter/add_by_link?link_token=0bak668e-7617-452c-b935-94d2c209e6cf)
- GitHub Issues
- WeChat: zengbin93

## ❓ FAQ

**Q: Python or Rust version?**
- Beginners: Read Python version (`czsc/py/`)
- Set `CZSC_USE_PYTHON=1` to force Python

**Q: What is `di` parameter?**
- `di`: Distance Index (倒数第几根K线)
- `di=1`: Last bar (real-time)
- `di=2`: Second to last bar

**Q: How to understand "remove inclusion"?**
- Core Chan Theory concept
- Merges bars with inclusion relationship
- See `remove_include` in `czsc/py/analyze.py`

## 📊 Strategy Structure

```python
from czsc import CzscStrategyBase, Position, Event

class MyStrategy(CzscStrategyBase):
    @property
    def positions(self):
        # Define entry events
        opens = [{
            "operate": "开多",
            "signals_all": ["signal1", "signal2"],  # Must satisfy all
            "signals_any": ["signal3"],              # Satisfy any
            "signals_not": ["signal5"],              # Must not appear
        }]
        
        # Define exit events
        exits = [...]
        
        # Create position object
        pos = Position(
            name="Strategy Name",
            symbol=self.symbol,
            opens=[Event.load(x) for x in opens],
            exits=[Event.load(x) for x in exits],
            interval=3600,  # Entry interval (seconds)
            timeout=100,    # Timeout (bars)
            stop_loss=500   # Stop loss (basis points)
        )
        return [pos]
```

## 🎓 Recommended Reading Order

1. ✅ **Day 1**: Core concepts (this document)
2. ✅ **Day 2-3**: Data structures (`objects.py`, `enum.py`)
3. ✅ **Day 4-6**: Core algorithms (`analyze.py`)
4. ✅ **Week 2**: Signal system (`signals/`)
5. ✅ **Week 3-4**: Trading framework (`traders/`, `strategies.py`)

**Remember**: Practice while learning! Run examples and modify code.

---

**Version**: v1.0.0  
**Last Updated**: 2024-02-16  
**Maintainer**: CZSC Community
