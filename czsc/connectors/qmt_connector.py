# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2022/12/31 16:03
describe: QMT 量化交易平台接口
"""
import os
import time
import random
import czsc
import pandas as pd
from typing import List
from tqdm import tqdm
from loguru import logger
from datetime import datetime, timedelta
from czsc.objects import Freq, RawBar
from czsc.fsa.im import IM
from czsc.traders.base import CzscTrader
from czsc.utils import resample_bars
from xtquant import xtconstant
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount

dt_fmt = "%Y-%m-%d %H:%M:%S"


def format_stock_kline(kline: pd.DataFrame, freq: Freq) -> List[RawBar]:
    """QMT A股市场K线数据转换

    :param kline: QMT 数据接口返回的K线数据
                         time   open   high    low  close  volume      amount  \
        0 2022-12-01 10:15:00  13.22  13.22  13.16  13.18   20053  26432861.0
        1 2022-12-01 10:20:00  13.18  13.19  13.15  13.15   32667  43002512.0
        2 2022-12-01 10:25:00  13.16  13.18  13.13  13.16   32466  42708049.0
        3 2022-12-01 10:30:00  13.16  13.19  13.13  13.18   15606  20540461.0
        4 2022-12-01 10:35:00  13.20  13.25  13.19  13.22   29959  39626170.0
              symbol
        0  000001.SZ
        1  000001.SZ
        2  000001.SZ
        3  000001.SZ
        4  000001.SZ
    :param freq: K线周期
    :return: 转换好的K线数据
    """
    bars = []
    dt_key = 'time'
    kline = kline.sort_values(dt_key, ascending=True, ignore_index=True)
    records = kline.to_dict('records')

    for i, record in enumerate(records):
        # 将每一根K线转换成 RawBar 对象
        bar = RawBar(symbol=record['symbol'], dt=pd.to_datetime(record[dt_key]), id=i, freq=freq,
                     open=record['open'], close=record['close'], high=record['high'], low=record['low'],
                     vol=record['volume'] * 100 if record['volume'] else 0,  # 成交量，单位：股
                     amount=record['amount'] if record['amount'] > 0 else 0,  # 成交额，单位：元
                     )
        bars.append(bar)
    return bars


def get_kline(symbol, period, start_time, end_time, count=-1, dividend_type='front_ratio', **kwargs):
    """获取 QMT K线数据，实盘、回测通用

    :param symbol: 股票代码 例如：300001.SZ
    :param period: 周期 分笔"tick" 分钟线"1m"/"5m" 日线"1d"
    :param start_time: 开始时间
    :param end_time: 结束时间
    :param count: 数量 -1全部，n: 从结束时间向前数n个
    :param dividend_type: 除权类型"none" "front" "back" "front_ratio" "back_ratio"

    :return: df Dataframe格式的数据，样例如下
                         time   open   high    low  close  volume      amount  \
        0 2022-12-01 10:15:00  13.22  13.22  13.16  13.18   20053  26432861.0
        1 2022-12-01 10:20:00  13.18  13.19  13.15  13.15   32667  43002512.0
        2 2022-12-01 10:25:00  13.16  13.18  13.13  13.16   32466  42708049.0
        3 2022-12-01 10:30:00  13.16  13.19  13.13  13.18   15606  20540461.0
        4 2022-12-01 10:35:00  13.20  13.25  13.19  13.22   29959  39626170.0
              symbol
        0  000001.SZ
        1  000001.SZ
        2  000001.SZ
        3  000001.SZ
        4  000001.SZ
    """
    start_time = pd.to_datetime(start_time).strftime('%Y%m%d%H%M%S')
    if '1d' == period:
        end_time = pd.to_datetime(end_time).replace(hour=15, minute=0).strftime('%Y%m%d%H%M%S')
    else:
        end_time = pd.to_datetime(end_time).strftime('%Y%m%d%H%M%S')

    if kwargs.get("download_hist", True):
        xtdata.download_history_data(symbol, period=period, start_time=start_time, end_time=end_time)

    field_list = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
    data = xtdata.get_market_data(field_list, stock_list=[symbol], period=period, count=count,
                                  dividend_type=dividend_type, start_time=start_time,
                                  end_time=end_time, fill_data=kwargs.get("fill_data", False))

    df = pd.DataFrame({key: value.values[0] for key, value in data.items()})
    df['time'] = pd.to_datetime(df['time'], unit='ms') + pd.to_timedelta('8H')
    df.reset_index(inplace=True, drop=True)
    df['symbol'] = symbol
    df = df.dropna()

    if kwargs.get("df", True):
        return df
    else:
        freq_map = {"1m": Freq.F1, "5m": Freq.F5, "1d": Freq.D}
        return format_stock_kline(df, freq=freq_map[period])


def get_raw_bars(symbol, freq, sdt, edt, fq='前复权', **kwargs) -> List[RawBar]:
    """获取 CZSC 库定义的标准 RawBar 对象列表

    :param symbol: 标的代码
    :param freq: 周期
    :param sdt: 开始时间
    :param edt: 结束时间
    :param fq: 除权类型
    :param kwargs:
    :return:
    """
    freq = Freq(freq)
    if freq == Freq.F1:
        period = '1m'
    elif freq in [Freq.F5, Freq.F15, Freq.F30, Freq.F60]:
        period = '5m'
    else:
        period = '1d'

    if fq == '前复权':
        dividend_type = 'front_ratio'
    elif fq == '后复权':
        dividend_type = 'back_ratio'
    else:
        assert fq == '不复权'
        dividend_type = 'none'

    kline = get_kline(symbol, period, sdt, edt, dividend_type=dividend_type,
                      download_hist=kwargs.get("download_hist", True), df=True)
    if kline.empty:
        return []

    kline['dt'] = pd.to_datetime(kline['time'])
    kline['vol'] = kline['volume']
    bars = resample_bars(kline, freq, raw_bars=True)
    return bars


def get_symbols(step):
    """获取择时策略投研不同阶段对应的标的列表

    :param step: 投研阶段
    :return: 标的列表
    """
    stocks = xtdata.get_stock_list_in_sector('沪深A股')
    stocks_map = {
        "index": ['000905.SH', '000016.SH', '000300.SH', '000001.SH', '000852.SH',
                  '399001.SZ', '399006.SZ', '399376.SZ', '399377.SZ', '399317.SZ', '399303.SZ'],
        "stock": stocks,
        "check": ['000001.SZ'],
        "train": stocks[:200],
        "valid": stocks[200:600],
        "etfs": ['512880.SH', '518880.SH', '515880.SH', '513050.SH', '512690.SH',
                 '512660.SH', '512400.SH', '512010.SH', '512000.SH', '510900.SH',
                 '510300.SH', '510500.SH', '510050.SH', '159992.SZ', '159985.SZ',
                 '159981.SZ', '159949.SZ', '159915.SZ'],
    }
    if step.upper() == 'ALL':
        return stocks_map['index'] + stocks_map['stock'] + stocks_map['etfs']

    return stocks_map[step]


def is_trade_time(dt: datetime = datetime.now()):
    """判断指定时间是否是交易时间"""
    hm = dt.strftime("%H:%M")
    if hm < "09:15" or hm > "15:00":
        return False
    else:
        return True


def is_trade_day(dt: datetime = datetime.now()):
    """判断指定日期是否是交易日"""
    date = dt.strftime('%Y%m%d')
    return True if xtdata.get_trading_dates('SH', date, date) else False


class TraderCallback(XtQuantTraderCallback):
    """基础回调类，主要是一些日志和IM通知功能"""

    def __init__(self, **kwargs):
        super(TraderCallback, self).__init__()
        self.kwargs = kwargs

        if kwargs.get('feishu_app_id', None) and kwargs.get('feishu_app_secret', None):
            self.im = IM(app_id=kwargs['feishu_app_id'], app_secret=kwargs['feishu_app_secret'])
            self.members = kwargs['feishu_members']
        else:
            self.im = None
            self.members = None

        # 推送模式：detail-详细模式，summary-汇总模式
        self.feishu_push_mode = kwargs.get('feishu_push_mode', 'detail')

        file_log = kwargs.get('file_log', None)
        if file_log:
            logger.add(file_log, rotation='1 day', encoding='utf-8', enqueue=True)
        self.file_log = file_log
        logger.info(f"TraderCallback init: {kwargs}")

    def push_message(self, msg: str, msg_type='text'):
        """批量推送消息"""
        if self.im and self.members:
            for member in self.members:
                try:
                    if msg_type == 'text':
                        self.im.send_text(msg, member)
                    elif msg_type == 'image':
                        self.im.send_image(msg, member)
                    elif msg_type == 'file':
                        self.im.send_file(msg, member)
                    else:
                        logger.error(f"不支持的消息类型：{msg_type}")
                except Exception as e:
                    logger.error(f"推送消息失败：{e}")

    def on_disconnected(self):
        """连接断开"""
        logger.info("connection lost")
        if is_trade_time():
            self.push_message("连接断开")

    def on_stock_order(self, order):
        """委托回报推送

        :param order: XtOrder对象
            http://docs.thinktrader.net/pages/198696/#%E5%A7%94%E6%89%98xtorder
            http://docs.thinktrader.net/pages/198696/#%E5%A7%94%E6%89%98%E7%8A%B6%E6%80%81-order-status
        """
        order_status_map = {xtconstant.ORDER_UNREPORTED: '未报', xtconstant.ORDER_WAIT_REPORTING: '待报',
                            xtconstant.ORDER_REPORTED: '已报', xtconstant.ORDER_REPORTED_CANCEL: '已报待撤',
                            xtconstant.ORDER_PARTSUCC_CANCEL: '部成待撤', xtconstant.ORDER_PART_CANCEL: '部撤',
                            xtconstant.ORDER_CANCELED: '已撤', xtconstant.ORDER_PART_SUCC: '部成',
                            xtconstant.ORDER_SUCCEEDED: '已成', xtconstant.ORDER_JUNK: '废单',
                            xtconstant.ORDER_UNKNOWN: '未知',
                            }

        msg = f"委托回报通知：\n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户：{order.account_id}\n" \
              f"标的：{order.stock_code}\n" \
              f"方向：{'做多' if order.order_type == 23 else '平多'}\n" \
              f"数量：{int(order.order_volume)}\n" \
              f"价格：{order.price}\n" \
              f"状态：{order_status_map[order.order_status]}"
        logger.info(f"on order callback: {msg}")
        if self.feishu_push_mode == 'detail' and is_trade_time():
            self.push_message(msg, msg_type='text')

    def on_stock_asset(self, asset):
        """资金变动推送

        :param asset: XtAsset对象
        """
        msg = f"资金变动通知: \n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户: {asset.account_id} \n" \
              f"可用资金：{asset.cash} \n" \
              f"总资产：{asset.total_asset}"
        logger.info(f"on asset callback: {msg}")
        if self.feishu_push_mode == 'detail' and is_trade_time():
            self.push_message(msg, msg_type='text')

    def on_stock_trade(self, trade):
        """成交变动推送

        :param trade: XtTrade对象
        """
        msg = f"成交变动通知：\n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户：{trade.account_id}\n" \
              f"标的：{trade.stock_code}\n" \
              f"方向：{'开多' if trade.order_type == 23 else '平多'}\n" \
              f"成交量：{int(trade.traded_volume)}\n" \
              f"成交价：{round(trade.traded_price, 2)}"
        logger.info(f"on trade callback: {msg}")
        if self.feishu_push_mode == 'detail' and is_trade_time():
            self.push_message(msg, msg_type='text')

    def on_stock_position(self, position):
        """持仓变动推送

        :param position: XtPosition对象
        """
        msg = f"持仓变动通知: \n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户：{position.account_id}\n" \
              f"标的：{position.stock_code}\n" \
              f"成交量：{position.volume}"
        logger.info(f"on position callback: {msg}")
        if self.feishu_push_mode == 'detail' and is_trade_time():
            self.push_message(msg, msg_type='text')

    def on_order_error(self, order_error):
        """委托失败推送

        :param order_error:XtOrderError 对象
        """
        msg = f"委托失败通知: \n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户：{order_error.account_id}\n" \
              f"订单编号：{order_error.order_id}\n" \
              f"错误编码：{order_error.error_id}\n" \
              f"失败原因：{order_error.error_msg}"
        logger.info(f"on order_error callback: {msg}")
        if is_trade_time():
            self.push_message(msg, msg_type='text')

    def on_cancel_error(self, cancel_error):
        """撤单失败推送

        :param cancel_error: XtCancelError 对象
        """
        msg = f"撤单失败通知: \n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户：{cancel_error.account_id}\n" \
              f"订单编号：{cancel_error.order_id}\n" \
              f"错误编码：{cancel_error.error_id}\n" \
              f"失败原因：{cancel_error.error_msg}"
        logger.info(f"on_cancel_error: {msg}")
        if is_trade_time():
            self.push_message(msg, msg_type='text')

    def on_order_stock_async_response(self, response):
        """异步下单回报推送

        :param response: XtOrderResponse 对象
        """
        msg = f"异步下单回报推送: \n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户：{response.account_id}\n" \
              f"订单编号：{response.order_id}\n" \
              f"策略名称：{response.strategy_name}"
        if is_trade_time():
            self.push_message(msg, msg_type='text')
        logger.info(f"on_order_stock_async_response: {msg}")

    def on_account_status(self, status):
        """账户状态变化推送

        :param status: XtAccountStatus 对象
        """
        status_map = {xtconstant.ACCOUNT_STATUS_OK: '正常',
                      xtconstant.ACCOUNT_STATUS_WAITING_LOGIN: '连接中',
                      xtconstant.ACCOUNT_STATUSING: '登陆中',
                      xtconstant.ACCOUNT_STATUS_FAIL: '失败'}
        msg = f"账户状态变化推送：\n{'*' * 31}\n" \
              f"时间：{datetime.now().strftime(dt_fmt)}\n" \
              f"账户ID：{status.account_id}\n" \
              f"账号类型：{'证券账户' if status.account_type == 2 else '其他'}\n" \
              f"账户状态：{status_map[status.status]}\n"

        logger.info(f"账户ID: {status.account_id} "
                    f"账号类型：{'证券账户' if status.account_type == 2 else '其他'} "
                    f"账户状态：{status_map[status.status]}")

        if is_trade_time():
            self.push_message(msg, msg_type='text')


def query_stock_positions(xtt: XtQuantTrader, acc: StockAccount):
    """查询股票市场的持仓单

    http://docs.thinktrader.net/pages/ee0e9b/#%E6%8C%81%E4%BB%93%E6%9F%A5%E8%AF%A2
    http://docs.thinktrader.net/pages/198696/#%E6%8C%81%E4%BB%93xtposition
    """
    res = xtt.query_stock_positions(acc)
    res = {x.stock_code: x for x in res} if len(res) > 0 else {}
    return res


def query_today_trades(xtt: XtQuantTrader, acc: StockAccount):
    """查询当日成交

    http://docs.thinktrader.net/pages/198696/#%E6%88%90%E4%BA%A4xttrade
    """
    trades = xtt.query_stock_trades(acc)
    res = [{'品种': x.stock_code, '均价': x.traded_price, "方向": "买入" if x.order_type == 23 else "卖出",
            '数量': x.traded_volume, '金额': x.traded_amount,
            '时间': time.strftime("%H:%M:%S", time.localtime(x.traded_time))} for x in trades]
    return res


def cancel_timeout_orders(xtt: XtQuantTrader, acc: StockAccount, minutes=30):
    """撤销超时的委托单

    http://docs.thinktrader.net/pages/ee0e9b/#%E8%82%A1%E7%A5%A8%E5%90%8C%E6%AD%A5%E6%92%A4%E5%8D%95
    http://docs.thinktrader.net/pages/ee0e9b/#%E5%A7%94%E6%89%98%E6%9F%A5%E8%AF%A2
    http://docs.thinktrader.net/pages/198696/#%E5%A7%94%E6%89%98xtorder

    :param minutes: 超时时间，单位分钟
    :return:
    """
    orders = xtt.query_stock_orders(acc, cancelable_only=True)
    for o in orders:
        if datetime.fromtimestamp(o.order_time) < datetime.now() - timedelta(minutes=minutes):
            xtt.cancel_order_stock(acc, o.order_id)


def is_order_exist(xtt: XtQuantTrader, acc: StockAccount, symbol, order_type, volume=None):
    """判断是否存在相同的委托单

    http://docs.thinktrader.net/pages/ee0e9b/#%E8%82%A1%E7%A5%A8%E5%90%8C%E6%AD%A5%E6%92%A4%E5%8D%95
    http://docs.thinktrader.net/pages/ee0e9b/#%E5%A7%94%E6%89%98%E6%9F%A5%E8%AF%A2
    http://docs.thinktrader.net/pages/198696/#%E5%A7%94%E6%89%98xtorder

    """
    orders = xtt.query_stock_orders(acc, cancelable_only=False)
    for o in orders:
        if o.stock_code == symbol and o.order_type == order_type:
            if not volume or o.order_volume == volume:
                return True
    return False


def is_allow_open(xtt: XtQuantTrader, acc: StockAccount, symbol, price, **kwargs):
    """判断是否允许开仓

    http://docs.thinktrader.net/pages/198696/#%E8%B5%84%E4%BA%A7xtasset

    :param symbol: 股票代码
    :param price: 股票现价
    :return: True 允许开仓，False 不允许开仓
    """
    symbol_max_pos = kwargs.get('max_pos', 0)  # 最大持仓数量

    # 如果 symbol_max_pos 为 0，不允许开仓
    if symbol_max_pos <= 0:
        return False

    # 如果 symbol 在禁止交易的列表中，不允许开仓
    if symbol in kwargs.get('forbidden_symbols', []):
        return False

    # 如果 未成交的开仓委托单 存在，不允许开仓
    if is_order_exist(xtt, acc, symbol, order_type=23):
        logger.warning(f"存在未成交的开仓委托单，symbol={symbol}")
        return False

    # 如果已经有持仓，不允许开仓
    if query_stock_positions(xtt, acc).get(symbol, None):
        return False

    # 如果资金不足，不允许开仓
    assets = xtt.query_stock_asset(acc)
    if assets.cash < price * 120:
        logger.warning(f"资金不足，无法开仓，symbol={symbol}")
        return False

    return True


def is_allow_exit(xtt: XtQuantTrader, acc: StockAccount, symbol, **kwargs):
    """判断是否允许平仓

    :param symbol: 股票代码
    :return: True 允许开仓，False 不允许开仓
    """
    # symbol 在禁止交易的列表中，不允许平仓
    if symbol in kwargs.get('forbidden_symbols', []):
        return False

    # 没有持仓 或 可用数量为 0，不允许平仓
    pos = query_stock_positions(xtt, acc).get(symbol, None)
    if not pos or pos.can_use_volume <= 0:
        return False

    # 未成交的平仓委托单 存在，不允许继续平仓
    if is_order_exist(xtt, acc, symbol, order_type=24):
        logger.warning(f"存在未成交的平仓委托单，symbol={symbol}")
        return False

    return True


def send_stock_order(xtt: XtQuantTrader, acc: StockAccount, **kwargs):
    """股票市场交易下单

    股票同步报单 http://docs.thinktrader.net/pages/ee0e9b/#%E8%82%A1%E7%A5%A8%E5%90%8C%E6%AD%A5%E6%8A%A5%E5%8D%95
    委托类型(order_type) http://docs.thinktrader.net/pages/198696/#%E5%A7%94%E6%89%98%E7%B1%BB%E5%9E%8B-order-type
    报价类型(price_type) http://docs.thinktrader.net/pages/198696/#%E6%8A%A5%E4%BB%B7%E7%B1%BB%E5%9E%8B-price-type

    stock_code: 证券代码, 例如"600000.SH"
    order_type: 委托类型, 23:买, 24:卖
    order_volume: 委托数量, 股票以'股'为单位, 债券以'张'为单位，ETF以'份'为单位；数量必须是100的整数倍
    price_type: 报价类型, 详见帮助手册
        xtconstant.LATEST_PRICE	    5	最新价
        xtconstant.FIX_PRICE	    11	限价
    price: 报价价格, 如果price_type为限价, 那price为指定的价格, 否则填0
    strategy_name: 策略名称
    order_remark: 委托备注

    :return: 返回下单请求序号, 成功委托后的下单请求序号为大于0的正整数, 如果为-1表示委托失败
    """
    stock_code = kwargs.get('stock_code')
    order_type = kwargs.get('order_type')
    order_volume = kwargs.get('order_volume')  # 委托数量, 股票以'股'为单位, 债券以'张'为单位
    price_type = kwargs.get('price_type', 5)
    price = kwargs.get('price', 0)
    strategy_name = kwargs.get('strategy_name', "程序下单")
    order_remark = kwargs.get('order_remark', "程序下单")

    if not xtt.connected:
        xtt.start()
        xtt.connect()

    order_volume = max(order_volume // 100 * 100, 0)        # 股票市场只允许做多 100 的整数倍
    assert xtt.connected, "交易服务器连接断开"
    _id = xtt.order_stock(acc, stock_code, order_type, int(order_volume), price_type, price, strategy_name, order_remark)
    return _id


def order_stock_target(xtt: XtQuantTrader, acc: StockAccount, symbol, target, **kwargs):
    """下单调整至目标仓位

    :param xtt: XtQuantTrader, QMT 交易接口
    :param acc: StockAccount, 账户
    :param symbol: str, 股票代码
    :param target: int, 目标仓位, 单位：股；正数表示持有多头仓位，负数表示持有空头仓位
    :param kwargs: dict, 其他参数

        - price_type: int, 报价类型, 详见帮助手册
            xtconstant.LATEST_PRICE	    5	最新价
            xtconstant.FIX_PRICE	    11	限价
        - price: float, 报价价格, 如果price_type为限价, 那price为指定的价格, 否则填0

    :return:
    """
    # 查询持仓
    pos = query_stock_positions(xtt, acc).get(symbol, None)
    current = pos.volume if pos else 0

    logger.info(f"当前持仓：{current}，目标仓位：{target}")
    if current == target:
        return

    price_type = kwargs.get('price_type', 5)
    price = kwargs.get('price', 0)

    # 如果目标小于当前，平仓
    if target < current:
        delta = min(current - target, pos.can_use_volume if pos else current)
        logger.info(f"{symbol}平仓，目标仓位：{target}，当前仓位：{current}，平仓数量：{delta}")
        if delta != 0:
            send_stock_order(xtt, acc, stock_code=symbol, order_type=24,
                             order_volume=delta, price_type=price_type, price=price)
            return

    # 如果目标大于当前，开仓
    if target > current:
        delta = target - current
        logger.info(f"{symbol}开仓，目标仓位：{target}，当前仓位：{current}，开仓数量：{delta}")
        if delta != 0:
            send_stock_order(xtt, acc, stock_code=symbol, order_type=23,
                             order_volume=delta, price_type=price_type, price=price)
            return


class QmtTradeManager:
    """QMT交易管理器（这是一个案例性质的存在，真正实盘的时候请参考这个，根据自己的逻辑重新实现）

    功能特性：

    1. 支持全市场品种定时交易
    2. 所有交易对象持久化，程序重启后自动恢复
    3. 仅支持股票交易
    4. 仅在仓位发生变化时进行交易

    """

    def __init__(self, mini_qmt_dir, account_id, **kwargs):
        """

        :param mini_qmt_dir: mini QMT 路径；如 D:\\国金QMT交易端模拟\\userdata_mini
        :param account_id: 账户ID
        :param kwargs:

        """
        self.cache_path = kwargs['cache_path']  # 交易缓存路径
        os.makedirs(self.cache_path, exist_ok=True)
        self.symbols = kwargs.get('symbols', [])  # 交易标的列表
        self.strategy = kwargs.get('strategy', [])  # 交易策略
        assert issubclass(self.strategy, czsc.CzscStrategyBase), "交易策略必须是CzscStrategyBase的子类"

        self.symbol_max_pos = kwargs.get('symbol_max_pos', 0.5)  # 每个标的最大持仓比例
        self.trade_sdt = kwargs.get('trade_sdt', '20220601')  # 交易跟踪开始日期
        self.mini_qmt_dir = mini_qmt_dir
        self.account_id = account_id
        self.base_freq = self.strategy(symbol='symbol').sorted_freqs[0]
        self.delta_days = int(kwargs.get('delta_days', 1))  # 定时执行获取的K线天数
        self.forbidden_symbols = kwargs.get('forbidden_symbols', [])  # 禁止交易的品种列表

        self.session = random.randint(10000, 20000)
        self.callback = TraderCallback(**kwargs.get('callback_params', {}))
        self.xtt = XtQuantTrader(mini_qmt_dir, session=self.session, callback=self.callback)
        self.acc = StockAccount(account_id, 'STOCK')
        self.xtt.start()
        self.xtt.connect()
        assert self.xtt.connected, "交易服务器连接失败"
        _res = self.xtt.subscribe(self.acc)
        assert _res == 0, "账号订阅失败"
        self.traders = self.__create_traders(**kwargs)

    def __create_traders(self, **kwargs):
        """创建交易策略"""
        traders = {}
        for symbol in tqdm(self.symbols, desc="创建交易对象", unit="个"):
            if symbol in self.forbidden_symbols:
                continue

            file_trader = os.path.join(self.cache_path, f"{symbol}.ct")
            try:
                if os.path.exists(file_trader):
                    # 从缓存文件中恢复交易对象，并更新K线数据
                    trader: CzscTrader = czsc.dill_load(file_trader)
                    kline_sdt = pd.to_datetime(trader.end_dt) - timedelta(days=self.delta_days)
                    bars = get_raw_bars(symbol, self.base_freq, kline_sdt, datetime.now(), fq="前复权",
                                        download_hist=True)
                    news = [x for x in bars if x.dt > trader.end_dt]
                    if news:
                        logger.info(f"{symbol} 需要更新的K线数量：{len(news)} | 最新的K线时间是 {news[-1].dt}")
                        for bar in news:
                            trader.on_bar(bar)

                else:
                    # 从头创建交易对象
                    bars = get_raw_bars(symbol, self.base_freq, '20180101', datetime.now(), fq="前复权")
                    trader: CzscTrader = self.strategy(symbol=symbol).init_trader(bars, sdt=self.trade_sdt)
                    czsc.dill_dump(trader, file_trader)

                mean_pos = trader.get_ensemble_pos('mean')
                if mean_pos == 0:
                    continue

                traders[symbol] = trader
                pos_info = {x.name: x.pos for x in trader.positions if x.pos != 0}
                logger.info(f"最新时间：{trader.end_dt}；{symbol} trader pos：{pos_info} | mean_pos: {mean_pos}")
            except Exception as e:
                logger.exception(f'创建交易对象失败，symbol={symbol}, e={e}')

        return traders

    def get_assets(self):
        """获取账户资产"""
        return self.xtt.query_stock_asset(self.acc)

    def query_stock_orders(self, cancelable_only=False):
        """查询股票市场的委托单

        http://docs.thinktrader.net/pages/ee0e9b/#%E5%A7%94%E6%89%98%E6%9F%A5%E8%AF%A2

        :param cancelable_only:
        :return:
        """
        return self.xtt.query_stock_orders(self.acc, cancelable_only)

    def query_today_trades(self):
        """查询当日成交"""
        # http://docs.thinktrader.net/pages/198696/#%E6%88%90%E4%BA%A4xttrade
        trades = self.xtt.query_stock_trades(self.acc)
        res = [{'品种': x.stock_code, '均价': x.traded_price, "方向": "买入" if x.order_type == 23 else "卖出",
                '数量': x.traded_volume, '金额': x.traded_amount,
                '时间': time.strftime("%H:%M:%S", time.localtime(x.traded_time))}
               for x in trades]
        return res

    def cancel_timeout_orders(self, minutes=30):
        """撤销超时的委托单

        :param minutes: 超时时间，单位分钟
        :return:
        """
        orders = self.query_stock_orders(cancelable_only=True)
        for o in orders:
            if datetime.fromtimestamp(o.order_time) < datetime.now() - timedelta(minutes=minutes):
                self.xtt.cancel_order_stock(self.acc, o.order_id)

    def is_order_exist(self, symbol, order_type, volume=None):
        """判断是否存在相同的委托单"""
        orders = self.query_stock_orders(cancelable_only=True)
        for o in orders:
            if o.stock_code == symbol and o.order_type == order_type:
                if not volume or o.order_volume == volume:
                    return True
        return False

    def is_allow_open(self, symbol, price):
        """判断是否允许开仓

        :param symbol: 股票代码
        :param price: 股票现价
        :return: True 允许开仓，False 不允许开仓
        """
        # 如果 symbol 在禁止交易的列表中，不允许开仓
        if symbol in self.forbidden_symbols:
            return False

        # 如果 未成交的开仓委托单 存在，不允许开仓
        if self.is_order_exist(symbol, order_type=23):
            logger.warning(f"存在未成交的开仓委托单，symbol={symbol}")
            return False

        # 如果 symbol_max_pos 为 0，不允许开仓
        if self.symbol_max_pos <= 0:
            return False

        # 如果已经有持仓，不允许开仓
        if self.query_stock_positions().get(symbol, None):
            return False

        # 如果资金不足，不允许开仓
        assets = self.get_assets()
        if assets.cash < price * 120:
            logger.warning(f"资金不足，无法开仓，symbol={symbol}")
            return False

        return True

    def is_allow_exit(self, symbol):
        """判断是否允许平仓

        :param symbol: 股票代码
        :return: True 允许开仓，False 不允许开仓
        """
        # symbol 在禁止交易的列表中，不允许平仓
        if symbol in self.forbidden_symbols:
            return False

        # 没有持仓，不允许平仓
        pos = self.query_stock_positions().get(symbol)
        if not pos:
            return False

        # 未成交的平仓委托单 存在，不允许平仓
        if self.is_order_exist(symbol, order_type=24):
            logger.warning(f"存在未成交的平仓委托单，symbol={symbol}")
            return False

        # 持仓可用数量为 0，不允许平仓
        if pos.can_use_volume <= 0:
            return False

        return True

    def query_stock_positions(self):
        """查询股票市场的持仓单

        http://docs.thinktrader.net/pages/ee0e9b/#%E6%8C%81%E4%BB%93%E6%9F%A5%E8%AF%A2
        """
        res = self.xtt.query_stock_positions(self.acc)
        if len(res) > 0:
            res = {x.stock_code: x for x in res}
        else:
            res = {}
        return res

    def send_stock_order(self, **kwargs):
        """股票市场交易下单

        http://docs.thinktrader.net/pages/ee0e9b/#%E8%82%A1%E7%A5%A8%E5%90%8C%E6%AD%A5%E6%8A%A5%E5%8D%95
        http://docs.thinktrader.net/pages/198696/#%E6%8A%A5%E4%BB%B7%E7%B1%BB%E5%9E%8B-price-type

        stock_code: 证券代码, 例如"600000.SH"
        order_type: 委托类型, 23:买, 24:卖
        order_volume: 委托数量, 股票以'股'为单位, 债券以'张'为单位
        price_type: 报价类型, 详见帮助手册
            xtconstant.LATEST_PRICE	5	最新价
            xtconstant.FIX_PRICE	11	限价
        price: 报价价格, 如果price_type为限价, 那price为指定的价格, 否则填0
        strategy_name: 策略名称
        order_remark: 委托备注

        :return: 返回下单请求序号, 成功委托后的下单请求序号为大于0的正整数, 如果为-1表示委托失败
        """
        stock_code = kwargs.get('stock_code')
        order_type = kwargs.get('order_type')
        order_volume = kwargs.get('order_volume')  # 委托数量, 股票以'股'为单位, 债券以'张'为单位
        price_type = kwargs.get('price_type', xtconstant.LATEST_PRICE)
        price = kwargs.get('price', 0)
        strategy_name = kwargs.get('strategy_name', "程序下单")
        order_remark = kwargs.get('order_remark', "程序下单")

        if not self.xtt.connected:
            self.xtt.connect()
            self.xtt.start()

        if order_volume % 100 != 0:
            order_volume = order_volume // 100 * 100

        assert self.xtt.connected, "交易服务器连接断开"
        _id = self.xtt.order_stock(self.acc, stock_code, order_type, int(order_volume),
                                   price_type, price, strategy_name, order_remark)
        return _id

    def update_traders(self):
        """更新交易策略"""
        holds = self.query_stock_positions()
        kline_sdt = datetime.now() - timedelta(days=self.delta_days)

        for symbol in self.traders.keys():
            try:
                trader = self.traders[symbol]
                bars = get_raw_bars(symbol, self.base_freq, kline_sdt, datetime.now(), fq="前复权", download_hist=True)

                news = [x for x in bars if x.dt > trader.end_dt]
                if news:
                    logger.info(f"{symbol} 需要更新的K线数量：{len(news)} | 最新的K线时间是 {news[-1].dt}")
                    for bar in news:
                        trader.on_bar(bar)

                        # 根据策略的交易信号，下单【股票只有多头】，只有当信号变化时才下单
                        if trader.get_ensemble_pos(method='vote') == 1 and trader.pos_changed \
                                and self.is_allow_open(symbol, price=news[-1].close):
                            assets = self.get_assets()
                            order_volume = min(self.symbol_max_pos * assets.total_asset, assets.cash) // news[-1].close
                            self.send_stock_order(stock_code=symbol, order_type=23, order_volume=order_volume)

                        # 平多头
                        if trader.get_ensemble_pos(method='vote') == 0 and self.is_allow_exit(symbol):
                            order_volume = holds[symbol].can_use_volume
                            self.send_stock_order(stock_code=symbol, order_type=24, order_volume=order_volume)

                else:
                    logger.info(f"{symbol} 没有需要更新的K线，最新的K线时间是 {trader.end_dt}")

                if trader.get_ensemble_pos('mean') > 0:
                    pos_info = {x.name: x.pos for x in trader.positions if x.pos != 0}
                    logger.info(
                        f"{trader.end_dt} {symbol} trader pos：{pos_info} | ensemble_pos: {trader.get_ensemble_pos('mean')}")

                # 更新交易对象
                self.traders[symbol] = trader

            except Exception as e:
                self.callback.push_message(f"{symbol} 更新交易策略失败，原因是 {e}")
                logger.error(f"{symbol} 更新交易策略失败，原因是 {e}")

    def update_offline_traders(self):
        """更新全部品种策略"""
        traders = {}
        kline_sdt = datetime.now() - timedelta(days=self.delta_days)

        for symbol in tqdm(self.symbols, desc="更新全部股票", unit="个"):
            if symbol in self.forbidden_symbols:
                continue

            file_trader = os.path.join(self.cache_path, f"{symbol}.ct")
            if not os.path.exists(file_trader):
                logger.error(f"{symbol} 交易对象不存在，无法更新")
                continue

            try:
                bars = get_raw_bars(symbol, self.base_freq, kline_sdt, datetime.now(), fq="前复权", download_hist=True)
                trader: CzscTrader = czsc.dill_load(file_trader)
                news = [x for x in bars if x.dt > trader.end_dt]
                if news:
                    logger.info(f"{symbol} 需要更新的K线数量：{len(news)} | 最新的K线时间是 {news[-1].dt}")
                    for bar in news:
                        trader.on_bar(bar)

                        # 根据策略的交易信号，下单【股票只有多头】，只有当信号变化时才下单
                        if trader.get_ensemble_pos(method='vote') == 1 and trader.pos_changed \
                                and self.is_allow_open(symbol, price=news[-1].close):
                            assets = self.get_assets()
                            order_volume = min(self.symbol_max_pos * assets.total_asset, assets.cash) // news[-1].close
                            self.send_stock_order(stock_code=symbol, order_type=23, order_volume=order_volume)

                    czsc.dill_dump(trader, file_trader)

                mean_pos = trader.get_ensemble_pos('mean')
                if mean_pos == 0:
                    continue

                traders[symbol] = trader
                pos_info = {x.name: x.pos for x in trader.positions if x.pos != 0}
                logger.info(f"最新时间：{trader.end_dt}；{symbol} trader pos：{pos_info} | mean_pos: {mean_pos}")
            except Exception as e:
                logger.exception(f'创建交易对象失败，symbol={symbol}, e={e}')

        self.traders = traders

    def report(self):
        """报告状态"""
        from czsc.utils import WordWriter

        writer = WordWriter()
        writer.add_title("QMT 交易报告")
        assets = self.get_assets()

        writer.add_heading('一、账户状态', level=1)
        writer.add_paragraph(f"交易品种数量：{len(self.traders)}\n"
                             f"传入品种数量：{len(self.symbols)}\n"
                             f"交易账户：{self.account_id}\n"
                             f"账户资产：{assets.total_asset}\n"
                             f"可用资金：{assets.cash}\n"
                             f"持仓市值：{assets.market_value}\n"
                             f"持仓情况：", first_line_indent=0)

        sp = self.query_stock_positions()
        if sp:
            _res_sp = []
            for k, v in sp.items():
                is_auto = "程序" if k in self.traders.keys() else "人工"
                _res_sp.append({'品种': k, '持仓股数': v.volume, '可用股数': v.can_use_volume,
                                '成本': v.open_price, '市值': int(v.market_value), '操盘手': is_auto})
            writer.add_df_table(pd.DataFrame(_res_sp))
        else:
            writer.add_paragraph("当前没有持仓", first_line_indent=0)

        # 当日成交
        trades = self.query_today_trades()
        writer.add_paragraph(f"当日成交：", first_line_indent=0)
        if trades:
            writer.add_df_table(pd.DataFrame(trades))
        else:
            writer.add_paragraph("当日没有成交", first_line_indent=0)

        writer.add_heading('二、策略状态', level=1)

        _res = []
        for symbol, trader in self.traders.items():
            if trader.get_ensemble_pos('mean') > 0:
                _pos_str = "\n\n".join([f"{x.name}：{x.pos}" for x in trader.positions if x.pos != 0])
                _ops = [x.operates[-1] for x in trader.positions if x.pos != 0]
                _ops_str = "\n\n".join([f"时间：{x['dt']}_价格：{x['price']}_描述：{x['op_desc']}" for x in _ops])
                _res.append({'symbol': symbol, 'pos': round(trader.get_ensemble_pos('mean'), 3),
                             'positions': _pos_str, 'operates': _ops_str})
        if _res:
            writer.add_df_table(pd.DataFrame(_res).sort_values(by='pos', ascending=False))
        else:
            writer.add_paragraph("当前所有品种都是空仓")

        file_docx = f"QMT{self.account_id}_交易报告_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"
        writer.save(file_docx)
        self.callback.push_message(file_docx, msg_type='file')
        os.remove(file_docx)

    def run(self, mode='30m', order_timeout=120):
        """运行策略"""
        self.report()

        if mode.lower() == '15m':
            _times = ["09:45", "10:00", "10:15", "10:30", "10:45", "11:00", "11:15", "11:30",
                      "13:15", "13:30", "13:45", "14:00", "14:15", "14:30", "14:45", "15:00"]
        elif mode.lower() == '30m':
            _times = ["09:45", "10:00", "10:30", "11:00", "11:30", "13:30", "14:00", "14:30", "15:00"]
        elif mode.lower() == '60m':
            _times = ["10:30", "11:30", "13:45", "14:30"]
        else:
            raise ValueError("mode 只能是 15m, 30m, 60m")

        while 1:
            now_dt = datetime.now().strftime("%H:%M")
            self.cancel_timeout_orders(minutes=order_timeout)

            if is_trade_day() and now_dt in _times:
                self.update_traders()
                self.report()
                time.sleep(60)
            else:
                time.sleep(3)

            # 如果断开，重新连接交易服务器
            if not self.xtt.connected:
                self.xtt.connect()
                self.xtt.start()

            if now_dt in ["11:35", "14:05", "15:05"]:
                self.callback.push_message(f"{self.account_id} 开始更新离线交易员对象", msg_type='text')
                self.update_offline_traders()
                self.report()


# ======================================================================================================================
# 以下是测试代码
# ======================================================================================================================

def test_get_kline():
    # 获取所有板块
    slt = xtdata.get_sector_list()
    stocks = xtdata.get_stock_list_in_sector('沪深A股')

    df = get_kline(symbol='000001.SZ', period='1m', count=1000, dividend_type='front',
                   start_time='20200427', end_time='20221231')
    assert not df.empty
    df = get_kline(symbol='000001.SZ', period='5m', count=1000, dividend_type='front',
                   start_time='20200427', end_time='20221231')
    assert not df.empty
    df = get_kline(symbol='000001.SZ', period='1d', count=1000, dividend_type='front',
                   start_time='20200427', end_time='20221231')
    assert not df.empty


def test_get_symbols():
    symbols = get_symbols('index')
    assert len(symbols) > 0
    symbols = get_symbols('stock')
    assert len(symbols) > 0
    symbols = get_symbols('check')
    assert len(symbols) > 0
    symbols = get_symbols('train')
    assert len(symbols) > 0
    symbols = get_symbols('valid')
    assert len(symbols) > 0
    symbols = get_symbols('etfs')
    assert len(symbols) > 0
