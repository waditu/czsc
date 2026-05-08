# tas_kdj_evc_V221201：KDJ 极值计数信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{c1}#{c2}_KDJ极值V221201`

## 信号逻辑

1. 计算 `K/D/J` 序列并提取 `key`；
2. 统计末端连续低于 `th` 或高于 `100-th` 的次数；
3. 连续次数落入 `[c1, c2)` 时分别输出 `多头/空头`，并在 `v2` 标注计数。

## 信号列表示例

- `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_多头_C5_任意_0')`
- `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_KDJ极值V221201_空头_C6_任意_0')`

## 参数说明

- `di`：信号计算截止在倒数第 `di` 根K线，默认 `1`；
- `key`：取值 `K/D/J`，默认 `K`；
- `th`：极值阈值，默认 `10`；
- `count_range`：连续计数区间，默认 `[5, 8]`。

## 对齐说明

连续计数、`v2=Cx` 标注方式与 Python `tas_kdj_evc_V221201` 保持一致。
