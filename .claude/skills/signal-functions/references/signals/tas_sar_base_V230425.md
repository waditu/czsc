# tas_sar_base_V230425：SAR 基础多空信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MO{max_overlap}SAR_BS辅助V230425`

## 信号逻辑

1. 计算 SAR 序列；
2. 若当前 `close > sar` 且窗口内存在任意 `close < sar`，判定 `看多`；
3. 若当前 `close < sar` 且窗口内存在任意 `close > sar`，判定 `看空`；
4. 否则返回 `其他`。

## 信号列表示例

- `Signal('60分钟_D1MO5SAR_BS辅助V230425_看多_任意_任意_0')`
- `Signal('60分钟_D1MO5SAR_BS辅助V230425_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `max_overlap`：重叠窗口，默认 `5`。

## 对齐说明

突破与重叠窗口判定逻辑对齐 Python `tas_sar_base_V230425`。
