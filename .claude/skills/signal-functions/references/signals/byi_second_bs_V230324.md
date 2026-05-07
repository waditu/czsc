# byi_second_bs_V230324：二类买卖点辅助信号

> 模块: `byi.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}回抽零轴_BS2辅助V230324`

## 信号逻辑

1. 基于最近 9 笔关键分型的 DIF 值和标准差构造条件；
2. 满足向下笔回抽零轴条件判 `看多`；
3. 满足向上笔回抽零轴条件判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9回抽零轴_BS2辅助V230324_看多_任意_任意_0')`
- `Signal('60分钟_D1MACD12#26#9回抽零轴_BS2辅助V230324_看空_任意_任意_0')`

## 参数说明

- `di`：从倒数第 `di` 笔开始检查，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD 参数，默认 `12/26/9`。

## 对齐说明

按 Python `byi_second_bs_V230324` 的 DIF 取样点和不等式链实现。
