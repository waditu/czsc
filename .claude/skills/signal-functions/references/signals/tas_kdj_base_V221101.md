# tas_kdj_base_V221101：KDJ基础辅助信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}K#KDJ{fastk_period}#{slowk_period}#{slowd_period}_KDJ辅助V221101`

## 信号逻辑

1. 计算 K、D、J 三序列；
2. `J > K > D` 判定 `多头`，`J < K < D` 判定 `空头`，否则 `其他`；
3. `J_now >= J_prev` 判定 `向上`，否则 `向下`。

## 信号列表示例

- `Signal('60分钟_D1K#KDJ9#3#3_KDJ辅助V221101_多头_向上_任意_0')`
- `Signal('60分钟_D1K#KDJ9#3#3_KDJ辅助V221101_空头_向下_任意_0')`
- `Signal('60分钟_D1K#KDJ9#3#3_KDJ辅助V221101_其他_向下_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastk_period/slowk_period/slowd_period`：KDJ参数，默认 `9/3/3`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
