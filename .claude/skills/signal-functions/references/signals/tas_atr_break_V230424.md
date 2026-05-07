# tas_atr_break_V230424：ATR 通道突破

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}ATR{timeperiod}T{th}突破_BS辅助V230424`

## 信号逻辑

1. 取窗口 `HH/LL` 和当前 ATR；
2. 若 `close` 落在 `HH-th*ATR` 与 `LL+th*ATR` 之间，输出 `其他`；
3. 向上突破输出 `看多`，向下突破输出 `看空`。

## 信号列表示例

- `Signal('60分钟_D1ATR5T30突破_BS辅助V230424_看多_任意_任意_0')`
- `Signal('60分钟_D1ATR5T30突破_BS辅助V230424_看空_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `timeperiod`：ATR 周期，默认 `5`；
- `th`：ATR 倍数（除以10），默认 `30`。

## 对齐说明

区间内返回 `其他` 的优先级与 Python `tas_atr_break_V230424` 一致。
