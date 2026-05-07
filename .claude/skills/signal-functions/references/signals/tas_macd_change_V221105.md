# tas_macd_change_V221105：MACD变色次数信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}K{n}#MACD{fastperiod}#{slowperiod}#{signalperiod}变色次数_BS辅助V221105`

## 信号逻辑

1. 在最近 `n` 根上计算 DIF/DEA 金叉死叉序列；
2. 过滤 `距离<2` 的抖动交叉；
3. 同类型连续交叉按 Python 语义合并；
4. 输出合并后次数 `"{num}次"`。

## 信号列表示例

- `Signal('60分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_0次_任意_任意_0')`
- `Signal('60分钟_D1K55#MACD12#26#9变色次数_BS辅助V221105_3次_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：统计窗口长度，默认 `55`；
- `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
