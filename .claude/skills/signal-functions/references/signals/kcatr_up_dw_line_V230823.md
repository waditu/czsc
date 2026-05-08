# kcatr_up_dw_line_V230823：ATR 通道突破多空

> 模块: `kcatr.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}N{n}M{m}T{th}_KCATR多空V230823`

## 信号逻辑

1. 在最近 `n` 根上计算平均真实波幅 `ATR`；
2. 在最近 `m` 根上计算收盘均值 `middle`；
3. 最新收盘价大于 `middle + ATR * th` 判 `看多`；
4. 最新收盘价小于 `middle - ATR * th` 判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1N30M16T2_KCATR多空V230823_看多_任意_任意_0')`
- `Signal('60分钟_D1N30M16T2_KCATR多空V230823_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：ATR 计算窗口，默认 `30`；
- `m`：中轨均值窗口，默认 `16`；
- `th`：ATR 倍数阈值，默认 `2`。

## 对齐说明

ATR 取样与突破阈值口径对齐 Python `kcatr_up_dw_line_V230823`。
