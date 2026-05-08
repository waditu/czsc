# bar_zdf_V221203：单根涨跌幅区间信号

> 模块: `bar.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}{mode}_{t1}至{t2}`

## 信号逻辑

1. 读取倒数第 `di` 根及其前一根K线；
2. `mode=ZF` 使用涨幅 `close/prev_close-1`，`mode=DF` 使用跌幅 `1-close/prev_close`；
3. 换算为 BP 后在 `[t1, t2]` 判 `满足`，否则 `其他`。

## 信号列表示例

- `Signal('日线_D1ZF_300至600_满足_任意_任意_0')`
- `Signal('日线_D1DF_300至600_其他_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `mode`：`ZF` 或 `DF`，默认 `ZF`；
- `span`：区间下上界（`t1,t2`），默认 `300,600`。

## 对齐说明

BP 计算与 Python `bar_zdf_V221203` 保持一致。
