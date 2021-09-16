# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:10
describe: 掘金量化实盘utils
"""
import dill
import time
from pprint import pprint
from czsc.utils.cache import home_path

from ..monitor import stocks_monitor_rt
from ..selector import stocks_dwm_selector_rt
from .base import *


def on_order_status(context, order):
    """
    https://www.myquant.cn/docs/python/python_object_trade#007ae8f5c7ec5298

    :param context:
    :param order:
    :return:
    """
    latest_dt = context.now.strftime("%Y-%m-%d %H:%M:%S")
    logger = context.logger
    symbol = order.symbol
    if symbol not in context.symbols_map.keys():
        context.logger.warn(f"{symbol} on_order_status error")
        return

    trader = context.symbols_map[symbol]['trader']
    file_orders = context.file_orders
    msg = f"订单状态更新通知：\n{'*' * 31}\n" \
          f"时间：{latest_dt}\n" \
          f"标的：{order.symbol}\n" \
          f"名称：{context.shares.get(order.symbol, '')}\n" \
          f"操作：{trader.op['operate'] + '#' + trader.cache['last_op_desc']}\n" \
          f"方向：{order.side}\n" \
          f"价格：{round(order.price, 2)}\n" \
          f"状态：{order.status}\n" \
          f"委托量：{int(order.volume)}\n" \
          f"已成量：{int(order.filled_volume)}\n" \
          f"均价：{round(order.filled_vwap, 2)}"

    logger.info(msg.replace("\n", " - "))
    if context.mode == MODE_BACKTEST:
        with open(file_orders, 'a', encoding="utf-8") as f:
            f.write(str(order) + '\n')
    else:
        if order.status in [1, 3]:
            push_text(content=str(msg), key=context.wx_key)


def on_execution_report(context, execrpt):
    """响应委托被执行事件，委托成交或者撤单拒绝后被触发。

    https://www.myquant.cn/docs/python/python_trade_event#on_execution_report%20-%20%E5%A7%94%E6%89%98%E6%89%A7%E8%A1%8C%E5%9B%9E%E6%8A%A5%E4%BA%8B%E4%BB%B6
    https://www.myquant.cn/docs/python/python_object_trade#ExecRpt%20-%20%E5%9B%9E%E6%8A%A5%E5%AF%B9%E8%B1%A1

    :param context:
    :param execrpt:
    :return:
    """
    latest_dt = context.now.strftime(dt_fmt)
    logger = context.logger
    msg = f"委托订单被执行通知：\n{'*' * 31}\n" \
          f"时间：{latest_dt}\n" \
          f"标的：{execrpt.symbol}\n" \
          f"方向：{execrpt.side}\n" \
          f"成交量：{int(execrpt.volume)}\n" \
          f"成交价：{round(execrpt.price, 2)}\n" \
          f"执行回报类型：{execrpt.exec_type}"

    logger.info(msg.replace("\n", " - "))
    if context.mode != MODE_BACKTEST and execrpt.exec_type in [1, 5, 6, 8, 12, 19]:
        push_text(content=str(msg), key=context.wx_key)


def on_error(context, code, info):
    logger = context.logger
    msg = "{} - {}".format(code, info)
    logger.warn(msg)
    if context.mode != MODE_BACKTEST:
        push_text(content=msg, key=context.wx_key)


def on_account_status(context, account):
    """响应交易账户状态更新事件，交易账户状态变化时被触发"""
    print(str(account))


def adjust_future_position_rt(context, symbol: str, trader: CzscTrader, mp: float):
    """调整单只标的仓位

    :param mp: 开仓比例限制
    :param trader:
    :param context:
    :param symbol: 交易标的
    :return:
    """
    assert 1 >= mp >= 0, "开仓限制错误"

    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.future_id)

    # 判断是否需要平多仓
    long_position = account.positions(symbol=symbol, side=PositionSide_Long)
    if long_position:
        lp = long_position[0].available
        oe = is_order_exist(context, symbol, OrderSide_Sell, PositionEffect_Close)
        if not oe and lp > 0 and trader.op['operate'] == Operate.LE.value:
            context.logger.info("{} - 平多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            write_bs(context, symbol, trader.op)
            order_volume(symbol=symbol, volume=lp, side=OrderSide_Sell, order_type=OrderType_Market,
                         position_effect=PositionEffect_Close, account=account.id)
            take_snapshot(context, trader, name=trader.op['desc'])

    # 判断是否需要平空仓
    short_position = account.positions(symbol=symbol, side=PositionSide_Short)
    if short_position:
        sp = short_position[0].available
        oe = is_order_exist(context, symbol, OrderSide_Buy, PositionEffect_Close)
        if not oe and sp > 0 and trader.op['operate'] == Operate.SE.value:
            context.logger.info("{} - 平空 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            write_bs(context, symbol, trader.op)
            order_volume(symbol=symbol, volume=sp, side=OrderSide_Buy, order_type=OrderType_Market,
                         position_effect=PositionEffect_Close, account=account.id)
            take_snapshot(context, trader, name=trader.op['desc'])

    # 判断是否需要开多仓
    if not long_position and trader.op['operate'] == Operate.LO.value:
        oe = is_order_exist(context, symbol, OrderSide_Buy, PositionEffect_Open)
        if not oe:
            context.logger.info("{} - 开多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            if mp >= 1:
                order_volume(symbol=symbol, volume=mp, side=OrderSide_Buy, order_type=OrderType_Market,
                             position_effect=PositionEffect_Open, account=account.id)
            else:
                order_target_percent(symbol=symbol, percent=mp, position_side=PositionSide_Long,
                                     order_type=OrderType_Market, account=account.id)
            take_snapshot(context, trader, name=trader.op['desc'])
            write_bs(context, symbol, trader.op)

    # 判断是否需要开空仓
    if not short_position and trader.op['operate'] == Operate.SO.value:
        oe = is_order_exist(context, symbol, OrderSide_Sell, PositionEffect_Open)
        if not oe:
            context.logger.info("{} - 开空 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            if mp >= 1:
                order_volume(symbol=symbol, volume=mp, side=OrderSide_Sell, order_type=OrderType_Market,
                             position_effect=PositionEffect_Open, account=account.id)
            else:
                order_target_percent(symbol=symbol, percent=mp, position_side=PositionSide_Short,
                                     order_type=OrderType_Market, account=account.id)
            take_snapshot(context, trader, name=trader.op['desc'])
            write_bs(context, symbol, trader.op)


def adjust_share_position_rt(context, symbol: str, trader: CzscTrader, mp: float, T0=False):
    """调整单只标的仓位

    :param T0: 是否允许 T+0 交易，默认为 False，表示不允许 T+0
    :param mp: 开仓比例限制
    :param trader:
    :param context:
    :param symbol: 交易标的
    :return:
    """
    assert 1 >= mp >= 0, "开仓限制错误"
    if symbol[:7] in ['SZSE.12', 'SHSE.11']:
        assert T0, "可转债支持 T+0 操作"

    in_trade_time = "14:59" > context.now.strftime("%H:%M") > "09:31"
    if not in_trade_time:
        return

    name = context.shares.get(symbol, "")
    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.share_id)

    long_position = account.positions(symbol=symbol, side=PositionSide_Long)
    if long_position:
        # 判断是否需要平多仓
        if T0:
            lp = long_position[0].volume
        else:
            lp = long_position[0].volume - long_position[0].volume_today

        oe = is_order_exist(context, symbol, OrderSide_Sell, PositionEffect_Close)

        if not oe and trader.op['operate'] in [Operate.LE.value, Operate.HO.value]:
            trader.op['desc'] = trader.cache['last_op_desc']
            if lp <= 0:
                context.logger.info(
                    "{} - {} - 可平仓位为零 - {} - {}".format(symbol, name, trader.op['desc'], trader.latest_price))
            else:
                context.logger.info(
                    "{} - {} - 平多 - {} - {}".format(symbol, name, trader.op['desc'], trader.latest_price))
                order_volume(symbol=symbol, volume=lp, side=OrderSide_Sell, order_type=OrderType_Market,
                             position_effect=PositionEffect_Close, account=account.id)
                take_snapshot(context, trader, name=trader.op['desc'])
                write_bs(context, symbol, trader.op)
    else:
        # 判断是否需要开多仓
        oe = is_order_exist(context, symbol, OrderSide_Buy, PositionEffect_Open)

        if not oe and trader.op['operate'] in [Operate.LO.value, Operate.HL.value]:
            trader.op['desc'] = trader.cache['last_op_desc']
            context.logger.info("{} - {} - 开多 - {} - {}".format(symbol, name, trader.op['desc'], trader.latest_price))

            if trader.kg.m1[-1].id - trader.cache['long_open_k1_id'] < context.wait_time:
                context.logger.info(f"{symbol}，开仓条件满足，等待开仓中，"
                                    f"已等待 {trader.kg.m1[-1].id - trader.cache['long_open_k1_id']}")
                return

            # 判断标的是否在允许开仓的股票列表中
            if symbol not in context.allow_open_shares:
                context.logger.info(f"{symbol} - {name} 不在允许开仓的股票列表中")
                return

            # 判断当前价格是否在开仓容差范围
            if abs(trader.latest_price - trader.cache['long_open_price']) > trader.cache['long_open_price'] * 0.03:
                context.logger.info(f"{symbol}，当前价（{trader.latest_price}）不在"
                                    f"开仓价（{trader.cache['long_open_price']}）容差范围，不允许开仓")
                return

            # 判断总仓位是否已经达到限制水平
            if 1 - account.cash.available / account.cash.nav > context.max_total_position:
                context.logger.info(f"当前持仓比例已经超过{context.max_total_position * 100}%，不允许再开仓")
                return

            # 判断是否有足够的资金用来开仓
            if account.cash.available < max(105 * trader.latest_price, 20000):
                context.logger.info(
                    "{} - {} - 开多信号触发 - {} - {}；可用资金小于2万 / 可用仓位不够开1手，暂不开仓".format(
                        symbol, name, trader.op['desc'], trader.latest_price))
                return

            if mp >= 1:
                max_mp = account.cash.available // (100 * trader.latest_price)
                mp = min(mp, max_mp)
                order_volume(symbol=symbol, volume=mp * 100, side=OrderSide_Buy, order_type=OrderType_Limit,
                             price=trader.latest_price, position_effect=PositionEffect_Open, account=account.id)
            else:
                max_mp = (account.cash.available * 0.95) / account.cash.nav
                mp = min(max_mp, mp)
                # 实盘陷阱：市价柜台是按照涨停价冻结资金的
                # 修改成 按最近一个1分钟bar的close开仓
                order_target_percent(symbol=symbol, percent=mp, position_side=PositionSide_Long,
                                     order_type=OrderType_Limit, price=trader.latest_price, account=account.id)
            take_snapshot(context, trader, name=trader.op['desc'])
            write_bs(context, symbol, trader.op)


def adjust_position_rt(context, symbol):
    bars = context.data(symbol=symbol, frequency='60s', count=100, fields='symbol,eob,open,close,high,low,volume')
    trader: CzscTrader = context.symbols_map[symbol]['trader']
    mp = context.symbols_map[symbol]['mp']
    bars = format_kline(bars, freq=Freq.F1)
    bars_new = [x for x in bars if x.dt > trader.kg.end_dt]
    if bars_new:
        for k in bars_new:
            trader.check_operate(k, context.stoploss, context.timeout, context.wait_time, context.max_open_tolerance)
    context.symbols_map[symbol]['trader'] = trader
    context.logger.info(context.shares.get(symbol, "无名标的") + " : op    : " + str(trader.op))
    context.logger.info(context.shares.get(symbol, "无名标的") + " : cache : " + str(dict(trader.cache)))

    if symbol in context.forbidden:
        context.logger.info(context.shares.get(symbol, "无名标的") + " 禁止交易")
        return

    # 可转债支持 T+0 交易
    if symbol[:7] in ['SZSE.12', 'SHSE.11']:
        adjust_share_position_rt(context, symbol, trader, mp, T0=True)
        return

    exchange, sec_code = symbol.split(".")
    if exchange in ["SZSE", "SHSE"]:
        adjust_share_position_rt(context, symbol, trader, mp, T0=False)
    else:
        adjust_future_position_rt(context, symbol, trader, mp)

    # 每隔30分钟保存一次trader对象
    if bars[-1].dt.minute % 30 == 0:
        file_gt = os.path.join(context.data_path, "{}.gt".format(symbol))
        dill.dump(trader, open(file_gt, 'wb'))
        context.logger.info(f'{symbol} trader cached into {file_gt}')


def on_bar(context, bars):
    context.unfinished_orders = get_unfinished_orders()
    cancel_timeout_orders(context, max_m=10)

    for bar in bars:
        symbol = bar['symbol']
        try:
            adjust_position_rt(context, symbol)
        except:
            traceback.print_exc()


def report_stocks_account_status(context):
    """报告股票账户状态"""
    if context.now.isoweekday() > 5:
        print(f"{context.now} 不是交易时间")
        return

    if not context.share_id:
        push_text("股票账户ID为空，无法获取账户状态报告。", key=context.wx_key)
        return

    account = context.account(account_id=context.share_id)
    cash = account.cash
    positions = account.positions(symbol="", side="")

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
                   f"标的名称：{context.shares.get(p.symbol, '')}\n" \
                   f'持仓数量：{p.volume}\n' \
                   f'最新价格：{round(p.price, 2)}\n' \
                   f'持仓成本：{round(p.vwap, 2)}\n' \
                   f'盈亏比例：{int((p.price - p.vwap) / p.vwap * 10000) / 100}%\n' \
                   f'持仓市值：{int(p.volume * p.vwap)}\n' \
                   f'持仓天数：{(context.now - p.created_at).days}\n' \
                   f"{'*' * 31}\n"
        except:
            print(p)

    push_text(msg.strip("\n *"), key=context.wx_key)


def is_order_exist(context, symbol, side, position_effect) -> bool:
    """判断同类型订单是否已经存在

    :param context:
    :param symbol: 交易标的
    :param side: 交易方向
    :param position_effect: 开平标志
    :return: bool
    """
    uo = context.unfinished_orders
    if not uo:
        return False
    else:
        for o in uo:
            if o.symbol == symbol and o.side == side and o.position_effect == position_effect:
                context.logger.info("同类型订单已存在：{} - {} - {}".format(symbol, side, position_effect))
                return True
    return False


def cancel_timeout_orders(context, max_m=10):
    """实盘仿真，撤销挂单时间超过 max_m 分钟的订单。

    :param context:
    :param max_m: 最大允许挂单分钟数
    :return:
    """
    for u_order in context.unfinished_orders:
        if context.ipo_shares and u_order.symbol in context.ipo_shares:
            # 跳过新股，新股申购订单不能撤
            continue

        if context.now - u_order.created_at >= timedelta(minutes=max_m):
            order_cancel(u_order)
            msg = "撤单通知：\n{}\n标的：{}\n".format("*" * 31, u_order.symbol)
            msg += "价格：{}\n时间：{}\n".format(u_order.price, u_order.created_at.strftime(dt_fmt))
            msg += "开平标志：{}\n买卖方向：{}".format(u_order.position_effect, u_order.side)
            context.logger.info(msg.replace("\n", " - "))
            if context.mode != MODE_BACKTEST:
                push_text(msg, context.wx_key)


def send_ipo_order(context):
    """实盘申购新股
    ipo_get_lot_info    https://www.myquant.cn/docs/python/python_select_api#0cbdf124a950907e
    ipo_get_instruments https://www.myquant.cn/docs/python/python_select_api#0cbdf124a950907e
    ipo_get_quota       https://www.myquant.cn/docs/python/python_select_api#0cbdf124a950907e
    ipo_buy             https://www.myquant.cn/docs/python/python_trade_api#31223e239affb510
    :param context:
    :return:
    """
    new_shares = ipo_get_instruments(sec_type=SEC_TYPE_STOCK, account_id=context.share_id, df=False)
    print(new_shares)
    if not new_shares:
        return
    context.ipo_shares = [x['symbol'] for x in new_shares]
    quota = ipo_get_quota(context.share_id)

    # ipo_buy(symbol, volume, price, account_id)


def push_operate_status(context):
    """推送全部交易标的操作状态"""
    if context.now.isoweekday() > 5:
        print(f"{context.now} 不是交易时间")
        return

    try:
        msg = "## 全部交易标的多空状态\n\n"
        i = 0
        for symbol, v in context.symbols_map.items():
            trader: CzscTrader = v['trader']
            last_op = trader.cache['last_op']
            last_op_desc = trader.cache['last_op_desc']

            if last_op in [Operate.HL.value, Operate.HS.value]:
                i += 1
                msg += f">{i}. {symbol} - {context.shares.get(symbol, '无名')} - {last_op} - {last_op_desc}\n"

        push_markdown(msg.strip("\n"), context.wx_key)
    except:
        print("push_operate_status fail.")
        traceback.print_exc()


def init_context_rt(context, name, symbols,
                    op_freq: Freq,
                    freqs: List[str],
                    get_signals: Callable,
                    get_events: Callable):
    """实盘 context 初始化方法

    :param context:
    :param name: tactic 的名称
    :param symbols: 交易列表
    :param op_freq: 交易周期
    :param freqs: 多级别周期
    :param get_signals: 信号计算方法
    :param get_events: 交易事件定义
    :return:
    """
    assert context.mode != MODE_BACKTEST
    path_gm_logs = os.environ.get('path_gm_logs', None)
    assert os.path.exists(path_gm_logs)
    data_path = os.path.join(path_gm_logs, f"realtime/{name}")
    cache_path = os.path.join(data_path, "cache")
    os.makedirs(cache_path, exist_ok=True)
    context.data_path = data_path
    context.cache_path = cache_path

    context.logger = create_logger(os.path.join(data_path, "realtime.log"), cmd=True, name="gm")
    context.file_orders = os.path.join(data_path, "orders.txt")
    context.share_id = os.environ['share_id']
    context.future_id = None
    context.shares = get_shares()

    context.op_freq = op_freq
    context.freqs = freqs
    context.get_signals = get_signals
    context.get_events = get_events

    context.wx_key = os.environ['wx_key']
    context.stoploss = float(os.environ['stoploss'])  # 止损条件设定
    context.timeout = int(os.environ['timeout'])      # 超时条件设定
    context.wait_time = int(os.environ['wait_time'])  # 开仓等待时长，单位：分钟
    context.max_open_tolerance = float(os.environ['max_open_tolerance'])    # 最大开仓容错百分比

    context.ipo_shares = []
    # 仓位控制[0, 1]，按资金百分比控制，1表示满仓，仅在开仓的时候控制
    context.max_total_position = float(os.environ['max_total_position'])
    context.max_share_position = float(os.environ['max_share_position'])
    assert 0 <= context.max_total_position <= 1
    assert 0 <= context.max_share_position <= 1
    assert context.max_total_position >= context.max_share_position >= 0

    context.logger.info("=" * 88)
    context.logger.info("实盘配置：")
    context.logger.info(f"总仓位控制：{context.max_total_position}")
    context.logger.info(f"单仓位控制：{context.max_share_position}")
    context.logger.info(f"异常退出条件：stoploss = {context.stoploss}; timeout = {context.timeout}")
    context.logger.info(f"K线交易周期：{context.op_freq}")
    context.logger.info(f"K线周期列表：{context.freqs}")
    context.logger.info("交易信号计算：\n" + inspect.getsource(context.get_signals))
    context.logger.info("交易事件定义：\n" + inspect.getsource(context.get_events))

    # 仅允许在最近设置的股票池列表中的股票上开仓
    context.allow_open_shares = list(symbols)

    # 查询当前持仓，保证持仓标的在交易标的列表中
    positions = context.account(account_id=context.share_id).positions(symbol="", side="")
    if positions:
        p_symbols = [p.symbol for p in positions]
        symbols += p_symbols

    symbols = sorted(list(set(symbols)))
    context.logger.info(f"交易标的数量：{len(symbols)}")
    symbols_map = {symbol: dict() for symbol in symbols}

    for symbol in symbols_map.keys():
        try:
            symbols_map[symbol]['mp'] = context.max_share_position
            file_gt = os.path.join(data_path, "{}.gt".format(symbol))
            if os.path.exists(file_gt) and time.time() - os.path.getmtime(file_gt) < 3600 * 72:
                trader: CzscTrader = dill.load(open(file_gt, 'rb'))
                context.logger.info("{} 加载成功，最新K线时间：{}".format(file_gt, trader.end_dt.strftime(dt_fmt)))
            else:
                kg = get_init_kg(symbol, context.now, max_count=2000, adjust=ADJUST_PREV, freqs=freqs)
                trader = CzscTrader(kg=kg, get_signals=get_signals, events=get_events(), op_freq=op_freq)

                # 更新多头持仓信息
                p = context.account(account_id=context.share_id).positions(symbol=symbol, side=PositionSide_Long)
                if p:
                    assert len(p) == 1
                    trader.cache['last_op'] = Operate.HL.value
                    trader.cache['last_op_desc'] = "启动时持多仓"
                    trader.cache['long_open_price'] = p[0].vwap
                    trader.cache['long_open_error_price'] = p[0].vwap * 0.97
                    trader.cache['long_open_k1_id'] = trader.kg.m1[-1].id
                    trader.cache['long_max_high'] = max(trader.latest_price, p[0].vwap)
                    context.logger.info(f'{symbol} 多头持仓信息更新成功：{dict(trader.cache)}')

                symbols_map[symbol]['trader'] = trader
                context.logger.info("{} 初始化完成，最新K线时间：{}".format(symbol, trader.end_dt.strftime(dt_fmt)))
                dill.dump(trader, open(file_gt, 'wb'))

            symbols_map[symbol]['trader'] = trader
        except:
            del symbols_map[symbol]
            print(f'init kg fail on {symbol}')

    subscribe(",".join(symbols_map.keys()), frequency='60s', count=300, wait_group=False)
    pprint(symbols_map)
    context.symbols_map = symbols_map

    # 设置定时任务
    # ------------------------------------------------------------------------------------------------------------------
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='09:31:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='10:01:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='10:31:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='11:01:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='11:31:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='13:01:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='13:31:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='14:01:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='14:31:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='15:01:00')
    # schedule(schedule_func=stocks_dwm_selector_rt, date_rule='1d', time_rule='17:05:00')
    # schedule(schedule_func=stocks_monitor_rt, date_rule='1d', time_rule='09:05:00')
    # schedule(schedule_func=stocks_monitor_rt, date_rule='1d', time_rule='11:35:00')
    # schedule(schedule_func=stocks_monitor_rt, date_rule='1d', time_rule='15:05:00')


def check_index_status(qywx_key=None):
    """查看指数状态"""
    for gm_symbol in indices.values():
        try:
            file_html = os.path.join(home_path, f"{gm_symbol}.html")
            gm_take_snapshot(gm_symbol, end_dt=datetime.now(), file_html=file_html)
            if qywx_key:
                push_file(file_html, qywx_key)
        except:
            traceback.print_exc()

