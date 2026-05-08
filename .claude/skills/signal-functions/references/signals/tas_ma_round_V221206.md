# tas_ma_round_V221206：笔端点触碰均线信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}TH{th}#碰{ma_type}#{timeperiod}_BE辅助V221206`

## 信号逻辑

1. 计算指定均线（`SMA/EMA`）；
2. 取倒数第 `di` 笔，提取其结束分型中间 NewBar 的原始K线；
3. 计算该批原始K线对应均线均值 `last_ma`；
4. 若上笔且 `abs(high-last_ma)/power_price < th/100`，判 `上碰`；
5. 若下笔且 `abs(low-last_ma)/power_price < th/100`，判 `下碰`；否则 `其他`。

## 信号列表示例

- `Signal('60分钟_D1TH10#碰SMA#60_BE辅助V221206_上碰_任意_任意_0')`
- `Signal('60分钟_D1TH10#碰SMA#60_BE辅助V221206_下碰_任意_任意_0')`

## 参数说明

- `di`：指定倒数第 `di` 笔，默认 `1`；
- `th`：端点触碰阈值（百分比），默认 `10`；
- `ma_type`：均线类型，默认 `SMA`；
- `timeperiod`：均线周期，默认 `5`。

## 对齐说明

与 Python 同名函数逻辑与边界条件保持一致。
