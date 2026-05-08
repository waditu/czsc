# tas_macd_power_V221108：MACD强弱分层信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}K#MACD{fastperiod}#{slowperiod}#{signalperiod}强弱_BS辅助V221108`

## 信号逻辑

1. 计算当前 `DIF/DEA`；
2. `dif >= dea >= 0` 判定 `超强`；
3. `dif - dea > 0` 判定 `强势`；
4. `dif <= dea <= 0` 判定 `超弱`；
5. `dif - dea < 0` 判定 `弱势`，其余为 `其他`。

## 信号列表示例

- `Signal('60分钟_D1K#MACD12#26#9强弱_BS辅助V221108_超强_任意_任意_0')`
- `Signal('60分钟_D1K#MACD12#26#9强弱_BS辅助V221108_弱势_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
