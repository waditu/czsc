# tas_cci_base_V230402：CCI 极值连续计数信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}CCI{timeperiod}#{min_count}#{max_count}_BS辅助V230402`

## 信号逻辑

1. 计算 CCI 序列；
2. 若末尾连续 `CCI > 100` 次数落在 `[min_count, max_count)`，判 `多头`；
3. 若末尾连续 `CCI < -100` 次数落在 `[min_count, max_count)`，判 `空头`。

## 信号列表示例

- `Signal('60分钟_D1CCI14#3#6_BS辅助V230402_多头_任意_任意_0')`
- `Signal('60分钟_D1CCI14#3#6_BS辅助V230402_空头_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `timeperiod`：CCI 周期，默认 `14`；
- `min_count`：最小连续次数，默认 `3`；
- `max_count`：最大连续次数上界（开区间），默认 `min_count + 3`。

## 对齐说明

连续计数和覆盖顺序与 Python `tas_cci_base_V230402` 一致。
