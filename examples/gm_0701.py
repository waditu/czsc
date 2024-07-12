# -*- coding: utf-8 -*-

# 自行创建 .env 文件，并使用 dotenv 加载环境变量
import dotenv
import pytz

dotenv.load_dotenv()
from czsc.connectors.gm_connector import *
import czsc
from datetime import datetime
import json

import os

underlyer_symbols = [
    'CZCE.AP',
    'CZCE.CF',
    'CZCE.CJ',
    'CZCE.CY',
    'CZCE.ER',
    'CZCE.FG',
    'CZCE.GN',
    'CZCE.JR',
    'CZCE.LR',
    'CZCE.MA',
    'CZCE.ME',
    'CZCE.OI',
    'CZCE.PF',
    'CZCE.PK',
    'CZCE.PM',
    'CZCE.PX',
    'CZCE.RI',
    'CZCE.RM',
    'CZCE.RO',
    'CZCE.RS',
    'CZCE.SA',
    'CZCE.SF',
    'CZCE.SH',
    'CZCE.SM',
    'CZCE.SR',
    'CZCE.TA',
    'CZCE.TC',
    'CZCE.UR',
    'CZCE.WH',
    'CZCE.WS',
    'CZCE.WT',
    'CZCE.ZC',
    'DCE.A',
    'DCE.B',
    'DCE.BB',
    'DCE.C',
    'DCE.CS',
    'DCE.EB',
    'DCE.EG',
    'DCE.FB',
    'DCE.I',
    'DCE.J',
    'DCE.JD',
    'DCE.JM',
    'DCE.L',
    'DCE.LH',
    'DCE.M',
    'DCE.P',
    'DCE.PG',
    'DCE.PP',
    'DCE.RR',
    'DCE.V',
    'DCE.Y',
    'GFEX.LC',
    'GFEX.SI',
    'INE.BC',
    'INE.LU',
    'INE.NR',
    'INE.SC',
    'SHFE.AG',
    'SHFE.AL',
    'SHFE.AO',
    'SHFE.AU',
    'SHFE.BR',
    'SHFE.BU',
    'SHFE.CU',
    'SHFE.FU',
    'SHFE.HC',
    'SHFE.NI',
    'SHFE.PB',
    'SHFE.RB',
    'SHFE.RU',
    'SHFE.SN',
    'SHFE.SP',
    'SHFE.SS',
    'SHFE.WR',
    'SHFE.ZN',

]


def init(context):
    """
    1. 初始化gm_log 日志记录器
    2. 读取accountID
    3. 初始化策略配置,包括了trader,symbol_max_pos等信息
    4. 初始化定时任务,主要备份和报告账户信息

    """
    context.account_id = os.environ.get("gm_accountID")
    context.strategyname = os.path.basename(__file__)
    # # 创建文件目录和日志目录
    init_context_universal(context, context.strategyname)
    # 初始化trader,symbol_max_pos等信息
    init_config(context)
    # 初始化定时任务
    init_context_schedule(context)


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


