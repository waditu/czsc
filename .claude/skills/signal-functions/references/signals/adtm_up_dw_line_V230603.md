# adtm_up_dw_line_V230603：ADTM 能量异动多空信号

> 模块: `ang.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}N{n}M{m}TH{th}_ADTMV230603`

## 信号逻辑

1. 计算 `N` 窗口 `up_sum` 与 `M` 窗口 `dw_sum`；
2. 计算 `adtm = (up_sum - dw_sum) / max(up_sum, dw_sum)`；
3. `up_sum > dw_sum` 或 `adtm > th/10` 判 `看多`；
4. `up_sum < dw_sum` 或 `adtm < th/10` 判 `看空`，否则 `其他`。

## 信号列表示例

- `Signal('60分钟_D1N30M20TH5_ADTMV230603_看多_任意_任意_0')`
- `Signal('60分钟_D1N30M20TH5_ADTMV230603_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：`up_sum` 窗口，默认 `30`；
- `m`：`dw_sum` 窗口，默认 `20`；
- `th`：阈值（除以 10 使用），默认 `5`。

## 对齐说明

与 Python `adtm_up_dw_line_V230603` 的条件优先级与阈值口径一致。
