# tas 模块信号索引

> 源码: `crates/czsc-signals/src/tas.rs`
> 共 59 个信号

| 信号名 | 参数模板 | 说明 | 详细文档 |
|--------|----------|------|----------|
| `cci_decision_V240620` | `"{freq}_N{n}CCI_决策区域V240620` | CCI 逆势决策区域 | [详细文档](signals/cci_decision_V240620.md) |
| `tas_accelerate_V230531` | `"{freq}_D{di}N{n}T{t}_BOLL加速V230531` | BOLL 通道加速信号 | [详细文档](signals/tas_accelerate_V230531.md) |
| `tas_angle_V230802` | `"{freq}_D{di}N{n}T{th}_笔角度V230802` | 笔角度偏离信号 | [详细文档](signals/tas_angle_V230802.md) |
| `tas_atr_V230630` | `"{freq}_D{di}ATR{timeperiod}_波动V230630` | ATR 波动分层信号 | [详细文档](signals/tas_atr_V230630.md) |
| `tas_atr_break_V230424` | `"{freq}_D{di}ATR{timeperiod}T{th}突破_BS辅助V230424` | ATR 通道突破 | [详细文档](signals/tas_atr_break_V230424.md) |
| `tas_boll_bc_V221118` | `"{freq}_D{di}N{n}M{m}L{line}#BOLL{timeperiod}_背驰V221118` | BOLL背驰辅助信号 | [详细文档](signals/tas_boll_bc_V221118.md) |
| `tas_boll_cc_V230312` | `"{freq}_D{di}BOLL{timeperiod}S{nbdev}SP{sp}_BS辅助V230312` | 布林进出场信号 | [详细文档](signals/tas_boll_cc_V230312.md) |
| `tas_boll_power_V221112` | `"{freq}_D{di}BOLL{timeperiod}_强弱V221112` | BOLL强弱分层信号 | [详细文档](signals/tas_boll_power_V221112.md) |
| `tas_boll_vt_V230212` | `"{freq}_D{di}BOLL{timeperiod}S{nbdev}MO{max_overlap}_BS辅助V230212` | BOLL 通道突破进出场信号 | [详细文档](signals/tas_boll_vt_V230212.md) |
| `tas_cci_base_V230402` | `"{freq}_D{di}CCI{timeperiod}#{min_count}#{max_count}_BS辅助V230402` | CCI 极值连续计数信号 | [详细文档](signals/tas_cci_base_V230402.md) |
| `tas_cross_status_V230619` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_金死叉V230619` | 0轴上下金死叉次数 | [详细文档](signals/tas_cross_status_V230619.md) |
| `tas_cross_status_V230624` | `"{freq}_D{di}N{n}MD{md}_MACD交叉数量V230624` | 指定金死叉数值 | [详细文档](signals/tas_cross_status_V230624.md) |
| `tas_cross_status_V230625` | `"{freq}_D{di}N{n}MD{md}J{j}S{s}_MACD交叉数量V230625` | 指定金叉/死叉次数后状态 | [详细文档](signals/tas_cross_status_V230625.md) |
| `tas_dif_layer_V241010` | `"{freq}_DIF分层W{w}T{t}_完全分类V241010` | DIF 三层分类 | [详细文档](signals/tas_dif_layer_V241010.md) |
| `tas_dif_zero_V240612` | `"{freq}_DIF靠近零轴T{t}_BS辅助V240612` | DIF靠近零轴买卖点信号（基于最近一笔） | [详细文档](signals/tas_dif_zero_V240612.md) |
| `tas_dif_zero_V240614` | `"{freq}_DIF靠近零轴W{w}T{t}_BS辅助V240614` | DIF靠近零轴买卖点信号 | [详细文档](signals/tas_dif_zero_V240614.md) |
| `tas_dma_bs_V240608` | `"{freq}_N{n}双均线{t1}#{t2}顺势_BS辅助V240608` | 双均线顺势回调买卖点 | [详细文档](signals/tas_dma_bs_V240608.md) |
| `tas_double_ma_V221203` | `"{freq}_D{di}T{th}#{ma_type}#{timeperiod1}#{timeperiod2}_JX辅助V221203` | 双均线多空强弱信号 | [详细文档](signals/tas_double_ma_V221203.md) |
| `tas_double_ma_V230511` | `"{freq}_D{di}#{ma_type}#{t1}#{t2}_BS辅助V230511` | 双均线反向信号 | [详细文档](signals/tas_double_ma_V230511.md) |
| `tas_double_ma_V240208` | `"{freq}_D{di}N{N}M{M}双均线_BS辅助V240208` | 双均线交叉结构信号 | [详细文档](signals/tas_double_ma_V240208.md) |
| `tas_first_bs_V230217` | `"{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS1辅助V230217` | 均线结合K线形态的一买一卖辅助 | [详细文档](signals/tas_first_bs_V230217.md) |
| `tas_hlma_V230301` | `"{freq}_D{di}#{ma_type}#{timeperiod}HLMA_BS辅助V230301` | HMA/LMA 多空信号 | [详细文档](signals/tas_hlma_V230301.md) |
| `tas_kdj_base_V221101` | `"{freq}_D{di}K#KDJ{fastk_period}#{slowk_period}#{slowd_period}_KDJ辅助V221101` | KDJ基础辅助信号 | [详细文档](signals/tas_kdj_base_V221101.md) |
| `tas_kdj_evc_V221201` | `"{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{c1}#{c2}_KDJ极值V221201` | KDJ 极值计数信号 | [详细文档](signals/tas_kdj_evc_V221201.md) |
| `tas_kdj_evc_V230401` | `"{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{min_count}#{max_count}_BS辅助V230401` | KDJ 极值计数信号 | [详细文档](signals/tas_kdj_evc_V230401.md) |
| `tas_low_trend_V230627` | `"{freq}_D{di}N{n}TH{th}_趋势230627` | 阴跌/小阳趋势信号 | [详细文档](signals/tas_low_trend_V230627.md) |
| `tas_ma_base_V221101` | `"{freq}_D{di}{ma_type}#{timeperiod}_分类V221101` | 单均线多空与方向信号 | [详细文档](signals/tas_ma_base_V221101.md) |
| `tas_ma_base_V221203` | `"{freq}_D{di}{ma_type}#{timeperiod}T{th}_分类V221203` | 单均线多空与距离分层信号 | [详细文档](signals/tas_ma_base_V221203.md) |
| `tas_ma_base_V230313` | `"{freq}_D{di}#{ma_type}#{timeperiod}MO{max_overlap}_BS辅助V230313` | 单均线开平仓辅助信号（带重叠约束） | [详细文档](signals/tas_ma_base_V230313.md) |
| `tas_ma_cohere_V230512` | `"{freq}_D{di}SMA{ma_seq}_均线系统V230512` | 均线系统粘合/扩散状态 | [详细文档](signals/tas_ma_cohere_V230512.md) |
| `tas_ma_round_V221206` | `"{freq}_D{di}TH{th}#碰{ma_type}#{timeperiod}_BE辅助V221206` | 笔端点触碰均线信号 | [详细文档](signals/tas_ma_round_V221206.md) |
| `tas_ma_system_V230513` | `"{freq}_D{di}SMA{ma_seq}_均线系统V230513` | 均线系统多空排列 | [详细文档](signals/tas_ma_system_V230513.md) |
| `tas_macd_base_V221028` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}#{key}_BS辅助V221028` | MACD/DIF/DEA 多空与方向信号 | [详细文档](signals/tas_macd_base_V221028.md) |
| `tas_macd_base_V230320` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}MO{max_overlap}#{key}_BS辅助V230320` | MACD/DIF/DEA 多空与方向信号（含重叠约束） | [详细文档](signals/tas_macd_base_V230320.md) |
| `tas_macd_bc_V221201` | `"{freq}_D{di}N{n}M{m}#MACD{fastperiod}#{slowperiod}#{signalperiod}_BCV221201` | MACD背驰辅助信号 | [详细文档](signals/tas_macd_bc_V221201.md) |
| `tas_macd_bc_V230803` | `"{freq}_MACD双分型背驰_BS辅助V230803` | 双分型 MACD 背驰信号 | [详细文档](signals/tas_macd_bc_V230803.md) |
| `tas_macd_bc_V230804` | `"{freq}_D{di}MACD背驰_BS辅助V230804` | MACD 黄白线背驰信号 | [详细文档](signals/tas_macd_bc_V230804.md) |
| `tas_macd_bc_V240307` | `"{freq}_D{di}N{n}柱子背驰_BS辅助V240307` | MACD 柱背驰计次信号 | [详细文档](signals/tas_macd_bc_V240307.md) |
| `tas_macd_bc_ubi_V230804` | `"{freq}_MACD背驰_UBI观察V230804` | 未完成笔 MACD 背驰观察 | [详细文档](signals/tas_macd_bc_ubi_V230804.md) |
| `tas_macd_bs1_V230312` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230312` | MACD 辅助一买一卖（笔结构） | [详细文档](signals/tas_macd_bs1_V230312.md) |
| `tas_macd_bs1_V230313` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230313` | MACD 红绿柱第一买卖点 | [详细文档](signals/tas_macd_bs1_V230313.md) |
| `tas_macd_bs1_V230411` | `"{freq}_D{di}T{tha}#{thb}#{thc}_BS1辅助V230411` | MACD DIF 五笔背驰信号 | [详细文档](signals/tas_macd_bs1_V230411.md) |
| `tas_macd_bs1_V230412` | `"{freq}_D{di}T{tha}#{thb}_BS1辅助V230412` | MACD DIF 五笔背驰简化信号 | [详细文档](signals/tas_macd_bs1_V230412.md) |
| `tas_macd_change_V221105` | `"{freq}_D{di}K{n}#MACD{fastperiod}#{slowperiod}#{signalperiod}变色次数_BS辅助V221105` | MACD变色次数信号 | [详细文档](signals/tas_macd_change_V221105.md) |
| `tas_macd_direct_V221106` | `"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}方向_BS辅助V221106` | MACD柱方向信号 | [详细文档](signals/tas_macd_direct_V221106.md) |
| `tas_macd_dist_V230408` | `"{freq}_{key}分层W{w}N{n}_BS辅助V230408` | DIF/DEA/MACD等宽分层信号 | [详细文档](signals/tas_macd_dist_V230408.md) |
| `tas_macd_dist_V230409` | `"{freq}_{key}远离W{w}N{n}T{t}_BS辅助V230409` | DIF/DEA/MACD远离零轴信号 | [详细文档](signals/tas_macd_dist_V230409.md) |
| `tas_macd_dist_V230410` | `"{freq}_{key}多空分层W{w}N{n}_BS辅助V230410` | DIF/DEA/MACD多空分层信号 | [详细文档](signals/tas_macd_dist_V230410.md) |
| `tas_macd_first_bs_V221201` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221201` | MACD一买一卖辅助信号 | [详细文档](signals/tas_macd_first_bs_V221201.md) |
| `tas_macd_first_bs_V221216` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221216` | MACD 第一买卖点（扩展版） | [详细文档](signals/tas_macd_first_bs_V221216.md) |
| `tas_macd_power_V221108` | `"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}强弱_BS辅助V221108` | MACD强弱分层信号 | [详细文档](signals/tas_macd_power_V221108.md) |
| `tas_macd_second_bs_V221201` | `"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS2辅助V221201` | MACD 第二买卖点 | [详细文档](signals/tas_macd_second_bs_V221201.md) |
| `tas_macd_xt_V221208` | `"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}形态_BS辅助V221208` | MACD 柱形态信号 | [详细文档](signals/tas_macd_xt_V221208.md) |
| `tas_rsi_base_V230227` | `"{freq}_D{di}T{th}RSI{timeperiod}_RSI辅助V230227` | RSI超买超卖与方向信号 | [详细文档](signals/tas_rsi_base_V230227.md) |
| `tas_rumi_V230704` | `"{freq}_D{di}F{timeperiod1}S{timeperiod2}R{rumi_window}_BS辅助V230704` | RUMI 零轴切换信号 | [详细文档](signals/tas_rumi_V230704.md) |
| `tas_sar_base_V230425` | `"{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425` | SAR 基础多空信号 | [详细文档](signals/tas_sar_base_V230425.md) |
| `tas_second_bs_V230228` | `"{freq}_D{di}N{n}#{ma_type}#{timeperiod}_BS2辅助V230228` | 均线结合K线形态的二买二卖辅助 | [详细文档](signals/tas_second_bs_V230228.md) |
| `tas_second_bs_V230303` | `"{freq}_D{di}{ma_type}#{timeperiod}_BS2辅助V230303` | 利用笔和均线辅助二买二卖 | [详细文档](signals/tas_second_bs_V230303.md) |
| `tas_slope_V231019` | `"{freq}_D{di}DIF{n}斜率T{th}_BS辅助V231019` | DIF 斜率分位多空 | [详细文档](signals/tas_slope_V231019.md) |