def init_config(context):
    """初始化策略配置"""
    now_str = context.now.strftime('%Y-%m-%d')
    # 主力合约
    if context.now.hour > 18:
        date = get_next_n_trading_dates(exchange='SHSE', date=now_str, n=1)[0]
        # logger.info(date)
    else:
        date = context.now.strftime('%Y-%m-%d')
    # logger.info(date)

    # 货值等权配置品种最大手数
    pos_multiplier1 = {
        "CFFEX.IF": 1,
        "SHFE.RB": 1,
        'SHFE.RU': 1,
        'SHFE.SN': 1,
        'SHFE.SP': 1,
        'SHFE.SS': 1,
        'SHFE.WR': 1,
        'SHFE.ZN': 1,
        'SHFE.AG': 1,
        'SHFE.AL': 1,
        'SHFE.AO': 1,
        'SHFE.AU': 1,
        'SHFE.BR': 1,
        'SHFE.BU': 1,
        'SHFE.CU': 1,
        'SHFE.FU': 1,
        'SHFE.HC': 1,
        'SHFE.NI': 1,
        'SHFE.PB': 1,
    }

    pos_multiplier2 = {
        "CFFEX.IC": 1,
    }
    # 以 json 文件配置的策略，每个json文件对应一个持仓策略配置
    files_position1 = [
        r"C:\趋势研究\完全分类\15分钟趋势突破海龟1策略多60#10#60分钟完全分类16#10.json",
        r"C:\趋势研究\完全分类\15分钟趋势突破海龟1策略多60#10#日线完全分类16#10.json",

    ]

    files_position2 = [
        r"C:\趋势研究\完全分类\15分钟趋势突破海龟1策略多60#10#日线完全分类9#60.json",
        r"C:\趋势研究\完全分类\15分钟趋势突破海龟1策略多60#10#日线完全分类9#120.json",
    ]
    # feishu_key = "d1a3d99f-5d74-41f2-b8b1-2517750d2ea6"
    context.feishu_key = "05ecf70e-f65a-4bd8-985a-5a232b903225"

    context.symbol_metas = {}
    for symbol, _ in pos_multiplier1.items():
        # 取主力合约
        csymbol = \
            fut_get_continuous_contracts(symbol, start_date=date, end_date=date)[0]['symbol']
        # print(csymbol)
        meta = create_symbol_trader(context, csymbol, files_position=files_position1, sdt="2024-07-01")
        context.symbol_metas[csymbol] = meta
        context.symbol_metas[csymbol]['max_pos'] = pos_multiplier1.get(symbol)

        # context.symbol_metas[csymbol]['tactic'] = czsc.CzscJsonStrategy(symbol=symbol, files_position=files_position1)

    for symbol, _ in pos_multiplier2.items():
        # 取主力合约
        csymbol = \
            fut_get_continuous_contracts(symbol, start_date=date, end_date=date)[0]['symbol']
        # print(csymbol)
        meta = create_symbol_trader(context, csymbol, files_position=files_position2, sdt="2024-07-01")
        context.symbol_metas[csymbol] = meta
        context.symbol_metas[csymbol]['max_pos'] = pos_multiplier2.get(symbol)

    # logger.info(context.symbol_metas)
    logger.info(f"策略初始化完成：{list(context.symbol_metas.keys())}")

    # 订阅行情
    subscribe(list(context.symbol_metas.keys()), '900s', count=100,
              fields='symbol,eob,open,close,high,low,volume,amount',
              unsubscribe_previous=True, format='df')

    # 有持仓时，检查持仓的合约是否为主力合约,非主力合约则卖出
    context.accountID = os.environ.get("gm_accountID")
    Account_positions = get_position(context.accountID)
    if Account_positions:
        for posi in Account_positions:
            if posi['symbol'] not in context.symbol_metas.keys():
                print('{}：持仓合约由{}替换为主力合约'.format(context.now, posi['symbol']))
                new_price = current(symbols=posi['symbol'])[0]['price']
                order_target_volume(symbol=posi['symbol'],
                                    volume=0,
                                    position_side=posi['side'],
                                    order_type=OrderType_Limit,
                                    price=new_price)


def on_bar(context, bars):
    # pass

    context.unfinished_orders = get_unfinished_orders()
    cancel_timeout_orders(context, max_m=30)
    # 更新trader
    for bar in bars:
        symbol = bar['symbol']
        logger.info(f"{symbol} - {bar} - {bar['eob']}")
        trader: CzscTrader = context.symbol_metas[symbol]['trader']

        base_freq = trader.base_freq
        bars = context.data(symbol=symbol, frequency=freq_cn2gm[base_freq], count=10,
                            fields='symbol,eob,open,close,high,low,volume,amount')

        bars = format_kline(bars, freq=trader.bg.freq_map[base_freq])
        bars_new = [x for x in bars if x.dt > trader.end_dt and x.vol > 0]
        logger.info(f"{symbol} - {bars_new[-1]}")
        #
        if not bars_new:
            logger.warning(f"{symbol} 没有新的K线")
            continue
        #
        if bars_new:
            for bar_ in bars_new:
                trader.update(bar_)

        if trader.pos_changed:
            # 消息推送，必须放在 is_changing 判断之后，这样可以保证消息的准确，同时不推送大量重复消息
            send_trader_change(trader, feishu_key=context.feishu_key, ensemble_method="mean",
                               symbol_max_pos=context.symbol_metas[symbol]['max_pos'], ensemble_desc="取均值")

        sync_position(context, trader)


