# cvolp_up_dw_line_V230612：CVOLP 动量变化率信号

> 模块: `cvolp.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}N{n}M{m}UP{up}DW{dw}_CVOLP动量变化率V230612`

## 信号逻辑

1. 取最近 `n+m` 根成交量，构造长度为 `n` 的指数权重；
2. 计算卷积平滑序列 `emap`，并将前 `n` 项置为 `emap[n]`；
3. 计算 `sroc = (emap - roll(emap, m))[-1] / roll(emap, m)[-1]`；
4. `sroc > up/100` 判 `看多`，`sroc < -dw/100` 判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1N34M55UP5DW5_CVOLP动量变化率V230612_看多_任意_任意_0')`
- `Signal('60分钟_D1N34M55UP5DW5_CVOLP动量变化率V230612_看空_任意_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `n`：卷积平滑窗口，默认 `34`；
- `m`：滚动比较窗口，默认 `55`；
- `up`：看多阈值（百分比整数），默认 `5`；
- `dw`：看空阈值（百分比整数），默认 `5`。

## 对齐说明

卷积平滑与 `roll` 口径对齐 Python `cvolp_up_dw_line_V230612`。
