# bar_section_momentum_V221112：区间动量强弱与波动

> 模块: `bar.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}K{n}B_阈值{th}BPV221112`

## 信号逻辑

1. 区间 BP：`(last_close/first_open-1)*10000`；
2. 区间波动：`(max_high/min_low-1)*10000`；
3. `v1`：`上涨/下跌`；`v2`：`强势/弱势`（`|bp|>=th`）；
4. `v3`：`高波动/低波动`（`|wave|/|bp| >= 3`）。

## 信号列表示例

- `Signal('60分钟_D1K10B_阈值100BPV221112_上涨_强势_高波动_0')`
- `Signal('60分钟_D1K10B_阈值100BPV221112_下跌_弱势_低波动_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `n`：窗口长度，默认 `10`；
- `th`：强弱阈值（BP），默认 `100`。

## 对齐说明

三段分类与 Python `bar_section_momentum_V221112` 一致。
