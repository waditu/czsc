# demakder_up_dw_line_V230605：DEMAKER 价格趋势信号

> 模块: `ang.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}N{n}TH{th}TL{tl}_DEMAKER价格趋势V230605`

## 信号逻辑

1. 统计窗口内上涨高点均值 `demax` 与下跌低点均值 `demin`；
2. 计算 `demaker = demax / (demax + demin)`；
3. `demaker > th/10` 判 `看多`，`demaker < tl/10` 判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1N105TH5TL5_DEMAKER价格趋势V230605_看多_任意_任意_0')`
- `Signal('60分钟_D1N105TH5TL5_DEMAKER价格趋势V230605_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：统计窗口，默认 `105`；
- `th/tl`：上下阈值（除以 10 使用），默认 `5/5`。

## 对齐说明

保持 Python `demakder_up_dw_line_V230605` 对空样本返回 NaN 的行为。
