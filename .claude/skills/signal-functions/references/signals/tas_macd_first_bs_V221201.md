# tas_macd_first_bs_V221201：MACD一买一卖辅助信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221201`

## 信号逻辑

1. 在近 300 根内统计 DIF/DEA 金叉死叉序列；
2. 满足特定零轴位置与节奏条件时，给出 `一买` 或 `一卖`；
3. 否则返回 `其他`。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9_BS1辅助V221201_一买_任意_任意_0')`
- `Signal('60分钟_D1MACD12#26#9_BS1辅助V221201_一卖_任意_任意_0')`
- `Signal('60分钟_D1MACD12#26#9_BS1辅助V221201_其他_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
