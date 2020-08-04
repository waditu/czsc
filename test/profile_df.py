# coding: utf-8
import sys
import warnings
sys.path.insert(0, ".")
sys.path.insert(0, "..")
import czsc
warnings.warn("czsc version is {}".format(czsc.__version__))

from cobra.data.kline import get_kline
import pandas as pd
from czsc.analyze import KlineAnalyze
from datetime import datetime, timedelta
from contextlib import closing
from tqsdk import TqApi
from tqsdk.tools import DataDownloader


def use_large_df():
    symbol = "KQ.m@CZCE.MA"
    freq = '5min'

    file_csv = f"{symbol}_kline_{freq}.csv"
    start_dt = datetime(2017, 1, 1, 6, 0, 0)
    end_dt = datetime(2020, 5, 1, 6, 0, 0)
    freq_dur_sec = {"1min": 60, '5min': 300, '30min': 1800, 'D': 3600*24}
    freq_delta = {"1min": timedelta(days=20), '5min': timedelta(days=100),
                  '30min': timedelta(days=300), 'D': timedelta(days=3000)}

    api = TqApi()
    k = DataDownloader(api, symbol_list=symbol, dur_sec=freq_dur_sec[freq],
                       start_dt=start_dt-freq_delta[freq],
                       end_dt=end_dt, csv_file_name=file_csv)

    with closing(api):
        while not k.is_finished():
            api.wait_update()
            print("download progress: %.2f%%" % k.get_progress())

    kline = pd.read_csv(file_csv)
    kline.columns = [x.replace(symbol + ".", "") for x in kline.columns]
    kline.rename({"volume": "vol"}, axis=1, inplace=True)
    kline.loc[:, "symbol"] = symbol
    kline.loc[:, "dt"] = kline['datetime'].apply(lambda x: x.split(".")[0])
    kline = kline[['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']]
    print(kline.shape)
    ka = KlineAnalyze(kline)
    return ka


def convert_to_list_v1(df):
    rows = [x.to_dict() for _, x in df.iterrows()]
    return rows


def convert_to_list_v2(df):
    rows = df.to_dict("records")
    return rows


def convert_to_list_v3(df):
    columns = df.columns.to_list()
    rows = [{k: v for k, v in zip(columns, row)} for row in df.values]
    return rows


if __name__ == '__main__':
    df = get_kline(ts_code="000001.SH", end_dt="2020-04-28 15:00:00", freq='1min', asset='I')
    print(df.shape)
    convert_to_list_v1(df)
    convert_to_list_v2(df)
    ka = use_large_df()


