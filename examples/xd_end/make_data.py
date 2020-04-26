# coding: utf-8

import traceback
import os
import pandas as pd
from copy import deepcopy
from datetime import timedelta, datetime
from cobra.data.kline import kline_simulator, get_kline
from cobra.data.basic import is_trade_day
from chan import SolidAnalyze, KlineAnalyze
from chan.analyze import is_macd_cross

data_path = "./data"
if not os.path.exists(data_path):
    os.mkdir(data_path)


def get_data(sa):
    mark_convert = {"d": 0, "g": 1}
    signals = {"交易标的": sa.symbol, "交易时间": sa.kas['1分钟'].end_dt}
    for freq, ka in sa.kas.items():
        signals[freq + "分型标记"] = mark_convert[ka.fx[-1]['fx_mark']]
        signals[freq + "笔标记"] = mark_convert[ka.bi[-1]['fx_mark']]
        signals[freq + "线段标记"] = mark_convert[ka.xd[-1]['fx_mark']]
        signals[freq + "MACD金叉"] = int(is_macd_cross(ka, direction='up'))
        signals[freq + "MACD死叉"] = int(is_macd_cross(ka, direction='down'))
    print(signals)
    return signals


def trade_simulator(ts_code, end_date, start_date, asset="E", watch_interval=5):
    """单只标的类实盘模拟，研究买卖点变化过程

    :param ts_code: str
        标的代码，如 300033.SZ
    :param end_date: str
        截止日期，如 2020-03-12
    :param start_date: str
        开始日期
    :param asset: str
        tushare 中的资产类型编码
    :param watch_interval: int
        看盘间隔，单位：分钟；默认值为 5分钟看盘一次
    :return: None
    """
    file_signals = os.path.join(data_path, "%s_%s_%s_signals.txt" % (ts_code, start_date, end_date))
    end_date = datetime.strptime(end_date.replace("-", ""), "%Y%m%d")
    start_date = datetime.strptime(start_date.replace("-", ""), "%Y%m%d")

    while start_date <= end_date:
        if (asset in ["E", "I"]) and (not is_trade_day(start_date.strftime('%Y%m%d'))):
            start_date += timedelta(days=1)
            continue

        ks = kline_simulator(ts_code, trade_dt=start_date.strftime('%Y-%m-%d'), asset=asset, count=1000)
        for i, klines in enumerate(ks.__iter__(), 1):
            if i % watch_interval != 0:
                continue
            sa = SolidAnalyze(klines)
            print(sa.kas['1分钟'].end_dt)
            try:
                signals = get_data(sa)

                with open(file_signals, 'a', encoding='utf-8') as f:
                    f.write(str(signals) + "\n")
            except:
                traceback.print_exc()

        start_date += timedelta(days=1)


def make_one_day(ts_code, trade_date, asset="E"):
    if "-" in trade_date:
        end_date = datetime.strptime(trade_date, '%Y-%m-%d')
    else:
        end_date = datetime.strptime(trade_date, '%Y-%m-%d')
    start_date = end_date - timedelta(days=1)
    end_dt = end_date + timedelta(days=30)
    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    if not is_trade_day(start_date):
        return
    print(f"start trade simulator on {start_date}")
    trade_simulator(ts_code=ts_code, start_date=start_date,
                    end_date=end_date, asset=asset, watch_interval=1)

    for freq in ['1min', '5min', '30min']:
        file_signals = os.path.join(data_path, f"{ts_code}_{start_date}_{end_date}_signals.txt")
        signals = [eval(x) for x in open(file_signals, encoding='utf-8').readlines()]
        df = pd.DataFrame(signals)
        kline = get_kline(ts_code, end_dt=end_dt.strftime("%Y-%m-%d %H:%M:%S"), freq=freq, asset=asset)
        ka = KlineAnalyze(kline)
        print(kline.head(), "\n\n")
        xd = deepcopy(ka.xd)
        xd = sorted(xd, key=lambda row: row['dt'], reverse=False)
        print(xd, "\n\n")

        def ___xd_status(dt):
            for x in xd:
                if x['dt'] >= dt:
                    if x['fx_mark'] == 'd':
                        s = "向下段"
                    elif x['fx_mark'] == 'g':
                        s = "向上段"
                    else:
                        raise ValueError
                    return s
            return "o"

        col = f'{freq}线段状态'
        df[col] = df['交易时间'].apply(___xd_status)
        file_excel = "./data/%s_%s_%s_%s.xlsx" % (ts_code, start_date, end_date, freq)
        df.to_excel(file_excel, index=False)


if __name__ == '__main__':
    ts_code = "000001.SH"
    start_date = "2019-08-01"
    end_date = "2019-10-01"
    asset = 'I'

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    while start_date < end_date:
        start_date += timedelta(days=1)
        make_one_day(ts_code, start_date.strftime("%Y-%m-%d"), asset)

