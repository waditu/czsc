# tas_rsi_base_V230227：RSI超买超卖与方向信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}T{th}RSI{timeperiod}_RSI辅助V230227`

## 信号逻辑

1. 使用 `n` 计算 RSI（与 Python 保持一致）；
2. `rsi <= th` 判 `超卖`，`rsi >= 100-th` 判 `超买`，否则 `其他`；
3. `rsi_now >= rsi_prev` 判 `向上`，否则 `向下`。

## 信号列表示例

- `Signal('60分钟_D1T20RSI6_RSI辅助V230227_超卖_向上_任意_0')`
- `Signal('60分钟_D1T20RSI6_RSI辅助V230227_超买_向下_任意_0')`
- `Signal('60分钟_D1T20RSI6_RSI辅助V230227_其他_向上_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `n`：RSI 实际计算周期，默认 `6`；
- `timeperiod`：仅用于信号键展示，默认 `6`；
- `th`：超买超卖阈值，默认 `20`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
