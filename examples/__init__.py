# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/2/15 16:09
"""
import os
import pandas as pd
from czsc.data import TsDataCache

os.environ['czsc_verbose'] = "0"        # 是否输出详细执行信息，包括一些用于debug的信息，0 不输出，1 输出
os.environ['czsc_min_bi_len'] = "6"     # 通过环境变量设定最小笔长度，6 对应新笔定义，7 对应老笔定义

pd.set_option('mode.chained_assignment', None)
pd.set_option('display.max_rows', 1000)
pd.set_option('display.max_columns', 20)


# data_path 是 TS_CACHE 缓存数据文件夹所在目录
dc = TsDataCache(data_path=r"C:\ts_data_czsc", refresh=False, sdt="20120101", edt="20221001")


