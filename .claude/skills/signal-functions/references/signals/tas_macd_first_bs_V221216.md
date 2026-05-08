# tas_macd_first_bs_V221216：MACD 第一买卖点（扩展版）

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V221216`

## 信号逻辑

1. 以最近 10 根与前 90 根做高低点对比（新高/新低）；
2. 结合最近交叉类型、零轴位置与 MACD 方向判断 `一买/一卖`；
3. `v2` 输出最后一次交叉类型（`金叉/死叉`）。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9_BS1辅助V221216_一买_死叉_任意_0')`
- `Signal('60分钟_D1MACD12#26#9_BS1辅助V221216_一卖_金叉_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。

## 对齐说明

分支条件、`or` 组合与 `v2` 输出语义对齐 Python `tas_macd_first_bs_V221216`。
