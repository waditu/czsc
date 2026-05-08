# tas_kdj_evc_V230401：KDJ 极值计数信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}T{th}KDJ{fastk_period}#{slowk_period}#{slowd_period}#{key}值突破{min_count}#{max_count}_BS辅助V230401`

## 信号逻辑

1. 计算 `K/D/J` 指标并提取目标序列；
2. 末端连续低于阈值记多头计数，连续高于阈值记空头计数；
3. 连续次数在 `[min_count, max_count)` 时输出 `多头/空头`。

## 信号列表示例

- `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_BS辅助V230401_多头_任意_任意_0')`
- `Signal('60分钟_D1T10KDJ9#3#3#K值突破5#8_BS辅助V230401_空头_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `key`：`K/D/J`，默认 `K`；
- `th`：极值阈值，默认 `10`；
- `min_count/max_count`：连续计数区间，默认 `5/8`。

## 对齐说明

参数校验与计数边界严格对齐 Python `tas_kdj_evc_V230401`。
