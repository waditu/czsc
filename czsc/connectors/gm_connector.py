# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2023/2/26 18:49
describe: 掘金量化终端对接
"""
import os
import dill
import inspect
import pandas as pd
from loguru import logger
try:
    from gm.api import *
except ModuleNotFoundError:
    logger.warning(f"gm 模块没有安装")
from datetime import datetime, timedelta
from collections import OrderedDict
from typing import List
from czsc import CzscTrader, CzscStrategyBase
from czsc.data import freq_cn2gm
from czsc.utils import qywx as wx
from czsc.utils import BarGenerator
from czsc.objects import RawBar, Freq
from czsc.fsa import push_message


dt_fmt = "%Y-%m-%d %H:%M:%S"
date_fmt = "%Y-%m-%d"


def set_gm_token(token):
    __file_token = os.path.join(os.path.expanduser("~"), "gm_token.txt")
    with open(__file_token, 'w', encoding='utf-8') as f:
        f.write(token)


file_token = os.path.join(os.path.expanduser("~"), "gm_token.txt")
if not os.path.exists(file_token):
    print("{} 文件不存在，请单独启动一个 python 终端，调用 set_gm_token 方法创建该文件，再重新执行。".format(file_token))
else:
    gm_token = open(file_token, encoding="utf-8").read()
    set_token(gm_token)


def gm_push_message(msg: str, msg_type: str = 'text', **kwargs):
    """统一飞书和企业微信消息推送服务

    :param msg:
    :param msg_type:
    :param kwargs:
    :return:
    """
    wx_key = kwargs.get('wx_key')
    fs_app = kwargs.get('fs_app')
    if wx_key:
        try:
            if msg_type == 'text':
                wx.push_text(msg, wx_key)
            elif msg_type == 'file':
                wx.push_file(msg, wx_key)
            else:
                logger.debug(f"企业微信通道仅支持 text 和 file 类型，当前类型为 {msg_type}")
        except Exception as _e:
            logger.debug(f"企业微信消息推送失败：{_e}")

    if fs_app:
        try:
            push_message(msg=msg, msg_type=msg_type,
                         feishu_app_secret=fs_app['feishu_app_secret'],
                         feishu_app_id=fs_app['feishu_app_id'],
                         feishu_members=fs_app['feishu_members'])
        except Exception as _e:
            logger.debug(f"飞书消息推送失败：{_e}")


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


def to_tz_datetime(dt):
    """格式化日期时间"""
    end_dt = pd.to_datetime(dt, utc=True)
    end_dt = end_dt.tz_convert('dateutil/PRC')
    # 时区转换之后，要减去8个小时才是设置的时间
    end_dt = end_dt - timedelta(hours=8)
    return end_dt


def get_raw_bars(symbol, freq, sdt, edt, fq='前复权', **kwargs):
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
    sdt = to_tz_datetime(sdt)
    edt = to_tz_datetime(edt)

    freq_map_ = {'60s': Freq.F1, '300s': Freq.F5, '900s': Freq.F15, '1800s': Freq.F30,
                 '3600s': Freq.F60, '1d': Freq.D}
    freq_map_ = {v: k for k, v in freq_map_.items()}
    period = freq_map_[freq]

    if fq == '前复权':
        adjust = ADJUST_PREV
    elif fq == '后复权':
        adjust = ADJUST_POST
    else:
        assert fq == '不复权'
        adjust = ADJUST_NONE

    bars = get_kline(symbol, freq=period, count=33000, end_time=edt, adjust=adjust)
    bars = [bar for bar in bars if bar.dt >= sdt]
    return bars


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
    """订单状态更新通知

    https://www.myquant.cn/docs/python/python_object_trade#007ae8f5c7ec5298

    :param context:
    :param order:
    :return:
    """
    if not is_trade_time(context.now):
        return

    symbol = order.symbol
    latest_dt = context.now.strftime("%Y-%m-%d %H:%M:%S")

    msg = f"订单状态更新通知：\n{'*' * 31}\n" \
          f"更新时间：{latest_dt}\n" \
          f"标的名称：{symbol} {context.stocks.get(symbol, '无名')}\n" \
          f"操作类型：{order_side_map[order.side]}{pos_effect_map[order.position_effect]}\n" \
          f"下单价格：{round(order.price, 2)}\n" \
          f"最新状态：{order_status_map[order.status]}\n" \
          f"委托（股）：{int(order.volume)}\n" \
          f"已成（股）：{int(order.filled_volume)}\n" \
          f"均价（元）：{round(order.filled_vwap, 2)}"

    logger.info(msg.replace("\n", " - ").replace('*', ""))
    if context.mode != MODE_BACKTEST and order.status in [1, 3, 5, 8, 9, 12]:
        gm_push_message(str(msg), msg_type='text', **context.push_msg_conf)


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
        gm_push_message(str(msg), msg_type='text', **context.push_msg_conf)


def on_backtest_finished(context, indicator):
    """回测结束回调函数

    :param context:
    :param indicator:
        https://www.myquant.cn/docs/python/python_object_trade#bd7f5adf22081af5
    :return:
    """
    data_path = context.data_path
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
    gm_push_message(content, msg_type='text', **context.push_msg_conf)


def on_error(context, code, info):
    if not is_trade_time(context.now):
        return

    msg = "{} - {}".format(code, info)
    logger.warning(msg)
    if context.mode != MODE_BACKTEST:
        gm_push_message(msg, msg_type='text', **context.push_msg_conf)


def on_account_status(context, account):
    """响应交易账户状态更新事件，交易账户状态变化时被触发

    https://www.myquant.cn/docs/python/python_trade_event#4f07d24fc4314e3c
    """
    status = account['status']
    if status['state'] == 3:
        return

    if not is_trade_time(context.now):
        return

    msg = f"{str(account)}"
    logger.warning(msg)
    if context.mode != MODE_BACKTEST:
        gm_push_message(msg, msg_type='text', **context.push_msg_conf)


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
    ct = CzscTrader(bg)
    for bar in data:
        ct.update(bar)

    if file_html:
        ct.take_snapshot(file_html)
        print(f'saved into {file_html}')
    return ct


def save_traders(context):
    """实盘：保存交易员快照"""
    if context.now.isoweekday() > 5:
        print(f"save_traders: {context.now} 不是交易时间")
        return

    for symbol in context.symbols_info.keys():
        trader: CzscTrader = context.symbols_info[symbol]['trader']
        if context.mode != MODE_BACKTEST:
            file_trader = os.path.join(context.data_path, f'traders/{symbol}.ct')
            dill.dump(trader, open(file_trader, 'wb'))


indices = {
    "上证指数": 'SHSE.000001',
    "上证50": 'SHSE.000016',
    "沪深300": "SHSE.000300",
    "中证1000": "SHSE.000852",
    "中证500": "SHSE.000905",

    "深证成指": "SZSE.399001",
    "创业板指数": 'SZSE.399006',
    "深次新股": "SZSE.399678",
    "中小板指": "SZSE.399005",
    "国证2000": "SZSE.399303",
    "小盘成长": "SZSE.399376",
    "小盘价值": "SZSE.399377",
}


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


def on_bar(context, bars):
    """订阅K线回调函数"""
    context.unfinished_orders = get_unfinished_orders()
    cancel_timeout_orders(context, max_m=30)

    for bar in bars:
        symbol = bar['symbol']
        trader: CzscTrader = context.symbols_info[symbol]['trader']

        # 确保数据更新到最新时刻
        base_freq = trader.base_freq
        bars = context.data(symbol=symbol, frequency=freq_cn2gm[base_freq], count=100,
                            fields='symbol,eob,open,close,high,low,volume,amount')
        bars = format_kline(bars, freq=trader.bg.freq_map[base_freq])
        bars_new = [x for x in bars if x.dt > trader.bg.bars[base_freq][-1].dt]
        if bars_new:
            for bar_ in bars_new:
                trader.update(bar_)

        sync_long_position(context, trader)


def report_account_status(context):
    """报告账户持仓状态"""
    if context.now.isoweekday() > 5:
        return

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
               f"标的数量：{len(positions)}\n"
        gm_push_message(msg, msg_type='text', **context.push_msg_conf)

        results = []
        for symbol, info in context.symbols_info.items():
            name = context.stocks.get(symbol, '无名')
            trader: CzscTrader = context.symbols_info[symbol]['trader']
            p = account.position(symbol=symbol, side=PositionSide_Long)

            row = {'交易标的': symbol, '标的名称': name,
                   '最新时间': trader.end_dt.strftime(dt_fmt),
                   '最新价格': trader.latest_price,
                   '集成仓位': trader.get_ensemble_pos(),
                   }

            if "日线" in trader.kas.keys():
                bar1, bar2 = trader.kas['日线'].bars_raw[-2:]
                row.update({'昨日收盘': round(bar1.close, 2),
                            '今日涨幅': round(bar2.close / bar1.close - 1, 4)})

            if p:
                row.update({"实盘持仓数量": p.volume,
                            "实盘持仓成本": round(p.vwap, 2),
                            "实盘持仓市值": int(p.volume * p.vwap)})
            else:
                row.update({"实盘持仓数量": 0,  "实盘持仓成本": 0, "实盘持仓市值": 0})

            results.append(row)

        df = pd.DataFrame(results)
        df.sort_values(['集成仓位'], ascending=False, inplace=True, ignore_index=True)
        file_xlsx = os.path.join(context.data_path, f"holds_{context.now.strftime('%Y%m%d_%H%M')}.xlsx")
        df.to_excel(file_xlsx, index=False)
        gm_push_message(file_xlsx, msg_type='file', **context.push_msg_conf)
        os.remove(file_xlsx)

        # 提示非策略交易标的持仓
        process_out_of_symbols(context)


def sync_long_position(context, trader: CzscTrader):
    """同步多头仓位到交易账户"""
    if not trader.positions:
        return

    symbol = trader.symbol
    name = context.stocks.get(symbol, "无名标的")
    ensemble_pos = trader.get_ensemble_pos(method='vote')
    max_sym_pos = context.symbols_info[symbol]['max_sym_pos']  # 最大标的仓位
    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.account_id)
    cash = account.cash

    price = trader.latest_price
    sym_position = account.position(symbol, PositionSide_Long)
    if ensemble_pos == 0 and not sym_position:
        # 如果多头仓位为0且掘金账户没有对应持仓，直接退出
        return

    if ensemble_pos == 0 and sym_position and sym_position.volume > 0:
        # 如果多头仓位为0且掘金账户依然还有持仓，清掉仓位
        order_target_volume(symbol=symbol, volume=0, position_side=PositionSide_Long,
                            order_type=OrderType_Limit, price=price, account=account.id)
        return

    # 没有仓位变化，直接退出
    if not trader.pos_changed:
        return

    # 仓位指向空头，直接退出
    if ensemble_pos < 0:
        return

    if cash.available < price * 120:
        logger.info(f"{context.now} {symbol} {name} 可用资金不足，无法开多仓，最少所需资金{int(price * 120)}元")
        return

    if is_order_exist(context, symbol, PositionSide_Long):
        logger.info(f"{context.now} {symbol} {name} 同方向订单已存在")
        return

    percent = max_sym_pos * ensemble_pos
    volume = int((cash.nav * percent / price // 100) * 100)     # 单位：股
    order_target_volume(symbol=symbol, volume=volume, position_side=PositionSide_Long,
                        order_type=OrderType_Limit, price=price, account=account.id)


def process_out_of_symbols(context):
    """实盘：处理不在交易列表的持仓股"""
    if context.now.isoweekday() > 5:
        print(f"process_out_of_symbols: {context.now} 不是交易时间")
        return

    if context.mode == MODE_BACKTEST:
        print(f"process_out_of_symbols: 回测模式下不需要执行")
        return

    account = context.account(account_id=context.account_id)
    positions = account.positions(symbol="", side=PositionSide_Long)

    oos = []
    for p in positions:
        symbol = p.symbol
        if p.volume > 0 and p.symbol not in context.symbols_info.keys():
            oos.append(symbol)
            # order_target_volume(symbol=symbol, volume=0, position_side=PositionSide_Long,
            #                     order_type=OrderType_Limit, price=p.price, account=account.id)
    if oos:
        gm_push_message(f"不在交易列表的持仓股：{', '.join(oos)}", msg_type='text', **context.push_msg_conf)


def init_context_universal(context, name):
    """通用 context 初始化：1、创建文件目录和日志记录

    :param context:
    :param name: 交易策略名称，建议使用英文
    """
    path_gm_logs = os.environ.get('path_gm_logs', None)
    if context.mode == MODE_BACKTEST:
        data_path = os.path.join(path_gm_logs, f"backtest/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    else:
        data_path = os.path.join(path_gm_logs, f"realtime/{name}")
    os.makedirs(data_path, exist_ok=True)

    context.name = name
    context.data_path = data_path
    context.stocks = get_symbol_names()

    logger.add(os.path.join(data_path, "gm_trader.log"), rotation="500MB",
               encoding="utf-8", enqueue=True, retention="1 days")
    logger.info("运行配置：")
    logger.info(f"data_path = {data_path}")

    if context.mode == MODE_BACKTEST:
        logger.info("backtest_start_time = " + str(context.backtest_start_time))
        logger.info("backtest_end_time = " + str(context.backtest_end_time))


def init_context_env(context):
    """通用 context 初始化：2、读入环境变量"""
    context.account_id = os.environ.get('account_id', '')
    if context.mode != MODE_BACKTEST:
        assert len(context.account_id) > 10, "非回测模式，必须设置 account_id "

    # 单个标的仓位控制[0, 1]，按资金百分比控制，1表示满仓，仅在开仓的时候控制
    context.max_sym_pos = float(os.environ['max_sym_pos'])
    assert 0 <= context.max_sym_pos <= 1

    logger.info(f"环境变量读取结果如下：")
    logger.info(f"单标的控制：context.max_sym_pos = {context.max_sym_pos}")


def init_context_traders(context, symbols: List[str], strategy):
    """通用 context 初始化：3、为每个标的创建 trader

    :param context:
    :param symbols: 交易标的列表
    :param strategy: 交易策略
    :return:
    """
    assert issubclass(strategy, CzscStrategyBase), "strategy 必须是 CzscStrategyBase 的子类"
    with open(os.path.join(context.data_path, f'{strategy.__name__}.txt'), mode='w') as f:
        f.write(inspect.getsource(strategy))

    tactic = strategy(symbol="000001")
    base_freq, freqs = tactic.sorted_freqs[0], tactic.sorted_freqs[1:]
    frequency = freq_cn2gm[base_freq]
    unsubscribe(symbols='*', frequency=frequency)

    data_path = context.data_path
    logger.info(f"输入交易标的数量：{len(symbols)}")
    logger.info(f"交易员的周期列表：base_freq = {base_freq}; freqs = {freqs}")

    os.makedirs(os.path.join(data_path, 'traders'), exist_ok=True)
    symbols_info = {symbol: dict() for symbol in symbols}
    for symbol in symbols:
        try:
            symbols_info[symbol]['max_sym_pos'] = context.max_sym_pos
            file_trader = os.path.join(data_path, f'traders/{symbol}.cat')

            if os.path.exists(file_trader) and context.mode != MODE_BACKTEST:
                trader: CzscTrader = dill.load(open(file_trader, 'rb'))
                logger.info(f"{symbol} Loaded Trader from {file_trader}")

            else:
                tactic = strategy(symbol=symbol)
                bg, data = get_init_bg(symbol, context.now, base_freq, freqs, 1000, ADJUST_PREV)
                trader = CzscTrader(bg, signals_config=tactic.signals_config, positions=tactic.positions)
                dill.dump(trader, open(file_trader, 'wb'))

            symbols_info[symbol]['trader'] = trader
            logger.info("{} Trader 构建成功，最新时间：{}，多仓：{}".format(symbol, trader.end_dt, trader.get_ensemble_pos('mean')))

        except Exception as e1:
            del symbols_info[symbol]
            logger.exception(f"{e1}：{symbol} - {context.stocks.get(symbol, '无名')} 初始化失败，当前时间：{context.now}")
    context.symbols_info = symbols_info

    # 订阅K线数据
    subscribe(",".join(symbols_info.keys()), frequency=frequency, count=300, wait_group=False)
    logger.info(f"订阅成功数量：{len(symbols_info)}，订阅K线周期：{frequency}")
    logger.info(f"交易标的配置：{symbols_info}")


def init_context_schedule(context):
    """通用 context 初始化：设置定时任务"""
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

    # 以下是 实盘/仿真 模式下的定时任务
    if context.mode != MODE_BACKTEST:
        schedule(schedule_func=save_traders, date_rule='1d', time_rule='11:40:00')
        schedule(schedule_func=save_traders, date_rule='1d', time_rule='15:10:00')
        # schedule(schedule_func=realtime_check_index_status, date_rule='1d', time_rule='17:30:00')
        # schedule(schedule_func=process_out_of_symbols, date_rule='1d', time_rule='09:40:00')