def create_symbol_trader(context, symbol, **kwargs):
    """创建一个品种的 CzscTrader, 回测与实盘场景同样适用

    :param symbol: 合约代码
    """
    adj_type = kwargs.get("adj_type", ADJUST_PREV)
    files_position = kwargs.get("files_position")
    tactic = czsc.CzscJsonStrategy(symbol=symbol, files_position=files_position)
    frequency = int(tactic.base_freq.strip("分钟")) * 60
    kline = history_n(symbol, f'{frequency}s', count=1000, end_time=None,
                      fields="symbol,eob,open,close,high,low,volume,amount",
                      skip_suspended=True, fill_missing=None, adjust=adj_type, adjust_end_time='', df=True)
    raw_bars = format_kline(kline, freq=tactic.base_freq)
    # print(raw_bars[-1])
    # print(raw_bars[-2])
    if kwargs.get("sdt"):
        sdt = pd.to_datetime(kwargs.get("sdt")).date()
    else:
        sdt = (pd.Timestamp.now() - pd.Timedelta(days=1)).date()

    os.makedirs(os.path.join(context.data_path, f'traders'), exist_ok=True)

    try:
        file_trader = os.path.join(context.data_path, f'traders/{symbol}.ct')

        if os.path.exists(file_trader) and context.mode != MODE_BACKTEST:
            trader: CzscTrader = dill.load(open(file_trader, 'rb'))
            logger.info(f"{symbol} Loaded Trader from {file_trader}")

        else:
            trader = tactic.init_trader(raw_bars, sdt=sdt)
            dill.dump(trader, open(file_trader, 'wb'))

        meta = {
            "symbol": symbol,
            "kline": kline,
            "trader": trader,
            "base_freq": tactic.base_freq,
        }
        return meta
    except Exception as e1:
        logger.exception(f"{e1}：{symbol} - 初始化失败，当前时间：{context.now}")


def format_kline(df, freq=Freq.F1):
    """对分钟K线进行格式化"""
    freq = Freq(freq)
    rows = df.to_dict("records")
    local_tz = pytz.timezone('Asia/Shanghai')
    raw_bars = []
    for i, row in enumerate(rows):
        # 首先将'eob'转换到本地时区
        local_dt = row['eob'].astimezone(local_tz)
        # 然后加一分钟（根据需要调整）
        adjusted_local_dt = local_dt + timedelta(minutes=1)
        # 最后转换为去除时区信息的datetime对象
        utc_naive = adjusted_local_dt.replace(tzinfo=None)

        bar = RawBar(
            symbol=row["symbol"],
            id=i,
            freq=freq,
            dt=utc_naive,
            open=row["open"],
            close=row["close"],
            high=row["high"],
            low=row["low"],
            vol=row["volume"],
            amount=row["volume"] * row["close"],
        )
        raw_bars.append(bar)
    return raw_bars


def sync_position(context, trader: CzscTrader):
    """同步多头仓位到交易账户"""
    if not trader.positions:
        return

    symbol = trader.symbol
    # name = context.stocks.get(symbol, "无名标的")
    ensemble_pos = trader.get_ensemble_pos(method='mean')
    max_sym_pos = context.symbol_metas[symbol]['max_pos']  # 最大标的仓位
    # target_volume = int(ensemble_pos * max_sym_pos)
    if context.mode == MODE_BACKTEST:
        account = context.account()
    else:
        account = context.account(account_id=context.accountID)
    cash = get_cash(account_id=context.accountID)
    logger.info(f"账户可用资金为：{cash.available}")

    price = trader.latest_price
    sym_positions = get_position(account_id=context.accountID)
    sym_pos_long = [x for x in sym_positions if x.side == PositionSide_Long]
    sym_pos_short = [x for x in sym_positions if x.side == PositionSide_Short]
    if ensemble_pos == 0 and not sym_positions:
        # 如果多头仓位为0且掘金账户没有对应持仓，直接退出
        return

    if ensemble_pos == 0 and sym_pos_long and sym_pos_long[0].volume > 0:
        # 如果多头仓位为0且掘金账户依然还有持仓，清掉仓位
        order_target_volume(symbol=symbol, volume=0, position_side=PositionSide_Long,
                            order_type=OrderType_Limit, price=price, account=context.accountID)
        return

    if ensemble_pos == 0 and sym_pos_short and sym_pos_short[0].volume > 0:
        # 如果多头仓位为0且掘金账户依然还有持仓，清掉仓位
        order_target_volume(symbol=symbol, volume=0, position_side=PositionSide_Short,
                            order_type=OrderType_Limit, price=price, account=context.accountID)
        return

    # 没有仓位变化，直接退出
    if not trader.pos_changed:
        return

    # 仓位指向空头，直接退出

    if cash.available < cash.nav * 0.6:
        logger.info(f"{context.now} {symbol} 可用资金不足，达到风控阈值，不再开仓")
        return

    if is_order_exist(context, symbol, PositionSide_Long):
        logger.info(f"{context.now} {symbol} 同方向订单已存在")
        return

    if ensemble_pos > 0:
        volume = max(int(max_sym_pos * ensemble_pos), 1)
        order_target_volume(symbol=symbol, volume=volume, position_side=PositionSide_Long,
                            order_type=OrderType_Limit, price=price, account=context.accountID)
    elif ensemble_pos < 0:
        volume = min(int(max_sym_pos * ensemble_pos), -1)
        order_target_volume(symbol=symbol, volume=abs(volume), position_side=PositionSide_Short,
                            order_type=OrderType_Limit, price=price, account=context.accountID)


