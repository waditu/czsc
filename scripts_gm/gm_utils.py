# coding: utf-8
"""

"""
import os
from gm.api import *
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
import pandas as pd
from czsc.analyze import CzscTrader, KlineGenerator, RawBar
from czsc.signals import get_default_signals
from czsc.enum import Freq, Operate
from czsc.utils.qywx import push_file, push_text

dt_fmt = "%Y-%m-%d %H:%M:%S"


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

indices = {
    "上证指数": 'SHSE.000001',
    "创业板指数": 'SZSE.399006',
    "上证50": 'SHSE.000016',
    "深证成指": "SZSE.399001",
    "沪深300": "SHSE.000300",
    "深次新股": "SZSE.399678",
    "中小板指": "SZSE.399005",
}


def get_index_shares(name, end_date=None):
    """获取某一交易日的指数成分股列表

    symbols = get_index_shares("上证50", "2019-01-01 09:30:00")
    """
    date_fmt = "%Y-%m-%d"
    if not end_date:
        end_date = datetime.now().strftime(date_fmt)
    else:
        end_date = pd.to_datetime(end_date).strftime(date_fmt)
    constituents = get_history_constituents(indices[name], end_date, end_date)[0]
    symbol_list = [k for k, v in constituents['constituents'].items()]
    return list(set(symbol_list))


def get_contract_basic(symbol, trade_date=None):
    """获取合约信息

    https://www.myquant.cn/docs/python/python_select_api#8ba2064987fb1d1f

    https://www.myquant.cn/docs/python/python_select_api#8f28e1de81b80633
    """
    if not trade_date:
        res = get_instruments(symbol)
        if not res:
            return None
        return res[0]
    else:
        res = None


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
        p_report = f"持仓标的：{p.symbol}，数量：{p.volume}，成本：{round(p.vwap, 2)}，方向：{p.side}，" \
                   f"当前价：{round(p.price, 2)}，成本市值：{int(p.volume * p.vwap)}，" \
                   f"建仓时间：{p.created_at.strftime(dt_fmt)}"
        logger.info(p_report)


# ======================================================================================================================
# 掘金系统回调函数
# ======================================================================================================================
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
          f"操作：{trader.op['operate'] + '#' + trader.op['desc']}\n" \
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

    push_text(content=content, key=context.wx_key)

    for symbol in context.symbols:
        # 查看买卖详情
        file_bs = os.path.join(context.cache_path, "{}_bs.txt".format(symbol))
        if os.path.exists(file_bs):
            lines = [eval(x) for x in open(file_bs, 'r', encoding="utf-8").read().strip().split("\n")]
            df = pd.DataFrame(lines)
            print(symbol, "\n", df.desc.value_counts())
            print(df)


def on_error(context, code, info):
    logger = context.logger
    msg = "{} - {}".format(code, info)
    logger.warn(msg)
    if context.mode != MODE_BACKTEST:
        push_text(content=msg, key=context.wx_key)


def on_account_status(context, account):
    """响应交易账户状态更新事件，交易账户状态变化时被触发"""
    context.logger.info(str(account))
    push_text(str(account), key=context.wx_key)


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

    :param symbol:
    :param end_time:
    :param freq:
    :param count:
    :param adjust:
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


def format_tick(tick):
    k = {'symbol': tick['symbol'],
         'dt': tick['created_at'],
         'price': tick['price'],
         'vol': tick['last_volume']}
    return k


def get_ticks(symbol, end_time, count=33000):
    if isinstance(end_time, datetime):
        end_time = end_time.strftime(dt_fmt)
    data = history_n(symbol=symbol, frequency="tick", end_time=end_time, count=count, df=False, adjust=1)
    return data


# ======================================================================================================================
# 实盘&仿真&回测共用函数
# ======================================================================================================================
def get_init_kg(symbol: str,
                end_dt: [str, datetime],
                generator: [KlineGenerator] = KlineGenerator,
                freqs=('1分钟', '5分钟', '15分钟', "30分钟", '60分钟', "日线"),
                max_count=1000,
                adjust=ADJUST_PREV):
    """获取symbol的初始化kline generator"""
    freq_map_ = {"1分钟": '60s', "5分钟": '300s', "15分钟": '900s', "30分钟": '1800s', "60分钟": '3600s', "日线": '1d'}
    end_dt = pd.to_datetime(end_dt, utc=True)
    end_dt = end_dt.tz_convert('dateutil/PRC')
    last_day = (end_dt - timedelta(days=1)).replace(hour=16, minute=0)

    kg = generator(max_count=max_count, freqs=freqs)

    for freq in freqs:
        bars = get_kline(symbol=symbol, end_time=last_day, freq=freq_map_[freq], count=max_count, adjust=adjust)
        kg.init_kline(freq, bars)
        print(f"{symbol} - {freq} - last_dt: {kg.get_kline(freq, 1)[-1].dt} - last_day: {last_day}")

    bars = get_kline(symbol=symbol, end_time=end_dt, freq="60s", count=300)
    data = [x for x in bars if x.dt > last_day]

    if data:
        print(f"{symbol}: 更新 kg 至 {end_dt.strftime(dt_fmt)}，共有{len(data)}行数据需要update")
        for row in data:
            kg.update(row)
    return kg


