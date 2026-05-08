# tas_cross_status_V230619：0轴上下金死叉次数

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_金死叉V230619`

## 信号逻辑

1. 取近 100 根 DIF/DEA 并截取最近过零后的有效段；
2. 在 0 轴上下分别统计金叉/死叉次数；
3. 若当根形成有效交叉，输出 `0轴上/下金叉(死叉)第N次`。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9_金死叉V230619_0轴下金叉第1次_任意_任意_0')`
- `Signal('60分钟_D1MACD12#26#9_金死叉V230619_0轴上死叉第2次_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。

## 对齐说明

过零截取与交叉计次逻辑对齐 Python `tas_cross_status_V230619`。
