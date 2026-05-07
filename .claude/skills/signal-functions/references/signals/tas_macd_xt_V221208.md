# tas_macd_xt_V221208：MACD 柱形态信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}形态_BS辅助V221208`

## 信号逻辑

1. 读取最近 5 根 MACD 柱；
2. 按柱子相对大小关系判定 `逼空棒/杀多棒/绿抽脚/红缩头`；
3. 按跨零关系判定 `空翻多/多翻空`。

## 信号列表示例

- `Signal('60分钟_D1K#MACD12#26#9形态_BS辅助V221208_逼空棒_任意_任意_0')`
- `Signal('60分钟_D1K#MACD12#26#9形态_BS辅助V221208_多翻空_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。

## 对齐说明

形态分支顺序与 Python `tas_macd_xt_V221208` 保持一致。
