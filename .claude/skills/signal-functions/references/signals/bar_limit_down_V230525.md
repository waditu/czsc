# bar_limit_down_V230525：跌停后反包阳线

> 模块: `bar.rs` | 类别: `kline`

## 参数模板

`"{freq}_跌停后无下影线长实体阳线_短线V230525`

## 信号逻辑

1. 仅日线级别；
2. 前一日近似跌停：`low==close<prev_close && close/prev_close<0.95`；
3. 当日无下影长阳：`low==open && close>open && solid>2*upper && close/open>1.07`；
4. 且当日最低低于前日最低，判 `满足`。

## 信号列表示例

- `Signal('日线_跌停后无下影线长实体阳线_短线V230525_满足_任意_任意_0')`
- `Signal('日线_跌停后无下影线长实体阳线_短线V230525_其他_任意_任意_0')`

## 参数说明

- 无额外参数。

## 对齐说明

条件组合与 Python `bar_limit_down_V230525` 保持一致。
