import sys
sys.path.insert(0, '.')
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
import pandas as pd
import os
from czsc import RawBar, Freq, CZSC, welcome

welcome()


def read_daily():
    file_kline = os.path.join(r"D:\ZB\git_repo\waditu\czsc\test", "data/000001.SH_D.csv")
    kline = pd.read_csv(file_kline, encoding="utf-8")
    kline['amount'] = kline['close'] * kline['vol']

    kline.loc[:, "dt"] = pd.to_datetime(kline.dt)
    bars = [RawBar(symbol=row['symbol'], id=i, freq=Freq.D, open=row['open'], dt=row['dt'],
                   close=row['close'], high=row['high'], low=row['low'], vol=row['vol'], amount=row['amount'])
            for i, row in kline.iterrows()]
    return bars

bars = read_daily()
c = CZSC(bars)
# %timeit c = CZSC(bars)