"""
czsc.mock —— 转发到 wbt.mock 的薄壳封装

历史背景:
    早期 czsc.mock 自行维护了约 540 行的随机 K 线/因子/组合/相关性等
    模拟数据生成实现。迁移期决定不再维持该并行实现，而是统一收敛到
    外部 wbt 包，避免两边算法漂移导致测试输出不一致。

当前职责:
    仅保留两个公开入口，转发到 wbt.mock 同名实现：
        - ``generate_symbol_kines``     —— 单标的多周期 K 线
        - ``generate_klines_with_weights`` —— 带权重列的 K 线（用于回测打样）

迁移影响:
    依赖旧 ``generate_klines`` / ``generate_cs_factor`` 等已删除函数的
    业务方需迁移到 wbt 或自己的业务模块，本模块不再提供兜底实现。
    与之相关的测试用例（test_mock_quality.py、test_eda.py 中相应切片）
    也已在裁剪阶段一并删除。
"""

from __future__ import annotations

import pandas as pd

# 内部使用的别名（带下划线前缀），避免被 ``from czsc.mock import *`` 误带出去
from wbt.mock import mock_symbol_kline as _mock_symbol_kline
from wbt.mock import mock_weights as _mock_weights

# 公开 API 契约：仅暴露这两个函数；其余符号一律视为内部细节
__all__ = ["generate_symbol_kines", "generate_klines_with_weights"]


def generate_symbol_kines(
    symbol: str,
    freq: str,
    sdt: str = "20100101",
    edt: str = "20250101",
    seed: int = 42,
) -> pd.DataFrame:
    """
    生成单标的、单周期的随机 K 线 DataFrame（转发到 wbt 实现）

    参数:
        symbol: 标的代码（任意字符串，会被原样写入 ``symbol`` 列）
        freq:   周期字符串（如 ``"30分钟"`` / ``"日线"``），需被 wbt 识别
        sdt:    起始日期，格式 ``YYYYMMDD``，默认 2010-01-01
        edt:    结束日期，格式 ``YYYYMMDD``，默认 2025-01-01
        seed:   随机种子；同 (symbol, freq, sdt, edt, seed) 五元组保证结果可复现

    返回:
        与 rs-czsc 的标准 K 线 schema 一致的 DataFrame，列包括:
            ``dt / symbol / open / close / high / low / vol / amount``

    用途:
        - 单元测试中替代真实行情，避免对外部数据源的网络依赖
        - 演示/教程脚本中作为最小可运行示例的数据来源
    """
    return _mock_symbol_kline(symbol, freq, sdt=sdt, edt=edt, seed=seed)


def generate_klines_with_weights(seed: int = 42) -> pd.DataFrame:
    """
    生成带权重列的多标的 K 线（转发到 ``wbt.mock.mock_weights``）

    参数:
        seed: 随机种子，相同 seed 保证结果可复现

    返回:
        DataFrame，含标的、时间、价格列以及一列模拟"目标权重"，
        典型用途为 :class:`wbt.WeightBacktest` 的输入打样数据。

    备注:
        wbt 端使用一组默认的 symbols / 频率，调用方目前无法自定义。
        如需更灵活的样本，请直接调用 ``wbt.mock.mock_weights``。
    """
    return _mock_weights(seed=seed)
