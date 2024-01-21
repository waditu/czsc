# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/11/15 20:45
describe: CZSC开源协作团队内部使用数据接口

接口说明：https://s0cqcxuy3p.feishu.cn/wiki/F3HGw9vDPisWtSkJr1ac5DEcnNh
"""
import os
import czsc
import pandas as pd
from tqdm import tqdm
from datetime import datetime
from czsc import RawBar, Freq

# 首次使用需要打开一个python终端按如下方式设置 token
# czsc.set_url_token(token='your token', url='http://zbczsc.com:9106')

cache_path = os.getenv("CZSC_CACHE_PATH", os.path.expanduser("~/.quant_data_cache"))
dc = czsc.DataClient(url='http://zbczsc.com:9106', cache_path=cache_path)


def format_kline(kline: pd.DataFrame, freq: Freq):
    """格式化K线数据

    :param kline: K线数据，格式如下：

        ==========  =========  ======  =======  ======  =====  ===========  ===========
        dt          code         open    close    high    low          vol       amount
        ==========  =========  ======  =======  ======  =====  ===========  ===========
        2022-01-04  600520.SH   20.54    21.12   21.17  20.33  2.1724e+06   1.94007e+07
        2022-01-05  600520.SH   21.17    20.73   21.29  20.52  1.8835e+06   1.67258e+07
        2022-01-06  600520.SH   20.56    21.17   21.57  18.69  3.4227e+06   3.11461e+07
        2022-01-07  600520.SH   21.5     20.61   21.5   20.61  2.51741e+06  2.24819e+07
        2022-01-10  600520.SH   20.4     21.69   21.69  20.4   4.80894e+06  4.39598e+07
        ==========  =========  ======  =======  ======  =====  ===========  ===========

    :return: 格式化后的K线数据
    """
    bars = []
    for i, row in kline.iterrows():
        bar = RawBar(symbol=row['code'], id=i, freq=freq, dt=row['dt'],
                     open=row['open'], close=row['close'], high=row['high'],
                     low=row['low'], vol=row['vol'], amount=row['amount'])
        bars.append(bar)
    return bars


def get_symbols(name, **kwargs):
    """获取指定分组下的所有标的代码

    :param name: 分组名称，可选值：'A股指数', 'ETF', '股票', '期货主力'
    :param kwargs:
    :return:
    """
    if name == "股票":
        data = dc.stock_basic(nobj=1, status=1)
        return data['code'].tolist()

    if name == "ETF":
        raise NotImplementedError

    if name == "A股指数":
        raise NotImplementedError

    if name == "期货主力":
        kline = dc.future_klines(trade_date="20231101")
        return kline['code'].unique().tolist()

    raise ValueError(f"{name} 分组无法识别，获取标的列表失败！")


def get_raw_bars(symbol, freq, sdt, edt, fq='前复权', **kwargs):
    """获取 CZSC 库定义的标准 RawBar 对象列表

    :param symbol: 标的代码
    :param freq: 周期，支持 Freq 对象，或者字符串，如
            '1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线', '季线', '年线'
    :param sdt: 开始时间
    :param edt: 结束时间
    :param fq: 除权类型，可选值：'前复权', '后复权', '不复权'
    :param kwargs:
    :return:
    """
    freq = czsc.Freq(freq)

    if symbol.endswith(".SH") or symbol.endswith(".SZ"):
        fq_map = {"前复权": "qfq", "后复权": "hfq", "不复权": None}
        adj = fq_map.get(fq, None)
        if freq.value.endswith('分钟'):
            df = dc.pro_bar(code=symbol, sdt=sdt, edt=edt, freq='min', adj=adj)
            df = df[~df['dt'].str.endswith("09:30:00")].reset_index(drop=True)
        else:
            df = dc.pro_bar(code=symbol, sdt=sdt, edt=edt, freq='day', adj=adj)
        df.rename(columns={'code': 'symbol'}, inplace=True)
        df['dt'] = pd.to_datetime(df['dt'])
        return czsc.resample_bars(df, target_freq=freq)

    if symbol.endswith("9001"):
        if freq.value.endswith('分钟'):
            df = dc.future_klines(code=symbol, sdt=sdt, edt=edt, freq='1m')
        else:
            df = dc.future_klines(code=symbol, sdt=sdt, edt=edt, freq='1d')
        df.rename(columns={'code': 'symbol'}, inplace=True)
        df['amount'] = df['vol'] * df['close']
        df = df[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol', 'amount']].copy().reset_index(drop=True)
        df['dt'] = pd.to_datetime(df['dt'])
        return czsc.resample_bars(df, target_freq=freq)

    raise ValueError(f"symbol {symbol} 无法识别，获取数据失败！")


@czsc.disk_cache(path=cache_path, ttl=-1)
def stocks_daily_klines(sdt='20170101', edt="20240101", **kwargs):
    """获取全市场A股的日线数据"""
    adj = kwargs.get('adj', 'hfq')
    sdt = pd.to_datetime(sdt).year
    edt = pd.to_datetime(edt).year
    years = [str(year) for year in range(sdt, edt + 1)]

    res = []
    for year in years:
        ttl = 3600 * 6 if year == str(datetime.now().year) else -1
        kline = dc.pro_bar(trade_year=year, adj=adj, v=2, ttl=ttl)
        res.append(kline)

    dfk = pd.concat(res, ignore_index=True)
    dfk['dt'] = pd.to_datetime(dfk['dt'])
    dfk = dfk.sort_values(['code', 'dt'], ascending=True).reset_index(drop=True)
    if kwargs.get('exclude_bj', True):
        dfk = dfk[~dfk['code'].str.endswith(".BJ")].reset_index(drop=True)

    nxb = kwargs.get('nxb', [1, 2, 5])
    if nxb:
        rows = []
        for _, dfg in tqdm(dfk.groupby('code'), desc="计算NXB收益率", ncols=80, colour='green'):
            czsc.update_nbars(dfg, numbers=nxb, move=1, price_col='open')
            rows.append(dfg)
        dfk = pd.concat(rows, ignore_index=True)

    dfk = dfk.rename(columns={'code': 'symbol'})
    return dfk
