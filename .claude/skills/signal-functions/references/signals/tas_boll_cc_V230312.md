# tas_boll_cc_V230312：布林进出场信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}BOLL{timeperiod}S{nbdev}SP{sp}_BS辅助V230312`

## 信号逻辑

1. 计算 BOLL 中轨与上下轨；
2. 计算 `bias = (close / mid - 1) * 10000`；
3. `close < upper 且 bias < -sp` 判 `看空`，`close > lower 且 bias > sp` 判 `看多`。

## 信号列表示例

- `Signal('60分钟_D1BOLL20S20SP400_BS辅助V230312_看空_任意_任意_0')`
- `Signal('60分钟_D1BOLL20S20SP400_BS辅助V230312_看多_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `timeperiod`：BOLL 周期，默认 `20`；
- `nbdev`：标准差倍数 *10，默认 `20`；
- `sp`：偏离阈值（BP），默认 `400`。

## 对齐说明

与 Python `tas_boll_cc_V230312` 的 bias 判定和阈值方向一致。
