# obv_up_dw_line_V230719：OBV 交叉信号

> 模块: `obv.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}N{n}M{m}MO{max_overlap}_OBV能量V230719`

## 信号逻辑

1. 先计算 OBV 累计量序列；
2. 计算 `obvm = EMA(OBV, n)`，再计算 `sig = EMA(obvm, m)`；
3. 若当前 `obvm > sig` 且 `max_overlap` 根前 `obvm < sig`，判 `看多`；
4. 若当前 `obvm < sig` 且 `max_overlap` 根前 `obvm > sig`，判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1N7M10MO3_OBV能量V230719_看多_任意_任意_0')`
- `Signal('60分钟_D1N7M10MO3_OBV能量V230719_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：OBVM EMA 周期，默认 `7`；
- `m`：信号线 EMA 周期，默认 `10`；
- `max_overlap`：交叉回看根数，默认 `3`。

## 对齐说明

交叉判定时点与 Python `obv_up_dw_line_V230719` 完全一致（使用 `-max_overlap`）。
