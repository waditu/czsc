# tas_double_ma_V221203：双均线多空强弱信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}T{th}#{ma_type}#{timeperiod1}#{timeperiod2}_JX辅助V221203`

## 信号逻辑

1. 计算两条均线 `ma1/ma2`；
2. `ma1 >= ma2` 判定 `多头`，否则 `空头`；
3. 两线相对距离（BP）超过 `th` 判 `强势`，否则 `弱势`。

## 信号列表示例

- `Signal('60分钟_D1T100#SMA#5#10_JX辅助V221203_多头_强势_任意_0')`
- `Signal('60分钟_D1T80#EMA#12#26_JX辅助V221203_空头_弱势_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `th`：强弱阈值（BP），默认 `100`；
- `ma_type`：均线类型，默认 `SMA`；
- `timeperiod1/timeperiod2`：两条均线周期，默认 `5/10`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
