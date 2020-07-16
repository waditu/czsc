# coding: utf-8
import sys
import warnings
sys.path.insert(0, '.')
sys.path.insert(0, '..')
import czsc
warnings.warn(f"czsc version is {czsc.__version__}")

import os
from tqsdk import TqApi, TqBacktest, TqSim
from datetime import date, datetime, timedelta
from copy import deepcopy
from pathlib import Path
import traceback
from czsc import KlineAnalyze
from zb.utils import create_logger

# 环境准备： pip install tqsdk zb czsc


class TradeAnalyze:
    """5分钟第三类买卖点 + 1分钟线段买卖点 + 日线分型"""
    def __init__(self, klines):
        self.klines = klines
        self.ka_1min = KlineAnalyze(self.klines['1分钟'], name='1分钟')
        self.ka_5min = KlineAnalyze(self.klines['5分钟'], name="5分钟")
        self.ka_D = KlineAnalyze(self.klines['日线'], name='日线')
        self.symbol = self.ka_1min.symbol
        self.end_dt = self.ka_1min.end_dt
        self.latest_price = self.ka_1min.latest_price
        self.s = self.signals()
        self.desc = self.__doc__

    def signals(self):
        """计算交易决策需要的状态信息"""
        s = {"symbol": self.symbol,
             "dt": self.end_dt,
             "base_price": self.ka_5min.xd[-1]['xd'],
             "latest_price": self.latest_price,
             "5分钟顶分型后有效跌破MA5": False,
             "5分钟底分型后有效升破MA5": False,
             "5分钟三买": False,
             "5分钟三卖": False,
             "5分钟线段标记": self.ka_5min.xd[-1]['fx_mark'],
             "5分钟笔标记": self.ka_5min.bi[-1]['fx_mark'],
             "日线最后一个分型": self.ka_D.fx[-1]['fx_mark'],
             "1分钟有线买": False,
             "1分钟有线卖": False,
             }

        b1 = is_xd_buy(self.ka_1min, self.ka_5min, pf=True)
        if b1["操作提示"] == "线买":
            s['1分钟有线买'] = True

        s1 = is_xd_sell(self.ka_1min, self.ka_5min, pf=True)
        if s1["操作提示"] == "线卖":
            s['1分钟有线卖'] = True

        ka = self.ka_5min
        xds = ka.xd[-6:]

        # 至少需要6个线段标记
        if len(xds) < 6:
            return s

        zs_d = max([x['xd'] for x in xds[:4] if x['fx_mark'] == 'd'])
        zs_g = min([x['xd'] for x in xds[:4] if x['fx_mark'] == 'g'])
        if zs_g > zs_d:
            if xds[-1]['fx_mark'] == 'd' and xds[-1]['xd'] > zs_g:
                s['5分钟三买'] = True

            if xds[-1]['fx_mark'] == 'g' and xds[-1]['xd'] < zs_d:
                s['5分钟三卖'] = True

        df = create_df(ka, ma_params=(5,))
        last_fx = ka.fx[-1]
        df_last = df[df.dt >= last_fx['dt']]

        if last_fx['fx_mark'] == 'g' and df_last.iloc[1]['close'] < df_last.iloc[1]['ma5']:
            s['5分钟顶分型后有效跌破MA5'] = True

        if last_fx['fx_mark'] == 'd' and df_last.iloc[1]['close'] > df_last.iloc[1]['ma5']:
            s['5分钟底分型后有效升破MA5'] = True

        return {k: v for k, v in s.items()}

    def long_open(self):
        s = self.s
        if s['日线最后一个分型'] == "d" and s['5分钟三买'] and s['5分钟底分型后有效升破MA5'] and s['1分钟有线买']:
            return True
        else:
            return False

    def long_close(self):
        s = self.s
        if s['5分钟线段标记'] == "g" and s['5分钟顶分型后有效跌破MA5'] and s['1分钟有线卖']:
            return True
        else:
            return False

    def short_open(self):
        s = self.s
        if s['日线最后一个分型'] == "g" and s['5分钟三卖'] and s['5分钟顶分型后有效跌破MA5'] and s['1分钟有线卖']:
            return True
        else:
            return False

    def short_close(self):
        s = self.s
        if s['5分钟线段标记'] == 'd' and s['5分钟底分型后有效升破MA5'] and s['1分钟有线买']:
            return True
        else:
            return False


def format_kline(kline):
    """格式化K线"""
    def __convert_time(t):
        try:
            dt = datetime.utcfromtimestamp(t/1000000000)
            dt = dt + timedelta(hours=8)    # 中国默认时区
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return ""

    kline['dt'] = kline['datetime'].apply(__convert_time)
    kline['vol'] = kline['volume']
    columns = ['symbol', 'dt', 'open', 'close', 'high', 'low', 'vol']
    df = kline[columns]
    df = df.dropna(axis=0)
    df.sort_values('dt', inplace=True, ascending=True)
    df.reset_index(drop=True, inplace=True)
    return df


