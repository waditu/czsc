# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/11/17 22:11
describe: 配合 CzscAdvancedTrader 进行使用的掘金工具
"""
import inspect
import traceback
from czsc.gms.gm_base import *
from czsc.utils import create_logger
from czsc.objects import PositionLong, Operate


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
        trader: CzscAdvancedTrader = context.symbols_info[symbol]['trader']

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
               f"标的数量：{len(positions)}\n"
        wx.push_text(msg.strip("\n *"), key=context.wx_key)

        results = []
        for symbol, info in context.symbols_info.items():
            name = context.stocks.get(symbol, '无名')
            trader: CzscAdvancedTrader = context.symbols_info[symbol]['trader']
            p = account.position(symbol=symbol, side=PositionSide_Long)

            row = {'交易标的': symbol, '标的名称': name,
                   '最新时间': trader.end_dt.strftime(dt_fmt),
                   '最新价格': trader.latest_price}

            if "日线" in trader.kas.keys():
                bar1, bar2 = trader.kas['日线'].bars_raw[-2:]
                row.update({'昨日收盘': round(bar1.close, 2),
                            '今日涨幅': round(bar2.close / bar1.close - 1, 4)})

            if trader.long_pos.pos > 0:
                row.update({'多头持仓': trader.long_pos.pos,
                            '多头成本': trader.long_pos.long_cost,
                            '多头收益': round(trader.latest_price / trader.long_pos.long_cost - 1, 4),
                            '开多时间': trader.long_pos.operates[-1]['dt'].strftime(dt_fmt)})
            else:
                row.update({'多头持仓': 0, '多头成本': 0, '多头收益': 0, '开多时间': None})

            if p:
                row.update({"实盘持仓数量": p.volume,
                            "实盘持仓成本": round(p.vwap, 2),
                            "实盘持仓市值": int(p.volume * p.vwap)})
            else:
                row.update({"实盘持仓数量": 0,  "实盘持仓成本": 0, "实盘持仓市值": 0})

            results.append(row)

        df = pd.DataFrame(results)
        df.sort_values(['多头持仓', '多头收益'], ascending=False, inplace=True, ignore_index=True)
        file_xlsx = os.path.join(context.data_path, f"holds_{context.now.strftime('%Y%m%d_%H%M')}.xlsx")
        df.to_excel(file_xlsx, index=False)
        wx.push_file(file_xlsx, key=context.wx_key)
        os.remove(file_xlsx)

        # 提示非策略交易标的持仓
        process_out_of_symbols(context)


def sync_long_position(context, trader: CzscAdvancedTrader):
    """同步多头仓位到交易账户"""
    if not trader.long_events:
        return

    symbol = trader.symbol
    name = context.stocks.get(symbol, "无名标的")
    long_pos: PositionLong = trader.long_pos
    max_sym_pos = context.symbols_info[symbol]['max_sym_pos']  # 最大标的仓位
    logger = context.logger
    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.account_id)
    cash = account.cash

    price = trader.latest_price
    print(f"{trader.end_dt}: {name}，多头：{long_pos.pos}，成本：{long_pos.long_cost}，"
          f"现价：{price}，操作次数：{len(long_pos.operates)}")

    algo_name = os.environ.get('algo_name', None)
    if algo_name:
        # 算法名称，TWAP、VWAP、ATS-SMART、ZC-POV
        algo_name = algo_name.upper()
        start_time = trader.end_dt.strftime("%H:%M:%S")
        end_time = (trader.end_dt + timedelta(minutes=30)).strftime("%H:%M:%S")
        end_time = min(end_time, '14:55:00')

        if algo_name == 'TWAP' or algo_name == 'VWAP' or algo_name == 'ZC-POV':
            algo_param = {
                "start_time": start_time,
                "end_time": end_time,
                "part_rate": 0.5,
                "min_amount": 5000,
            }
        elif algo_name == 'ATS-SMART':
            algo_param = {
                'start_time': start_time,
                'end_time_referred': end_time,
                'end_time': end_time,
                'end_time_valid': 1,
                'stop_sell_when_dl': 1,
                'cancel_when_pl': 0,
                'min_trade_amount': 5000
            }
        else:
            raise ValueError("算法单名称输入错误")
    else:
        algo_param = {}

    sym_position = account.position(symbol, PositionSide_Long)
    if long_pos.pos == 0 and not sym_position:
        # 如果多头仓位为0且掘金账户没有对应持仓，直接退出
        return

    if long_pos.pos == 0 and sym_position and sym_position.volume > 0:
        # 如果多头仓位为0且掘金账户依然还有持仓，清掉仓位
        volume = sym_position.volume
        if algo_name:
            assert len(algo_param) > 0, f"error: {algo_name}, {algo_param}"
            _ = algo_order(symbol=symbol, volume=volume, side=OrderSide_Sell,
                           order_type=OrderType_Limit, position_effect=PositionEffect_Close,
                           price=price, algo_name=algo_name, algo_param=algo_param, account=account.id)
        else:
            order_target_volume(symbol=symbol, volume=0, position_side=PositionSide_Long,
                                order_type=OrderType_Limit, price=price, account=account.id)
        return

    if not long_pos.pos_changed:
        return

    assert long_pos.pos > 0
    cash_left = cash.available
    if long_pos.operates[-1]['op'] in [Operate.LO, Operate.LA1, Operate.LA2]:
        change_amount = max_sym_pos * long_pos.operates[-1]['pos_change'] * cash.nav
        if cash_left < change_amount:
            logger.info(f"{context.now} {symbol} {name} 可用资金不足，无法开多仓；"
                        f"剩余资金{int(cash_left)}元，所需资金{int(change_amount)}元")
            return

    if is_order_exist(context, symbol, PositionSide_Long):
        logger.info(f"{context.now} {symbol} {name} 同方向订单已存在")
        return

    percent = max_sym_pos * long_pos.pos
    volume = int((cash.nav * percent / price // 100) * 100)     # 单位：股
    if algo_name:
        _ = algo_order(symbol=symbol, volume=volume, side=OrderSide_Buy,
                       order_type=OrderType_Limit, position_effect=PositionEffect_Open,
                       price=price, algo_name=algo_name, algo_param=algo_param, account=account.id)
    else:
        order_target_volume(symbol=symbol, volume=volume, position_side=PositionSide_Long,
                            order_type=OrderType_Limit, price=price, account=account.id)


def check_index_status(qywx_key):
    """查看主要指数状态"""
    from czsc.utils.cache import home_path

    wx.push_text(f"{datetime.now()} 开始获取主要指数行情快照", qywx_key)
    for gm_symbol in indices.values():
        try:
            file_html = os.path.join(home_path, f"{gm_symbol}_{datetime.now().strftime('%Y%m%d')}.html")
            gm_take_snapshot(gm_symbol, file_html=file_html)
            wx.push_file(file_html, qywx_key)
            os.remove(file_html)
        except:
            traceback.print_exc()
    wx.push_text(f"{datetime.now()} 获取主要指数行情快照获取结束，请仔细观察！！！", qywx_key)


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
        wx.push_text(f"不在交易列表的持仓股：{', '.join(oos)}", context.wx_key)


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
    context.logger = create_logger(os.path.join(data_path, "gm_trader.log"), cmd=True, name="gm")

    context.logger.info("运行配置：")
    context.logger.info(f"data_path = {data_path}")

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

    # 单个标的仓位控制[0, 1]，按资金百分比控制，1表示满仓，仅在开仓的时候控制
    context.max_sym_pos = float(os.environ['max_sym_pos'])
    assert 0 <= context.max_sym_pos <= 1

    logger = context.logger
    logger.info(f"环境变量读取结果如下：")
    logger.info(f"单标的控制：context.max_sym_pos = {context.max_sym_pos}")


def init_context_traders(context, symbols: List[str], strategy: Callable):
    """通用 context 初始化：3、为每个标的创建 trader

    :param context:
    :param symbols: 交易标的列表
    :param strategy: 交易策略
    :return:
    """
    with open(os.path.join(context.data_path, f'{strategy.__name__}.txt'), mode='w') as f:
        f.write(inspect.getsource(strategy))

    tactic = strategy("000001")
    base_freq, freqs = tactic['base_freq'], tactic['freqs']
    frequency = freq_cn2gm[base_freq]
    unsubscribe(symbols='*', frequency=frequency)

    data_path = context.data_path
    logger = context.logger
    logger.info(f"输入交易标的数量：{len(symbols)}")
    logger.info(f"交易员的周期列表：base_freq = {base_freq}; freqs = {freqs}")

    os.makedirs(os.path.join(data_path, 'traders'), exist_ok=True)
    symbols_info = {symbol: dict() for symbol in symbols}
    for symbol in symbols:
        try:
            symbols_info[symbol]['max_sym_pos'] = context.max_sym_pos
            file_trader = os.path.join(data_path, f'traders/{symbol}.cat')

            if os.path.exists(file_trader) and context.mode != MODE_BACKTEST:
                trader: CzscAdvancedTrader = dill.load(open(file_trader, 'rb'))
                logger.info(f"{symbol} Loaded Trader from {file_trader}")

            else:
                bg, data = get_init_bg(symbol, context.now, base_freq, freqs, 1000, ADJUST_PREV)
                trader = create_advanced_trader(bg, data, strategy)
                dill.dump(trader, open(file_trader, 'wb'))

            symbols_info[symbol]['trader'] = trader
            logger.info("{} Trader 构建成功，最新时间：{}，多仓：{}".format(symbol, trader.end_dt, trader.long_pos.pos))

        except:
            del symbols_info[symbol]
            logger.info(f"{symbol} - {context.stocks.get(symbol, '无名')} 初始化失败，当前时间：{context.now}")
            traceback.print_exc()

    subscribe(",".join(symbols_info.keys()), frequency=frequency, count=300, wait_group=False)
    logger.info(f"订阅成功数量：{len(symbols_info)}")
    logger.info(f"交易标的配置：{symbols_info}")
    context.symbols_info = symbols_info


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
