# tas_hlma_V230301：HMA/LMA 多空信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}#{ma_type}#{timeperiod}HLMA_BS辅助V230301`

## 信号逻辑

1. 取最近 `timeperiod` 根K线，计算 `hma=high均值`、`lma=low均值`；
2. 若 `close_now > hma` 且 `close_prev <= ma_prev`，判 `看多`；
3. 若 `close_now < lma` 且 `close_prev >= ma_prev`，判 `看空`；
4. 否则判 `其他`。

## 信号列表示例

- `Signal('60分钟_D1#SMA#3HLMA_BS辅助V230301_看多_任意_任意_0')`
- `Signal('60分钟_D1#SMA#3HLMA_BS辅助V230301_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `ma_type`：均线类型，默认 `SMA`；
- `timeperiod`：窗口周期，默认 `3`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
