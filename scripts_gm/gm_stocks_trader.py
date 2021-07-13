# coding: utf-8
"""掘金实盘仿真"""
import time
import inspect
from pprint import pprint
import traceback
from czsc.utils import create_logger, save_pkl, read_pkl

from scripts_gm.gm_utils import *
from czsc.objects import Event, Factor, Signal
from scripts_gm.gm_utils import GmCzscTrader
from scripts_gm.gm_selector import run_selector
from scripts_gm.strategy import get_signals_share_f15_v1 as get_user_signals
from scripts_gm.strategy import get_events_share_f15_v1 as get_user_events
from scripts_gm.strategy import freqs_share_f15_v1 as user_freqs

# 掘金仿真/实盘配置
wx_key = "909731bd-****-****-****-24b9830873a4"         # 企业微信群聊机器人 key
share_id = "2c632491-****-****-****-00163e0a4100"       # 掘金账户 id
sid = 'c7e84d1c-****-****-****-38f3abf8ed06'            # 掘金策略 id


def adjust_position(context, symbol):
    bars = context.data(symbol=symbol, frequency='60s', count=100, fields='symbol,eob,open,close,high,low,volume')
    trader = context.symbols_map[symbol]['trader']
    mp = context.symbols_map[symbol]['mp']
    bars = format_kline(bars, Freq.F1)
    bars_new = [x for x in bars if x.dt > trader.kg.end_dt]
    if bars_new:
        for k in bars_new:
            trader.check_operate(k, context.stoploss, context.timeout)
    context.symbols_map[symbol]['trader'] = trader
    print(trader.op)

    file_gt = os.path.join(context.data_path, "{}.gt".format(symbol))
    save_pkl(trader, file_gt)
    exchange = symbol.split(".")[0]
    assert exchange in ["SZSE", "SHSE"]
    adjust_share_position(context, symbol, trader, mp)


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
        msg += f'标的代码：{p.symbol}\n' \
               f'持仓数量：{p.volume}\n' \
               f'最新价格：{round(p.price, 2)}\n' \
               f'持仓成本：{round(p.vwap, 2)}\n' \
               f'盈亏比例：{int((p.price - p.vwap) / p.vwap * 10000) / 100}%\n' \
               f'持仓市值：{int(p.volume * p.vwap)}\n' \
               f"{'*' * 31}\n"

    push_text(msg.strip("\n *"), key=context.wx_key)


