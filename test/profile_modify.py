# coding: utf-8

import os
import pandas as pd
from datetime import datetime

# cur_path = os.path.split(os.path.realpath(__file__))[0]
cur_path = "./test"
file_kline = os.path.join(cur_path, "data/000001.XSHG_1MIN.csv")
kline = pd.read_csv(file_kline, encoding="utf-8")
kline.loc[:, 'dt'] = pd.to_datetime(kline['dt'])
bars = kline.to_dict("records")
# bars = [{k: v for k, v in zip(kline.columns, row)} for row in kline.values]
bars_s = pd.Series(bars, index=[x['dt'] for x in bars])

# 测试用 Series 给 List 加索引的性能
start_dt = datetime.strptime('2020-07-01 10:31:00', "%Y-%m-%d %H:%M:%S")
end_dt = datetime.strptime('2020-07-01 14:31:00', "%Y-%m-%d %H:%M:%S")

# %timeit inside_k1 = [x for x in bars if end_dt >= x['dt'] >= start_dt]
# %timeit inside_k2 = bars_s[start_dt: end_dt]
#

