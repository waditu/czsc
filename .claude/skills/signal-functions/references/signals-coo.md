# coo 模块信号索引

> 源码: `crates/czsc-signals/src/coo.rs`
> 共 5 个信号

| 信号名 | 参数模板 | 说明 | 详细文档 |
|--------|----------|------|----------|
| `coo_cci_V230323` | `"{freq}_D{di}CCI{n}#{ma_type}#{m}_BS辅助V230323` | CCI 结合均线的多空与方向信号 | [详细文档](signals/coo_cci_V230323.md) |
| `coo_kdj_V230322` | `"{freq}_D{di}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{ma_type}#{n}_BS辅助V230322` | 均线与 KDJ 配合多空信号 | [详细文档](signals/coo_kdj_V230322.md) |
| `coo_sar_V230325` | `"{freq}_D{di}N{n}SAR_BS辅助V230325` | SAR 与区间极值配合信号 | [详细文档](signals/coo_sar_V230325.md) |
| `coo_td_V221110` | `"{freq}_D{di}K_TD` | TD 神奇九转信号（旧版模板） | [详细文档](signals/coo_td_V221110.md) |
| `coo_td_V221111` | `"{freq}_D{di}TD_BS辅助V221111` | TD 神奇九转信号 | [详细文档](signals/coo_td_V221111.md) |
