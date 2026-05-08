# vol_single_ma_V230214：单成交量均线多空与方向信号

> 模块: `vol.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}VOL#{ma_type}#{timeperiod}_分类V230214`

## 信号逻辑

1. 计算指定成交量均线（`SMA/EMA/WMA`）；
2. `vol_now >= vol_ma_now` 判定 `多头`，否则 `空头`；
3. `vol_ma_now >= vol_ma_prev` 判定 `向上`，否则 `向下`。

## 信号列表示例

- `Signal('60分钟_D1VOL#SMA#5_分类V230214_多头_向上_任意_0')`
- `Signal('60分钟_D1VOL#EMA#12_分类V230214_空头_向下_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `ma_type`：均线类型，默认 `SMA`；
- `timeperiod`：均线周期，默认 `5`。

## 对齐说明

成交量均线缓存与判定口径对齐 Python `vol_single_ma_V230214`。
