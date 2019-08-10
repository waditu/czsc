# coding: utf-8

import sys
sys.path.insert(0, "..")

import os
from datetime import datetime
import pandas as pd
import chan
from tqdm import tqdm

shares = pd.read_excel(os.path.join(chan.cache_path, 'shares.xlsx'), sheets='pool')

today = datetime.now().date().__str__().replace("-", '')

chan.kline_viewer(ts_code='000001.SH', freq='5min', end_date=today, asset='I', show=True)


