# -*- coding: utf-8 -*-
"""
author: zengbin93
email: zeng_bin8888@163.com
create_dt: 2021/8/3 17:25
"""
import traceback
from czsc.signals.signals import get_default_signals
from czsc.objects import Signal, Factor, Event, Operate
from czsc.utils.io import read_pkl, save_pkl

from .utils.base import *


def get_monitor_signals(c):
    s = get_default_signals(c)
    return s


def stocks_monitor(symbols, wx_key):
    """对实盘股票池进行定时监控"""
    events = [
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

    shares = get_shares()
    data_path = './data/monitor'
    os.makedirs(data_path, exist_ok=True)
    push_text("实盘池监控启动 @ {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")), wx_key)

    for symbol in symbols:
        try:
            file_ct = os.path.join(data_path, "{}.ct".format(symbol))
            if os.path.exists(file_ct):
                ct: GmCzscTrader = read_pkl(file_ct)
                ct.update_factors()
            else:
                ct = GmCzscTrader(symbol, max_count=2000, get_signals=get_monitor_signals)
            save_pkl(ct, file_ct)
            print(f"run monitor on {symbol} at {ct.end_dt}")
            msg = f"标的代码：{symbol}\n标的名称：{shares.get(symbol, '')}\n" \
                  f"同花顺F10：http://basic.10jqka.com.cn/{symbol.split('.')[1]}\n"
            msg += f"新浪行情：https://finance.sina.com.cn/realstock/company/{symbol[:2].lower()}{symbol[-6:]}/nc.shtml\n"
            for event in events:
                m, f = event.is_match(ct.s)
                if m:
                    msg += "监控提醒：{}@{}\n".format(event.name, f)

            if "监控提醒" in msg:
                push_text(msg.strip("\n"), key=wx_key)

        except Exception as e:
            traceback.print_exc()
            print("{} 执行失败 - {}".format(symbol, e))
    push_text("实盘池监控结束 @ {}".format(datetime.now().strftime("%Y-%m-%d %H:%M")), wx_key)


def stocks_monitor_rt(context):
    if context.now.isoweekday() >= 6:
        return
    stocks_monitor(list(context.symbols_map.keys()), context.wx_key)


if __name__ == '__main__':
    symbols = pd.read_excel(r"C:\gm_logs\ZB20210726.xlsx")['股票代码'].unique().tolist()
    to_gm_symbol = lambda x: "SHSE." + x[:6] if x[0] == "6" else "SZSE." + x[:6]
    symbols = [to_gm_symbol(x) for x in symbols]
    wx_key = '909731bd-****-46ad-****-24b9830873a4'
    stocks_monitor(symbols, wx_key)

