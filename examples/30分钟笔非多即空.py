# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/10 19:45
describe: 30分钟笔非多即空策略
"""
import czsc
from pathlib import Path
from loguru import logger
from czsc.connectors import research
from czsc import Event, Position


def create_long_short_V230908(symbol, **kwargs):
    """30分钟笔非多即空策略

    使用的信号函数：

    https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230101.html
    """
    opens = [
        {
            "operate": "开多",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["30分钟_D1_表里关系V230101_向上_任意_任意_0"],
                    "signals_any": [],
                    "signals_not": ["30分钟_D1_涨跌停V230331_涨停_任意_任意_0"],
                }
            ],
        },
        {
            "operate": "开空",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": ["30分钟_D1_表里关系V230101_向下_任意_任意_0"],
                    "signals_any": [],
                    "signals_not": ["30分钟_D1_涨跌停V230331_跌停_任意_任意_0"],
                }
            ],
        },
    ]

    exits = []

    pos = Position(
        name="30分钟笔非多即空",
        symbol=symbol,
        opens=[Event.load(x) for x in opens],
        exits=[Event.load(x) for x in exits],
        interval=3600 * 4,
        timeout=16 * 30,
        stop_loss=500,
    )
    return pos


def create_long_short_V230909(symbol, **kwargs):
    """笔非多即空策略

    使用的信号函数：

    https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_bi_status_V230101.html
    """
    base_freq = kwargs.get('base_freq', '30分钟')

    opens = [
        {
            "operate": "开多",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": [f"{base_freq}_D1_表里关系V230101_向上_任意_任意_0"],
                    "signals_any": [],
                    "signals_not": [f"{base_freq}_D1_涨跌停V230331_涨停_任意_任意_0"],
                }
            ],
        },
        {
            "operate": "开空",
            "signals_all": [],
            "signals_any": [],
            "signals_not": [],
            "factors": [
                {
                    "signals_all": [f"{base_freq}_D1_表里关系V230101_向下_任意_任意_0"],
                    "signals_any": [],
                    "signals_not": [f"{base_freq}_D1_涨跌停V230331_跌停_任意_任意_0"],
                }
            ],
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_stocks = kwargs.get('is_stocks', True)

    @property
    def positions(self):
        pos_list = [
            # create_long_short_V230908(self.symbol),
            create_long_short_V230909(self.symbol, base_freq='30分钟'),
            create_long_short_V230909(self.symbol, base_freq='60分钟'),
            create_long_short_V230909(self.symbol, base_freq='日线'),
        ]
        return pos_list


if __name__ == '__main__':
    results_path = Path(r'D:\策略研究\笔非多即空')
    logger.add(results_path / "czsc.log", rotation="1 week", encoding="utf-8")
    results_path.mkdir(exist_ok=True, parents=True)

    symbols = research.get_symbols('中证500成分股')[:30]
    symbol = symbols[0]
    tactic = Strategy(symbol=symbol, is_stocks=True)

    # 使用 logger 记录策略的基本信息
    logger.info(f"K线周期列表：{tactic.freqs}")
    logger.info(f"信号函数配置列表：{tactic.signals_config}")

    # replay 查看策略的编写是否正确，执行过程是否符合预期
    bars = research.get_raw_bars(symbol, freq=tactic.base_freq, sdt='20150101', edt='20220101')
    trader = tactic.replay(bars, sdt='20210101', res_path=results_path / "replay", refresh=True)

    # 当策略执行过程符合预期后，将持仓策略保存到本地 json 文件中
    tactic.save_positions(results_path / "positions")
