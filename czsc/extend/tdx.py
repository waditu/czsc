from pytdx.hq import TdxHq_API
from collections import OrderedDict
import pandas as pd
import datetime as dt
from typing import List
from czsc.objects import RawBar
from czsc.data.jq import freq_map

api = TdxHq_API()


class Market():
    # 上海
    SH = 1
    # 深圳
    SZ = 0


def get_kline(symbol: str, end_date: [dt, str], freq: str,
              start_date: [dt, str] = None, count=None, fq: bool = True) -> List[RawBar]:
    pass


# 返回记录数量数
return_number = 600


class TdxStoreage():
    """
    通达信数据输出
    统一格式输出dataframe
    必须包含的列名 open  close  high low volume amount datetime date
    """

    def __init__(self):
        self.api = TdxHq_API()

    def __get_cal_data(self):
        request_per_item = 800
        if return_number < request_per_item:
            request_per_item = return_number

        scope = int(return_number / request_per_item)
        last_item_size = return_number % request_per_item
        if last_item_size > 0:
            scope += 1
        return scope, request_per_item, last_item_size

    def get_index_data(self, code, date_from, date_to=dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), market=Market.SZ,
                       freq: str = 'D'):
        """
        获取指数股票信息
        """
        with self.api.connect('119.147.212.81', 7709):
            data = []
            scope, request_per_item, last_item_size = self.__get_cal_data()

            for i in range(scope):
                count = request_per_item
                if i == scope - 1 and last_item_size != 0:
                    count = last_item_size
                data += self.api.get_index_bars(self._get_real_category(freq), market, code,
                                                (scope - 1 - i) * request_per_item,
                                                count)
        return self.format_data(data=data, code=code, freq=freq)

    def get_data(self, code, date_from='2021-01-01', date_to=dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                 market=Market.SZ,
                 freq: str = 'D'):
        """

        :param code:
        :param date_from:
        :param date_to:
        :param market:
        :param freq:  ['1min', '5min', '30min', '60min', 'D', 'W', 'M']
        :return:
        """
        with self.api.connect('119.147.212.81', 7709):
            data = []
            scope, request_per_item, last_item_size = self.__get_cal_data()
            for i in range(scope):
                count = request_per_item
                if i == scope - 1 and last_item_size != 0:
                    count = last_item_size
                data += self.api.get_security_bars(self._get_real_category(freq), market, code,
                                                   (scope - 1 - i) * request_per_item, count)
        return self.format_data(data=data, code=code, freq=freq)

    def format_data(self, data, freq, code):
        bars = []
        i = 0
        for row in data:
            current_dt = pd.to_datetime(row['datetime'])
            if freq == "D":
                current_dt = current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
            bars.append(RawBar(symbol=code, dt=current_dt, id=i, freq=freq_map[freq],
                               open=round(float(row['open']), 2),
                               close=round(float(row['close']), 2),
                               high=round(float(row['high']), 2),
                               low=round(float(row['low']), 2),
                               vol=int(row['vol'])))
            i = i + 1

        return bars

    def _get_real_category(self, category):
        real_category = 9
        if category == '1min':
            real_category = 7
        elif category == '5min':
            real_category = 0
        elif category == '15min':
            real_category = 1
        elif category == '30min':
            real_category = 2
        elif category == '60min':
            real_category = 3
        elif category == 'W':
            real_category = 5
        elif category == 'M':
            real_category = 6
        return real_category

    def close(self):
        pass


if __name__ == '__main__':
    t = TdxStoreage()
    return_number = 2
    item = t.get_data("300397", market=Market.SZ)
    print(item)
    a = 5
