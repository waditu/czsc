# v2.0.0 清理非缠论核心 API 迁移指南

> 关联：
> - 飞书任务：[《清理非缠论核心 API》](https://s0cqcxuy3p.feishu.cn/wiki/OGUUwZMZdi2jtykaFpKcAPz4nig)
> - 执行方案：[《执行方案与验收标准（v1）》](https://s0cqcxuy3p.feishu.cn/docx/UOv8dobnDoFO43xcTvbcsOxZntc)
> - 执行细节：[《执行细节与验收记录》](https://s0cqcxuy3p.feishu.cn/docx/GRtMdbDBSopOtCxa4TYcckHVnnd)

## 删除清单

| 对象 | 旧路径 | 状态 |
|---|---|---|
| Streamlit 组件 | `czsc.svc.*`（60+ `show_*`） | ❌ 删除 |
| Python TA 命名空间 | `czsc.ta.*` 顶层 alias | ❌ 删除（Rust `czsc._native.ta` 保留） |
| streamlit 运行时依赖 | `pyproject.toml` 核心 deps | ❌ 删除 |
| Streamlit 示例 | `docs/examples/{10,11,12,14,16}_streamlit_*.py` + `_streamlit_smoke.py` | ❌ 删除 |
| Streamlit renderer | `czsc/utils/plotting/lightweight/_streamlit_renderer.py` | ❌ 删除 |
| ta 数值等价测试 | `tests/unit/test_ta_parity.py` | ❌ 删除（Rust 单测覆盖） |
| HTML 可视化 | `czsc.utils.plotting.{kline,backtest,lightweight}.*` | ✅ 保留 |
| TA 顶层别名 | `czsc.{ema,sma,rolling_rank,boll_positions,ultimate_smoother}` | ✅ 保留 |
| Rust TA | `czsc._native.ta.*` | ✅ 保留（信号内部依赖） |

## 替代方案

### Streamlit 组件 → plotly + HTML

| 旧调用 | 新调用 |
|---|---|
| `czsc.svc.show_cumulative_returns(dret)` | `czsc.utils.plotting.backtest.plot_cumulative_returns(dret)` |
| `czsc.svc.show_drawdowns(dret)` | `czsc.utils.plotting.backtest.plot_drawdown_analysis(dret)` |
| `czsc.svc.show_monthly_return(dret)` | `czsc.utils.plotting.backtest.plot_monthly_heatmap(dret)` |
| `czsc.svc.show_weight_backtest(dfw)` | `wbt.WeightBacktest(data=dfw, ...)` + `plot_backtest_stats` |
| `czsc.svc.show_czsc_trader(ct)` | `czsc.utils.plotting.lightweight.plot_czsc_trader(ct, output="html")` |
| `czsc.svc.show_correlation(df)` | 自行 `plotly.express.imshow(df.corr())` |

完整 `show_*` 与 `plot_*` 的一一映射建议参考 PR-2 删除前的 `czsc/svc/` 源码（git 历史）。

### Python `czsc.ta.*` → Rust `czsc._native.ta.*`

```python
# 旧
from czsc.ta import sma, ema, ultimate_smoother

# 新（仅信号函数需要时用；普通业务代码请直接用 czsc.sma / czsc.ema 顶层别名）
from czsc._native.ta import sma, ema, ultimate_smoother
# 或者顶层别名（保留）
from czsc import sma, ema, ultimate_smoother, rolling_rank, boll_positions
```

### Streamlit 嵌入 lightweight chart → 调用方拼接

```python
# 旧
from czsc.utils.plotting.lightweight import plot_czsc
plot_czsc(c, output="streamlit")

# 新
import streamlit as st
from czsc.utils.plotting.lightweight import plot_czsc
html = plot_czsc(c, output="html")
st.components.v1.html(html, height=900, scrolling=True)
```

## 升级步骤

1. **安装新版本**：
   ```bash
   uv pip install --upgrade "czsc==2.0.0"
   # 若仍需 streamlit 集成
   uv pip install streamlit
   ```
2. **替换 `czsc.svc.*` 调用**：按上表逐项替换为 `czsc.utils.plotting.*`。
3. **替换 `czsc.ta.*` 调用**：批量改 `czsc.ta` → `czsc._native.ta` 或顶层别名。
4. **删除对已删 streamlit 示例的引用**：检查脚本目录，5 个示例已不存在。
5. **跑测试**：本仓库 `pytest` 应当全绿。

## 验收命令

完整验收清单详见执行方案 §5。关键命令：

```bash
# 顶层属性已删
python -c "import czsc; assert not hasattr(czsc, 'svc') and not hasattr(czsc, 'ta'); print('OK')"

# Rust TA 仍可用
python -c "import czsc._native.ta as t; print(t.sma([1.0]*30, 5)[-1])"

# 不自动安装 streamlit
rm -rf .venv && uv sync --extra dev
uv pip list | grep -i streamlit  # 期望 0 行

# 测试
uv run --no-sync pytest --run-slow
```
