# tas_rumi_V230704：RUMI 零轴切换信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}F{timeperiod1}S{timeperiod2}R{rumi_window}_BS辅助V230704`

## 信号逻辑

1. 计算 `SMA(timeperiod1)` 与 `WMA(timeperiod2)`，得到 `diff = fast - slow`；
2. 对 `diff` 做 `SMA(rumi_window)` 平滑，得到 `rumi`；
3. `rumi` 上穿 0 轴判 `多头`，下穿 0 轴判 `空头`。

## 信号列表示例

- `Signal('60分钟_D1F3S50R30_BS辅助V230704_多头_任意_任意_0')`
- `Signal('60分钟_D1F3S50R30_BS辅助V230704_空头_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `timeperiod1`：快线均线周期，默认 `3`；
- `timeperiod2`：慢线均线周期，默认 `50`；
- `rumi_window`：RUMI 平滑周期，默认 `30`。

## 对齐说明

快慢线选型与零轴交叉判定对齐 Python `tas_rumi_V230704`。
