# tas_atr_V230630：ATR 波动分层信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}ATR{timeperiod}_波动V230630`

## 信号逻辑

1. 计算 `ATR / close` 波动率；
2. 对最近 100 根波动率做 `qcut(10)` 分层；
3. 输出末值所在层级 `第{n}层`。

## 信号列表示例

- `Signal('60分钟_D1ATR14_波动V230630_第3层_任意_任意_0')`
- `Signal('60分钟_D1ATR14_波动V230630_第9层_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `timeperiod`：ATR 周期，默认 `14`。

## 对齐说明

ATR 预热与分层边界对齐 Python `tas_atr_V230630`。
