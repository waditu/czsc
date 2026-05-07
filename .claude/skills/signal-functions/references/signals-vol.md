# vol 模块信号索引

> 源码: `crates/czsc-signals/src/vol.rs`
> 共 6 个信号

| 信号名 | 参数模板 | 说明 | 详细文档 |
|--------|----------|------|----------|
| `vol_double_ma_V230214` | `"{freq}_D{di}VOL双均线{ma_type}#{t1}#{t2}_BS辅助V230214` | 成交量双均线多空信号 | [详细文档](signals/vol_double_ma_V230214.md) |
| `vol_gao_di_V221218` | `"{freq}_D{di}K_量柱V221218` | 高量柱与低量柱信号 | [详细文档](signals/vol_gao_di_V221218.md) |
| `vol_single_ma_V230214` | `"{freq}_D{di}VOL#{ma_type}#{timeperiod}_分类V230214` | 单成交量均线多空与方向信号 | [详细文档](signals/vol_single_ma_V230214.md) |
| `vol_ti_suo_V221216` | `"{freq}_D{di}K_量柱V221216` | 梯量与缩量柱信号 | [详细文档](signals/vol_ti_suo_V221216.md) |
| `vol_window_V230731` | `"{freq}_D{di}W{w}M{m}N{n}_窗口能量V230731` | 窗口成交量分层特征 | [详细文档](signals/vol_window_V230731.md) |
| `vol_window_V230801` | `"{freq}_D{di}W{w}_窗口能量V230801` | 窗口成交量先后顺序特征 | [详细文档](signals/vol_window_V230801.md) |
