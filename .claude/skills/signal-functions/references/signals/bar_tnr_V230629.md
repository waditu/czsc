# bar_tnr_V230629：TNR 分层信号

> 模块: `bar.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}TNR{timeperiod}_趋势V230629`

## 信号逻辑

1. 计算每根K线 TNR 值；
2. 取最近100个 TNR 做 `qcut(10)`；
3. 输出末根所在层：`第{n}层`。

## 信号列表示例

- `Signal('15分钟_D1TNR14_趋势V230629_第7层_任意_任意_0')`
- `Signal('15分钟_D1TNR14_趋势V230629_第2层_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `timeperiod`：TNR周期，默认 `14`。

## 对齐说明

分层逻辑与 `duplicates='drop'` 行为对齐 Python `bar_tnr_V230629`。
