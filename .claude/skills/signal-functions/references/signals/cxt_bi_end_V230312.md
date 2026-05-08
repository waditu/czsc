# cxt_bi_end_V230312：MACD辅助判断笔结束

> 模块: `cxt.rs` | 类别: `kline`

## 参数模板

`"{freq}_D0MACD{fastperiod}#{slowperiod}#{signalperiod}_BE辅助V230312`

## 信号逻辑

1. 计算指定参数的 MACD，并读取最后一笔终点分型对应的首末原始 K 线；
2. 向下笔若分型尾部 MACD 柱值高于分型起点，判定 `看多`；向上笔反向判定 `看空`；
3. MACD 缓存、分型样本或边界条件不满足时返回 `其他`。

## 信号列表示例

- `Signal('60分钟_D0MACD12#26#9_BE辅助V230312_看多_任意_任意_0')`
- `Signal('60分钟_D0MACD12#26#9_BE辅助V230312_看空_任意_任意_0')`

## 参数说明

- `fastperiod`：MACD 快线周期，默认 `12`；
- `slowperiod`：MACD 慢线周期，默认 `26`；
- `signalperiod`：信号线周期，默认 `9`。

## 对齐说明

与 Python `czsc.signals.cxt_bi_end_V230312` 保持一致。
