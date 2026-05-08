# bar 模块信号索引

> 源码: `crates/czsc-signals/src/bar.rs`
> 共 46 个信号

| 信号名 | 参数模板 | 说明 | 详细文档 |
|--------|----------|------|----------|
| `bar_accelerate_V221110` | `"{freq}_D{di}W{window}_加速V221110` | 区间加速走势判定 | [详细文档](signals/bar_accelerate_V221110.md) |
| `bar_accelerate_V221118` | `"{freq}_D{di}W{window}#{ma_type}#{timeperiod}_加速V221118` | 均线偏离加速判定 | [详细文档](signals/bar_accelerate_V221118.md) |
| `bar_accelerate_V240428` | `"{freq}_D{di}W{w}T{t}_加速V240428` | 滚动差分加速判定 | [详细文档](signals/bar_accelerate_V240428.md) |
| `bar_amount_acc_V230214` | `"{freq}_D{di}N{n}_累计超{t}千万` | 区间累计成交额信号 | [详细文档](signals/bar_amount_acc_V230214.md) |
| `bar_big_solid_V230215` | `"{freq}_D{di}N{n}_MIDV230215` | 窗口最大实体中位多空信号 | [详细文档](signals/bar_big_solid_V230215.md) |
| `bar_bpm_V230227` | `"{freq}_D{di}N{n}T{th}_绝对动量V230227` | 绝对动量分层 | [详细文档](signals/bar_bpm_V230227.md) |
| `bar_break_V240428` | `"{freq}_D{di}W{w}_事件V240428` | 收盘极值突破 | [详细文档](signals/bar_break_V240428.md) |
| `bar_channel_V230508` | `"{freq}_D{di}M{m}_通道V230507` | 窄幅通道方向判定 | [详细文档](signals/bar_channel_V230508.md) |
| `bar_classify_V240606` | `"{freq}_D{di}收盘位置_分类V240606` | 单根K线收盘位置分类 | [详细文档](signals/bar_classify_V240606.md) |
| `bar_classify_V240607` | `"{freq}_D{di}K2收盘位置_分类V240607` | 两根K线收盘位置分类 | [详细文档](signals/bar_classify_V240607.md) |
| `bar_decision_V240608` | `"{freq}_W{w}N{n}Q{q}放量_决策区域V240608` | 放量反向决策区 | [详细文档](signals/bar_decision_V240608.md) |
| `bar_decision_V240616` | `"{freq}_W{w}N{n}强弱_决策区域V240616` | 新高新低后的强弱决策 | [详细文档](signals/bar_decision_V240616.md) |
| `bar_dual_thrust_V230403` | `"{freq}_D{di}通道突破#{N}#{K1}#{K2}_BS辅助V230403` | Dual Thrust 通道突破 | [详细文档](signals/bar_dual_thrust_V230403.md) |
| `bar_eight_V230702` | `"{freq}_D{di}#8K_走势分类V230702` | 8K 走势分类 | [详细文档](signals/bar_eight_V230702.md) |
| `bar_end_V221211` | `"{freq}_{freq1}结束_BS辅助221211` | 判断大周期K线是否闭合 | [详细文档](signals/bar_end_V221211.md) |
| `bar_fake_break_V230204` | `"{freq}_D{di}N{n}M{m}_假突破V230204` | 区间假突破判定 | [详细文档](signals/bar_fake_break_V230204.md) |
| `bar_fang_liang_break_V221216` | `"{freq}_D{di}TH{th}#{ma_type}#{timeperiod}_突破V221216` | 放量突破与缩量回踩 | [详细文档](signals/bar_fang_liang_break_V221216.md) |
| `bar_limit_down_V230525` | `"{freq}_跌停后无下影线长实体阳线_短线V230525` | 跌停后反包阳线 | [详细文档](signals/bar_limit_down_V230525.md) |
| `bar_mean_amount_V221112` | `"{freq}_D{di}K{n}B均额_{th1}至{th2}千万` | 区间均额分类信号 | [详细文档](signals/bar_mean_amount_V221112.md) |
| `bar_operate_span_V221111` | `"{freq}_T{t1}#{t2}_时间区间V221111` | 日内时间区间过滤 | [详细文档](signals/bar_operate_span_V221111.md) |
| `bar_plr_V240427` | `"{freq}_D{di}W{w}T{t}M{m}_盈亏比V240427` | 盈亏比约束 | [详细文档](signals/bar_plr_V240427.md) |
| `bar_polyfit_V240428` | `"{freq}_D{di}W{w}_分类V240428` | 一阶二阶拟合分类 | [详细文档](signals/bar_polyfit_V240428.md) |
| `bar_r_breaker_V230326` | `"{freq}_RBreaker_BS辅助V230326` | RBreaker 价格位判定 | [详细文档](signals/bar_r_breaker_V230326.md) |
| `bar_reversal_V230227` | `"{freq}_D{di}A{avg_bp}_反转V230227` | 末根反转迹象判定 | [详细文档](signals/bar_reversal_V230227.md) |
| `bar_section_momentum_V221112` | `"{freq}_D{di}K{n}B_阈值{th}BPV221112` | 区间动量强弱与波动 | [详细文档](signals/bar_section_momentum_V221112.md) |
| `bar_shuang_fei_V230507` | `"{freq}_D{di}双飞_短线V230507` | 双飞涨停形态 | [详细文档](signals/bar_shuang_fei_V230507.md) |
| `bar_single_V230214` | `"{freq}_D{di}T{t}_状态V230214` | 单K状态信号 | [详细文档](signals/bar_single_V230214.md) |
| `bar_single_V230506` | `"{freq}_D{di}单K趋势N{n}_BS辅助V230506` | 单K趋势分层信号 | [详细文档](signals/bar_single_V230506.md) |
| `bar_td9_V240616` | `"{freq}_神奇九转N{n}_BS辅助V240616` | 神奇九转计数 | [详细文档](signals/bar_td9_V240616.md) |
| `bar_time_V230327` | `"{freq}_日内时间_分段V230327` | 日内时间分段信号 | [详细文档](signals/bar_time_V230327.md) |
| `bar_tnr_V230629` | `"{freq}_D{di}TNR{timeperiod}_趋势V230629` | TNR 分层信号 | [详细文档](signals/bar_tnr_V230629.md) |
| `bar_tnr_V230630` | `"{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630` | TNR 噪音变化判定 | [详细文档](signals/bar_tnr_V230630.md) |
| `bar_trend_V240209` | `"{freq}_D{di}N{N}趋势跟踪_BS辅助V240209` | 趋势跟踪结构判定 | [详细文档](signals/bar_trend_V240209.md) |
| `bar_triple_V230506` | `"{freq}_D{di}三K加速_裸K形态V230506` | 三K加速形态信号 | [详细文档](signals/bar_triple_V230506.md) |
| `bar_vol_bs1_V230224` | `"{freq}_D{di}N{n}量价_BS1辅助V230224` | 量价高低点辅助 | [详细文档](signals/bar_vol_bs1_V230224.md) |
| `bar_vol_grow_V221112` | `"{freq}_D{di}K{n}B_放量V221112` | 成交量放大信号 | [详细文档](signals/bar_vol_grow_V221112.md) |
| `bar_volatility_V241013` | `"{freq}_波动率分层W{w}N{n}_完全分类V241013` | 波动率三层分类 | [详细文档](signals/bar_volatility_V241013.md) |
| `bar_weekday_V230328` | `"{freq}_周内时间_分段V230328` | 周内时间分段信号 | [详细文档](signals/bar_weekday_V230328.md) |
| `bar_window_ps_V230731` | `"{freq}_W{w}M{m}N{n}L{l}_支撑压力位V230731` | 支撑压力位分位特征 | [详细文档](signals/bar_window_ps_V230731.md) |
| `bar_window_ps_V230801` | `"{freq}_N{n}W{w}_支撑压力位V230801` | 支撑压力位窗口极值 | [详细文档](signals/bar_window_ps_V230801.md) |
| `bar_window_std_V230731` | `"{freq}_D{di}W{w}M{m}N{n}_窗口波动V230731` | 窗口波动分层特征 | [详细文档](signals/bar_window_std_V230731.md) |
| `bar_zdf_V221203` | `"{freq}_D{di}{mode}_{t1}至{t2}` | 单根涨跌幅区间信号 | [详细文档](signals/bar_zdf_V221203.md) |
| `bar_zdt_V230331` | `"{freq}_D{di}_涨跌停V230331` | 涨跌停识别信号 | [详细文档](signals/bar_zdt_V230331.md) |
| `bar_zfzd_V241013` | `"{freq}_窄幅震荡N{n}_形态V241013` | 窄幅震荡（全重叠） | [详细文档](signals/bar_zfzd_V241013.md) |
| `bar_zfzd_V241014` | `"{freq}_窄幅震荡N{n}_形态V241014` | 窄幅震荡（最大实体重叠） | [详细文档](signals/bar_zfzd_V241014.md) |
| `bar_zt_count_V230504` | `"{freq}_D{di}W{window}涨停计数_裸K形态V230504` | 窗口涨停计数 | [详细文档](signals/bar_zt_count_V230504.md) |
