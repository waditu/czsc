from pytdx.hq import TdxHq_API
from collections import OrderedDict
import pandas as pd
import datetime as dt
from typing import List
from czsc.objects import RawBar

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
return_number = 50


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
            data_frame = self.api.to_df(data)
        return self.format_data(data_frame)

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

            data_frame = self.api.to_df(data)
        return self.format_data(original=data_frame)

    def format_data(self, original):
        # 重命名列头
        new_format_data = original.rename(
            columns={'vol': 'volume'}).sort_index()
        if new_format_data.size == 0:
            return new_format_data
        # # 字符串转日期
        new_format_data['datetime'] = new_format_data['datetime'].apply(
            lambda x: dt.datetime.strptime(x, '%Y-%m-%d %H:%M'))

        new_format_data['date'] = new_format_data['datetime'].apply(
            lambda x: x.date())
        new_format_data['index_time'] = new_format_data['datetime']
        new_format_data.set_index('index_time', inplace=True)

        return new_format_data

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
    print(t.get_data("300397", market=Market.SZ))
