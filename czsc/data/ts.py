# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/6/25 18:52
"""
import time
import json
import requests
import pandas as pd
import tushare as ts
from deprecated import deprecated
from datetime import datetime
from typing import List
from functools import partial
from loguru import logger

from ..analyze import RawBar
from ..enum import Freq


# 数据频度 ：支持分钟(min)/日(D)/周(W)/月(M)K线，其中1min表示1分钟（类推1/5/15/30/60分钟）。
# 对于分钟数据有600积分用户可以试用（请求2次），正式权限请在QQ群私信群主或积分管理员。
freq_map = {Freq.F1: "1min", Freq.F5: '5min', Freq.F15: "15min", Freq.F30: '30min',
            Freq.F60: "60min", Freq.D: 'D', Freq.W: "W", Freq.M: "M"}
freq_cn_map = {"1分钟": Freq.F1, "5分钟": Freq.F5, "15分钟": Freq.F15, "30分钟": Freq.F30,
               "60分钟": Freq.F60, "日线": Freq.D}
exchanges = {
    "SSE": "上交所",
    "SZSE": "深交所",
    "CFFEX": "中金所",
    "SHFE": "上期所",
    "CZCE": "郑商所",
    "DCE": "大商所",
    "INE": "能源",
    "IB": "银行间",
    "XHKG": "港交所"
}

dt_fmt = "%Y-%m-%d %H:%M:%S"
date_fmt = "%Y%m%d"


class TushareProApi:
    __token = ''
    __http_url = 'http://api.waditu.com'

    def __init__(self, token, timeout=30):
        """
        Parameters
        ----------
        token: str
            API接口TOKEN，用于用户认证
        """
        self.__token = token
        self.__timeout = timeout

    def query(self, api_name, fields='', **kwargs):
        if api_name in ['__getstate__', '__setstate__']:
            return pd.DataFrame()

        req_params = {
            'api_name': api_name,
            'token': self.__token,
            'params': kwargs,
            'fields': fields
        }

        res = requests.post(self.__http_url, json=req_params, timeout=self.__timeout)
        if res:
            result = json.loads(res.text)
            if result['code'] != 0:
                logger.warning(f"{req_params}: {result}")
                raise Exception(result['msg'])

            data = result['data']
            columns = data['fields']
            items = data['items']
            return pd.DataFrame(items, columns=columns)
        else:
            return pd.DataFrame()

    def __getattr__(self, name):
        return partial(self.query, name)


try:
    from tushare.util import upass
    pro = TushareProApi(upass.get_token(), timeout=60)
except:
    print("Tushare Pro 初始化失败")


def format_kline(kline: pd.DataFrame, freq: Freq) -> List[RawBar]:
    """Tushare K线数据转换

    :param kline: Tushare 数据接口返回的K线数据
    :param freq: K线周期
    :return: 转换好的K线数据
    """
    bars = []
    dt_key = 'trade_time' if '分钟' in freq.value else 'trade_date'
    kline = kline.sort_values(dt_key, ascending=True, ignore_index=True)
    records = kline.to_dict('records')

    for i, record in enumerate(records):
        if freq == Freq.D:
            vol = int(record['vol']*100)
            amount = int(record.get('amount', 0)*1000)
        else:
            vol = int(record['vol'])
            amount = int(record.get('amount', 0))

        # 将每一根K线转换成 RawBar 对象
        bar = RawBar(symbol=record['ts_code'], dt=pd.to_datetime(record[dt_key]),
                     id=i, freq=freq, open=record['open'], close=record['close'],
                     high=record['high'], low=record['low'],
                     vol=vol,          # 成交量，单位：股
                     amount=amount,    # 成交额，单位：元
                     )
        bars.append(bar)
    return bars


@deprecated(reason="统一到 TsDataCache 对象中", version='0.9.0')
def get_kline(ts_code: str,
              start_date: [datetime, str],
              end_date: [datetime, str],
              asset: str = 'E',
              freq: Freq = Freq.F1,
              fq: str = "qfq") -> List[RawBar]:
    """
    通用行情接口: https://tushare.pro/document/2?doc_id=109

    :param ts_code:
    :param asset:
    :param freq:
    :param start_date:
    :param end_date:
    :param fq:
    :return:
    """
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    if "分钟" in freq.value:
        start_date = start_date.strftime(dt_fmt)
        end_date = end_date.strftime(dt_fmt)
    else:
        start_date = start_date.strftime(date_fmt)
        end_date = end_date.strftime(date_fmt)

    df = ts.pro_bar(ts_code=ts_code, adj=fq, asset=asset, freq=freq_map[freq],
                    start_date=start_date, end_date=end_date)
    bars = format_kline(df, freq)
    if bars and bars[-1].dt < pd.to_datetime(end_date) and len(bars) == 8000:
        print(f"获取K线数量达到8000根，数据获取到 {bars[-1].dt}，目标 end_date 为 {end_date}")
    return bars
