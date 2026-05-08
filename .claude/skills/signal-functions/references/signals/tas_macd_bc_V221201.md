# tas_macd_bc_V221201：MACD背驰辅助信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}N{n}M{m}#MACD{fastperiod}#{slowperiod}#{signalperiod}_BCV221201`

## 信号逻辑

1. 取最近 `m+n` 根K线，前 `m` 为对照窗口，后 `n` 为近端窗口；
2. 若近端价格创新低且MACD低点抬高，判 `底部` 背驰；
3. 若近端价格创新高且MACD高点走低，判 `顶部` 背驰；
4. 并给出当前柱体颜色 `红柱/绿柱`。

## 信号列表示例

- `Signal('60分钟_D1N3M50#MACD12#26#9_BCV221201_底部_绿柱_任意_0')`
- `Signal('60分钟_D1N3M50#MACD12#26#9_BCV221201_顶部_红柱_任意_0')`
- `Signal('60分钟_D1N3M50#MACD12#26#9_BCV221201_其他_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `n/m`：近端窗口与对照窗口长度，默认 `3/50`；
- `fastperiod/slowperiod/signalperiod`：MACD参数，默认 `12/26/9`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