if __name__ == '__main__':
    start_dt = date(2020, 6, 16)
    end_dt = date(2020, 6, 16)
    init_balance = 100000
    port = '53318'
    freqs_k_count = {"1分钟": 1000, "5分钟": 1000, "日线": 200}

    max_positions = {
        "KQ.i@SHFE.au": 1,
        "KQ.i@DCE.jd": 4,
    }

    data_path = f"./logs/S05_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    Path(data_path).mkdir(parents=True, exist_ok=False)
    file_log = os.path.join(data_path, "backtest.log")
    file_signals = os.path.join(data_path, "signals.txt")

    logger = create_logger(log_file=file_log, cmd=True, name="S")
    logger.info(f"标的配置：{max_positions}")
    logger.info(f"前端地址：http://127.0.0.1:{port}")
    logger.info(f"策略描述：{TradeAnalyze.__doc__}")

    account = TqSim(init_balance=init_balance)
    backtest = TqBacktest(start_dt=start_dt, end_dt=end_dt)
    api = TqApi(account=account, backtest=backtest, web_gui=f":{port}")
    symbols = list(max_positions.keys())
    freqs = list(freqs_k_count.keys())

    freq_seconds = {"1分钟": 60, "5分钟": 60 * 5, "15分钟": 60 * 15,
                    "30分钟": 60 * 30, "60分钟": 60 * 60, "日线": 3600 * 24}

    # 订阅K线
    symbols_klines = {s: dict() for s in symbols}
    for symbol in symbols:
        for freq in freqs:
            symbols_klines[symbol][freq] = api.get_kline_serial(symbol,
                                                                freq_seconds[freq],
                                                                data_length=freqs_k_count[freq])

    account = api.get_account()
    positions = api.get_position()

    while True:
        api.wait_update()
        for symbol in symbols:
            if api.is_changing(symbols_klines[symbol]["5分钟"]):
                klines = {k: format_kline(deepcopy(symbols_klines[symbol][k])) for k in freqs}
                try:
                    ta = TradeAnalyze(klines)
                    with open(file_signals, 'a', encoding='utf-8') as f:
                        f.write(str(ta.s) + "\n")
                except:
                    traceback.print_exc()
                    continue

                cur_pos = positions.get(symbol, None)
                if cur_pos:
                    long_pos = {
                        "dt": ta.end_dt,
                        "volume": cur_pos.pos_long,
                        "td_volume": cur_pos.pos_long_today,
                        "yd_volume": cur_pos.pos_long_his,
                    }
                    short_pos = {
                        "dt": ta.end_dt,
                        "volume": cur_pos.pos_short,
                        "td_volume": cur_pos.pos_short_today,
                        "yd_volume": cur_pos.pos_short_his,
                    }
                else:
                    long_pos = {"dt": ta.end_dt, "volume": 0, "td_volume": 0, "yd_volume": 0}
                    short_pos = {"dt": ta.end_dt, "volume": 0, "td_volume": 0, "yd_volume": 0}

                logger.info(f"{symbol} - 当前多仓持仓情况：{long_pos}")
                logger.info(f"{symbol} - 当前空仓持仓情况：{short_pos}")

                # 下单
                if ta.long_close() and long_pos.get('volume', 0) > 0:
                    if long_pos.get("td_volume", 0):
                        order = api.insert_order(symbol=symbol, direction="SELL", offset="CLOSETODAY",
                                                 volume=long_pos['td_volume'])

                    if long_pos.get("yd_volume", 0):
                        order = api.insert_order(symbol=symbol, direction="SELL", offset="CLOSE",
                                                 volume=long_pos['yd_volume'])

                if ta.long_open() and long_pos.get('volume', 0) == 0:
                    order = api.insert_order(symbol=symbol, direction="BUY", offset="OPEN",
                                             volume=max_positions[symbol])

                # 平空仓
                if ta.short_close() and short_pos.get('volume', 0) > 0:
                    if short_pos.get("td_volume", 0) > 0:
                        order = api.insert_order(symbol=symbol, direction="BUY", offset="CLOSETODAY",
                                                 volume=short_pos['td_volume'])

                    if short_pos.get("yd_volume", 0) > 0:
                        order = api.insert_order(symbol=symbol, direction="BUY", offset="CLOSE",
                                                 volume=short_pos['yd_volume'])

                # 开空仓
                if ta.short_open() and short_pos.get('volume', 0) == 0:
                    order = api.insert_order(symbol=symbol, direction="SELL", offset="OPEN",
                                             volume=max_positions[symbol])
