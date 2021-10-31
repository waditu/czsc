# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/30 20:18
describe: A股市场感应器若干，主要作为编写感应器的示例

强势个股传感器
强势板块传感器
强势行业传感器
大盘指数传感器
"""
import traceback
from datetime import timedelta, datetime
from collections import OrderedDict

import pandas as pd
from tqdm import tqdm

from ..utils import WordWriter
from ..data.ts_cache import TsDataCache
from ..analyze import CZSC
from ..signals import get_selector_signals
from ..objects import Operate, Signal, Factor, Event, Freq
from ..utils.kline_generator import KlineGeneratorD


class StrongStocksSensor:
    """强势个股传感器

    输入：市场个股全部行情、概念板块成分信息
    输出：强势个股列表以及概念板块分布
    """
    def __init__(self, dc: TsDataCache):
        self.name = self.__class__.__name__
        self.data = OrderedDict()
        self.dc = dc

    def get_share_czsc_signals(self, ts_code: str, trade_date: datetime):
        """获取 ts_code 在 trade_date 的信号字典"""
        start_date = trade_date - timedelta(days=5000)
        bars = self.dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=trade_date,
                               freq='D', asset="E", raw_bar=True)
        assert bars[-1].dt.date() == trade_date.date()
        kgd = KlineGeneratorD(freqs=[Freq.D.value, Freq.W.value, Freq.M.value])
        for bar in bars:
            kgd.update(bar)

        c0 = CZSC(kgd.bars[Freq.D.value][-1000:], get_signals=get_selector_signals)
        c1 = CZSC(kgd.bars[Freq.W.value][-1000:], get_signals=get_selector_signals)
        c2 = CZSC(kgd.bars[Freq.M.value][-1000:], get_signals=get_selector_signals)

        s = OrderedDict(ts_code=ts_code, trade_date=trade_date)
        s.update(c0.signals)
        s.update(c1.signals)
        s.update(c2.signals)
        return s

    def process_one_day(self, trade_date: [datetime, str]):
        if isinstance(trade_date, str):
            trade_date = pd.to_datetime(trade_date)

        dc = self.dc
        stocks = dc.stock_basic()
        stocks = stocks[stocks.list_date <= (trade_date - timedelta(days=365)).strftime('%Y%m%d')]
        records = stocks.to_dict('records')

        event = Event(name="选股", operate=Operate.LO, factors=[
            Factor(name="月线KDJ金叉_日线MACD强势", signals_all=[
                Signal("月线_KDJ状态_任意_金叉_任意_任意_0"),
                Signal('日线_MACD状态_任意_DIFF大于0_DEA大于0_柱子增大_0'),
                Signal('日线_MA5状态_任意_收盘价在MA5上方_任意_任意_0'),
            ]),
            Factor(name="月线KDJ金叉_日线潜在三买", signals_all=[
                Signal("月线_KDJ状态_任意_金叉_任意_任意_0"),
                Signal('日线_倒0笔_潜在三买_构成中枢_近3K在中枢上沿附近_近7K突破中枢GG_0'),
                Signal('日线_MA5状态_任意_收盘价在MA5上方_任意_任意_0'),
            ]),
            Factor(
                name="月线KDJ金叉_周线三笔强势",
                signals_all=[
                    Signal("月线_KDJ状态_任意_金叉_任意_任意_0"),
                    Signal('日线_MA5状态_任意_收盘价在MA5上方_任意_任意_0'),
                ],
                signals_any=[
                    Signal('周线_倒1笔_三笔形态_向下不重合_任意_任意_0'),
                    Signal('周线_倒1笔_三笔形态_向下奔走型_任意_任意_0'),
                    Signal('周线_倒1笔_三笔形态_向下盘背_任意_任意_0'),
                ]
            ),
            Factor(name="月线KDJ金叉_周线MACD强势", signals_all=[
                Signal("月线_KDJ状态_任意_金叉_任意_任意_0"),
                Signal('周线_MACD状态_任意_DIFF大于0_DEA大于0_柱子增大_0'),
                Signal('日线_MA5状态_任意_收盘价在MA5上方_任意_任意_0'),
            ]),
        ])

        results = []
        for row in tqdm(records, desc=f"{trade_date} selector"):
            symbol = row['ts_code']
            try:
                s = self.get_share_czsc_signals(symbol, trade_date)
                m, f = event.is_match(s)
                if m:
                    dt_fmt = "%Y%m%d"
                    res = {
                        'symbol': symbol,
                        'name': row['name'],
                        'reason': f,
                        'end_dt': trade_date.strftime(dt_fmt),
                        'F10': f"http://basic.10jqka.com.cn/{symbol.split('.')[0]}",
                        'Kline': f"https://finance.sina.com.cn/realstock/company/{symbol[-2:].lower()}{symbol[:6]}/nc.shtml"
                    }
                    results.append(res)
                    print(res)
            except:
                print("fail on {}".format(symbol))
                traceback.print_exc()
        return results

    def validate(self):
        """"""
        pass

    def report(self, writer: WordWriter):
        """撰写报告"""
        raise NotImplementedError
