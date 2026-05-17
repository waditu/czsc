# 清理非缠论核心 API 迁移指南（1.0.0 核心重构延续，PR #313）

> 关联：
> - 飞书任务：[《清理非缠论核心 API》](https://s0cqcxuy3p.feishu.cn/wiki/OGUUwZMZdi2jtykaFpKcAPz4nig)
> - 执行方案：[《执行方案与验收标准（v1）》](https://s0cqcxuy3p.feishu.cn/docx/UOv8dobnDoFO43xcTvbcsOxZntc)
> - 执行细节：[《执行细节与验收记录》](https://s0cqcxuy3p.feishu.cn/docx/GRtMdbDBSopOtCxa4TYcckHVnnd)
> - 阶段二任务：[《20260517 清理非核心API接口》](https://s0cqcxuy3p.feishu.cn/wiki/NGlFw8qXoiGNcnkkDMacNKXhnph)
> - 阶段二方案：[《清理非核心 API 接口 v2 — 执行方案与验收标准》](https://s0cqcxuy3p.feishu.cn/docx/H0UodenI2oBvzHx0IeYc05rCn7e)

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

> ⚠️ **二阶段清理 PR-C 起**：`czsc.utils.plotting.backtest.plot_*` 系列已整体删除。下表中曾推荐过这些函数，请改用 `plotly.express` 直绘 / `wbt.generate_backtest_report` / `czsc.utils.plotting.lightweight.plot_czsc_trader`。

| 旧调用 | 新调用（阶段一推荐） | 阶段二实际状态 |
|---|---|---|
| `czsc.svc.show_cumulative_returns(dret)` | `czsc.utils.plotting.backtest.plot_cumulative_returns(dret)` | **已删除**，改用 `plotly.express.line((1 + dret).cumprod())` |
| `czsc.svc.show_drawdowns(dret)` | `czsc.utils.plotting.backtest.plot_drawdown_analysis(dret)` | **已删除**，改用 `wbt.top_drawdowns` + 自行画图 |
| `czsc.svc.show_monthly_return(dret)` | `czsc.utils.plotting.backtest.plot_monthly_heatmap(dret)` | **已删除**，改用 `dret.resample("M").sum().unstack()` + `px.imshow` |
| `czsc.svc.show_weight_backtest(dfw)` | `wbt.WeightBacktest(data=dfw, ...)` + `plot_backtest_stats` | `WeightBacktest` 仍可用；`plot_backtest_stats` **已删除**，改用 `wbt.generate_backtest_report` |
| `czsc.svc.show_czsc_trader(ct)` | `czsc.utils.plotting.lightweight.plot_czsc_trader(ct, output="html")` | 仍可用（lightweight 保留） |
| `czsc.svc.show_correlation(df)` | 自行 `plotly.express.imshow(df.corr())` | 仍可用 |

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

1. **安装新版本**（继续 1.0.0 系列，本次清理含 breaking change）：
   ```bash
   uv pip install --upgrade "czsc==1.0.0"
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

---

## 阶段二：删除剩余 17 个非缠论核心 API（PR-A/B/C/D，占位章节）

> 本章节由 PR-A 落地占位，PR-B / PR-C / PR-D 逐步补全。

### 阶段二删除清单

| 来源 | API | PR | 替代方案 |
|---|---|---|---|
| `czsc/eda.py` | `cal_yearly_days` | PR-B | 自行 `df.groupby(df.index.year).size().max()` 或直接传常数 `yearly_days=252` |
| `czsc/eda.py` | `weights_simple_ensemble` | PR-B | 自行 `df["weight"] = df[weight_cols].mean(axis=1)` 等等价的一行 pandas |
| `czsc/eda.py` | `cal_trade_price` | PR-B | 调用方自行在 1 分钟 K 线上 rolling 计算 TWAP/VWAP |
| `czsc/eda.py` | `turnover_rate` | PR-B | 自行 `dfw.groupby("symbol")["weight"].diff().abs()` |
| `czsc/utils/__init__.py` | `create_grid_params` | PR-B | 直接用 `sklearn.model_selection.ParameterGrid` |
| `czsc/utils/__init__.py` | `mac_address` | PR-B | 直接用 `uuid.getnode()` |
| `czsc/utils/analysis/stats.py` | `holds_performance` | PR-B | 调用 `wbt.WeightBacktest` 后取 `daily_performance` |
| `czsc/utils/analysis/stats.py` | `rolling_daily_performance` | PR-B | 自行 `daily_performance` 配合 `rolling.apply` |
| `czsc/utils/plotting/kline.py` | `KlineChart` | PR-C | 用 `czsc.utils.plotting.lightweight.plot_czsc{,_trader,_signals}` 输出 HTML |
| `czsc/utils/plotting/kline.py` | `plot_czsc_chart` | PR-C | 同上 |
| `czsc/utils/plotting/backtest.py` | `plot_cumulative_returns` | PR-C | 自行 `plotly.express.line((1 + dret).cumprod())` |
| `czsc/utils/plotting/backtest.py` | `plot_drawdown_analysis` | PR-C | 自行根据 `wbt.top_drawdowns` 画图 |
| `czsc/utils/plotting/backtest.py` | `plot_daily_return_distribution` | PR-C | 自行 `plotly.express.histogram(dret)` |
| `czsc/utils/plotting/backtest.py` | `plot_monthly_heatmap` | PR-C | 自行 `monthly = dret.resample("M").sum().unstack()` + `px.imshow` |
| `czsc/utils/plotting/backtest.py` | `plot_backtest_stats` | PR-C | 自行组合上述 4 个 |
| `czsc/utils/plotting/backtest.py` | `plot_colored_table` | PR-C | 自行 `plotly.graph_objects.Table` + `cell.fill.color` |
| `czsc/utils/plotting/backtest.py` | `plot_long_short_comparison` | PR-C | 自行 `make_subplots` + 上面的 2 个 |

### 附带清理（整文件 git rm）

| 文件 | PR | 原因 |
|---|---|---|
| `czsc/utils/plotting/backtest.py` | PR-C | 7 个 plot_* 删除后无残留逻辑 |
| `czsc/utils/plotting/common.py` | PR-C | 仅为 `backtest.py` 提供常量与辅助函数 |

> `_macd.py` 原计划与 backtest / common 一起 git rm，但 `lightweight/_data.py` 仍 lazy import `compute_macd`，故保留为 `czsc.utils.plotting` 内部模块（不对外暴露）。

### ratchet 测试位置

`tests/compat/test_drop_secondary_api.py` —— PR-A 创建的双轨 xfail strict 测试，PR-B / PR-C 删除后即可摘 `@xfail`。

### 详细完成状态

- [x] PR-A：防护测试 + 基线快照 + 迁移占位
- [x] PR-B：删除 8 个工具/分析函数
- [x] PR-C：删除 9 个绘图 API + 附带清理
- [x] PR-D：反转上一波防护测试 + 文档收尾
