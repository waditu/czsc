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
import os.path
import traceback
from datetime import timedelta, datetime
from collections import OrderedDict

import pandas as pd
from tqdm import tqdm

from ..utils import WordWriter
from ..data.ts_cache import TsDataCache
from ..signals import get_selector_signals
from ..objects import Operate, Signal, Factor, Event, Freq
from ..utils.kline_generator import KlineGeneratorD
from ..utils import io
from ..traders.daily import CzscDailyTrader


class StrongStocksSensor:
    """强势个股传感器

    输入：市场个股全部行情、概念板块成分信息
    输出：强势个股列表以及概念板块分布
    """

    def __init__(self, dc: TsDataCache):
        self.name = self.__class__.__name__
        self.data = OrderedDict()
        self.dc = dc
        self.strong_event = Event(name="选股", operate=Operate.LO, factors=[
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

    def get_share_czsc_signals(self, ts_code: str, trade_date: datetime):
        """获取 ts_code 在 trade_date 的信号字典"""
        start_date = trade_date - timedelta(days=5000)
        bars = self.dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=trade_date,
                               freq='D', asset="E", raw_bar=True)
        assert bars[-1].dt.date() == trade_date.date()
        kgd = KlineGeneratorD(freqs=[Freq.D.value, Freq.W.value, Freq.M.value])
        for bar in bars:
            kgd.update(bar)
        ct = CzscDailyTrader(kgd, get_selector_signals)
        return dict(ct.s)

    def process_one_day(self, trade_date: [datetime, str]):
        if isinstance(trade_date, str):
            trade_date = pd.to_datetime(trade_date)

        dc = self.dc
        stocks = dc.stock_basic()
        stocks = stocks[stocks.list_date <= (trade_date - timedelta(days=365)).strftime('%Y%m%d')]
        records = stocks.to_dict('records')

        event = self.strong_event

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

    def get_share_hist_signals(self, ts_code: str, trade_date: datetime):
        """获取单个标的全部历史信号"""
        file_pkl = os.path.join(self.dc.cache_path, f"{ts_code}_all_hist_signals.pkl")
        if os.path.exists(file_pkl):
            all_hist_signals = io.read_pkl(file_pkl)

        else:
            start_date = pd.to_datetime(self.dc.sdt) - timedelta(days=1000)
            bars = self.dc.pro_bar(ts_code=ts_code, start_date=start_date, end_date=self.dc.edt,
                                   freq='D', asset="E", raw_bar=True)
            kgd = KlineGeneratorD(freqs=[Freq.D.value, Freq.W.value, Freq.M.value])
            for bar in bars[:250]:
                kgd.update(bar)
            ct = CzscDailyTrader(kgd, get_selector_signals)

            all_hist_signals = {}
            for bar in tqdm(bars[250:], desc=f"{ts_code} all hist signals"):
                ct.update(bar)
                all_hist_signals[bar.dt.strftime('%Y%m%d')] = dict(ct.s)

            io.save_pkl(all_hist_signals, file_pkl)

        return all_hist_signals.get(trade_date.strftime("%Y%m%d"), None)

    def get_share_hist_returns(self, ts_code: str, trade_date: datetime):
        """获取单个标 trade_date 后的 n bar returns"""
        df = self.dc.pro_bar(ts_code=ts_code, start_date=trade_date, end_date=trade_date,
                             freq='D', asset="E", raw_bar=False)
        if df.empty:
            return None
        else:
            assert len(df) == 1
            return df.iloc[0].to_dict()

    def validate(self, sdt='20200101', edt='20201231'):
        """验证传感器在一段时间内的表现

        :param sdt: 开始时间
        :param edt: 结束时间
        :return:
        """
        stocks = self.dc.stock_basic()
        trade_cal = self.dc.trade_cal()
        trade_cal = trade_cal[(trade_cal.cal_date >= sdt) & (trade_cal.cal_date <= edt) & trade_cal.is_open]
        trade_dates = trade_cal.cal_date.to_list()

        event = self.strong_event
        results = []
        for trade_date in trade_dates:
            trade_date = pd.to_datetime(trade_date)
            min_list_date = (trade_date - timedelta(days=365)).strftime('%Y%m%d')
            rows = stocks[stocks.list_date <= min_list_date].to_dict('records')

            for row in tqdm(rows, desc=trade_date.strftime('%Y%m%d')):
                ts_code = row['ts_code']
                try:
                    s = self.get_share_hist_signals(ts_code, trade_date)
                    if not s:
                        continue

                    n = self.get_share_hist_returns(ts_code, trade_date)
                    m, f = event.is_match(s)
                    if m:
                        res = {
                            'symbol': ts_code,
                            'name': row['name'],
                            'reason': f,
                            'trade_date': trade_date.strftime("%Y%m%d"),
                        }
                        res.update(n)
                        results.append(res)
                        print(res)
                except:
                    traceback.print_exc()

        df = pd.DataFrame(results)
        df_m = df.groupby('trade_date').apply(lambda x: x[['n1b', 'n2b', 'n3b', 'n5b', 'n10b', 'n20b']].mean())
        return df, df_m

    def report(self, writer: WordWriter):
        """撰写报告"""
        raise NotImplementedError
