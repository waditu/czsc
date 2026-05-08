# tas_macd_second_bs_V221201：MACD 第二买卖点

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS2辅助V221201`

## 信号逻辑

1. 在近 350 根（去掉最早 50 根）统计交叉序列；
2. 结合最近交叉距今、零轴位置与 MACD 方向判 `二买/二卖`；
3. `v2` 返回最后交叉类型。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9_BS2辅助V221201_二买_死叉_任意_0')`
- `Signal('60分钟_D1MACD12#26#9_BS2辅助V221201_二卖_金叉_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。

## 对齐说明

`距今` 条件与零轴判定对齐 Python `tas_macd_second_bs_V221201`。
