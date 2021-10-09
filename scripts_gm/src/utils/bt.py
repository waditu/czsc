# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:10
describe: 掘金量化回测utils
"""
import os

from .base import *


def report_account_status(context, account_id=None):
    """报告账户持仓状态"""
    logger = context.logger
    latest_dt = context.now.strftime(dt_fmt)
    logger.info("=" * 30 + f" 账户状态【{latest_dt}】 " + "=" * 30)

    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=account_id)

    cash = account.cash
    positions = account.positions(symbol="", side="")

    cash_report = f"净值：{int(cash.nav)}，可用资金：{int(cash.available)}，" \
                  f"浮动盈亏：{int(cash.fpnl)}，标的数量：{len(positions)}"
    logger.info(cash_report)

    for p in positions:
        p_report = f"标的：{p.symbol}，名称：{context.shares.get(p.symbol, '无名标的')}，" \
                   f"数量：{p.volume}，成本：{round(p.vwap, 2)}，方向：{p.side}，" \
                   f"当前价：{round(p.price, 2)}，成本市值：{int(p.volume * p.vwap)}，" \
                   f"建仓时间：{p.created_at.strftime(dt_fmt)}"
        logger.info(p_report)


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
    trader = context.symbols_map[symbol]['trader']
    file_orders = context.file_orders
    msg = f"订单状态更新通知：\n{'*' * 31}\n" \
          f"时间：{latest_dt}\n" \
          f"标的：{order.symbol}\n" \
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


def on_backtest_finished(context, indicator):
    """

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
        "研究标的": ", ".join(list(context.symbols_map.keys())),
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
    df = pd.DataFrame([row])
    df.to_excel(os.path.join(context.data_path, "回测结果.xlsx"), index=False)
    logger.info("回测结果：{}".format(row))
    content = ""
    for k, v in row.items():
        content += "{}: {}\n".format(k, v)
    push_text(content=content, key=wx_key)

    trades = []
    for symbol in symbols:
        file_bs = os.path.join(data_path, "cache/{}_bs.txt".format(symbol))
        if os.path.exists(file_bs):
            lines = [eval(x) for x in open(file_bs, 'r', encoding="utf-8").read().strip().split("\n")]
            trades.extend(lines)
    df = pd.DataFrame(trades)
    file_trades = os.path.join(data_path, 'trades.xlsx')
    df.to_excel(file_trades, index=False)
    push_file(file_trades, wx_key)
    push_file(os.path.join(data_path, "backtest.log"), wx_key)
    print(df)


