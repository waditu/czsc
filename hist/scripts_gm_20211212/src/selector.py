# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:25
"""
import os
from tqdm import tqdm
import pandas as pd
from datetime import datetime
from typing import Callable
from czsc.analyze import CZSC
from czsc.signals import signals
from czsc.utils.io import read_pkl, save_pkl
from czsc.utils.kline_generator import KlineGeneratorD
from czsc.objects import Signal, Factor, Event, Operate

from .utils.base import *


def stocks_dwm_selector(event: Event, get_signals: Callable,
                        max_count: int = 3000,
                        end_date: [str, datetime] = datetime.now(), wx_key=None):
    """大级别选股（日线&月线&周线）"""
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)
    kgd_path = "./data/kgd"
    os.makedirs(kgd_path, exist_ok=True)

    df = get_instruments(exchanges='SZSE,SHSE', sec_types=1, fields="symbol,sec_name", df=True)
    records = df.to_dict('records')

    home_path = os.path.expanduser('~')

    push_text(content="start running selector", key=wx_key)
    results = []
    for row in tqdm(records, desc=f"{end_date} - get signals"):
        symbol = row['symbol']
        try:
            file_kgd = os.path.join(kgd_path, f'{symbol}.kgd')
            if os.path.exists(file_kgd):
                kgd: KlineGeneratorD = read_pkl(file_kgd)
                if kgd.end_dt.date() != datetime.now().date() and datetime.now().isoweekday() <= 5:
                    k0 = get_kline(symbol, freq="1d", end_time=datetime.now(), count=1)
                    k0 = [x for x in k0 if x.dt > kgd.end_dt]
                    if k0:
                        print(k0)
                        for bar in k0:
                            kgd.update(bar)
            else:
                k0 = get_kline(symbol, end_time=end_date, freq='1d', count=10000, adjust=ADJUST_PREV)
                kgd = KlineGeneratorD()
                for bar in k0:
                    kgd.update(bar)
            save_pkl(kgd, file_kgd)
            # assert kgd.end_dt.date() == datetime.now().date(), f"kgd.end_dt = {kgd.end_dt}"

            last_vols = [k_.open * k_.vol for k_ in kgd.bars[Freq.D.value][-10:]]
            if min(last_vols) < 1e8:
                continue

            c0 = CZSC(kgd.bars[Freq.D.value][-max_count:], get_signals=get_signals)
            c1 = CZSC(kgd.bars[Freq.W.value][-max_count:], get_signals=get_signals)
            c2 = CZSC(kgd.bars[Freq.M.value][-max_count:], get_signals=get_signals)

            s = OrderedDict(row)
            s.update(c0.signals)
            s.update(c1.signals)
            s.update(c2.signals)

            m, f = event.is_match(s)
            if m:
                msg = f"{s['sec_name']}: {f}\n"
                msg += f"最新时间：{kgd.end_dt.strftime(dt_fmt)}\n"
                msg += f"同花顺F10：http://basic.10jqka.com.cn/{symbol.split('.')[1]}\n"
                msg += f"新浪行情：https://finance.sina.com.cn/realstock/company/{symbol[:2].lower()}{symbol[-6:]}/nc.shtml"
                push_text(content=msg, key=wx_key)

                res = {
                    'symbol': symbol,
                    'name': s['sec_name'],
                    'reason': f,
                    'end_dt': kgd.end_dt.strftime(dt_fmt),
                    'F10': f"http://basic.10jqka.com.cn/{symbol.split('.')[1]}",
                    'Kline': f"https://finance.sina.com.cn/realstock/company/{symbol[:2].lower()}{symbol[-6:]}/nc.shtml"
                }
                results.append(res)
                print(res)
        except:
            print("fail on {}".format(symbol))
            traceback.print_exc()

    file_results = os.path.join(home_path, f"selector_results_{end_date.strftime('%Y%m%d')}.xlsx")
    df_r = pd.DataFrame(results)
    df_r.to_excel(file_results, index=False)
    push_file(file_results, key=wx_key)
    push_text(content="end running selector", key=wx_key)


def stocks_dwm_selector_rt(context):
    if context.now.isoweekday() >= 6:
        return

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
    stocks_dwm_selector(event, signals.get_selector_signals, end_date=context.now, wx_key=context.wx_key)


if __name__ == '__main__':
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
    stocks_dwm_selector(event, signals.get_selector_signals, max_count=1000, wx_key='909731bd-****-46ad-****-24b9830873a4')