def save_traders(context):
    """实盘：保存交易员快照"""
    if context.now.isoweekday() > 5:
        print(f"save_traders: {context.now} 不是交易时间")
        return

    for symbol in context.symbol_metas.keys():
        trader: CzscTrader = context.symbol_metas[symbol]['trader']
        if context.mode != MODE_BACKTEST:
            file_trader = os.path.join(context.data_path, f'traders/{symbol}.ct')
            dill.dump(trader, open(file_trader, 'wb'))


def init_context_schedule(context):
    """通用 context 初始化：设置定时任务"""
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='09:31:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='10:01:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='10:31:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='11:01:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='11:31:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='13:01:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='13:31:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='14:01:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='14:31:00')
    # schedule(schedule_func=report_account_status, date_rule='1d', time_rule='15:01:00')

    # 以下是 实盘/仿真 模式下的定时任务
    if context.mode != MODE_BACKTEST:
        schedule(schedule_func=save_traders, date_rule='1d', time_rule='11:40:00')
        schedule(schedule_func=save_traders, date_rule='1d', time_rule='15:23:00')
        # schedule(schedule_func=realtime_check_index_status, date_rule='1d', time_rule='17:30:00')
        # schedule(schedule_func=process_out_of_symbols, date_rule='1d', time_rule='09:40:00')


def send_trader_change(trader: czsc.CzscTrader, **kwargs):
    """发送持仓变化

    :param trader: czsc.CzscTrader, 交易员对象
    """
    if not trader.pos_changed:
        logger.info(f"{trader.symbol} 持仓未变化")
        return

    feishu_key = kwargs.get("feishu_key")
    ensemble_method = kwargs.get("ensemble_method", "mean")
    ensemble_desc = kwargs.get("ensemble_method", ensemble_method)
    symbol_max_pos = kwargs.get("symbol_max_pos", 0)

    rows = []
    for pos in trader.positions:
        if not pos.operates:
            continue

        last_op = pos.operates[-2] if len(pos.operates) > 1 else None
        curr_op = pos.operates[-1]

        if last_op:
            last_op = f"{last_op['dt']} | {last_op['op']} | 价格：{last_op['price']} | {last_op['op_desc']}"
        else:
            last_op = ""

        curr_op = f"{curr_op['dt']} | {curr_op['op']} | 价格：{curr_op['price']} | {curr_op['op_desc']}"

        row = {
            "pos": f"{pos.pos:.1%}",
            "pos_name": pos.name,
            "last_op": last_op,
            "curr_op": curr_op,
        }
        rows.append(row)

    dfr = pd.DataFrame(rows)

    # 总的目标仓位说明
    ensemble_pos = trader.get_ensemble_pos(ensemble_method)
    target_vol = int(ensemble_pos * symbol_max_pos)

    target = f"目标持仓：int({ensemble_pos} * {symbol_max_pos}) = {target_vol} 手；集成方法：{ensemble_desc}"

    # 使用 CzscTrader仓位变动通知卡片发送消息
    card = {
        "type": "template",
        "data": {
            # 卡片模板 ID 需要根据实际情况修改，可以在飞书后台查看
            "template_id": "AAq3L1dkwNCX3",
            "template_variable": {"symbol": trader.symbol,
                                  "target": target,
                                  "dfr": dfr.to_dict(orient="records")},
        },
    }
    card_str = json.dumps(card)
    czsc.fsa.push_card(card_str, feishu_key)


if __name__ == '__main__':
    run(filename=os.path.basename(__file__),
        token=os.environ['gm_token'],
        mode=MODE_LIVE,
        strategy_id=os.environ['gm_strategyID'])
