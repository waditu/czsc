# coo_kdj_V230322：均线与 KDJ 配合多空信号

> 模块: `coo.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{ma_type}#{n}_BS辅助V230322`

## 信号逻辑

1. 计算 `KDJ` 与 `MA(n)`；
2. `close > MA` 且 `K < D` 判 `多头`；
3. `close < MA` 且 `K > D` 判 `空头`，否则 `其他`。

## 信号列表示例

- `Signal('60分钟_D1KDJ9#3#3#EMA#3_BS辅助V230322_多头_任意_任意_0')`
- `Signal('60分钟_D1KDJ9#3#3#EMA#3_BS辅助V230322_空头_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：均线周期，默认 `3`；
- `ma_type`：均线类型，默认 `EMA`；
- `fastk_period/slowk_period/slowd_period`：KDJ 参数，默认 `9/3/3`。

## 对齐说明

与 Python `coo_kdj_V230322` 的组合条件一致。