def monitor(context):
    """对实盘股票池进行定时监控"""
    symbols = list(context.symbols_map.keys())

    events = get_user_events()
    events_monitor = [
        # 开多
        Event(name="一买", operate=Operate.LO, factors=[
            Factor(name="5分钟类一买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
            Factor(name="5分钟形一买", signals_all=[Signal("5分钟_倒1笔_基础形态_类一买_任意_任意_0")]),

            Factor(name="15分钟类一买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
            Factor(name="15分钟形一买", signals_all=[Signal("15分钟_倒1笔_基础形态_类一买_任意_任意_0")]),

            Factor(name="30分钟类一买", signals_all=[Signal("30分钟_倒1笔_类买卖点_类一买_任意_任意_0")]),
            Factor(name="30分钟形一买", signals_all=[Signal("30分钟_倒1笔_基础形态_类一买_任意_任意_0")]),
        ]),

        Event(name="二买", operate=Operate.LO, factors=[
            Factor(name="5分钟类二买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
            Factor(name="5分钟形二买", signals_all=[Signal("5分钟_倒1笔_基础形态_类二买_任意_任意_0")]),

            Factor(name="15分钟类二买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
            Factor(name="15分钟形二买", signals_all=[Signal("15分钟_倒1笔_基础形态_类二买_任意_任意_0")]),

            Factor(name="30分钟类二买", signals_all=[Signal("30分钟_倒1笔_类买卖点_类二买_任意_任意_0")]),
            Factor(name="30分钟形二买", signals_all=[Signal("30分钟_倒1笔_基础形态_类二买_任意_任意_0")]),
        ]),
        Event(name="三买", operate=Operate.LO, factors=[
            Factor(name="5分钟类三买", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
            Factor(name="5分钟形三买", signals_all=[Signal("5分钟_倒1笔_基础形态_类三买_任意_任意_0")]),

            Factor(name="15分钟类三买", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
            Factor(name="15分钟形三买", signals_all=[Signal("15分钟_倒1笔_基础形态_类三买_任意_任意_0")]),

            Factor(name="30分钟类三买", signals_all=[Signal("30分钟_倒1笔_类买卖点_类三买_任意_任意_0")]),
            Factor(name="30分钟形三买", signals_all=[Signal("30分钟_倒1笔_基础形态_类三买_任意_任意_0")]),
        ]),

        # 平多
        Event(name="一卖", operate=Operate.LE, factors=[
            Factor(name="5分钟类一卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="5分钟形一卖", signals_all=[Signal("5分钟_倒1笔_基础形态_类一卖_任意_任意_0")]),

            Factor(name="15分钟类一卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="15分钟形一卖", signals_all=[Signal("15分钟_倒1笔_基础形态_类一卖_任意_任意_0")]),

            Factor(name="30分钟类一卖", signals_all=[Signal("30分钟_倒1笔_类买卖点_类一卖_任意_任意_0")]),
            Factor(name="30分钟形一卖", signals_all=[Signal("30分钟_倒1笔_基础形态_类一卖_任意_任意_0")]),
        ]),
        Event(name="二卖", operate=Operate.LE, factors=[
            Factor(name="5分钟类二卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
            Factor(name="5分钟形二卖", signals_all=[Signal("5分钟_倒1笔_基础形态_类二卖_任意_任意_0")]),

            Factor(name="15分钟类二卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
            Factor(name="15分钟形二卖", signals_all=[Signal("15分钟_倒1笔_基础形态_类二卖_任意_任意_0")]),

            Factor(name="30分钟类二卖", signals_all=[Signal("30分钟_倒1笔_类买卖点_类二卖_任意_任意_0")]),
            Factor(name="30分钟形二卖", signals_all=[Signal("30分钟_倒1笔_基础形态_类二卖_任意_任意_0")]),
        ]),
        Event(name="三卖", operate=Operate.LE, factors=[
            Factor(name="5分钟类三卖", signals_all=[Signal("5分钟_倒1笔_类买卖点_类三卖_任意_任意_0")]),
            Factor(name="5分钟形三卖", signals_all=[Signal("5分钟_倒1笔_基础形态_类三卖_任意_任意_0")]),

            Factor(name="15分钟类三卖", signals_all=[Signal("15分钟_倒1笔_类买卖点_类三卖_任意_任意_0")]),
            Factor(name="15分钟形三卖", signals_all=[Signal("15分钟_倒1笔_基础形态_类三卖_任意_任意_0")]),

            Factor(name="30分钟类三卖", signals_all=[Signal("30分钟_倒1笔_类买卖点_类三卖_任意_任意_0")]),
            Factor(name="30分钟形三卖", signals_all=[Signal("30分钟_倒1笔_基础形态_类三卖_任意_任意_0")]),
        ]),
    ]
    events.extend(events_monitor)

    data_path = os.path.join(context.data_path, 'monitor')
    os.makedirs(data_path, exist_ok=True)
    qywx_key = context.wx_key
    push_text("实盘池监控启动 @ {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")), qywx_key)

    for symbol in symbols:
        try:
            file_ct = os.path.join(data_path, "{}.ct".format(symbol))
            if os.path.exists(file_ct):
                ct: GmCzscTrader = read_pkl(file_ct)
                ct.update_factors()
            else:
                ct = GmCzscTrader(symbol, max_count=2000)
            save_pkl(ct, file_ct)
            print(f"run monitor on {symbol} at {ct.end_dt}")
            msg = f"标的代码：{symbol}\n同花顺F10：http://basic.10jqka.com.cn/{symbol.split('.')[1]}\n"
            for event in events:
                m, f = event.is_match(ct.s)
                if m:
                    msg += "监控提醒：{}@{}\n".format(event.name, f)

            if "监控提醒" in msg:
                push_text(msg.strip("\n"), key=qywx_key)

        except Exception as e:
            traceback.print_exc()
            print("{} 执行失败 - {}".format(symbol, e))
    push_text("实盘池监控结束 @ {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")), qywx_key)


def init(context):
    assert context.mode != MODE_BACKTEST, "gm_stocks_trader.py 是实盘仿真脚本，回测请使用 gm_backtest_1min.py"
    path_gm_logs = "C:/gm_logs"
    data_path = os.path.join(path_gm_logs, 'stocks_trader')
    cache_path = os.path.join(data_path, "cache")
    os.makedirs(cache_path, exist_ok=True)

    context.wx_key = wx_key
    context.share_id = share_id
    context.future_id = None
    context.logger = create_logger(os.path.join(data_path, "simulator.log"), cmd=True, name="gm")
    context.data_path = data_path
    context.cache_path = cache_path
    context.file_orders = os.path.join(data_path, "orders.txt")
    context.ipo_shares = []
    context.stoploss = 0.05     # 止损条件设定
    context.timeout = 600       # 超时条件设定

    # 仓位控制[0, 1]，按资金百分比控制，1表示满仓，仅在开仓的时候控制
    context.max_total_position = 0.8
    context.max_share_position = 0.5
    assert 0 <= context.max_total_position <= 1
    assert 0 <= context.max_share_position <= 1
    assert context.max_total_position >= context.max_share_position >= 0

    context.logger.info("=" * 88)
    context.logger.info("实盘仿真开始 ...")
    context.logger.info(f"总仓位控制：{context.max_total_position}")
    context.logger.info(f"单仓位控制：{context.max_share_position}")
    context.logger.info(f"异常退出条件：stoploss = {context.stoploss}; timeout = {context.timeout}")
    context.logger.info("交易使用的信号定义如下：\n" + inspect.getsource(get_user_signals))
    context.logger.info("交易使用的买卖点定义如下：\n" + inspect.getsource(get_user_events))

    # 读取自选股，转成 gm symbol
    file_zx = os.path.join(path_gm_logs, "ZB20210628.xlsx")
    push_text("实盘仿真开始，以下是程序股票池：", wx_key)
    push_file(file_zx, wx_key)
    symbols = pd.read_excel(file_zx)['股票代码'].unique().tolist()
    to_gm_symbol = lambda x: "SHSE." + x[:6] if x[0] == "6" else "SZSE." + x[:6]
    symbols = [to_gm_symbol(x) for x in symbols]

    # 查询当前持仓，保证持仓标的在交易标的列表中
    positions = context.account(account_id=context.share_id).positions(symbol="", side="")
    if positions:
        p_symbols = [p.symbol for p in positions]
        symbols += p_symbols
    symbols = sorted(list(set(symbols)))
    context.logger.info(f"交易标的数量：{len(symbols)}")

    symbols_map = {symbol: dict() for symbol in symbols}
    for symbol in symbols:
        symbols_map[symbol]['mp'] = context.max_share_position
        try:
            file_gt = os.path.join(data_path, "{}.gt".format(symbol))
            if os.path.exists(file_gt) and time.time() - os.path.getmtime(file_gt) < 3600 * 24:
                trader: CzscTrader = read_pkl(file_gt)
                context.logger.info("{} 加载成功，最新K线时间：{}".format(file_gt, trader.end_dt.strftime(dt_fmt)))
            else:
                kg = get_init_kg(symbol, context.now, max_count=2000, adjust=ADJUST_PREV, freqs=user_freqs)
                trader = CzscTrader(kg, get_signals=get_user_signals, events=get_user_events())
                symbols_map[symbol]['trader'] = trader
                context.logger.info("{} 初始化完成，最新K线时间：{}".format(symbol, trader.end_dt.strftime(dt_fmt)))
                save_pkl(trader, file_gt)

            symbols_map[symbol]['trader'] = trader
        except:
            traceback.print_exc()
            context.logger.info("{} 初始化失败".format(symbol))

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
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='13:31:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='14:01:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='14:31:00')
    schedule(schedule_func=report_stocks_account_status, date_rule='1d', time_rule='15:01:00')
    schedule(schedule_func=run_selector, date_rule='1d', time_rule='15:05:00')
    schedule(schedule_func=monitor, date_rule='1d', time_rule='09:15:00')
    schedule(schedule_func=monitor, date_rule='1d', time_rule='11:45:00')
    schedule(schedule_func=monitor, date_rule='1d', time_rule='15:15:00')

def on_bar(context, bars):
    context.unfinished_orders = get_unfinished_orders()
    cancel_timeout_orders(context, max_m=10)

    for bar in bars:
        symbol = bar['symbol']
        try:
            adjust_position(context, symbol)
        except:
            traceback.print_exc()


if __name__ == '__main__':
    run(strategy_id=sid, mode=MODE_LIVE, filename='gm_stocks_trader.py', token=gm_token)

