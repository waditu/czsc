# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/10 19:45
describe: 30分钟笔非多即空策略

本示例展示如何使用 czsc 库定义和回放一个简单的择时策略。
策略基于不同级别K线的笔方向信号进行多空操作。

核心概念：
- CzscStrategyBase：策略基类，定义策略的核心要素
- Position：持仓策略，定义开平仓规则
- Event：事件，由信号组合构成，触发交易操作
- replay：回放功能，用于验证策略逻辑是否正确
"""
import czsc
from pathlib import Path
from loguru import logger
from czsc import Event, Position
from czsc.mock import generate_symbol_kines
from czsc import format_standard_kline, Freq


def create_long_short_V230909(symbol, **kwargs):
    """笔非多即空策略

    使用的信号函数：
    https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230101.html

    策略逻辑：
    - 当笔向上时开多，当笔向下时开空
    - 过滤涨跌停，避免追涨停或杀跌停
    """
    base_freq = kwargs.get('base_freq', '30分钟')

    opens = [
        {
            "operate": "开多",
            "signals_all": [f"{base_freq}_D1_表里关系V230101_向上_任意_任意_0"],
            "signals_any": [],
            "signals_not": [f"{base_freq}_D1_涨跌停V230331_涨停_任意_任意_0"],
        },
        {
            "operate": "开空",
            "signals_all": [f"{base_freq}_D1_表里关系V230101_向下_任意_任意_0"],
            "signals_any": [],
            "signals_not": [f"{base_freq}_D1_涨跌停V230331_跌停_任意_任意_0"],
        },
    ]

    exits = []

    pos = Position(
        name=f"{base_freq}笔非多即空",
        symbol=symbol,
        opens=[Event.load(x) for x in opens],
        exits=[Event.load(x) for x in exits],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )
    return pos


class Strategy(czsc.CzscStrategyBase):
    """30分钟笔非多即空策略

    该策略同时在30分钟、60分钟和日线三个级别上运行笔非多即空逻辑。
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def positions(self):
        pos_list = [
            create_long_short_V230909(self.symbol, base_freq='30分钟'),
            create_long_short_V230909(self.symbol, base_freq='60分钟'),
            create_long_short_V230909(self.symbol, base_freq='日线'),
        ]
        return pos_list


if __name__ == '__main__':
    results_path = Path('/tmp/czsc_examples/笔非多即空')
    results_path.mkdir(exist_ok=True, parents=True)
    logger.add(results_path / "czsc.log", rotation="1 week", encoding="utf-8")

    # 使用 mock 数据生成模拟K线（无需外部数据源）
    symbol = 'mock_000001'
    df = generate_symbol_kines(symbol, '15分钟', '20200101', '20230101', seed=42)
    bars = format_standard_kline(df, freq=Freq.F15)

    tactic = Strategy(symbol=symbol)

    # 使用 logger 记录策略的基本信息
    logger.info(f"K线周期列表：{tactic.freqs}")
    logger.info(f"信号函数配置列表：{tactic.signals_config}")

    # 回测策略
    trader = tactic.backtest(bars, sdt='20210101')

    # 查看每个持仓策略的回测结果
    for pos in trader.positions:
        logger.info(f"策略 [{pos.name}]: 持仓记录数={len(pos.holds)}, 交易对数={len(pos.pairs)}")

    # 将持仓策略保存到本地 json 文件中
    tactic.save_positions(results_path / "positions")
    logger.info(f"策略回测完成，结果保存在 {results_path}")
