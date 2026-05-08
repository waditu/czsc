# tas_macd_bs1_V230313：MACD 红绿柱第一买卖点

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230313`

## 信号逻辑

1. 近 10 与前 90 根对比新高新低；
2. 用交叉面积递减/递增与 MACD 方向判 `一买/一卖`；
3. `v2` 返回最后交叉类型。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9_BS1辅助V230313_一买_死叉_任意_0')`
- `Signal('60分钟_D1MACD12#26#9_BS1辅助V230313_一卖_金叉_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。

## 对齐说明

面积比较与条件优先级（`and/or`）按 Python `tas_macd_bs1_V230313` 对齐。
