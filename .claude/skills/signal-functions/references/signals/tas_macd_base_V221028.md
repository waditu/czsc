# tas_macd_base_V221028：MACD/DIF/DEA 多空与方向信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}#{key}_BS辅助V221028`

## 信号逻辑

1. 计算 MACD 三序列；
2. 依据 `key` 选择 `MACD/DIF/DEA`；
3. 当前值 `>=0` 判定 `多头`，否则 `空头`；
4. 当前值 `>=` 前值判定 `向上`，否则 `向下`。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9#MACD_BS辅助V221028_多头_向上_任意_0')`
- `Signal('60分钟_D1MACD12#26#9#DIF_BS辅助V221028_空头_向下_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`；
- `key`：`MACD`、`DIF` 或 `DEA`，默认 `MACD`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
