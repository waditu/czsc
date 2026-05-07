"""
公开 API ``format_standard_kline`` 的 Python 包装实现

功能定位：
    将标准列布局的 K 线 DataFrame 逐行转换为 ``list[RawBar]``，签名与
    rs-czsc 提供的 ``format_standard_kline(df, freq) -> list[RawBar]``
    完全对齐，是 Python 端调用 Rust 缠论分析的"输入预处理"环节。

实现取舍：
    - 不走 Rust 端的 pyarrow 字节流捷径（``format_standard_kline_bytes``），
      原因是 pyarrow 桥接代码尚未迁移到 czsc-python，引入会扩大依赖面
    - 直接遍历 DataFrame 并按行调用 PyO3 暴露的 ``RawBar`` 构造器，
      在 1 万根 K 线规模的测试输入下耗时可忽略（< 100 ms）
    - 若未来出现热路径性能问题，可再考虑把 ``format_standard_kline_bytes``
      迁移过来，本函数保持调用接口不变即可
"""

from __future__ import annotations

import pandas as pd

from czsc._native import Freq, RawBar

# 仅暴露公开函数，避免 ``from ... import *`` 时把 _FREQ_MAP 等内部对象带出去
__all__ = ["format_standard_kline"]


# 中文周期名 -> Rust Freq 枚举的查表映射
# 注意事项：
#   1. 必须与 rs-czsc 的 ``python/rs_czsc/_utils/utils.py::format_standard_kline``
#      保持完全同步，否则会导致同名周期在两端解析为不同枚举值
#   2. 大型周期（季线/年线）使用频率较低但仍需登记，避免使用方手写枚举
#   3. 未登记的字符串会在下方触发 KeyError，便于及时发现拼写错误
_FREQ_MAP: dict[str, Freq] = {
    "逐笔": Freq.Tick,
    "1分钟": Freq.F1,
    "2分钟": Freq.F2,
    "3分钟": Freq.F3,
    "4分钟": Freq.F4,
    "5分钟": Freq.F5,
    "6分钟": Freq.F6,
    "10分钟": Freq.F10,
    "12分钟": Freq.F12,
    "15分钟": Freq.F15,
    "20分钟": Freq.F20,
    "30分钟": Freq.F30,
    "60分钟": Freq.F60,
    "120分钟": Freq.F120,
    "日线": Freq.D,
    "周线": Freq.W,
    "月线": Freq.M,
    "季线": Freq.S,
    "年线": Freq.Y,
}


def format_standard_kline(df: pd.DataFrame, freq: Freq | str = Freq.F5) -> list[RawBar]:
    """
    将标准 K 线 DataFrame 转换为 RawBar 对象列表

    参数:
        df:  标准 K 线布局，必须包含以下八列（缺一即报错）：
             ``dt``     - 时间戳（``datetime64[ns]`` 或可被 ``pd.to_datetime`` 解析）
             ``symbol`` - 标的代码（任意可被 ``str()`` 表示的对象）
             ``open``   - 开盘价
             ``close``  - 收盘价
             ``high``   - 最高价
             ``low``    - 最低价
             ``vol``    - 成交量
             ``amount`` - 成交额
        freq: Rust ``Freq`` 枚举值，或中文周期字符串（如 ``"30分钟"``）。
              传字符串时会经 ``_FREQ_MAP`` 解析为枚举；未登记的字符串将抛 KeyError。
              默认值 ``Freq.F5`` 仅作占位，生产环境务必显式传入正确周期。

    返回:
        与输入 DataFrame 行序一致的 RawBar 列表

    异常:
        ValueError: DataFrame 缺少必需列
        KeyError:   freq 是字符串但未登记于 ``_FREQ_MAP``

    备注:
        - 函数对入参 df 不做原地修改：仅在 dt 列类型不匹配时才会做一次浅拷贝
        - 价格 / 成交量 / 成交额一律强制 ``float`` 化，与 RawBar 构造器签名匹配，
          避免 numpy 类型在 PyO3 边界产生隐式转换告警
    """
    # 字符串 freq 走查表；未登记的字符串会立即触发 KeyError，便于尽早暴露拼写错误
    if isinstance(freq, str):
        freq = _FREQ_MAP[freq]

    # 严格列校验：八个字段缺一即拒绝处理，避免后续 itertuples 报出难懂的 AttributeError
    required = ("dt", "symbol", "open", "close", "high", "low", "vol", "amount")
    for col in required:
        if col not in df.columns:
            raise ValueError(f"format_standard_kline: missing column {col!r}")

    # 仅在 dt 列类型不匹配时做一次浅拷贝并转换，避免污染调用方的原始 DataFrame
    if df["dt"].dtype != "datetime64[ns]":
        df = df.copy()
        df["dt"] = pd.to_datetime(df["dt"])

    # 使用 itertuples(index=False) 而非 iterrows，可显著减少每行的属性访问开销
    # （itertuples 返回 namedtuple，字段访问是 C 层实现）
    bars: list[RawBar] = []
    for row in df[list(required)].itertuples(index=False):
        bars.append(
            RawBar(
                symbol=str(row.symbol),
                dt=row.dt,
                freq=freq,
                open=float(row.open),
                close=float(row.close),
                high=float(row.high),
                low=float(row.low),
                vol=float(row.vol),
                amount=float(row.amount),
            )
        )
    return bars
