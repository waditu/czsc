# tas_macd_bs1_V230312：MACD 辅助一买一卖（笔结构）

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}_BS1辅助V230312`

## 信号逻辑

1. 最近 7 笔内，末笔创新低并满足三卖结构且末分型 MACD 抬升，判 `看多`；
2. 镜像条件（创新高 + 三买结构 + MACD 走弱）判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9_BS1辅助V230312_看多_任意_任意_0')`
- `Signal('60分钟_D1MACD12#26#9_BS1辅助V230312_看空_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 笔，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。

## 对齐说明

笔结构约束与末分型 MACD 比较逻辑对齐 Python `tas_macd_bs1_V230312`。
