# tas_macd_base_V230320：MACD/DIF/DEA 多空与方向信号（含重叠约束）

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}MACD{fastperiod}#{slowperiod}#{signalperiod}MO{max_overlap}#{key}_BS辅助V230320`

## 信号逻辑

1. 计算 `MACD/DIF/DEA` 序列；
2. 取倒数 `di` 截止的最近 `max_overlap+1` 根值；
3. 若 `last > 0` 且前序存在 `< 0` 判 `多头`；
4. 若 `last < 0` 且前序存在 `> 0` 判 `空头`；
5. 否则判 `其他`；方向由 `last >= prev` 判 `向上/向下`。

## 信号列表示例

- `Signal('60分钟_D1MACD12#26#9MO3#MACD_BS辅助V230320_多头_向上_任意_0')`
- `Signal('60分钟_D1MACD12#26#9MO3#DIF_BS辅助V230320_空头_向下_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `key`：指标键，`MACD/DIF/DEA`，默认 `MACD`；
- `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`；
- `max_overlap`：最大重叠窗口，默认 `3`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
