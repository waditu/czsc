# tas_ma_base_V230313：单均线开平仓辅助信号（带重叠约束）

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}#{ma_type}#{timeperiod}MO{max_overlap}_BS辅助V230313`

## 信号逻辑

1. 计算指定均线（`SMA/EMA`）；
2. 取倒数 `di` 截止的 `max_overlap+1` 根K线；
3. 若最新 `close >= ma` 且窗口内并非全部 `close > ma`，判 `看多`；
4. 若最新 `close < ma` 且窗口内并非全部 `close < ma`，判 `看空`；
5. 否则判 `其他`；并用 `ma_now >= ma_prev` 判方向 `向上/向下`。

## 信号列表示例

- `Signal('60分钟_D1#SMA#5MO5_BS辅助V230313_看多_向上_任意_0')`
- `Signal('60分钟_D1#EMA#12MO5_BS辅助V230313_看空_向下_任意_0')`
- `Signal('60分钟_D1#SMA#5MO5_BS辅助V230313_其他_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `ma_type`：均线类型，默认 `SMA`；
- `timeperiod`：均线周期，默认 `5`；
- `max_overlap`：相同方向最大重叠窗口，默认 `5`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
