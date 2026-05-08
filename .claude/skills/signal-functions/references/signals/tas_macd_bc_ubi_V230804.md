# tas_macd_bc_ubi_V230804：未完成笔 MACD 背驰观察

> 模块: `tas.rs` | 类别: `kline`

## 参数模板

`"{freq}_MACD背驰_UBI观察V230804`

## 信号逻辑

1. 使用未完成笔（UBI）方向与极值位置；
2. 在最近 6 笔中构造中枢并比较 UBI 末段 DIF 与历史对应笔 DIF；
3. 上行 UBI DIF 走弱判 `空头`，下行 UBI DIF 抬升判 `多头`。

## 信号列表示例

- `Signal('60分钟_MACD背驰_UBI观察V230804_空头_任意_任意_0')`
- `Signal('60分钟_MACD背驰_UBI观察V230804_多头_任意_任意_0')`

## 参数说明

- 无额外参数。

## 对齐说明

UBI 原始K线口径与 Python `tas_macd_bc_ubi_V230804` 一致。
