"""parity 测试套件共享 fixture 定义。

本目录下所有 parity 测试都遵循同一套测试范式：
    1. 同时导入 ``rs_czsc``（PyPI 上的基线版本）与 ``czsc``（迁移后的本地版本）
    2. 用同一份固定随机种子的输入数据分别驱动两套实现
    3. 比较输出，要求二者在数值/结构层面完全一致

``rs_czsc`` 通过 ``pyproject.toml`` 的开发依赖引入，仅供测试使用。
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def rs_czsc_module():
    """以 session 范围导入 ``rs_czsc`` 基线模块。

    若运行环境未安装 ``rs_czsc``，使用 ``pytest.importorskip`` 跳过整个
    parity 测试套件而不是报错，这样可以让 CI 在没有 Rust 运行时的环境
    下仍能完成其他测试。
    """
    rs_czsc = pytest.importorskip(
        "rs_czsc",
        reason="rs_czsc baseline must be installed to run parity tests",
    )
    return rs_czsc


@pytest.fixture(scope="session")
def czsc_module():
    """以 session 范围导入待测的 ``czsc`` 模块。"""
    import czsc

    return czsc


@pytest.fixture(scope="session")
def mock_kline_df():
    """单品种 K 线 DataFrame，固定随机种子，供所有需要 bars 输入的 parity
    测试使用。

    数据形态与 ``czsc._compat.bars_to_dataframe`` 输出保持一致：
    六个数值列（OHLC + vol + amount）使用 Float64，``dt`` 列为 datetime64。
    """
    from wbt.mock import mock_symbol_kline

    df = mock_symbol_kline("000001", "日线", "20230101", "20241231", seed=42)
    return df


@pytest.fixture(scope="session")
def sample_signal_strings():
    """一组真实存在于注册表中的信号字符串，供 ``derive_signals_*`` 等
    parity 测试使用。

    选取的信号必须在 rs_czsc 与 czsc 两边都能解析，否则等价性测试无法
    成立。
    """
    return [
        "日线_D1N5M5TH10_ADTMV230603_看多_任意_任意_0",
        "日线_D1N5M5_AMV能量V230603_看多_任意_任意_0",
        "日线_D1N5P5_ASI多空V230603_看多_任意_任意_0",
    ]


@pytest.fixture(scope="session")
def sample_position_dict():
    """一份典型的 Position dict，使用注册表中真实存在的信号，便于跑通
    完整的 ``run_research`` 流水线。

    关键字段：
        * opens / exits: 每边一个 Event，使用 dict 形式的 signals_all
        * interval / timeout / stop_loss: 风控相关参数
        * T0: 是否允许 T+0 交易
    """
    return {
        "name": "test_pos",
        "symbol": "000001",
        "opens": [
            {
                "name": "open_long",
                "operate": "开多",
                "signals_all": [{"key": "日线_D1N5M5TH10_ADTMV230603", "value": "看多_任意_任意_0"}],
                "signals_any": [],
                "signals_not": [],
            },
        ],
        "exits": [
            {
                "name": "exit_long",
                "operate": "平多",
                "signals_all": [{"key": "日线_D1N5M5TH10_ADTMV230603", "value": "看空_任意_任意_0"}],
                "signals_any": [],
                "signals_not": [],
            },
        ],
        "interval": 0,
        "timeout": 100,
        "stop_loss": 500.0,
        "T0": False,
    }
