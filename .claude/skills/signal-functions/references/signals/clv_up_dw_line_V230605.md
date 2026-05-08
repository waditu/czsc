# clv_up_dw_line_V230605：CLV 多空信号

> 模块: `clv.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}N{n}_CLV多空V230605`

## 信号逻辑

1. 取最近 `n` 根K线，计算每根 `(2*close-low-high)/(high-low)`；
2. 计算该序列均值 `clv_ma`；
3. `clv_ma > 0` 判 `看多`，否则判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1N70_CLV多空V230605_看多_任意_任意_0')`
- `Signal('60分钟_D1N70_CLV多空V230605_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：统计窗口大小，默认 `70`。

## 对齐说明

CLV 公式与阈值判断对齐 Python `clv_up_dw_line_V230605`。
