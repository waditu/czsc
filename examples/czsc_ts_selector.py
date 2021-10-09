# coding: utf-8
"""
基于 Tushare Pro 数据的选股案例

没有注册 tushare pro 的，可以通过这个链接注册：https://tushare.pro/register?reg=7
"""
import os
import pandas as pd
import traceback
from datetime import datetime
from tqdm import tqdm
from collections import OrderedDict
from czsc.data import ts
from czsc import signals, CZSC
from czsc.objects import Signal, Factor, Event, Freq, Operate


def stocks_dwm_selector(end_date: [str, datetime] = datetime.now(), data_path=None):
    """大级别选股（日线&月线&周线）"""
    if isinstance(end_date, str):
        end_date = pd.to_datetime(end_date)

    if not data_path:
        home_path = os.path.expanduser('~')
        data_path = os.path.join(home_path, '.czsc_selector')

    print(f"selector results path: {data_path}")

    df = ts.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
    records = df.to_dict('records')
    file_results = os.path.join(data_path, f"selector_results_{end_date.strftime('%Y%m%d')}.xlsx")

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
    signals_res = []
    for row in tqdm(records, desc=f"{end_date.strftime('%Y%m%d')} selector"):
        symbol = row['ts_code']
        try:
            k0 = ts.get_kline(symbol, asset='E', freq=Freq.D, start_date="20200101", end_date=end_date)
            k1 = ts.get_kline(symbol, asset='E', freq=Freq.W, start_date="20100101", end_date=end_date)
            k2 = ts.get_kline(symbol, asset='E', freq=Freq.M, start_date="20000101", end_date=end_date)

            c0 = CZSC(k0, get_signals=signals.get_selector_signals)
            c1 = CZSC(k1, get_signals=signals.get_selector_signals)
            c2 = CZSC(k2, get_signals=signals.get_selector_signals)

            s = OrderedDict(row)
            s.update(c0.signals)
            s.update(c1.signals)
            s.update(c2.signals)
            signals_res.append(s)

            m, f = event.is_match(s)
            if m:
                dt_fmt = "%Y%m%d"
                res = {
                    'symbol': symbol,
                    'name': s['name'],
                    'reason': f,
                    'end_dt': k0[-1].dt.strftime(dt_fmt),
                    'F10': f"http://basic.10jqka.com.cn/{symbol.split('.')[0]}",
                    'Kline': f"https://finance.sina.com.cn/realstock/company/{symbol[-2:].lower()}{symbol[:6]}/nc.shtml"
                }
                results.append(res)
                print(res)
        except:
            print("fail on {}".format(symbol))
            traceback.print_exc()

    df_r = pd.DataFrame(results)
    df_r.to_excel(file_results, index=False)
    print(f"selector results saved into {file_results}")
    return df_r


if __name__ == '__main__':
    stocks_dwm_selector()

