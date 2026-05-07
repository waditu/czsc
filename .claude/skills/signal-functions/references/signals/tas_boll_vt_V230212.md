# tas_boll_vt_V230212：BOLL 通道突破进出场信号

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_D{di}BOLL{timeperiod}S{nbdev}MO{max_overlap}_BS辅助V230212`

## 信号逻辑

1. 计算指定参数的 BOLL 上下轨（`nbdev / 10` 为标准差倍数）；
2. 最新收盘价在上轨上方，且窗口内曾有收盘价在上轨下方，判 `看多`；
3. 最新收盘价在下轨下方，且窗口内曾有收盘价在下轨上方，判 `看空`。

## 信号列表示例

- `Signal('60分钟_D1BOLL20S20MO5_BS辅助V230212_看多_任意_任意_0')`
- `Signal('60分钟_D1BOLL20S20MO5_BS辅助V230212_看空_任意_任意_0')`

## 参数说明

- `di`：倒数第 `di` 根K线，默认 `1`；
- `timeperiod`：BOLL 周期，默认 `20`；
- `nbdev`：标准差倍数 *10，默认 `20`；
- `max_overlap`：窗口重叠长度，默认 `5`。

## 对齐说明

严格按 Python `tas_boll_vt_V230212` 判定分支实现。
