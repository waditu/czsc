from czsc.extend.utils import push_text
from datetime import datetime
from czsc.extend.analyzeExtend import JKCzscTraderExtend as CzscTrader
import traceback
import time
import datetime

import shutil
import os
from czsc.objects import Signal, Factor, Event, Operate
from czsc.data.jq import get_kline
import pandas as pd

# 基础参数配置
ct_path = os.path.join("d:\\data", "czsc_traders")
os.makedirs(ct_path, exist_ok=True)
symbol = '399006.XSHE'

my_dic_container = {}
def start():
    moni_path = os.path.join(ct_path, "monitor")
    if os.path.exists(moni_path):
        shutil.rmtree(moni_path)
    os.makedirs(moni_path, exist_ok=True)
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
    try:
        current_date: datetime = pd.to_datetime('2021-08-10')
        end_date = pd.to_datetime("2021-08-20")
        ct = CzscTrader(symbol, max_count=1000, end_date=current_date)
        data = get_kline(symbol, end_date=end_date, start_date=current_date, freq="1min")

        hit_event: dict = {}

        for item in data:
            msg = f"标的代码：{symbol}\n同花顺F10：http://basic.10jqka.com.cn/{symbol.split('.')[0]}\n"
            for event in events_monitor:
                m, f = event.is_match(ct.s)
                container_key = "{}{}{}".format(symbol, f, item.dt.strftime('%Y-%m-%d'))
                if m:
                    result = my_dic_container.get(container_key, None)
                    if result is None:
                        print("监控提醒：date{} {}@{}\n".format(item.dt.strftime('%Y-%m-%d  %H:%M'), event.name, f))
                        key = item.dt.strftime('%Y-%m-%d') + f
                        contains = hit_event.get(key)
                        if contains is None:
                            hit_event[key] = '1'
                            my_dic_container[container_key] = 1
                            msg += "监控提醒：date{} {}@{}\n".format(item.dt.strftime('%Y-%m-%d  %H:%M'), event.name, f)
                            hit_event
            if "监控提醒" in msg:
                push_text(msg.strip("\n"))
                # 每次执行，会在moni_path下面保存一份快照
                file_html = os.path.join(moni_path, f"{ct.symbol}_{item.dt.strftime('%Y%m%d%H%M')}.html")
                ct.take_snapshot(file_html, width="1400px", height="580px")
            ct.update_factors_with_bars([item])
    except Exception as e:
        traceback.print_exc()
        print("{} 执行失败 - {}".format(symbol, e))


if __name__ == '__main__':
    start()
    print("end")
