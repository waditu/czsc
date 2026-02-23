# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/6/7 21:12
describe: CTAResearch 使用示例

本示例展示如何使用 CTAResearch 进行 CTA 策略研究，包括：
1. 定义策略类（继承 CzscStrategyBase）
2. 使用 mock 数据进行策略回放和回测
3. 查看回测结果

注意：如果使用多进程回测，必须在 __main__ 中执行，且必须在命令行中运行。
"""
from czsc import CTAResearch, CzscStrategyBase, Event, Position
from czsc.mock import generate_symbol_kines
from czsc import format_standard_kline, Freq


class MyStrategy(CzscStrategyBase):
    """简单的笔方向策略示例

    该策略基于日线笔方向进行多空操作：
    - 笔向上时开多
    - 笔向下时开空
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def positions(self):
        opens = [
            {
                "operate": "开多",
                "signals_all": ["日线_D1_表里关系V230101_向上_任意_任意_0"],
                "signals_any": [],
                "signals_not": [],
            },
            {
                "operate": "开空",
                "signals_all": ["日线_D1_表里关系V230101_向下_任意_任意_0"],
                "signals_any": [],
                "signals_not": [],
            },
        ]
        pos = Position(
            name="日线笔方向策略",
            symbol=self.symbol,
            opens=[Event.load(x) for x in opens],
            exits=[],
            interval=3600 * 4,
            timeout=16 * 30,
            stop_loss=500,
        )
        return [pos]


def read_mock_bars(symbol, freq, sdt, edt, **kwargs):
    """使用 mock 数据模拟 read_bars 接口

    CTAResearch 要求 read_bars 函数签名为：
    (symbol, freq, sdt, edt, **kwargs) -> List[RawBar]
    """
    freq_map = {'日线': ('日线', Freq.D), '30分钟': ('30分钟', Freq.F30), '15分钟': ('15分钟', Freq.F15)}
    mock_freq, bar_freq = freq_map.get(freq, ('日线', Freq.D))
    df = generate_symbol_kines(symbol, mock_freq, sdt, edt, seed=42)
    bars = format_standard_kline(df, freq=bar_freq)
    return bars


if __name__ == '__main__':
    bot = CTAResearch(
        results_path='/tmp/czsc_examples/CTA投研',
        signals_module_name='czsc.signals',
        strategy=MyStrategy,
        read_bars=read_mock_bars,
    )

    # 策略回测（多品种批量回测，max_workers=1 表示单进程）
    symbols = [f'mock_{i:06d}' for i in range(1, 4)]
    bot.backtest(symbols=symbols, max_workers=1, bar_sdt='20180101', edt='20230101', sdt='20200101')
