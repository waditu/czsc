# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:11
describe: 配合 CzscAdvancedTrader 进行使用的掘金工具
"""
import os
import dill
import czsc
import pandas as pd
from gm.api import *
from datetime import datetime, timedelta
from collections import OrderedDict
from typing import List, Callable
from czsc import CzscAdvancedTrader, create_advanced_trader
from czsc.data import freq_cn2gm
from czsc.utils import qywx as wx
from czsc.utils import BarGenerator
from czsc.objects import RawBar, Freq


dt_fmt = "%Y-%m-%d %H:%M:%S"
date_fmt = "%Y-%m-%d"

assert czsc.__version__ >= "0.8.29"


def set_gm_token(token):
    with open(os.path.join(os.path.expanduser("~"), "gm_token.txt"), 'w', encoding='utf-8') as f:
        f.write(token)


file_token = os.path.join(os.path.expanduser("~"), "gm_token.txt")
if not os.path.exists(file_token):
    print("{} 文件不存在，请单独启动一个 python 终端，调用 set_gm_token 方法创建该文件，再重新执行。".format(file_token))
else:
    gm_token = open(file_token, encoding="utf-8").read()
    set_token(gm_token)


def is_trade_date(dt):
    """判断 dt 时刻是不是交易日期"""
    dt = pd.to_datetime(dt)
    date_ = dt.strftime("%Y-%m-%d")
    trade_dates = get_trading_dates(exchange='SZSE', start_date=date_, end_date=date_)
    if trade_dates:
        return True
    else:
        return False


def is_trade_time(dt):
    """判断 dt 时刻是不是交易时间"""
    dt = pd.to_datetime(dt)
    date_ = dt.strftime("%Y-%m-%d")
    trade_dates = get_trading_dates(exchange='SZSE', start_date=date_, end_date=date_)
    if trade_dates and "15:00" > dt.strftime("%H:%M") > "09:30":
        return True
    else:
        return False


def get_symbol_names():
    """获取股票市场标的列表，包括股票、指数等"""
    df = get_instruments(exchanges='SZSE,SHSE', fields="symbol,sec_name", df=True)
    shares = {row['symbol']: row['sec_name'] for _, row in df.iterrows()}
    return shares


def format_kline(df, freq: Freq):
    bars = []
    for i, row in df.iterrows():
        # amount 单位：元
        bar = RawBar(symbol=row['symbol'], id=i, freq=freq, dt=row['eob'], open=round(row['open'], 2),
                     close=round(row['close'], 2), high=round(row['high'], 2),
                     low=round(row['low'], 2), vol=row['volume'], amount=row['amount'])
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
                       fields='symbol,eob,open,close,high,low,volume,amount', count=count, df=True)
    else:
        df = history_n(symbol=symbol, frequency=freq, end_time=end_time, adjust=adjust,
                       fields='symbol,eob,open,close,high,low,volume,amount,position', count=count, df=True)
    return format_kline(df, freq_map_[freq])


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

    delta_days = 180
    last_day = (end_dt - timedelta(days=delta_days)).replace(hour=16, minute=0)

    bg = BarGenerator(base_freq, freqs, max_count)
    if "周线" in freqs or "月线" in freqs:
        d_bars = get_kline(symbol, last_day, freq_cn2gm["日线"], count=5000, adjust=adjust)
        bgd = BarGenerator("日线", ['周线', '月线', '季线', '年线'])
        for b in d_bars:
            bgd.update(b)
    else:
        bgd = None

    for freq in bg.bars.keys():
        if freq in ['周线', '月线', '季线', '年线']:
            bars_ = bgd.bars[freq]
        else:
            bars_ = get_kline(symbol, last_day, freq_cn2gm[freq], max_count, adjust)
        bg.init_freq_bars(freq, bars_)
        print(f"{symbol} - {freq} - {len(bg.bars[freq])} - last_dt: {bg.bars[freq][-1].dt} - last_day: {last_day}")

    bars2 = get_kline(symbol, end_dt, freq_cn2gm[base_freq],
                      count=int(240 / int(base_freq.strip('分钟')) * delta_days))
    data = [x for x in bars2 if x.dt > last_day]
    assert len(data) > 0
    print(f"{symbol}: bar generator 最新时间 {bg.bars[base_freq][-1].dt.strftime(dt_fmt)}，还有{len(data)}行数据需要update")
    return bg, data


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
    if not is_trade_time(context.now):
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
        trader: CzscAdvancedTrader = context.symbols_info[symbol]['trader']
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
    if not is_trade_time(context.now):
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
        "标的数量": len(context.symbols_info.keys()),
        "开始时间": context.backtest_start_time,
        "结束时间": context.backtest_end_time,
        "累计收益": indicator['pnl_ratio'],
        "最大回撤": indicator['max_drawdown'],
        "年化收益": indicator['pnl_ratio_annual'],
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
        trader: CzscAdvancedTrader = context.symbols_info[symbol]['trader']
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
    if not is_trade_time(context.now):
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

    if not is_trade_time(context.now):
        return

    logger = context.logger
    msg = f"{str(account)}"
    logger.warn(msg)
    if context.mode != MODE_BACKTEST:
        wx.push_text(content=msg, key=context.wx_key)


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


def gm_take_snapshot(gm_symbol, end_dt=None, file_html=None,
                     freqs=('1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线', '周线', '月线'),
                     adjust=ADJUST_PREV, max_count=1000):
    """使用掘金的数据对任意标的、任意时刻的状态进行快照

    :param gm_symbol:
    :param end_dt:
    :param file_html:
    :param freqs:
    :param adjust:
    :param max_count:
    :return:
    """
    if not end_dt:
        end_dt = datetime.now().strftime(dt_fmt)

    bg, data = get_init_bg(gm_symbol, end_dt, freqs[0], freqs[1:], max_count, adjust)
    ct = CzscAdvancedTrader(bg)
    for bar in data:
        ct.update(bar)

    if file_html:
        ct.take_snapshot(file_html)
        print(f'saved into {file_html}')
    else:
        ct.open_in_browser()
    return ct


def strategy_snapshot(symbol, strategy: Callable, end_dt=None, file_html=None, adjust=ADJUST_PREV, max_count=1000):
    """使用掘金的数据对任意标的、任意时刻的状态进行策略快照

    :param symbol: 交易标的
    :param strategy: 择时交易策略
    :param end_dt: 结束时间，精确到分钟
    :param file_html: 结果文件
    :param adjust: 复权类型
    :param max_count: 最大K线数量
    :return: trader
    """
    tactic = strategy(symbol)
    base_freq = tactic['base_freq']
    freqs = tactic['freqs']
    bg, data = get_init_bg(symbol, end_dt, base_freq, freqs, max_count, adjust)
    trader = create_advanced_trader(bg, data, strategy)
    if file_html:
        trader.take_snapshot(file_html)
        print(f'saved into {file_html}')
    else:
        trader.open_in_browser()
    return trader


def save_traders(context):
    """实盘：保存交易员快照"""
    if context.now.isoweekday() > 5:
        print(f"save_traders: {context.now} 不是交易时间")
        return

    for symbol in context.symbols_info.keys():
        trader: CzscAdvancedTrader = context.symbols_info[symbol]['trader']
        if context.mode != MODE_BACKTEST:
            file_trader = os.path.join(context.data_path, f'traders/{symbol}.cat')
            dill.dump(trader, open(file_trader, 'wb'))

