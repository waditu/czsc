# coding: utf-8
import inspect
from czsc.analyze import *
from czsc.utils.log import create_logger
from scripts_gm.gm_utils import *
from scripts_gm.strategy import get_signals_share_f15_v1 as get_user_signals
from scripts_gm.strategy import get_events_share_f15_v1 as get_user_events
from scripts_gm.strategy import freqs_share_f15_v1 as user_freqs


def adjust_position(context, symbol):
    bars = context.data(symbol=symbol, frequency='60s', count=100, fields='symbol,eob,open,close,high,low,volume')
    trader: CzscTrader = context.symbols_map[symbol]['trader']
    mp = context.symbols_map[symbol]['mp']
    bars = format_kline(bars, freq=Freq.F1)
    bars_new = [x for x in bars if x.dt > trader.kg.end_dt]
    if bars_new:
        for k in bars_new:
            trader.check_operate(k, context.stoploss, context.timeout)
    context.symbols_map[symbol]['trader'] = trader
    last_bar = bars[-1]
    if last_bar.dt.minute % 30 == 0:
        print(trader.op)

    exchange = symbol.split(".")[0]
    if exchange in ["SZSE", "SHSE"]:
        adjust_share_position(context, symbol, trader, mp)
    else:
        adjust_future_position(context, symbol, trader, mp)


def init(context):
    data_path = "C:/gm_logs/1min_{}".format(datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))

    # 填写企业微信群聊机器人的 key，会发送消息到对应企业微信群聊
    context.wx_key = "2daec96b-f3f1-****-****-2952fe2731c0"

    cache_path = os.path.join(data_path, "cache")
    os.makedirs(cache_path, exist_ok=False)
    context.logger = create_logger(os.path.join(data_path, "backtest.log"), cmd=True, name="gm")
    context.data_path = data_path
    context.cache_path = cache_path
    context.file_orders = os.path.join(data_path, "orders.txt")

    context.stoploss = 0.05     # 止损条件设定
    context.timeout = 600      # 超时条件设定

    # 仓位控制[0, 1]，按资金百分比控制，1表示满仓，仅在开仓的时候控制
    context.max_total_position = 0.3
    context.max_share_position = 0.3
    assert 0 <= context.max_total_position <= 1
    assert 0 <= context.max_share_position <= 1
    assert context.max_total_position >= context.max_share_position >= 0

    context.logger.info("回测配置：")
    context.logger.info("backtest_start_time = " + str(context.backtest_start_time))
    context.logger.info("backtest_end_time = " + str(context.backtest_end_time))
    context.logger.info(f"异常退出条件：stoploss = {context.stoploss}; timeout = {context.timeout}")
    context.logger.info("交易使用的信号定义如下：\n" + inspect.getsource(get_user_signals))
    context.logger.info("交易使用的买卖点定义如下：\n" + inspect.getsource(get_user_events))

    symbols = [
        'SHSE.510500',
        'SZSE.300014',
        'SHSE.600143'
    ]
    context.logger.info(f"交易标的数量：{len(symbols)}")

    symbols_map = {symbol: dict() for symbol in symbols}
    for symbol in symbols:
        try:
            symbols_map[symbol]['mp'] = context.max_share_position
            kg = get_init_kg(symbol, context.now, max_count=2000, adjust=ADJUST_POST, freqs=user_freqs)
            trader = CzscTrader(kg, get_signals=get_user_signals, events=get_user_events())
            symbols_map[symbol]['trader'] = trader
            context.logger.info("{} 初始化完成，当前时间：{}".format(symbol, trader.end_dt))
        except:
            traceback.print_exc()
            context.logger.info("{} 初始化失败".format(symbol))

    subscribe(",".join(symbols_map.keys()), frequency='60s', count=300, wait_group=True)
    context.logger.info(f"交易标的配置：{symbols_map}")
    context.symbols_map = symbols_map


def on_bar(context, bars):
    context.unfinished_orders = get_unfinished_orders()

    for bar in bars:
        symbol = bar['symbol']
        try:
            adjust_position(context, symbol)
        except:
            traceback.print_exc()

    if context.now.hour == 13 and context.now.minute == 59:
        report_account_status(context)


if __name__ == '__main__':
    run(filename='gm_backtest_1min.py', token=gm_token,
        strategy_id='692dc7b5-d19f-11eb-af0a-38f3abf8ed06',
        mode=MODE_BACKTEST,
        backtest_start_time='2020-01-06 14:30:00',
        backtest_end_time='2020-12-31 15:30:00',
        backtest_initial_cash=100000000,
        backtest_transaction_ratio=1,
        backtest_commission_ratio=0.001,
        backtest_slippage_ratio=0.0005,
        backtest_adjust=ADJUST_POST,
        backtest_check_cache=1)
