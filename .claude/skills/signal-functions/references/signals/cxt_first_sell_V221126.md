# cxt_first_sell_V221126：一卖信号

> 模块: `cxt.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}B_SELL1V221126`

## 信号逻辑

1. 依次尝试最近 `21/19/17/15/13/11/9/7/5` 笔；
2. 调用统一的 `check_first_sell` 结构判定函数识别一卖；
3. 命中后输出对应笔数，否则返回 `其他`。

## 信号列表示例

- `Signal('60分钟_D1B_SELL1_一卖_5笔_任意_0')`
- `Signal('60分钟_D1B_SELL1_一卖_13笔_任意_0')`

## 参数说明

- `di`：从倒数第 `di` 笔开始取样，默认 `1`；
- 一卖结构判定复用 Python 同名逻辑。

## 对齐说明

与 Python `czsc.signals.cxt_first_sell_V221126` 保持一致。
