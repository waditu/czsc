# tas_macd_direct_V221106：MACD柱方向信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}方向_BS辅助V221106`

## 信号逻辑

1. 计算 MACD 柱序列；
2. 取倒数 `di` 对齐的最近 3 根柱值；
3. 严格递增判定 `向上`，严格递减判定 `向下`，否则 `模糊`。

## 信号列表示例

- `Signal('60分钟_D1K#MACD12#26#9方向_BS辅助V221106_向上_任意_任意_0')`
- `Signal('60分钟_D1K#MACD12#26#9方向_BS辅助V221106_向下_任意_任意_0')`
- `Signal('60分钟_D1K#MACD12#26#9方向_BS辅助V221106_模糊_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
