# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:11
describe: 配合 CzscAdvancedTrader 进行使用的掘金工具
"""
import os
import dill
import inspect
import traceback
from gm.api import *
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
import pandas as pd
from typing import List, Callable
from czsc.traders import CzscAdvancedTrader
from czsc.utils import BarGenerator
from czsc.utils import qywx as wx
from czsc.objects import RawBar, Event, Freq, Operate, PositionLong
from czsc.utils.log import create_logger
from czsc.signals.signals import get_default_signals

dt_fmt = "%Y-%m-%d %H:%M:%S"
date_fmt = "%Y-%m-%d"


def set_gm_token(token):
    with open(os.path.join(os.path.expanduser("~"), "gm_token.txt"), 'w', encoding='utf-8') as f:
        f.write(token)


file_token = os.path.join(os.path.expanduser("~"), "gm_token.txt")
if not os.path.exists(file_token):
    print("{} 文件不存在，请单独启动一个 python 终端，调用 set_gm_token 方法创建该文件，再重新执行。".format(file_token))
else:
    gm_token = open(file_token, encoding="utf-8").read()
    set_token(gm_token)

freq_map = {"60s": "1分钟", "300s": "5分钟", "900s": "15分钟",
            "1800s": "30分钟", "3600s": "60分钟", "1d": "日线"}
freq_map_inv = {v: k for k, v in freq_map.items()}

indices = {
    "上证指数": 'SHSE.000001',
    "上证50": 'SHSE.000016',
    "沪深300": "SHSE.000300",
    "中证1000": "SHSE.000852",

    "深证成指": "SZSE.399001",
    "创业板指数": 'SZSE.399006',
    "深次新股": "SZSE.399678",
    "中小板指": "SZSE.399005",
    "中证500": "SZSE.399905",
    "国证2000": "SZSE.399303",
    "小盘成长": "SZSE.399376",
    "小盘价值": "SZSE.399377",
}


def get_stocks():
    """获取股票市场标的列表，包括股票、指数等"""
    df = get_instruments(exchanges='SZSE,SHSE', fields="symbol,sec_name", df=True)
    shares = {row['symbol']: row['sec_name'] for _, row in df.iterrows()}
    return shares


def get_index_shares(name, end_date=None):
    """获取某一交易日的指数成分股列表

    symbols = get_index_shares("上证50", "2019-01-01 09:30:00")
    """
    if not end_date:
        end_date = datetime.now().strftime(date_fmt)
    else:
        end_date = pd.to_datetime(end_date).strftime(date_fmt)
    constituents = get_history_constituents(indices[name], end_date, end_date)[0]
    symbol_list = [k for k, v in constituents['constituents'].items()]
    return list(set(symbol_list))


# ======================================================================================================================
# 行情数据获取
# ======================================================================================================================
def format_kline(df, freq: Freq):
    bars = []
    for i, row in df.iterrows():
        bar = RawBar(symbol=row['symbol'], id=i, freq=freq, dt=row['eob'], open=round(row['open'], 2),
                     close=round(row['close'], 2), high=round(row['high'], 2),
                     low=round(row['low'], 2), vol=row['volume'])
        bars.append(bar)
    return bars


def get_kline(symbol, end_time, freq='60s', count=33000, adjust=ADJUST_PREV):
    """获取K线数据

    :param symbol: 标的代码
    :param end_time: 结束时间
    :param freq: K线周期
    :param count: K线数量
    :param adjust: 复权方式
    :return:
    """
    if isinstance(end_time, datetime):
        end_time = end_time.strftime(dt_fmt)

    exchange = symbol.split(".")[0]
    freq_map_ = {'60s': Freq.F1, '300s': Freq.F5, '900s': Freq.F15, '1800s': Freq.F30,
                 '3600s': Freq.F60, '1d': Freq.D}

    if exchange in ["SZSE", "SHSE"]:
        df = history_n(symbol=symbol, frequency=freq, end_time=end_time, adjust=adjust,
                       fields='symbol,eob,open,close,high,low,volume', count=count, df=True)
    else:
        df = history_n(symbol=symbol, frequency=freq, end_time=end_time, adjust=adjust,
                       fields='symbol,eob,open,close,high,low,volume,position', count=count, df=True)
    return format_kline(df, freq_map_[freq])


# ======================================================================================================================
# 实盘&仿真&回测共用函数
# ======================================================================================================================
def get_init_bg(symbol: str,
                end_dt: [str, datetime],
                base_freq: str,
                freqs: List[str],
                max_count=1000,
                adjust=ADJUST_PREV):
    """获取 symbol 的初始化 bar generator"""
    if isinstance(end_dt, str):
        end_dt = pd.to_datetime(end_dt, utc=True)
        end_dt = end_dt.tz_convert('dateutil/PRC')
        # 时区转换之后，要减去8个小时才是设置的时间
        end_dt = end_dt - timedelta(hours=8)
    else:
        assert end_dt.tzinfo._filename == 'PRC'
    last_day = (end_dt - timedelta(days=1)).replace(hour=16, minute=0)

    bg = BarGenerator(base_freq, freqs, max_count)
    if "周线" in freqs or "月线" in freqs:
        d_bars = get_kline(symbol=symbol, end_time=last_day, freq=freq_map_inv["日线"], count=5000, adjust=adjust)
        bgd = BarGenerator("日线", ['周线', '月线', '季线', '年线'])
        for b in d_bars:
            bgd.update(b)
    else:
        bgd = None

    for freq in bg.bars.keys():
        if freq in ['周线', '月线', '季线', '年线']:
            bars_ = bgd.bars[freq]
        else:
            bars_ = get_kline(symbol=symbol, end_time=last_day, freq=freq_map_inv[freq], count=max_count, adjust=adjust)
        bg.bars[freq] = bars_
        print(f"{symbol} - {freq} - {len(bg.bars[freq])} - last_dt: {bg.bars[freq][-1].dt} - last_day: {last_day}")

    bars2 = get_kline(symbol=symbol, end_time=end_dt, freq=freq_map_inv[base_freq], count=300)
    data = [x for x in bars2 if x.dt > last_day]

    if data:
        print(f"{symbol}: 更新 bar generator 至 {end_dt.strftime(dt_fmt)}，共有{len(data)}行数据需要update")
        for row in data:
            bg.update(row)
    return bg


# ======================================================================================================================
# 掘金系统回调函数
# ======================================================================================================================

order_side_map = {OrderSide_Unknown: '其他', OrderSide_Buy: '买入', OrderSide_Sell: '卖出'}
order_status_map = {
    OrderStatus_Unknown: "其他",
    OrderStatus_New: "已报",
    OrderStatus_PartiallyFilled: "部成",
    OrderStatus_Filled: "已成",
    OrderStatus_Canceled: "已撤",
    OrderStatus_PendingCancel: "待撤",
    OrderStatus_Rejected: "已拒绝",
    OrderStatus_Suspended: "挂起（无效）",
    OrderStatus_PendingNew: "待报",
    OrderStatus_Expired: "已过期",
}
pos_side_map = {PositionSide_Unknown: '其他', PositionSide_Long: '多头', PositionSide_Short: '空头'}
pos_effect_map = {
    PositionEffect_Unknown: '其他',
    PositionEffect_Open: '开仓',
    PositionEffect_Close: '平仓',
    PositionEffect_CloseToday: '平今仓',
    PositionEffect_CloseYesterday: '平昨仓',
}
exec_type_map = {
    ExecType_Unknown: "其他",
    ExecType_New: "已报",
    ExecType_Canceled: "已撤销",
    ExecType_PendingCancel: "待撤销",
    ExecType_Rejected: "已拒绝",
    ExecType_Suspended: "挂起",
    ExecType_PendingNew: "待报",
    ExecType_Expired: "过期",
    ExecType_Trade: "成交(有效)",
    ExecType_OrderStatus: "委托状态",
    ExecType_CancelRejected: "撤单被拒绝(有效)",
}


def on_order_status(context, order):
    """
    https://www.myquant.cn/docs/python/python_object_trade#007ae8f5c7ec5298

    :param context:
    :param order:
    :return:
    """
    if context.now.isoweekday() > 5 or context.now.hour not in [9, 10, 11, 13, 14]:
        # print(f"on_order_status: {context.now} 不是交易时间")
        return

    symbol = order.symbol
    latest_dt = context.now.strftime("%Y-%m-%d %H:%M:%S")
    logger = context.logger

    if symbol not in context.symbols_info.keys():
        msg = f"订单状态更新通知：\n{'*' * 31}\n" \
              f"更新时间：{latest_dt}\n" \
              f"标的名称：{symbol} {context.stocks.get(symbol, '无名')}\n" \
              f"操作类型：{order_side_map[order.side]}{pos_effect_map[order.position_effect]}\n" \
              f"操作描述：非机器交易标的\n" \
              f"下单价格：{round(order.price, 2)}\n" \
              f"最新状态：{order_status_map[order.status]}\n" \
              f"委托（股）：{int(order.volume)}\n" \
              f"已成（股）：{int(order.filled_volume)}\n" \
              f"均价（元）：{round(order.filled_vwap, 2)}"

    else:
        trader: GmCzscTrader = context.symbols_info[symbol]['trader']
        if trader.long_pos.operates:
            last_op_desc = trader.long_pos.operates[-1]['op_desc']
        else:
            last_op_desc = ""

        msg = f"订单状态更新通知：\n{'*' * 31}\n" \
              f"更新时间：{latest_dt}\n" \
              f"标的名称：{symbol} {context.stocks.get(symbol, '无名')}\n" \
              f"操作类型：{order_side_map[order.side]}{pos_effect_map[order.position_effect]}\n" \
              f"操作描述：{last_op_desc}\n" \
              f"下单价格：{round(order.price, 2)}\n" \
              f"最新状态：{order_status_map[order.status]}\n" \
              f"委托（股）：{int(order.volume)}\n" \
              f"已成（股）：{int(order.filled_volume)}\n" \
              f"均价（元）：{round(order.filled_vwap, 2)}"

    logger.info(msg.replace("\n", " - ").replace('*', ""))
    if context.mode != MODE_BACKTEST and order.status in [1, 3, 5, 8, 9, 12]:
        wx.push_text(content=str(msg), key=context.wx_key)


def on_execution_report(context, execrpt):
    """响应委托被执行事件，委托成交或者撤单拒绝后被触发。

    https://www.myquant.cn/docs/python/python_trade_event#on_execution_report%20-%20%E5%A7%94%E6%89%98%E6%89%A7%E8%A1%8C%E5%9B%9E%E6%8A%A5%E4%BA%8B%E4%BB%B6
    https://www.myquant.cn/docs/python/python_object_trade#ExecRpt%20-%20%E5%9B%9E%E6%8A%A5%E5%AF%B9%E8%B1%A1

    :param context:
    :param execrpt:
    :return:
    """
    if context.now.isoweekday() > 5 or context.now.hour not in [9, 10, 11, 13, 14]:
        # print(f"on_execution_report: {context.now} 不是交易时间")
        return

    latest_dt = context.now.strftime(dt_fmt)
    logger = context.logger
    msg = f"委托订单被执行通知：\n{'*' * 31}\n" \
          f"时间：{latest_dt}\n" \
          f"标的：{execrpt.symbol}\n" \
          f"名称：{context.stocks.get(execrpt.symbol, '无名')}\n" \
          f"方向：{order_side_map[execrpt.side]}{pos_effect_map[execrpt.position_effect]}\n" \
          f"成交量：{int(execrpt.volume)}\n" \
          f"成交价：{round(execrpt.price, 2)}\n" \
          f"执行回报类型：{exec_type_map[execrpt.exec_type]}"

    logger.info(msg.replace("\n", " - ").replace('*', ""))
    if context.mode != MODE_BACKTEST and execrpt.exec_type in [1, 5, 6, 8, 12, 19]:
        wx.push_text(content=str(msg), key=context.wx_key)


def on_backtest_finished(context, indicator):
    """回测结束回调函数

    :param context:
    :param indicator:
        https://www.myquant.cn/docs/python/python_object_trade#bd7f5adf22081af5
    :return:
    """
    wx_key = context.wx_key
    symbols = context.symbols
    data_path = context.data_path
    logger = context.logger

    logger.info(str(indicator))
    logger.info("回测结束 ... ")
    cash = context.account().cash

    for k, v in indicator.items():
        if isinstance(v, float):
            indicator[k] = round(v, 4)

    row = OrderedDict({
        "研究标的": ", ".join(list(context.symbols_info.keys())),
        "回测开始时间": context.backtest_start_time,
        "回测结束时间": context.backtest_end_time,
        "累计收益率": indicator['pnl_ratio'],
        "最大回撤": indicator['max_drawdown'],
        "年化收益率": indicator['pnl_ratio_annual'],
        "夏普比率": indicator['sharp_ratio'],
        "盈利次数": indicator['win_count'],
        "亏损次数": indicator['lose_count'],
        "交易胜率": indicator['win_ratio'],
        "累计出入金": int(cash['cum_inout']),
        "累计交易额": int(cash['cum_trade']),
        "累计手续费": int(cash['cum_commission']),
        "累计平仓收益": int(cash['cum_pnl']),
        "净收益": int(cash['pnl']),
    })
    sdt = pd.to_datetime(context.backtest_start_time).strftime('%Y%m%d')
    edt = pd.to_datetime(context.backtest_end_time).strftime('%Y%m%d')
    file_xlsx = os.path.join(data_path, f'{context.name}_{sdt}_{edt}.xlsx')
    file = pd.ExcelWriter(file_xlsx, mode='w')

    dfe = pd.DataFrame({"指标": list(row.keys()), "值": list(row.values())})
    dfe.to_excel(file, sheet_name='回测表现', index=False)

    logger.info("回测结果：{}".format(row))
    content = ""
    for k, v in row.items():
        content += "{}: {}\n".format(k, v)
    wx.push_text(content=content, key=wx_key)

    trades = []
    operates = []
    performances = []
    for symbol in symbols:
        trader: GmCzscTrader = context.symbols_info[symbol]['trader']
        trades.extend(trader.long_pos.pairs)
        operates.extend(trader.long_pos.operates)
        performances.append(trader.long_pos.evaluate_operates())

    df = pd.DataFrame(trades)
    df['开仓时间'] = df['开仓时间'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M"))
    df['平仓时间'] = df['平仓时间'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M"))
    df.to_excel(file, sheet_name='交易汇总', index=False)

    dfo = pd.DataFrame(operates)
    dfo['dt'] = dfo['dt'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M"))
    dfo.to_excel(file, sheet_name='操作汇总', index=False)

    dfp = pd.DataFrame(performances)
    dfp.to_excel(file, sheet_name='表现汇总', index=False)
    file.close()

    wx.push_file(file_xlsx, wx_key)


def on_error(context, code, info):
    if context.now.isoweekday() > 5 or context.now.hour not in [9, 10, 11, 13, 14]:
        # print(f"on_error: {context.now} 不是交易时间")
        return

    logger = context.logger
    msg = "{} - {}".format(code, info)
    logger.warn(msg)
    if context.mode != MODE_BACKTEST:
        wx.push_text(content=msg, key=context.wx_key)


def on_account_status(context, account):
    """响应交易账户状态更新事件，交易账户状态变化时被触发
    https://www.myquant.cn/docs/python/python_trade_event#4f07d24fc4314e3c
    """
    status = account['status']
    if status['state'] == 3:
        return

    if context.now.isoweekday() > 5 or context.now.hour not in [9, 10, 11, 13, 14]:
        # print(f"on_account_status: {context.now} 不是交易时间")
        return

    logger = context.logger
    msg = f"{str(account)}"
    logger.warn(msg)
    if context.mode != MODE_BACKTEST:
        wx.push_text(content=msg, key=context.wx_key)


def on_bar(context, bars):
    """订阅K线回调函数"""
    context.unfinished_orders = get_unfinished_orders()
    cancel_timeout_orders(context, max_m=30)

    for bar in bars:
        symbol = bar['symbol']
        trader: GmCzscTrader = context.symbols_info[symbol]['trader']
        trader.sync_long_position(context)

        if context.mode != MODE_BACKTEST and context.now.strftime("%H:%M") == '14:00':
            file_trader = os.path.join(context.data_path, f'traders/{symbol}.cat')
            dill.dump(trader, open(file_trader, 'wb'))


def is_order_exist(context, symbol, side) -> bool:
    """判断同方向订单是否已经存在

    :param context:
    :param symbol: 交易标的
    :param side: 交易方向
    :return: bool
    """
    uo = context.unfinished_orders
    if not uo:
        return False
    else:
        for o in uo:
            if o.symbol == symbol and o.side == side:
                context.logger.info("同类型订单已存在：{} - {}".format(symbol, side))
                return True
    return False


def cancel_timeout_orders(context, max_m=30):
    """实盘仿真，撤销挂单时间超过 max_m 分钟的订单。

    :param context:
    :param max_m: 最大允许挂单分钟数
    :return:
    """
    for u_order in context.unfinished_orders:
        if context.now - u_order.created_at >= timedelta(minutes=max_m):
            order_cancel(u_order)


# ======================================================================================================================
# 系统状态报告函数
# ======================================================================================================================

def report_account_status(context):
    """报告账户持仓状态"""
    if context.now.isoweekday() > 5:
        print(f"{context.now} 不是交易时间")
        return

    logger = context.logger
    latest_dt = context.now.strftime(dt_fmt)
    account = context.account(account_id=context.account_id)
    cash = account.cash
    positions = account.positions()

    logger.info("=" * 30 + f" 账户状态【{latest_dt}】 " + "=" * 30)
    cash_report = f"净值：{int(cash.nav)}，可用资金：{int(cash.available)}，" \
                  f"浮动盈亏：{int(cash.fpnl)}，标的数量：{len(positions)}"
    logger.info(cash_report)

    for p in positions:
        p_report = f"标的：{p.symbol}，名称：{context.stocks.get(p.symbol, '无名')}，" \
                   f"数量：{p.volume}，成本：{round(p.vwap, 2)}，方向：{p.side}，" \
                   f"当前价：{round(p.price, 2)}，成本市值：{int(p.volume * p.vwap)}，" \
                   f"建仓时间：{p.created_at.strftime(dt_fmt)}"
        logger.info(p_report)

    # 实盘或仿真，推送账户信息到企业微信
    if context.mode != MODE_BACKTEST:

        msg = f"股票账户状态报告\n{'*' * 31}\n"
        msg += f"账户净值：{int(cash.nav)}\n" \
               f"持仓市值：{int(cash.market_value)}\n" \
               f"可用资金：{int(cash.available)}\n" \
               f"浮动盈亏：{int(cash.fpnl)}\n" \
               f"标的数量：{len(positions)}\n" \
               f"{'*' * 31}\n"

        for p in positions:
            try:
                msg += f'标的代码：{p.symbol}\n' \
                       f"标的名称：{context.stocks.get(p.symbol, '无名')}\n" \
                       f'持仓数量：{p.volume}\n' \
                       f'最新价格：{round(p.price, 2)}\n' \
                       f'持仓成本：{round(p.vwap, 2)}\n' \
                       f'盈亏比例：{int((p.price - p.vwap) / p.vwap * 10000) / 100}%\n' \
                       f'持仓市值：{int(p.volume * p.vwap)}\n' \
                       f'持仓天数：{(context.now - p.created_at).days}\n' \
                       f"{'*' * 31}\n"
            except:
                print(p)

        wx.push_text(msg.strip("\n *"), key=context.wx_key)


# ======================================================================================================================
# 使用掘金系统的交易员
# ======================================================================================================================

class GmCzscTrader(CzscAdvancedTrader):
    def __init__(self, bg: BarGenerator,
                 get_signals: Callable,
                 long_events: List[Event] = None,
                 long_pos: PositionLong = None):
        super().__init__(bg, get_signals, long_events, long_pos)

    def sync_long_position(self, context):
        """同步多头仓位到交易账户"""
        if not self.long_events:
            return
        assert isinstance(self.long_pos, PositionLong)

        symbol = self.symbol
        name = context.stocks.get(symbol, "无名标的")
        base_freq = self.base_freq
        bg = self.bg
        long_pos = self.long_pos
        max_sym_pos = context.symbols_info[symbol]['max_sym_pos']   # 最大标的仓位
        max_all_pos = context.max_all_pos                           # 最大账户仓位
        logger = context.logger
        if context.mode == MODE_BACKTEST:
            account = context.account()
        else:
            account = context.account(account_id=context.account_id)
        cash = account.cash

        # 确保数据更新到最新时刻
        bars = context.data(symbol=symbol, frequency=freq_map_inv[self.base_freq], count=100,
                            fields='symbol,eob,open,close,high,low,volume')
        bars = format_kline(bars, freq=bg.freq_map[base_freq])
        bars_new = [x for x in bars if x.dt > bg.bars[base_freq][-1].dt]
        if bars_new:
            for bar in bars_new:
                self.update(bar)

        price = self.latest_price
        print(f"{self.end_dt}: {name} - {long_pos.pos} - {long_pos.long_cost} - {price} - {len(long_pos.operates)}")

        sym_position = account.position(symbol, PositionSide_Long)
        if long_pos.pos == 0 and sym_position and sym_position.volume > 0:
            order_target_percent(symbol=symbol, percent=0, position_side=PositionSide_Long,
                                 order_type=OrderType_Limit, price=price, account=account.id)
            return

        if not long_pos.pos_changed:
            return

        # 判断总仓位是否已经达到限制水平
        cash_left = cash.available
        if 1 - cash_left / cash.nav > max_all_pos:
            logger.info(f"{context.now} 当前持仓比例已经超过{max_all_pos * 100}%，不允许再开仓")
            return

        all_positions = account.positions()
        if len(all_positions) >= 1 \
                and symbol not in [p.symbol for p in all_positions] \
                and len(all_positions) >= context.max_sym_num:
            logger.info(f"{context.now} 当前持仓数量已经超过{context.max_sym_num}只，不允许再开仓")
            return

        if long_pos.operates[-1]['op'] in [Operate.LO, Operate.LA1, Operate.LA2]:
            change_amount = max_sym_pos * long_pos.operates[-1]['pos_change'] * cash.nav
            if cash_left < change_amount:
                logger.info(f"{context.now} {symbol} {name} 可用资金不足，无法开多仓；"
                            f"剩余资金{cash_left}元，所需资金{change_amount}元")
                return

        if is_order_exist(context, symbol, PositionSide_Long):
            logger.info(f"{context.now} {symbol} {name} 同方向订单已存在")
            return

        percent = max_sym_pos * long_pos.pos
        order_target_percent(symbol=symbol, percent=percent, position_side=PositionSide_Long,
                             order_type=OrderType_Limit, price=price, account=account.id)


def gm_take_snapshot(gm_symbol, end_dt: str = None, file_html=None,
                     get_signals: Callable = get_default_signals,
                     adjust=ADJUST_PREV, max_count=1000):
    """使用掘金的数据对任意标的、任意时刻的状态进行快照

    :param gm_symbol:
    :param end_dt:
    :param file_html:
    :param get_signals:
    :param adjust:
    :param max_count:
    :return:
    """
    if not end_dt:
        end_dt = datetime.now().strftime(dt_fmt)

    bg = get_init_bg(gm_symbol, end_dt, base_freq='1分钟',
                     freqs=['5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线'],
                     max_count=max_count, adjust=adjust)
    ct = GmCzscTrader(bg, get_signals=get_signals)
    if file_html:
        ct.take_snapshot(file_html)
        print(f'saved into {file_html}')
    else:
        ct.open_in_browser()
    return ct


def check_index_status(qywx_key):
    """查看主要指数状态"""
    from czsc.utils.cache import home_path

    end_dt = datetime.now().strftime(dt_fmt)
    wx.push_text(f"{end_dt} 开始获取主要指数行情快照", qywx_key)
    for gm_symbol in indices.values():
        try:
            file_html = os.path.join(home_path, f"{gm_symbol}_{datetime.now().strftime('%Y%m%d')}.html")
            gm_take_snapshot(gm_symbol, end_dt, file_html=file_html)
            wx.push_file(file_html, qywx_key)
            os.remove(file_html)
        except:
            traceback.print_exc()
    wx.push_text(f"{end_dt} 获取主要指数行情快照获取结束，请仔细观察！！！", qywx_key)


def realtime_check_index_status(context):
    """实盘：发送主要指数行情图表"""
    if context.now.isoweekday() > 5:
        print(f"realtime_check_index_status: {context.now} 不是交易时间")
        return

    check_index_status(context.wx_key)


def process_out_of_symbols(context):
    """实盘：处理不在交易列表的持仓股"""
    if context.now.isoweekday() > 5:
        print(f"process_out_of_symbols: {context.now} 不是交易时间")
        return

    account = context.account(account_id=context.account_id)
    positions = account.positions(symbol="", side=PositionSide_Long)

    for p in positions:
        symbol = p.symbol
        if p.volume > 0 and p.symbol not in context.symbols_info.keys():
            order_target_percent(symbol=symbol, percent=0, position_side=PositionSide_Long,
                                 order_type=OrderType_Market, account=account.id)


# ======================================================================================================================
# 掘金系统初始化
# ======================================================================================================================
def init_context_universal(context, name):
    """通用 context 初始化：1、创建文件目录和日志记录

    :param context:
    :param name: 交易策略名称，建议使用英文
    """
    path_gm_logs = os.environ.get('path_gm_logs', None)
    assert os.path.exists(path_gm_logs)
    if context.mode == MODE_BACKTEST:
        data_path = os.path.join(path_gm_logs, f"backtest/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    else:
        data_path = os.path.join(path_gm_logs, f"realtime/{name}")
    cache_path = os.path.join(data_path, "cache")
    os.makedirs(cache_path, exist_ok=True)
    context.name = name
    context.data_path = data_path
    context.cache_path = cache_path
    context.stocks = get_stocks()
    context.logger = create_logger(os.path.join(data_path, "gm_trader.log"), cmd=True, name="gm")

    context.logger.info("运行配置：")
    context.logger.info(f"data_path = {data_path}")
    context.logger.info(f"cache_path = {cache_path}")

    if context.mode == MODE_BACKTEST:
        context.logger.info("backtest_start_time = " + str(context.backtest_start_time))
        context.logger.info("backtest_end_time = " + str(context.backtest_end_time))


def init_context_env(context):
    """通用 context 初始化：2、读入环境变量

    :param context:
    """
    context.wx_key = os.environ['wx_key']
    context.account_id = os.environ.get('account_id', '')
    if context.mode != MODE_BACKTEST:
        assert len(context.account_id) > 10, "非回测模式，必须设置 account_id "

    # 仓位控制[0, 1]，按资金百分比控制，1表示满仓，仅在开仓的时候控制
    context.max_all_pos = float(os.environ['max_all_pos'])
    context.max_sym_pos = float(os.environ['max_sym_pos'])
    context.max_sym_num = int(context.max_all_pos / context.max_sym_pos) * 2
    assert 0 <= context.max_all_pos <= 1
    assert 0 <= context.max_sym_pos <= 1
    assert context.max_all_pos >= context.max_sym_pos >= 0

    logger = context.logger
    logger.info(f"环境变量读取结果如下：")
    logger.info(f"总仓位控制：context.max_all_pos = {context.max_all_pos}")
    logger.info(f"单标的控制：context.max_sym_pos = {context.max_sym_pos}")


def init_context_traders(context, symbols: List[str],
                         base_freq: str,
                         freqs: List[str],
                         states_pos: dict,
                         get_signals: Callable,
                         get_long_events: Callable):
    """通用 context 初始化：3、为每个标的创建 GmCzscTrader 对象

    :param context:
    :param symbols:
    :param base_freq:
    :param freqs:
    :param states_pos:
    :param get_signals:
    :param get_long_events:
    :return:
    """
    frequency = freq_map_inv[base_freq]
    unsubscribe(symbols='*', frequency=frequency)

    context.states_pos = states_pos
    data_path = context.data_path
    logger = context.logger
    logger.info(f"输入交易标的数量：{len(symbols)}")
    logger.info(f"交易员的周期列表：base_freq = {base_freq}; freqs = {freqs}")
    logger.info(f"持仓状态对应仓位：{states_pos}")
    logger.info(f"交易信号定义函数：\n{inspect.getsource(get_signals)}")
    logger.info(f"多头事件定义函数：\n{inspect.getsource(get_long_events)}")

    if context.mode == MODE_BACKTEST:
        adjust = ADJUST_POST
    else:
        adjust = ADJUST_PREV
    os.makedirs(os.path.join(data_path, 'traders'), exist_ok=True)

    account = context.account(account_id=context.account_id)
    cash = account.cash

    long_events = get_long_events()
    symbols_info = {symbol: dict() for symbol in symbols}
    for symbol in symbols:
        try:
            symbols_info[symbol]['max_sym_pos'] = context.max_sym_pos
            file_trader = os.path.join(data_path, f'traders/{symbol}.cat')

            if os.path.exists(file_trader):
                trader: GmCzscTrader = dill.load(open(file_trader, 'rb'))
                logger.info(f"{symbol} Loaded Trader from {file_trader}")

            else:
                long_pos = PositionLong(symbol, T0=False,
                                        hold_long_a=states_pos['hold_long_a'],
                                        hold_long_b=states_pos['hold_long_b'],
                                        hold_long_c=states_pos['hold_long_c'])

                # 根据持仓更新 long_pos 到对应状态
                position = account.position(symbol, PositionSide_Long)
                if position:
                    position = position.amount / cash.nav
                    logger.info(f"{symbol} 最新时间：{context.now}，多仓：{position}")
                    if position > long_pos.pos_map['hold_long_c']:
                        long_pos.long_open()
                        long_pos.long_add1()
                        long_pos.long_add2()
                    elif position > long_pos.pos_map['hold_long_b']:
                        long_pos.long_open()
                        long_pos.long_add1()
                    elif position > long_pos.pos_map['hold_long_a']:
                        long_pos.long_open()

                bg = get_init_bg(symbol, context.now, base_freq=base_freq, freqs=freqs, max_count=1000, adjust=adjust)
                trader = GmCzscTrader(bg, get_signals=get_signals, long_events=long_events, long_pos=long_pos)
                dill.dump(trader, open(file_trader, 'wb'))

            symbols_info[symbol]['trader'] = trader
            logger.info("{} Trader 构建成功，最新时间：{}，多仓：{}".format(symbol, trader.end_dt, trader.long_pos.pos))

        except:
            del symbols_info[symbol]
            logger.info(f"{symbol} - {context.stocks[symbol]} 初始化失败，当前时间：{context.now}")
            traceback.print_exc()

    subscribe(",".join(symbols_info.keys()), frequency=frequency, count=300, wait_group=True)
    logger.info(f"订阅成功交易标的数量：{len(symbols_info)}")
    logger.info(f"交易标的配置：{symbols_info}")
    context.symbols_info = symbols_info


def init_context_schedule(context):
    """通用 context 初始化：设置定时任务

    :param context:
    """
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='09:31:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='10:01:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='10:31:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='11:01:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='11:31:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='13:01:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='13:31:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='14:01:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='14:31:00')
    schedule(schedule_func=report_account_status, date_rule='1d', time_rule='15:01:00')

    if context.mode != MODE_BACKTEST:
        # 以下是 实盘/仿真 模式下的定时任务
        schedule(schedule_func=realtime_check_index_status, date_rule='1d', time_rule='17:30:00')
        schedule(schedule_func=process_out_of_symbols, date_rule='1d', time_rule='09:40:00')
        schedule(schedule_func=process_out_of_symbols, date_rule='1d', time_rule='10:45:00')
        schedule(schedule_func=process_out_of_symbols, date_rule='1d', time_rule='11:25:00')
