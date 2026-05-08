# pos 模块信号索引

> 源码: `crates/czsc-signals/src/pos.rs`
> 共 16 个信号

| 信号名 | 参数模板 | 说明 | 详细文档 |
|--------|----------|------|----------|
| `pos_bar_stop_V230524` | `"{pos_name}_{freq1}N{n}K_止损V230524` | 按开仓点附近N根K线极值止损 | [详细文档](signals/pos_bar_stop_V230524.md) |
| `pos_fix_exit_V230624` | `"{pos_name}_固定{th}BP止盈止损_出场V230624` | 固定 BP 止盈止损 | [详细文档](signals/pos_fix_exit_V230624.md) |
| `pos_fx_stop_V230414` | `"{freq1}_{pos_name}N{n}_止损V230414` | 按开仓点附近分型止损 | [详细文档](signals/pos_fx_stop_V230414.md) |
| `pos_holds_V230414` | `"{pos_name}_{freq1}N{n}M{m}_趋势判断V230414` | 开仓后 N 根K线收益与阈值比较 | [详细文档](signals/pos_holds_V230414.md) |
| `pos_holds_V230807` | `"{pos_name}_{freq1}N{n}M{m}T{t}_BS辅助V230807` | 开仓后收益在 (t, m) 之间触发保本 | [详细文档](signals/pos_holds_V230807.md) |
| `pos_holds_V240428` | `"{pos_name}_{freq1}H{h}T{t}N{n}_保本V240428` | 最大盈利回撤比例保本 | [详细文档](signals/pos_holds_V240428.md) |
| `pos_holds_V240608` | `"{pos_name}_{freq1}W{w}N{n}_保本V240608` | 跌破/升破开仓前窗口极值后，回到成本价指定档位保本 | [详细文档](signals/pos_holds_V240608.md) |
| `pos_ma_V230414` | `"{pos_name}_{freq1}#{ma_type}#{timeperiod}_持有状态V230414` | 判断开仓后是否升破/跌破均线 | [详细文档](signals/pos_ma_V230414.md) |
| `pos_profit_loss_V230624` | `"{pos_name}_{freq1}YKB{ykb}N{n}_盈亏比判断V230624` | 盈亏比阈值判断 | [详细文档](signals/pos_profit_loss_V230624.md) |
| `pos_status_V230808` | `"{pos_name}_持仓状态_BS辅助V230808` | 持仓状态 | [详细文档](signals/pos_status_V230808.md) |
| `pos_stop_V240331` | `"{pos_name}_{freq1}#{n}_止损V240331` | 最近 N 根K线追踪止损 | [详细文档](signals/pos_stop_V240331.md) |
| `pos_stop_V240428` | `"{pos_name}_{freq1}T{t}N{n}_止损V240428` | 按开仓前离散价位跳数止损 | [详细文档](signals/pos_stop_V240428.md) |
| `pos_stop_V240608` | `"{pos_name}_{freq1}W{w}N{n}_止损V240608` | 开仓后突破开仓前窗口极值 N 档止损 | [详细文档](signals/pos_stop_V240608.md) |
| `pos_stop_V240614` | `"{pos_name}_{freq1}N{n}_止损V240614` | 开仓后低于/高于成本价的 K线数量计数止损 | [详细文档](signals/pos_stop_V240614.md) |
| `pos_stop_V240717` | `"{pos_name}_{freq1}N{n}T{timeperiod}_止损V240717` | 基于开仓时 ATR 的计数止损 | [详细文档](signals/pos_stop_V240717.md) |
| `pos_take_V240428` | `"{pos_name}_{freq1}T{t}N{n}_止盈V240428` | 倍量阳/阴线计数止盈 | [详细文档](signals/pos_take_V240428.md) |
