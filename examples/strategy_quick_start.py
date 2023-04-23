# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/4/7 19:45
describe: 策略编写快速入门
"""
import czsc
# 导入 CZSC 投研共享数据接口
from czsc.connectors import research
from czsc import Event, Position


def create_beta_long_V230406(symbol, **kwargs):
    """

    使用的信号函数：

    - https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_third_bs_V230319.html
    - https://czsc.readthedocs.io/en/latest/api/czsc.signals.bar_single_V230214.html
    - https://czsc.readthedocs.io/en/latest/api/czsc.signals.bar_zdt_V230331.html

    :param symbol:
    :return:
    """
    opens = [
        {'name': '开多',
         'operate': '开多',
         'signals_all': [],
         'signals_any': [],
         'signals_not': [],
         'factors': [{'name': '15分钟三买',
                      'signals_all': ['15分钟_D1#SMA#34_BS3辅助V230319_三买_任意_任意_0'],
                      'signals_any': [],
                      'signals_not': []}
                     ]},
    ]

    exits = [
        {'name': '平多',
         'operate': '平多',
         'signals_all': [],
         'signals_any': [],
         'signals_not': [],
         'factors': [{'name': '日线大阴线',
                      'signals_all': ['日线_D1T10_状态_阴线_长实体_任意_0'],
                      'signals_any': [],
                      'signals_not': []}]},

    ]
    if kwargs.get('is_stocks', False):
        opens[0]['signals_not'].append('15分钟_D1_涨跌停V230331_涨停_任意_任意_0')
        exits[0]['signals_not'].append('15分钟_D1_涨跌停V230331_跌停_任意_任意_0')

    pos = Position(name="15分钟三买多头", symbol=symbol,
                   opens=[Event.load(x) for x in opens],
                   exits=[Event.load(x) for x in exits],
                   interval=3600 * 4, timeout=16 * 30, stop_loss=500)
    return pos


def create_beta_long_V230407(symbol, **kwargs):
    """

    使用的信号函数：

    - https://czsc.readthedocs.io/en/latest/api/czsc.signals.cxt_third_bs_V230319.html
    - https://czsc.readthedocs.io/en/latest/api/czsc.signals.bar_single_V230214.html
    - https://czsc.readthedocs.io/en/latest/api/czsc.signals.bar_zdt_V230331.html

    :param symbol:
    :return:
    """
    opens = [
        {'name': '开多',
         'operate': '开多',
         'signals_all': [],
         'signals_any': [],
         'signals_not': [],
         'factors': [{'name': '15分钟三买',
                      'signals_all': ['15分钟_D1#SMA#34_BS3辅助V230319_三买_任意_任意_0'],
                      'signals_any': [],
                      'signals_not': []}
                     ]},
    ]

    exits = [
        {'name': '平多',
         'operate': '平多',
         'signals_all': [],
         'signals_any': [],
         'signals_not': [],
         'factors': [{'name': '日线大阴线',
                      'signals_all': ['日线_D1T10_状态_阴线_长实体_任意_0'],
                      'signals_any': [],
                      'signals_not': []},
                     {'name': '日线大阳线',
                      'signals_all': ['日线_D1T10_状态_阳线_长实体_任意_0'],
                      'signals_any': [],
                      'signals_not': []},
                     ]},

    ]
    if kwargs.get('is_stocks', False):
        opens[0]['signals_not'].append('15分钟_D1_涨跌停V230331_涨停_任意_任意_0')
        exits[0]['signals_not'].append('15分钟_D1_涨跌停V230331_跌停_任意_任意_0')

    pos = Position(name="15分钟三买V1多头", symbol=symbol,
                   opens=[Event.load(x) for x in opens],
                   exits=[Event.load(x) for x in exits],
                   interval=3600 * 4, timeout=16 * 30, stop_loss=500)
    return pos


class CzscStocksBeta(czsc.CzscStrategyBase):
    """CZSC 股票 Beta 策略"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.is_stocks = kwargs.get('is_stocks', False)

    @property
    def positions(self):
        pos_list = [
            create_beta_long_V230406(self.symbol, is_stocks=self.is_stocks),
            create_beta_long_V230407(self.symbol, is_stocks=self.is_stocks)
        ]
        return pos_list


if __name__ == '__main__':
    symbols = research.get_symbols('中证500成分股')[:30]

    # 执行单品种策略回放
    symbol = symbols[0]
    tactic = CzscStocksBeta(symbol=symbol, is_stocks=True)
    # tactic.freqs              # 查看策略使用的K线周期列表
    # tactic.signals_config     # 查看策略使用的信号函数配置列表

    bars = research.get_raw_bars(symbol, freq=tactic.base_freq, sdt='20150101', edt='20220101')
    trader = tactic.replay(bars, sdt='20200101', res_path=r'D:\策略研究\测试1')
    for _pos in trader.positions:
        print(_pos.name, symbol, _pos.evaluate('多头'))

    # dummy backtest, 只能通过命令行执行，不能在PyCharm中的Python终端执行
    from czsc import DummyBacktest
    db = DummyBacktest(strategy=CzscStocksBeta, signals_path=r'D:\策略研究\signals',
                       results_path=r'D:\策略研究\CzscStocksBetaV2', read_bars=research.get_raw_bars)
    # db.execute(symbols=symbols, n_jobs=10)

    # on bar 回测
    stats = []
    for symbol in symbols[:3]:
        try:
            tactic = CzscStocksBeta(symbol=symbol, is_stocks=True)
            bars = research.get_raw_bars(symbol, freq=tactic.base_freq, sdt='20150101', edt='20220101')
            trader = tactic.backtest(bars, sdt='20200101')
            for _pos in trader.positions:
                stats.append(_pos.evaluate('多头'))
                print(_pos.name, symbol, _pos.evaluate('多头'))
        except Exception as e:
            print(symbol, '回测失败', e)

