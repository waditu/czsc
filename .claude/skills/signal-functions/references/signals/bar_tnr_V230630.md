# bar_tnr_V230630：TNR 噪音变化判定

> 模块: `bar.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}TNR{timeperiod}K{k}_趋势V230630`

## 信号逻辑

1. 计算 TNR：`|close_t-close_{t-n}| / sum(|diff(close)|)`；
2. 取最近 `k` 根 TNR 均值，与当前 TNR 比较；
3. 当前值大于均值判 `噪音减少`，否则判 `噪音增加`。

## 信号列表示例

- `Signal('15分钟_D1TNR14K3_趋势V230630_噪音减少_任意_任意_0')`
- `Signal('15分钟_D1TNR14K3_趋势V230630_噪音增加_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `timeperiod`：TNR周期，默认 `14`；
- `k`：均值窗口，默认 `3`。

## 对齐说明

TNR与噪音方向定义对齐 Python `bar_tnr_V230630`。