def adjust_future_position_bt(context, symbol: str, trader: CzscTrader, mp: float):
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
        if lp > 0 and trader.op['operate'] == Operate.LE.value:
            context.logger.info("{} - 平多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            write_bs(context, symbol, trader.op)
            order_volume(symbol=symbol, volume=lp, side=OrderSide_Sell, order_type=OrderType_Market,
                         position_effect=PositionEffect_Close, account=account.id)
            take_snapshot(context, trader, name=trader.op['desc'])

    # 判断是否需要平空仓
    short_position = account.positions(symbol=symbol, side=PositionSide_Short)
    if short_position:
        sp = short_position[0].available
        if sp > 0 and trader.op['operate'] == Operate.SE.value:
            context.logger.info("{} - 平空 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            write_bs(context, symbol, trader.op)
            order_volume(symbol=symbol, volume=sp, side=OrderSide_Buy, order_type=OrderType_Market,
                         position_effect=PositionEffect_Close, account=account.id)
            take_snapshot(context, trader, name=trader.op['desc'])

    # 判断是否需要开多仓
    if not long_position and trader.op['operate'] == Operate.LO.value:
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
        context.logger.info("{} - 开空 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
        if mp >= 1:
            order_volume(symbol=symbol, volume=mp, side=OrderSide_Sell, order_type=OrderType_Market,
                         position_effect=PositionEffect_Open, account=account.id)
        else:
            order_target_percent(symbol=symbol, percent=mp, position_side=PositionSide_Short,
                                 order_type=OrderType_Market, account=account.id)
        take_snapshot(context, trader, name=trader.op['desc'])
        write_bs(context, symbol, trader.op)


def adjust_share_position_bt(context, symbol: str, trader: CzscTrader, mp: float, T0=False):
    """调整A股（股票、可转债、ETF）单只标的仓位

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

        if trader.op['operate'] in [Operate.LE.value, Operate.HO.value]:
            trader.op['desc'] = trader.cache['last_op_desc']
            if lp <= 0:
                context.logger.info("{} - 可平仓位为零 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            else:
                context.logger.info("{} - 平多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
                order_volume(symbol=symbol, volume=lp, side=OrderSide_Sell, order_type=OrderType_Market,
                             position_effect=PositionEffect_Close, account=account.id)
                take_snapshot(context, trader, name=trader.op['desc'])
                write_bs(context, symbol, trader.op)
    else:
        # 判断是否需要开多仓
        if trader.op['operate'] in [Operate.LO.value, Operate.HL.value]:
            trader.op['desc'] = trader.cache['last_op_desc']
            context.logger.info("{} - 开多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))

            if trader.kg.m1[-1].id - trader.cache['long_open_k1_id'] < context.wait_time:
                context.logger.info(f"{symbol}，开仓条件满足，等待开仓中，"
                                    f"已等待 {trader.kg.m1[-1].id - trader.cache['long_open_k1_id']}")
                return

            # 判断当前价格是否在开仓容差范围
            if abs(trader.latest_price - trader.cache['long_open_price']) > trader.cache['long_open_price'] * 0.03:
                context.logger.info(f"{symbol}，当前价（{trader.latest_price}）不在"
                                    f"开仓价（{trader.cache['long_open_price']}）容差范围，不允许开仓")
                return

            # 判断总仓位是否已经达到限制水平
            assert account.cash.available > account.cash.order_frozen
            cash_left = account.cash.available - account.cash.order_frozen
            if 1 - cash_left / account.cash.nav > context.max_total_position:
                context.logger.info(f"当前持仓比例已经超过{context.max_total_position * 100}%，不允许再开仓")
                return

            if account.cash.available < max(105 * trader.latest_price, 20000):
                context.logger.info(
                    "{} - 开多信号触发 - {} - {}；可用资金小于2万 / 可用仓位不够开1手，暂不开仓".format(
                        symbol, trader.op['desc'], trader.latest_price))
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


def adjust_position_bt(context, symbol):
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

    # 可转债支持 T+0 交易
    if symbol[:7] in ['SZSE.12', 'SHSE.11']:
        adjust_share_position_bt(context, symbol, trader, mp, T0=True)
        return

    exchange, sec_code = symbol.split(".")
    if exchange in ["SZSE", "SHSE"]:
        adjust_share_position_bt(context, symbol, trader, mp)
    else:
        adjust_future_position_bt(context, symbol, trader, mp)


def on_bar(context, bars):
    context.unfinished_orders = get_unfinished_orders()

    for bar in bars:
        symbol = bar['symbol']
        try:
            adjust_position_bt(context, symbol)
        except:
            traceback.print_exc()

    if context.now.hour == 13 and context.now.minute == 59:
        report_account_status(context)


def init_context_bt(context, name, symbols,
                    op_freq: Freq,
                    freqs: List[str],
                    get_signals: Callable,
                    get_events: Callable):
    """回测 context 初始化方法

    :param context: 掘金context
    :param name: tactic 的名称
    :param symbols: 交易标的列表
    :param op_freq: 指定的操作级别
    :param freqs: K线周期列表
    :param get_signals: 信号计算方法
    :param get_events: 事件列表获取
    :return:
    """
    path_gm_logs = os.environ.get('path_gm_logs', None)
    assert os.path.exists(path_gm_logs)
    data_path = os.path.join(path_gm_logs, f"backtest/{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    context.wx_key = os.environ['wx_key']
    cache_path = os.path.join(data_path, "cache")
    os.makedirs(cache_path, exist_ok=False)
    context.logger = create_logger(os.path.join(data_path, "backtest.log"), cmd=True, name="gm")
    context.data_path = data_path
    context.cache_path = cache_path
    context.file_orders = os.path.join(data_path, "orders.txt")
    context.shares = get_shares()
    context.stoploss = float(os.environ['stoploss'])  # 止损条件设定
    context.timeout = int(os.environ['timeout'])      # 超时条件设定
    context.wait_time = int(os.environ['wait_time'])  # 开仓等待时长，单位：分钟
    context.max_open_tolerance = float(os.environ['max_open_tolerance'])    # 最大开仓容错百分比

    # 仓位控制[0, 1]，按资金百分比控制，1表示满仓，仅在开仓的时候控制
    context.max_total_position = float(os.environ['max_total_position'])
    context.max_share_position = float(os.environ['max_share_position'])
    assert 0 <= context.max_total_position <= 1
    assert 0 <= context.max_share_position <= 1
    assert context.max_total_position >= context.max_share_position >= 0

    context.logger.info("回测配置：")
    context.logger.info("backtest_start_time = " + str(context.backtest_start_time))
    context.logger.info("backtest_end_time = " + str(context.backtest_end_time))
    context.logger.info(f"总仓位控制：{context.max_total_position}")
    context.logger.info(f"单仓位控制：{context.max_share_position}")
    context.logger.info(f"异常退出条件：stoploss = {context.stoploss}; timeout = {context.timeout}; wait_time = {context.wait_time}")
    context.logger.info(f"K线周期列表：{freqs}")
    context.logger.info("交易信号计算：\n" + inspect.getsource(get_signals))
    context.logger.info("交易事件定义：\n" + inspect.getsource(get_events))

    events = get_events()
    context.logger.info(f"交易标的数量：{len(symbols)}")
    symbols_map = {symbol: dict() for symbol in symbols}
    for symbol in symbols:
        try:
            symbols_map[symbol]['mp'] = context.max_share_position
            kg = get_init_kg(symbol, context.now, max_count=2000, adjust=ADJUST_POST, freqs=freqs)
            trader = CzscTrader(op_freq=op_freq, kg=kg, get_signals=get_signals, events=events)
            symbols_map[symbol]['trader'] = trader
            context.logger.info("{} 初始化完成，当前时间：{}".format(symbol, trader.end_dt))
        except:
            del symbols_map[symbol]
            print(f'init kg fail on {symbol}')

    subscribe(",".join(symbols_map.keys()), frequency='60s', count=300, wait_group=True)
    context.logger.info(f"交易标的配置：{symbols_map}")
    context.symbols_map = symbols_map

