# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/10/30 20:21
"""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')

from czsc.data.ts_cache import TsDataCache
from czsc.sensors.stocks import StocksDaySensor
from czsc.objects import Operate, Signal, Factor, Event
from czsc.signals import get_selector_signals


dc = TsDataCache(data_path=r'C:\ts_data', sdt='2019-01-01', edt='20211029')

def get_event():
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
    return event


if __name__ == '__main__':
    params = {
        "validate_sdt": "20210101",
        "validate_edt": "20211114",
        "min_total_mv": 5e5,    # 最小总市值，单位为万元，1e6万元 = 100亿
        "fc_top_n": 30,         # 板块效应 - 选择出现数量最多的 top_n 概念
        'fc_min_n': 2           # 单股票至少有 min_n 概念在 top_n 中
    }
    sds = StocksDaySensor(dc, get_selector_signals, get_event, params)

    results_path = fr"C:\ZB\data\strong_stocks_selector\{sds.event.name}_{sds.sdt}_{sds.edt}"
    file_docx = r"C:\ZB\data\strong_stocks_selector\股票选股强度验证.docx"
    df_holds = sds.report_performance(results_path, file_docx)

    # 获取最后一个交易日的持仓明细
    # max_date = df_holds.成分日期.max()
    # df_last_holds = df_holds[df_holds['成分日期'] == max_date]
    # df_last_holds.to_excel(f"{sss.event.name}_{max_date.replace('/', '')}_持仓明细.xlsx", index=False)

