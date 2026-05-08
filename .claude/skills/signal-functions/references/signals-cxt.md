# cxt 模块信号索引

> 源码: `crates/czsc-signals/src/cxt.rs`
> 共 41 个信号

| 信号名 | 参数模板 | 说明 | 详细文档 |
|--------|----------|------|----------|
| `cxt_bi_base_V230228` | `"{freq}_D0BL{bi_init_length}_V230228` | 笔基础状态信号 | [详细文档](signals/cxt_bi_base_V230228.md) |
| `cxt_bi_end_V230104` | `"{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230104` | 单均线辅助判断笔结束 | [详细文档](signals/cxt_bi_end_V230104.md) |
| `cxt_bi_end_V230105` | `"{freq}_D0{ma_type}#{timeperiod}T{th}_BE辅助V230105` | K线形态+均线辅助判断笔结束 | [详细文档](signals/cxt_bi_end_V230105.md) |
| `cxt_bi_end_V230222` | `"{freq}_D1MO{max_overlap}_BE辅助V230222` | 未完成笔分型新高新低次数 | [详细文档](signals/cxt_bi_end_V230222.md) |
| `cxt_bi_end_V230224` | `"{freq}_D1_BE辅助V230224` | 量价配合笔结束辅助 | [详细文档](signals/cxt_bi_end_V230224.md) |
| `cxt_bi_end_V230312` | `"{freq}_D0MACD{fastperiod}#{slowperiod}#{signalperiod}_BE辅助V230312` | MACD辅助判断笔结束 | [详细文档](signals/cxt_bi_end_V230312.md) |
| `cxt_bi_end_V230320` | `"{freq}_D0质数窗口MO{max_overlap}_BE辅助V230320` | 质数窗口笔结束辅助 | [详细文档](signals/cxt_bi_end_V230320.md) |
| `cxt_bi_end_V230322` | `"{freq}_D0分型配合{ma_type}#{timeperiod}_BE辅助V230322` | 分型配合均线的笔结束辅助 | [详细文档](signals/cxt_bi_end_V230322.md) |
| `cxt_bi_end_V230324` | `"{freq}_D0{ma_type}#{timeperiod}均线突破_BE辅助V230324` | 笔结束分型均线突破 | [详细文档](signals/cxt_bi_end_V230324.md) |
| `cxt_bi_end_V230618` | `"{freq}_D{di}MO{max_overlap}_BE辅助V230618` | 笔结束小中枢辅助 | [详细文档](signals/cxt_bi_end_V230618.md) |
| `cxt_bi_end_V230815` | `"{freq}_快速突破_BE辅助V230815` | 快速突破反向笔 | [详细文档](signals/cxt_bi_end_V230815.md) |
| `cxt_bi_status_V230101` | `"{freq}_D1_表里关系V230101` | 笔表里关系信号 | [详细文档](signals/cxt_bi_status_V230101.md) |
| `cxt_bi_status_V230102` | `"{freq}_D1_表里关系V230102` | 笔表里关系信号 | [详细文档](signals/cxt_bi_status_V230102.md) |
| `cxt_bi_stop_V230815` | `"{freq}_距离{th}BP_止损V230815` | 笔止损距离状态 | [详细文档](signals/cxt_bi_stop_V230815.md) |
| `cxt_bi_trend_V230824` | `"{freq}_D{di}N{n}TH{th}_形态V230824` | N笔形态判断 | [详细文档](signals/cxt_bi_trend_V230824.md) |
| `cxt_bi_trend_V230913` | `"{freq}_D{di}N{n}笔趋势_高低点辅助判断V230913` | 笔趋势高低点回归信号 | [详细文档](signals/cxt_bi_trend_V230913.md) |
| `cxt_bi_zdf_V230601` | `"{freq}_D{di}N{n}_分层V230601` | BI涨跌幅分层 | [详细文档](signals/cxt_bi_zdf_V230601.md) |
| `cxt_bs_V240526` | `"{freq}_趋势跟随_BS辅助V240526` | 趋势跟随 BS 辅助 | [详细文档](signals/cxt_bs_V240526.md) |
| `cxt_bs_V240527` | `"{freq}_趋势跟随_BS辅助V240527` | 未完成笔上的趋势跟随 BS 辅助 | [详细文档](signals/cxt_bs_V240527.md) |
| `cxt_decision_V240526` | `"{freq}_分型区域N{n}_决策区域V240526` | 分型区域决策 | [详细文档](signals/cxt_decision_V240526.md) |
| `cxt_decision_V240612` | `"{freq}_W{w}N{n}高低点_决策区域V240612` | 高低点N档决策区间 | [详细文档](signals/cxt_decision_V240612.md) |
| `cxt_decision_V240613` | `"{freq}_放量笔N{n}BS2_决策区域V240613` | 放量笔N4BS2决策区 | [详细文档](signals/cxt_decision_V240613.md) |
| `cxt_decision_V240614` | `"{freq}_放量笔N{n}_决策区域V240614` | 放量新高/新低决策区 | [详细文档](signals/cxt_decision_V240614.md) |
| `cxt_double_zs_V230311` | `"{freq}_D{di}双中枢_BS1辅助V230311` | 双中枢 BS1 辅助 | [详细文档](signals/cxt_double_zs_V230311.md) |
| `cxt_eleven_bi_V230622` | `"{freq}_D{di}十一笔_形态V230622` | 十一笔形态分类信号 | [详细文档](signals/cxt_eleven_bi_V230622.md) |
| `cxt_first_buy_V221126` | `"{freq}_D{di}B_BUY1V221126` | 一买信号 | [详细文档](signals/cxt_first_buy_V221126.md) |
| `cxt_first_sell_V221126` | `"{freq}_D{di}B_SELL1V221126` | 一卖信号 | [详细文档](signals/cxt_first_sell_V221126.md) |
| `cxt_five_bi_V230619` | `"{freq}_D{di}五笔_形态V230619` | 五笔形态分类信号 | [详细文档](signals/cxt_five_bi_V230619.md) |
| `cxt_fx_power_V221107` | `"{freq}_D{di}F_分型强弱V221107` | 倒数分型强弱 | [详细文档](signals/cxt_fx_power_V221107.md) |
| `cxt_nine_bi_V230621` | `"{freq}_D{di}九笔_形态V230621` | 九笔形态分类信号 | [详细文档](signals/cxt_nine_bi_V230621.md) |
| `cxt_overlap_V240526` | `"{freq}_顶底重合_支撑压力V240526` | 收盘价与最近分型区间重合次数 | [详细文档](signals/cxt_overlap_V240526.md) |
| `cxt_overlap_V240612` | `"{freq}_SNR顺畅N{n}_支撑压力V240612` | 顺畅笔分型支撑压力信号 | [详细文档](signals/cxt_overlap_V240612.md) |
| `cxt_range_oscillation_V230620` | `"{freq}_D{di}TH{th}_区间震荡V230620` | 区间震荡笔数统计 | [详细文档](signals/cxt_range_oscillation_V230620.md) |
| `cxt_second_bs_V230320` | `"{freq}_D{di}#{ma_type}#{timeperiod}_BS2辅助V230320` | 均线辅助识别第二类买卖点 | [详细文档](signals/cxt_second_bs_V230320.md) |
| `cxt_second_bs_V240524` | `"{freq}_D{di}W{w}T{t}_第二买卖点V240524` | 第二买卖点重叠计数信号 | [详细文档](signals/cxt_second_bs_V240524.md) |
| `cxt_seven_bi_V230620` | `"{freq}_D{di}七笔_形态V230620` | 七笔形态分类信号 | [详细文档](signals/cxt_seven_bi_V230620.md) |
| `cxt_third_bs_V230318` | `"{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230318` | 均线辅助识别第三类买卖点 | [详细文档](signals/cxt_third_bs_V230318.md) |
| `cxt_third_bs_V230319` | `"{freq}_D{di}#{ma_type}#{timeperiod}_BS3辅助V230319` | 带均线形态的第三类买卖点辅助 | [详细文档](signals/cxt_third_bs_V230319.md) |
| `cxt_third_buy_V230228` | `"{freq}_D{di}_三买辅助V230228` | 笔三买辅助 | [详细文档](signals/cxt_third_buy_V230228.md) |
| `cxt_three_bi_V230618` | `"{freq}_D{di}三笔_形态V230618` | 三笔形态分类信号 | [详细文档](signals/cxt_three_bi_V230618.md) |
| `cxt_ubi_end_V230816` | `"{freq}_UBI_BE辅助V230816` | UBI 新高新低次数信号 | [详细文档](signals/cxt_ubi_end_V230816.md) |