def write_bs(context, symbol, bs):
    """把bs详细信息写入文本文件"""
    file_bs = os.path.join(context.cache_path, "{}_bs.txt".format(symbol))
    with open(file_bs, 'a', encoding="utf-8") as f:
        row = dict(bs)
        row['dt'] = row['dt'].strftime("%Y-%m-%d %H:%M:%S")
        f.write(str(row) + "\n")


def take_snapshot(context, trader, name):
    """

    :param context:
    :param trader:
    :param name: str
        平多、平空、开多、开空、快照
    :return:
    """
    symbol = trader.symbol
    now_ = context.now.strftime('%Y%m%d_%H%M')
    price = trader.latest_price
    file_html = os.path.join(context.cache_path, f"{symbol}_{price}_{now_}.html")
    trader.take_snapshot(file_html, width="1400px", height="580px")
    print(f"snapshot saved into {file_html}")
    if context.mode != MODE_BACKTEST:
        push_file(file_html, key=context.wx_key)


def adjust_future_position(context, symbol: str, trader: CzscTrader, mp: float):
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
            # take_snapshot(context, trader, name=trader.op['desc'])

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
            # take_snapshot(context, trader, name=trader.op['desc'])

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
            # take_snapshot(context, trader, name=trader.op['desc'])
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
            # take_snapshot(context, trader, name=trader.op['desc'])
            write_bs(context, symbol, trader.op)


def adjust_share_position(context, symbol: str, trader: CzscTrader, mp: float):
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
        account = context.account(account_id=context.share_id)

    long_position = account.positions(symbol=symbol, side=PositionSide_Long)
    if long_position:
        # 判断是否需要平多仓
        lp = long_position[0].volume - long_position[0].volume_today
        oe = is_order_exist(context, symbol, OrderSide_Sell, PositionEffect_Close)
        in_trade_time = "14:59" > context.now.strftime("%H:%M") > "09:31"

        if not oe and trader.op['operate'] == Operate.LE.value and in_trade_time:
            if lp <= 0:
                context.logger.info("{} - 昨仓为零，禁止平多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
            else:
                context.logger.info("{} - 平多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))
                write_bs(context, symbol, trader.op)
                order_volume(symbol=symbol, volume=lp, side=OrderSide_Sell, order_type=OrderType_Market,
                             position_effect=PositionEffect_Close, account=account.id)
                # take_snapshot(context, trader, name=trader.op['desc'])
    else:
        # 判断是否需要开多仓
        oe = is_order_exist(context, symbol, OrderSide_Buy, PositionEffect_Open)
        in_trade_time = "14:59" > context.now.strftime("%H:%M") > "09:31"
        if not oe and trader.op['operate'] == Operate.LO.value and in_trade_time:
            context.logger.info("{} - 开多 - {} - {}".format(symbol, trader.op['desc'], trader.latest_price))

            # 判断总仓位是否已经达到限制水平
            if 1 - account.cash.available / account.cash.nav > context.max_total_position:
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
            # take_snapshot(context, trader, name=trader.op['desc'])
            write_bs(context, symbol, trader.op)


# ======================================================================================================================
# 实盘&仿真专用函数
# ======================================================================================================================
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


class GmCzscTrader(CzscTrader):
    def __init__(self, symbol, end_dt=None, max_count=2000):
        self.symbol = symbol
        self.freq_map = {"1分钟": '60s', "5分钟": '300s', "15分钟": '900s', "30分钟": '1800s',
                         "60分钟": '3600s', "日线": '1d'}

        if not end_dt:
            end_dt = datetime.now(timezone(timedelta(hours=8)))
        kg = get_init_kg(symbol, end_dt, max_count=max_count, freqs=['1分钟', '5分钟', '15分钟', '30分钟', '60分钟', '日线'])
        super(GmCzscTrader, self).__init__(kg, get_signals=get_default_signals, events=[])

    def get_latest_kline(self):
        exchange = self.symbol.split('.')[0]
        if exchange in ["SZSE", "SHSE"]:
            fields = 'symbol,eob,open,close,high,low,volume'
        else:
            fields = 'symbol,eob,open,close,high,low,volume,position'
        df = history(self.symbol, '60s', start_time=self.end_dt, end_time=datetime.now(), fields=fields,
                     skip_suspended=True, fill_missing=None, adjust=ADJUST_NONE, adjust_end_time='', df=True)
        return format_kline(df, Freq.F1)

    def update_factors(self):
        """更新K线数据到最新状态"""
        bars = self.get_latest_kline()
        if not bars or bars[-1].dt <= self.end_dt:
            return
        for bar in bars:
            self.check_operate(bar)
