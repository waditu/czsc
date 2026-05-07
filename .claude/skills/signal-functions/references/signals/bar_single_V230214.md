# bar_single_V230214：单K状态信号

> 模块: `bar.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}T{t}_状态V230214`

## 信号逻辑

1. 倒数第 `di` 根K线，按 `close/open` 判 `阳线/阴线`；
2. 若 `solid > (upper+lower)*t/10` 判 `长实体`；
3. 若 `upper > (solid+lower)*t/10` 判 `长上影`；
4. 若 `lower > (solid+upper)*t/10` 判 `长下影`，否则 `其他`。

## 信号列表示例

- `Signal('日线_D1T10_状态V230214_阳线_长实体_任意_0')`
- `Signal('日线_D1T10_状态V230214_阴线_长上影_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `t`：长实体/长影阈值（/10），默认 `10`。

## 对齐说明

分类阈值与 Python `bar_single_V230214` 保持一致。
