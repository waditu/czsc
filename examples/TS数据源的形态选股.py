# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/9/25 19:45
describe: 使用 Tushare 数据源的形态选股

相关飞书文档：
1. https://s0cqcxuy3p.feishu.cn/wiki/UGvvw2bMiihciHkRnJecKzm6nnb
"""
import czsc
import shutil
import pandas as pd
import tushare as ts
from pathlib import Path
from czsc.connectors.ts_connector import get_raw_bars, get_symbols, dc


pro = ts.pro_api()

# 首次使用，需要设置 Tushare 的 token，注意，每台电脑只需要执行一次即可，token 会保存在本地文件中
# 没有 token 的用户，可以点击 https://tushare.pro/register?reg=7 进行注册
# import tushare as ts
# ts.set_token("your token")

# 如果是每天选股，需要执行以下代码先清空缓存，否则会导致选股结果不更新
# dc.clear()


def get_events_matched(refresh=False):
    """执行形态选股"""

    # 获取A股所有股票代码
    symbols = get_symbols("stock")

    # 定义形态事件, 支持多个事件
    events = [
        {
            "name": "日线CCI多头",
            "operate": "开多",
            "signals_not": [
                "日线_D1_涨跌停V230331_跌停_任意_任意_0",
                "日线_D1_涨跌停V230331_涨停_任意_任意_0"
            ],
            "factors": [{"name": "CCI看多", "signals_all": ["日线_D1CCI14#3#10_BS辅助V230402_多头_任意_任意_0"]}],
        },

        {"name": "日线CCI多头；不过滤涨跌停",
         "operate": "开多",
         "factors": [{"name": "CCI看多", "signals_all": ["日线_D1CCI14#3#10_BS辅助V230402_多头_任意_任意_0"]}]},
    ]

    ems_params = {
        "events": events,
        "symbols": symbols,
        "read_bars": get_raw_bars,
        "bar_sdt": "2017-01-01",
        "sdt": "2022-01-01",
        "edt": "2023-01-01",
        "max_workers": 10,
        "results_path": r"D:\量化投研\EMS测试A",
    }
    path = Path(ems_params['results_path'])
    if path.exists() and refresh:
        shutil.rmtree(path)

    ems = czsc.EventMatchSensor(**ems_params)

    # 获取截面匹配结果
    df = ems.data.copy()
    results = {}
    for name in ems.events_name:
        results[name] = df[df[name] == 1][['symbol', 'dt']].copy().reset_index(drop=True)
    return results


if __name__ == '__main__':
    results = get_events_matched(refresh=True)

    # 获取最新的选股结果
    max_dt = max([df.dt.max() for df in results.values()])
    print(f"最新选股日期：{max_dt}")
    latest = {k: df[df.dt == max_dt]['symbol'].to_list() for k, df in results.items()}

    # 过滤掉ST股票
    dfb = dc.daily_basic_new(max_dt)[['ts_code', 'name', 'industry', 'area']]
    st_stocks = dfb[dfb.name.str.contains('ST').fillna(True)]['ts_code'].to_list()
    latest = {k: [s for s in v if s not in st_stocks] for k, v in latest.items()}
    latest = {k: dfb[dfb['ts_code'].isin(v)] for k, v in latest.items() if len(v) > 0}

    # 保存选股结果到 excel
    file_xlsx = Path.cwd() / f"选股结果_{pd.to_datetime(max_dt).strftime('%Y%m%d')}.xlsx"
    with pd.ExcelWriter(file_xlsx) as writer:
        for k, v in latest.items():
            v.to_excel(writer, sheet_name=k, index=False)
    print(f"选股结果保存到：{file_xlsx}")
