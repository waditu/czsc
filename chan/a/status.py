# coding:utf-8

from collections import OrderedDict
from chan import a
from chan.utils import kline_status

#
# def kline_status(ts_code, trade_date, freq='D', asset="I"):
#     kline = a.get_kline(ts_code, freq=freq, end_date=trade_date, asset=asset, indicators=('ma', 'macd'))
#
#     # MACD 多空状态
#     last_raw = kline.iloc[-1]
#     if last_raw['diff'] < 0 and last_raw['dea'] < 0:
#         macd_status = '空头行情'
#     elif last_raw['diff'] > 0 and last_raw['dea'] > 0:
#         macd_status = '多头行情'
#     else:
#         macd_status = '转折行情'
#
#     # 最近三根K线状态
#     pred = preprocess(kline)
#     last_three = pred.iloc[-3:]
#
#     # 笔状态：最近三根 K 线的走势状态
#     if min(last_three['low']) == last_three.iloc[-1]['low']:
#         bi_status = "向下笔延伸中"
#     elif min(last_three['low']) == last_three.iloc[-2]['low']:
#         bi_status = "底分型构造中"
#     elif max(last_three['high']) == last_three.iloc[-1]['high']:
#         bi_status = "向上笔延伸中"
#     elif max(last_three['high']) == last_three.iloc[-2]['high']:
#         bi_status = "顶分型构造中"
#     else:
#         raise ValueError("kline 数据出错")
#
#     return OrderedDict(macd_status=macd_status, bi_status=bi_status)
#


def _status(ts_code, trade_date, asset="I"):
    status = OrderedDict()
    status['上一交易日状态'] = a.daily_classifier(ts_code, trade_date, asset=asset)

    for freq in ['30min', 'D', 'W']:
        kline = a.get_kline(ts_code, freq=freq, end_date=trade_date, asset=asset, indicators=None)
        status[freq] = kline_status(kline)

    status_msg = '%s（%s） ：%s；' % (ts_code, trade_date, status['上一交易日状态'])
    status_msg += "30分钟线%s，MACD呈现%s；" % (status['30min']['bi_status'], status['30min']['macd_status'])
    status_msg += "日线%s，MACD呈现%s；" % (status['D']['bi_status'], status['D']['macd_status'])
    status_msg += "周线%s，MACD呈现%s；" % (status['W']['bi_status'], status['W']['macd_status'])

    return status, status_msg


def share_status(ts_code, trade_date):
    return _status(ts_code, trade_date, asset="E")


def index_status(ts_code, trade_date):
    return _status(ts_code, trade_date, asset="I")

